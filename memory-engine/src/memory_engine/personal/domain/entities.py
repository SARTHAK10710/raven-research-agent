"""Entities, mentions, resolution history and relationships (Phase 8.2 step 3).

Sources: Decisions 5.4.8, 5.4.12-5.4.15, 5.4.27, 5.4.33-5.4.34; the Phase 8.2
amendment sections 3-5 and 8; approved step-3 vocabularies (5.4 Phase 8.2
amendment section 12).

Rules enforced here, without a database:

* Shared entities are not permitted yet (Decision 11).
* A merged entity names its survivor; nothing merges into itself.
* Symmetric relationships are stored once, lower identifier as source
  (Decision 5.4.15 rule 5); use :func:`ordered_pair`.
* ``supersedes`` memory relationships carry a reason; other types do not.
* Resolution records reference exactly what their outcome implies.
"""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any

from memory_engine.domain.errors import DomainValidationError
from memory_engine.domain.vocabulary import (
    EntityRelationshipType,
    EntityResolutionOutcome,
    EntityScope,
    EntityStatus,
    EntityType,
    MemoryEntityRole,
    MemoryRelationshipType,
    MentionResolutionStatus,
    ProvenanceOriginKind,
    SupersessionReason,
)

JsonMap = Mapping[str, Any]


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


def _require_temporal(
    valid_from: datetime | None,
    valid_to: datetime | None,
    recorded_at: datetime,
    superseded_at: datetime | None,
) -> None:
    for name, value in (
        ("valid_from", valid_from),
        ("valid_to", valid_to),
        ("recorded_at", recorded_at),
        ("superseded_at", superseded_at),
    ):
        _require_aware(name, value)
    if valid_from is not None and valid_to is not None and valid_to < valid_from:
        raise DomainValidationError("valid_to must not be earlier than valid_from")
    if superseded_at is not None and superseded_at < recorded_at:
        raise DomainValidationError("superseded_at must not be earlier than recorded_at")


def ordered_pair(first: uuid.UUID, second: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    """Canonical order for symmetric relationships (same order as PostgreSQL uuid)."""
    return (first, second) if first < second else (second, first)


def _require_endpoints(source: uuid.UUID, target: uuid.UUID, *, symmetric: bool) -> None:
    if source == target:
        raise DomainValidationError("a relationship needs two different endpoints")
    if symmetric and not source < target:
        raise DomainValidationError(
            "symmetric relationships are stored once, lower id as source; use ordered_pair()"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class Entity:
    """A canonical identity (Decisions 5.4.8, 5.4.13)."""

    id: uuid.UUID
    owner_id: uuid.UUID
    entity_type: EntityType
    canonical_name: str
    status: EntityStatus
    scope: EntityScope = EntityScope.PRIVATE
    merged_into_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        if self.scope is not EntityScope.PRIVATE:
            raise DomainValidationError("shared entities are not permitted (Decision 11)")
        _require_text("canonical_name", self.canonical_name)
        if (self.status is EntityStatus.MERGED) != (self.merged_into_id is not None):
            raise DomainValidationError("merged_into_id is required exactly when merged")
        if self.merged_into_id == self.id:
            raise DomainValidationError("an entity cannot be merged into itself")


@dataclass(frozen=True, slots=True, kw_only=True)
class EntityAlias:
    """An alternative name for an entity (Decision 5.4.14). Not proof of identity."""

    id: uuid.UUID
    owner_id: uuid.UUID
    entity_id: uuid.UUID
    alias: str
    source_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        _require_text("alias", self.alias)

    @staticmethod
    def normalize(text: str) -> str:
        """Matching key: trimmed, case-folded, inner whitespace collapsed."""
        return " ".join(text.split()).casefold()


@dataclass(frozen=True, slots=True, kw_only=True)
class EntityMention:
    """What Raven observed, with its current resolution (Decisions 5.4.33-5.4.34).

    The original wording is never changed; only the resolution moves.
    """

    id: uuid.UUID
    owner_id: uuid.UUID
    source_id: uuid.UUID
    mention_text: str
    mention_type: EntityType
    resolution_status: MentionResolutionStatus
    entity_id: uuid.UUID | None = None
    candidate_id: uuid.UUID | None = None
    confidence: float | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    context: JsonMap = field(default_factory=_empty)

    def __post_init__(self) -> None:
        _require_text("mention_text", self.mention_text)
        _require_score("confidence", self.confidence)
        if (self.resolution_status is MentionResolutionStatus.RESOLVED) != (
            self.entity_id is not None
        ):
            raise DomainValidationError("entity_id is required exactly when resolved")
        if self.start_offset is not None and self.start_offset < 0:
            raise DomainValidationError("start_offset must not be negative")
        if self.end_offset is not None and (
            self.start_offset is None or self.end_offset < self.start_offset
        ):
            raise DomainValidationError("end_offset requires a start_offset and must follow it")
        object.__setattr__(self, "context", MappingProxyType(dict(self.context)))


_MENTION_OUTCOMES = {
    EntityResolutionOutcome.MATCHED_EXISTING,
    EntityResolutionOutcome.CREATED_NEW,
    EntityResolutionOutcome.LEFT_UNRESOLVED,
    EntityResolutionOutcome.SENT_TO_REVIEW,
    EntityResolutionOutcome.CORRECTED,
    EntityResolutionOutcome.REASSIGNED,
}
_CHANGES_PREVIOUS = {
    EntityResolutionOutcome.CORRECTED,
    EntityResolutionOutcome.REASSIGNED,
    EntityResolutionOutcome.MERGED,
}


@dataclass(frozen=True, slots=True, kw_only=True)
class EntityResolutionRecord:
    """One material resolution decision, kept as history (Decision 5.4.34).

    * mention outcomes reference the mention;
    * ``merged`` references no mention: ``previous_entity_id`` is merged into
      ``entity_id`` (the survivor);
    * ``corrected`` / ``reassigned`` record the entity they replace.
    """

    id: uuid.UUID
    owner_id: uuid.UUID
    outcome: EntityResolutionOutcome
    recorded_at: datetime
    mention_id: uuid.UUID | None = None
    entity_id: uuid.UUID | None = None
    previous_entity_id: uuid.UUID | None = None
    candidate_entity_ids: tuple[uuid.UUID, ...] = ()
    rationale: str | None = None
    evidence: JsonMap = field(default_factory=_empty)

    def __post_init__(self) -> None:
        _require_aware("recorded_at", self.recorded_at)
        if (self.outcome in _MENTION_OUTCOMES) != (self.mention_id is not None):
            raise DomainValidationError("mention outcomes, and only they, reference a mention")
        if self.outcome.assigns_entity != (self.entity_id is not None):
            raise DomainValidationError(f"outcome '{self.outcome}' and entity_id disagree")
        if (self.outcome in _CHANGES_PREVIOUS) != (self.previous_entity_id is not None):
            raise DomainValidationError(f"outcome '{self.outcome}' and previous_entity_id disagree")
        if self.previous_entity_id is not None and self.previous_entity_id == self.entity_id:
            raise DomainValidationError("previous_entity_id must differ from entity_id")
        if self.rationale is not None:
            _require_text("rationale", self.rationale)
        object.__setattr__(self, "candidate_entity_ids", tuple(self.candidate_entity_ids))
        object.__setattr__(self, "evidence", MappingProxyType(dict(self.evidence)))

    def mention_status(self) -> MentionResolutionStatus:
        """The mention state this decision leaves behind."""
        if self.outcome is EntityResolutionOutcome.SENT_TO_REVIEW:
            return MentionResolutionStatus.NEEDS_REVIEW
        if self.outcome is EntityResolutionOutcome.LEFT_UNRESOLVED:
            return (
                MentionResolutionStatus.AMBIGUOUS
                if len(self.candidate_entity_ids) > 1
                else MentionResolutionStatus.UNRESOLVED
            )
        if self.outcome is EntityResolutionOutcome.MERGED:
            raise DomainValidationError("a merge does not resolve a mention")
        return MentionResolutionStatus.RESOLVED


@dataclass(frozen=True, slots=True, kw_only=True)
class EntityRelationship:
    """A typed, directed, time-bounded link between two entities (Decision 5.4.15).

    Rows are closed (``valid_to`` / ``superseded_at``) and replaced, never
    overwritten (Phase 8.2 amendment section 3).
    """

    id: uuid.UUID
    owner_id: uuid.UUID
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relationship_type: EntityRelationshipType
    origin_kind: ProvenanceOriginKind
    recorded_at: datetime
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    superseded_at: datetime | None = None
    confidence: float | None = None
    source_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        _require_endpoints(
            self.source_entity_id,
            self.target_entity_id,
            symmetric=self.relationship_type.symmetric,
        )
        _require_temporal(self.valid_from, self.valid_to, self.recorded_at, self.superseded_at)
        _require_score("confidence", self.confidence)


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryRelationship:
    """A typed link between two Atomic Memories (Decision 5.4.27; amendment section 4).

    Persisting a relationship does not apply its effect (for example a
    ``supersedes`` target becoming ``historical``); resolution (8.6) does both
    in one unit of work.
    """

    id: uuid.UUID
    owner_id: uuid.UUID
    source_memory_id: uuid.UUID
    target_memory_id: uuid.UUID
    relationship_type: MemoryRelationshipType
    origin_kind: ProvenanceOriginKind
    recorded_at: datetime
    reason: SupersessionReason | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    superseded_at: datetime | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        _require_endpoints(
            self.source_memory_id,
            self.target_memory_id,
            symmetric=self.relationship_type.symmetric,
        )
        if (self.relationship_type is MemoryRelationshipType.SUPERSEDES) != (
            self.reason is not None
        ):
            raise DomainValidationError("a reason is required exactly for 'supersedes'")
        _require_temporal(self.valid_from, self.valid_to, self.recorded_at, self.superseded_at)
        _require_score("confidence", self.confidence)


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryEntityAssociation:
    """Which entity an Atomic Memory concerns, and how (amendment section 5)."""

    id: uuid.UUID
    owner_id: uuid.UUID
    memory_id: uuid.UUID
    entity_id: uuid.UUID
    role: MemoryEntityRole
