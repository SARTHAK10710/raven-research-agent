"""Phase 8.4 step 2: the relevance gate inside the extraction worker, on PostgreSQL.

Real spaCy analyzer, real database; fact extraction (step 3) is a stand-in.
Synthetic data only.
"""

import json
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from memory_engine.config.settings import ExtractionSettings, OutboxSettings, RelevanceSettings
from memory_engine.domain.errors import OwnershipError
from memory_engine.domain.handoff import OutboxMessage
from memory_engine.domain.identifiers import OwnerScope, new_id
from memory_engine.domain.vocabulary import (
    CandidateOrigin,
    CandidateStatus,
    RelevanceOutcome,
    SourceProcessingStatus,
    SourceType,
)
from memory_engine.infrastructure.messaging import OutboxRelay
from memory_engine.infrastructure.nlp import SpacySentenceAnalyzer
from memory_engine.infrastructure.object_storage import InMemoryObjectStorage
from memory_engine.infrastructure.persistence import SqlAlchemyPersonalUnitOfWorkFactory
from memory_engine.personal.application.extraction import (
    ExtractionService,
    PipelineResult,
    SourceContent,
)
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
    SelectedSentence,
)
from memory_engine.personal.domain import MemoryCandidate

pytestmark = pytest.mark.integration

Uow = SqlAlchemyPersonalUnitOfWorkFactory
T0 = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
LIMITS = IngestionLimits(
    max_text_bytes=256 * 1024, max_conversation_messages=1000, max_conversation_bytes=4 * 1024**2
)
PRIVATE = "I prefer window seats when I fly to conferences."


class OneCandidatePerSentence:
    """Stands in for fact extraction (step 3): one candidate per selected sentence."""

    def __init__(self) -> None:
        self.selected: list[SelectedSentence] = []

    def extract(
        self, content: SourceContent, selected: Sequence[SelectedSentence]
    ) -> PipelineResult:
        self.selected = list(selected)
        source = content.source
        return PipelineResult(
            status=SourceProcessingStatus.EXTRACTED,
            candidates=[
                MemoryCandidate(
                    id=new_id(),
                    owner_id=source.owner_id,
                    source_id=source.id,
                    proposition="Synthetic proposition.",
                    status=CandidateStatus.CANDIDATE,
                    origin=CandidateOrigin.EXPLICIT,
                )
                for _ in selected
            ],
        )


class _Publisher:
    def __init__(self) -> None:
        self.published: list[OutboxMessage] = []

    def publish(self, message: OutboxMessage) -> None:
        self.published.append(message)


def _queued(uow: Uow, session_factory: sessionmaker[Session], owner: OwnerScope, text: str) -> Any:
    storage = InMemoryObjectStorage()
    service = PersonalIngestionService(uow, storage, LIMITS, clock=lambda: T0)
    source_id = service.ingest(
        owner,
        IngestionRequest(
            owner_id=owner.owner_id,
            idempotency_key=str(uuid.uuid4()),
            source_type=SourceType.TEXT,
            text=text,
        ),
    ).source_id
    publisher = _Publisher()
    OutboxRelay(
        session_factory,
        publisher,
        OutboxSettings(),
        clock=lambda: T0 + timedelta(minutes=1),
        jitter=lambda d: d,
    ).relay_due()
    [message] = [m for m in publisher.published if m.subject_id == source_id]
    return storage, source_id, message.envelope.to_dict()


def _worker(uow: Uow, storage: Any, downstream: Any) -> ExtractionService:
    gate = RelevanceGate(
        SpacySentenceAnalyzer(),
        RelevancePolicy.from_settings(RelevanceSettings()),
        clock=lambda: T0 + timedelta(minutes=2),
    )
    return ExtractionService(
        uow,
        storage,
        GatedPipeline(gate, downstream),
        language_policy(ExtractionSettings()),
        clock=lambda: T0 + timedelta(minutes=2),
    )


def test_a_relevant_source_is_extracted_with_its_decision_recorded(
    uow_factory: Uow, session_factory: sessionmaker[Session], owner: OwnerScope
) -> None:
    storage, source_id, envelope = _queued(
        uow_factory, session_factory, owner, f"Thanks! {PRIVATE} Should I book now?"
    )
    downstream = OneCandidatePerSentence()
    report = _worker(uow_factory, storage, downstream).handle(envelope)
    assert (report.status, report.candidates) == (SourceProcessingStatus.EXTRACTED, 1)
    assert [s.sentence.text for s in downstream.selected] == [PRIVATE]
    with uow_factory() as uow:
        [assessment] = uow.relevance.for_source(owner, source_id)
    assert assessment.outcome is RelevanceOutcome.PROCESS
    assert [(u.outcome.value, u.reason_code) for u in assessment.units] == [
        ("reject", "SMALL_TALK"),
        ("process", None),
        ("reject", "QUESTION_ONLY"),
    ]
    assert assessment.method_version.startswith("1+spacy-")


@pytest.mark.parametrize(
    ("text", "status", "reason"),
    [
        ("Thanks! Good morning!", SourceProcessingStatus.REJECTED, "SMALL_TALK"),
        ("Tom likes jazz.", SourceProcessingStatus.DEFERRED, "AMBIGUOUS_RELEVANCE"),
    ],
)
def test_a_gated_source_stops_with_the_gate_reason(
    uow_factory: Uow,
    session_factory: sessionmaker[Session],
    owner: OwnerScope,
    text: str,
    status: SourceProcessingStatus,
    reason: str,
) -> None:
    storage, source_id, envelope = _queued(uow_factory, session_factory, owner, text)
    downstream = OneCandidatePerSentence()
    report = _worker(uow_factory, storage, downstream).handle(envelope)
    assert (report.status, report.reason_code) == (status, reason)
    assert downstream.selected == []  # never reaches fact extraction
    with uow_factory() as uow:
        events = uow.processing.events(owner, source_id)
        [assessment] = uow.relevance.for_source(owner, source_id)
        candidates = uow.candidates.list_for_source(owner, source_id)
    assert events[-1].reason_code == reason and candidates == []
    assert assessment.reason_code == reason


def test_the_stored_decision_never_contains_the_text(
    uow_factory: Uow, session_factory: sessionmaker[Session], owner: OwnerScope
) -> None:
    storage, source_id, envelope = _queued(uow_factory, session_factory, owner, PRIVATE)
    _worker(uow_factory, storage, OneCandidatePerSentence()).handle(envelope)
    with uow_factory() as uow:
        raw = uow.relevance._session.execute(  # test-only: read the stored JSON
            text("SELECT units FROM memory.pm_relevance_assessment WHERE source_id = :s"),
            {"s": source_id},
        ).scalar_one()
    stored = json.dumps(raw)
    assert "window" not in stored and "conferences" not in stored


def test_a_decision_is_owner_scoped(
    uow_factory: Uow,
    session_factory: sessionmaker[Session],
    owner: OwnerScope,
    other_owner: OwnerScope,
) -> None:
    storage, source_id, envelope = _queued(uow_factory, session_factory, owner, PRIVATE)
    _worker(uow_factory, storage, OneCandidatePerSentence()).handle(envelope)
    with uow_factory() as uow:
        assert uow.relevance.for_source(other_owner, source_id) == []
        [mine] = uow.relevance.for_source(owner, source_id)
    with pytest.raises(OwnershipError), uow_factory() as uow:
        uow.relevance.add(other_owner, mine)


def test_the_database_enforces_the_decision_rules(
    uow_factory: Uow, session_factory: sessionmaker[Session], owner: OwnerScope
) -> None:
    storage, source_id, envelope = _queued(uow_factory, session_factory, owner, PRIVATE)
    _worker(uow_factory, storage, OneCandidatePerSentence()).handle(envelope)
    insert = text(
        "INSERT INTO memory.pm_relevance_assessment (id, owner_id, source_id, outcome, "
        "reason_code, method, method_version, units, assessed_at) VALUES (gen_random_uuid(), "
        ":o, :s, :outcome, :reason, 'relevance_gate', '1', CAST(:units AS jsonb), now())"
    )
    for outcome, reason, units, constraint in (
        ("reject", None, "[]", "reason_required"),
        ("process", "WHY", "[]", "reason_required"),
        ("process", None, "{}", "units_array"),
        ("ignore", "WHY", "[]", "outcome"),
    ):
        values = {"o": owner.owner_id, "s": source_id, "outcome": outcome, "reason": reason}
        with (
            pytest.raises(DBAPIError, match=f"ck_pm_relevance_assessment_{constraint}"),
            uow_factory() as uow,
        ):
            uow.relevance._session.execute(insert, values | {"units": units})
    with pytest.raises(DBAPIError, match="immutable"), uow_factory() as uow:
        uow.relevance._session.execute(
            text(
                "UPDATE memory.pm_relevance_assessment SET outcome = 'reject' WHERE source_id = :s"
            ),
            {"s": source_id},
        )
