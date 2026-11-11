"""Plan 8.2 tests for Personal Memory persistence against real PostgreSQL.

Covers repository behavior, ownership enforcement, revisions with optimistic
concurrency, transaction rollback, and the integrity rules the database itself
enforces (composite owner foreign keys, check constraints, append-only rows).

``build`` is the synthetic-record fixture from conftest.py.
"""

import uuid
from dataclasses import replace
from typing import Any

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from memory_engine.domain.errors import DomainValidationError, OwnershipError
from memory_engine.domain.identifiers import OwnerScope, new_id
from memory_engine.domain.vocabulary import MemoryLifecycleStatus, RevisionChangeType
from memory_engine.exceptions import (
    ConcurrencyConflictError,
    PersistenceError,
    RecordNotFoundError,
)
from memory_engine.infrastructure.persistence import SqlAlchemyPersonalUnitOfWorkFactory

pytestmark = pytest.mark.integration

UowFactory = SqlAlchemyPersonalUnitOfWorkFactory


# --- round trips -------------------------------------------------------------------


def test_source_and_candidates_round_trip(
    uow_factory: UowFactory, owner: OwnerScope, build: Any
) -> None:
    source = build.source(owner)
    first, second = build.candidate(owner, source.id), build.candidate(owner, source.id)
    with uow_factory() as uow:
        uow.sources.add(owner, source)
        uow.candidates.add(owner, first)
        uow.candidates.add(owner, second)

    with uow_factory() as uow:
        assert uow.sources.get(owner, source.id) == source
        assert uow.candidates.get(owner, first.id) == first
        assert {c.id for c in uow.candidates.list_for_source(owner, source.id)} == {
            first.id,
            second.id,
        }


def test_memory_with_revision_and_provenance_round_trip(
    uow_factory: UowFactory, owner: OwnerScope, build: Any
) -> None:
    source = build.source(owner)
    candidate = build.candidate(owner, source.id)
    memory, revision = build.memory(owner)
    evidence = build.provenance(owner, memory.id, source_id=source.id, candidate_id=candidate.id)
    with uow_factory() as uow:
        uow.sources.add(owner, source)
        uow.candidates.add(owner, candidate)
        uow.memories.add(owner, memory, revision)
        uow.provenance.add(owner, evidence)

    with uow_factory() as uow:
        assert uow.memories.get(owner, memory.id) == memory
        assert uow.memories.list_revisions(owner, memory.id) == [revision]
        assert uow.provenance.list_for_memory(owner, memory.id) == [evidence]


# --- ownership isolation -----------------------------------------------------------


def test_other_owners_records_are_invisible(
    uow_factory: UowFactory, owner: OwnerScope, other_owner: OwnerScope, build: Any
) -> None:
    source = build.source(owner)
    candidate = build.candidate(owner, source.id)
    memory, revision = build.memory(owner)
    with uow_factory() as uow:
        uow.sources.add(owner, source)
        uow.candidates.add(owner, candidate)
        uow.memories.add(owner, memory, revision)
        uow.provenance.add(owner, build.provenance(owner, memory.id, source_id=source.id))

    with uow_factory() as uow:
        assert uow.sources.get(other_owner, source.id) is None
        assert uow.candidates.get(other_owner, candidate.id) is None
        assert uow.candidates.list_for_source(other_owner, source.id) == []
        assert uow.memories.get(other_owner, memory.id) is None
        assert uow.memories.list_revisions(other_owner, memory.id) == []
        assert uow.memories.list_retrievable(other_owner) == []
        assert uow.provenance.list_for_memory(other_owner, memory.id) == []


def test_writing_a_record_outside_the_scope_is_rejected(
    uow_factory: UowFactory, owner: OwnerScope, other_owner: OwnerScope, build: Any
) -> None:
    with uow_factory() as uow, pytest.raises(OwnershipError):
        uow.sources.add(other_owner, build.source(owner))


def test_candidate_cannot_reference_another_owners_source(
    uow_factory: UowFactory, owner: OwnerScope, other_owner: OwnerScope, build: Any
) -> None:
    foreign_source = build.source(other_owner)
    with uow_factory() as uow:
        uow.sources.add(other_owner, foreign_source)

    # Same error as for a missing source: existence is not revealed.
    with uow_factory() as uow, pytest.raises(RecordNotFoundError):
        uow.candidates.add(owner, build.candidate(owner, foreign_source.id))
    with uow_factory() as uow, pytest.raises(RecordNotFoundError):
        uow.candidates.add(owner, build.candidate(owner, new_id()))


def test_provenance_cannot_reference_another_owners_records(
    uow_factory: UowFactory, owner: OwnerScope, other_owner: OwnerScope, build: Any
) -> None:
    memory, revision = build.memory(owner)
    foreign_source = build.source(other_owner)
    with uow_factory() as uow:
        uow.memories.add(owner, memory, revision)
        uow.sources.add(other_owner, foreign_source)

    with uow_factory() as uow, pytest.raises(RecordNotFoundError):
        uow.provenance.add(owner, build.provenance(owner, memory.id, source_id=foreign_source.id))


def test_database_rejects_a_cross_owner_reference_even_without_the_repository(
    connection: Connection,
    owner: OwnerScope,
    other_owner: OwnerScope,
    uow_factory: UowFactory,
    build: Any,
) -> None:
    foreign_source = build.source(other_owner)
    with uow_factory() as uow:
        uow.sources.add(other_owner, foreign_source)

    savepoint = connection.begin_nested()
    with pytest.raises(IntegrityError, match="fk_pm_memory_candidate_source_id_pm_memory_source"):
        connection.execute(
            text(
                "INSERT INTO memory.pm_memory_candidate (id, owner_id, source_id, proposition, "
                "status, origin) VALUES (:id, :owner, :source, 'x', 'candidate', 'explicit')"
            ),
            {"id": new_id(), "owner": owner.owner_id, "source": foreign_source.id},
        )
    savepoint.rollback()


# --- lifecycle-aware retrieval -----------------------------------------------------


def test_default_retrieval_returns_active_memories_only(
    uow_factory: UowFactory, owner: OwnerScope, build: Any
) -> None:
    active, active_rev = build.memory(owner, "Synthetic fact that is current.")
    old, old_rev = build.memory(owner, "Synthetic fact that was replaced.")
    with uow_factory() as uow:
        uow.memories.add(owner, active, active_rev)
        uow.memories.add(owner, old, old_rev)
        historical, historical_rev = build.next_state(
            old, RevisionChangeType.SUPERSEDED, lifecycle_status=MemoryLifecycleStatus.HISTORICAL
        )
        uow.memories.apply_revision(owner, historical, historical_rev, expected_revision_number=1)

    with uow_factory() as uow:
        assert [m.id for m in uow.memories.list_retrievable(owner)] == [active.id]
        # Still readable directly (history is retained), just not returned by default.
        stored = uow.memories.get(owner, old.id)
        assert stored is not None
        assert stored.lifecycle_status is MemoryLifecycleStatus.HISTORICAL


def test_tombstoned_memories_are_never_returned(
    uow_factory: UowFactory, owner: OwnerScope, build: Any
) -> None:
    memory, revision = build.memory(owner)
    with uow_factory() as uow:
        uow.memories.add(owner, memory, revision)
        pending, pending_rev = build.next_state(
            memory,
            RevisionChangeType.RETRACTED,
            lifecycle_status=MemoryLifecycleStatus.DELETION_PENDING,
        )
        uow.memories.apply_revision(owner, pending, pending_rev, expected_revision_number=1)

    with uow_factory() as uow:
        assert uow.memories.get(owner, memory.id) is None
        assert uow.memories.list_retrievable(owner) == []
        # And a tombstoned memory cannot be revised back into visibility.
        revived, revived_rev = build.next_state(
            pending, RevisionChangeType.UPDATED, lifecycle_status=MemoryLifecycleStatus.ACTIVE
        )
        with pytest.raises(RecordNotFoundError):
            uow.memories.apply_revision(owner, revived, revived_rev, expected_revision_number=2)


# --- revisions and optimistic concurrency ------------------------------------------


def test_revision_history_is_preserved(
    uow_factory: UowFactory, owner: OwnerScope, build: Any
) -> None:
    memory, created = build.memory(owner, "Synthetic user lives in City A.")
    with uow_factory() as uow:
        uow.memories.add(owner, memory, created)
        moved, updated = build.next_state(
            memory, RevisionChangeType.UPDATED, content="Synthetic user lives in City B."
        )
        uow.memories.apply_revision(owner, moved, updated, expected_revision_number=1)

    with uow_factory() as uow:
        current = uow.memories.get(owner, memory.id)
        history = uow.memories.list_revisions(owner, memory.id)
    assert current is not None
    assert current.content == "Synthetic user lives in City B."
    assert current.revision_number == 2
    assert [(r.revision_number, r.change_type, r.content) for r in history] == [
        (1, RevisionChangeType.CREATED, "Synthetic user lives in City A."),
        (2, RevisionChangeType.UPDATED, "Synthetic user lives in City B."),
    ]


def test_stale_update_is_rejected_and_writes_nothing(
    uow_factory: UowFactory, owner: OwnerScope, build: Any
) -> None:
    memory, created = build.memory(owner)
    with uow_factory() as uow:
        uow.memories.add(owner, memory, created)

    # Two writers both read revision 1; the first one wins.
    first, first_rev = build.next_state(memory, RevisionChangeType.UPDATED, content="First edit.")
    second, second_rev = build.next_state(
        memory, RevisionChangeType.UPDATED, content="Second edit."
    )
    with uow_factory() as uow:
        uow.memories.apply_revision(owner, first, first_rev, expected_revision_number=1)

    with pytest.raises(ConcurrencyConflictError), uow_factory() as uow:
        uow.memories.apply_revision(owner, second, second_rev, expected_revision_number=1)

    with uow_factory() as uow:
        stored = uow.memories.get(owner, memory.id)
        assert stored is not None
        assert stored.content == "First edit."
        assert len(uow.memories.list_revisions(owner, memory.id)) == 2


def test_revising_another_owners_memory_looks_like_not_found(
    uow_factory: UowFactory, owner: OwnerScope, other_owner: OwnerScope, build: Any
) -> None:
    memory, created = build.memory(owner)
    with uow_factory() as uow:
        uow.memories.add(owner, memory, created)

    # Another owner forges a state for the same memory id inside their own scope.
    impostor = replace(build.memory(other_owner)[0], id=memory.id)
    hijack, hijack_rev = build.next_state(impostor, RevisionChangeType.UPDATED)
    with pytest.raises(RecordNotFoundError), uow_factory() as uow:
        uow.memories.apply_revision(other_owner, hijack, hijack_rev, expected_revision_number=1)

    with uow_factory() as uow:
        assert uow.memories.get(owner, memory.id) == memory


def test_inconsistent_revision_writes_are_rejected_before_the_database(
    uow_factory: UowFactory, owner: OwnerScope, build: Any
) -> None:
    memory, created = build.memory(owner)
    with uow_factory() as uow:
        # A new memory must start at revision 1 with a 'created' snapshot of itself.
        second, second_rev = build.next_state(memory, RevisionChangeType.UPDATED)
        with pytest.raises(DomainValidationError):
            uow.memories.add(owner, second, second_rev)
        other_snapshot = build.memory(owner, "A different synthetic fact.")[1]
        with pytest.raises(DomainValidationError, match="does not match"):
            uow.memories.add(owner, memory, other_snapshot)
        uow.memories.add(owner, memory, created)

        updated, updated_rev = build.next_state(memory, RevisionChangeType.UPDATED)
        with pytest.raises(DomainValidationError, match="one revision ahead"):
            uow.memories.apply_revision(owner, updated, updated_rev, expected_revision_number=2)
        stale_snapshot = replace(updated_rev, content="Not what the state says.")
        with pytest.raises(DomainValidationError, match="does not match"):
            uow.memories.apply_revision(owner, updated, stale_snapshot, expected_revision_number=1)

    with uow_factory() as uow:
        assert uow.memories.list_revisions(owner, memory.id) == [created]


def test_provenance_rejects_a_missing_candidate(
    uow_factory: UowFactory, owner: OwnerScope, build: Any
) -> None:
    memory, created = build.memory(owner)
    with uow_factory() as uow:
        uow.memories.add(owner, memory, created)
        with pytest.raises(RecordNotFoundError, match="candidate"):
            uow.provenance.add(owner, build.provenance(owner, memory.id, candidate_id=new_id()))
        with pytest.raises(RecordNotFoundError, match="memory"):
            uow.provenance.add(owner, build.provenance(owner, new_id(), source_id=new_id()))


# --- transactions ------------------------------------------------------------------


def test_failed_unit_of_work_rolls_back_everything(
    uow_factory: UowFactory, owner: OwnerScope, build: Any
) -> None:
    source = build.source(owner)

    class BoomError(Exception):
        pass

    with pytest.raises(BoomError), uow_factory() as uow:
        uow.sources.add(owner, source)
        raise BoomError

    with uow_factory() as uow:
        assert uow.sources.get(owner, source.id) is None


def test_duplicate_identifier_surfaces_as_persistence_error(
    uow_factory: UowFactory, owner: OwnerScope, build: Any
) -> None:
    source = build.source(owner)
    with uow_factory() as uow:
        uow.sources.add(owner, source)

    with pytest.raises(PersistenceError) as caught, uow_factory() as uow:
        uow.sources.add(owner, source)
    assert caught.value.details["constraint"] == "pk_pm_memory_source"
    # The safe message never echoes record content.
    assert str(source.id) not in str(caught.value)


# --- integrity enforced by PostgreSQL itself ---------------------------------------


@pytest.mark.parametrize(
    ("statement", "constraint"),
    [
        (
            "INSERT INTO memory.pm_atomic_memory (id, owner_id, content, origin, lifecycle_status,"
            " recorded_at, revision_number)"
            " VALUES (:id, :owner, NULL, 'explicit', 'active', now(), 1)",
            "ck_pm_atomic_memory_content_matches_lifecycle",
        ),
        (
            "INSERT INTO memory.pm_atomic_memory (id, owner_id, content, origin, lifecycle_status,"
            " recorded_at, revision_number)"
            " VALUES (:id, :owner, 'x', 'explicit', 'archived', now(), 1)",
            "ck_pm_atomic_memory_lifecycle_status",
        ),
        (
            "INSERT INTO memory.pm_atomic_memory (id, owner_id, content, origin, lifecycle_status,"
            " recorded_at, revision_number, confidence)"
            " VALUES (:id, :owner, 'x', 'explicit', 'active', now(), 1, 1.5)",
            "ck_pm_atomic_memory_confidence",
        ),
        (
            "INSERT INTO memory.pm_atomic_memory (id, owner_id, content, origin, lifecycle_status,"
            " recorded_at, revision_number, valid_from, valid_to) VALUES (:id, :owner, 'x',"
            " 'explicit', 'active', now(), 1, now(), now() - interval '1 day')",
            "ck_pm_atomic_memory_valid_interval",
        ),
    ],
)
def test_check_constraints_reject_invalid_rows(
    connection: Connection, owner: OwnerScope, statement: str, constraint: str
) -> None:
    savepoint = connection.begin_nested()
    with pytest.raises(IntegrityError, match=constraint):
        connection.execute(text(statement), {"id": uuid.uuid4(), "owner": owner.owner_id})
    savepoint.rollback()


@pytest.mark.parametrize("table", ["pm_atomic_memory_revision", "pm_provenance"])
def test_append_only_rows_cannot_be_updated(
    connection: Connection, uow_factory: UowFactory, owner: OwnerScope, build: Any, table: str
) -> None:
    source = build.source(owner)
    memory, revision = build.memory(owner)
    with uow_factory() as uow:
        uow.sources.add(owner, source)
        uow.memories.add(owner, memory, revision)
        uow.provenance.add(owner, build.provenance(owner, memory.id, source_id=source.id))

    savepoint = connection.begin_nested()
    with pytest.raises(DBAPIError, match="append-only"):
        connection.execute(
            # table comes from the fixed parametrize list above, never from input
            text(f"UPDATE memory.{table} SET recorded_at = now() WHERE memory_id = :id"),  # noqa: S608
            {"id": memory.id},
        )
    savepoint.rollback()
