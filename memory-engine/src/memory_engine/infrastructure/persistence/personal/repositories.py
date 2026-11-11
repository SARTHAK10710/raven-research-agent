"""SQLAlchemy implementations of the Personal Memory ports.

Ownership: every query filters on ``owner_id`` in SQL, so another owner's rows
are never loaded, ranked or counted (Decision 5.8.6). Writes check that the
records being written belong to the caller's scope before touching the
database; composite foreign keys enforce the same rule inside PostgreSQL.

Repositories return immutable domain records, never ORM instances.
"""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import exists, select, update
from sqlalchemy.orm import Session

from memory_engine.documents.domain.vocabulary import DocumentLifecycleStatus
from memory_engine.domain.errors import DomainValidationError, OwnershipError
from memory_engine.domain.identifiers import OwnerScope
from memory_engine.domain.vocabulary import (
    CandidateOrigin,
    CandidateStatus,
    DocumentEvidenceStatus,
    IngestionPriority,
    InstructionType,
    MemoryLifecycleStatus,
    MemoryOrigin,
    ProvenanceOriginKind,
    ProvenanceRole,
    RevisionChangeType,
    SourceProcessingStatus,
    SourceType,
)
from memory_engine.exceptions import (
    ConcurrencyConflictError,
    DeletionInProgressError,
    RecordNotFoundError,
)
from memory_engine.infrastructure.persistence.database import translate_database_errors
from memory_engine.infrastructure.persistence.documents.models import (
    DocumentChunkRow,
    DocumentRow,
    DocumentVersionRow,
)
from memory_engine.infrastructure.persistence.personal.models import (
    AtomicMemoryRevisionRow,
    AtomicMemoryRow,
    DocumentEvidenceRefRow,
    MemoryCandidateRow,
    MemorySourceRow,
    ProvenanceRow,
)
from memory_engine.personal.domain import (
    AtomicMemory,
    AtomicMemoryRevision,
    DocumentEvidenceRef,
    MemoryCandidate,
    MemorySource,
    ProvenanceRecord,
)

_TOMBSTONED = (
    MemoryLifecycleStatus.DELETION_PENDING.value,
    MemoryLifecycleStatus.DELETED.value,
)


def _require_in_scope(scope: OwnerScope, *owner_ids: uuid.UUID) -> None:
    if not all(scope.owns(owner_id) for owner_id in owner_ids):
        raise OwnershipError("record owner does not match the operation's owner scope")


def _json(value: Any) -> dict[str, Any]:
    return dict(value)


# --- Memory Source ---------------------------------------------------------------


def _source_from_row(row: MemorySourceRow) -> MemorySource:
    return MemorySource(
        id=row.id,
        owner_id=row.owner_id,
        source_type=SourceType(row.source_type),
        processing_status=SourceProcessingStatus(row.processing_status),
        received_at=row.received_at,
        content_ref=row.content_ref,
        content_sha256=row.content_sha256,
        instruction_type=InstructionType(row.instruction_type),
        priority=IngestionPriority(row.priority),
        idempotency_key=row.idempotency_key,
        request_sha256=row.request_sha256,
        source_ref=row.source_ref,
        source_timestamp=row.source_timestamp,
        normalized_ref=row.normalized_ref,
    )


class SqlAlchemyMemorySourceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, scope: OwnerScope, source: MemorySource) -> None:
        _require_in_scope(scope, source.owner_id)
        with translate_database_errors("add memory source"):
            self._session.add(
                MemorySourceRow(
                    id=source.id,
                    owner_id=source.owner_id,
                    source_type=source.source_type.value,
                    processing_status=source.processing_status.value,
                    received_at=source.received_at,
                    content_ref=source.content_ref,
                    content_sha256=source.content_sha256,
                    instruction_type=source.instruction_type.value,
                    priority=source.priority.value,
                    idempotency_key=source.idempotency_key,
                    request_sha256=source.request_sha256,
                    source_ref=source.source_ref,
                    source_timestamp=source.source_timestamp,
                    normalized_ref=source.normalized_ref,
                )
            )
            self._session.flush()

    def find_by_idempotency_key(self, scope: OwnerScope, key: str) -> MemorySource | None:
        with translate_database_errors("find memory source by idempotency key"):
            row = self._session.scalar(
                select(MemorySourceRow)
                .where(
                    MemorySourceRow.owner_id == scope.owner_id,
                    MemorySourceRow.idempotency_key == key,
                )
                .execution_options(populate_existing=True)
            )
        return None if row is None else _source_from_row(row)

    def get(self, scope: OwnerScope, source_id: uuid.UUID) -> MemorySource | None:
        with translate_database_errors("get memory source"):
            row = self._session.scalar(
                select(MemorySourceRow)
                .where(MemorySourceRow.id == source_id, MemorySourceRow.owner_id == scope.owner_id)
                .execution_options(populate_existing=True)
            )
        return None if row is None else _source_from_row(row)

    def exists(self, scope: OwnerScope, source_id: uuid.UUID) -> bool:
        with translate_database_errors("check memory source"):
            return bool(
                self._session.scalar(
                    select(
                        exists().where(
                            MemorySourceRow.id == source_id,
                            MemorySourceRow.owner_id == scope.owner_id,
                        )
                    )
                )
            )


# --- Memory Candidate --------------------------------------------------------------


def _candidate_from_row(row: MemoryCandidateRow) -> MemoryCandidate:
    return MemoryCandidate(
        id=row.id,
        owner_id=row.owner_id,
        source_id=row.source_id,
        proposition=row.proposition,
        status=CandidateStatus(row.status),
        origin=CandidateOrigin(row.origin),
        importance=row.importance,
        confidence=row.confidence,
        extraction_confidence=row.extraction_confidence,
        context=row.context,
        temporal=row.temporal,
        extraction_metadata=row.extraction_metadata,
    )


class SqlAlchemyMemoryCandidateRepository:
    def __init__(self, session: Session, sources: SqlAlchemyMemorySourceRepository) -> None:
        self._session = session
        self._sources = sources

    def add(self, scope: OwnerScope, candidate: MemoryCandidate) -> None:
        _require_in_scope(scope, candidate.owner_id)
        if not self._sources.exists(scope, candidate.source_id):
            raise RecordNotFoundError("memory source not found")
        with translate_database_errors("add memory candidate"):
            self._session.add(
                MemoryCandidateRow(
                    id=candidate.id,
                    owner_id=candidate.owner_id,
                    source_id=candidate.source_id,
                    proposition=candidate.proposition,
                    status=candidate.status.value,
                    origin=candidate.origin.value,
                    importance=candidate.importance,
                    confidence=candidate.confidence,
                    extraction_confidence=candidate.extraction_confidence,
                    context=_json(candidate.context),
                    temporal=_json(candidate.temporal),
                    extraction_metadata=_json(candidate.extraction_metadata),
                )
            )
            self._session.flush()

    def get(self, scope: OwnerScope, candidate_id: uuid.UUID) -> MemoryCandidate | None:
        with translate_database_errors("get memory candidate"):
            row = self._session.scalar(
                select(MemoryCandidateRow)
                .where(
                    MemoryCandidateRow.id == candidate_id,
                    MemoryCandidateRow.owner_id == scope.owner_id,
                )
                .execution_options(populate_existing=True)
            )
        return None if row is None else _candidate_from_row(row)

    def list_for_source(self, scope: OwnerScope, source_id: uuid.UUID) -> Sequence[MemoryCandidate]:
        with translate_database_errors("list memory candidates"):
            rows = self._session.scalars(
                select(MemoryCandidateRow)
                .where(
                    MemoryCandidateRow.owner_id == scope.owner_id,
                    MemoryCandidateRow.source_id == source_id,
                )
                .order_by(MemoryCandidateRow.created_at, MemoryCandidateRow.id)
                .execution_options(populate_existing=True)
            ).all()
        return [_candidate_from_row(row) for row in rows]

    def exists(self, scope: OwnerScope, candidate_id: uuid.UUID) -> bool:
        with translate_database_errors("check memory candidate"):
            return bool(
                self._session.scalar(
                    select(
                        exists().where(
                            MemoryCandidateRow.id == candidate_id,
                            MemoryCandidateRow.owner_id == scope.owner_id,
                        )
                    )
                )
            )


# --- Atomic Memory -----------------------------------------------------------------


def _memory_values(memory: AtomicMemory) -> dict[str, Any]:
    return {
        "content": memory.content,
        "structured": _json(memory.structured),
        "context": _json(memory.context),
        "origin": memory.origin.value,
        "lifecycle_status": memory.lifecycle_status.value,
        "importance": memory.importance,
        "confidence": memory.confidence,
        "valid_from": memory.valid_from,
        "valid_to": memory.valid_to,
        "observed_at": memory.observed_at,
        "recorded_at": memory.recorded_at,
        "superseded_at": memory.superseded_at,
        "revision_number": memory.revision_number,
    }


def _memory_from_row(row: AtomicMemoryRow) -> AtomicMemory:
    return AtomicMemory(
        id=row.id,
        owner_id=row.owner_id,
        content=row.content,
        origin=MemoryOrigin(row.origin),
        lifecycle_status=MemoryLifecycleStatus(row.lifecycle_status),
        recorded_at=row.recorded_at,
        revision_number=row.revision_number,
        structured=row.structured,
        context=row.context,
        importance=row.importance,
        confidence=row.confidence,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        observed_at=row.observed_at,
        superseded_at=row.superseded_at,
    )


def _revision_row(revision: AtomicMemoryRevision) -> AtomicMemoryRevisionRow:
    return AtomicMemoryRevisionRow(
        id=revision.id,
        owner_id=revision.owner_id,
        memory_id=revision.memory_id,
        revision_number=revision.revision_number,
        change_type=revision.change_type.value,
        content=revision.content,
        structured=_json(revision.structured),
        context=_json(revision.context),
        origin=revision.origin.value,
        lifecycle_status=revision.lifecycle_status.value,
        importance=revision.importance,
        confidence=revision.confidence,
        valid_from=revision.valid_from,
        valid_to=revision.valid_to,
        observed_at=revision.observed_at,
        recorded_at=revision.recorded_at,
        reason=revision.reason,
    )


def _revision_from_row(row: AtomicMemoryRevisionRow) -> AtomicMemoryRevision:
    return AtomicMemoryRevision(
        id=row.id,
        owner_id=row.owner_id,
        memory_id=row.memory_id,
        revision_number=row.revision_number,
        change_type=RevisionChangeType(row.change_type),
        content=row.content,
        origin=MemoryOrigin(row.origin),
        lifecycle_status=MemoryLifecycleStatus(row.lifecycle_status),
        recorded_at=row.recorded_at,
        structured=row.structured,
        context=row.context,
        importance=row.importance,
        confidence=row.confidence,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        observed_at=row.observed_at,
        reason=row.reason,
    )


def _require_revision_matches(memory: AtomicMemory, revision: AtomicMemoryRevision) -> None:
    """The appended revision must be an exact snapshot of the new current state."""
    expected = AtomicMemoryRevision.snapshot(
        memory, revision_id=revision.id, change_type=revision.change_type, reason=revision.reason
    )
    if revision != expected:
        raise DomainValidationError("revision does not match the memory state it records")


class SqlAlchemyAtomicMemoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, scope: OwnerScope, memory: AtomicMemory, revision: AtomicMemoryRevision) -> None:
        _require_in_scope(scope, memory.owner_id, revision.owner_id)
        if memory.revision_number != 1 or revision.change_type is not RevisionChangeType.CREATED:
            raise DomainValidationError("a new memory starts at revision 1 with change 'created'")
        _require_revision_matches(memory, revision)
        with translate_database_errors("add atomic memory"):
            self._session.add(
                AtomicMemoryRow(id=memory.id, owner_id=memory.owner_id, **_memory_values(memory))
            )
            self._session.flush()
            self._session.add(_revision_row(revision))
            self._session.flush()

    def get(self, scope: OwnerScope, memory_id: uuid.UUID) -> AtomicMemory | None:
        with translate_database_errors("get atomic memory"):
            row = self._session.scalar(
                select(AtomicMemoryRow)
                .where(
                    AtomicMemoryRow.id == memory_id,
                    AtomicMemoryRow.owner_id == scope.owner_id,
                    AtomicMemoryRow.lifecycle_status.not_in(_TOMBSTONED),
                )
                .execution_options(populate_existing=True)
            )
        return None if row is None else _memory_from_row(row)

    def apply_revision(
        self,
        scope: OwnerScope,
        memory: AtomicMemory,
        revision: AtomicMemoryRevision,
        *,
        expected_revision_number: int,
    ) -> None:
        _require_in_scope(scope, memory.owner_id, revision.owner_id)
        if memory.revision_number != expected_revision_number + 1:
            raise DomainValidationError("the new state must be exactly one revision ahead")
        if revision.change_type is RevisionChangeType.CREATED:
            raise DomainValidationError("'created' is only valid for the first revision")
        _require_revision_matches(memory, revision)
        with translate_database_errors("apply atomic memory revision"):
            # Conditional update: the optimistic-concurrency check and the write are
            # one statement, so a concurrent writer cannot slip in between.
            result = self._session.execute(
                update(AtomicMemoryRow)
                .where(
                    AtomicMemoryRow.id == memory.id,
                    AtomicMemoryRow.owner_id == scope.owner_id,
                    AtomicMemoryRow.revision_number == expected_revision_number,
                    AtomicMemoryRow.lifecycle_status.not_in(_TOMBSTONED),
                )
                .values(**_memory_values(memory))
                .execution_options(synchronize_session=False)
            )
            if getattr(result, "rowcount", 0) != 1:
                if self.get(scope, memory.id) is None:
                    raise RecordNotFoundError("atomic memory not found")
                raise ConcurrencyConflictError("atomic memory changed since it was read")
            self._session.add(_revision_row(revision))
            self._session.flush()

    def list_revisions(
        self, scope: OwnerScope, memory_id: uuid.UUID
    ) -> Sequence[AtomicMemoryRevision]:
        with translate_database_errors("list atomic memory revisions"):
            rows = self._session.scalars(
                select(AtomicMemoryRevisionRow)
                .where(
                    AtomicMemoryRevisionRow.owner_id == scope.owner_id,
                    AtomicMemoryRevisionRow.memory_id == memory_id,
                )
                .order_by(AtomicMemoryRevisionRow.revision_number)
                .execution_options(populate_existing=True)
            ).all()
        return [_revision_from_row(row) for row in rows]

    def list_retrievable(self, scope: OwnerScope) -> Sequence[AtomicMemory]:
        with translate_database_errors("list retrievable atomic memories"):
            rows = self._session.scalars(
                select(AtomicMemoryRow)
                .where(
                    AtomicMemoryRow.owner_id == scope.owner_id,
                    AtomicMemoryRow.lifecycle_status == MemoryLifecycleStatus.ACTIVE.value,
                )
                .order_by(AtomicMemoryRow.recorded_at, AtomicMemoryRow.id)
                .execution_options(populate_existing=True)
            ).all()
        return [_memory_from_row(row) for row in rows]

    def exists(self, scope: OwnerScope, memory_id: uuid.UUID) -> bool:
        return self.get(scope, memory_id) is not None


# --- Document evidence -------------------------------------------------------------
#
# The one sanctioned path from Personal Memory into Document Intelligence. This
# module may read doc_ tables to validate references; the documents side never
# imports Personal Memory code.


def _evidence_from_row(row: DocumentEvidenceRefRow) -> DocumentEvidenceRef:
    return DocumentEvidenceRef(
        id=row.id,
        owner_id=row.owner_id,
        candidate_id=row.candidate_id,
        document_ref=row.document_ref,
        version_ref=row.version_ref,
        chunk_ref=row.chunk_ref,
        extraction_method=row.extraction_method,
        status=DocumentEvidenceStatus(row.status),
        recorded_at=row.recorded_at,
        page_number=row.page_number,
        section_heading=row.section_heading,
        start_offset=row.start_offset,
        end_offset=row.end_offset,
    )


class SqlAlchemyDocumentEvidenceRepository:
    def __init__(self, session: Session, candidates: SqlAlchemyMemoryCandidateRepository) -> None:
        self._session = session
        self._candidates = candidates

    def add(self, scope: OwnerScope, evidence: DocumentEvidenceRef) -> None:
        _require_in_scope(scope, evidence.owner_id)
        if evidence.status is not DocumentEvidenceStatus.ACTIVE:
            raise DomainValidationError("new document evidence must be active")
        if not self._candidates.exists(scope, evidence.candidate_id):
            raise RecordNotFoundError("memory candidate not found")
        with translate_database_errors("add document evidence"):
            # The version must belong to the document and the chunk to the version,
            # all within the owner's scope; anything else looks like "not found".
            lifecycle = self._session.scalar(
                select(DocumentRow.lifecycle_status)
                .join(DocumentVersionRow, DocumentVersionRow.document_id == DocumentRow.id)
                .where(
                    DocumentRow.id == evidence.document_ref,
                    DocumentRow.owner_id == scope.owner_id,
                    DocumentVersionRow.id == evidence.version_ref,
                    DocumentVersionRow.owner_id == scope.owner_id,
                )
            )
            if lifecycle is None or lifecycle == DocumentLifecycleStatus.DELETED.value:
                raise RecordNotFoundError("document version not found")
            if not DocumentLifecycleStatus(lifecycle).retrievable and lifecycle != (
                DocumentLifecycleStatus.REGISTERED.value
            ):
                raise DeletionInProgressError("document is being deleted")
            if evidence.chunk_ref is not None and not self._session.scalar(
                select(
                    exists().where(
                        DocumentChunkRow.id == evidence.chunk_ref,
                        DocumentChunkRow.version_id == evidence.version_ref,
                        DocumentChunkRow.owner_id == scope.owner_id,
                    )
                )
            ):
                raise RecordNotFoundError("document chunk not found")
            self._session.add(
                DocumentEvidenceRefRow(
                    id=evidence.id,
                    owner_id=evidence.owner_id,
                    candidate_id=evidence.candidate_id,
                    document_ref=evidence.document_ref,
                    version_ref=evidence.version_ref,
                    chunk_ref=evidence.chunk_ref,
                    document_id=evidence.document_ref,
                    version_id=evidence.version_ref,
                    chunk_id=evidence.chunk_ref,
                    extraction_method=evidence.extraction_method,
                    page_number=evidence.page_number,
                    section_heading=evidence.section_heading,
                    start_offset=evidence.start_offset,
                    end_offset=evidence.end_offset,
                    status=evidence.status.value,
                    recorded_at=evidence.recorded_at,
                )
            )
            self._session.flush()

    def list_for_candidate(
        self, scope: OwnerScope, candidate_id: uuid.UUID
    ) -> Sequence[DocumentEvidenceRef]:
        with translate_database_errors("list document evidence"):
            rows = self._session.scalars(
                select(DocumentEvidenceRefRow)
                .where(
                    DocumentEvidenceRefRow.owner_id == scope.owner_id,
                    DocumentEvidenceRefRow.candidate_id == candidate_id,
                )
                .order_by(DocumentEvidenceRefRow.recorded_at, DocumentEvidenceRefRow.id)
                .execution_options(populate_existing=True)
            ).all()
        return [_evidence_from_row(row) for row in rows]

    def exists(self, scope: OwnerScope, evidence_id: uuid.UUID) -> bool:
        with translate_database_errors("check document evidence"):
            return bool(
                self._session.scalar(
                    select(
                        exists().where(
                            DocumentEvidenceRefRow.id == evidence_id,
                            DocumentEvidenceRefRow.owner_id == scope.owner_id,
                        )
                    )
                )
            )

    def dependent_memory_ids(
        self, scope: OwnerScope, document_id: uuid.UUID
    ) -> Sequence[uuid.UUID]:
        with translate_database_errors("find memories citing a document"):
            return list(
                self._session.scalars(
                    select(ProvenanceRow.memory_id)
                    .join(
                        DocumentEvidenceRefRow,
                        (DocumentEvidenceRefRow.id == ProvenanceRow.document_evidence_id)
                        & (DocumentEvidenceRefRow.owner_id == ProvenanceRow.owner_id),
                    )
                    .where(
                        ProvenanceRow.owner_id == scope.owner_id,
                        DocumentEvidenceRefRow.document_ref == document_id,
                    )
                    .distinct()
                    .order_by(ProvenanceRow.memory_id)
                ).all()
            )

    def mark_source_deleted(self, scope: OwnerScope, document_id: uuid.UUID) -> int:
        with translate_database_errors("detach document evidence"):
            result = self._session.execute(
                update(DocumentEvidenceRefRow)
                .where(
                    DocumentEvidenceRefRow.owner_id == scope.owner_id,
                    DocumentEvidenceRefRow.document_ref == document_id,
                    DocumentEvidenceRefRow.status == DocumentEvidenceStatus.ACTIVE.value,
                )
                .values(
                    status=DocumentEvidenceStatus.SOURCE_DELETED.value,
                    document_id=None,
                    version_id=None,
                    chunk_id=None,
                )
                .execution_options(synchronize_session=False)
            )
        return int(getattr(result, "rowcount", 0))


# --- Provenance --------------------------------------------------------------------


def _provenance_from_row(row: ProvenanceRow) -> ProvenanceRecord:
    return ProvenanceRecord(
        id=row.id,
        owner_id=row.owner_id,
        memory_id=row.memory_id,
        role=ProvenanceRole(row.role),
        origin_kind=ProvenanceOriginKind(row.origin_kind),
        recorded_at=row.recorded_at,
        source_id=row.source_id,
        candidate_id=row.candidate_id,
        document_evidence_id=row.document_evidence_id,
        revision_number=row.revision_number,
    )


class SqlAlchemyProvenanceRepository:
    def __init__(
        self,
        session: Session,
        sources: SqlAlchemyMemorySourceRepository,
        candidates: SqlAlchemyMemoryCandidateRepository,
        memories: SqlAlchemyAtomicMemoryRepository,
        evidence: SqlAlchemyDocumentEvidenceRepository,
    ) -> None:
        self._session = session
        self._sources = sources
        self._candidates = candidates
        self._memories = memories
        self._evidence = evidence

    def add(self, scope: OwnerScope, record: ProvenanceRecord) -> None:
        _require_in_scope(scope, record.owner_id)
        if not self._memories.exists(scope, record.memory_id):
            raise RecordNotFoundError("atomic memory not found")
        if record.source_id is not None and not self._sources.exists(scope, record.source_id):
            raise RecordNotFoundError("memory source not found")
        if record.candidate_id is not None and not self._candidates.exists(
            scope, record.candidate_id
        ):
            raise RecordNotFoundError("memory candidate not found")
        if record.document_evidence_id is not None and not self._evidence.exists(
            scope, record.document_evidence_id
        ):
            raise RecordNotFoundError("document evidence not found")
        with translate_database_errors("add provenance record"):
            self._session.add(
                ProvenanceRow(
                    id=record.id,
                    owner_id=record.owner_id,
                    memory_id=record.memory_id,
                    revision_number=record.revision_number,
                    source_id=record.source_id,
                    candidate_id=record.candidate_id,
                    document_evidence_id=record.document_evidence_id,
                    role=record.role.value,
                    origin_kind=record.origin_kind.value,
                    recorded_at=record.recorded_at,
                )
            )
            self._session.flush()

    def list_for_memory(
        self, scope: OwnerScope, memory_id: uuid.UUID
    ) -> Sequence[ProvenanceRecord]:
        with translate_database_errors("list provenance records"):
            rows = self._session.scalars(
                select(ProvenanceRow)
                .where(
                    ProvenanceRow.owner_id == scope.owner_id, ProvenanceRow.memory_id == memory_id
                )
                .order_by(ProvenanceRow.recorded_at, ProvenanceRow.id)
                .execution_options(populate_existing=True)
            ).all()
        return [_provenance_from_row(row) for row in rows]
