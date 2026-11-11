"""Processing, evaluation, correction and deletion records (Phase 8.2 step 5).

History and workflow records around the core Personal Memory records
(Decisions 5.4.24-5.4.26 and 5.4.28; 6.5.8-6.5.9). Sources for the
vocabularies: 5.4 Phase 8.2 amendment section 14.

Rules checked here, without a database:

* Every processing event changes the source status, and only failures carry
  an error code.
* An evaluation's outcome limits the candidate status it can leave behind
  (``reject`` -> ``rejected``, ``defer`` -> ``candidate`` ...).
* A correction request is resolved exactly when it has a resolution time, and a
  ``deleted`` one keeps no proposed content (5.4.24 rule 7).
* A deletion operation is finished exactly when it has a finish time; ledger
  rows hold identifiers only, never content.
* Error and reason codes are UPPER_SNAKE_CASE codes, never free text, so they
  cannot carry user content.
"""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any

from memory_engine.domain.errors import DomainValidationError
from memory_engine.domain.vocabulary import (
    CandidateStatus,
    CorrectionStatus,
    DeletionAction,
    DeletionOperationStatus,
    DeletionRequestKind,
    DeletionTargetKind,
    DeletionTargetState,
    EvaluationOutcome,
    ProcessingEventType,
    SourceProcessingStatus,
)

JsonMap = Mapping[str, Any]
_SAFE_CODE_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")


def _empty() -> JsonMap:
    return MappingProxyType({})


def _require_text(name: str, value: str) -> None:
    if not value.strip():
        raise DomainValidationError(f"{name} must not be empty")


def _require_aware(name: str, value: datetime | None) -> None:
    if value is not None and value.utcoffset() is None:
        raise DomainValidationError(f"{name} must be timezone-aware")


def _require_score(name: str, value: float | None) -> None:
    if value is not None and not 0.0 <= value <= 1.0:
        raise DomainValidationError(f"{name} must be between 0 and 1")


def _require_code(name: str, value: str | None) -> None:
    if value is not None and (
        not value or not value[0].isalpha() or set(value) - _SAFE_CODE_CHARS or len(value) > 64
    ):
        raise DomainValidationError(f"{name} must be an UPPER_SNAKE_CASE code")


def _require_not_before(start: datetime, end: datetime | None, name: str) -> None:
    _require_aware(name, end)
    if end is not None and end < start:
        raise DomainValidationError(f"{name} must not be earlier than when the record started")


# --- source processing and candidate evaluation ---------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceProcessingEvent:
    """A meaningful Memory Source processing transition (Decision 5.4.28)."""

    id: uuid.UUID
    owner_id: uuid.UUID
    source_id: uuid.UUID
    event_type: ProcessingEventType
    from_status: SourceProcessingStatus
    to_status: SourceProcessingStatus
    attempt: int
    occurred_at: datetime
    error_code: str | None = None
    reason_code: str | None = None

    def __post_init__(self) -> None:
        _require_aware("occurred_at", self.occurred_at)
        if self.from_status is self.to_status:
            raise DomainValidationError("a processing event changes the source status")
        if self.attempt < 1:
            raise DomainValidationError("attempt starts at 1")
        if (self.event_type is ProcessingEventType.FAILURE) != (self.error_code is not None):
            raise DomainValidationError("an error_code is required exactly for failures")
        _require_code("error_code", self.error_code)
        if self.to_status.needs_reason != (self.reason_code is not None):
            raise DomainValidationError(
                "a reason_code is required exactly for deferral and rejection"
            )
        _require_code("reason_code", self.reason_code)


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateEvaluation:
    """One material evaluation of a Memory Candidate, kept as history (Decision 5.4.25).

    Holds outcomes, scores and a reason code; never the proposition itself.
    """

    id: uuid.UUID
    owner_id: uuid.UUID
    candidate_id: uuid.UUID
    outcome: EvaluationOutcome
    from_status: CandidateStatus
    to_status: CandidateStatus
    method: str
    method_version: str
    evaluated_at: datetime
    importance: float | None = None
    confidence: float | None = None
    reason_code: str | None = None

    def __post_init__(self) -> None:
        _require_text("method", self.method)
        _require_text("method_version", self.method_version)
        _require_aware("evaluated_at", self.evaluated_at)
        if self.to_status not in self.outcome.allowed_statuses():
            raise DomainValidationError(
                f"outcome '{self.outcome}' cannot leave a candidate '{self.to_status}'"
            )
        _require_score("importance", self.importance)
        _require_score("confidence", self.confidence)
        _require_code("reason_code", self.reason_code)


# --- corrections -----------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class CorrectionRequest:
    """A complex correction awaiting or after review (Decision 5.4.26 rules 2-3, 7).

    Simple corrections are a new Atomic Memory revision and need no request.
    """

    id: uuid.UUID
    owner_id: uuid.UUID
    status: CorrectionStatus
    requested_at: datetime
    proposed_change: JsonMap | None
    evidence: JsonMap = field(default_factory=_empty)
    resolution_note: str | None = None
    resolved_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_aware("requested_at", self.requested_at)
        _require_not_before(self.requested_at, self.resolved_at, "resolved_at")
        if self.status is CorrectionStatus.DELETED:
            if self.proposed_change is not None or self.evidence or self.resolution_note:
                raise DomainValidationError("a deleted correction request keeps no content")
        else:
            if not self.proposed_change:
                raise DomainValidationError("a correction request proposes a change")
            object.__setattr__(
                self, "proposed_change", MappingProxyType(dict(self.proposed_change))
            )
        if self.status is CorrectionStatus.OPEN and (
            self.resolved_at is not None or self.resolution_note is not None
        ):
            raise DomainValidationError("an open correction request is not resolved")
        if self.status.resolved and self.resolved_at is None:
            raise DomainValidationError("a resolved correction request records when")
        if self.resolution_note is not None:
            _require_text("resolution_note", self.resolution_note)
        object.__setattr__(self, "evidence", MappingProxyType(dict(self.evidence)))


@dataclass(frozen=True, slots=True, kw_only=True)
class CorrectionTarget:
    """A memory a correction request affects (Decision 5.4.26 rule 3).

    ``base_revision_number`` is the revision the request was made against;
    ``applied_revision_number`` the revision that applied it once accepted.
    """

    memory_id: uuid.UUID
    base_revision_number: int
    applied_revision_number: int | None = None

    def __post_init__(self) -> None:
        if self.base_revision_number < 1:
            raise DomainValidationError("base_revision_number starts at 1")
        if (
            self.applied_revision_number is not None
            and self.applied_revision_number <= self.base_revision_number
        ):
            raise DomainValidationError("a correction is applied by a later revision")


# --- deletion ------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class DeletionOperation:
    """A coordinated Memory Deletion Operation (Decision 5.4.24; 6.5.8).

    Holds no content (5.4.24 rule 7). Its ledger rows (:class:`DeletionTarget`)
    name the affected records by identifier.
    """

    id: uuid.UUID
    owner_id: uuid.UUID
    request_kind: DeletionRequestKind
    status: DeletionOperationStatus
    idempotency_key: str
    requested_at: datetime
    finished_at: datetime | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        _require_text("idempotency_key", self.idempotency_key)
        if len(self.idempotency_key) > 200:
            raise DomainValidationError("idempotency_key is too long")
        _require_aware("requested_at", self.requested_at)
        _require_not_before(self.requested_at, self.finished_at, "finished_at")
        if self.status.finished != (self.finished_at is not None):
            raise DomainValidationError("finished_at is required exactly when finished")
        if self.status is DeletionOperationStatus.FAILED and self.error_code is None:
            raise DomainValidationError("a failed deletion records an error_code")
        if self.status is DeletionOperationStatus.COMPLETED and self.error_code is not None:
            raise DomainValidationError("a completed deletion has no error_code")
        _require_code("error_code", self.error_code)


@dataclass(frozen=True, slots=True, kw_only=True)
class DeletionTarget:
    """One ledger row: a record the deletion must handle, and its progress (6.5.9).

    ``direct`` marks records named by the request, as opposed to dependencies
    found while building the inventory. The ledger keeps identifiers after the
    record itself is purged, so deletions can be reapplied after a restore.
    """

    target_kind: DeletionTargetKind
    target_id: uuid.UUID
    action: DeletionAction
    direct: bool
    state: DeletionTargetState = DeletionTargetState.PENDING
    attempts: int = 0
    error_code: str | None = None

    def __post_init__(self) -> None:
        if self.attempts < 0:
            raise DomainValidationError("attempts must not be negative")
        if (self.state is DeletionTargetState.FAILED) != (self.error_code is not None):
            raise DomainValidationError("an error_code is required exactly for failed targets")
        _require_code("error_code", self.error_code)
