"""Phase 8.4 step 3: gate and fact extraction inside the worker, on PostgreSQL.

Evaluation and candidate generation (steps 4-5) are a stand-in that turns each
extracted proposal into a candidate, so the assembled pipeline runs end to end.
Synthetic data only.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.orm import Session, sessionmaker

from memory_engine.config.settings import (
    ExtractionSettings,
    FactExtractionSettings,
    OutboxSettings,
    RelevanceSettings,
)
from memory_engine.domain.handoff import OutboxMessage
from memory_engine.domain.identifiers import OwnerScope, new_id
from memory_engine.domain.vocabulary import (
    CandidateOrigin,
    CandidateStatus,
    ProposalStatus,
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
from memory_engine.personal.application.facts import (
    FactExtraction,
    FactExtractionStage,
    FactExtractor,
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
)
from memory_engine.personal.domain import MemoryCandidate

pytestmark = pytest.mark.integration

Uow = SqlAlchemyPersonalUnitOfWorkFactory
T0 = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
LIMITS = IngestionLimits(
    max_text_bytes=256 * 1024, max_conversation_messages=1000, max_conversation_bytes=4 * 1024**2
)


class ProposalsAsCandidates:
    """Stands in for steps 4-5: every non-rejected proposal becomes a candidate."""

    def __init__(self) -> None:
        self.extraction: FactExtraction | None = None

    def evaluate(self, content: SourceContent, extraction: FactExtraction) -> PipelineResult:
        self.extraction = extraction
        source = content.source
        candidates = [
            MemoryCandidate(
                id=new_id(),
                owner_id=source.owner_id,
                source_id=source.id,
                proposition=p.proposition,
                status=(
                    CandidateStatus.CANDIDATE
                    if p.status is ProposalStatus.EXTRACTED
                    else CandidateStatus.NEEDS_REVIEW
                ),
                origin=CandidateOrigin.EXPLICIT,
                extraction_confidence=p.extraction_confidence,
                context=p.structure(),
                temporal={"expressions": list(p.temporal), "reference": p.temporal_reference},
            )
            for p in extraction.proposals
            if p.status is not ProposalStatus.REJECTED
        ]
        status = (
            SourceProcessingStatus.PARTIALLY_EXTRACTED
            if extraction.partial
            else SourceProcessingStatus.EXTRACTED
        )
        return PipelineResult(status=status, candidates=candidates)


class _Publisher:
    def __init__(self) -> None:
        self.published: list[OutboxMessage] = []

    def publish(self, message: OutboxMessage) -> None:
        self.published.append(message)


def _run(
    uow: Uow, session_factory: sessionmaker[Session], owner: OwnerScope, text: str
) -> tuple[Any, uuid.UUID, ProposalsAsCandidates]:
    storage = InMemoryObjectStorage()
    source_id = (
        PersonalIngestionService(uow, storage, LIMITS, clock=lambda: T0)
        .ingest(
            owner,
            IngestionRequest(
                owner_id=owner.owner_id,
                idempotency_key=str(uuid.uuid4()),
                source_type=SourceType.TEXT,
                text=text,
            ),
        )
        .source_id
    )
    publisher = _Publisher()
    OutboxRelay(
        session_factory,
        publisher,
        OutboxSettings(),
        clock=lambda: T0 + timedelta(minutes=1),
        jitter=lambda d: d,
    ).relay_due()
    [message] = [m for m in publisher.published if m.subject_id == source_id]
    analyzer = SpacySentenceAnalyzer()
    downstream = ProposalsAsCandidates()
    pipeline = GatedPipeline(
        RelevanceGate(analyzer, RelevancePolicy.from_settings(RelevanceSettings())),
        FactExtractionStage(FactExtractor(FactExtractionSettings()), downstream),
    )
    report = ExtractionService(
        uow, storage, pipeline, language_policy(ExtractionSettings())
    ).handle(message.envelope.to_dict())
    return report, source_id, downstream


def test_atomic_facts_reach_the_candidate_store_with_their_structure(
    uow_factory: Uow, session_factory: sessionmaker[Session], owner: OwnerScope
) -> None:
    text = (
        "I am a software engineering student, currently learning Kotlin, "
        "and I want to become an Android developer."
    )
    report, source_id, downstream = _run(uow_factory, session_factory, owner, text)
    assert (report.status, report.candidates) == (SourceProcessingStatus.EXTRACTED, 3)
    with uow_factory() as uow:
        candidates = uow.candidates.list_for_source(owner, source_id)
        [assessment] = uow.relevance.for_source(owner, source_id)
    assert sorted(c.proposition for c in candidates) == [
        "The user is a software engineering student.",
        "The user is currently learning Kotlin.",
        "The user wants to become an Android developer.",
    ]
    intended = next(c for c in candidates if "Android" in c.proposition)
    assert intended.context["modality"] == "intended"
    assert intended.context["predicate"] == "want to become"
    assert assessment.outcome.value == "process"
    assert downstream.extraction is not None and not downstream.extraction.partial


def test_reported_and_ambiguous_statements_go_to_review(
    uow_factory: Uow, session_factory: sessionmaker[Session], owner: OwnerScope
) -> None:
    report, source_id, _ = _run(
        uow_factory, session_factory, owner, "My friend said he is moving to Canada."
    )
    assert report.status is SourceProcessingStatus.EXTRACTED
    with uow_factory() as uow:
        [candidate] = uow.candidates.list_for_source(owner, source_id)
    assert candidate.status is CandidateStatus.NEEDS_REVIEW
    assert candidate.context["attributed_to"] == "the user's friend"
    assert candidate.context["unresolved_references"] == ["he"]
