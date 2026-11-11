"""Derived knowledge and memory metadata (Phase 8.2 step 4).

Episodes, profiles, category assignments and memory embedding metadata. All are
derived from, or describe, Atomic Memories; none of them is authoritative
(Decisions 5.4.16-5.4.23, 5.4.29-5.4.32; 6.5.4, 6.5.6). Sources for the
vocabularies: 5.4 Phase 8.2 amendment section 13.

Rules checked here, without a database:

* A time whose precision is ``unknown`` has no value, and a known one does
  (5.4.30: unknown dates are never fabricated).
* A refresh outcome decides whether a new profile revision exists and which
  status the profile ends in; a partial or failed refresh never leaves a
  profile ``current`` (6.5.6).
* An ``aspect`` embedding names its aspect; a ``primary`` one does not.
"""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any

from memory_engine.domain.errors import DomainValidationError
from memory_engine.domain.vocabulary import (
    EmbeddingPurpose,
    EmbeddingStatus,
    EpisodeStatus,
    MemoryCategory,
    MemoryOrigin,
    ProfileStatus,
    ProfileType,
    RefreshOutcome,
    RefreshTrigger,
    TemporalPrecision,
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


def _require_precise(name: str, value: datetime | None, precision: TemporalPrecision) -> None:
    _require_aware(name, value)
    if (precision is TemporalPrecision.UNKNOWN) != (value is None):
        raise DomainValidationError(f"{name} is required exactly when its precision is known")


def _require_closed_after(opened: datetime, closed: datetime | None, name: str) -> None:
    _require_aware(name, closed)
    if closed is not None and closed < opened:
        raise DomainValidationError(f"{name} must not be earlier than when the record started")


# --- episodes ------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class Episode:
    """A derived grouping of related memories with temporal boundaries (5.4.16, 5.4.30)."""

    id: uuid.UUID
    owner_id: uuid.UUID
    status: EpisodeStatus
    method: str
    method_version: str
    recorded_at: datetime
    title: str | None = None
    summary: str | None = None
    starts_at: datetime | None = None
    start_precision: TemporalPrecision = TemporalPrecision.UNKNOWN
    ends_at: datetime | None = None
    end_precision: TemporalPrecision = TemporalPrecision.UNKNOWN

    def __post_init__(self) -> None:
        _require_text("method", self.method)
        _require_text("method_version", self.method_version)
        _require_aware("recorded_at", self.recorded_at)
        for name, value in (("title", self.title), ("summary", self.summary)):
            if value is not None:
                _require_text(name, value)
        _require_precise("starts_at", self.starts_at, self.start_precision)
        _require_precise("ends_at", self.ends_at, self.end_precision)
        if self.starts_at and self.ends_at and self.ends_at < self.starts_at:
            raise DomainValidationError("an episode cannot end before it starts")


@dataclass(frozen=True, slots=True, kw_only=True)
class EpisodeMembership:
    """One memory's membership in an episode (5.4.29). Removal closes it, never deletes."""

    id: uuid.UUID
    owner_id: uuid.UUID
    episode_id: uuid.UUID
    memory_id: uuid.UUID
    added_at: datetime
    sequence: int | None = None
    confidence: float | None = None
    removed_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_aware("added_at", self.added_at)
        _require_closed_after(self.added_at, self.removed_at, "removed_at")
        if self.sequence is not None and self.sequence < 0:
            raise DomainValidationError("sequence must not be negative")
        _require_score("confidence", self.confidence)


@dataclass(frozen=True, slots=True, kw_only=True)
class EpisodeEvent:
    """A timeline milestone (5.4.30). Corrections add a row and close the old one."""

    id: uuid.UUID
    owner_id: uuid.UUID
    episode_id: uuid.UUID
    label: str
    precision: TemporalPrecision
    recorded_at: datetime
    occurred_at: datetime | None = None
    memory_id: uuid.UUID | None = None
    superseded_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_text("label", self.label)
        _require_aware("recorded_at", self.recorded_at)
        _require_precise("occurred_at", self.occurred_at, self.precision)
        _require_closed_after(self.recorded_at, self.superseded_at, "superseded_at")


# --- profiles ------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class Profile:
    """Current state of a Derived Profile (5.4.17, 5.4.32).

    The content lives in immutable :class:`ProfileRevision` records;
    ``revision_number`` names the current one.
    """

    id: uuid.UUID
    owner_id: uuid.UUID
    profile_type: ProfileType
    status: ProfileStatus
    revision_number: int
    refreshed_at: datetime
    subject_entity_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        if self.revision_number < 1:
            raise DomainValidationError("revision_number starts at 1")
        _require_aware("refreshed_at", self.refreshed_at)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfileSupport:
    """A memory (at a specific revision) that supports a profile revision (5.4.31)."""

    memory_id: uuid.UUID
    memory_revision_number: int
    attribute: str | None = None
    relevance: float | None = None

    def __post_init__(self) -> None:
        if self.memory_revision_number < 1:
            raise DomainValidationError("memory_revision_number starts at 1")
        if self.attribute is not None:
            _require_text("attribute", self.attribute)
        _require_score("relevance", self.relevance)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfileRevision:
    """Immutable profile content and the exact memory revisions it was built from.

    Recording memory revisions makes a profile reproducible (6.5.6) and lets a
    refresh find which sources changed.
    """

    id: uuid.UUID
    owner_id: uuid.UUID
    profile_id: uuid.UUID
    revision_number: int
    method: str
    method_version: str
    recorded_at: datetime
    attributes: JsonMap = field(default_factory=_empty)
    supports: tuple[ProfileSupport, ...] = ()

    def __post_init__(self) -> None:
        if self.revision_number < 1:
            raise DomainValidationError("revision_number starts at 1")
        _require_text("method", self.method)
        _require_text("method_version", self.method_version)
        _require_aware("recorded_at", self.recorded_at)
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))
        object.__setattr__(self, "supports", tuple(self.supports))


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfileRefresh:
    """One meaningful refresh event, kept as history (Decision 5.4.32)."""

    id: uuid.UUID
    owner_id: uuid.UUID
    profile_id: uuid.UUID
    trigger: RefreshTrigger
    outcome: RefreshOutcome
    from_revision: int
    recorded_at: datetime
    to_revision: int | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        _require_aware("recorded_at", self.recorded_at)
        if self.outcome.creates_revision != (self.to_revision is not None):
            raise DomainValidationError(f"outcome '{self.outcome}' and to_revision disagree")
        if self.to_revision is not None and self.to_revision != self.from_revision + 1:
            raise DomainValidationError("a refresh creates exactly the next revision")
        if (self.outcome is RefreshOutcome.FAILED) != (self.error_code is not None):
            raise DomainValidationError("an error_code is required exactly when a refresh failed")
        if self.error_code is not None and (
            not self.error_code
            or not self.error_code[0].isalpha()
            or set(self.error_code) - _SAFE_CODE_CHARS
            or len(self.error_code) > 64
        ):
            raise DomainValidationError("error_code must be an UPPER_SNAKE_CASE code")


# --- categories and memory embeddings -------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class CategoryAssignment:
    """A memory's category (5.4.9, 5.4.22). Changes close the old row, never overwrite."""

    id: uuid.UUID
    owner_id: uuid.UUID
    memory_id: uuid.UUID
    category: MemoryCategory
    origin: MemoryOrigin
    recorded_at: datetime
    confidence: float | None = None
    superseded_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_aware("recorded_at", self.recorded_at)
        _require_closed_after(self.recorded_at, self.superseded_at, "superseded_at")
        _require_score("confidence", self.confidence)


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryEmbedding:
    """Embedding metadata for one memory revision (5.4.19-5.4.21). Vectors arrive in 8.7."""

    id: uuid.UUID
    owner_id: uuid.UUID
    memory_id: uuid.UUID
    revision_number: int
    purpose: EmbeddingPurpose
    model_id: str
    model_revision: str
    dimensions: int
    preprocessing_version: str
    status: EmbeddingStatus
    aspect_label: str | None = None

    def __post_init__(self) -> None:
        if self.revision_number < 1:
            raise DomainValidationError("revision_number starts at 1")
        if (self.purpose is EmbeddingPurpose.ASPECT) != (self.aspect_label is not None):
            raise DomainValidationError("aspect_label is required exactly for aspect embeddings")
        if self.aspect_label is not None:
            _require_text("aspect_label", self.aspect_label)
        for name in ("model_id", "model_revision", "preprocessing_version"):
            _require_text(name, getattr(self, name))
        if self.dimensions < 1:
            raise DomainValidationError("dimensions must be positive")
