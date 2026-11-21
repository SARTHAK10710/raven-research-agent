"""Phase 8.4 step 5: candidate generation and validation (6.2.6), no I/O."""

import uuid
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import pytest

from memory_engine.config.settings import EvaluationSettings
from memory_engine.domain.errors import DomainValidationError
from memory_engine.domain.vocabulary import (
    CandidateOrigin,
    CandidateStatus,
    EvaluationOutcome,
    FactModality,
    IngestionPriority,
    InstructionType,
    MemoryCategory,
    ProcessingEventType,
    ProposalStatus,
    SourceProcessingStatus,
    SourceType,
)
from memory_engine.personal.application.candidates import (
    ALL_PROPOSALS_REJECTED,
    CONDITION_LOST,
    EVIDENCE_NOT_FOUND,
    NEGATION_LOST,
    NO_FACT_PROPOSALS,
    OWNERSHIP_MISMATCH,
    CandidateGenerator,
    categories,
)
from memory_engine.personal.application.evaluation import ProposalEvaluator
from memory_engine.personal.application.extraction import (
    PipelineResult,
    Segment,
    SourceContent,
)
from memory_engine.personal.application.facts import FactExtraction
from memory_engine.personal.domain import (
    CandidateEvaluation,
    EvaluatedProposal,
    FactProposal,
    MemoryCandidate,
    MemorySource,
    SourceProcessingEvent,
)

T0 = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)
OWNER = uuid.uuid4()
SOURCE = MemorySource(
    id=uuid.uuid4(),
    owner_id=OWNER,
    source_type=SourceType.TEXT,
    processing_status=SourceProcessingStatus.QUEUED,
    received_at=T0,
    content_sha256="a" * 64,
    instruction_type=InstructionType.NORMAL,
    priority=IngestionPriority.NORMAL,
)
TEXT = "I prefer tea."
CONTENT = SourceContent(source=SOURCE, segments=[Segment(position=0, text=TEXT)])
EVALUATOR = ProposalEvaluator(EvaluationSettings())
GENERATOR = CandidateGenerator(clock=lambda: T0)


def _proposal(**values: Any) -> FactProposal:
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "owner_id": OWNER,
        "source_id": SOURCE.id,
        "segment": 0,
        "sentence": 0,
        "original_text": TEXT,
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


def _run(*proposals: FactProposal, **extraction: Any) -> PipelineResult:
    facts = FactExtraction(proposals=list(proposals), **extraction)
    return GENERATOR.generate(CONTENT, facts, EVALUATOR.evaluate(CONTENT, facts.proposals))


def _evaluated(proposal: FactProposal) -> EvaluatedProposal:
    [item] = EVALUATOR.evaluate(CONTENT, [proposal])
    return item


def _status(result: PipelineResult, candidate: MemoryCandidate) -> CandidateStatus:
    [evaluation] = [e for e in result.evaluations if e.candidate_id == candidate.id]
    return evaluation.to_status


# --- generation --------------------------------------------------------------------


def test_a_valid_proposal_becomes_a_validated_candidate() -> None:
    result = _run(_proposal())
    assert (result.status, result.reason_code, result.validated) == (
        SourceProcessingStatus.EXTRACTED,
        None,
        1,
    )
    [candidate] = result.candidates
    [evaluation] = result.evaluations
    # Inserted as a candidate; the recorded evaluation validates it (rule 9: not a memory).
    assert candidate.status is CandidateStatus.CANDIDATE
    assert (evaluation.from_status, evaluation.to_status, evaluation.outcome) == (
        CandidateStatus.CANDIDATE,
        CandidateStatus.VALIDATED,
        EvaluationOutcome.PROCEED,
    )
    assert evaluation.reason_code is None and evaluation.evaluated_at == T0
    assert candidate.categories == (MemoryCategory.PERSONAL_PREFERENCE,)
    assert candidate.origin is CandidateOrigin.EXPLICIT


def test_scores_context_and_provenance_stay_separate() -> None:
    # 6.2.6 AC-05, AC-06, AC-08, AC-09.
    [candidate] = _run(_proposal(extraction_confidence=0.75, temporal=("on Friday",))).candidates
    assert (candidate.importance, candidate.confidence, candidate.extraction_confidence) == (
        0.7,
        0.9,
        0.75,
    )
    assert candidate.context["predicate"] == "prefer"
    assert candidate.temporal == {
        "expressions": ["on Friday"],
        "reference_time": T0.isoformat(),
        "past": False,
        "modality": "factual",
        "conditional": False,
    }
    assert candidate.extraction_metadata["location"] == {"segment": 0, "sentence": 0}
    metadata = candidate.evaluation_metadata
    assert (metadata["category_rule"], metadata["freshness"]) == ("PREFERENCE", "time_bound")
    assert metadata["origin"]["reason_code"] == "DIRECT_USER_STATEMENT"
    assert metadata["origin"]["evidence"] == [[0, 0]]


def test_inferred_candidates_keep_their_evidence() -> None:
    # 6.2.6 AC-07.
    [candidate] = _run(_proposal(derived_from=((0, 0),))).candidates
    assert candidate.origin is CandidateOrigin.INFERRED
    assert candidate.extraction_metadata["derived_from"] == [[0, 0]]
    assert candidate.evaluation_metadata["origin"]["evidence"] == [[0, 0]]


def test_metadata_carries_no_source_text() -> None:
    [candidate] = _run(_proposal()).candidates
    text = repr(dict(candidate.extraction_metadata)) + repr(dict(candidate.evaluation_metadata))
    assert TEXT not in text and "tea" not in text


def test_review_keeps_the_candidate_with_its_reason() -> None:
    # 6.2.6 AC-13: unresolved origin stays in review, never validated.
    result = _run(
        _proposal(
            unresolved_references=("it",),
            object="it",
            status=ProposalStatus.NEEDS_REVIEW,
            reason_code="UNRESOLVED_REFERENCE",
        )
    )
    [candidate] = result.candidates
    [evaluation] = result.evaluations
    assert candidate.origin is CandidateOrigin.UNRESOLVED
    assert (evaluation.outcome, evaluation.to_status, evaluation.reason_code) == (
        EvaluationOutcome.NEEDS_REVIEW,
        CandidateStatus.NEEDS_REVIEW,
        "UNRESOLVED_REFERENCE",
    )
    assert result.status is SourceProcessingStatus.EXTRACTED and result.validated == 0


def test_a_classification_review_names_the_classification_reason() -> None:
    result = _run(_proposal(subject=None))
    [evaluation] = result.evaluations
    assert (evaluation.to_status, evaluation.reason_code) == (
        CandidateStatus.NEEDS_REVIEW,
        "NO_SUBJECT",
    )


def test_rejected_proposals_are_counted_never_stored() -> None:
    rejected = _proposal(status=ProposalStatus.REJECTED, reason_code="LOW_EXTRACTION_CONFIDENCE")
    result = _run(_proposal(), rejected)
    assert len(result.candidates) == 1
    assert result.outcome_summary == {
        "proposals": 2,
        "candidates": 1,
        "validated": 1,
        "needs_review": 0,
        "deferred": 0,
        "rejected": 1,
        "failed_sentences": 0,
        "skipped_questions": 0,
        "rejected:EXTRACTION_REJECTED": 1,
    }


def test_a_source_whose_proposals_are_all_rejected_is_rejected() -> None:
    result = _run(_proposal(status=ProposalStatus.REJECTED, reason_code="NO_VERB"))
    assert (result.status, result.reason_code, result.candidates) == (
        SourceProcessingStatus.REJECTED,
        ALL_PROPOSALS_REJECTED,
        [],
    )


def test_a_source_without_proposals_is_rejected() -> None:
    result = _run(skipped_questions=2)
    assert (result.status, result.reason_code) == (
        SourceProcessingStatus.REJECTED,
        NO_FACT_PROPOSALS,
    )
    assert result.outcome_summary is not None
    assert result.outcome_summary["skipped_questions"] == 2


def test_a_partial_extraction_stays_partial() -> None:
    result = _run(_proposal(), failed=[(0, 1)])
    assert result.status is SourceProcessingStatus.PARTIALLY_EXTRACTED
    assert result.outcome_summary is not None
    assert result.outcome_summary["failed_sentences"] == 1
    assert _run(failed=[(0, 0)]).status is SourceProcessingStatus.PARTIALLY_EXTRACTED


def test_a_proposal_of_another_owner_or_source_is_rejected() -> None:
    # 6.2.6 AC-11: ownership validation; never stored.
    for values in ({"owner_id": uuid.uuid4()}, {"source_id": uuid.uuid4()}):
        result = _run(_proposal(**values))
        assert result.candidates == []
        assert result.outcome_summary is not None
        assert result.outcome_summary[f"rejected:{OWNERSHIP_MISMATCH}"] == 1


def test_defer_leaves_a_candidate() -> None:
    item = _evaluated(_proposal())
    deferred = replace(
        item,
        evaluation=replace(
            item.evaluation, outcome=EvaluationOutcome.DEFER, reason_code="AMBIGUOUS"
        ),
    )
    result = GENERATOR.generate(CONTENT, FactExtraction(proposals=[item.proposal]), [deferred])
    [evaluation] = result.evaluations
    assert (evaluation.to_status, evaluation.reason_code) == (
        CandidateStatus.CANDIDATE,
        "AMBIGUOUS",
    )
    assert result.outcome_summary is not None and result.outcome_summary["deferred"] == 1


# --- validation (6.2.6 section 8.7) ---------------------------------------------------


@pytest.mark.parametrize(
    ("values", "code"),
    [
        ({"original_text": "I prefer coffee."}, EVIDENCE_NOT_FOUND),
        ({"segment": 3}, EVIDENCE_NOT_FOUND),
        ({"derived_from": ((4, 0),)}, EVIDENCE_NOT_FOUND),
        ({"negated": True}, NEGATION_LOST),
        ({"modality": FactModality.CONDITIONAL}, CONDITION_LOST),
    ],
)
def test_a_candidate_that_fails_validation_goes_to_review(
    values: dict[str, Any], code: str
) -> None:
    result = _run(_proposal(**values))
    [candidate] = result.candidates
    assert _status(result, candidate) is CandidateStatus.NEEDS_REVIEW
    [evaluation] = result.evaluations
    assert evaluation.reason_code == code


@pytest.mark.parametrize(
    "proposition",
    ["The user does not like tea.", "The user doesn't like tea.", "The user never drinks tea."],
)
def test_a_kept_negation_passes(proposition: str) -> None:
    result = _run(_proposal(negated=True, proposition=proposition))
    assert result.validated == 1


def test_evidence_matching_ignores_spacing_and_case() -> None:
    content = SourceContent(source=SOURCE, segments=[Segment(position=0, text="  I  PREFER\ntea.")])
    facts = FactExtraction(proposals=[_proposal()])
    result = GENERATOR.generate(content, facts, EVALUATOR.evaluate(content, facts.proposals))
    assert result.validated == 1


# --- categories (6.2.6 section 8.4) --------------------------------------------------


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ({"predicate": "want to become", "object": "an AI engineer"}, ("goal",)),
        ({"predicate": "decide to use", "object": "PostgreSQL"}, ("decision",)),
        ({"predicate": "graduate", "object": None, "past": True}, ("important_event",)),
        ({"subject": "the user's friend", "predicate": "work"}, ("relationship",)),
        ({"predicate": "learn", "object": "distributed systems"}, ("knowledge",)),
        ({"predicate": "build", "object": "Raven"}, ("project",)),
        ({"predicate": "have", "object": "a meeting"}, ("commitment",)),
        ({"predicate": "want to learn", "object": "Rust"}, ("goal", "knowledge")),
        ({"predicate": "decide to build", "object": "a startup"}, ("decision", "project")),
        ({"predicate": "work", "object": None, "attributes": ("on a mobile app",)}, ("project",)),
        ({"subject": "the user's sister", "predicate": "want to become"}, ("goal", "relationship")),
        ({"predicate": "be", "object": "allergic to peanuts"}, ()),
        ({"predicate": "delete", "object": "the app"}, ()),
    ],
)
def test_categories_follow_the_evidence(values: dict[str, Any], expected: tuple[str, ...]) -> None:
    item = _evaluated(_proposal(**values))
    assert tuple(c.value for c in categories(item)) == expected


# --- domain records ------------------------------------------------------------------


def _candidate(**values: Any) -> MemoryCandidate:
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "owner_id": OWNER,
        "source_id": SOURCE.id,
        "proposition": "Synthetic proposition.",
        "status": CandidateStatus.CANDIDATE,
        "origin": CandidateOrigin.EXPLICIT,
    }
    return MemoryCandidate(**base | values)


def test_candidate_categories_and_metadata_are_frozen() -> None:
    candidate = _candidate(categories=("goal",), evaluation_metadata={"freshness": "stable"})
    assert candidate.categories == (MemoryCategory.GOAL,)
    with pytest.raises(TypeError):
        candidate.evaluation_metadata["freshness"] = "changing"  # type: ignore[index]
    with pytest.raises(DomainValidationError, match="once"):
        _candidate(categories=(MemoryCategory.GOAL, MemoryCategory.GOAL))
    with pytest.raises(ValueError, match="not_a_category"):
        _candidate(categories=("not_a_category",))


def _evaluation(candidate: MemoryCandidate) -> CandidateEvaluation:
    return CandidateEvaluation(
        id=uuid.uuid4(),
        owner_id=OWNER,
        candidate_id=candidate.id,
        outcome=EvaluationOutcome.PROCEED,
        from_status=CandidateStatus.CANDIDATE,
        to_status=CandidateStatus.VALIDATED,
        method="m",
        method_version="1",
        evaluated_at=T0,
    )


def test_a_pipeline_result_only_evaluates_its_own_candidates() -> None:
    candidate = _candidate()
    with pytest.raises(DomainValidationError, match="evaluation"):
        PipelineResult(
            status=SourceProcessingStatus.EXTRACTED,
            candidates=[candidate],
            evaluations=[_evaluation(_candidate())],
        )
    with pytest.raises(DomainValidationError, match="unique"):
        PipelineResult(status=SourceProcessingStatus.EXTRACTED, candidates=[candidate, candidate])
    result = PipelineResult(
        status=SourceProcessingStatus.EXTRACTED,
        candidates=[candidate],
        evaluations=[_evaluation(candidate)],
    )
    assert result.validated == 1


def _event(**values: Any) -> SourceProcessingEvent:
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "owner_id": OWNER,
        "source_id": SOURCE.id,
        "event_type": ProcessingEventType.TRANSITION,
        "from_status": SourceProcessingStatus.PROCESSING,
        "to_status": SourceProcessingStatus.EXTRACTED,
        "attempt": 1,
        "occurred_at": T0,
    }
    return SourceProcessingEvent(**base | values)


def test_an_outcome_summary_holds_counts_and_codes_only() -> None:
    event = _event(outcome_summary={"validated": 2, "rejected:LOW_IMPORTANCE": 1})
    assert event.outcome_summary == {"validated": 2, "rejected:LOW_IMPORTANCE": 1}
    with pytest.raises(TypeError):
        event.outcome_summary["validated"] = 3  # type: ignore[index]


@pytest.mark.parametrize(
    "summary",
    [
        {"Validated": 1},
        {"validated count": 1},
        {"rejected:not a code": 1},
        {"validated": -1},
        {"validated": True},
        {"validated": 1.5},
        {"text": "I prefer tea."},
    ],
)
def test_an_invalid_outcome_summary_is_refused(summary: dict[str, Any]) -> None:
    with pytest.raises(DomainValidationError):
        _event(outcome_summary=summary)


def test_only_transitions_carry_a_summary() -> None:
    with pytest.raises(DomainValidationError):
        _event(
            event_type=ProcessingEventType.FAILURE,
            to_status=SourceProcessingStatus.PROCESSING_FAILED,
            error_code="EXTRACTION_FAILED",
            outcome_summary={"proposals": 1},
        )
