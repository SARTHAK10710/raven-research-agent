"""Candidate generation and validation (6.2.6; owner-approved, 8.4 step 5).

The last pipeline stage. For every evaluated proposal (6.2.4-6.2.5):

- **Rejected** proposals (evaluation outcome ``reject``, or a failed ownership
  check) are never stored: the run's ``outcome_summary`` counts them by
  reason code (owner decision).
- Every other proposal becomes a Memory Candidate, inserted as ``candidate``
  and then moved by one recorded evaluation (5.4.25) to ``validated``,
  ``needs_review`` or, for ``defer``, left ``candidate``. Nothing is merged,
  resolved or activated here (rules 8-9); validated candidates are handed to
  memory resolution (plan 8.6) through the outbox.

**Categories** (5.4.9; owner decision: rules, multi-label) come only from
evidence in the proposal: the importance rule that applied (goal,
commitment, decision, relationship; preference and habit as personal
preference; event as important event), plus knowledge (a learning
predicate), project (a building predicate, or working on a project-like
object) and relationship (a subject that names a related person). Health,
identity and anything else get no category rather than a guess. Order
follows the taxonomy.

**Validation** (6.2.6 section 8.7) on top of the domain invariants:
ownership (reject), evidence present in the source (else review),
negation kept in the proposition (else review), a conditional keeps its
condition (else review). Low confidence follows the evaluation's review
policy. Candidates keep their structure, temporal information, extraction
and evaluation metadata separately (rules 4-7); metadata holds locations,
codes and scores, never text other than the proposition and its structure.
"""

import re
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any

from memory_engine.domain.identifiers import new_id
from memory_engine.domain.vocabulary import (
    CandidateStatus,
    EvaluationOutcome,
    FactModality,
    MemoryCategory,
    SourceProcessingStatus,
)
from memory_engine.personal.application.evaluation import (
    COMMITMENT,
    DECISION,
    EVENT,
    GOAL,
    HABIT,
    PREFERENCE,
    RELATIONSHIP,
    names_relation,
)
from memory_engine.personal.application.extraction import PipelineResult, SourceContent
from memory_engine.personal.application.facts import FactExtraction
from memory_engine.personal.domain import (
    CandidateEvaluation,
    EvaluatedProposal,
    FactProposal,
    MemoryCandidate,
)

METHOD = "candidate_rules"
METHOD_VERSION = "1"

# Source outcomes when nothing becomes a candidate.
NO_FACT_PROPOSALS = "NO_FACT_PROPOSALS"
ALL_PROPOSALS_REJECTED = "ALL_PROPOSALS_REJECTED"
# Validation codes (6.2.6 section 8.7).
OWNERSHIP_MISMATCH = "OWNERSHIP_MISMATCH"
EVIDENCE_NOT_FOUND = "EVIDENCE_NOT_FOUND"
NEGATION_LOST = "NEGATION_LOST"
CONDITION_LOST = "CONDITION_LOST"
NEEDS_REVIEW_FALLBACK = "NEEDS_REVIEW"

_BY_KIND = {
    GOAL: MemoryCategory.GOAL,
    COMMITMENT: MemoryCategory.COMMITMENT,
    DECISION: MemoryCategory.DECISION,
    RELATIONSHIP: MemoryCategory.RELATIONSHIP,
    PREFERENCE: MemoryCategory.PERSONAL_PREFERENCE,
    HABIT: MemoryCategory.PERSONAL_PREFERENCE,
    EVENT: MemoryCategory.IMPORTANT_EVENT,
}
_TAXONOMY = tuple(MemoryCategory)
_KNOWLEDGE_VERBS = frozenset(
    {"learn", "study", "know", "understand", "research", "master", "practise", "practice"}
)
_PROJECT_VERBS = frozenset(
    {"build", "develop", "create", "design", "prototype", "code", "program", "found"}
)
_PROJECT_ACTIVITIES = frozenset(
    {"work", "start", "launch", "finish", "ship", "run", "lead", "manage", "make"}
)
_PROJECT_NOUNS = frozenset(
    {
        "project",
        "projects",
        "app",
        "apps",
        "application",
        "startup",
        "website",
        "product",
        "prototype",
        "library",
        "platform",
        "game",
        "tool",
        "thesis",
    }
)
_WORD = re.compile(r"[a-z']+")
_NEGATION = re.compile(r"\b(?:not|never|no|nor|cannot)\b|n't")
_TYPOGRAPHIC_APOSTROPHE = chr(0x2019)
_SPACE = re.compile(r"\s+")


def _words(*texts: str | None) -> set[str]:
    return {w for text in texts if text for w in _WORD.findall(text.lower())}


def categories(item: EvaluatedProposal) -> tuple[MemoryCategory, ...]:
    """The 5.4.9 categories the proposal's own evidence supports (zero or more)."""
    proposal = item.proposal
    found: set[MemoryCategory] = set()
    kind = _BY_KIND.get(item.evaluation.category)
    if kind is not None:
        found.add(kind)
    predicate = _words(proposal.predicate)
    if predicate & _KNOWLEDGE_VERBS:
        found.add(MemoryCategory.KNOWLEDGE)
    if predicate & _PROJECT_VERBS or (
        # "working on a mobile app": the thing worked on is an object or a
        # prepositional attribute.
        predicate & _PROJECT_ACTIVITIES
        and _words(proposal.object, *proposal.attributes) & _PROJECT_NOUNS
    ):
        found.add(MemoryCategory.PROJECT)
    if names_relation(proposal.subject):
        found.add(MemoryCategory.RELATIONSHIP)
    return tuple(c for c in _TAXONOMY if c in found)


def _normalized(text: str) -> str:
    return _SPACE.sub(" ", text).strip().lower()


def _utc_now() -> datetime:
    return datetime.now(UTC)


class CandidateGenerator:
    """Implements the ``CandidateStage`` port (6.2.6)."""

    def __init__(self, *, clock: Callable[[], datetime] = _utc_now) -> None:
        self._clock = clock

    def generate(
        self,
        content: SourceContent,
        extraction: FactExtraction,
        evaluated: Sequence[EvaluatedProposal],
    ) -> PipelineResult:
        source = content.source
        candidates: list[MemoryCandidate] = []
        evaluations: list[CandidateEvaluation] = []
        rejected: Counter[str] = Counter()
        now = self._clock()
        for item in evaluated:
            proposal = item.proposal
            if proposal.owner_id != source.owner_id or proposal.source_id != source.id:
                rejected[OWNERSHIP_MISMATCH] += 1  # 6.2.6 section 8.10: cross-user -> reject
                continue
            outcome, reason = self._decision(content, item)
            if outcome is EvaluationOutcome.REJECT:
                rejected[reason or EvaluationOutcome.REJECT.name] += 1
                continue
            candidate = self._candidate(item)
            candidates.append(candidate)
            evaluations.append(self._evaluation(candidate, item, outcome, reason, now))
        summary = self._summary(extraction, evaluated, evaluations, rejected)
        if extraction.partial:
            status, code = SourceProcessingStatus.PARTIALLY_EXTRACTED, None
        elif candidates:
            status, code = SourceProcessingStatus.EXTRACTED, None
        else:
            status = SourceProcessingStatus.REJECTED
            code = ALL_PROPOSALS_REJECTED if evaluated else NO_FACT_PROPOSALS
        return PipelineResult(
            status=status,
            candidates=candidates,
            evaluations=evaluations,
            reason_code=code,
            outcome_summary=summary,
        )

    @staticmethod
    def _decision(
        content: SourceContent, item: EvaluatedProposal
    ) -> tuple[EvaluationOutcome, str | None]:
        """Steps 2-3 and 8-9: the evaluation's outcome, then validation."""
        outcome = item.outcome
        if outcome is EvaluationOutcome.REJECT:
            return outcome, item.evaluation.reason_code
        if outcome is not EvaluationOutcome.PROCEED:
            reason = item.evaluation.reason_code
            if reason is None:  # proceed turned into review by the classification
                reason = item.classification.reason_code
            return outcome, reason
        problem = _validation_problem(content, item)
        if problem is not None:
            return EvaluationOutcome.NEEDS_REVIEW, problem
        return EvaluationOutcome.PROCEED, None

    @staticmethod
    def _candidate(item: EvaluatedProposal) -> MemoryCandidate:
        proposal, evaluation, origin = item.proposal, item.evaluation, item.classification
        return MemoryCandidate(
            id=new_id(),
            owner_id=proposal.owner_id,
            source_id=proposal.source_id,
            proposition=proposal.proposition,
            status=CandidateStatus.CANDIDATE,
            origin=origin.origin,
            importance=evaluation.importance,
            confidence=evaluation.fact_confidence,
            extraction_confidence=proposal.extraction_confidence,
            categories=categories(item),
            context=proposal.structure(),
            temporal=_temporal(proposal),
            extraction_metadata=_extraction_metadata(proposal),
            evaluation_metadata=_evaluation_metadata(item),
        )

    @staticmethod
    def _evaluation(
        candidate: MemoryCandidate,
        item: EvaluatedProposal,
        outcome: EvaluationOutcome,
        reason: str | None,
        now: datetime,
    ) -> CandidateEvaluation:
        to_status = {
            EvaluationOutcome.PROCEED: CandidateStatus.VALIDATED,
            EvaluationOutcome.NEEDS_REVIEW: CandidateStatus.NEEDS_REVIEW,
            EvaluationOutcome.DEFER: CandidateStatus.CANDIDATE,
        }[outcome]
        if outcome is not EvaluationOutcome.PROCEED and reason is None:
            reason = NEEDS_REVIEW_FALLBACK
        return CandidateEvaluation(
            id=new_id(),
            owner_id=candidate.owner_id,
            candidate_id=candidate.id,
            outcome=outcome,
            from_status=CandidateStatus.CANDIDATE,
            to_status=to_status,
            method=METHOD,
            method_version=METHOD_VERSION,
            evaluated_at=now,
            importance=item.evaluation.importance,
            confidence=item.evaluation.fact_confidence,
            reason_code=reason,
        )

    @staticmethod
    def _summary(
        extraction: FactExtraction,
        evaluated: Sequence[EvaluatedProposal],
        evaluations: Sequence[CandidateEvaluation],
        rejected: Counter[str],
    ) -> dict[str, int]:
        statuses = Counter(e.to_status for e in evaluations)
        summary = {
            "proposals": len(evaluated),
            "candidates": len(evaluations),
            "validated": statuses[CandidateStatus.VALIDATED],
            "needs_review": statuses[CandidateStatus.NEEDS_REVIEW],
            "deferred": statuses[CandidateStatus.CANDIDATE],
            "rejected": sum(rejected.values()),
            "failed_sentences": len(extraction.failed),
            "skipped_questions": extraction.skipped_questions,
        }
        summary.update({f"rejected:{code}": n for code, n in sorted(rejected.items())})
        return summary


def _validation_problem(content: SourceContent, item: EvaluatedProposal) -> str | None:
    proposal = item.proposal
    segments = {s.position: s for s in content.segments}
    segment = segments.get(proposal.segment)
    if segment is None or _normalized(proposal.original_text) not in _normalized(segment.text):
        return EVIDENCE_NOT_FOUND
    if any(location[0] not in segments for location in item.classification.evidence):
        return EVIDENCE_NOT_FOUND  # inferred candidates need reachable evidence (AC-07)
    proposition = proposal.proposition.lower().replace(_TYPOGRAPHIC_APOSTROPHE, "'")
    if proposal.negated and not _NEGATION.search(proposition):
        return NEGATION_LOST
    if proposal.modality is FactModality.CONDITIONAL and not proposal.conditions:
        return CONDITION_LOST
    return None


def _temporal(proposal: FactProposal) -> dict[str, Any]:
    """Rule 6: past, current, future, recurring and conditional stay distinguishable."""
    return {
        "expressions": list(proposal.temporal),
        "reference_time": proposal.temporal_reference,  # the source's own time, never invented
        "past": proposal.past,
        "modality": proposal.modality.value,
        "conditional": bool(proposal.conditions),
    }


def _extraction_metadata(proposal: FactProposal) -> dict[str, Any]:
    return {
        "method": proposal.method,
        "method_version": proposal.method_version,
        "proposal_status": proposal.status.value,
        "reason_code": proposal.reason_code,
        "weaknesses": list(proposal.weaknesses),
        "location": {"segment": proposal.segment, "sentence": proposal.sentence},
        "derived_from": [list(location) for location in proposal.derived_from],
        "generation": {"method": METHOD, "method_version": METHOD_VERSION},
    }


def _evaluation_metadata(item: EvaluatedProposal) -> dict[str, Any]:
    evaluation, origin = item.evaluation, item.classification
    return {
        "category_rule": evaluation.category,
        "confidence_basis": evaluation.confidence_basis,
        "freshness": evaluation.freshness.value,
        "observed_at": evaluation.observed_at,
        "long_term_utility": evaluation.long_term_utility,
        "contextual_significance": evaluation.contextual_significance,
        "uncertainty": list(evaluation.uncertainty),
        "evaluation_outcome": evaluation.outcome.value,
        "evaluation_reason": evaluation.reason_code,
        "method": evaluation.method,
        "method_version": evaluation.method_version,
        "origin": {
            "reason_code": origin.reason_code,
            "confidence": origin.confidence,
            "evidence": [list(location) for location in origin.evidence],
            "needs_review": origin.needs_review,
            "method": origin.method,
            "method_version": origin.method_version,
        },
    }
