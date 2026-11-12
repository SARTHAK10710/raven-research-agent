"""Phase 8.4 step 4: gate, extraction, evaluation and classification in the worker.

Candidate generation (step 5) is a stand-in that copies each evaluation onto a
candidate, so the assembled pipeline runs end to end on PostgreSQL.
Synthetic data only.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from memory_engine.config.settings import (
    EvaluationSettings,
    ExtractionSettings,
    FactExtractionSettings,
    OutboxSettings,
    RelevanceSettings,
)
from memory_engine.domain.handoff import OutboxMessage
from memory_engine.domain.identifiers import OwnerScope, new_id
from memory_engine.domain.vocabulary import (
    CandidateStatus,
    EvaluationOutcome,
    SourceProcessingStatus,
    SourceType,
)
from memory_engine.infrastructure.messaging import OutboxRelay
from memory_engine.infrastructure.nlp import SpacySentenceAnalyzer
from memory_engine.infrastructure.object_storage import InMemoryObjectStorage
from memory_engine.infrastructure.persistence import SqlAlchemyPersonalUnitOfWorkFactory
from memory_engine.personal.application.evaluation import EvaluationStage, ProposalEvaluator
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
from memory_engine.personal.domain import EvaluatedProposal, MemoryCandidate

pytestmark = pytest.mark.integration

Uow = SqlAlchemyPersonalUnitOfWorkFactory
T0 = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
LIMITS = IngestionLimits(
    max_text_bytes=256 * 1024, max_conversation_messages=1000, max_conversation_bytes=4 * 1024**2
)


class EvaluationsAsCandidates:
    """Stands in for step 5: carry each evaluation onto a candidate, drop rejections."""

    def generate(
        self,
        content: SourceContent,
        extraction: FactExtraction,
        evaluated: Sequence[EvaluatedProposal],
    ) -> PipelineResult:
        source = content.source
        candidates = [
            MemoryCandidate(
                id=new_id(),
                owner_id=source.owner_id,
                source_id=source.id,
                proposition=item.proposal.proposition,
                status=(
                    CandidateStatus.CANDIDATE
                    if item.outcome is EvaluationOutcome.PROCEED
                    else CandidateStatus.NEEDS_REVIEW
                ),
                origin=item.classification.origin,
                importance=item.evaluation.importance,
                confidence=item.evaluation.fact_confidence,
                extraction_confidence=item.proposal.extraction_confidence,
                context=item.proposal.structure(),
            )
            for item in evaluated
            if item.outcome is not EvaluationOutcome.REJECT
        ]
        return PipelineResult(status=SourceProcessingStatus.EXTRACTED, candidates=candidates)


class _Publisher:
    def __init__(self) -> None:
        self.published: list[OutboxMessage] = []

    def publish(self, message: OutboxMessage) -> None:
        self.published.append(message)


def test_evaluated_candidates_keep_independent_scores_and_origin(
    uow_factory: Uow, session_factory: sessionmaker[Session], owner: OwnerScope
) -> None:
    storage = InMemoryObjectStorage()
    text = "I'm allergic to peanuts. My friend said he is moving to Canada."
    source_id = (
        PersonalIngestionService(uow_factory, storage, LIMITS, clock=lambda: T0)
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
    pipeline = GatedPipeline(
        RelevanceGate(analyzer, RelevancePolicy.from_settings(RelevanceSettings())),
        FactExtractionStage(
            FactExtractor(FactExtractionSettings()),
            EvaluationStage(ProposalEvaluator(EvaluationSettings()), EvaluationsAsCandidates()),
        ),
    )
    report = ExtractionService(
        uow_factory, storage, pipeline, language_policy(ExtractionSettings())
    ).handle(message.envelope.to_dict())
    assert (report.status, report.candidates) == (SourceProcessingStatus.EXTRACTED, 2)
    with uow_factory() as uow:
        candidates = {c.proposition: c for c in uow.candidates.list_for_source(owner, source_id)}
    allergy = candidates["The user is allergic to peanuts."]
    assert (allergy.importance, allergy.confidence, allergy.origin.value) == (
        0.85,
        0.9,
        "explicit",
    )
    assert allergy.status is CandidateStatus.CANDIDATE
    hearsay = candidates["According to the user's friend, he is moving to Canada."]
    assert (hearsay.origin.value, hearsay.status) == ("unresolved", CandidateStatus.NEEDS_REVIEW)
    assert hearsay.confidence == pytest.approx(0.15)  # second-hand and unresolved
