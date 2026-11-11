"""Document Intelligence vocabularies, enforced again by database check constraints.

Approved 2026-11-11 and recorded in the Phase 5.4 Document Intelligence
amendment, section 14 ("Persisted vocabularies"). Sources: 5.10 sections
6.1-6.3, 5.4 amendment section 7, Decision 5.4.20, memory/05 section 3, and the
security rule restricting formats to PDF, DOCX and TXT.

Do not add values without an approved specification change.
"""

from enum import StrEnum


class DocumentMediaType(StrEnum):
    """The only accepted formats, by validated content type (not file extension)."""

    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    TXT = "text/plain"


class DocumentLifecycleStatus(StrEnum):
    """Availability and deletion state of a document (5.10 section 6.1).

    Distinct from processing status: a document can be available while optional
    derived processing is still incomplete.
    """

    REGISTERED = "registered"
    AVAILABLE = "available"
    DELETION_REQUESTED = "deletion_requested"
    DELETING = "deleting"
    DELETED = "deleted"

    @property
    def retrievable(self) -> bool:
        """Only available documents may contribute retrieval results."""
        return self is DocumentLifecycleStatus.AVAILABLE


class VersionProcessingStatus(StrEnum):
    """Processing state of one document version (5.4 amendment section 7; 5.10 section 6.2).

    ``superseded`` is deliberately absent: whether a version is current is
    derived from the document's current-version reference, never stored twice.
    """

    REGISTERED = "registered"
    VALIDATED = "validated"
    STORED = "stored"
    PARSING = "parsing"
    EXTRACTED = "extracted"
    CHUNKED = "chunked"
    EMBEDDED = "embedded"
    INDEXED = "indexed"
    VALIDATION_FAILED = "validation_failed"
    EXTRACTION_FAILED = "extraction_failed"
    PROCESSING_FAILED = "processing_failed"
    RETRY_PENDING = "retry_pending"
    DELETION_REQUESTED = "deletion_requested"
    DELETING = "deleting"
    DELETED = "deleted"


class ExtractionStatus(StrEnum):
    """Outcome recorded on an Extracted Document Representation."""

    EXTRACTED = "extracted"
    PARTIALLY_EXTRACTED = "partially_extracted"
    EXTRACTION_FAILED = "extraction_failed"


class EmbeddingStatus(StrEnum):
    """Embedding metadata lifecycle (Decision 5.4.20)."""

    PENDING = "pending"
    GENERATING = "generating"
    GENERATED = "generated"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"
    SUPERSEDED = "superseded"
    DELETION_PENDING = "deletion_pending"


class OperationType(StrEnum):
    """Document pipeline stages, each independently traceable (memory/05 section 3)."""

    VALIDATION = "validation"
    STORAGE = "storage"
    EXTRACTION = "extraction"
    STRUCTURE_EXTRACTION = "structure_extraction"
    NORMALIZATION = "normalization"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    DELETION = "deletion"


class OperationStatus(StrEnum):
    """Processing operation lifecycle (5.10 section 6.3)."""

    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY_PENDING = "retry_pending"
    CANCELLATION_REQUESTED = "cancellation_requested"
    CANCELLED = "cancelled"

    @property
    def open(self) -> bool:
        """Work that a deletion must stop or wait for (memory/05 section 18)."""
        return self not in (
            OperationStatus.COMPLETED,
            OperationStatus.FAILED,
            OperationStatus.CANCELLED,
        )
