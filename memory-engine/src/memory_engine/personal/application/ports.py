"""Persistence ports for Personal Memory.

Every method takes an :class:`OwnerScope` and only ever reads or writes records
of that owner. A record that belongs to another owner behaves exactly as if it
did not exist (``None`` or :class:`RecordNotFoundError`), so a port never
reveals whether another user's private record exists (Decision 5.8.6).

Writes become durable only when the enclosing unit of work commits.
"""

import uuid
from collections.abc import Sequence
from contextlib import AbstractContextManager
from typing import Protocol

from memory_engine.domain.identifiers import OwnerScope
from memory_engine.personal.domain import (
    AtomicMemory,
    AtomicMemoryRevision,
    MemoryCandidate,
    MemorySource,
    ProvenanceRecord,
)


class MemorySourceRepository(Protocol):
    def add(self, scope: OwnerScope, source: MemorySource) -> None: ...

    def get(self, scope: OwnerScope, source_id: uuid.UUID) -> MemorySource | None: ...


class MemoryCandidateRepository(Protocol):
    def add(self, scope: OwnerScope, candidate: MemoryCandidate) -> None:
        """Add a candidate. Raises RecordNotFoundError if its source is not in scope."""
        ...

    def get(self, scope: OwnerScope, candidate_id: uuid.UUID) -> MemoryCandidate | None: ...

    def list_for_source(
        self, scope: OwnerScope, source_id: uuid.UUID
    ) -> Sequence[MemoryCandidate]: ...


class AtomicMemoryRepository(Protocol):
    def add(self, scope: OwnerScope, memory: AtomicMemory, revision: AtomicMemoryRevision) -> None:
        """Create a memory together with its first ('created') revision."""
        ...

    def get(self, scope: OwnerScope, memory_id: uuid.UUID) -> AtomicMemory | None:
        """Return the current state, in any lifecycle status except tombstoned ones."""
        ...

    def apply_revision(
        self,
        scope: OwnerScope,
        memory: AtomicMemory,
        revision: AtomicMemoryRevision,
        *,
        expected_revision_number: int,
    ) -> None:
        """Replace the current state with ``memory`` and append ``revision``.

        Optimistic concurrency: succeeds only if the stored current state is
        still at ``expected_revision_number``; otherwise raises
        ConcurrencyConflictError and writes nothing.
        """
        ...

    def list_revisions(
        self, scope: OwnerScope, memory_id: uuid.UUID
    ) -> Sequence[AtomicMemoryRevision]: ...

    def list_retrievable(self, scope: OwnerScope) -> Sequence[AtomicMemory]:
        """Memories returned by default retrieval: lifecycle status ``active`` only."""
        ...


class ProvenanceRepository(Protocol):
    def add(self, scope: OwnerScope, record: ProvenanceRecord) -> None:
        """Append evidence. Raises RecordNotFoundError if a referenced record is out of scope."""
        ...

    def list_for_memory(
        self, scope: OwnerScope, memory_id: uuid.UUID
    ) -> Sequence[ProvenanceRecord]: ...


class PersonalUnitOfWork(Protocol):
    """One short transaction over Personal Memory records.

    Used as a context manager: it commits when the block finishes normally and
    rolls back if the block raises. Never hold one open across parsing,
    embedding or network calls (plan 8.2 section 8).
    """

    @property
    def sources(self) -> MemorySourceRepository: ...

    @property
    def candidates(self) -> MemoryCandidateRepository: ...

    @property
    def memories(self) -> AtomicMemoryRepository: ...

    @property
    def provenance(self) -> ProvenanceRepository: ...


class PersonalUnitOfWorkFactory(Protocol):
    def __call__(self) -> AbstractContextManager[PersonalUnitOfWork]: ...
