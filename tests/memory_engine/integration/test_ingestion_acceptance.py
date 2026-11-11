"""Phase 8.3 step 5: the remaining plan 8.3 section 12 cases, end to end on PostgreSQL.

Unauthorized requests (as an owner-scope mismatch; authentication belongs to
the Entry layer, owner decision 2026-11-12), retry after failure, retry after
partial completion, all three formats registered and handed off, and the
separation of personal memory and document ingestion. Synthetic data only.
"""

import io
import zipfile
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import Connection, func, select

from memory_engine.documents.application.ingestion import (
    DocumentIngestionService,
    DocumentUpload,
)
from memory_engine.documents.domain.vocabulary import DocumentMediaType, OperationStatus
from memory_engine.domain.errors import OwnershipError
from memory_engine.domain.handoff import HandoffKind
from memory_engine.domain.identifiers import OwnerScope
from memory_engine.domain.vocabulary import SourceProcessingStatus, SourceType
from memory_engine.exceptions import ObjectStorageError, PersistenceError
from memory_engine.infrastructure.object_storage import InMemoryObjectStorage
from memory_engine.infrastructure.persistence import (
    SqlAlchemyDocumentUnitOfWorkFactory,
    SqlAlchemyPersonalUnitOfWorkFactory,
)
from memory_engine.infrastructure.persistence.documents.models import (
    DocumentRow,
    ProcessingOperationRow,
)
from memory_engine.infrastructure.persistence.documents.repositories import (
    SqlAlchemyDocumentRepository,
)
from memory_engine.infrastructure.persistence.outbox import OutboxRow
from memory_engine.infrastructure.persistence.personal.models import MemorySourceRow
from memory_engine.personal.application.ingestion import (
    IngestionLimits,
    IngestionRequest,
    PersonalIngestionService,
)

pytestmark = pytest.mark.integration

Uow = SqlAlchemyPersonalUnitOfWorkFactory
DocUow = SqlAlchemyDocumentUnitOfWorkFactory
T0 = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
LIMITS = IngestionLimits(
    max_text_bytes=256 * 1024, max_conversation_messages=1000, max_conversation_bytes=4 * 1024**2
)
PDF = b"%PDF-1.7\nsynthetic\n%%EOF\n"
TXT = "Synthetic notes: café.\n".encode()


def _docx() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<w:document/>")
    return buffer.getvalue()


def _personal(uow: Uow, storage: Any) -> PersonalIngestionService:
    return PersonalIngestionService(uow, storage, LIMITS, clock=lambda: T0)


def _documents(uow: DocUow, storage: Any) -> DocumentIngestionService:
    return DocumentIngestionService(uow, storage, max_upload_bytes=1024 * 1024, clock=lambda: T0)


def _text(owner: OwnerScope, key: str = "k-1") -> IngestionRequest:
    return IngestionRequest(
        owner_id=owner.owner_id,
        idempotency_key=key,
        source_type=SourceType.TEXT,
        text="Synthetic note for the acceptance tests.",
    )


def _upload(
    owner: OwnerScope, key: str = "u-1", data: bytes = PDF, filename: str = "s.pdf"
) -> DocumentUpload:
    return DocumentUpload(
        owner_id=owner.owner_id, idempotency_key=key, filename=filename, data=io.BytesIO(data)
    )


def _count(connection: Connection, table: Any, owner: OwnerScope) -> int:
    return int(
        connection.scalar(
            select(func.count()).select_from(table).where(table.owner_id == owner.owner_id)
        )
        or 0
    )


def _outbox_kinds(connection: Connection, owner: OwnerScope) -> list[str]:
    return sorted(
        connection.scalars(select(OutboxRow.kind).where(OutboxRow.owner_id == owner.owner_id))
    )


# --- 12.1 / 12.2: unauthorized (scope mismatch) ------------------------------------------


def test_an_unauthorized_caller_stores_registers_and_hands_off_nothing(
    uow_factory: Uow,
    doc_uow_factory: DocUow,
    connection: Connection,
    owner: OwnerScope,
    other_owner: OwnerScope,
) -> None:
    storage = InMemoryObjectStorage()
    with pytest.raises(OwnershipError):
        _personal(uow_factory, storage).ingest(owner, _text(other_owner))
    with pytest.raises(OwnershipError):
        _documents(doc_uow_factory, storage).ingest(owner, _upload(other_owner))
    assert storage._objects == {}  # test-only inspection of the fake
    for scope in (owner, other_owner):
        assert _count(connection, MemorySourceRow, scope) == 0
        assert _count(connection, DocumentRow, scope) == 0
        assert _outbox_kinds(connection, scope) == []


# --- 12.1: retry after failure -----------------------------------------------------------


def test_a_retry_after_a_failure_registers_and_hands_off_once(
    uow_factory: Uow, connection: Connection, owner: OwnerScope
) -> None:
    storage = InMemoryObjectStorage()
    storage.available = False
    with pytest.raises(ObjectStorageError):
        _personal(uow_factory, storage).ingest(owner, _text(owner))
    storage.available = True
    first = _personal(uow_factory, storage).ingest(owner, _text(owner))
    again = _personal(uow_factory, storage).ingest(owner, _text(owner))
    assert first.created and not again.created and again.source_id == first.source_id
    assert first.status is SourceProcessingStatus.VALIDATED
    assert _count(connection, MemorySourceRow, owner) == 1
    assert _outbox_kinds(connection, owner) == ["personal_extraction"]
    assert len(storage._objects) == 2  # original and normalized, once


# --- 12.2: retry after partial completion ------------------------------------------------


def test_a_retry_after_partial_completion_registers_one_document(
    doc_uow_factory: DocUow,
    connection: Connection,
    owner: OwnerScope,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = InMemoryObjectStorage()
    original = SqlAlchemyDocumentRepository.register

    def fail_once(self: Any, *args: Any, **kwargs: Any) -> None:
        monkeypatch.setattr(SqlAlchemyDocumentRepository, "register", original)
        raise PersistenceError("synthetic failure after the upload")

    monkeypatch.setattr(SqlAlchemyDocumentRepository, "register", fail_once)
    with pytest.raises(PersistenceError):
        _documents(doc_uow_factory, storage).ingest(owner, _upload(owner))
    assert storage._objects == {}  # the stored original was removed

    result = _documents(doc_uow_factory, storage).ingest(owner, _upload(owner))
    assert result.created
    assert _count(connection, DocumentRow, owner) == 1
    assert _count(connection, ProcessingOperationRow, owner) == 1
    assert _outbox_kinds(connection, owner) == ["document_extraction"]
    assert list(storage._objects) == [
        f"documents/{owner.owner_id}/{result.document_id}/{result.version_id}/original"
    ]


# --- 12.2: valid PDF, DOCX and TXT ---------------------------------------------------------


@pytest.mark.parametrize(
    ("data", "filename", "media_type"),
    [
        (PDF, "report.pdf", DocumentMediaType.PDF),
        (_docx(), "report.docx", DocumentMediaType.DOCX),
        (TXT, "notes.txt", DocumentMediaType.TXT),
    ],
    ids=["pdf", "docx", "txt"],
)
def test_each_supported_format_is_stored_registered_and_queued_for_handoff(
    doc_uow_factory: DocUow,
    connection: Connection,
    owner: OwnerScope,
    data: bytes,
    filename: str,
    media_type: DocumentMediaType,
) -> None:
    storage = InMemoryObjectStorage()
    result = _documents(doc_uow_factory, storage).ingest(
        owner, _upload(owner, data=data, filename=filename)
    )
    assert result.media_type is media_type
    with doc_uow_factory() as uow:
        operation = uow.operations.get(owner, result.operation_id)
        [message] = uow.outbox.for_subject(owner, result.operation_id)
    assert operation is not None and operation.status is OperationStatus.CREATED
    assert message.envelope.payload["media_type"] == media_type.value
    # The original reference stays valid.
    assert storage.get(owner, message.envelope.payload_reference or "") == data


# --- 12.3: personal memory and document ingestion remain separate ---------------------------


def test_personal_and_document_ingestion_stay_separate(
    uow_factory: Uow,
    doc_uow_factory: DocUow,
    connection: Connection,
    owner: OwnerScope,
) -> None:
    storage = InMemoryObjectStorage()
    document = _documents(doc_uow_factory, storage).ingest(owner, _upload(owner))
    # A document upload creates no Memory Source (Decision 13; architecture rules).
    assert _count(connection, MemorySourceRow, owner) == 0
    source = _personal(uow_factory, storage).ingest(owner, _text(owner))
    # A personal source creates no document records.
    assert _count(connection, DocumentRow, owner) == 1
    with uow_factory() as uow:
        [personal] = uow.outbox.for_subject(owner, source.source_id)
        [doc] = uow.outbox.for_subject(owner, document.operation_id)
    assert personal.kind is HandoffKind.PERSONAL_EXTRACTION
    assert doc.kind is HandoffKind.DOCUMENT_EXTRACTION
    assert personal.envelope.destination_component != doc.envelope.destination_component
    assert "document_id" not in personal.envelope.payload
    assert "source_id" not in doc.envelope.payload
    keys = {k.split("/")[0] for k in storage._objects}
    assert keys == {"documents", "memory-sources"}  # separate object-key areas
