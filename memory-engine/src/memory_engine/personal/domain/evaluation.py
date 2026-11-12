"""Evaluation and origin classification of fact proposals (6.2.4-6.2.5).

In memory only, like the proposals themselves (5.4 Phase 8.4 amendment
section 19): step 5 stores the outcome in ``pm_candidate_evaluation`` and the
rest on the candidate. Importance, fact confidence, freshness, utility and
contextual significance stay separate dimensions (6.2.4 AC-02 to AC-06).
"""

import math
import re
from dataclasses import dataclass

from memory_engine.domain.errors import DomainValidationError
from memory_engine.domain.vocabulary import CandidateOrigin, EvaluationOutcome, FreshnessClass
from memory_engine.personal.domain.facts import FactProposal

_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")


def _score(name: str, value: float) -> None:
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise DomainValidationError(f"{name} must be within [0, 1]")


def _code(name: str, value: str | None) -> None:
    if value is not None and not _CODE.fullmatch(value):
        raise DomainValidationError(f"{name} must be an UPPER_SNAKE_CASE code")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProposalEvaluation:
    """6.2.4 for one proposal. ``category`` is the importance rule that applied;
    ``uncertainty`` lists codes such as HEDGED, CONDITIONAL, REPORTED,
    UNRESOLVED_REFERENCE, CONFLICT, REPEATED (AC-07, AC-09, AC-11)."""

    category: str
    importance: float
    fact_confidence: float
    confidence_basis: str
    freshness: FreshnessClass
    observed_at: str | None
    long_term_utility: float
    contextual_significance: float
    outcome: EvaluationOutcome
    method: str
    method_version: str
    uncertainty: tuple[str, ...] = ()
    reason_code: str | None = None

    def __post_init__(self) -> None:
        for name in ("importance", "fact_confidence", "long_term_utility"):
            _score(name, getattr(self, name))
        _score("contextual_significance", self.contextual_significance)
        for name in ("category", "confidence_basis"):
            _code(name, getattr(self, name))
            if not getattr(self, name):
                raise DomainValidationError(f"{name} is required")
        _code("reason_code", self.reason_code)
        for code in self.uncertainty:
            _code("uncertainty", code)
        if (self.outcome is EvaluationOutcome.PROCEED) != (self.reason_code is None):
            raise DomainValidationError("review, rejection and deferral need a reason")
        if not self.method.strip() or not self.method_version.strip():
            raise DomainValidationError("method and method_version are required")


@dataclass(frozen=True, slots=True, kw_only=True)
class OriginClassification:
    """6.2.5 for one proposal: explicit, inferred or unresolved, with its evidence."""

    origin: CandidateOrigin
    confidence: float
    reason_code: str
    evidence: tuple[tuple[int, int], ...]  # (segment, sentence) locations
    speaker: str
    subject: str | None
    needs_review: bool
    method: str
    method_version: str

    def __post_init__(self) -> None:
        _score("confidence", self.confidence)
        _code("reason_code", self.reason_code)
        if not self.evidence:
            raise DomainValidationError("a classification keeps its evidence (6.2.5 AC-07)")
        if self.origin is CandidateOrigin.UNRESOLVED and not self.needs_review:
            raise DomainValidationError("an unresolved origin always needs review")


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluatedProposal:
    proposal: FactProposal
    evaluation: ProposalEvaluation
    classification: OriginClassification

    @property
    def outcome(self) -> EvaluationOutcome:
        """The combined processing decision for candidate generation (step 5)."""
        evaluation = self.evaluation.outcome
        if evaluation is EvaluationOutcome.PROCEED and self.classification.needs_review:
            return EvaluationOutcome.NEEDS_REVIEW
        return evaluation
