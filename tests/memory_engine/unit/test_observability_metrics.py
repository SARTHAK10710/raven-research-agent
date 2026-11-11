"""Phase 8.3 step 5: the metrics port and ingestion events (plan 8.3 section 11; 7.7)."""

import json
import logging
import uuid
from typing import Any

import pytest

from memory_engine.domain.errors import OwnershipError
from memory_engine.exceptions import (
    ConcurrencyConflictError,
    ConfigurationError,
    DeletionInProgressError,
    IdempotencyKeyReusedError,
    IngestionRejectedError,
    ObjectStorageError,
    PersistenceError,
    RecordNotFoundError,
)
from memory_engine.observability import (
    NO_METRICS,
    InMemoryMetrics,
    JsonFormatter,
    observe_ingestion,
    validate_labels,
)
from memory_engine.observability.metrics import (
    INGESTION_DURATION,
    INGESTION_REJECTIONS,
    INGESTION_REQUESTS,
)

OWNER = uuid.UUID("00000000-0000-4000-8000-0000000000aa")


# --- labels ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "labels",
    [
        {"input": "text", "outcome": "accepted"},
        {"reason": "EMPTY_CONTENT"},
        {"kind": "personal_extraction"},
        {"reason": "CONTENT_TOO_LARGE_2"},
    ],
)
def test_bounded_labels_are_accepted(labels: dict[str, str]) -> None:
    assert validate_labels(labels) == tuple(sorted(labels.items()))


@pytest.mark.parametrize(
    "labels",
    [
        {"owner": "x"},  # unknown key
        {"input": str(OWNER)},  # an identifier
        {"input": "Text"},  # mixed case
        {"input": "text with spaces"},
        {"input": ""},
        {"reason": "A" * 65},
        {"input": "a" * 65},
        {"outcome": 3},
    ],
)
def test_identifiers_and_free_text_never_become_labels(labels: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="metric label"):
        validate_labels(labels)


def test_the_no_op_recorder_still_checks_labels() -> None:
    NO_METRICS.increment("x", {"input": "text"})
    NO_METRICS.observe("x", 1.0)
    NO_METRICS.set_gauge("x", 1.0, None)
    with pytest.raises(ValueError, match="metric label"):
        NO_METRICS.observe("x", 1.0, {"input": str(OWNER)})


def test_the_in_memory_recorder_keeps_counts_observations_and_gauges() -> None:
    metrics = InMemoryMetrics()
    metrics.increment("requests", {"input": "text", "outcome": "accepted"})
    metrics.increment("requests", {"outcome": "accepted", "input": "text"}, amount=2)
    metrics.observe("duration", 0.5, {"input": "text"})
    metrics.set_gauge("pending", 3)
    metrics.set_gauge("pending", 1)
    assert metrics.count("requests", input="text", outcome="accepted") == 3
    assert metrics.count("requests", input="document", outcome="accepted") == 0
    assert metrics.observations("duration", input="text") == [0.5]
    assert metrics.gauge("pending") == 1 and metrics.gauge("missing") is None
    assert metrics.label_values() == {"input": {"text"}, "outcome": {"accepted"}}
    with pytest.raises(ValueError, match="only increase"):
        metrics.increment("requests", amount=-1)


# --- ingestion events -----------------------------------------------------------------


def _records(caplog: pytest.LogCaptureFixture) -> list[dict[str, Any]]:
    formatter = JsonFormatter(service="test", environment="testing")
    return [
        json.loads(formatter.format(r))
        for r in caplog.records
        if r.name == "raven.memory_engine.ingestion"
    ]


def test_an_accepted_request_emits_one_event_and_its_metrics(
    caplog: pytest.LogCaptureFixture,
) -> None:
    metrics = InMemoryMetrics()
    caplog.set_level(logging.DEBUG, logger="raven.memory_engine")
    with observe_ingestion(metrics, input_type="text", owner_id=OWNER) as observation:
        observation.fields["source_id"] = "s-1"
    assert metrics.count(INGESTION_REQUESTS, input="text", outcome="accepted") == 1
    [duration] = metrics.observations(INGESTION_DURATION, input="text", outcome="accepted")
    assert duration >= 0
    [event] = _records(caplog)
    assert event["event_type"] == "ingestion.accepted" and event["level"] == "INFO"
    assert event["user_scope"] == str(OWNER) and event["source_id"] == "s-1"
    assert "error_code" not in event
    assert str(OWNER) not in str(metrics.label_values())  # owner only in logs


CASES = [
    (
        IngestionRejectedError(
            "x", details={"outcome": "invalid_input", "reason": "EMPTY_CONTENT"}
        ),
        "invalid_input",
        "EMPTY_CONTENT",
        "WARNING",
    ),
    (
        IngestionRejectedError(
            "x", details={"outcome": "unsupported_input", "reason": "UNSUPPORTED_SOURCE_TYPE"}
        ),
        "unsupported_input",
        "UNSUPPORTED_SOURCE_TYPE",
        "WARNING",
    ),
    (IdempotencyKeyReusedError("x"), "key_reused", "IDEMPOTENCY_KEY_REUSED", "WARNING"),
    (OwnershipError("x"), "ownership_denied", None, "WARNING"),
    (ObjectStorageError("x"), "storage_failed", "OBJECT_STORAGE_ERROR", "ERROR"),
    (PersistenceError("x"), "registration_failed", "PERSISTENCE_ERROR", "ERROR"),
    (DeletionInProgressError("x"), "refused", None, "WARNING"),
    (RecordNotFoundError("x"), "refused", None, "WARNING"),
    (ConcurrencyConflictError("x"), "refused", None, "WARNING"),
    (ConfigurationError("x"), "failed", "CONFIGURATION_ERROR", "ERROR"),
    (RuntimeError("synthetic secret detail"), "failed", "UNEXPECTED_ERROR", "ERROR"),
]


@pytest.mark.parametrize(("error", "outcome", "code", "level"), CASES)
def test_every_failure_is_classified_and_re_raised(
    caplog: pytest.LogCaptureFixture,
    error: Exception,
    outcome: str,
    code: str | None,
    level: str,
) -> None:
    metrics = InMemoryMetrics()
    caplog.set_level(logging.DEBUG, logger="raven.memory_engine")
    with (
        pytest.raises(type(error)),
        observe_ingestion(metrics, input_type="document", owner_id=OWNER),
    ):
        raise error
    assert metrics.count(INGESTION_REQUESTS, input="document", outcome=outcome) == 1
    [event] = _records(caplog)
    assert event["event_type"] == f"ingestion.{outcome}" and event["level"] == level
    expected = code if code is not None else getattr(error, "code", None)
    assert event["error_code"] == expected
    assert "synthetic secret detail" not in json.dumps(event)  # never the message
    if outcome in ("invalid_input", "unsupported_input"):
        assert metrics.count(INGESTION_REJECTIONS, input="document", reason=expected) == 1
    else:
        assert metrics.label_values().get("reason") is None
    if expected == "UNEXPECTED_ERROR":
        assert event["error_type"] == "RuntimeError"


class _BrokenMetrics(InMemoryMetrics):
    def increment(self, name: str, labels: Any = None, amount: int = 1) -> None:
        raise RuntimeError("synthetic: exporter down")


def test_broken_telemetry_never_changes_the_outcome(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="raven.memory_engine")
    with observe_ingestion(_BrokenMetrics(), input_type="text", owner_id=OWNER):
        pass  # success stays success
    with (
        pytest.raises(PersistenceError),
        observe_ingestion(_BrokenMetrics(), input_type="text", owner_id=OWNER),
    ):
        raise PersistenceError("x")  # the original error is the one raised
    warnings = [r for r in _records(caplog) if r["event_type"] == "observability.failure"]
    assert len(warnings) == 2 and warnings[0]["error_type"] == "RuntimeError"
