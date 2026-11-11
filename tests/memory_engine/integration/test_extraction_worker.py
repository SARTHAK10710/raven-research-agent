"""Phase 8.4 step 1: the extraction worker against real PostgreSQL.

The pipeline (steps 2-5) is a stand-in here; object storage is the in-memory
fake; the broker is replaced by a recording publisher (``test_broker_handoff``
covers RabbitMQ). Synthetic data only.
"""

import hashlib
import io
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from memory_engine.config.settings import BrokerSettings, ExtractionSettings, OutboxSettings
from memory_engine.domain.handoff import HandoffKind, OutboxMessage, OutboxStatus
from memory_engine.domain.identifiers import OwnerScope, new_id
from memory_engine.domain.vocabulary import (
    CandidateOrigin,
    CandidateStatus,
    InstructionType,
    ProcessingEventType,
    SourceProcessingStatus,
    SourceType,
)
from memory_engine.exceptions import (
    ConcurrencyConflictError,
    ObjectStorageError,
    PersistenceError,
    RecordNotFoundError,
)
from memory_engine.infrastructure.messaging import (
    OutboxRelay,
    create_celery_app,
    register_extraction_task,
)
from memory_engine.infrastructure.object_storage import InMemoryObjectStorage
from memory_engine.infrastructure.persistence import SqlAlchemyPersonalUnitOfWorkFactory
from memory_engine.personal.application.extraction import (
    EXTRACTION_FAILED,
    MALFORMED_CONTENT,
    ExtractionOutcome,
    ExtractionService,
    PipelineResult,
    SourceContent,
)
from memory_engine.personal.application.ingestion import (
    ConversationMessage,
    IngestionLimits,
    IngestionRequest,
    PersonalIngestionService,
    source_keys,
)
from memory_engine.personal.application.language import UNSUPPORTED_LANGUAGE, language_policy
from memory_engine.personal.domain import MemoryCandidate, SourceProcessingEvent

pytestmark = pytest.mark.integration

Uow = SqlAlchemyPersonalUnitOfWorkFactory
T0 = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
LIMITS = IngestionLimits(
    max_text_bytes=256 * 1024, max_conversation_messages=1000, max_conversation_bytes=4 * 1024**2
)
ENGLISH = "I prefer window seats when I fly to conferences abroad."
SPANISH = "Me gusta mucho viajar en tren porque puedo leer y descansar durante el viaje."
POLICY = language_policy(ExtractionSettings())


class StubPipeline:
    """Stands in for steps 2-5: one candidate per source, or a chosen result."""

    def __init__(self, result: Callable[[SourceContent], PipelineResult] | None = None) -> None:
        self.calls: list[SourceContent] = []
        self._result = result

    def run(self, content: SourceContent) -> PipelineResult:
        self.calls.append(content)
        if self._result is not None:
            return self._result(content)
        source = content.source
        return PipelineResult(
            status=SourceProcessingStatus.EXTRACTED,
            candidates=[
                MemoryCandidate(
                    id=new_id(),
                    owner_id=source.owner_id,
                    source_id=source.id,
                    proposition="Synthetic user prefers window seats.",
                    status=CandidateStatus.CANDIDATE,
                    origin=CandidateOrigin.EXPLICIT,
                )
            ],
        )


class Publisher:
    def __init__(self) -> None:
        self.published: list[OutboxMessage] = []

    def publish(self, message: OutboxMessage) -> None:
        self.published.append(message)


class Harness:
    """Ingest, hand off and extract within the rolled-back test transaction."""

    def __init__(self, uow: Uow, session_factory: sessionmaker[Session]) -> None:
        self.uow = uow
        self.storage = InMemoryObjectStorage()
        self.publisher = Publisher()
        self.now = T0 + timedelta(minutes=1)  # relay clock
        self.relay = OutboxRelay(
            session_factory,
            self.publisher,
            OutboxSettings(),
            clock=lambda: self.now,
            jitter=lambda d: d,
        )

    def ingest(self, owner: OwnerScope, key: str = "k-1", **request: Any) -> uuid.UUID:
        values: dict[str, Any] = {
            "owner_id": owner.owner_id,
            "idempotency_key": key,
            "source_type": SourceType.TEXT,
            "text": ENGLISH,
        }
        service = PersonalIngestionService(self.uow, self.storage, LIMITS, clock=lambda: T0)
        return service.ingest(owner, IngestionRequest(**values | request)).source_id

    def handoff(self, owner: OwnerScope, key: str = "k-1", **request: Any) -> dict[str, Any]:
        source_id = self.ingest(owner, key, **request)
        self.relay.relay_due()
        message = next(m for m in self.publisher.published if m.subject_id == source_id)
        return message.envelope.to_dict()

    def service(self, pipeline: Any = None, storage: Any = None) -> ExtractionService:
        return ExtractionService(
            self.uow,
            storage or self.storage,
            pipeline or StubPipeline(),
            POLICY,
            clock=lambda: T0 + timedelta(minutes=2),
        )

    def state(self, owner: OwnerScope, source_id: uuid.UUID) -> Any:
        with self.uow() as uow:
            source = uow.sources.get(owner, source_id)
            events = uow.processing.events(owner, source_id)
            candidates = uow.candidates.list_for_source(owner, source_id)
        assert source is not None
        return source.processing_status, events, candidates


@pytest.fixture
def h(uow_factory: Uow, session_factory: sessionmaker[Session]) -> Harness:
    return Harness(uow_factory, session_factory)


def _source_id(envelope: dict[str, Any]) -> uuid.UUID:
    return uuid.UUID(envelope["task_id"])


# --- outcomes ------------------------------------------------------------------------


def test_a_queued_source_is_extracted_atomically(h: Harness, owner: OwnerScope) -> None:
    envelope = h.handoff(owner)
    pipeline = StubPipeline()
    report = h.service(pipeline).handle(envelope)
    assert report.outcome is ExtractionOutcome.COMPLETED
    assert (report.status, report.candidates) == (SourceProcessingStatus.EXTRACTED, 1)
    status, events, candidates = h.state(owner, _source_id(envelope))
    assert status is SourceProcessingStatus.EXTRACTED
    assert [(e.from_status, e.to_status) for e in events[-2:]] == [
        (SourceProcessingStatus.QUEUED, SourceProcessingStatus.PROCESSING),
        (SourceProcessingStatus.PROCESSING, SourceProcessingStatus.EXTRACTED),
    ]
    assert len(candidates) == 1 and candidates[0].status is CandidateStatus.CANDIDATE
    [content] = pipeline.calls
    assert [s.text for s in content.segments] == [ENGLISH]  # normalized content, not raw


def test_a_conversation_reaches_the_pipeline_as_ordered_segments(
    h: Harness, owner: OwnerScope
) -> None:
    envelope = h.handoff(
        owner,
        source_type=SourceType.CONVERSATION,
        text=None,
        messages=[
            ConversationMessage(speaker="Sam", from_user=True, text="I moved to Leeds last month."),
            ConversationMessage(speaker="Raven", from_user=False, text="How do you like it?"),
        ],
    )
    pipeline = StubPipeline()
    h.service(pipeline).handle(envelope)
    [content] = pipeline.calls
    assert [(s.position, s.from_user, s.speaker) for s in content.segments] == [
        (0, True, "Sam"),
        (1, False, "Raven"),
    ]


def test_a_second_delivery_does_nothing(h: Harness, owner: OwnerScope) -> None:
    envelope = h.handoff(owner)
    pipeline = StubPipeline()
    service = h.service(pipeline)
    service.handle(envelope)
    again = service.handle(envelope)
    assert again.outcome is ExtractionOutcome.ALREADY_HANDLED
    assert again.status is SourceProcessingStatus.EXTRACTED
    _, events, candidates = h.state(owner, _source_id(envelope))
    assert len(candidates) == 1 and len(pipeline.calls) == 1
    assert len(events) == 3  # validated->queued, queued->processing, processing->extracted


def test_a_non_english_source_is_deferred_with_a_reason(h: Harness, owner: OwnerScope) -> None:
    envelope = h.handoff(owner, text=SPANISH)
    pipeline = StubPipeline()
    report = h.service(pipeline).handle(envelope)
    assert (report.status, report.reason_code) == (
        SourceProcessingStatus.DEFERRED,
        UNSUPPORTED_LANGUAGE,
    )
    assert pipeline.calls == []  # never run through English rules
    status, events, candidates = h.state(owner, _source_id(envelope))
    assert status is SourceProcessingStatus.DEFERRED and candidates == []
    assert events[-1].reason_code == UNSUPPORTED_LANGUAGE and events[-1].error_code is None


def test_a_rejected_source_records_its_reason(h: Harness, owner: OwnerScope) -> None:
    envelope = h.handoff(owner)
    pipeline = StubPipeline(
        lambda _: PipelineResult(
            status=SourceProcessingStatus.REJECTED, reason_code="NOT_PERSONALLY_RELEVANT"
        )
    )
    h.service(pipeline).handle(envelope)
    status, events, _ = h.state(owner, _source_id(envelope))
    assert status is SourceProcessingStatus.REJECTED
    assert events[-1].reason_code == "NOT_PERSONALLY_RELEVANT"


# --- refusals ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tamper",
    [
        lambda e: e.update(schema_version="2"),
        lambda e: e.update(operation="document_extraction"),
        lambda e: e.update(task_id="not-a-uuid"),
        lambda e: e.clear(),
        lambda e: e.update(
            operation="document_extraction",
            destination_component="memory_engine.document_pipeline",
        ),
    ],
    ids=["version", "operation", "task_id", "empty", "document_kind"],
)
def test_an_invalid_message_is_refused_without_side_effects(
    h: Harness, owner: OwnerScope, tamper: Callable[[dict[str, Any]], None]
) -> None:
    envelope = h.handoff(owner)
    source_id = _source_id(envelope)
    tamper(envelope)
    pipeline = StubPipeline()
    report = h.service(pipeline).handle(envelope)
    assert report.outcome is ExtractionOutcome.INVALID_MESSAGE and pipeline.calls == []
    assert h.state(owner, source_id)[0] is SourceProcessingStatus.QUEUED


def test_a_message_naming_another_owner_finds_nothing(
    h: Harness, owner: OwnerScope, other_owner: OwnerScope
) -> None:
    envelope = h.handoff(owner)
    envelope["user_id"] = str(other_owner.owner_id)  # someone else's scope, my source
    report = h.service().handle(envelope)
    assert report.outcome is ExtractionOutcome.SOURCE_MISSING
    assert h.state(owner, _source_id(envelope))[0] is SourceProcessingStatus.QUEUED


def test_a_forget_source_is_never_extracted(h: Harness, owner: OwnerScope) -> None:
    source_id = h.ingest(owner, instruction_type=InstructionType.FORGET)
    assert h.publisher.published == []  # no handoff exists (8.3 step 4)
    with h.uow() as uow:  # simulate a stray message for it
        uow.processing.transition(
            owner,
            SourceProcessingEvent(
                id=new_id(),
                owner_id=owner.owner_id,
                source_id=source_id,
                event_type=ProcessingEventType.TRANSITION,
                from_status=SourceProcessingStatus.VALIDATED,
                to_status=SourceProcessingStatus.QUEUED,
                attempt=1,
                occurred_at=T0,
            ),
        )
    stray = _personal_message(owner, source_id)
    pipeline = StubPipeline()
    report = h.service(pipeline).handle(stray.envelope.to_dict())
    assert report.outcome is ExtractionOutcome.FORGET_REFUSED and pipeline.calls == []
    assert h.state(owner, source_id)[0] is SourceProcessingStatus.QUEUED  # left for 8.10


def _personal_message(owner: OwnerScope, source_id: uuid.UUID) -> OutboxMessage:
    return OutboxMessage.new(
        owner,
        kind=HandoffKind.PERSONAL_EXTRACTION,
        subject_id=source_id,
        payload={},
        payload_reference=None,
        priority="high",
        created_at=T0,
    )


# --- failures and recovery -------------------------------------------------------------


class _BrokenError(Exception):
    pass


def test_a_pipeline_failure_ends_processing_failed(h: Harness, owner: OwnerScope) -> None:
    envelope = h.handoff(owner)

    def boom(_: SourceContent) -> PipelineResult:
        raise _BrokenError("synthetic NLP failure")

    report = h.service(StubPipeline(boom)).handle(envelope)
    assert (report.status, report.error_code) == (
        SourceProcessingStatus.PROCESSING_FAILED,
        EXTRACTION_FAILED,
    )
    status, events, candidates = h.state(owner, _source_id(envelope))
    assert status is SourceProcessingStatus.PROCESSING_FAILED and candidates == []
    assert events[-1].event_type is ProcessingEventType.FAILURE


def test_a_memory_engine_error_keeps_its_code(h: Harness, owner: OwnerScope) -> None:
    envelope = h.handoff(owner)

    def missing(_: SourceContent) -> PipelineResult:
        raise RecordNotFoundError("synthetic")

    report = h.service(StubPipeline(missing)).handle(envelope)
    assert report.error_code == "RECORD_NOT_FOUND"


def test_unreadable_normalized_content_ends_parsing_failed(h: Harness, owner: OwnerScope) -> None:
    envelope = h.handoff(owner)
    source_id = _source_id(envelope)
    _, normalized = source_keys(owner.owner_id, source_id)
    junk = b"not json"
    h.storage.delete(owner, normalized)
    h.storage.put(
        owner,
        normalized,
        io.BytesIO(junk),
        content_type="application/json",
        size_bytes=len(junk),
        sha256=hashlib.sha256(junk).hexdigest(),
    )
    report = h.service().handle(envelope)
    assert (report.status, report.error_code) == (
        SourceProcessingStatus.PARSING_FAILED,
        MALFORMED_CONTENT,
    )


def test_a_candidate_for_another_source_is_refused(h: Harness, owner: OwnerScope) -> None:
    envelope = h.handoff(owner)

    def wrong(content: SourceContent) -> PipelineResult:
        result = StubPipeline().run(content)
        bad = result.candidates[0].__class__(
            id=new_id(),
            owner_id=owner.owner_id,
            source_id=uuid.uuid4(),
            proposition="x",
            status=CandidateStatus.CANDIDATE,
            origin=CandidateOrigin.EXPLICIT,
        )
        return PipelineResult(status=SourceProcessingStatus.EXTRACTED, candidates=[bad])

    report = h.service(StubPipeline(wrong)).handle(envelope)
    assert report.error_code == "INVALID_CANDIDATE"
    assert h.state(owner, _source_id(envelope))[2] == []


def test_a_storage_outage_is_retried_then_failed_then_reprocessed(
    h: Harness, owner: OwnerScope
) -> None:
    envelope = h.handoff(owner)
    source_id = _source_id(envelope)
    down = InMemoryObjectStorage()
    down.available = False
    with pytest.raises(ObjectStorageError):  # transient: the task retries this
        h.service(storage=down).handle(envelope)
    assert h.state(owner, source_id)[0] is SourceProcessingStatus.QUEUED

    failed = h.service().mark_failed(envelope, "OBJECT_STORAGE_ERROR", attempt=6)
    assert failed.status is SourceProcessingStatus.PROCESSING_FAILED
    status, events, _ = h.state(owner, source_id)
    assert status is SourceProcessingStatus.PROCESSING_FAILED
    assert (events[-1].error_code, events[-1].attempt) == ("OBJECT_STORAGE_ERROR", 6)
    late = h.service().mark_failed(envelope, "OBJECT_STORAGE_ERROR", attempt=7)
    assert late.outcome is ExtractionOutcome.ALREADY_HANDLED

    h.service().reprocess_failed(owner, source_id)  # the explicit retry
    assert h.state(owner, source_id)[0] is SourceProcessingStatus.VALIDATED
    with h.uow() as uow:
        [message] = uow.outbox.for_subject(owner, source_id)
    assert message.status is OutboxStatus.PENDING and message.published_at is None
    h.now = T0 + timedelta(minutes=5)  # after the re-arm
    h.relay.relay_due()  # the same handoff goes out again and re-queues the source
    assert h.state(owner, source_id)[0] is SourceProcessingStatus.QUEUED
    assert h.service().handle(envelope).status is SourceProcessingStatus.EXTRACTED
    retry = [e for e in h.state(owner, source_id)[1] if e.event_type is ProcessingEventType.RETRY]
    assert len(retry) == 1 and retry[0].attempt == 2


def test_only_a_failed_source_can_be_reprocessed(h: Harness, owner: OwnerScope) -> None:
    envelope = h.handoff(owner)
    with pytest.raises(ConcurrencyConflictError):
        h.service().reprocess_failed(owner, _source_id(envelope))


# --- database rules ----------------------------------------------------------------------


def test_the_database_requires_a_reason_exactly_for_deferral_and_rejection(
    h: Harness, owner: OwnerScope
) -> None:
    source_id = h.ingest(owner)
    insert = text(
        "INSERT INTO memory.pm_source_processing_event "
        "(id, owner_id, source_id, event_type, from_status, to_status, attempt, "
        "reason_code, occurred_at) VALUES (gen_random_uuid(), :owner, :source, "
        "'transition', 'validated', :to, 1, :reason, now())"
    )
    for to_status, reason in (("deferred", None), ("queued", "WHY")):
        values = {"owner": owner.owner_id, "source": source_id, "to": to_status, "reason": reason}
        with (
            pytest.raises(DBAPIError, match="ck_pm_source_processing_event_reason_required"),
            h.uow() as uow,
        ):
            uow.processing._session.execute(insert, values)  # test-only: bypass the repository


# --- the Celery task ----------------------------------------------------------------------


def _app() -> Any:
    return create_celery_app(
        BrokerSettings(
            host="broker.test.invalid",
            virtual_host="raven_test",
            user="u",
            password=SecretStr("synthetic-broker-password"),
        )
    )


def test_the_task_runs_the_service(h: Harness, owner: OwnerScope) -> None:
    envelope = h.handoff(owner)
    task = register_extraction_task(_app(), lambda: h.service(), ExtractionSettings())
    result = task.apply(args=[envelope]).get()
    assert result["outcome"] == "completed" and result["status"] == "extracted"


def test_the_task_retries_transient_errors_then_marks_the_source_failed(
    h: Harness, owner: OwnerScope
) -> None:
    envelope = h.handoff(owner)
    down = InMemoryObjectStorage()
    down.available = False
    calls: list[int] = []

    def service() -> ExtractionService:
        calls.append(1)
        return h.service(storage=down)

    task = register_extraction_task(_app(), service, ExtractionSettings(max_retries=2))
    result = task.apply(args=[envelope]).get()
    assert len(calls) == 3  # the first attempt and two retries
    assert (result["status"], result["error_code"]) == ("processing_failed", "OBJECT_STORAGE_ERROR")
    _, events, _ = h.state(owner, _source_id(envelope))
    assert events[-1].attempt == 3


def test_a_transient_error_inside_the_pipeline_is_retried(h: Harness, owner: OwnerScope) -> None:
    envelope = h.handoff(owner)

    def database_down(_: SourceContent) -> PipelineResult:
        raise PersistenceError("synthetic outage")

    with pytest.raises(PersistenceError):
        h.service(StubPipeline(database_down)).handle(envelope)
    assert h.state(owner, _source_id(envelope))[0] is SourceProcessingStatus.QUEUED


def test_a_concurrent_delivery_that_finishes_first_wins(h: Harness, owner: OwnerScope) -> None:
    envelope = h.handoff(owner)
    winner = StubPipeline()

    def race(content: SourceContent) -> PipelineResult:
        # Another worker completes the same source while this one is still running.
        h.service(winner).handle(envelope)
        return StubPipeline().run(content)

    report = h.service(StubPipeline(race)).handle(envelope)
    assert report.outcome is ExtractionOutcome.ALREADY_HANDLED
    status, _, candidates = h.state(owner, _source_id(envelope))
    assert status is SourceProcessingStatus.EXTRACTED and len(candidates) == 1  # winner's only


def test_marking_an_invalid_message_failed_does_nothing(h: Harness, owner: OwnerScope) -> None:
    report = h.service().mark_failed({"schema_version": "9"}, "PERSISTENCE_ERROR", attempt=1)
    assert report.outcome is ExtractionOutcome.INVALID_MESSAGE
