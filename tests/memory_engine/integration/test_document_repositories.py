"""Plan 8.2 section 13: document persistence, isolation and failure tests (real PostgreSQL).

``build`` is the synthetic-record fixture from conftest.py; all content is synthetic.
"""

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from memory_engine.documents.domain.vocabulary import (
    DocumentLifecycleStatus,
    EmbeddingStatus,
    ExtractionStatus,
    OperationStatus,
    OperationType,
    VersionProcessingStatus,
)
from memory_engine.domain.errors import DomainValidationError, OwnershipError
from memory_engine.domain.identifiers import OwnerScope, new_id
from memory_engine.domain.vocabulary import DocumentEvidenceStatus
from memory_engine.exceptions import (
    ConcurrencyConflictError,
    DeletionInProgressError,
    PersistenceError,
    RecordNotFoundError,
)
from memory_engine.infrastructure.persistence import (
    SqlAlchemyDocumentUnitOfWorkFactory,
    SqlAlchemyPersonalUnitOfWorkFactory,
)

pytestmark = pytest.mark.integration

DocUow = SqlAlchemyDocumentUnitOfWorkFactory
PmUow = SqlAlchemyPersonalUnitOfWorkFactory


def _registered(doc_uow_factory: DocUow, owner: OwnerScope, build: Any) -> tuple[Any, Any]:
    document, version = build.document(owner)
    with doc_uow_factory() as uow:
        uow.documents.register(owner, document, version)
    return document, version


def _chunked(
    doc_uow_factory: DocUow, owner: OwnerScope, build: Any, *texts: str
) -> tuple[Any, Any, list[Any]]:
    document, version = _registered(doc_uow_factory, owner, build)
    representation = build.representation(owner, version.id)
    chunks = build.chunks(owner, version.id, representation.id, *texts)
    with doc_uow_factory() as uow:
        uow.contents.add_representation(owner, representation)
        uow.contents.add_chunks(owner, chunks)
    return document, version, chunks


# --- registration and versions -----------------------------------------------------


def test_document_registration_round_trip(
    doc_uow_factory: DocUow, owner: OwnerScope, build: Any
) -> None:
    document, version = _registered(doc_uow_factory, owner, build)
    with doc_uow_factory() as uow:
        assert uow.documents.get(owner, document.id) == document
        assert uow.documents.get_version(owner, version.id) == version
        stored = uow.documents.list_versions(owner, document.id)
    assert stored == [version]
    assert stored[0].object_key == f"documents/{owner.owner_id}/{document.id}/{version.id}/original"
    assert "synthetic-report" not in stored[0].object_key


def test_same_filename_creates_distinct_documents(
    doc_uow_factory: DocUow, owner: OwnerScope, build: Any
) -> None:
    first, _ = _registered(doc_uow_factory, owner, build)
    second, _ = _registered(doc_uow_factory, owner, build)
    assert first.original_filename == second.original_filename
    assert first.id != second.id


def test_new_version_becomes_current_and_history_is_kept(
    doc_uow_factory: DocUow, owner: OwnerScope, build: Any
) -> None:
    document, v1 = _registered(doc_uow_factory, owner, build)
    v2 = build.version(owner, document.id, number=2)
    with doc_uow_factory() as uow:
        uow.documents.add_version(owner, v2, expected_current_version_id=v1.id)

    with doc_uow_factory() as uow:
        current = uow.documents.get(owner, document.id)
        history = uow.documents.list_versions(owner, document.id)
    assert current is not None and current.current_version_id == v2.id
    assert history == [v1, v2]
    assert v1.content_sha256 != v2.content_sha256


def test_stale_version_update_is_rejected_and_writes_nothing(
    doc_uow_factory: DocUow, owner: OwnerScope, build: Any
) -> None:
    document, v1 = _registered(doc_uow_factory, owner, build)
    v2 = build.version(owner, document.id, number=2)
    with doc_uow_factory() as uow:
        uow.documents.add_version(owner, v2, expected_current_version_id=v1.id)

    v3 = build.version(owner, document.id, number=3)
    with pytest.raises(ConcurrencyConflictError), doc_uow_factory() as uow:
        uow.documents.add_version(owner, v3, expected_current_version_id=v1.id)
    with pytest.raises(DomainValidationError, match="consecutively"), doc_uow_factory() as uow:
        uow.documents.add_version(
            owner, build.version(owner, document.id, number=5), expected_current_version_id=v2.id
        )

    with doc_uow_factory() as uow:
        assert [v.version_number for v in uow.documents.list_versions(owner, document.id)] == [1, 2]


def test_registration_rejects_inconsistent_input(
    doc_uow_factory: DocUow, owner: OwnerScope, build: Any
) -> None:
    document, version = build.document(owner)
    other_version = build.version(owner, document.id, number=1)
    with pytest.raises(DomainValidationError), doc_uow_factory() as uow:
        uow.documents.register(owner, document, other_version)
    second = build.version(owner, document.id, number=2, version_id=version.id)
    with pytest.raises(DomainValidationError), doc_uow_factory() as uow:
        uow.documents.register(owner, document, second)


# --- extracted content, chunks and locations ---------------------------------------


def test_chunks_keep_order_provenance_and_locations(
    doc_uow_factory: DocUow, owner: OwnerScope, build: Any
) -> None:
    _, version, chunks = _chunked(doc_uow_factory, owner, build, "First part.", "Second part.")
    with doc_uow_factory() as uow:
        stored = uow.contents.list_chunks(owner, version.id)
    assert stored == chunks
    assert [c.sequence for c in stored] == [0, 1]
    first_locations = stored[0].locations
    assert {loc.page_number for loc in first_locations} == {1, None}
    # Unknown location fields stay unknown rather than being fabricated.
    offsets_only = next(loc for loc in first_locations if loc.page_number is None)
    assert offsets_only.section_heading is None
    assert (offsets_only.start_offset, offsets_only.end_offset) == (0, 99)


def test_representation_round_trip(doc_uow_factory: DocUow, owner: OwnerScope, build: Any) -> None:
    _, version = _registered(doc_uow_factory, owner, build)
    representation = build.representation(owner, version.id)
    with doc_uow_factory() as uow:
        uow.contents.add_representation(owner, representation)
        assert uow.contents.get_representation(owner, representation.id) == representation


def test_a_chunk_never_mixes_versions(
    doc_uow_factory: DocUow, connection: Connection, owner: OwnerScope, build: Any
) -> None:
    document, v1 = _registered(doc_uow_factory, owner, build)
    v2 = build.version(owner, document.id, number=2)
    rep_v1 = build.representation(owner, v1.id)
    with doc_uow_factory() as uow:
        uow.documents.add_version(owner, v2, expected_current_version_id=v1.id)
        uow.contents.add_representation(owner, rep_v1)

    # Repository: a v2 chunk cannot use v1's representation.
    with pytest.raises(RecordNotFoundError), doc_uow_factory() as uow:
        uow.contents.add_chunks(owner, build.chunks(owner, v2.id, rep_v1.id, "Mixed."))
    # Database: the composite foreign key rejects the same thing in raw SQL.
    savepoint = connection.begin_nested()
    with pytest.raises(IntegrityError, match="fk_doc_chunk_representation_id"):
        connection.execute(
            text(
                "INSERT INTO memory.doc_chunk (id, owner_id, version_id, representation_id,"
                " sequence, content, content_sha256, chunking_strategy, chunking_version)"
                " VALUES (:id, :owner, :v2, :rep, 0, 'x', :sha, 's', '1')"
            ),
            {
                "id": new_id(),
                "owner": owner.owner_id,
                "v2": v2.id,
                "rep": rep_v1.id,
                "sha": "c" * 64,
            },
        )
    savepoint.rollback()


def test_a_failed_extraction_records_failure_and_cannot_be_chunked(
    doc_uow_factory: DocUow, owner: OwnerScope, build: Any
) -> None:
    _, version = _registered(doc_uow_factory, owner, build)
    failed = build.representation(owner, version.id, ExtractionStatus.EXTRACTION_FAILED)
    with doc_uow_factory() as uow:
        uow.contents.add_representation(owner, failed)
        uow.documents.set_version_status(
            owner,
            version.id,
            VersionProcessingStatus.EXTRACTION_FAILED,
            expected=VersionProcessingStatus.STORED,
        )
    with pytest.raises(DomainValidationError, match="failed extraction"), doc_uow_factory() as uow:
        uow.contents.add_chunks(owner, build.chunks(owner, version.id, failed.id, "Nothing."))

    with doc_uow_factory() as uow:
        stored = uow.documents.get_version(owner, version.id)
        representation = uow.contents.get_representation(owner, failed.id)
    assert stored is not None
    assert stored.processing_status is VersionProcessingStatus.EXTRACTION_FAILED
    assert representation is not None and representation.error_code == "ENCRYPTED_PDF"


def test_chunk_batches_must_share_version_and_representation(
    doc_uow_factory: DocUow, owner: OwnerScope, build: Any
) -> None:
    _, version = _registered(doc_uow_factory, owner, build)
    mixed = build.chunks(owner, version.id, new_id(), "a") + build.chunks(
        owner, version.id, new_id(), "b"
    )
    with pytest.raises(DomainValidationError), doc_uow_factory() as uow:
        uow.contents.add_chunks(owner, mixed)
    with doc_uow_factory() as uow:
        uow.contents.add_chunks(owner, [])  # nothing to do is not an error


def test_keyword_search_finds_chunks_within_one_owner_only(
    doc_uow_factory: DocUow,
    connection: Connection,
    owner: OwnerScope,
    other_owner: OwnerScope,
    build: Any,
) -> None:
    _chunked(doc_uow_factory, owner, build, "Quarterly revenue grew strongly.")
    _chunked(doc_uow_factory, other_owner, build, "Quarterly revenue fell sharply.")
    found = connection.scalars(
        text(
            "SELECT content FROM memory.doc_chunk"
            " WHERE owner_id = :owner AND tsv @@ plainto_tsquery('simple', 'quarterly revenue')"
        ),
        {"owner": owner.owner_id},
    ).all()
    assert found == ["Quarterly revenue grew strongly."]


# --- embedding metadata ------------------------------------------------------------


def test_embedding_metadata_is_version_aware_and_not_duplicated(
    doc_uow_factory: DocUow, owner: OwnerScope, build: Any
) -> None:
    _, version, (chunk,) = _chunked(doc_uow_factory, owner, build, "Embed me.")
    embedding = build.embedding(owner, chunk)
    with doc_uow_factory() as uow:
        uow.contents.add_embedding(owner, embedding)
        uow.contents.set_embedding_status(
            owner, embedding.id, EmbeddingStatus.GENERATING, expected=EmbeddingStatus.PENDING
        )
        stored = uow.contents.get_embedding(owner, embedding.id)
    assert stored is not None
    assert (stored.version_id, stored.status) == (version.id, EmbeddingStatus.GENERATING)

    duplicate = build.embedding(owner, chunk)
    with pytest.raises(PersistenceError) as caught, doc_uow_factory() as uow:
        uow.contents.add_embedding(owner, duplicate)
    assert caught.value.details["constraint"] == "uq_doc_embedding_chunk_model"
    with pytest.raises(ConcurrencyConflictError), doc_uow_factory() as uow:
        uow.contents.set_embedding_status(
            owner, embedding.id, EmbeddingStatus.GENERATED, expected=EmbeddingStatus.PENDING
        )


# --- processing operations: idempotency and recovery -------------------------------


def test_operations_are_idempotent_per_key(
    doc_uow_factory: DocUow, owner: OwnerScope, build: Any
) -> None:
    document, version = _registered(doc_uow_factory, owner, build)
    first = build.operation(owner, document.id, "chunk:v1", version_id=version.id)
    retry = build.operation(owner, document.id, "chunk:v1", version_id=version.id)
    with doc_uow_factory() as uow:
        stored, created = uow.operations.start(owner, first)
    assert created and stored == first
    with doc_uow_factory() as uow:
        again, created_again = uow.operations.start(owner, retry)
    assert not created_again
    assert again.id == first.id


def test_operation_retry_and_failure_are_recorded(
    doc_uow_factory: DocUow, owner: OwnerScope, build: Any
) -> None:
    document, _ = _registered(doc_uow_factory, owner, build)
    operation = build.operation(owner, document.id, "extract:1", OperationType.EXTRACTION)
    with doc_uow_factory() as uow:
        uow.operations.start(owner, operation)
        uow.operations.transition(
            owner,
            operation.id,
            OperationStatus.RUNNING,
            expected=OperationStatus.QUEUED,
            count_attempt=True,
        )
        failed = uow.operations.transition(
            owner,
            operation.id,
            OperationStatus.RETRY_PENDING,
            expected=OperationStatus.RUNNING,
            error_code="PARSER_TIMEOUT",
        )
    assert (failed.status, failed.attempts, failed.error_code) == (
        OperationStatus.RETRY_PENDING,
        1,
        "PARSER_TIMEOUT",
    )
    # A stale worker that still thinks the operation is running is rejected.
    with pytest.raises(ConcurrencyConflictError), doc_uow_factory() as uow:
        uow.operations.transition(
            owner, operation.id, OperationStatus.COMPLETED, expected=OperationStatus.RUNNING
        )
    with pytest.raises(DomainValidationError), doc_uow_factory() as uow:
        uow.operations.transition(
            owner,
            operation.id,
            OperationStatus.FAILED,
            expected=OperationStatus.RETRY_PENDING,
            error_code="free text with content",
        )


# --- ownership isolation -----------------------------------------------------------


def test_another_owners_documents_are_invisible(
    doc_uow_factory: DocUow, owner: OwnerScope, other_owner: OwnerScope, build: Any
) -> None:
    document, version, _ = _chunked(doc_uow_factory, owner, build, "Private text.")
    operation = build.operation(owner, document.id, "op")
    with doc_uow_factory() as uow:
        uow.operations.start(owner, operation)

    with doc_uow_factory() as uow:
        assert uow.documents.get(other_owner, document.id) is None
        assert uow.documents.get_version(other_owner, version.id) is None
        assert uow.documents.list_versions(other_owner, document.id) == []
        assert uow.contents.list_chunks(other_owner, version.id) == []
        assert uow.operations.get(other_owner, operation.id) is None
        with pytest.raises(RecordNotFoundError):
            uow.documents.dependencies(other_owner, document.id)


def test_another_owner_cannot_write_into_a_document(
    doc_uow_factory: DocUow, owner: OwnerScope, other_owner: OwnerScope, build: Any
) -> None:
    document, version = _registered(doc_uow_factory, owner, build)
    with pytest.raises(RecordNotFoundError), doc_uow_factory() as uow:
        uow.contents.add_representation(other_owner, build.representation(other_owner, version.id))
    with pytest.raises(RecordNotFoundError), doc_uow_factory() as uow:
        uow.operations.start(other_owner, build.operation(other_owner, document.id, "steal"))
    with pytest.raises(RecordNotFoundError), doc_uow_factory() as uow:
        uow.documents.add_version(
            other_owner,
            build.version(other_owner, document.id, number=2),
            expected_current_version_id=version.id,
        )
    with pytest.raises(OwnershipError), doc_uow_factory() as uow:
        uow.contents.add_representation(owner, build.representation(other_owner, version.id))


# --- deletion awareness and dependency discovery -----------------------------------


def test_no_derived_content_is_written_once_deletion_is_requested(
    doc_uow_factory: DocUow, owner: OwnerScope, build: Any
) -> None:
    document, version, (chunk,) = _chunked(doc_uow_factory, owner, build, "Going away.")
    with doc_uow_factory() as uow:
        uow.documents.set_lifecycle_status(
            owner,
            document.id,
            DocumentLifecycleStatus.DELETION_REQUESTED,
            expected=DocumentLifecycleStatus.AVAILABLE,
        )

    stale_writes: list[Callable[[Any], object]] = [
        lambda uow: uow.contents.add_representation(owner, build.representation(owner, version.id)),
        lambda uow: uow.contents.add_embedding(owner, build.embedding(owner, chunk)),
        lambda uow: uow.operations.start(owner, build.operation(owner, document.id, "late-chunk")),
        lambda uow: uow.documents.add_version(
            owner,
            build.version(owner, document.id, number=2),
            expected_current_version_id=version.id,
        ),
    ]
    for write in stale_writes:
        with pytest.raises(DeletionInProgressError), doc_uow_factory() as uow:
            write(uow)

    # The deletion workflow itself may still record its operation.
    deletion = build.operation(owner, document.id, "delete:doc", OperationType.DELETION)
    with doc_uow_factory() as uow:
        _, created = uow.operations.start(owner, deletion)
    assert created


def test_deletion_dependencies_are_discoverable(
    doc_uow_factory: DocUow, owner: OwnerScope, build: Any
) -> None:
    document, version, chunks = _chunked(doc_uow_factory, owner, build, "One.", "Two.")
    embedding = build.embedding(owner, chunks[0])
    pending = build.operation(owner, document.id, "embed:1", OperationType.EMBEDDING)
    done = build.operation(owner, document.id, "chunk:1")
    with doc_uow_factory() as uow:
        uow.contents.add_embedding(owner, embedding)
        uow.operations.start(owner, pending)
        uow.operations.start(owner, done)
        uow.operations.transition(
            owner, done.id, OperationStatus.COMPLETED, expected=OperationStatus.QUEUED
        )
        found = uow.documents.dependencies(owner, document.id)

    assert found.version_ids == (version.id,)
    assert found.object_keys == (version.object_key,)
    assert len(found.representation_ids) == 1
    assert set(found.chunk_ids) == {c.id for c in chunks}
    assert found.chunk_location_count == 4
    assert found.embedding_ids == (embedding.id,)
    assert found.open_operation_ids == (pending.id,)


# --- database guards ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("statement", "allowed"),
    [
        ("UPDATE memory.doc_document_version SET object_key = 'x' WHERE id = :version", False),
        ("UPDATE memory.doc_document_version SET size_bytes = 1 WHERE id = :version", False),
        ("UPDATE memory.doc_chunk SET content = 'changed' WHERE version_id = :version", False),
        (
            "UPDATE memory.doc_chunk_location SET page_number = 9 WHERE version_id = :version",
            False,
        ),
        (
            "UPDATE memory.doc_document_version SET processing_status = 'chunked'"
            " WHERE id = :version",
            True,
        ),
    ],
)
def test_immutable_columns_are_guarded_by_the_database(
    doc_uow_factory: DocUow,
    connection: Connection,
    owner: OwnerScope,
    build: Any,
    statement: str,
    allowed: bool,
) -> None:
    _, version, _ = _chunked(doc_uow_factory, owner, build, "Immutable text.")
    savepoint = connection.begin_nested()
    if allowed:
        connection.execute(text(statement), {"version": version.id})
    else:
        with pytest.raises(DBAPIError, match="immutable columns"):
            connection.execute(text(statement), {"version": version.id})
    savepoint.rollback()


# --- separation from Personal Memory and the evidence path -------------------------


def test_document_chunks_are_never_personal_memories(
    doc_uow_factory: DocUow, uow_factory: PmUow, owner: OwnerScope, build: Any
) -> None:
    _chunked(doc_uow_factory, owner, build, "I prefer tea.", "I live in City A.")
    with uow_factory() as uow:
        assert uow.memories.list_retrievable(owner) == []


def _memory_with_document_evidence(
    doc_uow_factory: DocUow, uow_factory: PmUow, owner: OwnerScope, build: Any
) -> tuple[Any, Any, Any, Any, Any]:
    document, version, (chunk,) = _chunked(doc_uow_factory, owner, build, "Born in 1990.")
    source = build.source(owner)
    candidate = build.candidate(owner, source.id)
    memory, created = build.memory(owner, "Synthetic user was born in 1990.")
    evidence = build.evidence(owner, candidate.id, chunk, document.id)
    with uow_factory() as uow:
        uow.sources.add(owner, source)
        uow.candidates.add(owner, candidate)
        uow.evidence.add(owner, evidence)
        uow.memories.add(owner, memory, created)
        uow.provenance.add(
            owner,
            build.provenance(
                owner, memory.id, candidate_id=candidate.id, document_evidence_id=evidence.id
            ),
        )
    return document, version, chunk, memory, evidence


def test_document_evidence_is_traceable_to_memories(
    doc_uow_factory: DocUow, uow_factory: PmUow, owner: OwnerScope, build: Any
) -> None:
    document, version, chunk, memory, evidence = _memory_with_document_evidence(
        doc_uow_factory, uow_factory, owner, build
    )
    with uow_factory() as uow:
        assert uow.evidence.list_for_candidate(owner, evidence.candidate_id) == [evidence]
        assert uow.evidence.dependent_memory_ids(owner, document.id) == [memory.id]
        cited = uow.provenance.list_for_memory(owner, memory.id)
    assert [p.document_evidence_id for p in cited] == [evidence.id]
    assert (evidence.version_ref, evidence.chunk_ref) == (version.id, chunk.id)


def test_a_new_version_does_not_move_existing_evidence(
    doc_uow_factory: DocUow, uow_factory: PmUow, owner: OwnerScope, build: Any
) -> None:
    document, v1, _, _, evidence = _memory_with_document_evidence(
        doc_uow_factory, uow_factory, owner, build
    )
    with doc_uow_factory() as uow:
        uow.documents.add_version(
            owner, build.version(owner, document.id, number=2), expected_current_version_id=v1.id
        )
    with uow_factory() as uow:
        (stored,) = uow.evidence.list_for_candidate(owner, evidence.candidate_id)
    assert stored.version_ref == v1.id  # citations still point at the version they came from


def test_active_evidence_blocks_document_deletion_until_detached(
    doc_uow_factory: DocUow,
    uow_factory: PmUow,
    connection: Connection,
    owner: OwnerScope,
    build: Any,
) -> None:
    document, _, chunk, memory, evidence = _memory_with_document_evidence(
        doc_uow_factory, uow_factory, owner, build
    )
    savepoint = connection.begin_nested()
    with pytest.raises(IntegrityError, match="fk_pm_document_evidence_ref_chunk_id_doc_chunk"):
        connection.execute(
            text("DELETE FROM memory.doc_chunk_location WHERE chunk_id = :chunk"),
            {"chunk": chunk.id},
        )
        connection.execute(
            text("DELETE FROM memory.doc_chunk WHERE id = :chunk"), {"chunk": chunk.id}
        )
    savepoint.rollback()

    with uow_factory() as uow:
        assert uow.evidence.mark_source_deleted(owner, document.id) == 1
        assert uow.evidence.mark_source_deleted(owner, document.id) == 0  # idempotent

    savepoint = connection.begin_nested()
    connection.execute(
        text("DELETE FROM memory.doc_chunk_location WHERE chunk_id = :chunk"), {"chunk": chunk.id}
    )
    connection.execute(text("DELETE FROM memory.doc_chunk WHERE id = :chunk"), {"chunk": chunk.id})
    savepoint.commit()

    with uow_factory() as uow:
        (detached,) = uow.evidence.list_for_candidate(owner, evidence.candidate_id)
        assert detached.status is DocumentEvidenceStatus.SOURCE_DELETED
        # Opaque identifiers survive for provenance; the memory itself is untouched.
        assert (detached.document_ref, detached.chunk_ref) == (document.id, chunk.id)
        assert uow.memories.get(owner, memory.id) == memory
        assert uow.evidence.dependent_memory_ids(owner, document.id) == [memory.id]


def test_evidence_must_match_the_document_and_owner(
    doc_uow_factory: DocUow,
    uow_factory: PmUow,
    owner: OwnerScope,
    other_owner: OwnerScope,
    build: Any,
) -> None:
    document, _, (chunk,) = _chunked(doc_uow_factory, owner, build, "Mine.")
    foreign_doc, _, (foreign_chunk,) = _chunked(doc_uow_factory, other_owner, build, "Theirs.")
    other_doc, _, _ = _chunked(doc_uow_factory, owner, build, "Another document.")
    source = build.source(owner)
    candidate = build.candidate(owner, source.id)
    with uow_factory() as uow:
        uow.sources.add(owner, source)
        uow.candidates.add(owner, candidate)

    bad = [
        build.evidence(owner, candidate.id, foreign_chunk, foreign_doc.id),  # other owner
        build.evidence(owner, candidate.id, chunk, other_doc.id),  # version of another document
        build.evidence(owner, new_id(), chunk, document.id),  # unknown candidate
    ]
    for evidence in bad:
        with pytest.raises(RecordNotFoundError), uow_factory() as uow:
            uow.evidence.add(owner, evidence)

    with doc_uow_factory() as uow:
        uow.documents.set_lifecycle_status(
            owner,
            document.id,
            DocumentLifecycleStatus.DELETION_REQUESTED,
            expected=DocumentLifecycleStatus.AVAILABLE,
        )
    with pytest.raises(DeletionInProgressError), uow_factory() as uow:
        uow.evidence.add(owner, build.evidence(owner, candidate.id, chunk, document.id))


def test_evidence_link_columns_must_match_status(connection: Connection, owner: OwnerScope) -> None:
    savepoint = connection.begin_nested()
    with pytest.raises(IntegrityError, match="ck_pm_document_evidence_ref_links_match_status"):
        connection.execute(
            text(
                "INSERT INTO memory.pm_document_evidence_ref (id, owner_id, candidate_id,"
                " document_ref, version_ref, extraction_method, status, recorded_at)"
                " VALUES (:id, :owner, :cand, :doc, :ver, 'm', 'active', now())"
            ),
            {
                "id": uuid.uuid4(),
                "owner": owner.owner_id,
                "cand": uuid.uuid4(),
                "doc": uuid.uuid4(),
                "ver": uuid.uuid4(),
            },
        )
    savepoint.rollback()
