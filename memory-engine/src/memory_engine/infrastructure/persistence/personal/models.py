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
    DocumentEvidenceStatus,
    MemoryLifecycleStatus,
    MemoryOrigin,
    ProvenanceOriginKind,
    ProvenanceRole,
    RevisionChangeType,
    SourceProcessingStatus,
    SourceType,
)
from memory_engine.infrastructure.persistence.base import Base, in_vocabulary

Json = dict[str, Any]

# A deleted memory keeps only a tombstone; every other state needs real content.
# (A bare length(...) > 0 check would pass for NULL, so NULL is tested explicitly.)
CONTENT_MATCHES_LIFECYCLE = (
    "(lifecycle_status = 'deleted' AND content IS NULL)"
    " OR (lifecycle_status <> 'deleted' AND content IS NOT NULL AND length(btrim(content)) > 0)"
)

PROVENANCE_REFERENCES_EVIDENCE = (
    "source_id IS NOT NULL OR candidate_id IS NOT NULL OR document_evidence_id IS NOT NULL"
)

# Active evidence links the live document rows; deleted-source evidence links nothing.
# IS NOT DISTINCT FROM (not "="): a plain equality is NULL when the link is missing,
# and PostgreSQL treats a NULL check result as passing. The _ref columns are NOT NULL,
# so this forces the links to be present (a test caught the "=" version).
EVIDENCE_LINKS_MATCH_STATUS = (
    "(status = 'active' AND document_id IS NOT DISTINCT FROM document_ref"
    " AND version_id IS NOT DISTINCT FROM version_ref"
    " AND chunk_id IS NOT DISTINCT FROM chunk_ref)"
    " OR (status = 'source_deleted' AND document_id IS NULL AND version_id IS NULL"
    " AND chunk_id IS NULL)"
)


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
    document_evidence_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
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
        ForeignKeyConstraint(
            ["document_evidence_id", "owner_id"],
            ["pm_document_evidence_ref.id", "pm_document_evidence_ref.owner_id"],
            ondelete="RESTRICT",
        ),
        in_vocabulary("role", ProvenanceRole, name="role"),
        in_vocabulary("origin_kind", ProvenanceOriginKind, name="origin_kind"),
        CheckConstraint(PROVENANCE_REFERENCES_EVIDENCE, name="references_evidence"),
        CheckConstraint(
            "revision_number IS NULL OR revision_number >= 1", name="revision_number_positive"
        ),
        Index(None, "owner_id", "memory_id"),
        Index(None, "owner_id", "document_evidence_id"),
    )


class DocumentEvidenceRefRow(Base):
    """The one sanctioned link from Personal Memory to Document Intelligence.

    Two sets of document identifiers (7.1 section 23.3, Phase 8.2 step 2):

    * ``document_id`` / ``version_id`` / ``chunk_id`` carry ``RESTRICT`` foreign
      keys, so a document cannot be deleted while active evidence points at it.
    * ``document_ref`` / ``version_ref`` / ``chunk_ref`` are opaque copies with no
      foreign key. They are never cleared, so provenance stays traceable.

    The deletion workflow sets ``status = 'source_deleted'``, which (by check
    constraint) requires the foreign-key columns to be NULL; only then can the
    document rows be removed.
    """

    __tablename__ = "pm_document_evidence_ref"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    candidate_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    document_ref: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    version_ref: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    chunk_ref: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    extraction_method: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    section_heading: Mapped[str | None] = mapped_column(Text)
    start_offset: Mapped[int | None] = mapped_column(Integer)
    end_offset: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("id", "owner_id"),
        ForeignKeyConstraint(
            ["candidate_id", "owner_id"],
            ["pm_memory_candidate.id", "pm_memory_candidate.owner_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["document_id", "owner_id"],
            ["doc_document.id", "doc_document.owner_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["version_id", "document_id"],
            ["doc_document_version.id", "doc_document_version.document_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["chunk_id", "version_id"],
            ["doc_chunk.id", "doc_chunk.version_id"],
            ondelete="RESTRICT",
        ),
        in_vocabulary("status", DocumentEvidenceStatus, name="status"),
        CheckConstraint(EVIDENCE_LINKS_MATCH_STATUS, name="links_match_status"),
        CheckConstraint("length(btrim(extraction_method)) > 0", name="extraction_method"),
        CheckConstraint("page_number IS NULL OR page_number >= 1", name="page_number"),
        CheckConstraint("start_offset IS NULL OR start_offset >= 0", name="start_offset"),
        CheckConstraint(
            "end_offset IS NULL OR (start_offset IS NOT NULL AND end_offset >= start_offset)",
            name="end_offset",
        ),
        Index(None, "owner_id", "document_ref"),
        Index(None, "owner_id", "candidate_id"),
    )
