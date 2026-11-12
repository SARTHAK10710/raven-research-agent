"""Relevance gate decisions (6.2.2; 5.4 Phase 8.4 amendment section 17).

One :class:`RelevanceAssessment` per extraction run of a Memory Source: the
rolled-up outcome with its reason, the method and version that produced it,
and one :class:`UnitAssessment` per judged sentence. Units hold positions,
outcomes, codes and scores only; never the text (7.7 section 18).
"""

import math
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any

from memory_engine.domain.errors import DomainValidationError
from memory_engine.domain.vocabulary import RelevanceOutcome

_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
_SIGNAL = re.compile(r"[a-z][a-z0-9_]{0,39}")


def _check_score(name: str, value: float | None) -> None:
    if value is not None and (not math.isfinite(value) or not 0.0 <= value <= 1.0):
        raise DomainValidationError(f"{name} must be within [0, 1]")


@dataclass(frozen=True, slots=True, kw_only=True)
class UnitAssessment:
    """The decision on one sentence: ``segment`` is the message position, ``sentence``
    the sentence index inside it.

    ``signals`` maps signal names to values in [0, 1]; a signal that could not
    be evaluated is absent, never zero (6.2.2 AC-07). ``protection`` names the
    protection rule that forced processing, if any. A ``process`` unit may carry
    a reason only when it is a protection code.
    """

    segment: int
    sentence: int
    outcome: RelevanceOutcome
    reason_code: str | None = None
    score: float | None = None
    signals: Mapping[str, float] = field(default_factory=dict)
    protection: str | None = None

    def __post_init__(self) -> None:
        if self.segment < 0 or self.sentence < 0:
            raise DomainValidationError("unit positions must not be negative")
        if self.outcome is RelevanceOutcome.PROCESS:
            if self.reason_code is not None:
                raise DomainValidationError("a processed unit has no rejection reason")
        elif self.reason_code is None or not _CODE.fullmatch(self.reason_code):
            raise DomainValidationError("deferred and rejected units need a reason code")
        if self.protection is not None and not _CODE.fullmatch(self.protection):
            raise DomainValidationError("protection must be an UPPER_SNAKE_CASE code")
        _check_score("score", self.score)
        for name, value in self.signals.items():
            if not _SIGNAL.fullmatch(name):
                raise DomainValidationError("signal names are lowercase identifiers")
            _check_score(f"signal {name}", value)
        object.__setattr__(self, "signals", MappingProxyType(dict(self.signals)))

    def to_json(self) -> dict[str, Any]:
        return {
            "segment": self.segment,
            "sentence": self.sentence,
            "outcome": self.outcome.value,
            "reason_code": self.reason_code,
            "score": self.score,
            "signals": dict(self.signals),
            "protection": self.protection,
        }

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> "UnitAssessment":
        return cls(
            segment=int(data["segment"]),
            sentence=int(data["sentence"]),
            outcome=RelevanceOutcome(data["outcome"]),
            reason_code=data.get("reason_code"),
            score=data.get("score"),
            signals=dict(data.get("signals") or {}),
            protection=data.get("protection"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class RelevanceAssessment:
    """The gate's decision for one extraction run of a Memory Source (6.2.2 step 8)."""

    id: uuid.UUID
    owner_id: uuid.UUID
    source_id: uuid.UUID
    outcome: RelevanceOutcome
    method: str
    method_version: str
    assessed_at: datetime
    units: Sequence[UnitAssessment]
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if self.outcome is RelevanceOutcome.PROCESS:
            if self.reason_code is not None:
                raise DomainValidationError("a processed source has no rejection reason")
        elif self.reason_code is None or not _CODE.fullmatch(self.reason_code):
            raise DomainValidationError("deferred and rejected sources need a reason code")
        if not self.method.strip() or not self.method_version.strip():
            raise DomainValidationError("method and method_version are required")
        if self.assessed_at.utcoffset() is None:
            raise DomainValidationError("assessed_at must be timezone-aware")
        units = tuple(self.units)
        positions = [(u.segment, u.sentence) for u in units]
        if len(set(positions)) != len(positions):
            raise DomainValidationError("each unit is assessed once")
        outcomes = {u.outcome for u in units}
        if (RelevanceOutcome.PROCESS in outcomes) != (self.outcome is RelevanceOutcome.PROCESS):
            raise DomainValidationError("a source is processed exactly when a unit is")
        object.__setattr__(self, "units", units)

    @property
    def processed(self) -> tuple[UnitAssessment, ...]:
        return tuple(u for u in self.units if u.outcome is RelevanceOutcome.PROCESS)
