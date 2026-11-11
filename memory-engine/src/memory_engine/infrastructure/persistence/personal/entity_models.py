"""SQLAlchemy models for entities and relationships (Phase 8.2 step 3, migration 0003).

Integrity enforced by PostgreSQL, in addition to owner-scoped composite foreign
keys with ``RESTRICT``:

* Entities are private only: ``scope = 'private'`` is checked (Decision 11).
* A merged entity names its survivor, and never itself.
* A resolved mention references an entity; any other mention does not.
* Resolution records reference exactly what their outcome implies, and are
  append-only, as are aliases and memory-entity associations.
* Symmetric relationships are stored once (lower id as source), and at most one
  *current* row exists per endpoint pair and type (partial unique index);
  closed rows remain as history. Only ``valid_to``/``superseded_at`` may change.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Double,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

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
from memory_engine.infrastructure.persistence.base import Base, in_vocabulary
from memory_engine.infrastructure.persistence.personal.models import score_range

Json = dict[str, Any]


def _values(*members: object) -> str:
    return ", ".join(f"'{getattr(member, 'value', member)}'" for member in members)


MENTION_OUTCOMES = _values(
    EntityResolutionOutcome.MATCHED_EXISTING,
    EntityResolutionOutcome.CREATED_NEW,
    EntityResolutionOutcome.LEFT_UNRESOLVED,
    EntityResolutionOutcome.SENT_TO_REVIEW,
    EntityResolutionOutcome.CORRECTED,
    EntityResolutionOutcome.REASSIGNED,
)
ASSIGNING_OUTCOMES = _values(*(o for o in EntityResolutionOutcome if o.assigns_entity))
CHANGING_OUTCOMES = _values(
    EntityResolutionOutcome.CORRECTED,
    EntityResolutionOutcome.REASSIGNED,
    EntityResolutionOutcome.MERGED,
)
SYMMETRIC_ENTITY_TYPES = _values(*(t for t in EntityRelationshipType if t.symmetric))
SYMMETRIC_MEMORY_TYPES = _values(*(t for t in MemoryRelationshipType if t.symmetric))
PREVIOUS_DIFFERS = "previous_entity_id IS NULL OR previous_entity_id IS DISTINCT FROM entity_id"
TEMPORAL_CHECKS = (
    ("valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from", "valid_interval"),
    ("superseded_at IS NULL OR superseded_at >= recorded_at", "superseded_after_recorded"),
)


def _now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def _updated() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


def _owner_fk(columns: list[str], table: str) -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        [columns[0], "owner_id"], [f"{table}.id", f"{table}.owner_id"], ondelete="RESTRICT"
    )


class EntityRow(Base):
    __tablename__ = "pm_entity"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _updated()

    __table_args__ = (
        UniqueConstraint("id", "owner_id"),
        _owner_fk(["merged_into_id"], "pm_entity"),
        in_vocabulary("scope", EntityScope, name="scope"),
        CheckConstraint("scope = 'private'", name="private_only"),
        in_vocabulary("entity_type", EntityType, name="entity_type"),
        in_vocabulary("status", EntityStatus, name="status"),
        CheckConstraint("(status = 'merged') = (merged_into_id IS NOT NULL)", name="merged_target"),
        CheckConstraint("merged_into_id IS DISTINCT FROM id", name="not_merged_into_self"),
        CheckConstraint("length(btrim(canonical_name)) > 0", name="canonical_name"),
        CheckConstraint("length(normalized_name) > 0", name="normalized_name"),
        Index(None, "owner_id", "normalized_name"),
    )


class EntityAliasRow(Base):
    __tablename__ = "pm_entity_alias"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    alias: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_alias: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = _now()

    __table_args__ = (
        UniqueConstraint("entity_id", "normalized_alias"),
        _owner_fk(["entity_id"], "pm_entity"),
        _owner_fk(["source_id"], "pm_memory_source"),
        CheckConstraint("length(btrim(alias)) > 0", name="alias"),
        CheckConstraint("length(normalized_alias) > 0", name="normalized_alias"),
        Index(None, "owner_id", "normalized_alias"),
    )


class EntityMentionRow(Base):
    __tablename__ = "pm_entity_mention"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    mention_text: Mapped[str] = mapped_column(Text, nullable=False)
    mention_type: Mapped[str] = mapped_column(String(32), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    confidence: Mapped[float | None] = mapped_column(Double)
    start_offset: Mapped[int | None] = mapped_column(Integer)
    end_offset: Mapped[int | None] = mapped_column(Integer)
    context: Mapped[Json] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _updated()

    __table_args__ = (
        UniqueConstraint("id", "owner_id"),
        _owner_fk(["source_id"], "pm_memory_source"),
        _owner_fk(["candidate_id"], "pm_memory_candidate"),
        _owner_fk(["entity_id"], "pm_entity"),
        in_vocabulary("mention_type", EntityType, name="mention_type"),
        in_vocabulary("resolution_status", MentionResolutionStatus, name="resolution_status"),
        CheckConstraint(
            "(resolution_status = 'resolved') = (entity_id IS NOT NULL)", name="resolved_entity"
        ),
        CheckConstraint("length(btrim(mention_text)) > 0", name="mention_text"),
        CheckConstraint("start_offset IS NULL OR start_offset >= 0", name="start_offset"),
        CheckConstraint(
            "end_offset IS NULL OR (start_offset IS NOT NULL AND end_offset >= start_offset)",
            name="end_offset",
        ),
        *score_range(("confidence",)),
        Index(None, "owner_id", "entity_id"),
        Index(None, "owner_id", "source_id"),
    )


class EntityResolutionRow(Base):
    __tablename__ = "pm_entity_resolution"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    # Insertion order. now() is fixed per transaction, so created_at cannot order
    # several decisions recorded together; history is ordered by (recorded_at, seq).
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    mention_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    previous_entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    candidate_entity_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    rationale: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[Json] = mapped_column(JSONB, nullable=False, server_default="{}")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = _now()

    __table_args__ = (
        _owner_fk(["mention_id"], "pm_entity_mention"),
        _owner_fk(["entity_id"], "pm_entity"),
        _owner_fk(["previous_entity_id"], "pm_entity"),
        in_vocabulary("outcome", EntityResolutionOutcome, name="outcome"),
        CheckConstraint(
            f"(outcome IN ({MENTION_OUTCOMES})) = (mention_id IS NOT NULL)", name="mention_ref"
        ),
        CheckConstraint(
            f"(outcome IN ({ASSIGNING_OUTCOMES})) = (entity_id IS NOT NULL)", name="entity_ref"
        ),
        CheckConstraint(
            f"(outcome IN ({CHANGING_OUTCOMES})) = (previous_entity_id IS NOT NULL)",
            name="previous_ref",
        ),
        # Not a bare IS DISTINCT FROM: that is false when both are NULL, which is
        # the normal case for unresolved and review outcomes (a test caught it).
        CheckConstraint(PREVIOUS_DIFFERS, name="previous_differs"),
        CheckConstraint("jsonb_typeof(candidate_entity_ids) = 'array'", name="candidates_array"),
        Index(None, "owner_id", "mention_id"),
        Index(None, "owner_id", "entity_id"),
    )


class EntityRelationshipRow(Base):
    __tablename__ = "pm_entity_relationship"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    target_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(32), nullable=False)
    origin_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Double)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _updated()

    __table_args__ = (
        _owner_fk(["source_entity_id"], "pm_entity"),
        _owner_fk(["target_entity_id"], "pm_entity"),
        _owner_fk(["source_id"], "pm_memory_source"),
        in_vocabulary("relationship_type", EntityRelationshipType, name="relationship_type"),
        in_vocabulary("origin_kind", ProvenanceOriginKind, name="origin_kind"),
        CheckConstraint("source_entity_id <> target_entity_id", name="distinct_endpoints"),
        CheckConstraint(
            f"relationship_type NOT IN ({SYMMETRIC_ENTITY_TYPES})"
            " OR source_entity_id < target_entity_id",
            name="symmetric_order",
        ),
        *(CheckConstraint(condition, name=name) for condition, name in TEMPORAL_CHECKS),
        *score_range(("confidence",)),
        Index(
            "uq_pm_entity_relationship_current",
            "source_entity_id",
            "target_entity_id",
            "relationship_type",
            unique=True,
            postgresql_where=text("superseded_at IS NULL"),
        ),
        Index(None, "owner_id", "source_entity_id"),
        Index(None, "owner_id", "target_entity_id"),
    )


class MemoryRelationshipRow(Base):
    __tablename__ = "pm_memory_relationship"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_memory_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    target_memory_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(32))
    origin_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Double)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _updated()

    __table_args__ = (
        _owner_fk(["source_memory_id"], "pm_atomic_memory"),
        _owner_fk(["target_memory_id"], "pm_atomic_memory"),
        in_vocabulary("relationship_type", MemoryRelationshipType, name="relationship_type"),
        in_vocabulary("origin_kind", ProvenanceOriginKind, name="origin_kind"),
        CheckConstraint(
            f"reason IS NULL OR reason IN ({_values(*SupersessionReason)})", name="reason"
        ),
        CheckConstraint(
            "(relationship_type = 'supersedes') = (reason IS NOT NULL)", name="reason_required"
        ),
        CheckConstraint("source_memory_id <> target_memory_id", name="distinct_endpoints"),
        CheckConstraint(
            f"relationship_type NOT IN ({SYMMETRIC_MEMORY_TYPES})"
            " OR source_memory_id < target_memory_id",
            name="symmetric_order",
        ),
        *(CheckConstraint(condition, name=name) for condition, name in TEMPORAL_CHECKS),
        *score_range(("confidence",)),
        Index(
            "uq_pm_memory_relationship_current",
            "source_memory_id",
            "target_memory_id",
            "relationship_type",
            unique=True,
            postgresql_where=text("superseded_at IS NULL"),
        ),
        Index(None, "owner_id", "source_memory_id"),
        Index(None, "owner_id", "target_memory_id"),
    )


class MemoryEntityRow(Base):
    __tablename__ = "pm_memory_entity"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    memory_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = _now()

    __table_args__ = (
        UniqueConstraint("memory_id", "entity_id", "role"),
        _owner_fk(["memory_id"], "pm_atomic_memory"),
        _owner_fk(["entity_id"], "pm_entity"),
        in_vocabulary("role", MemoryEntityRole, name="role"),
        Index(None, "owner_id", "entity_id"),
    )
