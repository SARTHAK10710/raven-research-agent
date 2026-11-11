"""Controlled vocabularies for Personal Memory records.

Values are lowercase ``snake_case`` strings and are enforced again by database
check constraints. Sources:

* Phase 5.4 "Phase 8.2 Amendment" (memory relationships, Memory-Entity roles,
  revision change types, Atomic Memory lifecycle, provenance roles,
  resolution outcomes).
* Phase 6.2 section 8.6 (candidate states) and 6.2.5 (origin classification).
* Decision 5.4.18 rule 4 (provenance origin kinds).
* Phase 5.4 "Memory Source processing states" amendment (approved 2026-11-11).

Do not add values here without an approved specification change.
"""

from enum import StrEnum


class SourceType(StrEnum):
    """Kinds of input a Memory Source can hold (6.2.1 section 3)."""

    TEXT = "text"
    CONVERSATION = "conversation"
    DOCUMENT = "document"


class SourceProcessingStatus(StrEnum):
    """Current processing state of a stored Memory Source (Decision 5.4.28)."""

    VALIDATED = "validated"
    QUEUED = "queued"
    PROCESSING = "processing"
    EXTRACTED = "extracted"
    PARTIALLY_EXTRACTED = "partially_extracted"
    REJECTED = "rejected"
    PARSING_FAILED = "parsing_failed"
    PROCESSING_FAILED = "processing_failed"


class CandidateStatus(StrEnum):
    """Memory Candidate lifecycle states (6.2 section 8.6)."""

    CANDIDATE = "candidate"
    VALIDATED = "validated"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class CandidateOrigin(StrEnum):
    """Origin classification of a candidate (6.2.5); unresolved needs review."""

    EXPLICIT = "explicit"
    INFERRED = "inferred"
    UNRESOLVED = "unresolved"


class MemoryOrigin(StrEnum):
    """Origin of an accepted Atomic Memory (Decision 5.4.10)."""

    EXPLICIT = "explicit"
    INFERRED = "inferred"


class MemoryLifecycleStatus(StrEnum):
    """Atomic Memory lifecycle (Phase 8.2 amendment section 7)."""

    ACTIVE = "active"
    HISTORICAL = "historical"
    NEEDS_REVIEW = "needs_review"
    RETRACTED = "retracted"
    DELETION_PENDING = "deletion_pending"
    DELETED = "deleted"

    @property
    def retrievable_by_default(self) -> bool:
        """Only active memories are returned by default retrieval."""
        return self is MemoryLifecycleStatus.ACTIVE

    @property
    def never_retrievable(self) -> bool:
        """Tombstoned memories are never returned, by any query."""
        return self in (MemoryLifecycleStatus.DELETION_PENDING, MemoryLifecycleStatus.DELETED)


class RevisionChangeType(StrEnum):
    """Why an immutable Atomic Memory revision was created (amendment section 6)."""

    CREATED = "created"
    UPDATED = "updated"
    CORRECTED = "corrected"
    EVIDENCE_ADDED = "evidence_added"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"
    RETRACTED = "retracted"
    RECLASSIFIED = "reclassified"


class ProvenanceRole(StrEnum):
    """Role a piece of evidence plays for a memory (amendment section 9)."""

    ORIGIN = "origin"
    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    CORRECTING = "correcting"


class ProvenanceOriginKind(StrEnum):
    """Explicit, inferred or system-generated information (Decision 5.4.18 rule 4)."""

    EXPLICIT = "explicit"
    INFERRED = "inferred"
    SYSTEM_GENERATED = "system_generated"


class DocumentEvidenceStatus(StrEnum):
    """State of a Personal Memory reference to document evidence (7.1 section 23.3).

    ``source_deleted``: the document was deleted; the reference keeps only the
    opaque identifiers so provenance stays traceable without blocking deletion.
    """

    ACTIVE = "active"
    SOURCE_DELETED = "source_deleted"


class MemoryRelationshipType(StrEnum):
    """Atomic Memory to Atomic Memory relationships (amendment section 4)."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    SUPERSEDES = "supersedes"
    UPDATES = "updates"
    PART_OF = "part_of"
    DERIVED_FROM = "derived_from"
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"

    @property
    def symmetric(self) -> bool:
        return self in (MemoryRelationshipType.CONTRADICTS, MemoryRelationshipType.RELATED_TO)


class SupersessionReason(StrEnum):
    """Reason recorded on a ``supersedes`` relationship (amendment section 4)."""

    TEMPORAL_CHANGE = "temporal_change"
    REPLACEMENT = "replacement"
    CORRECTION = "correction"


class ResolutionOutcome(StrEnum):
    """Processing decisions of Phase 6.3; recorded in audit, not stored as links."""

    CREATE_NEW = "create_new"
    MERGE = "merge"
    UPDATE_EXISTING = "update_existing"
    LINK_EXISTING = "link_existing"
    SUPERSEDE = "supersede"
    NEEDS_REVIEW = "needs_review"
    REJECT = "reject"
    NO_CHANGE = "no_change"
