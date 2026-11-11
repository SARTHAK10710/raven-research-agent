"""Document ingestion: acceptance and registration (plan 8.3 section 6; Decision 13).

Ingestion accepts an upload; it never parses it. Flow, with the owner's step-3
choices:

1. Owner check; read at most ``max_upload_bytes`` (25 MiB by default).
2. Detect the actual format (PDF, DOCX, TXT) from content; the extension and any
   declared type must agree. Compute the SHA-256.
3. Replay: a known idempotency key returns the earlier registration, or raises
   :class:`IdempotencyKeyReusedError` if the upload differs.
4. Without ``document_id`` the upload is always a new document, even when its
   content matches another (plan 8.3 section 8). With ``document_id`` it becomes
   the next version, refused when identical to the current one.
5. Store the original under its owner-partitioned key, then, in one
   transaction, register the document or version (``stored``), create the
   ``extraction`` operation for the document pipeline (``created``) and record
   its handoff in the outbox (8.3 step 4). If that fails, the stored object is
   removed (7.2 section 11).

The outbox relay later publishes the handoff and only then moves the operation
to ``queued``; nothing here reports processing as started or complete.
No malware scan runs (none is approved; recorded as a known constraint).
"""

import contextlib
import hashlib
import io
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import BinaryIO

from memory_engine.documents.application.formats import (
    check_declared,
    detect_media_type,
    reject,
    safe_filename,
)
from memory_engine.documents.application.ports import (
    DocumentUnitOfWork,
    DocumentUnitOfWorkFactory,
)
from memory_engine.documents.domain import Document, DocumentVersion, ProcessingOperation
from memory_engine.documents.domain.vocabulary import (
    DocumentLifecycleStatus,
    DocumentMediaType,
    OperationStatus,
    OperationType,
    VersionProcessingStatus,
)
from memory_engine.domain.errors import OwnershipError
from memory_engine.domain.handoff import HandoffKind, OutboxMessage
from memory_engine.domain.identifiers import OwnerScope, new_id
from memory_engine.domain.object_storage import ObjectStorage
from memory_engine.exceptions import (
    ConcurrencyConflictError,
    DeletionInProgressError,
    IdempotencyKeyReusedError,
    ObjectStorageError,
    PersistenceError,
    RecordNotFoundError,
)

_KEY_PREFIX = "upload:"
_MAX_KEY = 200 - len(_KEY_PREFIX)
_WRITABLE = (DocumentLifecycleStatus.REGISTERED, DocumentLifecycleStatus.AVAILABLE)


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentUpload:
    """An upload request. ``data`` is read once, up to the size limit."""

    owner_id: uuid.UUID
    idempotency_key: str
    filename: str
    data: BinaryIO
    declared_media_type: DocumentMediaType | None = None
    document_id: uuid.UUID | None = None  # set to add a version to an existing document
    title: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentIngestionResult:
    """Accepted and stored; processing has not started (plan 8.3 section 9)."""

    document_id: uuid.UUID
    version_id: uuid.UUID
    version_number: int
    operation_id: uuid.UUID
    media_type: DocumentMediaType
    version_status: VersionProcessingStatus
    created: bool


@dataclass(frozen=True, slots=True)
class _Checked:
    content: bytes
    media_type: DocumentMediaType
    sha256: str
    filename: str


class _LostRaceError(Exception):
    def __init__(self, operation: ProcessingOperation) -> None:
        self.operation = operation


def _utc_now() -> datetime:
    return datetime.now(UTC)


def extraction_handoff(
    scope: OwnerScope, operation: ProcessingOperation, version: DocumentVersion
) -> OutboxMessage:
    """The handoff of a registered version to the document pipeline (plan 8.12 section 6.3)."""
    return OutboxMessage.new(
        scope,
        kind=HandoffKind.DOCUMENT_EXTRACTION,
        subject_id=operation.id,
        payload={
            "document_id": str(version.document_id),
            "version_id": str(version.id),
            "operation_id": str(operation.id),
            "operation_type": operation.operation_type.value,
            "media_type": version.media_type.value,
            "content_sha256": version.content_sha256,
            "size_bytes": str(version.size_bytes),
        },
        payload_reference=version.object_key,
        priority="normal",
        created_at=version.uploaded_at,
    )


class DocumentIngestionService:
    def __init__(
        self,
        uow_factory: DocumentUnitOfWorkFactory,
        storage: ObjectStorage,
        *,
        max_upload_bytes: int,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._uow_factory = uow_factory
        self._storage = storage
        self._max_upload_bytes = max_upload_bytes
        self._now = clock

    def ingest(self, scope: OwnerScope, upload: DocumentUpload) -> DocumentIngestionResult:
        if not scope.owns(upload.owner_id):
            raise OwnershipError("upload belongs to a different owner scope")
        checked = self._check(upload)
        key = _KEY_PREFIX + upload.idempotency_key
        existing = self._existing(scope, key)
        if existing is not None:
            return self._replay(scope, existing, upload, checked)

        version_id = new_id()
        with self._uow_factory() as uow:
            if upload.document_id is None:
                document = Document(
                    id=new_id(),
                    owner_id=scope.owner_id,
                    original_filename=checked.filename,
                    media_type=checked.media_type,
                    lifecycle_status=DocumentLifecycleStatus.REGISTERED,
                    current_version_id=version_id,
                    title=upload.title,
                )
                number, expected_current = 1, None
            else:
                document, number, expected_current = self._next_version(
                    uow, scope, upload.document_id, checked
                )
        version = DocumentVersion(
            id=version_id,
            owner_id=scope.owner_id,
            document_id=document.id,
            version_number=number,
            object_key=DocumentVersion.object_key_for(scope.owner_id, document.id, version_id),
            content_sha256=checked.sha256,
            size_bytes=len(checked.content),
            media_type=checked.media_type,
            uploaded_at=self._now(),
            processing_status=VersionProcessingStatus.STORED,
        )
        self._storage.put(
            scope,
            version.object_key,
            io.BytesIO(checked.content),
            content_type=checked.media_type.value,
            size_bytes=version.size_bytes,
            sha256=checked.sha256,
        )
        operation = ProcessingOperation(
            id=new_id(),
            owner_id=scope.owner_id,
            document_id=document.id,
            version_id=version_id,
            operation_type=OperationType.EXTRACTION,
            status=OperationStatus.CREATED,
            idempotency_key=key,
        )
        try:
            with self._uow_factory() as uow:
                if expected_current is None:
                    uow.documents.register(scope, document, version)
                else:
                    uow.documents.add_version(
                        scope, version, expected_current_version_id=expected_current
                    )
                stored, created = uow.operations.start(scope, operation)
                if not created:  # a concurrent request with the same key won
                    raise _LostRaceError(stored)
                uow.outbox.add(scope, extraction_handoff(scope, operation, version))
        except _LostRaceError as lost:
            self._discard(scope, version.object_key)
            return self._replay(scope, lost.operation, upload, checked)
        except (PersistenceError, ConcurrencyConflictError, DeletionInProgressError):
            self._discard(scope, version.object_key)
            raise
        return DocumentIngestionResult(
            document_id=document.id,
            version_id=version_id,
            version_number=number,
            operation_id=operation.id,
            media_type=checked.media_type,
            version_status=version.processing_status,
            created=True,
        )

    def _check(self, upload: DocumentUpload) -> _Checked:
        key = upload.idempotency_key
        if not key.strip() or len(key) > _MAX_KEY:
            raise reject("invalid_input", "INVALID_IDEMPOTENCY_KEY")
        if upload.title is not None and not upload.title.strip():
            raise reject("invalid_input", "INVALID_TITLE")
        filename = safe_filename(upload.filename)
        content = upload.data.read(self._max_upload_bytes + 1)
        if len(content) > self._max_upload_bytes:
            raise reject("invalid_input", "FILE_TOO_LARGE")
        media_type = detect_media_type(content, max_bytes=self._max_upload_bytes)
        check_declared(media_type, filename=filename, declared=upload.declared_media_type)
        return _Checked(content, media_type, hashlib.sha256(content).hexdigest(), filename)

    def _next_version(
        self,
        uow: DocumentUnitOfWork,
        scope: OwnerScope,
        document_id: uuid.UUID,
        checked: _Checked,
    ) -> tuple[Document, int, uuid.UUID]:
        documents = uow.documents
        document = documents.get(scope, document_id)
        if document is None or document.current_version_id is None:
            raise RecordNotFoundError("document not found")
        if document.lifecycle_status not in _WRITABLE:
            raise DeletionInProgressError("document is being deleted")
        if document.media_type is not checked.media_type:
            raise reject("invalid_input", "MEDIA_TYPE_CHANGED")
        versions = documents.list_versions(scope, document_id)
        current = next(v for v in versions if v.id == document.current_version_id)
        if current.content_sha256 == checked.sha256:
            raise reject("invalid_input", "DUPLICATE_VERSION")
        number = max(v.version_number for v in versions) + 1
        return document, number, document.current_version_id

    def _existing(self, scope: OwnerScope, key: str) -> ProcessingOperation | None:
        with self._uow_factory() as uow:
            return uow.operations.find_by_idempotency_key(scope, key)

    def _replay(
        self,
        scope: OwnerScope,
        operation: ProcessingOperation,
        upload: DocumentUpload,
        checked: _Checked,
    ) -> DocumentIngestionResult:
        with self._uow_factory() as uow:
            document = uow.documents.get(scope, operation.document_id)
            version = (
                None
                if operation.version_id is None
                else uow.documents.get_version(scope, operation.version_id)
            )
        if document is None or version is None:
            raise RecordNotFoundError("document not found")
        same = (
            version.content_sha256 == checked.sha256
            and upload.document_id in (None, document.id)
            and (upload.document_id is not None or document.original_filename == checked.filename)
        )
        if not same:
            raise IdempotencyKeyReusedError("idempotency key was already used for another upload")
        return DocumentIngestionResult(
            document_id=document.id,
            version_id=version.id,
            version_number=version.version_number,
            operation_id=operation.id,
            media_type=version.media_type,
            version_status=version.processing_status,
            created=False,
        )

    def _discard(self, scope: OwnerScope, key: str) -> None:
        # Best effort; a leftover object has no record and is found by reconciliation.
        with contextlib.suppress(ObjectStorageError):
            self._storage.delete(scope, key)
