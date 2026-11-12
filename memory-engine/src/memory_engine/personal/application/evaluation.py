"""Memory evaluation and origin classification (6.2.4-6.2.5; owner-approved, 8.4 step 4).

Every proposal from fact extraction gets an evaluation, rejected ones included
(6.2.4 AC-01). Dimensions stay independent:

- **Importance** (rule table): what the fact is about, first match wins:
  goal, commitment, decision, relationship, health/identity, preference,
  habit, event, other; plus a bonus when the user asked to remember (an
  explicit remember instruction or a "remember that" phrase), capped at 1.
- **Fact confidence** (rule table): the evidence situation: direct, intended,
  conditional, possible (hedged); a reported claim is capped at the
  second-hand value; an unresolved reference costs a penalty. Extraction
  confidence is a separate number (6.2.3 AC-16).
- **Freshness** (class, no decay): stable, time-bound, historical or changing;
  ``observed_at`` is the source's own time, never invented (AC-10).
- **Long-term utility** and **contextual significance**: simple considered
  signals (durable categories; corrections and facts sharing a subject).
- **Uncertainty**: HEDGED, CONDITIONAL, REPORTED, UNRESOLVED_REFERENCE,
  CONFLICT (contradicting facts in the same source, kept for resolution,
  AC-11) and REPEATED (a repetition adds no evidence, AC-09).

Outcome policy: reject what extraction rejected or what falls below the
importance floor without a remember request; review what extraction sent to
review or what has low fact confidence; ``defer`` is not used (no
re-evaluation mechanism exists). Otherwise proceed.

Origin (6.2.5): a proposal with derived evidence is ``inferred`` (no step
derives inferences yet); one with an unresolved reference or no subject is
``unresolved`` and needs review; every other direct statement is ``explicit``,
with the reason saying whether it is about the user, a third party, a
reported claim or a remember request. Subjects and attribution are kept as
extracted, so third-party facts are never assigned to the user (AC-05).
"""

import re
from collections.abc import Sequence
from typing import Protocol

from memory_engine.config.settings import EvaluationSettings
from memory_engine.domain.vocabulary import (
    CandidateOrigin,
    EvaluationOutcome,
    FactModality,
    FreshnessClass,
    InstructionType,
    ProposalStatus,
)
from memory_engine.personal.application.extraction import PipelineResult, SourceContent
from memory_engine.personal.application.facts import FactExtraction
from memory_engine.personal.domain import FactProposal
from memory_engine.personal.domain.evaluation import (
    EvaluatedProposal,
    OriginClassification,
    ProposalEvaluation,
)

METHOD = "evaluation_rules"
METHOD_VERSION = "1"
CLASSIFICATION_METHOD = "origin_rules"

# Importance categories, in priority order.
GOAL = "GOAL"
COMMITMENT = "COMMITMENT"
DECISION = "DECISION"
RELATIONSHIP = "RELATIONSHIP"
HEALTH_IDENTITY = "HEALTH_IDENTITY"
PREFERENCE = "PREFERENCE"
HABIT = "HABIT"
EVENT = "EVENT"
OTHER = "OTHER"
_DURABLE = frozenset({GOAL, COMMITMENT, DECISION, RELATIONSHIP, HEALTH_IDENTITY, PREFERENCE, HABIT})

_RELATION_NOUNS = frozenset(
    [
        "sister",
        "brother",
        "mother",
        "father",
        "mom",
        "mum",
        "dad",
        "parent",
        "parents",
        "wife",
        "husband",
        "partner",
        "boyfriend",
        "girlfriend",
        "friend",
        "friends",
        "son",
        "daughter",
        "child",
        "children",
        "kid",
        "kids",
        "cousin",
        "uncle",
        "aunt",
        "grandmother",
        "grandfather",
        "grandma",
        "grandpa",
        "boss",
        "manager",
        "colleague",
        "colleagues",
        "coworker",
        "neighbour",
        "neighbor",
        "roommate",
        "fiance",
        "fiancee",
        "family",
    ]
)
_HEALTH_IDENTITY_WORDS = frozenset(
    [
        "allergic",
        "allergy",
        "allergies",
        "diabetic",
        "diabetes",
        "vegetarian",
        "vegan",
        "pregnant",
        "born",
        "birthday",
        "anniversary",
        "name",
        "nationality",
        "citizen",
        "religion",
        "asthma",
        "gluten",
        "lactose",
        "disability",
        "medication",
        "intolerant",
    ]
)
_IDENTITY_PREDICATES = frozenset({"work", "study", "live"})
_GOAL_LEMMAS = frozenset({"want", "aim", "hope", "plan", "intend", "wish", "dream"})
_GOAL_WORDS = frozenset({"goal", "goals", "dream", "ambition", "objective", "plan"})
_COMMITMENT_PREFIXES = ("have to", "need to", "promise", "commit", "agree to")
_COMMITMENT_WORDS = frozenset({"deadline", "appointment", "meeting", "exam", "interview", "due"})
_DECISION_LEMMAS = frozenset({"decide", "choose", "opt", "pick", "settle"})
_PREFERENCE_LEMMAS = frozenset(
    {"prefer", "like", "love", "hate", "dislike", "enjoy", "adore", "favor", "favour"}
)
_PREFERENCE_WORDS = frozenset({"favourite", "favorite"})
_HABIT_WORDS = frozenset(
    {"usually", "always", "often", "every", "daily", "weekly", "monthly", "each", "regularly"}
)
_EVENT_LEMMAS = frozenset(
    {"move", "travel", "visit", "buy", "start", "graduate", "marry", "relocate", "attend", "meet"}
)
_REMEMBER = re.compile(
    r"\b(remember that|please remember|remember:|don't forget|do not forget|keep in mind|"
    r"note that|for the record)\b"
)
_WORD = re.compile(r"[a-z']+")


class CandidateStage(Protocol):
    """Candidate generation and validation (6.2.6, step 5)."""

    def generate(
        self,
        content: SourceContent,
        extraction: FactExtraction,
        evaluated: Sequence[EvaluatedProposal],
    ) -> PipelineResult: ...


def _words(*texts: str | None) -> set[str]:
    return {w for text in texts if text for w in _WORD.findall(text.lower())}


def about_user(subject: str | None) -> bool:
    """'the user', 'the user's goal', 'the user and others' are the user; 'the user's
    sister' is someone else (6.2.5 rule 4)."""
    if subject is None or not subject.lower().startswith("the user"):
        return False
    return not (_words(subject) & _RELATION_NOUNS)


def _lemma(proposal: FactProposal) -> str:
    return (proposal.predicate or "").split(" ")[0]


def category(proposal: FactProposal) -> str:
    """The first importance category whose rule matches (also used by step 5)."""
    predicate = proposal.predicate or ""
    lemma = _lemma(proposal)
    subject_words = _words(proposal.subject)
    all_words = _words(proposal.subject, proposal.object, *proposal.attributes)
    if lemma in _GOAL_LEMMAS or subject_words & _GOAL_WORDS:
        return GOAL
    if predicate.startswith(_COMMITMENT_PREFIXES) or all_words & _COMMITMENT_WORDS:
        return COMMITMENT
    if lemma in _DECISION_LEMMAS:
        return DECISION
    if subject_words & _RELATION_NOUNS:
        return RELATIONSHIP
    if all_words & _HEALTH_IDENTITY_WORDS or lemma in _IDENTITY_PREDICATES:
        return HEALTH_IDENTITY
    if lemma == "be" and about_user(proposal.subject) and proposal.object:
        return HEALTH_IDENTITY  # "the user is a software engineering student"
    if lemma in _PREFERENCE_LEMMAS or all_words & _PREFERENCE_WORDS:
        return PREFERENCE
    if _words(proposal.proposition) & _HABIT_WORDS:
        return HABIT
    if lemma in _EVENT_LEMMAS or proposal.past:
        return EVENT
    return OTHER


def _freshness(proposal: FactProposal, kind: str) -> FreshnessClass:
    words = _words(proposal.subject, proposal.object, *proposal.attributes)
    if kind == RELATIONSHIP or (kind == HEALTH_IDENTITY and words & _HEALTH_IDENTITY_WORDS):
        return FreshnessClass.STABLE
    if proposal.temporal and kind != HABIT:
        return FreshnessClass.TIME_BOUND
    if proposal.past and kind in (EVENT, OTHER):
        return FreshnessClass.HISTORICAL
    return FreshnessClass.CHANGING


def _remember(content: SourceContent, proposal: FactProposal) -> bool:
    return content.source.instruction_type is InstructionType.REMEMBER or bool(
        _REMEMBER.search(proposal.original_text.lower())
    )


def _key(p: FactProposal) -> tuple[str | None, str | None, str | None]:
    return ((p.subject or "").lower() or None, p.predicate, (p.object or "").lower() or None)


class ProposalEvaluator:
    def __init__(self, settings: EvaluationSettings) -> None:
        self._s = settings

    def evaluate(
        self, content: SourceContent, proposals: Sequence[FactProposal]
    ) -> list[EvaluatedProposal]:
        conflicting = self._conflicts(proposals)
        seen: set[tuple[object, ...]] = set()
        subjects = [(p.subject or "").lower() for p in proposals]
        results = []
        for index, proposal in enumerate(proposals):
            identity = (*_key(proposal), proposal.negated, proposal.modality)
            repeated = identity in seen and proposal.predicate is not None
            seen.add(identity)
            shares_subject = bool(proposal.subject) and subjects.count(subjects[index]) > 1
            evaluation = self._evaluation(
                content, proposal, index in conflicting, repeated, shares_subject
            )
            results.append(
                EvaluatedProposal(
                    proposal=proposal,
                    evaluation=evaluation,
                    classification=self._classification(content, proposal),
                )
            )
        return results

    @staticmethod
    def _conflicts(proposals: Sequence[FactProposal]) -> set[int]:
        """Proposals in one source that assert and deny the same thing (6.2.4 AC-11)."""
        found: set[int] = set()
        for i, a in enumerate(proposals):
            for j in range(i + 1, len(proposals)):
                b = proposals[j]
                if a.predicate and _key(a) == _key(b) and a.negated != b.negated:
                    found |= {i, j}
        return found

    def _importance(self, kind: str, remember: bool) -> float:
        s = self._s
        table = {
            GOAL: s.importance_goal,
            COMMITMENT: s.importance_commitment,
            DECISION: s.importance_decision,
            RELATIONSHIP: s.importance_relationship,
            HEALTH_IDENTITY: s.importance_health_identity,
            PREFERENCE: s.importance_preference,
            HABIT: s.importance_habit,
            EVENT: s.importance_event,
            OTHER: s.importance_other,
        }
        return round(min(1.0, table[kind] + (s.remember_bonus if remember else 0.0)), 4)

    def _fact_confidence(self, proposal: FactProposal) -> tuple[float, str, list[str]]:
        s = self._s
        by_modality = {
            FactModality.FACTUAL: (s.confidence_direct, "DIRECT", None),
            FactModality.INTENDED: (s.confidence_intended, "INTENDED", None),
            FactModality.CONDITIONAL: (s.confidence_conditional, "CONDITIONAL", "CONDITIONAL"),
            FactModality.POSSIBLE: (s.confidence_possible, "POSSIBLE", "HEDGED"),
        }
        value, basis, flag = by_modality[proposal.modality]
        uncertainty = [flag] if flag else []
        if proposal.attributed_to:
            value, basis = min(value, s.confidence_reported), "REPORTED"
            uncertainty.append("REPORTED")
        if proposal.unresolved_references:
            value -= s.unresolved_penalty
            uncertainty.append("UNRESOLVED_REFERENCE")
        return round(max(0.0, value), 4), basis, uncertainty

    def _evaluation(
        self,
        content: SourceContent,
        proposal: FactProposal,
        conflict: bool,
        repeated: bool,
        shares_subject: bool,
    ) -> ProposalEvaluation:
        kind = category(proposal)
        remember = _remember(content, proposal)
        importance = self._importance(kind, remember)
        confidence, basis, uncertainty = self._fact_confidence(proposal)
        if conflict:
            uncertainty.append("CONFLICT")
        if repeated:
            uncertainty.append("REPEATED")
        outcome, reason = self._outcome(proposal, importance, confidence, remember)
        return ProposalEvaluation(
            category=kind,
            importance=importance,
            fact_confidence=confidence,
            confidence_basis=basis,
            freshness=_freshness(proposal, kind),
            observed_at=proposal.temporal_reference,
            long_term_utility=1.0 if kind in _DURABLE else 0.5 if kind == EVENT else 0.2,
            contextual_significance=1.0 if proposal.correction else 0.6 if shares_subject else 0.3,
            uncertainty=tuple(uncertainty),
            outcome=outcome,
            reason_code=reason,
            method=METHOD,
            method_version=METHOD_VERSION,
        )

    def _outcome(
        self, proposal: FactProposal, importance: float, confidence: float, remember: bool
    ) -> tuple[EvaluationOutcome, str | None]:
        if proposal.status is ProposalStatus.REJECTED:
            return EvaluationOutcome.REJECT, "EXTRACTION_REJECTED"
        if importance < self._s.reject_importance and not remember:
            return EvaluationOutcome.REJECT, "LOW_IMPORTANCE"
        if proposal.status is ProposalStatus.NEEDS_REVIEW:
            return EvaluationOutcome.NEEDS_REVIEW, proposal.reason_code
        if confidence < self._s.review_fact_confidence:
            return EvaluationOutcome.NEEDS_REVIEW, "LOW_FACT_CONFIDENCE"
        return EvaluationOutcome.PROCEED, None

    def _classification(
        self, content: SourceContent, proposal: FactProposal
    ) -> OriginClassification:
        evidence = proposal.derived_from or ((proposal.segment, proposal.sentence),)
        confidence = proposal.extraction_confidence
        if proposal.derived_from:
            origin, reason = CandidateOrigin.INFERRED, "DERIVED_FROM_EVIDENCE"
            review = confidence < self._s.review_fact_confidence
        elif proposal.unresolved_references:
            origin, reason, review = CandidateOrigin.UNRESOLVED, "UNRESOLVED_REFERENCE", True
            confidence *= 0.5
        elif proposal.subject is None:
            origin, reason, review = CandidateOrigin.UNRESOLVED, "NO_SUBJECT", True
            confidence *= 0.5
        else:
            origin, review = CandidateOrigin.EXPLICIT, False
            if _remember(content, proposal) and about_user(proposal.subject):
                reason = "REMEMBER_INSTRUCTION"
            elif proposal.attributed_to:
                reason = "REPORTED_STATEMENT"
            elif not about_user(proposal.subject):
                reason = "THIRD_PARTY_STATEMENT"
            else:
                reason = "DIRECT_USER_STATEMENT"
        return OriginClassification(
            origin=origin,
            confidence=round(confidence, 4),
            reason_code=reason,
            evidence=tuple(evidence),
            speaker=proposal.speaker,
            subject=proposal.subject,
            needs_review=review,
            method=CLASSIFICATION_METHOD,
            method_version=METHOD_VERSION,
        )


class EvaluationStage:
    """The pipeline stage after fact extraction: evaluate and classify, then step 5."""

    def __init__(self, evaluator: ProposalEvaluator, downstream: CandidateStage) -> None:
        self._evaluator = evaluator
        self._downstream = downstream

    def evaluate(self, content: SourceContent, extraction: FactExtraction) -> PipelineResult:
        evaluated = self._evaluator.evaluate(content, extraction.proposals)
        return self._downstream.generate(content, extraction, evaluated)
