"""SQLAlchemy models for the core Personal Memory tables (Phase 8.2 step 1).

Integrity rules enforced in the database, not only in code:

* Every row has ``owner_id``. Child rows reference parents through composite
  foreign keys on ``(id, owner_id)``, so a child can never point at another
  owner's parent.
* Foreign keys use ``RESTRICT``: there is no implicit cascade on user data;
  deletion runs as explicit, verified workflow steps (7.1 section 23.3).
* Vocabulary columns carry check constraints built from the domain enums.
* Revisions and provenance are append-only: migration 0001 installs triggers
  that reject ``UPDATE`` (deletion workflows may still ``DELETE``).

The migration is the source of truth for the deployed schema; a unit test keeps
these models and the migration's frozen vocabularies in step.
"""

import uuid
from collections.abc import Iterable
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Double,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from memory_engine.domain.vocabulary import (
    CandidateOrigin,
    CandidateStatus,
    MemoryLifecycleStatus,
    MemoryOrigin,
    ProvenanceOriginKind,
    ProvenanceRole,
    RevisionChangeType,
    SourceProcessingStatus,
    SourceType,
)
from memory_engine.infrastructure.persistence.base import Base

Json = dict[str, Any]

# A deleted memory keeps only a tombstone; every other state needs real content.
# (A bare length(...) > 0 check would pass for NULL, so NULL is tested explicitly.)
CONTENT_MATCHES_LIFECYCLE = (
    "(lifecycle_status = 'deleted' AND content IS NULL)"
    " OR (lifecycle_status <> 'deleted' AND content IS NOT NULL AND length(btrim(content)) > 0)"
)


def in_vocabulary(column: str, vocabulary: type[StrEnum], *, name: str) -> CheckConstraint:
    values = ", ".join(f"'{member.value}'" for member in vocabulary)
    return CheckConstraint(f"{column} IN ({values})", name=name)


def score_range(columns: Iterable[str]) -> list[CheckConstraint]:
    return [
        CheckConstraint(f"{column} IS NULL OR ({column} >= 0 AND {column} <= 1)", name=column)
        for column in columns
    ]


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MemorySourceRow(Base):
    __tablename__ = "pm_memory_source"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(32), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_ref: Mapped[str | None] = mapped_column(Text)
    content_sha256: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("id", "owner_id"),
        in_vocabulary("source_type", SourceType, name="source_type"),
        in_vocabulary("processing_status", SourceProcessingStatus, name="processing_status"),
        CheckConstraint("content_sha256 ~ '^[0-9a-f]{64}$'", name="content_sha256"),
        Index(None, "owner_id", "received_at"),
    )


class MemoryCandidateRow(Base):
    __tablename__ = "pm_memory_candidate"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    proposition: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    origin: Mapped[str] = mapped_column(String(32), nullable=False)
    importance: Mapped[float | None] = mapped_column(Double)
    confidence: Mapped[float | None] = mapped_column(Double)
    extraction_confidence: Mapped[float | None] = mapped_column(Double)
    context: Mapped[Json] = mapped_column(JSONB, nullable=False, server_default="{}")
    temporal: Mapped[Json] = mapped_column(JSONB, nullable=False, server_default="{}")
    extraction_metadata: Mapped[Json] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("id", "owner_id"),
        ForeignKeyConstraint(
            ["source_id", "owner_id"],
            ["pm_memory_source.id", "pm_memory_source.owner_id"],
            ondelete="RESTRICT",
        ),
        in_vocabulary("status", CandidateStatus, name="status"),
        in_vocabulary("origin", CandidateOrigin, name="origin"),
        CheckConstraint("length(btrim(proposition)) > 0", name="proposition_not_blank"),
        CheckConstraint(
            "NOT (origin = 'unresolved' AND status = 'validated')", name="unresolved_not_validated"
        ),
        *score_range(("importance", "confidence", "extraction_confidence")),
        Index(None, "owner_id", "source_id"),
        Index(None, "owner_id", "status"),
    )


class AtomicMemoryRow(Base):
    __tablename__ = "pm_atomic_memory"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    structured: Mapped[Json] = mapped_column(JSONB, nullable=False, server_default="{}")
    context: Mapped[Json] = mapped_column(JSONB, nullable=False, server_default="{}")
    origin: Mapped[str] = mapped_column(String(32), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(32), nullable=False)
    importance: Mapped[float | None] = mapped_column(Double)
    confidence: Mapped[float | None] = mapped_column(Double)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Optimistic concurrency token: the number of the revision this state equals.
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("id", "owner_id"),
        in_vocabulary("origin", MemoryOrigin, name="origin"),
        in_vocabulary("lifecycle_status", MemoryLifecycleStatus, name="lifecycle_status"),
        CheckConstraint(CONTENT_MATCHES_LIFECYCLE, name="content_matches_lifecycle"),
        CheckConstraint("revision_number >= 1", name="revision_number_positive"),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="valid_interval",
        ),
        CheckConstraint(
            "superseded_at IS NULL OR superseded_at >= recorded_at",
            name="superseded_after_recorded",
        ),
        *score_range(("importance", "confidence")),
        Index(None, "owner_id", "lifecycle_status"),
    )


class AtomicMemoryRevisionRow(Base):
    __tablename__ = "pm_atomic_memory_revision"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    memory_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    change_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    structured: Mapped[Json] = mapped_column(JSONB, nullable=False, server_default="{}")
    context: Mapped[Json] = mapped_column(JSONB, nullable=False, server_default="{}")
    origin: Mapped[str] = mapped_column(String(32), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(32), nullable=False)
    importance: Mapped[float | None] = mapped_column(Double)
    confidence: Mapped[float | None] = mapped_column(Double)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()

    __table_args__ = (
        UniqueConstraint("memory_id", "revision_number"),
        ForeignKeyConstraint(
            ["memory_id", "owner_id"],
            ["pm_atomic_memory.id", "pm_atomic_memory.owner_id"],
            ondelete="RESTRICT",
        ),
        in_vocabulary("change_type", RevisionChangeType, name="change_type"),
        in_vocabulary("origin", MemoryOrigin, name="origin"),
        in_vocabulary("lifecycle_status", MemoryLifecycleStatus, name="lifecycle_status"),
        CheckConstraint(CONTENT_MATCHES_LIFECYCLE, name="content_matches_lifecycle"),
        CheckConstraint("revision_number >= 1", name="revision_number_positive"),
        CheckConstraint(
            "(revision_number = 1) = (change_type = 'created')", name="created_is_first"
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="valid_interval",
        ),
        *score_range(("importance", "confidence")),
        Index(None, "owner_id", "memory_id"),
    )


class ProvenanceRow(Base):
    __tablename__ = "pm_provenance"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    memory_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    source_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    origin_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = _created_at()

    __table_args__ = (
        ForeignKeyConstraint(
            ["memory_id", "owner_id"],
            ["pm_atomic_memory.id", "pm_atomic_memory.owner_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["memory_id", "revision_number"],
            ["pm_atomic_memory_revision.memory_id", "pm_atomic_memory_revision.revision_number"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["source_id", "owner_id"],
            ["pm_memory_source.id", "pm_memory_source.owner_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["candidate_id", "owner_id"],
            ["pm_memory_candidate.id", "pm_memory_candidate.owner_id"],
            ondelete="RESTRICT",
        ),
        in_vocabulary("role", ProvenanceRole, name="role"),
        in_vocabulary("origin_kind", ProvenanceOriginKind, name="origin_kind"),
        CheckConstraint(
            "source_id IS NOT NULL OR candidate_id IS NOT NULL", name="references_evidence"
        ),
        CheckConstraint(
            "revision_number IS NULL OR revision_number >= 1", name="revision_number_positive"
        ),
        Index(None, "owner_id", "memory_id"),
    )
