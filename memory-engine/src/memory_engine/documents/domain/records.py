"""Document Intelligence records (Phase 5.4 Document Intelligence amendment, section 3).

Records are immutable value objects. Versions, extracted representations,
chunks and chunk locations never change once written; only status fields of
documents, versions, embeddings and operations move, through repository
methods with an expected-current-state check.
"""

import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any

from memory_engine.documents.domain.vocabulary import (
    DocumentLifecycleStatus,
    DocumentMediaType,
    EmbeddingStatus,
    ExtractionStatus,
    OperationStatus,
    OperationType,
    VersionProcessingStatus,
)
from memory_engine.domain.errors import DomainValidationError

JsonMap = Mapping[str, Any]
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
MAX_FILENAME_LENGTH = 255


def _empty() -> JsonMap:
    return MappingProxyType({})


def _frozen(value: JsonMap) -> JsonMap:
    return MappingProxyType(dict(value))


def _require_aware(name: str, value: datetime | None) -> None:
    if value is not None and value.utcoffset() is None:
        raise DomainValidationError(f"{name} must be timezone-aware")


def _require_text(name: str, value: str) -> None:
    if not value.strip():
        raise DomainValidationError(f"{name} must not be empty")


def _require_sha256(name: str, value: str) -> None:
    if not _SHA256.fullmatch(value):
        raise DomainValidationError(f"{name} must be 64 lowercase hex characters")


def validate_error_code(value: str | None) -> None:
    """Error codes are stable UPPER_SNAKE_CASE identifiers, never free text.

    Free-text failure messages can carry document content into the database.
    """
    if value is not None and not _SAFE_CODE.fullmatch(value):
        raise DomainValidationError("error_code must be an UPPER_SNAKE_CASE code")


@dataclass(frozen=True, slots=True, kw_only=True)
class Document:
    """Identity of an uploaded document, independent of its filename (3.1)."""

    id: uuid.UUID
    owner_id: uuid.UUID
    original_filename: str
    media_type: DocumentMediaType
    lifecycle_status: DocumentLifecycleStatus
    current_version_id: uuid.UUID | None = None
    title: str | None = None

    def __post_init__(self) -> None:
        _require_text("original_filename", self.original_filename)
        if len(self.original_filename) > MAX_FILENAME_LENGTH:
            raise DomainValidationError("original_filename is too long")
        if self.title is not None:
            _require_text("title", self.title)


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentVersion:
    """One immutable content version of a document (3.2).

    ``object_key`` is the opaque object-storage reference of the original file
    (7.1 section 23.3); it never contains the filename.
    """

    id: uuid.UUID
    owner_id: uuid.UUID
    document_id: uuid.UUID
    version_number: int
    object_key: str
    content_sha256: str
    size_bytes: int
    media_type: DocumentMediaType
    uploaded_at: datetime
    processing_status: VersionProcessingStatus

    def __post_init__(self) -> None:
        if self.version_number < 1:
            raise DomainValidationError("version_number starts at 1")
        _require_text("object_key", self.object_key)
        _require_sha256("content_sha256", self.content_sha256)
        if self.size_bytes < 1:
            raise DomainValidationError("size_bytes must be positive; empty files are rejected")
        _require_aware("uploaded_at", self.uploaded_at)

    @staticmethod
    def object_key_for(owner_id: uuid.UUID, document_id: uuid.UUID, version_id: uuid.UUID) -> str:
        """The owner-partitioned key layout from the decision review (section 5.5)."""
        return f"documents/{owner_id}/{document_id}/{version_id}/original"


@dataclass(frozen=True, slots=True, kw_only=True)
class ExtractedRepresentation:
    """Content derived from one version by one extraction method (3.3)."""

    id: uuid.UUID
    owner_id: uuid.UUID
    version_id: uuid.UUID
    extraction_method: str
    extraction_version: str
    status: ExtractionStatus
    extracted_at: datetime
    content_ref: str | None = None
    structure: JsonMap = field(default_factory=_empty)
    error_code: str | None = None

    def __post_init__(self) -> None:
        _require_text("extraction_method", self.extraction_method)
        _require_text("extraction_version", self.extraction_version)
        _require_aware("extracted_at", self.extracted_at)
        validate_error_code(self.error_code)
        if (self.status is ExtractionStatus.EXTRACTION_FAILED) != (self.error_code is not None):
            raise DomainValidationError("an error_code is required exactly when extraction failed")
        object.__setattr__(self, "structure", _frozen(self.structure))


@dataclass(frozen=True, slots=True, kw_only=True)
class ChunkLocation:
    """Where a chunk came from (3.5). Unknown fields stay None, never guessed."""

    id: uuid.UUID
    page_number: int | None = None
    section_heading: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    structural_path: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if all(
            value is None
            for value in (
                self.page_number,
                self.section_heading,
                self.start_offset,
                self.structural_path,
            )
        ):
            raise DomainValidationError("a location must carry at least one known field")
        if self.page_number is not None and self.page_number < 1:
            raise DomainValidationError("page_number starts at 1")
        if self.start_offset is not None and self.start_offset < 0:
            raise DomainValidationError("start_offset must not be negative")
        if self.end_offset is not None and (
            self.start_offset is None or self.end_offset < self.start_offset
        ):
            raise DomainValidationError("end_offset requires a start_offset and must follow it")
        if self.structural_path is not None:
            object.__setattr__(self, "structural_path", tuple(self.structural_path))


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentChunk:
    """A retrieval unit derived from one representation of one version (3.4)."""

    id: uuid.UUID
    owner_id: uuid.UUID
    version_id: uuid.UUID
    representation_id: uuid.UUID
    sequence: int
    content: str
    content_sha256: str
    chunking_strategy: str
    chunking_version: str
    locations: Sequence[ChunkLocation] = ()

    def __post_init__(self) -> None:
        if self.sequence < 0:
            raise DomainValidationError("sequence must not be negative")
        _require_text("content", self.content)
        _require_sha256("content_sha256", self.content_sha256)
        _require_text("chunking_strategy", self.chunking_strategy)
        _require_text("chunking_version", self.chunking_version)
        object.__setattr__(self, "locations", tuple(self.locations))


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentEmbedding:
    """Embedding metadata for one chunk (3.6). Vectors arrive in Phase 8.7."""

    id: uuid.UUID
    owner_id: uuid.UUID
    chunk_id: uuid.UUID
    version_id: uuid.UUID
    model_id: str
    model_revision: str
    dimensions: int
    preprocessing_version: str
    status: EmbeddingStatus

    def __post_init__(self) -> None:
        _require_text("model_id", self.model_id)
        _require_text("model_revision", self.model_revision)
        _require_text("preprocessing_version", self.preprocessing_version)
        if self.dimensions < 1:
            raise DomainValidationError("dimensions must be positive")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessingOperation:
    """A durable, idempotent processing step for a document or version (3.7)."""

    id: uuid.UUID
    owner_id: uuid.UUID
    document_id: uuid.UUID
    operation_type: OperationType
    status: OperationStatus
    idempotency_key: str
    version_id: uuid.UUID | None = None
    attempts: int = 0
    error_code: str | None = None

    def __post_init__(self) -> None:
        _require_text("idempotency_key", self.idempotency_key)
        if len(self.idempotency_key) > 200:
            raise DomainValidationError("idempotency_key is too long")
        if self.attempts < 0:
            raise DomainValidationError("attempts must not be negative")
        validate_error_code(self.error_code)


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentDependencies:
    """Everything derived from a document that deletion must cover (5.4 amendment section 9).

    Personal-memory evidence that references the document is discovered
    separately, by the Personal Memory domain (it never lives in this package).
    """

    document_id: uuid.UUID
    version_ids: tuple[uuid.UUID, ...]
    object_keys: tuple[str, ...]
    representation_ids: tuple[uuid.UUID, ...]
    representation_content_refs: tuple[str, ...]
    chunk_ids: tuple[uuid.UUID, ...]
    chunk_location_count: int
    embedding_ids: tuple[uuid.UUID, ...]
    open_operation_ids: tuple[uuid.UUID, ...]
