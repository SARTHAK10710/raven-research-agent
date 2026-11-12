"""Atomic fact proposals (6.2.3 section 5.6; 5.4 Phase 8.4 amendment section 18).

A :class:`FactProposal` lives only inside one extraction run: evaluation
(6.2.4-6.2.5) and candidate generation (6.2.6) consume it, and only a Memory
Candidate is persisted, carrying the proposal's structure in its JSON fields
(owner decision, 8.4 step 3). A proposal is never an active memory.
"""

import math
import re
import uuid
from dataclasses import dataclass
from typing import Any

from memory_engine.domain.errors import DomainValidationError
from memory_engine.domain.vocabulary import FactModality, ProposalStatus

_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")


def _codes(name: str, values: tuple[str, ...]) -> None:
    for value in values:
        if not _CODE.fullmatch(value):
            raise DomainValidationError(f"{name} must be UPPER_SNAKE_CASE codes")


@dataclass(frozen=True, slots=True, kw_only=True)
class FactProposal:
    """One independently meaningful proposition, with its evidence and structure.

    ``segment`` and ``sentence`` locate the supporting text in the source;
    ``original_text`` is that sentence exactly. ``proposition`` restates the
    clause in the third person ("The user prefers window seats.") and keeps any
    condition. ``subject``, ``predicate`` and ``object`` are absent when the
    parse did not identify them. ``temporal`` keeps the original expressions;
    ``temporal_reference`` is the moment they are relative to (6.2.3 AC-11: no
    absolute date is invented). ``speaker`` wrote the text; ``attributed_to``
    is set when the user reports someone else's statement (AC-14).
    """

    id: uuid.UUID
    owner_id: uuid.UUID
    source_id: uuid.UUID
    segment: int
    sentence: int
    original_text: str
    proposition: str
    modality: FactModality
    speaker: str
    extraction_confidence: float
    status: ProposalStatus
    method: str
    method_version: str
    subject: str | None = None
    predicate: str | None = None
    object: str | None = None
    attributes: tuple[str, ...] = ()
    negated: bool = False
    conditions: tuple[str, ...] = ()
    temporal: tuple[str, ...] = ()
    temporal_reference: str | None = None
    quantities: tuple[str, ...] = ()
    attributed_to: str | None = None
    correction: bool = False
    unresolved_references: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if self.segment < 0 or self.sentence < 0:
            raise DomainValidationError("proposal positions must not be negative")
        for name in ("original_text", "proposition", "speaker", "method", "method_version"):
            if not getattr(self, name).strip():
                raise DomainValidationError(f"{name} is required")
        value = self.extraction_confidence
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise DomainValidationError("extraction_confidence must be within [0, 1]")
        if (self.status is ProposalStatus.EXTRACTED) != (self.reason_code is None):
            raise DomainValidationError("review and rejection need a reason; extraction none")
        if self.reason_code is not None and not _CODE.fullmatch(self.reason_code):
            raise DomainValidationError("reason_code must be an UPPER_SNAKE_CASE code")
        if self.unresolved_references and self.status is ProposalStatus.EXTRACTED:
            raise DomainValidationError("an unresolved reference is never extracted as is")
        if self.conditions and self.modality is not FactModality.CONDITIONAL:
            raise DomainValidationError("a proposal with conditions is conditional")
        _codes("weaknesses", self.weaknesses)

    def structure(self) -> dict[str, Any]:
        """The structured part, as stored with the candidate (step 5)."""
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "attributes": list(self.attributes),
            "modality": self.modality.value,
            "negated": self.negated,
            "conditions": list(self.conditions),
            "quantities": list(self.quantities),
            "speaker": self.speaker,
            "attributed_to": self.attributed_to,
            "correction": self.correction,
            "unresolved_references": list(self.unresolved_references),
        }
