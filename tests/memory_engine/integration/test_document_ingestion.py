"""Phase 8.3 step 3: document ingestion against real PostgreSQL.

Object storage is the in-memory fake. All files are synthetic.
"""

import io
from datetime import UTC, datetime
from typing import Any

import pytest

from memory_engine.documents.application.ingestion import (
    DocumentIngestionService,
    DocumentUpload,
)
from memory_engine.documents.domain.vocabulary import (
    DocumentLifecycleStatus,
    DocumentMediaType,
    OperationStatus,
    OperationType,
    VersionProcessingStatus,
)
from memory_engine.domain.errors import OwnershipError
from memory_engine.domain.identifiers import OwnerScope, new_id
from memory_engine.exceptions import (
    DeletionInProgressError,
    IdempotencyKeyReusedError,
    IngestionRejectedError,
    ObjectStorageError,
    PersistenceError,
    RecordNotFoundError,
)
from memory_engine.infrastructure.object_storage import InMemoryObjectStorage
from memory_engine.infrastructure.persistence import SqlAlchemyDocumentUnitOfWorkFactory
from memory_engine.infrastructure.persistence.documents.repositories import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyProcessingOperationRepository,
)

pytestmark = pytest.mark.integration

DocUow = SqlAlchemyDocumentUnitOfWorkFactory
T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
PDF = b"%PDF-1.7\nsynthetic\n%%EOF\n"
PDF_V2 = b"%PDF-1.7\nsynthetic, revised\n%%EOF\n"


def _service(uow: DocUow, storage: Any, limit: int = 1024 * 1024) -> DocumentIngestionService:
    return DocumentIngestionService(uow, storage, max_upload_bytes=limit, clock=lambda: T0)


def _upload(
    owner: OwnerScope, key: str = "up-1", data: bytes = PDF, **extra: Any
) -> DocumentUpload:
    values: dict[str, Any] = {
        "owner_id": owner.owner_id,
        "idempotency_key": key,
        "filename": "Synthetic report.pdf",
        "data": io.BytesIO(data),
    }
    return DocumentUpload(**values | extra)


def _keys(storage: InMemoryObjectStorage) -> set[str]:
    return set(storage._objects)  # test-only inspection of the fake


def test_an_upload_is_stored_registered_and_handed_an_operation(
    doc_uow_factory: DocUow, owner: OwnerScope
) -> None:
    storage = InMemoryObjectStorage()
    result = _service(doc_uow_factory, storage).ingest(owner, _upload(owner, title="Q3 notes"))
    assert result.created and result.version_number == 1
    assert result.media_type is DocumentMediaType.PDF
    with doc_uow_factory() as uow:
        document = uow.documents.get(owner, result.document_id)
        version = uow.documents.get_version(owner, result.version_id)
        operation = uow.operations.get(owner, result.operation_id)
    assert document is not None and version is not None and operation is not None
    assert document.lifecycle_status is DocumentLifecycleStatus.REGISTERED
    assert (document.original_filename, document.title) == ("Synthetic report.pdf", "Q3 notes")
    assert version.processing_status is VersionProcessingStatus.STORED  # not "processed"
    assert (operation.operation_type, operation.status) == (
        OperationType.EXTRACTION,
        OperationStatus.CREATED,
    )
    assert operation.version_id == version.id
    assert storage.get(owner, version.object_key) == PDF
    assert "Synthetic report" not in version.object_key  # filenames never become keys


def test_identical_content_uploaded_again_is_a_separate_document(
    doc_uow_factory: DocUow, owner: OwnerScope
) -> None:
    service = _service(doc_uow_factory, InMemoryObjectStorage())
    first = service.ingest(owner, _upload(owner, "up-1"))
    second = service.ingest(owner, _upload(owner, "up-2"))
    assert first.document_id != second.document_id and second.created


def test_a_retry_returns_the_same_registration(doc_uow_factory: DocUow, owner: OwnerScope) -> None:
    storage = InMemoryObjectStorage()
    service = _service(doc_uow_factory, storage)
    first = service.ingest(owner, _upload(owner))
    stored = _keys(storage)
    again = service.ingest(owner, _upload(owner))
    assert (again.document_id, again.version_id, again.created) == (
        first.document_id,
        first.version_id,
        False,
    )
    assert _keys(storage) == stored
    with pytest.raises(IdempotencyKeyReusedError):
        service.ingest(owner, _upload(owner, data=PDF_V2))
    with pytest.raises(IdempotencyKeyReusedError):
        service.ingest(owner, _upload(owner, filename="Other.pdf"))
    assert _keys(storage) == stored


def test_a_new_version_is_added_to_a_named_document(
    doc_uow_factory: DocUow, owner: OwnerScope
) -> None:
    storage = InMemoryObjectStorage()
    service = _service(doc_uow_factory, storage)
    first = service.ingest(owner, _upload(owner, "up-1"))
    second = service.ingest(
        owner, _upload(owner, "up-2", data=PDF_V2, document_id=first.document_id)
    )
    assert (second.document_id, second.version_number) == (first.document_id, 2)
    with doc_uow_factory() as uow:
        document = uow.documents.get(owner, first.document_id)
        versions = uow.documents.list_versions(owner, first.document_id)
    assert document is not None and document.current_version_id == second.version_id
    assert [v.version_number for v in versions] == [1, 2]  # history kept
    with pytest.raises(IngestionRejectedError) as caught:
        service.ingest(owner, _upload(owner, "up-3", data=PDF_V2, document_id=first.document_id))
    assert caught.value.details["reason"] == "DUPLICATE_VERSION"
    with pytest.raises(IngestionRejectedError) as caught:
        service.ingest(
            owner,
            _upload(
                owner,
                "up-4",
                data=b"plain text now",
                filename="notes.txt",
                document_id=first.document_id,
            ),
        )
    assert caught.value.details["reason"] == "MEDIA_TYPE_CHANGED"


def test_uploads_are_owner_scoped(
    doc_uow_factory: DocUow, owner: OwnerScope, other_owner: OwnerScope
) -> None:
    storage = InMemoryObjectStorage()
    service = _service(doc_uow_factory, storage)
    mine = service.ingest(owner, _upload(owner))
    with pytest.raises(RecordNotFoundError):
        service.ingest(
            other_owner, _upload(other_owner, "up-x", data=PDF_V2, document_id=mine.document_id)
        )
    with pytest.raises(OwnershipError):
        service.ingest(owner, _upload(other_owner, "up-y"))
    theirs = service.ingest(other_owner, _upload(other_owner, "up-1"))  # same key, other owner
    assert theirs.created and theirs.document_id != mine.document_id


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"data": b""}, "EMPTY_FILE"),
        ({"filename": "report.docx"}, "EXTENSION_MISMATCH"),
        ({"data": b"%PDF-1.7\ncut off"}, "MALFORMED_DOCUMENT"),
        ({"data": PDF + b"x" * 2048}, "FILE_TOO_LARGE"),
        ({"key": " "}, "INVALID_IDEMPOTENCY_KEY"),
    ],
)
def test_rejected_uploads_store_and_register_nothing(
    doc_uow_factory: DocUow, owner: OwnerScope, overrides: dict[str, Any], reason: str
) -> None:
    storage = InMemoryObjectStorage()
    with pytest.raises(IngestionRejectedError) as caught:
        _service(doc_uow_factory, storage, limit=1024).ingest(owner, _upload(owner, **overrides))
    assert caught.value.details["reason"] == reason
    assert _keys(storage) == set()


def test_a_storage_outage_registers_nothing(doc_uow_factory: DocUow, owner: OwnerScope) -> None:
    storage = InMemoryObjectStorage()
    storage.available = False
    with pytest.raises(ObjectStorageError):
        _service(doc_uow_factory, storage).ingest(owner, _upload(owner))
    with doc_uow_factory() as uow:
        assert uow.operations.find_by_idempotency_key(owner, "upload:up-1") is None


def test_a_failed_registration_removes_the_stored_original(
    doc_uow_factory: DocUow, owner: OwnerScope, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = InMemoryObjectStorage()

    def fail(self: Any, *args: Any, **kwargs: Any) -> None:
        raise PersistenceError("simulated database failure")

    monkeypatch.setattr(SqlAlchemyDocumentRepository, "register", fail)
    with pytest.raises(PersistenceError):
        _service(doc_uow_factory, storage).ingest(owner, _upload(owner))
    assert _keys(storage) == set()


def test_a_lost_race_on_the_same_key_returns_the_winner(
    doc_uow_factory: DocUow, owner: OwnerScope, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = InMemoryObjectStorage()
    service = _service(doc_uow_factory, storage)
    winner = service.ingest(owner, _upload(owner))
    winner_keys = _keys(storage)
    original = SqlAlchemyProcessingOperationRepository.find_by_idempotency_key
    calls = {"n": 0}

    def find_late(self: Any, scope: OwnerScope, key: str) -> Any:
        calls["n"] += 1
        return None if calls["n"] == 1 else original(self, scope, key)

    monkeypatch.setattr(
        SqlAlchemyProcessingOperationRepository, "find_by_idempotency_key", find_late
    )
    loser = service.ingest(owner, _upload(owner))
    assert (loser.document_id, loser.created) == (winner.document_id, False)
    assert _keys(storage) == winner_keys  # the loser's original was removed
    with doc_uow_factory() as uow:  # and its document rolled back
        assert uow.documents.get(owner, winner.document_id) is not None


def test_a_document_being_deleted_takes_no_new_version(
    doc_uow_factory: DocUow, owner: OwnerScope
) -> None:
    storage = InMemoryObjectStorage()
    service = _service(doc_uow_factory, storage)
    first = service.ingest(owner, _upload(owner))
    with doc_uow_factory() as uow:
        uow.documents.set_lifecycle_status(
            owner,
            first.document_id,
            DocumentLifecycleStatus.DELETION_REQUESTED,
            expected=DocumentLifecycleStatus.REGISTERED,
        )
    stored = _keys(storage)
    with pytest.raises(DeletionInProgressError):
        service.ingest(owner, _upload(owner, "up-2", data=PDF_V2, document_id=first.document_id))
    assert _keys(storage) == stored
    with pytest.raises(RecordNotFoundError):
        service.ingest(owner, _upload(owner, "up-3", data=PDF_V2, document_id=new_id()))
