"""SQLAlchemy models for Document Intelligence (Phase 8.2 step 2; 7.1 section 23.3).

Integrity enforced by PostgreSQL:

* Every row has ``owner_id``; parents are referenced through composite keys that
  include the owner or the parent version, so a row can never attach to another
  owner's document or mix two versions (memory/05 section 8.7).
* ``RESTRICT`` everywhere: deletion is an explicit, verified workflow (8.10).
* Representations, chunks and chunk locations are append-only. Versions,
  embeddings, operations and documents may change only their status columns
  (``me_guard_columns`` trigger, migration 0002).
* ``doc_chunk.tsv`` is a stored full-text vector using the language-neutral
  ``simple`` configuration (approved 2026-11-11; the language requirement G6 is
  still open).
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from memory_engine.documents.domain.vocabulary import (
    DocumentLifecycleStatus,
    DocumentMediaType,
    EmbeddingStatus,
    ExtractionStatus,
    OperationStatus,
    OperationType,
    VersionProcessingStatus,
)
from memory_engine.infrastructure.persistence.base import Base, in_vocabulary

Json = dict[str, Any]
SHA256_CHECK = "~ '^[0-9a-f]{64}$'"
TEXT_SEARCH_CONFIG = "simple"
SAFE_ERROR_CODE = "error_code IS NULL OR error_code ~ '^[A-Z][A-Z0-9_]{0,63}$'"


def _now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def _updated() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DocumentRow(Base):
    __tablename__ = "doc_document"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _updated()

    __table_args__ = (
        UniqueConstraint("id", "owner_id"),
        # The current version must be a version of this very document. use_alter:
        # the two tables reference each other, so this key is added after both exist.
        ForeignKeyConstraint(
            ["current_version_id", "id"],
            ["doc_document_version.id", "doc_document_version.document_id"],
            ondelete="RESTRICT",
            use_alter=True,
        ),
        in_vocabulary("media_type", DocumentMediaType, name="media_type"),
        in_vocabulary("lifecycle_status", DocumentLifecycleStatus, name="lifecycle_status"),
        CheckConstraint("length(btrim(original_filename)) > 0", name="original_filename"),
        CheckConstraint("title IS NULL OR length(btrim(title)) > 0", name="title"),
        Index(None, "owner_id", "lifecycle_status"),
    )


class DocumentVersionRow(Base):
    __tablename__ = "doc_document_version"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _updated()

    __table_args__ = (
        UniqueConstraint("id", "owner_id"),
        UniqueConstraint("id", "document_id"),
        UniqueConstraint("document_id", "version_number"),
        UniqueConstraint("object_key"),
        ForeignKeyConstraint(
            ["document_id", "owner_id"],
            ["doc_document.id", "doc_document.owner_id"],
            ondelete="RESTRICT",
        ),
        in_vocabulary("media_type", DocumentMediaType, name="media_type"),
        in_vocabulary("processing_status", VersionProcessingStatus, name="processing_status"),
        CheckConstraint("version_number >= 1", name="version_number"),
        CheckConstraint("size_bytes > 0", name="size_bytes"),
        CheckConstraint(f"content_sha256 {SHA256_CHECK}", name="content_sha256"),
        CheckConstraint("length(btrim(object_key)) > 0", name="object_key"),
        Index(None, "owner_id", "document_id"),
    )


class ExtractedRepresentationRow(Base):
    __tablename__ = "doc_extracted_representation"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    version_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    extraction_method: Mapped[str] = mapped_column(Text, nullable=False)
    extraction_version: Mapped[str] = mapped_column(Text, nullable=False)
    content_ref: Mapped[str | None] = mapped_column(Text)
    structure: Mapped[Json] = mapped_column(JSONB, nullable=False, server_default="{}")
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = _now()

    __table_args__ = (
        UniqueConstraint("id", "version_id"),
        ForeignKeyConstraint(
            ["version_id", "owner_id"],
            ["doc_document_version.id", "doc_document_version.owner_id"],
            ondelete="RESTRICT",
        ),
        in_vocabulary("status", ExtractionStatus, name="status"),
        CheckConstraint(SAFE_ERROR_CODE, name="error_code"),
        CheckConstraint(
            "(status = 'extraction_failed') = (error_code IS NOT NULL)", name="failure_has_code"
        ),
        Index(None, "owner_id", "version_id"),
    )


class DocumentChunkRow(Base):
    __tablename__ = "doc_chunk"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    version_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    representation_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    chunking_strategy: Mapped[str] = mapped_column(Text, nullable=False)
    chunking_version: Mapped[str] = mapped_column(Text, nullable=False)
    tsv: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(f"to_tsvector('{TEXT_SEARCH_CONFIG}'::regconfig, content)", persisted=True),
    )
    created_at: Mapped[datetime] = _now()

    __table_args__ = (
        UniqueConstraint("id", "version_id"),
        UniqueConstraint("representation_id", "sequence"),
        ForeignKeyConstraint(
            ["version_id", "owner_id"],
            ["doc_document_version.id", "doc_document_version.owner_id"],
            ondelete="RESTRICT",
        ),
        # The representation must belong to the same version as the chunk.
        ForeignKeyConstraint(
            ["representation_id", "version_id"],
            ["doc_extracted_representation.id", "doc_extracted_representation.version_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("sequence >= 0", name="sequence"),
        CheckConstraint("length(btrim(content)) > 0", name="content"),
        CheckConstraint(f"content_sha256 {SHA256_CHECK}", name="content_sha256"),
        Index(None, "owner_id", "version_id"),
        Index("ix_doc_chunk_tsv", "tsv", postgresql_using="gin"),
    )


class ChunkLocationRow(Base):
    __tablename__ = "doc_chunk_location"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    chunk_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    version_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    # Position of this location within its chunk (a chunk may span pages or sections).
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    section_heading: Mapped[str | None] = mapped_column(Text)
    start_offset: Mapped[int | None] = mapped_column(Integer)
    end_offset: Mapped[int | None] = mapped_column(Integer)
    structural_path: Mapped[list[str] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = _now()

    __table_args__ = (
        UniqueConstraint("chunk_id", "ordinal"),
        ForeignKeyConstraint(
            ["chunk_id", "version_id"],
            ["doc_chunk.id", "doc_chunk.version_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["version_id", "owner_id"],
            ["doc_document_version.id", "doc_document_version.owner_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("ordinal >= 0", name="ordinal"),
        CheckConstraint(
            "page_number IS NOT NULL OR section_heading IS NOT NULL"
            " OR start_offset IS NOT NULL OR structural_path IS NOT NULL",
            name="has_known_field",
        ),
        CheckConstraint("page_number IS NULL OR page_number >= 1", name="page_number"),
        CheckConstraint("start_offset IS NULL OR start_offset >= 0", name="start_offset"),
        CheckConstraint(
            "end_offset IS NULL OR (start_offset IS NOT NULL AND end_offset >= start_offset)",
            name="end_offset",
        ),
        Index(None, "owner_id", "chunk_id"),
    )


class DocumentEmbeddingRow(Base):
    __tablename__ = "doc_embedding"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    chunk_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    version_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    model_id: Mapped[str] = mapped_column(Text, nullable=False)
    model_revision: Mapped[str] = mapped_column(Text, nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    preprocessing_version: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _updated()

    __table_args__ = (
        # One embedding per chunk, model, revision and preprocessing: no duplicate work.
        UniqueConstraint(
            "chunk_id",
            "model_id",
            "model_revision",
            "preprocessing_version",
            name="uq_doc_embedding_chunk_model",  # the generated name exceeds 63 characters
        ),
        ForeignKeyConstraint(
            ["chunk_id", "version_id"],
            ["doc_chunk.id", "doc_chunk.version_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["version_id", "owner_id"],
            ["doc_document_version.id", "doc_document_version.owner_id"],
            ondelete="RESTRICT",
        ),
        in_vocabulary("status", EmbeddingStatus, name="status"),
        CheckConstraint("dimensions > 0", name="dimensions"),
        Index(None, "owner_id", "version_id"),
    )


class ProcessingOperationRow(Base):
    __tablename__ = "doc_processing_operation"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    operation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _updated()

    __table_args__ = (
        UniqueConstraint("owner_id", "idempotency_key"),
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
        in_vocabulary("operation_type", OperationType, name="operation_type"),
        in_vocabulary("status", OperationStatus, name="status"),
        CheckConstraint("attempts >= 0", name="attempts"),
        CheckConstraint(SAFE_ERROR_CODE, name="error_code"),
        CheckConstraint("length(btrim(idempotency_key)) > 0", name="idempotency_key"),
        Index(None, "owner_id", "document_id", "status"),
    )
