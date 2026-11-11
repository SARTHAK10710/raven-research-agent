"""Domain invariants of the core Personal Memory records (no database)."""

import uuid
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from memory_engine.domain.errors import DomainValidationError
from memory_engine.domain.identifiers import OwnerScope, new_id
from memory_engine.domain.vocabulary import (
    CandidateOrigin,
    CandidateStatus,
    MemoryLifecycleStatus,
    MemoryOrigin,
    ProvenanceOriginKind,
    ProvenanceRole,
    RevisionChangeType,
    SourceProcessingStatus,
    SourceType,
)
from memory_engine.personal.domain import (
    AtomicMemory,
    AtomicMemoryRevision,
    MemoryCandidate,
    MemorySource,
    ProvenanceRecord,
)

T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
OWNER = uuid.UUID("00000000-0000-4000-8000-000000000001")


def memory(**overrides: Any) -> AtomicMemory:
    values: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "content": "Synthetic user prefers tea.",
        "origin": MemoryOrigin.EXPLICIT,
        "lifecycle_status": MemoryLifecycleStatus.ACTIVE,
        "recorded_at": T0,
        "revision_number": 1,
    }
    return AtomicMemory(**{**values, **overrides})


def candidate(**overrides: Any) -> MemoryCandidate:
    values: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "source_id": new_id(),
        "proposition": "Synthetic user prefers tea.",
        "status": CandidateStatus.CANDIDATE,
        "origin": CandidateOrigin.EXPLICIT,
    }
    return MemoryCandidate(**{**values, **overrides})


# --- OwnerScope ----------------------------------------------------------------------


def test_owner_scope_rejects_nil_and_non_uuid() -> None:
    with pytest.raises(DomainValidationError):
        OwnerScope(uuid.UUID(int=0))
    with pytest.raises(DomainValidationError):
        OwnerScope("not-a-uuid")  # type: ignore[arg-type]


def test_owner_scope_owns_only_its_owner() -> None:
    scope = OwnerScope(OWNER)
    assert scope.owns(OWNER)
    assert not scope.owns(new_id())


# --- Memory Source -------------------------------------------------------------------


def test_source_requires_aware_time_and_valid_checksum() -> None:
    base: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "source_type": SourceType.TEXT,
        "processing_status": SourceProcessingStatus.QUEUED,
        "received_at": T0,
    }
    MemorySource(**base, content_sha256="0" * 64)
    with pytest.raises(DomainValidationError, match="timezone"):
        MemorySource(**{**base, "received_at": T0.replace(tzinfo=None)})
    with pytest.raises(DomainValidationError, match="hex"):
        MemorySource(**base, content_sha256="Z" * 64)
    with pytest.raises(DomainValidationError):
        MemorySource(**base, content_ref="  ")


# --- Memory Candidate ----------------------------------------------------------------


@pytest.mark.parametrize("field", ["importance", "confidence", "extraction_confidence"])
@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_candidate_scores_stay_in_unit_range(field: str, value: float) -> None:
    with pytest.raises(DomainValidationError, match=field):
        candidate(**{field: value})


def test_candidate_scores_stay_independent() -> None:
    record = candidate(importance=0.9, confidence=0.1, extraction_confidence=0.5)
    assert (record.importance, record.confidence, record.extraction_confidence) == (0.9, 0.1, 0.5)


def test_unresolved_origin_cannot_be_validated() -> None:
    with pytest.raises(DomainValidationError, match="unresolved"):
        candidate(origin=CandidateOrigin.UNRESOLVED, status=CandidateStatus.VALIDATED)
    candidate(origin=CandidateOrigin.UNRESOLVED, status=CandidateStatus.NEEDS_REVIEW)


def test_blank_proposition_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        candidate(proposition="   ")


def test_candidate_json_fields_are_copied_and_read_only() -> None:
    context = {"scope": "ui"}
    record = candidate(context=context)
    context["scope"] = "changed"
    assert record.context["scope"] == "ui"
    with pytest.raises(TypeError):
        record.context["scope"] = "x"  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        record.proposition = "x"  # type: ignore[misc]


# --- Atomic Memory -------------------------------------------------------------------


def test_active_memory_requires_content() -> None:
    with pytest.raises(DomainValidationError, match="content"):
        memory(content=None)
    with pytest.raises(DomainValidationError):
        memory(content=" ")


def test_deleted_memory_keeps_only_a_tombstone() -> None:
    memory(lifecycle_status=MemoryLifecycleStatus.DELETED, content=None)
    with pytest.raises(DomainValidationError, match="tombstone"):
        memory(lifecycle_status=MemoryLifecycleStatus.DELETED, content="still here")
    with pytest.raises(DomainValidationError, match="tombstone"):
        memory(lifecycle_status=MemoryLifecycleStatus.DELETED, content=None, context={"a": 1})


def test_valid_time_interval_must_be_ordered() -> None:
    memory(valid_from=T0, valid_to=T0 + timedelta(days=1))
    with pytest.raises(DomainValidationError, match="valid_to"):
        memory(valid_from=T0, valid_to=T0 - timedelta(seconds=1))


def test_transaction_time_must_be_ordered_and_aware() -> None:
    with pytest.raises(DomainValidationError, match="superseded_at"):
        memory(superseded_at=T0 - timedelta(days=1))
    with pytest.raises(DomainValidationError, match="timezone"):
        memory(observed_at=datetime(2026, 1, 1))  # deliberately naive


def test_revision_numbers_start_at_one() -> None:
    with pytest.raises(DomainValidationError):
        memory(revision_number=0)


# --- revisions -----------------------------------------------------------------------


def test_snapshot_copies_the_memory_exactly() -> None:
    current = memory(structured={"k": "v"}, importance=0.3, valid_from=T0, observed_at=T0)
    snap = AtomicMemoryRevision.snapshot(
        current, revision_id=new_id(), change_type=RevisionChangeType.CREATED
    )
    assert (snap.memory_id, snap.revision_number, snap.content) == (current.id, 1, current.content)
    assert dict(snap.structured) == {"k": "v"}
    assert (snap.importance, snap.valid_from, snap.observed_at) == (0.3, T0, T0)


def test_only_the_first_revision_is_created() -> None:
    first = memory()
    with pytest.raises(DomainValidationError, match="created"):
        AtomicMemoryRevision.snapshot(
            first, revision_id=new_id(), change_type=RevisionChangeType.UPDATED
        )
    second = replace(first, revision_number=2)
    with pytest.raises(DomainValidationError, match="created"):
        AtomicMemoryRevision.snapshot(
            second, revision_id=new_id(), change_type=RevisionChangeType.CREATED
        )


# --- provenance ----------------------------------------------------------------------


def test_provenance_must_reference_evidence() -> None:
    base: dict[str, Any] = {
        "id": new_id(),
        "owner_id": OWNER,
        "memory_id": new_id(),
        "role": ProvenanceRole.SUPPORTING,
        "origin_kind": ProvenanceOriginKind.SYSTEM_GENERATED,
        "recorded_at": T0,
    }
    with pytest.raises(DomainValidationError, match="a source, a candidate or document evidence"):
        ProvenanceRecord(**base)
    ProvenanceRecord(**base, candidate_id=new_id())
    with pytest.raises(DomainValidationError):
        ProvenanceRecord(**base, source_id=new_id(), revision_number=0)


# --- lifecycle vocabulary semantics --------------------------------------------------


def test_only_active_memories_are_retrievable_by_default() -> None:
    assert [s for s in MemoryLifecycleStatus if s.retrievable_by_default] == [
        MemoryLifecycleStatus.ACTIVE
    ]
    assert {s for s in MemoryLifecycleStatus if s.never_retrievable} == {
        MemoryLifecycleStatus.DELETION_PENDING,
        MemoryLifecycleStatus.DELETED,
    }
