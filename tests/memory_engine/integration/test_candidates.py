"""Phase 8.4 step 5: the whole extraction pipeline on PostgreSQL, ending in candidates.

Ingestion, the relay, the gate, fact extraction, evaluation and candidate
generation run for real; the result is checked in the database: candidates
with categories and metadata, their evaluation history, the run summary and
the resolution handoff. Synthetic data only.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import Connection, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from memory_engine.config.settings import (
    EvaluationSettings,
    ExtractionSettings,
    FactExtractionSettings,
    OutboxSettings,
    RelevanceSettings,
)
from memory_engine.domain.handoff import (
    EXTRACTION_COMPONENT,
    HandoffEnvelope,
    HandoffKind,
    OutboxMessage,
    OutboxStatus,
)
from memory_engine.domain.identifiers import OwnerScope, new_id
from memory_engine.domain.vocabulary import (
    CandidateStatus,
    EvaluationOutcome,
    InstructionType,
    MemoryCategory,
    SourceProcessingStatus,
    SourceType,
)
from memory_engine.infrastructure.messaging import OutboxRelay
from memory_engine.infrastructure.nlp import SpacySentenceAnalyzer
from memory_engine.infrastructure.object_storage import InMemoryObjectStorage
from memory_engine.infrastructure.persistence import SqlAlchemyPersonalUnitOfWorkFactory
from memory_engine.infrastructure.persistence.outbox import OutboxRow
from memory_engine.observability.metrics import (
    EXTRACTION_CANDIDATES,
    EXTRACTION_DURATION,
    EXTRACTION_RUNS,
    NO_METRICS,
    InMemoryMetrics,
    Metrics,
)
from memory_engine.personal.application.candidates import CandidateGenerator
from memory_engine.personal.application.evaluation import EvaluationStage, ProposalEvaluator
from memory_engine.personal.application.extraction import ExtractionOutcome, ExtractionService
from memory_engine.personal.application.facts import FactExtractionStage, FactExtractor
from memory_engine.personal.application.ingestion import (
    IngestionLimits,
    IngestionRequest,
    PersonalIngestionService,
)
from memory_engine.personal.application.language import language_policy
from memory_engine.personal.application.relevance import (
    GatedPipeline,
    RelevanceGate,
    RelevancePolicy,
)
from memory_engine.personal.domain import CandidateEvaluation

pytestmark = pytest.mark.integration

Uow = SqlAlchemyPersonalUnitOfWorkFactory
T0 = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)
LIMITS = IngestionLimits(
    max_text_bytes=256 * 1024, max_conversation_messages=1000, max_conversation_bytes=4 * 1024**2
)
ANALYZER = SpacySentenceAnalyzer()


class _Publisher:
    def __init__(self) -> None:
        self.published: list[OutboxMessage] = []

    def publish(self, message: OutboxMessage) -> None:
        self.published.append(message)


def _relay(session_factory: sessionmaker[Session], publisher: _Publisher, minutes: int) -> None:
    OutboxRelay(
        session_factory,
        publisher,
        OutboxSettings(),
        clock=lambda: T0 + timedelta(minutes=minutes),
        jitter=lambda d: d,
    ).relay_due()


def _service(
    uow_factory: Uow, storage: InMemoryObjectStorage, metrics: Metrics = NO_METRICS
) -> ExtractionService:
    pipeline = GatedPipeline(
        RelevanceGate(ANALYZER, RelevancePolicy.from_settings(RelevanceSettings())),
        FactExtractionStage(
            FactExtractor(FactExtractionSettings()),
            EvaluationStage(
                ProposalEvaluator(EvaluationSettings()),
                CandidateGenerator(clock=lambda: T0 + timedelta(minutes=2)),
            ),
        ),
    )
    return ExtractionService(
        uow_factory,
        storage,
        pipeline,
        language_policy(ExtractionSettings()),
        clock=lambda: T0 + timedelta(minutes=2),
        metrics=metrics,
    )


def _extract(
    uow_factory: Uow,
    session_factory: sessionmaker[Session],
    owner: OwnerScope,
    text: str,
    instruction: InstructionType = InstructionType.REMEMBER,
    metrics: Metrics = NO_METRICS,
) -> tuple[uuid.UUID, OutboxMessage, ExtractionService, _Publisher]:
    storage = InMemoryObjectStorage()
    source_id = (
        PersonalIngestionService(uow_factory, storage, LIMITS, clock=lambda: T0)
        .ingest(
            owner,
            IngestionRequest(
                owner_id=owner.owner_id,
                idempotency_key=str(uuid.uuid4()),
                source_type=SourceType.TEXT,
                text=text,
                instruction_type=instruction,
            ),
        )
        .source_id
    )
    publisher = _Publisher()
    _relay(session_factory, publisher, 1)
    [message] = [m for m in publisher.published if m.subject_id == source_id]
    return source_id, message, _service(uow_factory, storage, metrics), publisher


def test_extraction_ends_in_validated_candidates_and_a_resolution_handoff(
    uow_factory: Uow, session_factory: sessionmaker[Session], owner: OwnerScope
) -> None:
    text = "I want to learn Rust. My friend said he is moving to Canada."
    source_id, message, service, publisher = _extract(uow_factory, session_factory, owner, text)
    report = service.handle(message.envelope.to_dict())
    assert (report.outcome, report.status, report.candidates, report.validated) == (
        ExtractionOutcome.COMPLETED,
        SourceProcessingStatus.EXTRACTED,
        2,
        1,
    )
    with uow_factory() as uow:
        candidates = {c.proposition: c for c in uow.candidates.list_for_source(owner, source_id)}
        goal = candidates["The user wants to learn Rust."]
        hearsay = candidates["According to the user's friend, he is moving to Canada."]
        goal_history = uow.evaluations.history(owner, goal.id)
        hearsay_history = uow.evaluations.history(owner, hearsay.id)
        events = uow.processing.events(owner, source_id)
    # Stored with categories and separate metadata (6.2.6 AC-02 to AC-09).
    assert goal.status is CandidateStatus.VALIDATED
    assert goal.categories == (MemoryCategory.GOAL, MemoryCategory.KNOWLEDGE)
    assert goal.evaluation_metadata["category_rule"] == "GOAL"
    assert goal.extraction_metadata["location"] == {"segment": 0, "sentence": 0}
    assert goal.temporal["reference_time"] is not None
    assert hearsay.status is CandidateStatus.NEEDS_REVIEW
    # Evaluation history: candidate -> validated / needs_review (5.4.25).
    [validated] = goal_history
    [review] = hearsay_history
    assert (validated.from_status, validated.to_status, validated.outcome) == (
        CandidateStatus.CANDIDATE,
        CandidateStatus.VALIDATED,
        EvaluationOutcome.PROCEED,
    )
    assert (review.to_status, review.reason_code) == (
        CandidateStatus.NEEDS_REVIEW,
        "UNRESOLVED_REFERENCE",  # fact extraction's review reason comes first
    )
    # The run's summary sits on the final transition; counts and codes only.
    final = events[-1]
    assert final.to_status is SourceProcessingStatus.EXTRACTED
    assert final.outcome_summary is not None
    assert {k: final.outcome_summary[k] for k in ("candidates", "validated", "needs_review")} == {
        "candidates": 2,
        "validated": 1,
        "needs_review": 1,
    }
    # One resolution handoff, published by the relay; the source does not move.
    _relay(session_factory, publisher, 3)
    [handoff] = [
        m
        for m in publisher.published
        if m.subject_id == source_id and m.kind is HandoffKind.PERSONAL_RESOLUTION
    ]
    envelope = HandoffEnvelope.from_dict(handoff.envelope.to_dict())
    assert envelope.source_component == EXTRACTION_COMPONENT
    assert envelope.destination_component == "memory_engine.resolution"
    assert envelope.correlation_id == message.envelope.correlation_id
    assert envelope.priority == "high"  # a remember instruction stays high priority
    assert dict(envelope.payload) == {"source_id": str(source_id), "validated_candidates": "1"}
    assert text not in repr(envelope.to_dict())
    with uow_factory() as uow:
        source = uow.sources.get(owner, source_id)
    assert source is not None and source.processing_status is SourceProcessingStatus.EXTRACTED


def test_a_second_delivery_adds_nothing(
    uow_factory: Uow, session_factory: sessionmaker[Session], owner: OwnerScope
) -> None:
    source_id, message, service, _ = _extract(
        uow_factory, session_factory, owner, "I decided to build a startup."
    )
    assert service.handle(message.envelope.to_dict()).validated == 1
    again = service.handle(message.envelope.to_dict())
    assert again.outcome is ExtractionOutcome.ALREADY_HANDLED
    with uow_factory() as uow:
        assert len(uow.candidates.list_for_source(owner, source_id)) == 1
    with session_factory() as session:
        kinds = session.scalars(
            select(OutboxRow.kind).where(
                OutboxRow.owner_id == owner.owner_id, OutboxRow.subject_id == source_id
            )
        ).all()
    assert sorted(kinds) == ["personal_extraction", "personal_resolution"]


def test_no_validated_candidate_means_no_resolution_handoff(
    uow_factory: Uow, session_factory: sessionmaker[Session], owner: OwnerScope
) -> None:
    source_id, message, service, _ = _extract(uow_factory, session_factory, owner, "I love it.")
    report = service.handle(message.envelope.to_dict())
    assert (report.status, report.candidates, report.validated) == (
        SourceProcessingStatus.EXTRACTED,
        1,
        0,
    )
    with session_factory() as session:
        kinds = session.scalars(
            select(OutboxRow.kind).where(
                OutboxRow.owner_id == owner.owner_id, OutboxRow.subject_id == source_id
            )
        ).all()
    assert kinds == ["personal_extraction"]


def test_a_resolution_handoff_whose_candidates_left_validated_is_abandoned(
    uow_factory: Uow, session_factory: sessionmaker[Session], owner: OwnerScope
) -> None:
    source_id, message, service, publisher = _extract(
        uow_factory, session_factory, owner, "I prefer dark mode."
    )
    service.handle(message.envelope.to_dict())
    with uow_factory() as uow:
        [candidate] = uow.candidates.list_for_source(owner, source_id)
        uow.evaluations.record(
            owner,
            CandidateEvaluation(
                id=new_id(),
                owner_id=owner.owner_id,
                candidate_id=candidate.id,
                outcome=EvaluationOutcome.NEEDS_REVIEW,
                from_status=CandidateStatus.VALIDATED,
                to_status=CandidateStatus.NEEDS_REVIEW,
                method="synthetic",
                method_version="1",
                evaluated_at=T0 + timedelta(minutes=3),
                reason_code="SYNTHETIC",
            ),
        )
    _relay(session_factory, publisher, 4)
    assert not [m for m in publisher.published if m.kind is HandoffKind.PERSONAL_RESOLUTION]
    with session_factory() as session:
        status = session.scalar(
            select(OutboxRow.status).where(
                OutboxRow.owner_id == owner.owner_id,
                OutboxRow.subject_id == source_id,
                OutboxRow.kind == HandoffKind.PERSONAL_RESOLUTION.value,
            )
        )
    assert status == OutboxStatus.FAILED.value


def test_a_source_of_another_owner_is_never_seen(
    uow_factory: Uow, session_factory: sessionmaker[Session], owner: OwnerScope
) -> None:
    source_id, message, service, _ = _extract(
        uow_factory, session_factory, owner, "I am building Raven."
    )
    service.handle(message.envelope.to_dict())
    stranger = OwnerScope(uuid.uuid4())
    with uow_factory() as uow:
        assert uow.candidates.list_for_source(stranger, source_id) == []
        [candidate] = uow.candidates.list_for_source(owner, source_id)
        assert candidate.categories == (MemoryCategory.PROJECT,)
        assert uow.evaluations.history(stranger, candidate.id) == []


def test_categories_and_metadata_are_insert_only_and_checked(
    connection: Connection,
    uow_factory: Uow,
    session_factory: sessionmaker[Session],
    owner: OwnerScope,
) -> None:
    source_id, message, service, _ = _extract(
        uow_factory, session_factory, owner, "I prefer dark mode."
    )
    service.handle(message.envelope.to_dict())
    with uow_factory() as uow:
        [candidate] = uow.candidates.list_for_source(owner, source_id)
    for column, value in (("categories", "'{goal}'"), ("evaluation_metadata", "'{}'")):
        savepoint = connection.begin_nested()
        with pytest.raises(DBAPIError, match="immutable columns"):
            connection.execute(
                text(f"UPDATE memory.pm_memory_candidate SET {column} = {value} WHERE id = :id"),  # noqa: S608
                {"id": candidate.id},
            )
        savepoint.rollback()
    savepoint = connection.begin_nested()
    with pytest.raises(IntegrityError, match="ck_pm_memory_candidate_categories"):
        connection.execute(
            text(
                "INSERT INTO memory.pm_memory_candidate SELECT (json_populate_record(c,"
                " json_build_object('id', gen_random_uuid(), 'categories', ARRAY['bogus']))).*"
                " FROM memory.pm_memory_candidate c WHERE c.id = :id"
            ),
            {"id": candidate.id},
        )
    savepoint.rollback()


# --- observability (8.4 step 6) ------------------------------------------------------


class _BrokenMetrics(InMemoryMetrics):
    def increment(self, name: str, labels: Any = None, amount: int = 1) -> None:
        raise RuntimeError("synthetic: metrics backend down")


def _extraction_events(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if getattr(r, "event_type", "").startswith("extraction.")]


def test_a_run_records_bounded_metrics_and_one_event(
    uow_factory: Uow,
    session_factory: sessionmaker[Session],
    owner: OwnerScope,
    caplog: pytest.LogCaptureFixture,
) -> None:
    metrics = InMemoryMetrics()
    text = "I want to learn Rust. My friend said he is moving to Canada."
    source_id, message, service, _ = _extract(
        uow_factory, session_factory, owner, text, metrics=metrics
    )
    caplog.set_level(logging.INFO, logger="raven.memory_engine")
    service.handle(message.envelope.to_dict())
    service.handle(message.envelope.to_dict())  # a duplicate delivery
    assert metrics.count(EXTRACTION_RUNS, input="text", outcome="extracted") == 1
    assert metrics.count(EXTRACTION_RUNS, input="text", outcome="already_handled") == 1
    assert len(metrics.observations(EXTRACTION_DURATION, input="text", outcome="extracted")) == 1
    assert metrics.count(EXTRACTION_CANDIDATES, kind="validated") == 1
    assert metrics.count(EXTRACTION_CANDIDATES, kind="needs_review") == 1
    labels = {value for values in metrics.label_values().values() for value in values}
    assert str(owner.owner_id) not in labels and str(source_id) not in labels
    [done, duplicate] = _extraction_events(caplog)
    assert done.event_type == "extraction.extracted"  # type: ignore[attr-defined]
    assert done.outcome_summary["validated"] == 1  # type: ignore[attr-defined]
    assert done.user_scope == str(owner.owner_id)  # type: ignore[attr-defined]
    assert done.duration_ms >= 0  # type: ignore[attr-defined]
    assert duplicate.event_type == "extraction.already_handled"  # type: ignore[attr-defined]
    logged = " ".join(repr(r.__dict__) for r in caplog.records)
    assert "Rust" not in logged and "Canada" not in logged  # never content


def test_an_invalid_message_is_counted_without_an_input(
    uow_factory: Uow, session_factory: sessionmaker[Session], owner: OwnerScope
) -> None:
    metrics = InMemoryMetrics()
    _, _, service, _ = _extract(
        uow_factory, session_factory, owner, "I prefer tea.", metrics=metrics
    )
    service.handle({"schema_version": "0"})
    assert metrics.count(EXTRACTION_RUNS, outcome="invalid_message") == 1


def test_telemetry_failure_never_changes_the_outcome(
    uow_factory: Uow,
    session_factory: sessionmaker[Session],
    owner: OwnerScope,
    caplog: pytest.LogCaptureFixture,
) -> None:
    source_id, message, service, _ = _extract(
        uow_factory, session_factory, owner, "I prefer dark mode.", metrics=_BrokenMetrics()
    )
    caplog.set_level(logging.INFO, logger="raven.memory_engine")
    report = service.handle(message.envelope.to_dict())
    assert (report.outcome, report.validated) == (ExtractionOutcome.COMPLETED, 1)
    with uow_factory() as uow:
        assert len(uow.candidates.list_for_source(owner, source_id)) == 1
    assert any(getattr(r, "event_type", None) == "observability.failure" for r in caplog.records)
