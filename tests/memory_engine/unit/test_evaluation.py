"""Phase 8.4 step 4: evaluation (6.2.4) and origin classification (6.2.5), no I/O."""

import uuid
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import pytest

from memory_engine.config.settings import EvaluationSettings
from memory_engine.domain.errors import DomainValidationError
from memory_engine.domain.vocabulary import (
    CandidateOrigin,
    EvaluationOutcome,
    FactModality,
    FreshnessClass,
    IngestionPriority,
    InstructionType,
    ProposalStatus,
    SourceProcessingStatus,
    SourceType,
)
from memory_engine.personal.application.evaluation import (
    EvaluationStage,
    ProposalEvaluator,
    about_user,
    category,
)
from memory_engine.personal.application.extraction import (
    PipelineResult,
    Segment,
    SourceContent,
)
from memory_engine.personal.application.facts import FactExtraction
from memory_engine.personal.domain import (
    EvaluatedProposal,
    FactProposal,
    MemorySource,
    OriginClassification,
    ProposalEvaluation,
)

T0 = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
OWNER = uuid.uuid4()


def _content(instruction: InstructionType = InstructionType.NORMAL) -> SourceContent:
    source = MemorySource(
        id=uuid.uuid4(),
        owner_id=OWNER,
        source_type=SourceType.TEXT,
        processing_status=SourceProcessingStatus.QUEUED,
        received_at=T0,
        content_sha256="a" * 64,
        instruction_type=instruction,
        priority=(
            IngestionPriority.NORMAL
            if instruction is InstructionType.NORMAL
            else IngestionPriority.HIGH
        ),
    )
    return SourceContent(source=source, segments=[Segment(position=0, text="x")])


def _proposal(**values: Any) -> FactProposal:
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "owner_id": OWNER,
        "source_id": uuid.uuid4(),
        "segment": 0,
        "sentence": 0,
        "original_text": "I prefer tea.",
        "proposition": "The user prefers tea.",
        "subject": "the user",
        "predicate": "prefer",
        "object": "tea",
        "modality": FactModality.FACTUAL,
        "speaker": "user",
        "extraction_confidence": 1.0,
        "status": ProposalStatus.EXTRACTED,
        "method": "dependency_rules",
        "method_version": "1",
        "temporal_reference": T0.isoformat(),
    }
    return FactProposal(**base | values)


def _one(proposal: FactProposal, **settings: Any) -> EvaluatedProposal:
    content = _content()
    [item] = ProposalEvaluator(EvaluationSettings(**settings)).evaluate(content, [proposal])
    return item


def test_every_proposal_is_evaluated_even_a_rejected_one() -> None:
    rejected = _proposal(status=ProposalStatus.REJECTED, reason_code="LOW_EXTRACTION_CONFIDENCE")
    item = _one(rejected)
    assert (item.outcome, item.evaluation.reason_code) == (
        EvaluationOutcome.REJECT,
        "EXTRACTION_REJECTED",
    )


def test_low_importance_is_rejected_unless_the_user_asked_to_remember() -> None:
    other = _proposal(predicate="cancel", subject="the project", object=None)
    assert _one(other, reject_importance=0.5).evaluation.reason_code == "LOW_IMPORTANCE"
    content = _content(InstructionType.REMEMBER)
    [kept] = ProposalEvaluator(EvaluationSettings(reject_importance=0.5)).evaluate(content, [other])
    assert kept.evaluation.outcome is EvaluationOutcome.PROCEED
    assert kept.evaluation.importance == pytest.approx(0.4)  # other 0.3 + remember 0.1


def test_importance_is_capped_at_one() -> None:
    content = _content(InstructionType.REMEMBER)
    [item] = ProposalEvaluator(EvaluationSettings(remember_bonus=0.5)).evaluate(
        content, [_proposal(predicate="want to become")]
    )
    assert item.evaluation.importance == 1.0


def test_an_inferred_proposal_keeps_its_evidence() -> None:
    proposal = _proposal(derived_from=((0, 0), (1, 0)), extraction_confidence=0.7)
    classification = _one(proposal).classification
    assert classification.origin is CandidateOrigin.INFERRED
    assert classification.evidence == ((0, 0), (1, 0))
    assert classification.reason_code == "DERIVED_FROM_EVIDENCE"
    assert not classification.needs_review
    weak = _one(replace(proposal, extraction_confidence=0.3)).classification
    assert weak.needs_review  # 6.2.5 rule 6: a weak inference is not promoted


def test_a_fact_without_a_subject_is_unresolved() -> None:
    proposal = _proposal(
        subject=None,
        status=ProposalStatus.NEEDS_REVIEW,
        reason_code="LOW_EXTRACTION_CONFIDENCE",
        extraction_confidence=0.2,
    )
    item = _one(proposal)
    assert (item.classification.origin, item.classification.reason_code) == (
        CandidateOrigin.UNRESOLVED,
        "NO_SUBJECT",
    )
    assert item.outcome is EvaluationOutcome.NEEDS_REVIEW


def test_classification_review_turns_a_proceed_into_review() -> None:
    item = _one(_proposal(derived_from=((0, 0),), extraction_confidence=0.3))
    assert item.evaluation.outcome is EvaluationOutcome.PROCEED
    assert item.outcome is EvaluationOutcome.NEEDS_REVIEW


@pytest.mark.parametrize(
    ("subject", "expected"),
    [
        ("the user", True),
        ("the user's goal this year", True),
        ("the user and others", True),
        ("the user's sister", False),
        ("Tom", False),
        (None, False),
    ],
)
def test_subjects_about_the_user(subject: str | None, expected: bool) -> None:
    assert about_user(subject) is expected


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ({"predicate": "want to become"}, "GOAL"),
        ({"predicate": "have to call"}, "COMMITMENT"),
        ({"predicate": "decide to switch"}, "DECISION"),
        ({"subject": "the user's brother", "predicate": "live"}, "RELATIONSHIP"),
        ({"predicate": "live", "object": None}, "HEALTH_IDENTITY"),
        ({"predicate": "prefer"}, "PREFERENCE"),
        ({"predicate": "swim", "proposition": "The user swims every day."}, "HABIT"),
        ({"predicate": "visit"}, "EVENT"),
        ({"predicate": "read", "past": True}, "EVENT"),
        ({"predicate": "read"}, "OTHER"),
    ],
)
def test_category_rules(values: dict[str, Any], expected: str) -> None:
    assert category(_proposal(**values)) == expected


def test_freshness_of_a_dated_habit_stays_changing() -> None:
    habit = _proposal(
        predicate="swim", proposition="The user swims every morning.", temporal=("morning",)
    )
    assert _one(habit).evaluation.freshness is FreshnessClass.CHANGING


def test_settings_change_the_tables() -> None:
    item = _one(_proposal(), confidence_direct=0.75, importance_preference=0.5)
    assert (item.evaluation.fact_confidence, item.evaluation.importance) == (0.75, 0.5)


# --- the stage ------------------------------------------------------------------------


class _Generate:
    def __init__(self) -> None:
        self.evaluated: list[EvaluatedProposal] = []

    def generate(
        self,
        content: SourceContent,
        extraction: FactExtraction,
        evaluated: Sequence[EvaluatedProposal],
    ) -> PipelineResult:
        self.evaluated = list(evaluated)
        return PipelineResult(status=SourceProcessingStatus.EXTRACTED)


def test_the_stage_hands_evaluated_proposals_to_candidate_generation() -> None:
    downstream = _Generate()
    stage = EvaluationStage(ProposalEvaluator(EvaluationSettings()), downstream)
    result = stage.evaluate(_content(), FactExtraction(proposals=[_proposal(), _proposal()]))
    assert result.status is SourceProcessingStatus.EXTRACTED
    assert len(downstream.evaluated) == 2
    assert "REPEATED" in downstream.evaluated[1].evaluation.uncertainty


# --- records ---------------------------------------------------------------------------


def _evaluation(**values: Any) -> ProposalEvaluation:
    base: dict[str, Any] = {
        "category": "PREFERENCE",
        "importance": 0.7,
        "fact_confidence": 0.9,
        "confidence_basis": "DIRECT",
        "freshness": FreshnessClass.CHANGING,
        "observed_at": T0.isoformat(),
        "long_term_utility": 1.0,
        "contextual_significance": 0.3,
        "outcome": EvaluationOutcome.PROCEED,
        "method": "evaluation_rules",
        "method_version": "1",
    }
    return ProposalEvaluation(**base | values)


@pytest.mark.parametrize(
    "values",
    [
        {"importance": 1.5},
        {"fact_confidence": -0.1},
        {"long_term_utility": float("nan")},
        {"contextual_significance": 2.0},
        {"category": "lower"},
        {"category": ""},
        {"outcome": EvaluationOutcome.NEEDS_REVIEW},
        {"reason_code": "WHY"},
        {"uncertainty": ("bad code",)},
        {"method": " "},
    ],
)
def test_evaluation_invariants(values: dict[str, Any]) -> None:
    with pytest.raises(DomainValidationError):
        _evaluation(**values)


def _classification(**values: Any) -> OriginClassification:
    base: dict[str, Any] = {
        "origin": CandidateOrigin.EXPLICIT,
        "confidence": 1.0,
        "reason_code": "DIRECT_USER_STATEMENT",
        "evidence": ((0, 0),),
        "speaker": "user",
        "subject": "the user",
        "needs_review": False,
        "method": "origin_rules",
        "method_version": "1",
    }
    return OriginClassification(**base | values)


@pytest.mark.parametrize(
    "values",
    [
        {"evidence": ()},
        {"origin": CandidateOrigin.UNRESOLVED, "needs_review": False},
        {"confidence": 1.1},
        {"reason_code": "lower"},
    ],
)
def test_classification_invariants(values: dict[str, Any]) -> None:
    with pytest.raises(DomainValidationError):
        _classification(**values)
