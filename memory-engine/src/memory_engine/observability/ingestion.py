"""Ingestion events and metrics (plan 8.3 section 11; owner-approved, 8.3 step 5).

Both ingestion services wrap one request in :func:`observe_ingestion`. On exit
it emits one structured log event and the request metrics, classifying the
outcome from the plan 8.3 section 9 states:

======================  =============================================
outcome                 cause
======================  =============================================
``accepted``            stored and registered now
``replayed``            a duplicate request answered from the record
``invalid_input``       rejected by validation (reason code)
``unsupported_input``   unsupported type or schema (reason code)
``key_reused``          idempotency key reused for another request
``ownership_denied``    the caller's scope does not own the request
``storage_failed``      object storage failed; nothing registered
``registration_failed`` the database failed; uploads removed
``refused``             a business rule refused it (error code)
``failed``              anything else (error code or type)
======================  =============================================

Events carry identifiers, codes, durations and the opaque owner id as
``user_scope`` (owner decision); never content, filenames or caller-supplied
idempotency keys. Metric labels never carry identifiers.
"""

import logging
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from memory_engine.domain.errors import OwnershipError
from memory_engine.exceptions import (
    ConcurrencyConflictError,
    DeletionInProgressError,
    IdempotencyKeyReusedError,
    IngestionRejectedError,
    MemoryEngineError,
    ObjectStorageError,
    PersistenceError,
    RecordNotFoundError,
)
from memory_engine.observability.logging import get_logger
from memory_engine.observability.metrics import (
    INGESTION_DURATION,
    INGESTION_REJECTIONS,
    INGESTION_REQUESTS,
    Metrics,
)

_logger = get_logger("ingestion")

_WARNING_OUTCOMES = frozenset(
    {"invalid_input", "unsupported_input", "key_reused", "ownership_denied", "refused"}
)
_ERROR_OUTCOMES = frozenset({"storage_failed", "registration_failed", "failed"})


@dataclass(slots=True)
class IngestionObservation:
    """Filled in by the service: its success outcome and the record identifiers."""

    outcome: str = "accepted"
    fields: dict[str, str] = field(default_factory=dict)


def _classify(error: BaseException) -> tuple[str, str]:
    if isinstance(error, IngestionRejectedError):
        outcome = error.details.get("outcome", "invalid_input")
        return outcome, error.details.get("reason", error.code)
    if isinstance(error, IdempotencyKeyReusedError):
        return "key_reused", error.code
    if isinstance(error, OwnershipError):
        return "ownership_denied", error.code
    if isinstance(error, ObjectStorageError):
        return "storage_failed", error.code
    if isinstance(error, PersistenceError):
        return "registration_failed", error.code
    if isinstance(error, DeletionInProgressError | RecordNotFoundError | ConcurrencyConflictError):
        return "refused", error.code
    if isinstance(error, MemoryEngineError):
        return "failed", error.code
    return "failed", "UNEXPECTED_ERROR"


@contextmanager
def observe_ingestion(
    metrics: Metrics, *, input_type: str, owner_id: uuid.UUID
) -> Iterator[IngestionObservation]:
    """Record one ingestion request's outcome, duration and event; re-raises errors."""
    observation = IngestionObservation()
    started = time.perf_counter()
    try:
        yield observation
    except BaseException as error:
        outcome, reason = _classify(error)
        _safe_emit(metrics, input_type, owner_id, outcome, reason, started, observation, error)
        raise
    _safe_emit(metrics, input_type, owner_id, observation.outcome, None, started, observation, None)


def _safe_emit(*args: Any) -> None:
    # Telemetry must never change an ingestion's outcome: a committed registration
    # stays reported as success, and the original error is the one re-raised.
    try:
        _emit(*args)
    except Exception as err:
        _logger.warning(
            "ingestion telemetry failed",
            extra={"event_type": "observability.failure", "error_type": type(err).__name__},
        )


def _emit(
    metrics: Metrics,
    input_type: str,
    owner_id: uuid.UUID,
    outcome: str,
    reason: str | None,
    started: float,
    observation: IngestionObservation,
    error: BaseException | None,
) -> None:
    elapsed = time.perf_counter() - started
    labels = {"input": input_type, "outcome": outcome}
    metrics.increment(INGESTION_REQUESTS, labels)
    metrics.observe(INGESTION_DURATION, elapsed, labels)
    if outcome in ("invalid_input", "unsupported_input") and reason is not None:
        metrics.increment(INGESTION_REJECTIONS, {"input": input_type, "reason": reason})
    extra: dict[str, Any] = {
        "event_type": f"ingestion.{outcome}",
        "input_type": input_type,
        "outcome": outcome,
        "user_scope": str(owner_id),
        "duration_ms": round(elapsed * 1000, 3),
        **observation.fields,
    }
    if reason is not None:
        extra["error_code"] = reason
    if error is not None and reason == "UNEXPECTED_ERROR":
        extra["error_type"] = type(error).__name__  # never the message (security rules)
    level = (
        logging.ERROR
        if outcome in _ERROR_OUTCOMES
        else logging.WARNING
        if outcome in _WARNING_OUTCOMES
        else logging.INFO
    )
    _logger.log(level, "ingestion %s", outcome, extra=extra)
