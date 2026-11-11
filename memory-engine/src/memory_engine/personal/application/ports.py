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
from datetime import datetime
from typing import Protocol

from memory_engine.domain.identifiers import OwnerScope
from memory_engine.domain.vocabulary import MentionResolutionStatus
from memory_engine.personal.domain import (
    AtomicMemory,
    AtomicMemoryRevision,
    DocumentEvidenceRef,
    Entity,
    EntityAlias,
    EntityMention,
    EntityRelationship,
    EntityResolutionRecord,
    MemoryCandidate,
    MemoryEntityAssociation,
    MemoryRelationship,
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


class DocumentEvidenceRepository(Protocol):
    def add(self, scope: OwnerScope, evidence: DocumentEvidenceRef) -> None:
        """Attach document evidence to a candidate.

        Raises RecordNotFoundError if the candidate, document, version or chunk is
        not in scope, or if the version or chunk does not belong to the document.
        """
        ...

    def list_for_candidate(
        self, scope: OwnerScope, candidate_id: uuid.UUID
    ) -> Sequence[DocumentEvidenceRef]: ...

    def dependent_memory_ids(
        self, scope: OwnerScope, document_id: uuid.UUID
    ) -> Sequence[uuid.UUID]:
        """Memories whose provenance cites this document (deletion discovery, 5.10 5.2)."""
        ...

    def mark_source_deleted(self, scope: OwnerScope, document_id: uuid.UUID) -> int:
        """Detach all references to a document being deleted; return how many changed.

        Memories are never deleted here; the deletion workflow (8.10) decides.
        """
        ...


class EntityRepository(Protocol):
    def add(self, scope: OwnerScope, entity: Entity) -> None: ...

    def get(self, scope: OwnerScope, entity_id: uuid.UUID) -> Entity | None:
        """Any status except ``deleted``."""
        ...

    def canonical(self, scope: OwnerScope, entity_id: uuid.UUID) -> Entity | None:
        """Follow merges to the surviving entity."""
        ...

    def add_alias(self, scope: OwnerScope, alias: EntityAlias) -> None: ...

    def list_aliases(self, scope: OwnerScope, entity_id: uuid.UUID) -> Sequence[EntityAlias]: ...

    def find_by_alias(self, scope: OwnerScope, text: str) -> Sequence[Entity]:
        """Active entities whose name or alias normalizes to ``text``.

        These are candidates only: alias matching never proves identity (5.4.14).
        """
        ...

    def merge(self, scope: OwnerScope, record: EntityResolutionRecord) -> None:
        """Merge ``record.previous_entity_id`` into ``record.entity_id`` and keep the record."""
        ...


class EntityMentionRepository(Protocol):
    def add(self, scope: OwnerScope, mention: EntityMention) -> None: ...

    def get(self, scope: OwnerScope, mention_id: uuid.UUID) -> EntityMention | None: ...

    def list_for_entity(
        self, scope: OwnerScope, entity_id: uuid.UUID
    ) -> Sequence[EntityMention]: ...

    def apply_resolution(
        self,
        scope: OwnerScope,
        record: EntityResolutionRecord,
        *,
        expected_status: MentionResolutionStatus,
    ) -> EntityMention:
        """Move a mention to the state ``record`` implies and append ``record``.

        Conditional on the mention still being in ``expected_status``.
        """
        ...

    def history(
        self,
        scope: OwnerScope,
        *,
        mention_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> Sequence[EntityResolutionRecord]: ...


class RelationshipRepository(Protocol):
    def add_entity_relationship(
        self, scope: OwnerScope, relationship: EntityRelationship
    ) -> None: ...

    def close_entity_relationship(
        self,
        scope: OwnerScope,
        relationship_id: uuid.UUID,
        *,
        valid_to: datetime | None,
        superseded_at: datetime,
    ) -> None:
        """End a current relationship; it is kept as history, never overwritten."""
        ...

    def entity_relationships(
        self, scope: OwnerScope, entity_id: uuid.UUID, *, include_history: bool = False
    ) -> Sequence[EntityRelationship]: ...

    def add_memory_relationship(
        self, scope: OwnerScope, relationship: MemoryRelationship
    ) -> None: ...

    def close_memory_relationship(
        self,
        scope: OwnerScope,
        relationship_id: uuid.UUID,
        *,
        valid_to: datetime | None,
        superseded_at: datetime,
    ) -> None: ...

    def memory_relationships(
        self, scope: OwnerScope, memory_id: uuid.UUID, *, include_history: bool = False
    ) -> Sequence[MemoryRelationship]: ...

    def associate(self, scope: OwnerScope, association: MemoryEntityAssociation) -> None: ...

    def entities_of_memory(
        self, scope: OwnerScope, memory_id: uuid.UUID
    ) -> Sequence[MemoryEntityAssociation]: ...

    def memories_of_entity(
        self, scope: OwnerScope, entity_id: uuid.UUID
    ) -> Sequence[MemoryEntityAssociation]: ...


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

    @property
    def evidence(self) -> DocumentEvidenceRepository: ...

    @property
    def entities(self) -> EntityRepository: ...

    @property
    def mentions(self) -> EntityMentionRepository: ...

    @property
    def relationships(self) -> RelationshipRepository: ...


class PersonalUnitOfWorkFactory(Protocol):
    def __call__(self) -> AbstractContextManager[PersonalUnitOfWork]: ...
