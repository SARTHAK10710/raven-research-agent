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
from memory_engine.domain.vocabulary import (
    EmbeddingStatus,
    EpisodeStatus,
    MemoryCategory,
    MentionResolutionStatus,
    ProfileStatus,
)
from memory_engine.personal.domain import (
    AtomicMemory,
    AtomicMemoryRevision,
    CategoryAssignment,
    DocumentEvidenceRef,
    Entity,
    EntityAlias,
    EntityMention,
    EntityRelationship,
    EntityResolutionRecord,
    Episode,
    EpisodeEvent,
    EpisodeMembership,
    MemoryCandidate,
    MemoryEmbedding,
    MemoryEntityAssociation,
    MemoryRelationship,
    MemorySource,
    Profile,
    ProfileRefresh,
    ProfileRevision,
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


class EpisodeRepository(Protocol):
    def add(self, scope: OwnerScope, episode: Episode) -> None: ...

    def get(self, scope: OwnerScope, episode_id: uuid.UUID) -> Episode | None:
        """Any status except ``deleted``."""
        ...

    def update(
        self, scope: OwnerScope, episode: Episode, *, expected_status: EpisodeStatus
    ) -> None:
        """Replace title, summary, boundaries and status; conditional on the current status."""
        ...

    def add_member(self, scope: OwnerScope, membership: EpisodeMembership) -> None: ...

    def remove_member(
        self, scope: OwnerScope, membership_id: uuid.UUID, *, removed_at: datetime
    ) -> None:
        """Close a current membership; it stays as history."""
        ...

    def members(
        self, scope: OwnerScope, episode_id: uuid.UUID, *, include_removed: bool = False
    ) -> Sequence[EpisodeMembership]:
        """Ordered by sequence (unsequenced last), then when added."""
        ...

    def episodes_of_memory(self, scope: OwnerScope, memory_id: uuid.UUID) -> Sequence[Episode]: ...

    def add_event(self, scope: OwnerScope, event: EpisodeEvent) -> None: ...

    def correct_event(
        self, scope: OwnerScope, event_id: uuid.UUID, correction: EpisodeEvent
    ) -> None:
        """Close ``event_id`` and add ``correction``; the earlier understanding is kept."""
        ...

    def timeline(
        self, scope: OwnerScope, episode_id: uuid.UUID, *, include_history: bool = False
    ) -> Sequence[EpisodeEvent]: ...


class ProfileRepository(Protocol):
    def create(self, scope: OwnerScope, profile: Profile, revision: ProfileRevision) -> None:
        """Create a profile with its first revision and supporting memories."""
        ...

    def get(self, scope: OwnerScope, profile_id: uuid.UUID) -> Profile | None: ...

    def revision(
        self, scope: OwnerScope, profile_id: uuid.UUID, revision_number: int | None = None
    ) -> ProfileRevision | None:
        """A revision with its supports; the current one when ``revision_number`` is None."""
        ...

    def apply_refresh(
        self,
        scope: OwnerScope,
        refresh: ProfileRefresh,
        *,
        expected_status: ProfileStatus,
        new_revision: ProfileRevision | None = None,
    ) -> Profile:
        """Record one refresh: append the new revision (if the outcome creates one),
        move the profile to the status the outcome implies, and keep the history record.

        Conditional on the profile still being at ``refresh.from_revision`` in
        ``expected_status``.
        """
        ...

    def history(self, scope: OwnerScope, profile_id: uuid.UUID) -> Sequence[ProfileRefresh]: ...

    def profiles_supported_by(self, scope: OwnerScope, memory_id: uuid.UUID) -> Sequence[uuid.UUID]:
        """Profiles whose *current* revision uses this memory (for refresh and deletion)."""
        ...


class CategoryRepository(Protocol):
    def assign(self, scope: OwnerScope, assignment: CategoryAssignment) -> None: ...

    def close(
        self, scope: OwnerScope, assignment_id: uuid.UUID, *, superseded_at: datetime
    ) -> None: ...

    def current(self, scope: OwnerScope, memory_id: uuid.UUID) -> Sequence[CategoryAssignment]: ...

    def history(self, scope: OwnerScope, memory_id: uuid.UUID) -> Sequence[CategoryAssignment]: ...

    def memories_in(self, scope: OwnerScope, category: MemoryCategory) -> Sequence[uuid.UUID]:
        """Memories currently assigned to ``category`` (retrievable memories only)."""
        ...


class MemoryEmbeddingRepository(Protocol):
    def add(self, scope: OwnerScope, embedding: MemoryEmbedding) -> None: ...

    def set_status(
        self,
        scope: OwnerScope,
        embedding_id: uuid.UUID,
        status: EmbeddingStatus,
        *,
        expected: EmbeddingStatus,
    ) -> None: ...

    def for_memory(self, scope: OwnerScope, memory_id: uuid.UUID) -> Sequence[MemoryEmbedding]: ...


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

    @property
    def episodes(self) -> EpisodeRepository: ...

    @property
    def profiles(self) -> ProfileRepository: ...

    @property
    def categories(self) -> CategoryRepository: ...

    @property
    def memory_embeddings(self) -> MemoryEmbeddingRepository: ...


class PersonalUnitOfWorkFactory(Protocol):
    def __call__(self) -> AbstractContextManager[PersonalUnitOfWork]: ...
