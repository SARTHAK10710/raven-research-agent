"""Persistence ports for Document Intelligence.

Same ownership contract as Personal Memory: every method takes an
:class:`OwnerScope`, and another owner's record behaves exactly like a missing
one. Status changes take the status the caller expects to replace; a mismatch
raises ConcurrencyConflictError and writes nothing.

Derived content (representations, chunks, embeddings) can only be written while
the document is ``registered`` or ``available`` and its version is not being
deleted; otherwise DeletionInProgressError is raised, so a stale worker never
recreates content for a deleted document (memory/05 sections 18-19).
"""

import uuid
from collections.abc import Sequence
from contextlib import AbstractContextManager
from typing import Protocol

from memory_engine.documents.domain import (
    Document,
    DocumentChunk,
    DocumentDependencies,
    DocumentEmbedding,
    DocumentVersion,
    ExtractedRepresentation,
    ProcessingOperation,
)
from memory_engine.documents.domain.vocabulary import (
    DocumentLifecycleStatus,
    EmbeddingStatus,
    OperationStatus,
    VersionProcessingStatus,
)
from memory_engine.domain.handoff import OutboxWriter
from memory_engine.domain.identifiers import OwnerScope


class DocumentRepository(Protocol):
    def register(self, scope: OwnerScope, document: Document, version: DocumentVersion) -> None:
        """Create a document with its first version, which becomes current."""
        ...

    def add_version(
        self,
        scope: OwnerScope,
        version: DocumentVersion,
        *,
        expected_current_version_id: uuid.UUID,
    ) -> None:
        """Append a new version and make it current; history is never overwritten."""
        ...

    def get(self, scope: OwnerScope, document_id: uuid.UUID) -> Document | None:
        """Any lifecycle state except ``deleted``."""
        ...

    def get_version(self, scope: OwnerScope, version_id: uuid.UUID) -> DocumentVersion | None: ...

    def list_versions(
        self, scope: OwnerScope, document_id: uuid.UUID
    ) -> Sequence[DocumentVersion]: ...

    def set_lifecycle_status(
        self,
        scope: OwnerScope,
        document_id: uuid.UUID,
        status: DocumentLifecycleStatus,
        *,
        expected: DocumentLifecycleStatus,
    ) -> None: ...

    def set_version_status(
        self,
        scope: OwnerScope,
        version_id: uuid.UUID,
        status: VersionProcessingStatus,
        *,
        expected: VersionProcessingStatus,
    ) -> None: ...

    def dependencies(self, scope: OwnerScope, document_id: uuid.UUID) -> DocumentDependencies:
        """Everything deletion must cover on the document side (5.4 amendment section 9)."""
        ...


class DocumentContentRepository(Protocol):
    def add_representation(
        self, scope: OwnerScope, representation: ExtractedRepresentation
    ) -> None: ...

    def add_chunks(self, scope: OwnerScope, chunks: Sequence[DocumentChunk]) -> None:
        """Add chunks, with their locations, from one representation of one version."""
        ...

    def list_chunks(self, scope: OwnerScope, version_id: uuid.UUID) -> Sequence[DocumentChunk]:
        """Chunks of one version in sequence order, with their locations."""
        ...

    def add_embedding(self, scope: OwnerScope, embedding: DocumentEmbedding) -> None: ...

    def set_embedding_status(
        self,
        scope: OwnerScope,
        embedding_id: uuid.UUID,
        status: EmbeddingStatus,
        *,
        expected: EmbeddingStatus,
    ) -> None: ...


class ProcessingOperationRepository(Protocol):
    def start(
        self, scope: OwnerScope, operation: ProcessingOperation
    ) -> tuple[ProcessingOperation, bool]:
        """Record an operation once per idempotency key.

        Returns the stored operation and whether it was created now. A repeated
        request with the same key returns the existing operation unchanged.
        """
        ...

    def get(self, scope: OwnerScope, operation_id: uuid.UUID) -> ProcessingOperation | None: ...

    def find_by_idempotency_key(self, scope: OwnerScope, key: str) -> ProcessingOperation | None:
        """The operation an earlier request with this key recorded, if any."""
        ...

    def transition(
        self,
        scope: OwnerScope,
        operation_id: uuid.UUID,
        status: OperationStatus,
        *,
        expected: OperationStatus,
        error_code: str | None = None,
        count_attempt: bool = False,
    ) -> ProcessingOperation: ...


class DocumentUnitOfWork(Protocol):
    """One short transaction over Document Intelligence records."""

    @property
    def documents(self) -> DocumentRepository: ...

    @property
    def contents(self) -> DocumentContentRepository: ...

    @property
    def operations(self) -> ProcessingOperationRepository: ...

    @property
    def outbox(self) -> OutboxWriter: ...


class DocumentUnitOfWorkFactory(Protocol):
    def __call__(self) -> AbstractContextManager[DocumentUnitOfWork]: ...
