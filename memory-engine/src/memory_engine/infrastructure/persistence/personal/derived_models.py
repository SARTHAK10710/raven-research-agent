"""SQLAlchemy models for derived knowledge and memory metadata (Phase 8.2 step 4, 0004).

Episodes, profiles, category assignments and memory embedding metadata.
Integrity enforced by PostgreSQL in addition to owner-scoped foreign keys:

* Times with ``unknown`` precision have no value; known ones do (5.4.30).
* Profiles keep content in append-only revisions; each revision's supporting
  memories reference the exact memory revision used (foreign key), so a profile
  cannot claim a version that does not exist.
* At most one live profile per owner and type (or type and subject entity).
* Refresh history is append-only and ordered by ``seq``; outcomes imply exactly
  whether a revision was created and whether an error code is present.
* Episodes carry a ``version`` (0006) that every update checks and increments.
* Memberships, timeline events and category assignments are closed, never
  overwritten; at most one current row per pair (partial unique indexes).
* At most one primary embedding per memory revision, model and preprocessing.
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
from memory_engine.infrastructure.persistence.base import Base, in_vocabulary
from memory_engine.infrastructure.persistence.personal.models import score_range

Json = dict[str, Any]

REVISION_OUTCOMES = ", ".join(f"'{o.value}'" for o in RefreshOutcome if o.creates_revision)
SAFE_ERROR_CODE = "error_code IS NULL OR error_code ~ '^[A-Z][A-Z0-9_]{0,63}$'"


def _precise(column: str, precision: str) -> str:
    return f"({precision} = 'unknown') = ({column} IS NULL)"


def _now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def _updated() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


def _owner_fk(column: str, table: str) -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        [column, "owner_id"], [f"{table}.id", f"{table}.owner_id"], ondelete="RESTRICT"
    )


def _memory_revision_fk(revision_column: str) -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        ["memory_id", revision_column],
        ["pm_atomic_memory_revision.memory_id", "pm_atomic_memory_revision.revision_number"],
        ondelete="RESTRICT",
    )


# --- episodes ------------------------------------------------------------------------


class EpisodeRow(Base):
    __tablename__ = "pm_episode"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    start_precision: Mapped[str] = mapped_column(String(16), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_precision: Mapped[str] = mapped_column(String(16), nullable=False)
    method: Mapped[str] = mapped_column(Text, nullable=False)
    method_version: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Optimistic concurrency (0006): every update must name the version it read.
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _updated()

    __table_args__ = (
        UniqueConstraint("id", "owner_id"),
        CheckConstraint("version >= 1", name="version_positive"),
        in_vocabulary("status", EpisodeStatus, name="status"),
        in_vocabulary("start_precision", TemporalPrecision, name="start_precision"),
        in_vocabulary("end_precision", TemporalPrecision, name="end_precision"),
        CheckConstraint(_precise("starts_at", "start_precision"), name="start_known"),
        CheckConstraint(_precise("ends_at", "end_precision"), name="end_known"),
        CheckConstraint(
            "starts_at IS NULL OR ends_at IS NULL OR ends_at >= starts_at", name="boundaries"
        ),
        CheckConstraint("title IS NULL OR length(btrim(title)) > 0", name="title"),
        CheckConstraint("length(btrim(method)) > 0", name="method"),
        Index(None, "owner_id", "status"),
    )


class EpisodeMembershipRow(Base):
    __tablename__ = "pm_episode_membership"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    episode_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    memory_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    sequence: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float | None] = mapped_column(Double)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _updated()

    __table_args__ = (
        _owner_fk("episode_id", "pm_episode"),
        _owner_fk("memory_id", "pm_atomic_memory"),
        CheckConstraint("sequence IS NULL OR sequence >= 0", name="sequence"),
        CheckConstraint("removed_at IS NULL OR removed_at >= added_at", name="removed_after_added"),
        *score_range(("confidence",)),
        Index(
            "uq_pm_episode_membership_current",
            "episode_id",
            "memory_id",
            unique=True,
            postgresql_where=text("removed_at IS NULL"),
        ),
        Index(None, "owner_id", "memory_id"),
    )


class EpisodeEventRow(Base):
    __tablename__ = "pm_episode_event"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    episode_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    memory_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    precision: Mapped[str] = mapped_column(String(16), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _updated()

    __table_args__ = (
        _owner_fk("episode_id", "pm_episode"),
        _owner_fk("memory_id", "pm_atomic_memory"),
        in_vocabulary("precision", TemporalPrecision, name="precision"),
        CheckConstraint(_precise("occurred_at", "precision"), name="occurred_known"),
        CheckConstraint("length(btrim(label)) > 0", name="label"),
        CheckConstraint(
            "superseded_at IS NULL OR superseded_at >= recorded_at",
            name="superseded_after_recorded",
        ),
        Index(None, "owner_id", "episode_id"),
    )


# --- profiles ------------------------------------------------------------------------


class ProfileRow(Base):
    __tablename__ = "pm_profile"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    profile_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _updated()

    __table_args__ = (
        UniqueConstraint("id", "owner_id"),
        _owner_fk("subject_entity_id", "pm_entity"),
        # The current revision must exist. use_alter: the tables reference each other.
        ForeignKeyConstraint(
            ["id", "current_revision_number"],
            ["pm_profile_revision.profile_id", "pm_profile_revision.revision_number"],
            ondelete="RESTRICT",
            use_alter=True,
            deferrable=True,
            initially="DEFERRED",
        ),
        in_vocabulary("profile_type", ProfileType, name="profile_type"),
        in_vocabulary("status", ProfileStatus, name="status"),
        CheckConstraint("current_revision_number >= 1", name="revision_number_positive"),
        Index(
            "uq_pm_profile_one_per_type",
            "owner_id",
            "profile_type",
            unique=True,
            postgresql_where=text("subject_entity_id IS NULL AND status <> 'deleted'"),
        ),
        Index(
            "uq_pm_profile_one_per_subject",
            "owner_id",
            "profile_type",
            "subject_entity_id",
            unique=True,
            postgresql_where=text("subject_entity_id IS NOT NULL AND status <> 'deleted'"),
        ),
    )


class ProfileRevisionRow(Base):
    __tablename__ = "pm_profile_revision"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    attributes: Mapped[Json] = mapped_column(JSONB, nullable=False, server_default="{}")
    method: Mapped[str] = mapped_column(Text, nullable=False)
    method_version: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = _now()

    __table_args__ = (
        UniqueConstraint("profile_id", "revision_number"),
        _owner_fk("profile_id", "pm_profile"),
        CheckConstraint("revision_number >= 1", name="revision_number_positive"),
        CheckConstraint("length(btrim(method)) > 0", name="method"),
    )


class ProfileMemoryRow(Base):
    __tablename__ = "pm_profile_memory"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    memory_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    memory_revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    attribute: Mapped[str | None] = mapped_column(Text)
    relevance: Mapped[float | None] = mapped_column(Double)
    created_at: Mapped[datetime] = _now()

    __table_args__ = (
        _owner_fk("profile_id", "pm_profile"),
        ForeignKeyConstraint(
            ["profile_id", "revision_number"],
            ["pm_profile_revision.profile_id", "pm_profile_revision.revision_number"],
            ondelete="RESTRICT",
        ),
        _owner_fk("memory_id", "pm_atomic_memory"),
        _memory_revision_fk("memory_revision_number"),
        CheckConstraint("attribute IS NULL OR length(btrim(attribute)) > 0", name="attribute"),
        *score_range(("relevance",)),
        Index(None, "owner_id", "memory_id"),
        Index(None, "profile_id", "revision_number"),
    )


class ProfileRefreshRow(Base):
    __tablename__ = "pm_profile_refresh"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True), nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    trigger: Mapped[str] = mapped_column(String(16), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    from_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    to_revision: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(64))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = _now()

    __table_args__ = (
        _owner_fk("profile_id", "pm_profile"),
        in_vocabulary("trigger", RefreshTrigger, name="trigger"),
        in_vocabulary("outcome", RefreshOutcome, name="outcome"),
        CheckConstraint(
            f"(outcome IN ({REVISION_OUTCOMES})) = (to_revision IS NOT NULL)",
            name="revision_matches_outcome",
        ),
        CheckConstraint(
            "to_revision IS NULL OR to_revision = from_revision + 1", name="next_revision"
        ),
        CheckConstraint("(outcome = 'failed') = (error_code IS NOT NULL)", name="failure_code"),
        CheckConstraint(SAFE_ERROR_CODE, name="error_code"),
        Index(None, "owner_id", "profile_id"),
    )


# --- categories and memory embeddings ------------------------------------------------


class MemoryCategoryRow(Base):
    __tablename__ = "pm_memory_category"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    memory_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    origin: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Double)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _updated()

    __table_args__ = (
        _owner_fk("memory_id", "pm_atomic_memory"),
        in_vocabulary("category", MemoryCategory, name="category"),
        in_vocabulary("origin", MemoryOrigin, name="origin"),
        CheckConstraint(
            "superseded_at IS NULL OR superseded_at >= recorded_at",
            name="superseded_after_recorded",
        ),
        *score_range(("confidence",)),
        Index(
            "uq_pm_memory_category_current",
            "memory_id",
            "category",
            unique=True,
            postgresql_where=text("superseded_at IS NULL"),
        ),
        Index(None, "owner_id", "category"),
    )


class MemoryEmbeddingRow(Base):
    __tablename__ = "pm_memory_embedding"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    memory_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    purpose: Mapped[str] = mapped_column(String(16), nullable=False)
    aspect_label: Mapped[str | None] = mapped_column(Text)
    model_id: Mapped[str] = mapped_column(Text, nullable=False)
    model_revision: Mapped[str] = mapped_column(Text, nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    preprocessing_version: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _updated()

    __table_args__ = (
        _owner_fk("memory_id", "pm_atomic_memory"),
        _memory_revision_fk("revision_number"),
        in_vocabulary("purpose", EmbeddingPurpose, name="purpose"),
        in_vocabulary("status", EmbeddingStatus, name="status"),
        CheckConstraint("(purpose = 'aspect') = (aspect_label IS NOT NULL)", name="aspect_label"),
        CheckConstraint("dimensions > 0", name="dimensions"),
        Index(
            "uq_pm_memory_embedding_primary",
            "memory_id",
            "revision_number",
            "model_id",
            "model_revision",
            "preprocessing_version",
            unique=True,
            postgresql_where=text("purpose = 'primary'"),
        ),
        Index(
            "uq_pm_memory_embedding_aspect",
            "memory_id",
            "revision_number",
            "model_id",
            "model_revision",
            "preprocessing_version",
            "aspect_label",
            unique=True,
            postgresql_where=text("purpose = 'aspect'"),
        ),
        Index(None, "owner_id", "memory_id"),
    )
