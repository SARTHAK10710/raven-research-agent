"""Phase 8.3 step 5: ingestion and handoff events and metrics against real PostgreSQL.

Plan 8.3 section 11: requests, accepted and rejected requests, validation and
storage failures, duplicates, document registration, handoff, handoff failures,
latency, retry counts and outbox backlog, correlated by identifiers, with no
content in logs and no identifiers in metric labels. Synthetic data only.
"""

import io
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.orm import Session, sessionmaker

from memory_engine.config.settings import OutboxSettings
from memory_engine.documents.application.ingestion import (
    DocumentIngestionService,
    DocumentUpload,
)
from memory_engine.domain.errors import OwnershipError
from memory_engine.domain.handoff import OutboxMessage
from memory_engine.domain.identifiers import OwnerScope
from memory_engine.domain.vocabulary import InstructionType, SourceType
from memory_engine.exceptions import (
    IngestionRejectedError,
    MessagePublishError,
    ObjectStorageError,
    PersistenceError,
)
from memory_engine.infrastructure.messaging import OutboxRelay
from memory_engine.infrastructure.object_storage import InMemoryObjectStorage
from memory_engine.infrastructure.persistence import (
    SqlAlchemyDocumentUnitOfWorkFactory,
    SqlAlchemyPersonalUnitOfWorkFactory,
)
from memory_engine.infrastructure.persistence.outbox import SqlAlchemyOutboxRepository
from memory_engine.observability import InMemoryMetrics, JsonFormatter
from memory_engine.observability.metrics import (
    DOCUMENT_REGISTRATIONS,
    HANDOFF_ATTEMPTS,
    HANDOFF_LATENCY,
    INGESTION_REJECTIONS,
    INGESTION_REQUESTS,
    OUTBOX_FAILED,
    OUTBOX_OLDEST_PENDING_AGE,
    OUTBOX_PENDING,
)
from memory_engine.personal.application.ingestion import (
    IngestionLimits,
    IngestionRequest,
    PersonalIngestionService,
)

pytestmark = pytest.mark.integration

T0 = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
LIMITS = IngestionLimits(
    max_text_bytes=256 * 1024, max_conversation_messages=1000, max_conversation_bytes=4 * 1024**2
)
PRIVATE_TEXT = "Synthetic private note: my locker code is 4417."
PDF = b"%PDF-1.7\nsynthetic\n%%EOF\n"
PDF_V2 = b"%PDF-1.7\nsynthetic, revised\n%%EOF\n"


def _events(caplog: pytest.LogCaptureFixture) -> list[dict[str, Any]]:
    formatter = JsonFormatter(service="test", environment="testing")
    return [
        json.loads(formatter.format(r))
        for r in caplog.records
        if r.name.startswith("raven.memory_engine")
    ]


@pytest.fixture(autouse=True)
def capture(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="raven.memory_engine")


def _personal(
    uow: SqlAlchemyPersonalUnitOfWorkFactory, metrics: InMemoryMetrics, storage: Any = None
) -> PersonalIngestionService:
    return PersonalIngestionService(
        uow, storage or InMemoryObjectStorage(), LIMITS, clock=lambda: T0, metrics=metrics
    )


def _text(owner: OwnerScope, key: str = "k-1", **overrides: Any) -> IngestionRequest:
    values: dict[str, Any] = {
        "owner_id": owner.owner_id,
        "idempotency_key": key,
        "source_type": SourceType.TEXT,
        "text": PRIVATE_TEXT,
    }
    return IngestionRequest(**values | overrides)


def test_personal_outcomes_are_counted_and_logged_without_content(
    uow_factory: SqlAlchemyPersonalUnitOfWorkFactory,
    owner: OwnerScope,
    other_owner: OwnerScope,
    caplog: pytest.LogCaptureFixture,
) -> None:
    metrics = InMemoryMetrics()
    service = _personal(uow_factory, metrics)
    result = service.ingest(owner, _text(owner))
    service.ingest(owner, _text(owner))  # duplicate
    with pytest.raises(IngestionRejectedError):
        service.ingest(owner, _text(owner, "k-2", text="  "))
    with pytest.raises(OwnershipError):
        service.ingest(owner, _text(other_owner, "k-3"))
    down = InMemoryObjectStorage()
    down.available = False
    with pytest.raises(ObjectStorageError):
        _personal(uow_factory, metrics, down).ingest(owner, _text(owner, "k-4"))

    def count(outcome: str) -> int:
        return metrics.count(INGESTION_REQUESTS, input="text", outcome=outcome)

    assert [count(o) for o in ("accepted", "replayed", "invalid_input")] == [1, 1, 1]
    assert [count(o) for o in ("ownership_denied", "storage_failed")] == [1, 1]
    assert metrics.count(INGESTION_REJECTIONS, input="text", reason="EMPTY_CONTENT") == 1

    events = _events(caplog)
    accepted = next(e for e in events if e["event_type"] == "ingestion.accepted")
    assert accepted["source_id"] == str(result.source_id)
    assert accepted["user_scope"] == str(owner.owner_id)
    assert (accepted["handoff"], accepted["processing_status"]) == ("true", "validated")
    assert "duration_ms" in accepted
    logged = json.dumps(events)
    assert PRIVATE_TEXT not in logged and "4417" not in logged  # never content
    assert "k-1" not in logged  # nor caller-supplied idempotency keys
    labels = str(metrics.label_values())
    assert str(owner.owner_id) not in labels and str(result.source_id) not in labels


def test_a_forget_instruction_is_logged_as_not_handed_off(
    uow_factory: SqlAlchemyPersonalUnitOfWorkFactory,
    owner: OwnerScope,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _personal(uow_factory, InMemoryMetrics()).ingest(
        owner, _text(owner, instruction_type=InstructionType.FORGET)
    )
    [event] = [e for e in _events(caplog) if e["event_type"] == "ingestion.accepted"]
    assert (event["instruction_type"], event["handoff"]) == ("forget", "false")


def test_document_registrations_are_counted_by_kind(
    doc_uow_factory: SqlAlchemyDocumentUnitOfWorkFactory,
    owner: OwnerScope,
    caplog: pytest.LogCaptureFixture,
) -> None:
    metrics = InMemoryMetrics()
    service = DocumentIngestionService(
        doc_uow_factory, InMemoryObjectStorage(), max_upload_bytes=1024, metrics=metrics
    )

    def upload(key: str, data: bytes, **extra: Any) -> DocumentUpload:
        return DocumentUpload(
            owner_id=owner.owner_id,
            idempotency_key=key,
            filename="Synthetic confidential plan.pdf",
            data=io.BytesIO(data),
            **extra,
        )

    first = service.ingest(owner, upload("d-1", PDF))
    service.ingest(owner, upload("d-1", PDF))  # duplicate
    service.ingest(owner, upload("d-2", PDF_V2, document_id=first.document_id))
    with pytest.raises(IngestionRejectedError):
        service.ingest(owner, upload("d-3", b""))

    assert metrics.count(DOCUMENT_REGISTRATIONS, kind="document") == 1
    assert metrics.count(DOCUMENT_REGISTRATIONS, kind="version") == 1
    assert metrics.count(INGESTION_REQUESTS, input="document", outcome="accepted") == 2
    assert metrics.count(INGESTION_REQUESTS, input="document", outcome="replayed") == 1
    assert metrics.count(INGESTION_REJECTIONS, input="document", reason="EMPTY_FILE") == 1
    events = _events(caplog)
    accepted = next(e for e in events if e["event_type"] == "ingestion.accepted")
    assert accepted["document_id"] == str(first.document_id)
    assert accepted["operation_id"] == str(first.operation_id)
    assert accepted["version_status"] == "stored"  # registered, not processed
    assert "confidential" not in json.dumps(events)  # filenames are not logged


class _Publisher:
    def __init__(self, failures: int = 0) -> None:
        self.failures = failures

    def publish(self, message: OutboxMessage) -> None:
        if self.failures:
            self.failures -= 1
            raise MessagePublishError("synthetic: broker unavailable")


def test_handoff_attempts_latency_and_backlog_are_measured(
    uow_factory: SqlAlchemyPersonalUnitOfWorkFactory,
    session_factory: sessionmaker[Session],
    owner: OwnerScope,
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = _personal(uow_factory, InMemoryMetrics())
    for key in ("a", "b"):
        service.ingest(owner, _text(owner, key))
    metrics = InMemoryMetrics()
    now = T0 + timedelta(seconds=30)

    def relay(publisher: _Publisher, at: datetime) -> OutboxRelay:
        return OutboxRelay(
            session_factory,
            publisher,
            OutboxSettings(max_attempts=1),
            clock=lambda: at,
            jitter=lambda d: d,
            metrics=metrics,
        )

    relay(_Publisher(failures=1), now).relay_due()  # one fails for good, batch stops
    assert metrics.count(HANDOFF_ATTEMPTS, kind="personal_extraction", outcome="failed") == 1
    assert (metrics.gauge(OUTBOX_PENDING), metrics.gauge(OUTBOX_FAILED)) == (1, 1)
    # Database clock; the test transaction's now() equals the rows' created_at.
    assert metrics.gauge(OUTBOX_OLDEST_PENDING_AGE) == 0.0

    relay(_Publisher(), now).relay_due()
    assert metrics.count(HANDOFF_ATTEMPTS, kind="personal_extraction", outcome="published") == 1
    assert metrics.observations(HANDOFF_LATENCY, kind="personal_extraction") == [30.0]
    assert (metrics.gauge(OUTBOX_PENDING), metrics.gauge(OUTBOX_OLDEST_PENDING_AGE)) == (0, 0.0)

    handoffs = [e for e in _events(caplog) if e["event_type"].startswith("handoff.")]
    assert [e["event_type"] for e in handoffs] == ["handoff.failed", "handoff.published"]
    failed = handoffs[0]
    assert failed["error_code"] == "MESSAGE_PUBLISH_ERROR" and failed["attempts"] == 1
    assert failed["user_scope"] == str(owner.owner_id)
    assert {"message_id", "task_id", "correlation_id"} <= set(failed)  # correlated (7.7 §5)
    assert PRIVATE_TEXT not in json.dumps(handoffs)


def test_a_failed_backlog_measurement_keeps_the_handled_messages(
    uow_factory: SqlAlchemyPersonalUnitOfWorkFactory,
    session_factory: sessionmaker[Session],
    owner: OwnerScope,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _personal(uow_factory, InMemoryMetrics()).ingest(owner, _text(owner))

    def fail(self: Any) -> Any:
        raise PersistenceError("synthetic: database gone after the batch")

    monkeypatch.setattr(SqlAlchemyOutboxRepository, "backlog", fail)
    relay = OutboxRelay(
        session_factory, _Publisher(), OutboxSettings(), clock=lambda: T0, metrics=InMemoryMetrics()
    )
    with pytest.raises(PersistenceError):
        relay.relay_due()
    with uow_factory() as uow:
        stored = uow.sources.get(owner, source.source_id)
    assert stored is not None and stored.processing_status.value == "queued"
