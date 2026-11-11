"""Phase 8.3 step 4: transactional outbox and relay against real PostgreSQL (plan 8.3 §12.3).

The broker is replaced by a recording publisher here; ``test_broker_handoff.py``
covers RabbitMQ itself. Object storage is the in-memory fake. Synthetic data only.
"""

import io
import threading
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import Engine, delete, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from memory_engine.config.settings import OutboxSettings
from memory_engine.documents.application.ingestion import (
    DocumentIngestionService,
    DocumentUpload,
)
from memory_engine.documents.domain.vocabulary import (
    DocumentLifecycleStatus,
    OperationStatus,
    VersionProcessingStatus,
)
from memory_engine.domain.handoff import HandoffKind, OutboxMessage, OutboxStatus
from memory_engine.domain.identifiers import OwnerScope
from memory_engine.domain.vocabulary import (
    InstructionType,
    ProcessingEventType,
    SourceProcessingStatus,
    SourceType,
)
from memory_engine.exceptions import (
    ConcurrencyConflictError,
    MessagePublishError,
    PersistenceError,
    RecordNotFoundError,
)
from memory_engine.infrastructure.messaging import OutboxRelay
from memory_engine.infrastructure.messaging.relay import SUBJECT_NOT_PENDING
from memory_engine.infrastructure.object_storage import InMemoryObjectStorage
from memory_engine.infrastructure.persistence import (
    SqlAlchemyDocumentUnitOfWorkFactory,
    SqlAlchemyPersonalUnitOfWorkFactory,
    create_session_factory,
)
from memory_engine.infrastructure.persistence.outbox import (
    OutboxRow,
    SqlAlchemyOutboxRepository,
)
from memory_engine.infrastructure.persistence.personal.lifecycle_repositories import (
    SqlAlchemyProcessingHistoryRepository,
)
from memory_engine.personal.application.ingestion import (
    IngestionLimits,
    IngestionRequest,
    PersonalIngestionService,
)

pytestmark = pytest.mark.integration

Uow = SqlAlchemyPersonalUnitOfWorkFactory
DocUow = SqlAlchemyDocumentUnitOfWorkFactory
T0 = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
LIMITS = IngestionLimits(
    max_text_bytes=256 * 1024, max_conversation_messages=1000, max_conversation_bytes=4 * 1024**2
)
PDF = b"%PDF-1.7\nsynthetic\n%%EOF\n"


class RecordingPublisher:
    """Stands in for the broker: confirms, or refuses ``failures`` times."""

    def __init__(self, failures: int = 0) -> None:
        self.failures = failures
        self.published: list[OutboxMessage] = []
        self.on_publish: Callable[[], None] | None = None

    def publish(self, message: OutboxMessage) -> None:
        if self.failures:
            self.failures -= 1
            raise MessagePublishError("synthetic: broker unavailable")
        self.published.append(message)
        if self.on_publish is not None:
            self.on_publish()


class Clock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


@pytest.fixture
def clock() -> Clock:
    return Clock(T0 + timedelta(minutes=1))


@pytest.fixture
def make_relay(session_factory: sessionmaker[Session], clock: Clock) -> Callable[..., OutboxRelay]:
    def make(publisher: RecordingPublisher, **settings: Any) -> OutboxRelay:
        return OutboxRelay(
            session_factory,
            publisher,
            OutboxSettings(**settings),
            clock=clock,
            jitter=lambda delay: delay,  # deterministic backoff in tests
        )

    return make


def _ingest_text(
    uow_factory: Uow,
    owner: OwnerScope,
    key: str = "msg-1",
    instruction: InstructionType = InstructionType.NORMAL,
) -> uuid.UUID:
    service = PersonalIngestionService(
        uow_factory, InMemoryObjectStorage(), LIMITS, clock=lambda: T0
    )
    request = IngestionRequest(
        owner_id=owner.owner_id,
        idempotency_key=key,
        source_type=SourceType.TEXT,
        instruction_type=instruction,
        text="Synthetic note: I prefer aisle seats.",
    )
    return service.ingest(owner, request).source_id


def _upload(doc_uow_factory: DocUow, owner: OwnerScope, key: str = "up-1") -> Any:
    service = DocumentIngestionService(
        doc_uow_factory, InMemoryObjectStorage(), max_upload_bytes=1024 * 1024, clock=lambda: T0
    )
    upload = DocumentUpload(
        owner_id=owner.owner_id,
        idempotency_key=key,
        filename="synthetic.pdf",
        data=io.BytesIO(PDF),
    )
    return service.ingest(owner, upload)


def _outbox(uow_factory: Uow, owner: OwnerScope, subject_id: uuid.UUID) -> list[OutboxMessage]:
    with uow_factory() as uow:
        return list(uow.outbox.for_subject(owner, subject_id))


def _source_status(uow_factory: Uow, owner: OwnerScope, source_id: uuid.UUID) -> Any:
    with uow_factory() as uow:
        source = uow.sources.get(owner, source_id)
        events = uow.processing.events(owner, source_id)
    assert source is not None
    return source.processing_status, events


# --- registration writes the handoff in the same transaction ------------------------


def test_registering_a_source_records_one_pending_handoff(
    uow_factory: Uow, owner: OwnerScope
) -> None:
    source_id = _ingest_text(uow_factory, owner)
    [message] = _outbox(uow_factory, owner, source_id)
    assert message.kind is HandoffKind.PERSONAL_EXTRACTION
    assert message.status is OutboxStatus.PENDING and message.attempts == 0
    assert message.envelope.task_id == source_id
    status, events = _source_status(uow_factory, owner, source_id)
    assert status is SourceProcessingStatus.VALIDATED and events == []  # not queued yet


def test_a_forget_instruction_is_never_handed_to_extraction(
    uow_factory: Uow, owner: OwnerScope, make_relay: Callable[..., OutboxRelay]
) -> None:
    source_id = _ingest_text(uow_factory, owner, instruction=InstructionType.FORGET)
    assert _outbox(uow_factory, owner, source_id) == []
    publisher = RecordingPublisher()
    assert make_relay(publisher).relay_due().handled == 0
    assert publisher.published == []
    status, _ = _source_status(uow_factory, owner, source_id)
    assert status is SourceProcessingStatus.VALIDATED  # waits for plan 8.10


def test_a_failed_outbox_write_registers_nothing(
    uow_factory: Uow, owner: OwnerScope, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(self: Any, scope: OwnerScope, message: OutboxMessage) -> None:
        raise PersistenceError("synthetic outbox failure")

    monkeypatch.setattr(SqlAlchemyOutboxRepository, "add", fail)
    storage = InMemoryObjectStorage()
    service = PersonalIngestionService(uow_factory, storage, LIMITS, clock=lambda: T0)
    request = IngestionRequest(
        owner_id=owner.owner_id, idempotency_key="k", source_type=SourceType.TEXT, text="x"
    )
    with pytest.raises(PersistenceError):
        service.ingest(owner, request)
    with uow_factory() as uow:
        assert uow.sources.find_by_idempotency_key(owner, "k") is None
    assert storage._objects == {}  # uploads removed with the failed registration


def test_a_failed_document_handoff_write_registers_nothing(
    doc_uow_factory: DocUow, owner: OwnerScope, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(self: Any, scope: OwnerScope, message: OutboxMessage) -> None:
        raise PersistenceError("synthetic outbox failure")

    monkeypatch.setattr(SqlAlchemyOutboxRepository, "add", fail)
    with pytest.raises(PersistenceError):
        _upload(doc_uow_factory, owner)
    with doc_uow_factory() as uow:
        assert uow.operations.find_by_idempotency_key(owner, "upload:up-1") is None


def test_retried_registrations_never_duplicate_the_handoff(
    uow_factory: Uow, doc_uow_factory: DocUow, owner: OwnerScope
) -> None:
    first = _ingest_text(uow_factory, owner)
    assert _ingest_text(uow_factory, owner) == first
    assert len(_outbox(uow_factory, owner, first)) == 1
    upload = _upload(doc_uow_factory, owner)
    again = _upload(doc_uow_factory, owner)
    assert (again.operation_id, again.created) == (upload.operation_id, False)
    assert len(_outbox(uow_factory, owner, upload.operation_id)) == 1


def test_a_second_handoff_of_the_same_subject_is_refused(
    uow_factory: Uow, owner: OwnerScope
) -> None:
    source_id = _ingest_text(uow_factory, owner)
    [message] = _outbox(uow_factory, owner, source_id)
    duplicate = OutboxMessage.new(
        owner,
        kind=message.kind,
        subject_id=source_id,
        payload={},
        payload_reference=None,
        priority="normal",
        created_at=T0,
    )
    with pytest.raises(PersistenceError), uow_factory() as uow:
        uow.outbox.add(owner, duplicate)


# --- relay: publish, then mark queued ----------------------------------------------


def test_relay_publishes_a_source_and_only_then_queues_it(
    uow_factory: Uow, owner: OwnerScope, make_relay: Callable[..., OutboxRelay], clock: Clock
) -> None:
    source_id = _ingest_text(uow_factory, owner)
    publisher = RecordingPublisher()
    report = make_relay(publisher).relay_due()
    assert (report.published, report.handled) == (1, 1)
    [sent] = publisher.published
    assert sent.subject_id == source_id and sent.envelope.user_id == owner.owner_id
    [message] = _outbox(uow_factory, owner, source_id)
    assert message.status is OutboxStatus.PUBLISHED and message.published_at == clock.now
    status, events = _source_status(uow_factory, owner, source_id)
    assert status is SourceProcessingStatus.QUEUED
    [event] = events
    assert (event.event_type, event.from_status, event.to_status) == (
        ProcessingEventType.TRANSITION,
        SourceProcessingStatus.VALIDATED,
        SourceProcessingStatus.QUEUED,
    )
    assert make_relay(publisher).relay_due().handled == 0  # published once


def test_relay_hands_a_document_to_the_pipeline_without_claiming_progress(
    doc_uow_factory: DocUow, uow_factory: Uow, owner: OwnerScope, make_relay: Any
) -> None:
    result = _upload(doc_uow_factory, owner)
    publisher = RecordingPublisher()
    assert make_relay(publisher).relay_due().published == 1
    with doc_uow_factory() as uow:
        operation = uow.operations.get(owner, result.operation_id)
        version = uow.documents.get_version(owner, result.version_id)
        document = uow.documents.get(owner, result.document_id)
    assert operation is not None and operation.status is OperationStatus.QUEUED
    # Handed off is not processed: the version and document are untouched (plan 8.3 §9).
    assert version is not None and version.processing_status is VersionProcessingStatus.STORED
    assert document is not None and document.lifecycle_status is DocumentLifecycleStatus.REGISTERED
    [message] = _outbox(uow_factory, owner, result.operation_id)
    assert message.status is OutboxStatus.PUBLISHED
    assert message.envelope.payload["version_id"] == str(result.version_id)


def test_relay_respects_its_limit(
    uow_factory: Uow, owner: OwnerScope, make_relay: Callable[..., OutboxRelay]
) -> None:
    for key in ("a", "b", "c"):
        _ingest_text(uow_factory, owner, key)
    relay = make_relay(RecordingPublisher())
    assert relay.relay_due(limit=2).published == 2
    assert relay.relay_due().published == 1


# --- failed handoff and recovery ------------------------------------------------------


def test_a_failed_publish_is_recoverable_and_never_marks_the_source_queued(
    uow_factory: Uow, owner: OwnerScope, make_relay: Callable[..., OutboxRelay], clock: Clock
) -> None:
    source_id = _ingest_text(uow_factory, owner)
    publisher = RecordingPublisher(failures=1)
    relay = make_relay(publisher)
    assert relay.relay_due().retry_scheduled == 1
    [message] = _outbox(uow_factory, owner, source_id)
    assert message.status is OutboxStatus.PENDING
    assert (message.attempts, message.last_error_code) == (1, "MESSAGE_PUBLISH_ERROR")
    assert message.next_attempt_at == clock.now + timedelta(seconds=2)
    status, events = _source_status(uow_factory, owner, source_id)
    assert status is SourceProcessingStatus.VALIDATED and events == []

    assert relay.relay_due().handled == 0  # not due yet: backoff
    clock.advance(2)
    assert relay.relay_due().published == 1
    status, events = _source_status(uow_factory, owner, source_id)
    assert status is SourceProcessingStatus.QUEUED and len(events) == 1
    assert len(publisher.published) == 1


def test_exhausted_attempts_fail_visibly_until_an_explicit_retry(
    uow_factory: Uow, owner: OwnerScope, make_relay: Callable[..., OutboxRelay], clock: Clock
) -> None:
    source_id = _ingest_text(uow_factory, owner)
    publisher = RecordingPublisher(failures=3)
    relay = make_relay(publisher, max_attempts=3)
    outcomes = []
    for _ in range(3):
        report = relay.relay_due()
        outcomes.append((report.retry_scheduled, report.failed))
        clock.advance(600)
    assert outcomes == [(1, 0), (1, 0), (0, 1)]
    [message] = _outbox(uow_factory, owner, source_id)
    assert (message.status, message.attempts) == (OutboxStatus.FAILED, 3)
    clock.advance(86_400)
    assert relay.relay_due().handled == 0  # failed rows are never retried by themselves
    status, _ = _source_status(uow_factory, owner, source_id)
    assert status is SourceProcessingStatus.VALIDATED  # never falsely queued

    with uow_factory() as uow:
        assert uow.outbox.retry_failed(owner, clock.now, [message.id]) == 1
    [message] = _outbox(uow_factory, owner, source_id)
    assert (message.status, message.attempts) == (OutboxStatus.PENDING, 0)
    assert message.last_error_code == "MESSAGE_PUBLISH_ERROR"  # kept for diagnosis
    assert relay.relay_due().published == 1
    status, _ = _source_status(uow_factory, owner, source_id)
    assert status is SourceProcessingStatus.QUEUED


def test_a_commit_failure_after_publishing_republishes_the_same_message(
    uow_factory: Uow,
    owner: OwnerScope,
    make_relay: Callable[..., OutboxRelay],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_id = _ingest_text(uow_factory, owner)
    original = SqlAlchemyProcessingHistoryRepository.transition

    def fail(self: Any, scope: OwnerScope, event: Any) -> None:
        raise PersistenceError("synthetic failure after publish")

    monkeypatch.setattr(SqlAlchemyProcessingHistoryRepository, "transition", fail)
    publisher = RecordingPublisher()
    relay = make_relay(publisher)
    with pytest.raises(PersistenceError):
        relay.relay_due()
    [message] = _outbox(uow_factory, owner, source_id)
    assert message.status is OutboxStatus.PENDING and message.attempts == 0
    status, _ = _source_status(uow_factory, owner, source_id)
    assert status is SourceProcessingStatus.VALIDATED

    monkeypatch.setattr(SqlAlchemyProcessingHistoryRepository, "transition", original)
    assert relay.relay_due().published == 1
    # At least once: the same message id twice, so a consumer can deduplicate.
    assert [m.id for m in publisher.published] == [message.id, message.id]
    status, events = _source_status(uow_factory, owner, source_id)
    assert status is SourceProcessingStatus.QUEUED and len(events) == 1
    with uow_factory() as uow:
        assert uow.sources.find_by_idempotency_key(owner, "msg-1") is not None
    assert len(_outbox(uow_factory, owner, source_id)) == 1


def test_a_publish_failure_ends_the_batch_and_leaves_the_rest_untouched(
    uow_factory: Uow, owner: OwnerScope, make_relay: Callable[..., OutboxRelay]
) -> None:
    first = _ingest_text(uow_factory, owner, "a")
    second = _ingest_text(uow_factory, owner, "b")
    report = make_relay(RecordingPublisher(failures=1)).relay_due()
    assert (report.retry_scheduled, report.handled) == (1, 1)
    attempts = sorted(
        message.attempts
        for subject in (first, second)
        for message in _outbox(uow_factory, owner, subject)
    )
    assert attempts == [0, 1]  # the second message was not tried against a failing broker


def test_a_cancelled_operation_is_not_handed_off(
    doc_uow_factory: DocUow, uow_factory: Uow, owner: OwnerScope, make_relay: Any
) -> None:
    result = _upload(doc_uow_factory, owner)
    with doc_uow_factory() as uow:
        uow.operations.transition(
            owner,
            result.operation_id,
            OperationStatus.CANCELLATION_REQUESTED,
            expected=OperationStatus.CREATED,
        )
    publisher = RecordingPublisher()
    assert make_relay(publisher).relay_due().abandoned == 1
    assert publisher.published == []
    [message] = _outbox(uow_factory, owner, result.operation_id)
    assert (message.status, message.last_error_code) == (OutboxStatus.FAILED, SUBJECT_NOT_PENDING)


def test_relay_writes_each_owner_in_its_own_scope(
    uow_factory: Uow,
    owner: OwnerScope,
    other_owner: OwnerScope,
    make_relay: Callable[..., OutboxRelay],
) -> None:
    mine = _ingest_text(uow_factory, owner)
    theirs = _ingest_text(uow_factory, other_owner)
    failing = make_relay(RecordingPublisher(failures=2), max_attempts=1)
    assert failing.relay_due().failed == 1  # a publish failure ends the batch
    assert failing.relay_due().failed == 1
    with uow_factory() as uow:
        assert uow.outbox.for_subject(owner, theirs) == []  # never visible across owners
        assert uow.outbox.get(owner, _outbox(uow_factory, other_owner, theirs)[0].id) is None
        assert uow.outbox.retry_failed(owner, T0) == 1  # only this owner's message
    [other] = _outbox(uow_factory, other_owner, theirs)
    assert other.status is OutboxStatus.FAILED
    assert make_relay(RecordingPublisher()).relay_due().published == 1
    assert _source_status(uow_factory, owner, mine)[0] is SourceProcessingStatus.QUEUED
    assert _source_status(uow_factory, other_owner, theirs)[0] is SourceProcessingStatus.VALIDATED


def test_the_message_itself_is_immutable(uow_factory: Uow, owner: OwnerScope) -> None:
    source_id = _ingest_text(uow_factory, owner)
    [message] = _outbox(uow_factory, owner, source_id)
    with pytest.raises(DBAPIError, match="immutable"), uow_factory() as uow:
        uow.outbox._session.execute(  # test-only: bypass the repository
            text("UPDATE memory.me_outbox SET subject_id = gen_random_uuid() WHERE id = :id"),
            {"id": message.id},
        )
    with pytest.raises(DBAPIError, match="ck_me_outbox_published_at"), uow_factory() as uow:
        uow.outbox._session.execute(
            text("UPDATE memory.me_outbox SET status = 'published' WHERE id = :id"),
            {"id": message.id},
        )


# --- the relay process ----------------------------------------------------------------


def test_run_forever_relays_until_stopped(
    uow_factory: Uow, owner: OwnerScope, make_relay: Callable[..., OutboxRelay]
) -> None:
    source_id = _ingest_text(uow_factory, owner)
    stop = threading.Event()
    publisher = RecordingPublisher()
    publisher.on_publish = stop.set
    make_relay(publisher, poll_interval_seconds=0.01).run_forever(stop)
    assert _source_status(uow_factory, owner, source_id)[0] is SourceProcessingStatus.QUEUED


def test_run_forever_survives_a_database_outage(
    make_relay: Callable[..., OutboxRelay], monkeypatch: pytest.MonkeyPatch
) -> None:
    stop = threading.Event()
    relay = make_relay(RecordingPublisher(), poll_interval_seconds=0.01)
    calls: list[int] = []

    def flaky(limit: int | None = None) -> Any:
        calls.append(1)
        if len(calls) == 1:
            raise PersistenceError("synthetic outage")
        stop.set()
        return relay.__class__.relay_due(relay, limit)

    monkeypatch.setattr(relay, "relay_due", flaky)
    relay.run_forever(stop)
    assert len(calls) == 2


# --- two relays never publish the same row (committed data, separate connections) -------


@pytest.fixture
def committed_message(engine: Engine) -> Iterator[OutboxMessage]:
    owner = OwnerScope(uuid.uuid4())
    message = OutboxMessage.new(
        owner,
        kind=HandoffKind.PERSONAL_EXTRACTION,
        subject_id=uuid.uuid4(),
        payload={},
        payload_reference=None,
        priority="normal",
        created_at=T0,
    )
    factory = create_session_factory(engine)
    with factory() as session:
        SqlAlchemyOutboxRepository(session).add(owner, message)
        session.commit()
    try:
        yield message
    finally:
        with factory() as session:
            session.execute(delete(OutboxRow).where(OutboxRow.id == message.id))
            session.commit()


def test_concurrent_relays_skip_a_claimed_message(
    engine: Engine, committed_message: OutboxMessage
) -> None:
    factory = create_session_factory(engine)
    now = T0 + timedelta(minutes=1)
    with factory() as first, factory() as second:
        claimed = SqlAlchemyOutboxRepository(first).claim_next(now)
        assert claimed is not None and claimed.id == committed_message.id
        other = SqlAlchemyOutboxRepository(second).claim_next(now)
        assert other is None or other.id != committed_message.id
        first.rollback()
        second.rollback()


def test_rearm_needs_a_published_or_failed_handoff(uow_factory: Uow, owner: OwnerScope) -> None:
    source_id = _ingest_text(uow_factory, owner)
    with pytest.raises(ConcurrencyConflictError), uow_factory() as uow:  # still pending
        uow.outbox.rearm(owner, HandoffKind.PERSONAL_EXTRACTION, source_id, T0)
    with pytest.raises(RecordNotFoundError), uow_factory() as uow:
        uow.outbox.rearm(owner, HandoffKind.PERSONAL_EXTRACTION, uuid.uuid4(), T0)
