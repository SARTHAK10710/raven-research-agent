"""SQLAlchemy implementations of the Document Intelligence ports.

Same rules as Personal Memory: every query filters on ``owner_id`` in SQL,
writes check scope before touching the database, and repositories return
immutable domain records. Status changes are conditional ``UPDATE`` statements
on the expected current status, so the check and the write are one statement.
"""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from memory_engine.documents.domain import (
    ChunkLocation,
    Document,
    DocumentChunk,
    DocumentDependencies,
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
from memory_engine.domain.errors import DomainValidationError, OwnershipError
from memory_engine.domain.identifiers import OwnerScope
from memory_engine.exceptions import (
    DeletionInProgressError,
    RecordNotFoundError,
)
from memory_engine.infrastructure.persistence.database import (
    conditional_update,
    translate_database_errors,
)
from memory_engine.infrastructure.persistence.documents.models import (
    ChunkLocationRow,
    DocumentChunkRow,
    DocumentEmbeddingRow,
    DocumentRow,
    DocumentVersionRow,
    ExtractedRepresentationRow,
    ProcessingOperationRow,
)

WRITABLE_DOCUMENT_STATES = (
    DocumentLifecycleStatus.REGISTERED.value,
    DocumentLifecycleStatus.AVAILABLE.value,
)
DELETING_VERSION_STATES = (
    VersionProcessingStatus.DELETION_REQUESTED.value,
    VersionProcessingStatus.DELETING.value,
    VersionProcessingStatus.DELETED.value,
)
OPEN_OPERATION_STATES = tuple(status.value for status in OperationStatus if status.open)


def _require_in_scope(scope: OwnerScope, *owner_ids: uuid.UUID) -> None:
    if not all(scope.owns(owner_id) for owner_id in owner_ids):
        raise OwnershipError("record owner does not match the operation's owner scope")


# --- mapping -----------------------------------------------------------------------


def _document(row: DocumentRow) -> Document:
    return Document(
        id=row.id,
        owner_id=row.owner_id,
        original_filename=row.original_filename,
        media_type=DocumentMediaType(row.media_type),
        lifecycle_status=DocumentLifecycleStatus(row.lifecycle_status),
        current_version_id=row.current_version_id,
        title=row.title,
    )


def _version(row: DocumentVersionRow) -> DocumentVersion:
    return DocumentVersion(
        id=row.id,
        owner_id=row.owner_id,
        document_id=row.document_id,
        version_number=row.version_number,
        object_key=row.object_key,
        content_sha256=row.content_sha256,
        size_bytes=row.size_bytes,
        media_type=DocumentMediaType(row.media_type),
        uploaded_at=row.uploaded_at,
        processing_status=VersionProcessingStatus(row.processing_status),
    )


def _version_row(version: DocumentVersion) -> DocumentVersionRow:
    return DocumentVersionRow(
        id=version.id,
        owner_id=version.owner_id,
        document_id=version.document_id,
        version_number=version.version_number,
        object_key=version.object_key,
        content_sha256=version.content_sha256,
        size_bytes=version.size_bytes,
        media_type=version.media_type.value,
        uploaded_at=version.uploaded_at,
        processing_status=version.processing_status.value,
    )


def _location(row: ChunkLocationRow) -> ChunkLocation:
    return ChunkLocation(
        id=row.id,
        page_number=row.page_number,
        section_heading=row.section_heading,
        start_offset=row.start_offset,
        end_offset=row.end_offset,
        structural_path=None if row.structural_path is None else tuple(row.structural_path),
    )


def _operation(row: ProcessingOperationRow) -> ProcessingOperation:
    return ProcessingOperation(
        id=row.id,
        owner_id=row.owner_id,
        document_id=row.document_id,
        version_id=row.version_id,
        operation_type=OperationType(row.operation_type),
        status=OperationStatus(row.status),
        idempotency_key=row.idempotency_key,
        attempts=row.attempts,
        error_code=row.error_code,
    )


def _embedding(row: DocumentEmbeddingRow) -> DocumentEmbedding:
    return DocumentEmbedding(
        id=row.id,
        owner_id=row.owner_id,
        chunk_id=row.chunk_id,
        version_id=row.version_id,
        model_id=row.model_id,
        model_revision=row.model_revision,
        dimensions=row.dimensions,
        preprocessing_version=row.preprocessing_version,
        status=EmbeddingStatus(row.status),
    )


def _representation(row: ExtractedRepresentationRow) -> ExtractedRepresentation:
    return ExtractedRepresentation(
        id=row.id,
        owner_id=row.owner_id,
        version_id=row.version_id,
        extraction_method=row.extraction_method,
        extraction_version=row.extraction_version,
        status=ExtractionStatus(row.status),
        extracted_at=row.extracted_at,
        content_ref=row.content_ref,
        structure=row.structure,
        error_code=row.error_code,
    )


# --- shared guard ------------------------------------------------------------------


def require_writable_version(session: Session, scope: OwnerScope, version_id: uuid.UUID) -> None:
    """Derived content may only be written for a live document and version.

    A stale worker must never recreate content for a document whose deletion has
    been requested (memory/05 sections 18-19; 5.10 section 9.3).
    """
    state = session.execute(
        select(DocumentRow.lifecycle_status, DocumentVersionRow.processing_status)
        .join(DocumentRow, DocumentRow.id == DocumentVersionRow.document_id)
        .where(
            DocumentVersionRow.id == version_id,
            DocumentVersionRow.owner_id == scope.owner_id,
            DocumentRow.owner_id == scope.owner_id,
        )
    ).one_or_none()
    if state is None or state.lifecycle_status == DocumentLifecycleStatus.DELETED.value:
        raise RecordNotFoundError("document version not found")
    if (
        state.lifecycle_status not in WRITABLE_DOCUMENT_STATES
        or state.processing_status in DELETING_VERSION_STATES
    ):
        raise DeletionInProgressError("document is being deleted")


# --- documents and versions --------------------------------------------------------


class SqlAlchemyDocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def register(self, scope: OwnerScope, document: Document, version: DocumentVersion) -> None:
        _require_in_scope(scope, document.owner_id, version.owner_id)
        if version.document_id != document.id or document.current_version_id != version.id:
            raise DomainValidationError(
                "the first version must belong to and be current for the document"
            )
        if version.version_number != 1:
            raise DomainValidationError("a new document starts at version 1")
        if version.media_type is not document.media_type:
            raise DomainValidationError("the first version must have the document's media type")
        if document.lifecycle_status.value not in WRITABLE_DOCUMENT_STATES:
            raise DomainValidationError("a new document is registered or available")
        with translate_database_errors("register document"):
            self._session.add(
                DocumentRow(
                    id=document.id,
                    owner_id=document.owner_id,
                    title=document.title,
                    original_filename=document.original_filename,
                    media_type=document.media_type.value,
                    lifecycle_status=document.lifecycle_status.value,
                    current_version_id=None,
                )
            )
            self._session.flush()
            self._session.add(_version_row(version))
            self._session.flush()
            self._session.execute(
                update(DocumentRow)
                .where(DocumentRow.id == document.id)
                .values(current_version_id=version.id)
                .execution_options(synchronize_session=False)
            )

    def add_version(
        self,
        scope: OwnerScope,
        version: DocumentVersion,
        *,
        expected_current_version_id: uuid.UUID,
    ) -> None:
        _require_in_scope(scope, version.owner_id)
        with translate_database_errors("add document version"):
            lifecycle = self._session.scalar(
                select(DocumentRow.lifecycle_status).where(
                    DocumentRow.id == version.document_id, DocumentRow.owner_id == scope.owner_id
                )
            )
            if lifecycle is None or lifecycle == DocumentLifecycleStatus.DELETED.value:
                raise RecordNotFoundError("document not found")
            if lifecycle not in WRITABLE_DOCUMENT_STATES:
                raise DeletionInProgressError("document is being deleted")
            latest = self._session.scalar(
                select(func.max(DocumentVersionRow.version_number)).where(
                    DocumentVersionRow.document_id == version.document_id
                )
            )
            if version.version_number != (latest or 0) + 1:
                raise DomainValidationError("versions are numbered consecutively")
            self._session.add(_version_row(version))
            self._session.flush()
            conditional_update(
                self._session,
                update(DocumentRow)
                .where(
                    DocumentRow.id == version.document_id,
                    DocumentRow.owner_id == scope.owner_id,
                    DocumentRow.current_version_id == expected_current_version_id,
                )
                .values(current_version_id=version.id),
                exists=_document_exists(scope, version.document_id),
                what="document",
            )

    def get(self, scope: OwnerScope, document_id: uuid.UUID) -> Document | None:
        with translate_database_errors("get document"):
            row = self._session.scalar(
                select(DocumentRow)
                .where(
                    DocumentRow.id == document_id,
                    DocumentRow.owner_id == scope.owner_id,
                    DocumentRow.lifecycle_status != DocumentLifecycleStatus.DELETED.value,
                )
                .execution_options(populate_existing=True)
            )
        return None if row is None else _document(row)

    def get_version(self, scope: OwnerScope, version_id: uuid.UUID) -> DocumentVersion | None:
        with translate_database_errors("get document version"):
            row = self._session.scalar(
                select(DocumentVersionRow)
                .where(
                    DocumentVersionRow.id == version_id,
                    DocumentVersionRow.owner_id == scope.owner_id,
                )
                .execution_options(populate_existing=True)
            )
        return None if row is None else _version(row)

    def list_versions(self, scope: OwnerScope, document_id: uuid.UUID) -> Sequence[DocumentVersion]:
        with translate_database_errors("list document versions"):
            rows = self._session.scalars(
                select(DocumentVersionRow)
                .where(
                    DocumentVersionRow.owner_id == scope.owner_id,
                    DocumentVersionRow.document_id == document_id,
                )
                .order_by(DocumentVersionRow.version_number)
                .execution_options(populate_existing=True)
            ).all()
        return [_version(row) for row in rows]

    def set_lifecycle_status(
        self,
        scope: OwnerScope,
        document_id: uuid.UUID,
        status: DocumentLifecycleStatus,
        *,
        expected: DocumentLifecycleStatus,
    ) -> None:
        with translate_database_errors("set document lifecycle status"):
            conditional_update(
                self._session,
                update(DocumentRow)
                .where(
                    DocumentRow.id == document_id,
                    DocumentRow.owner_id == scope.owner_id,
                    DocumentRow.lifecycle_status == expected.value,
                )
                .values(lifecycle_status=status.value),
                exists=_document_exists(scope, document_id),
                what="document",
            )

    def set_version_status(
        self,
        scope: OwnerScope,
        version_id: uuid.UUID,
        status: VersionProcessingStatus,
        *,
        expected: VersionProcessingStatus,
    ) -> None:
        with translate_database_errors("set document version status"):
            conditional_update(
                self._session,
                update(DocumentVersionRow)
                .where(
                    DocumentVersionRow.id == version_id,
                    DocumentVersionRow.owner_id == scope.owner_id,
                    DocumentVersionRow.processing_status == expected.value,
                )
                .values(processing_status=status.value),
                exists=select(DocumentVersionRow.id)
                .where(
                    DocumentVersionRow.id == version_id,
                    DocumentVersionRow.owner_id == scope.owner_id,
                )
                .exists(),
                what="document version",
            )

    def dependencies(self, scope: OwnerScope, document_id: uuid.UUID) -> DocumentDependencies:
        with translate_database_errors("discover document dependencies"):
            if not self._session.scalar(select(_document_exists(scope, document_id))):
                raise RecordNotFoundError("document not found")
            versions = self._session.execute(
                select(DocumentVersionRow.id, DocumentVersionRow.object_key)
                .where(
                    DocumentVersionRow.owner_id == scope.owner_id,
                    DocumentVersionRow.document_id == document_id,
                )
                .order_by(DocumentVersionRow.version_number)
            ).all()
            version_ids = [row.id for row in versions]
            representations = self._session.execute(
                select(ExtractedRepresentationRow.id, ExtractedRepresentationRow.content_ref)
                .where(
                    ExtractedRepresentationRow.owner_id == scope.owner_id,
                    ExtractedRepresentationRow.version_id.in_(version_ids),
                )
                .order_by(ExtractedRepresentationRow.id)
            ).all()
            chunk_ids = self._ids(DocumentChunkRow, scope, version_ids)
            location_count = self._session.scalar(
                select(func.count())
                .select_from(ChunkLocationRow)
                .where(
                    ChunkLocationRow.owner_id == scope.owner_id,
                    ChunkLocationRow.version_id.in_(version_ids),
                )
            )
            embedding_ids = self._ids(DocumentEmbeddingRow, scope, version_ids)
            open_operations = self._session.scalars(
                select(ProcessingOperationRow.id)
                .where(
                    ProcessingOperationRow.owner_id == scope.owner_id,
                    ProcessingOperationRow.document_id == document_id,
                    ProcessingOperationRow.status.in_(OPEN_OPERATION_STATES),
                )
                .order_by(ProcessingOperationRow.id)
            ).all()
        return DocumentDependencies(
            document_id=document_id,
            version_ids=tuple(version_ids),
            object_keys=tuple(row.object_key for row in versions),
            representation_ids=tuple(row.id for row in representations),
            representation_content_refs=tuple(
                row.content_ref for row in representations if row.content_ref is not None
            ),
            chunk_ids=tuple(chunk_ids),
            chunk_location_count=location_count or 0,
            embedding_ids=tuple(embedding_ids),
            open_operation_ids=tuple(open_operations),
        )

    def _ids(
        self,
        model: type[DocumentChunkRow] | type[DocumentEmbeddingRow],
        scope: OwnerScope,
        version_ids: list[uuid.UUID],
    ) -> list[uuid.UUID]:
        return list(
            self._session.scalars(
                select(model.id)
                .where(model.owner_id == scope.owner_id, model.version_id.in_(version_ids))
                .order_by(model.id)
            ).all()
        )


def _document_exists(scope: OwnerScope, document_id: uuid.UUID) -> ColumnElement[bool]:
    return (
        select(DocumentRow.id)
        .where(DocumentRow.id == document_id, DocumentRow.owner_id == scope.owner_id)
        .exists()
    )


# --- derived content ---------------------------------------------------------------


class SqlAlchemyDocumentContentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_representation(
        self, scope: OwnerScope, representation: ExtractedRepresentation
    ) -> None:
        _require_in_scope(scope, representation.owner_id)
        with translate_database_errors("add extracted representation"):
            require_writable_version(self._session, scope, representation.version_id)
            self._session.add(
                ExtractedRepresentationRow(
                    id=representation.id,
                    owner_id=representation.owner_id,
                    version_id=representation.version_id,
                    extraction_method=representation.extraction_method,
                    extraction_version=representation.extraction_version,
                    content_ref=representation.content_ref,
                    structure=dict(representation.structure),
                    status=representation.status.value,
                    error_code=representation.error_code,
                    extracted_at=representation.extracted_at,
                )
            )
            self._session.flush()

    def get_representation(
        self, scope: OwnerScope, representation_id: uuid.UUID
    ) -> ExtractedRepresentation | None:
        with translate_database_errors("get extracted representation"):
            row = self._session.scalar(
                select(ExtractedRepresentationRow).where(
                    ExtractedRepresentationRow.id == representation_id,
                    ExtractedRepresentationRow.owner_id == scope.owner_id,
                )
            )
        return None if row is None else _representation(row)

    def add_chunks(self, scope: OwnerScope, chunks: Sequence[DocumentChunk]) -> None:
        if not chunks:
            return
        _require_in_scope(scope, *(chunk.owner_id for chunk in chunks))
        version_ids = {chunk.version_id for chunk in chunks}
        representation_ids = {chunk.representation_id for chunk in chunks}
        if len(version_ids) != 1 or len(representation_ids) != 1:
            # memory/05 section 8.7: a batch never mixes versions or representations.
            raise DomainValidationError("chunks in one call must share version and representation")
        (version_id,), (representation_id,) = version_ids, representation_ids
        with translate_database_errors("add document chunks"):
            require_writable_version(self._session, scope, version_id)
            representation = self._session.scalar(
                select(ExtractedRepresentationRow.status).where(
                    ExtractedRepresentationRow.id == representation_id,
                    ExtractedRepresentationRow.version_id == version_id,
                    ExtractedRepresentationRow.owner_id == scope.owner_id,
                )
            )
            if representation is None:
                raise RecordNotFoundError("extracted representation not found for this version")
            if representation == ExtractionStatus.EXTRACTION_FAILED.value:
                raise DomainValidationError("a failed extraction has no content to chunk")
            for chunk in chunks:
                self._session.add(
                    DocumentChunkRow(
                        id=chunk.id,
                        owner_id=chunk.owner_id,
                        version_id=chunk.version_id,
                        representation_id=chunk.representation_id,
                        sequence=chunk.sequence,
                        content=chunk.content,
                        content_sha256=chunk.content_sha256,
                        chunking_strategy=chunk.chunking_strategy,
                        chunking_version=chunk.chunking_version,
                    )
                )
            self._session.flush()
            for chunk in chunks:
                for ordinal, location in enumerate(chunk.locations):
                    self._session.add(
                        ChunkLocationRow(
                            id=location.id,
                            owner_id=chunk.owner_id,
                            chunk_id=chunk.id,
                            version_id=chunk.version_id,
                            ordinal=ordinal,
                            page_number=location.page_number,
                            section_heading=location.section_heading,
                            start_offset=location.start_offset,
                            end_offset=location.end_offset,
                            structural_path=None
                            if location.structural_path is None
                            else list(location.structural_path),
                        )
                    )
            self._session.flush()

    def list_chunks(self, scope: OwnerScope, version_id: uuid.UUID) -> Sequence[DocumentChunk]:
        with translate_database_errors("list document chunks"):
            rows = self._session.scalars(
                select(DocumentChunkRow)
                .where(
                    DocumentChunkRow.owner_id == scope.owner_id,
                    DocumentChunkRow.version_id == version_id,
                )
                .order_by(DocumentChunkRow.representation_id, DocumentChunkRow.sequence)
            ).all()
            locations: dict[uuid.UUID, list[ChunkLocation]] = {row.id: [] for row in rows}
            for location in self._session.scalars(
                select(ChunkLocationRow)
                .where(
                    ChunkLocationRow.owner_id == scope.owner_id,
                    ChunkLocationRow.version_id == version_id,
                )
                .order_by(ChunkLocationRow.chunk_id, ChunkLocationRow.ordinal)
            ):
                locations[location.chunk_id].append(_location(location))
        return [
            DocumentChunk(
                id=row.id,
                owner_id=row.owner_id,
                version_id=row.version_id,
                representation_id=row.representation_id,
                sequence=row.sequence,
                content=row.content,
                content_sha256=row.content_sha256,
                chunking_strategy=row.chunking_strategy,
                chunking_version=row.chunking_version,
                locations=locations[row.id],
            )
            for row in rows
        ]

    def add_embedding(self, scope: OwnerScope, embedding: DocumentEmbedding) -> None:
        _require_in_scope(scope, embedding.owner_id)
        with translate_database_errors("add document embedding"):
            require_writable_version(self._session, scope, embedding.version_id)
            self._session.add(
                DocumentEmbeddingRow(
                    id=embedding.id,
                    owner_id=embedding.owner_id,
                    chunk_id=embedding.chunk_id,
                    version_id=embedding.version_id,
                    model_id=embedding.model_id,
                    model_revision=embedding.model_revision,
                    dimensions=embedding.dimensions,
                    preprocessing_version=embedding.preprocessing_version,
                    status=embedding.status.value,
                )
            )
            self._session.flush()

    def get_embedding(self, scope: OwnerScope, embedding_id: uuid.UUID) -> DocumentEmbedding | None:
        with translate_database_errors("get document embedding"):
            row = self._session.scalar(
                select(DocumentEmbeddingRow)
                .where(
                    DocumentEmbeddingRow.id == embedding_id,
                    DocumentEmbeddingRow.owner_id == scope.owner_id,
                )
                .execution_options(populate_existing=True)
            )
        return None if row is None else _embedding(row)

    def set_embedding_status(
        self,
        scope: OwnerScope,
        embedding_id: uuid.UUID,
        status: EmbeddingStatus,
        *,
        expected: EmbeddingStatus,
    ) -> None:
        with translate_database_errors("set document embedding status"):
            conditional_update(
                self._session,
                update(DocumentEmbeddingRow)
                .where(
                    DocumentEmbeddingRow.id == embedding_id,
                    DocumentEmbeddingRow.owner_id == scope.owner_id,
                    DocumentEmbeddingRow.status == expected.value,
                )
                .values(status=status.value),
                exists=select(DocumentEmbeddingRow.id)
                .where(
                    DocumentEmbeddingRow.id == embedding_id,
                    DocumentEmbeddingRow.owner_id == scope.owner_id,
                )
                .exists(),
                what="document embedding",
            )


# --- processing operations ---------------------------------------------------------


class SqlAlchemyProcessingOperationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def start(
        self, scope: OwnerScope, operation: ProcessingOperation
    ) -> tuple[ProcessingOperation, bool]:
        _require_in_scope(scope, operation.owner_id)
        with translate_database_errors("start processing operation"):
            lifecycle = self._session.scalar(
                select(DocumentRow.lifecycle_status).where(
                    DocumentRow.id == operation.document_id,
                    DocumentRow.owner_id == scope.owner_id,
                )
            )
            if lifecycle is None or lifecycle == DocumentLifecycleStatus.DELETED.value:
                raise RecordNotFoundError("document not found")
            if (
                lifecycle not in WRITABLE_DOCUMENT_STATES
                and operation.operation_type is not OperationType.DELETION
            ):
                raise DeletionInProgressError("document is being deleted")
            values: dict[str, Any] = {
                "id": operation.id,
                "owner_id": operation.owner_id,
                "document_id": operation.document_id,
                "version_id": operation.version_id,
                "operation_type": operation.operation_type.value,
                "status": operation.status.value,
                "idempotency_key": operation.idempotency_key,
                "attempts": operation.attempts,
                "error_code": operation.error_code,
            }
            inserted = self._session.scalar(
                pg_insert(ProcessingOperationRow)
                .values(**values)
                .on_conflict_do_nothing(index_elements=["owner_id", "idempotency_key"])
                .returning(ProcessingOperationRow.id)
            )
            row = self._session.scalar(
                select(ProcessingOperationRow)
                .where(
                    ProcessingOperationRow.owner_id == scope.owner_id,
                    ProcessingOperationRow.idempotency_key == operation.idempotency_key,
                )
                .execution_options(populate_existing=True)
            )
        if row is None:  # pragma: no cover - the row was just inserted or already existed
            raise RecordNotFoundError("processing operation not found")
        return _operation(row), inserted is not None

    def get(self, scope: OwnerScope, operation_id: uuid.UUID) -> ProcessingOperation | None:
        with translate_database_errors("get processing operation"):
            row = self._session.scalar(
                select(ProcessingOperationRow)
                .where(
                    ProcessingOperationRow.id == operation_id,
                    ProcessingOperationRow.owner_id == scope.owner_id,
                )
                .execution_options(populate_existing=True)
            )
        return None if row is None else _operation(row)

    def find_by_idempotency_key(self, scope: OwnerScope, key: str) -> ProcessingOperation | None:
        with translate_database_errors("find processing operation by idempotency key"):
            row = self._session.scalar(
                select(ProcessingOperationRow)
                .where(
                    ProcessingOperationRow.owner_id == scope.owner_id,
                    ProcessingOperationRow.idempotency_key == key,
                )
                .execution_options(populate_existing=True)
            )
        return None if row is None else _operation(row)

    def transition(
        self,
        scope: OwnerScope,
        operation_id: uuid.UUID,
        status: OperationStatus,
        *,
        expected: OperationStatus,
        error_code: str | None = None,
        count_attempt: bool = False,
    ) -> ProcessingOperation:
        validate_error_code(error_code)
        values: dict[str, Any] = {"status": status.value, "error_code": error_code}
        if count_attempt:
            values["attempts"] = ProcessingOperationRow.attempts + 1
        with translate_database_errors("transition processing operation"):
            conditional_update(
                self._session,
                update(ProcessingOperationRow)
                .where(
                    ProcessingOperationRow.id == operation_id,
                    ProcessingOperationRow.owner_id == scope.owner_id,
                    ProcessingOperationRow.status == expected.value,
                )
                .values(**values),
                exists=select(ProcessingOperationRow.id)
                .where(
                    ProcessingOperationRow.id == operation_id,
                    ProcessingOperationRow.owner_id == scope.owner_id,
                )
                .exists(),
                what="processing operation",
            )
        stored = self.get(scope, operation_id)
        if stored is None:  # pragma: no cover - updated in this transaction
            raise RecordNotFoundError("processing operation not found")
        return stored
