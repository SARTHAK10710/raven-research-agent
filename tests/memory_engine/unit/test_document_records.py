"""Domain invariants of Document Intelligence records (no database)."""

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from memory_engine.documents.domain import (
    ChunkLocation,
    Document,
    DocumentChunk,
    DocumentEmbedding,
    DocumentVersion,
    ExtractedRepresentation,
    ProcessingOperation,
)
from memory_engine.documents.domain.records import validate_error_code
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
from memory_engine.domain.identifiers import new_id
from memory_engine.domain.vocabulary import DocumentEvidenceStatus
from memory_engine.personal.domain import DocumentEvidenceRef

T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
OWNER = uuid.UUID("00000000-0000-4000-8000-000000000002")
SHA = "b" * 64


def version(**overrides: Any) -> DocumentVersion:
    values: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "document_id": new_id(),
        "version_number": 1,
        "object_key": "documents/o/d/v/original",
        "content_sha256": SHA,
        "size_bytes": 10,
        "media_type": DocumentMediaType.PDF,
        "uploaded_at": T0,
        "processing_status": VersionProcessingStatus.REGISTERED,
    }
    return DocumentVersion(**{**values, **overrides})


def chunk(**overrides: Any) -> DocumentChunk:
    values: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "version_id": new_id(),
        "representation_id": new_id(),
        "sequence": 0,
        "content": "Synthetic paragraph.",
        "content_sha256": SHA,
        "chunking_strategy": "structure_aware",
        "chunking_version": "1",
    }
    return DocumentChunk(**{**values, **overrides})


def test_document_identity_does_not_depend_on_filename() -> None:
    first = Document(
        id=new_id(),
        owner_id=OWNER,
        original_filename="report.pdf",
        media_type=DocumentMediaType.PDF,
        lifecycle_status=DocumentLifecycleStatus.REGISTERED,
    )
    second = Document(
        id=new_id(),
        owner_id=OWNER,
        original_filename="report.pdf",
        media_type=DocumentMediaType.PDF,
        lifecycle_status=DocumentLifecycleStatus.REGISTERED,
    )
    assert first.id != second.id
    with pytest.raises(DomainValidationError):
        Document(
            id=new_id(),
            owner_id=OWNER,
            original_filename=" ",
            media_type=DocumentMediaType.TXT,
            lifecycle_status=DocumentLifecycleStatus.REGISTERED,
        )
    with pytest.raises(DomainValidationError, match="too long"):
        Document(
            id=new_id(),
            owner_id=OWNER,
            original_filename="a" * 256,
            media_type=DocumentMediaType.TXT,
            lifecycle_status=DocumentLifecycleStatus.REGISTERED,
        )


def test_only_pdf_docx_and_txt_are_supported() -> None:
    assert {m.value for m in DocumentMediaType} == {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("version_number", 0),
        ("size_bytes", 0),
        ("content_sha256", "XYZ"),
        ("object_key", " "),
        ("uploaded_at", datetime(2026, 1, 1)),  # naive
    ],
)
def test_version_invariants(field: str, value: object) -> None:
    with pytest.raises(DomainValidationError):
        version(**{field: value})


def test_object_keys_are_owner_partitioned_and_never_use_filenames() -> None:
    owner, document, ver = new_id(), new_id(), new_id()
    key = DocumentVersion.object_key_for(owner, document, ver)
    assert key == f"documents/{owner}/{document}/{ver}/original"


def test_failed_extraction_needs_a_safe_error_code() -> None:
    base: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "version_id": new_id(),
        "extraction_method": "pypdf",
        "extraction_version": "1",
        "extracted_at": T0,
    }
    ExtractedRepresentation(**base, status=ExtractionStatus.EXTRACTED)
    ExtractedRepresentation(
        **base, status=ExtractionStatus.EXTRACTION_FAILED, error_code="ENCRYPTED_PDF"
    )
    with pytest.raises(DomainValidationError, match="exactly when"):
        ExtractedRepresentation(**base, status=ExtractionStatus.EXTRACTION_FAILED)
    with pytest.raises(DomainValidationError, match="exactly when"):
        ExtractedRepresentation(**base, status=ExtractionStatus.EXTRACTED, error_code="X")
    with pytest.raises(DomainValidationError, match="UPPER_SNAKE_CASE"):
        ExtractedRepresentation(
            **base, status=ExtractionStatus.EXTRACTION_FAILED, error_code="page 3 said hello"
        )


def test_error_codes_never_carry_free_text() -> None:
    validate_error_code(None)
    validate_error_code("TIMEOUT")
    for bad in ("timeout", "TIME OUT", "A" * 65, "1ABC"):
        with pytest.raises(DomainValidationError):
            validate_error_code(bad)


def test_chunk_invariants() -> None:
    with pytest.raises(DomainValidationError):
        chunk(sequence=-1)
    with pytest.raises(DomainValidationError):
        chunk(content="   ")
    assert isinstance(chunk(locations=[ChunkLocation(id=new_id(), page_number=1)]).locations, tuple)


def test_missing_location_metadata_stays_unknown_not_fabricated() -> None:
    with pytest.raises(DomainValidationError, match="at least one known field"):
        ChunkLocation(id=new_id())
    location = ChunkLocation(id=new_id(), section_heading="Results")
    assert location.page_number is None
    with pytest.raises(DomainValidationError):
        ChunkLocation(id=new_id(), page_number=0)
    with pytest.raises(DomainValidationError):
        ChunkLocation(id=new_id(), start_offset=10, end_offset=5)
    with pytest.raises(DomainValidationError):
        ChunkLocation(id=new_id(), page_number=1, end_offset=5)


def test_embedding_and_operation_invariants() -> None:
    with pytest.raises(DomainValidationError):
        DocumentEmbedding(
            id=new_id(),
            owner_id=OWNER,
            chunk_id=new_id(),
            version_id=new_id(),
            model_id="m",
            model_revision="r",
            dimensions=0,
            preprocessing_version="p",
            status=EmbeddingStatus.PENDING,
        )
    with pytest.raises(DomainValidationError):
        ProcessingOperation(
            id=new_id(),
            owner_id=OWNER,
            document_id=new_id(),
            operation_type=OperationType.CHUNKING,
            status=OperationStatus.CREATED,
            idempotency_key=" ",
        )


def test_open_operation_states() -> None:
    assert {s for s in OperationStatus if not s.open} == {
        OperationStatus.COMPLETED,
        OperationStatus.FAILED,
        OperationStatus.CANCELLED,
    }


def test_only_available_documents_are_retrievable() -> None:
    assert [s for s in DocumentLifecycleStatus if s.retrievable] == [
        DocumentLifecycleStatus.AVAILABLE
    ]


def test_document_evidence_reference_invariants() -> None:
    base: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "candidate_id": new_id(),
        "document_ref": new_id(),
        "version_ref": new_id(),
        "extraction_method": "manual_authorized_extraction",
        "status": DocumentEvidenceStatus.ACTIVE,
        "recorded_at": T0,
    }
    DocumentEvidenceRef(**base, page_number=3)
    with pytest.raises(DomainValidationError):
        DocumentEvidenceRef(**{**base, "extraction_method": " "})
    with pytest.raises(DomainValidationError):
        DocumentEvidenceRef(**base, start_offset=5, end_offset=1)
    with pytest.raises(DomainValidationError):
        DocumentEvidenceRef(**base, page_number=0)
