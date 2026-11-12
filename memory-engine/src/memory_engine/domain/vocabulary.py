"""Controlled vocabularies for Personal Memory records.

Values are lowercase ``snake_case`` strings and are enforced again by database
check constraints. Sources:

* Phase 5.4 "Phase 8.2 Amendment" (memory relationships, Memory-Entity roles,
  revision change types, Atomic Memory lifecycle, provenance roles,
  resolution outcomes).
* Phase 6.2 section 8.6 (candidate states) and 6.2.5 (origin classification).
* Decision 5.4.18 rule 4 (provenance origin kinds).
* Phase 5.4 "Memory Source processing states" amendment (approved 2026-11-11).
* Phase 5.4 Phase 8.2 amendment sections 12-14 (entities; derived knowledge;
  processing events, evaluation, correction and deletion records).

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
    # Held for controlled later processing, with a reason code (6.2.2 DEFER;
    # G6 English first). 5.4 Phase 8.4 amendment, approved 2026-11-12.
    DEFERRED = "deferred"

    @property
    def needs_reason(self) -> bool:
        """Transitions into these states record why (5.4 Phase 8.4 amendment)."""
        return self in (SourceProcessingStatus.DEFERRED, SourceProcessingStatus.REJECTED)


class InstructionType(StrEnum):
    """Explicit memory instruction carried by an input (6.2.1 step 8; plan 8.3 section 5.4)."""

    NORMAL = "normal"
    REMEMBER = "remember"
    FORGET = "forget"


class IngestionPriority(StrEnum):
    """Initial scheduling priority of an input (6.2.1 step 9).

    A scheduling signal only, never the memory's importance score.
    """

    NORMAL = "normal"
    HIGH = "high"


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


class EntityScope(StrEnum):
    """Entity scope (Decision 5.4.13).

    Only ``private`` is permitted today (Decision 11, approved 2026-11-11):
    shared entities are the only data visible across users, so they stay
    disabled, by a database check, until a curation process is approved.
    """

    PRIVATE = "private"
    SHARED = "shared"


class EntityType(StrEnum):
    """Entity and mention types (6.3.4 section 6.1, plus ``unknown``).

    ``other``: identifiable but none of the listed types. ``unknown``: the type
    could not be determined; uncertainty is kept rather than forced (plan 8.5).
    """

    PERSON = "person"
    ORGANIZATION = "organization"
    PROJECT = "project"
    PRODUCT = "product"
    PLACE = "place"
    INSTITUTION = "institution"
    TECHNOLOGY = "technology"
    EVENT = "event"
    OTHER = "other"
    UNKNOWN = "unknown"


class EntityStatus(StrEnum):
    """Lifecycle of a canonical entity. A merged entity points at its survivor."""

    ACTIVE = "active"
    MERGED = "merged"
    DELETION_PENDING = "deletion_pending"
    DELETED = "deleted"


class MentionResolutionStatus(StrEnum):
    """Current resolution state of an Entity Mention (Decisions 5.4.33-5.4.34)."""

    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    NEEDS_REVIEW = "needs_review"


class EntityResolutionOutcome(StrEnum):
    """Outcome of one recorded entity-resolution decision (Decision 5.4.34; 6.3.4)."""

    MATCHED_EXISTING = "matched_existing"
    CREATED_NEW = "created_new"
    LEFT_UNRESOLVED = "left_unresolved"
    SENT_TO_REVIEW = "sent_to_review"
    CORRECTED = "corrected"
    REASSIGNED = "reassigned"
    MERGED = "merged"

    @property
    def assigns_entity(self) -> bool:
        """Outcomes that leave a mention (or a merge) pointing at an entity."""
        return self in (
            EntityResolutionOutcome.MATCHED_EXISTING,
            EntityResolutionOutcome.CREATED_NEW,
            EntityResolutionOutcome.CORRECTED,
            EntityResolutionOutcome.REASSIGNED,
            EntityResolutionOutcome.MERGED,
        )


class EntityRelationshipType(StrEnum):
    """Entity to Entity relationships (Phase 8.2 amendment section 3)."""

    WORKS_AT = "works_at"
    MEMBER_OF = "member_of"
    REPORTS_TO = "reports_to"
    KNOWS = "knows"
    PART_OF = "part_of"
    LOCATED_IN = "located_in"
    USES = "uses"
    ACQUIRED_BY = "acquired_by"
    MERGED_INTO = "merged_into"
    RENAMED_TO = "renamed_to"
    RELATED_TO = "related_to"

    @property
    def symmetric(self) -> bool:
        return self in (EntityRelationshipType.KNOWS, EntityRelationshipType.RELATED_TO)


class MemoryEntityRole(StrEnum):
    """Role of an entity in an Atomic Memory (Phase 8.2 amendment section 5)."""

    SUBJECT = "subject"
    OBJECT = "object"
    MENTIONED = "mentioned"
    CONTEXT = "context"


class EmbeddingStatus(StrEnum):
    """Embedding metadata lifecycle (Decision 5.4.20).

    Shared by memory embeddings and document embeddings; the two stay in
    separate tables with separate ownership and retrieval rules.
    """

    PENDING = "pending"
    GENERATING = "generating"
    GENERATED = "generated"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"
    SUPERSEDED = "superseded"
    DELETION_PENDING = "deletion_pending"


class EmbeddingPurpose(StrEnum):
    """Why a memory embedding exists (Decision 5.4.21)."""

    PRIMARY = "primary"
    ASPECT = "aspect"


class MemoryCategory(StrEnum):
    """Memory category taxonomy (Decision 5.4.9; 6.2 section 8.4)."""

    PERSONAL_PREFERENCE = "personal_preference"
    GOAL = "goal"
    DECISION = "decision"
    IMPORTANT_EVENT = "important_event"
    RELATIONSHIP = "relationship"
    KNOWLEDGE = "knowledge"
    PROJECT = "project"
    COMMITMENT = "commitment"


class EpisodeStatus(StrEnum):
    """Lifecycle of an Episode, a derived grouping of memories (Decision 5.4.16)."""

    ACTIVE = "active"
    NEEDS_REFRESH = "needs_refresh"
    NEEDS_REVIEW = "needs_review"
    DELETION_PENDING = "deletion_pending"
    DELETED = "deleted"


class TemporalPrecision(StrEnum):
    """How precisely a time is known (Decision 5.4.30: never fabricate dates)."""

    EXACT = "exact"
    DAY = "day"
    MONTH = "month"
    YEAR = "year"
    APPROXIMATE = "approximate"
    UNKNOWN = "unknown"


class ProfileType(StrEnum):
    """Derived profile kinds (6.5.6 profile categories)."""

    USER = "user"
    PREFERENCE = "preference"
    PROJECT = "project"
    SKILL_KNOWLEDGE = "skill_knowledge"
    RELATIONSHIP_CONTEXT = "relationship_context"
    WORK_CONTEXT = "work_context"


class ProfileStatus(StrEnum):
    """Current freshness and refresh state of a Derived Profile (Decision 5.4.32)."""

    CURRENT = "current"
    STALE = "stale"
    REFRESHING = "refreshing"
    REFRESH_FAILED = "refresh_failed"
    NEEDS_REVIEW = "needs_review"
    DELETION_PENDING = "deletion_pending"
    DELETED = "deleted"


class RefreshTrigger(StrEnum):
    """What started a profile refresh (6.5.1 trigger categories)."""

    EVENT = "event"
    SCHEDULED = "scheduled"
    ON_DEMAND = "on_demand"


class RefreshOutcome(StrEnum):
    """Result of one recorded profile refresh (Decision 5.4.32; 6.5.6)."""

    REFRESHED = "refreshed"
    NO_CHANGE = "no_change"
    PARTIALLY_REFRESHED = "partially_refreshed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"

    @property
    def creates_revision(self) -> bool:
        return self in (RefreshOutcome.REFRESHED, RefreshOutcome.PARTIALLY_REFRESHED)

    def resulting_status(self) -> ProfileStatus:
        """The profile status this outcome leaves behind.

        A partial or failed refresh never marks a profile current (6.5.6 safeguard).
        """
        return {
            RefreshOutcome.REFRESHED: ProfileStatus.CURRENT,
            RefreshOutcome.NO_CHANGE: ProfileStatus.CURRENT,
            RefreshOutcome.PARTIALLY_REFRESHED: ProfileStatus.STALE,
            RefreshOutcome.FAILED: ProfileStatus.REFRESH_FAILED,
            RefreshOutcome.NEEDS_REVIEW: ProfileStatus.NEEDS_REVIEW,
        }[self]


class ProcessingEventType(StrEnum):
    """Meaningful Memory Source processing events (Decision 5.4.28; amendment section 14)."""

    TRANSITION = "transition"
    FAILURE = "failure"
    RETRY = "retry"
    RECOVERY = "recovery"


class EvaluationOutcome(StrEnum):
    """Candidate evaluation decisions (6.2.3 section 6.7); not memory lifecycle states."""

    PROCEED = "proceed"
    NEEDS_REVIEW = "needs_review"
    REJECT = "reject"
    DEFER = "defer"

    def allowed_statuses(self) -> frozenset[CandidateStatus]:
        """Candidate statuses an evaluation with this outcome may leave behind."""
        return {
            EvaluationOutcome.PROCEED: frozenset(
                {CandidateStatus.CANDIDATE, CandidateStatus.VALIDATED}
            ),
            EvaluationOutcome.NEEDS_REVIEW: frozenset({CandidateStatus.NEEDS_REVIEW}),
            EvaluationOutcome.REJECT: frozenset({CandidateStatus.REJECTED}),
            EvaluationOutcome.DEFER: frozenset({CandidateStatus.CANDIDATE}),
        }[self]


class CorrectionStatus(StrEnum):
    """Memory Correction Request states (Decision 5.4.26; amendment section 14)."""

    OPEN = "open"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    DELETED = "deleted"

    @property
    def resolved(self) -> bool:
        return self in (
            CorrectionStatus.ACCEPTED,
            CorrectionStatus.REJECTED,
            CorrectionStatus.WITHDRAWN,
        )


class DeletionRequestKind(StrEnum):
    """Who asked for a coordinated deletion (6.5.8 B and C).

    Policy-driven forgetting (6.5.8 A) is a lifecycle decision and creates no
    deletion operation.
    """

    USER_REQUEST = "user_request"
    ACCOUNT = "account"
    ADMINISTRATIVE = "administrative"
    SYSTEM = "system"


class DeletionOperationStatus(StrEnum):
    """Memory Deletion Operation states (6.5.8)."""

    REQUESTED = "requested"
    VALIDATING = "validating"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    PROPAGATING = "propagating"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    REQUIRES_RECONCILIATION = "requires_reconciliation"

    @property
    def finished(self) -> bool:
        """No further propagation is planned. ``requires_reconciliation`` is resumable."""
        return self in (
            DeletionOperationStatus.COMPLETED,
            DeletionOperationStatus.PARTIALLY_COMPLETED,
            DeletionOperationStatus.FAILED,
        )


class DeletionTargetKind(StrEnum):
    """Personal Memory record kinds a deletion ledger row can name.

    One value per ``pm_`` table (without the prefix), except the deletion
    tables themselves; a unit test keeps the two in step.
    """

    MEMORY_SOURCE = "memory_source"
    SOURCE_PROCESSING_EVENT = "source_processing_event"
    MEMORY_CANDIDATE = "memory_candidate"
    CANDIDATE_EVALUATION = "candidate_evaluation"
    ATOMIC_MEMORY = "atomic_memory"
    ATOMIC_MEMORY_REVISION = "atomic_memory_revision"
    PROVENANCE = "provenance"
    DOCUMENT_EVIDENCE_REF = "document_evidence_ref"
    ENTITY = "entity"
    ENTITY_ALIAS = "entity_alias"
    ENTITY_MENTION = "entity_mention"
    ENTITY_RESOLUTION = "entity_resolution"
    ENTITY_RELATIONSHIP = "entity_relationship"
    MEMORY_RELATIONSHIP = "memory_relationship"
    MEMORY_ENTITY = "memory_entity"
    EPISODE = "episode"
    EPISODE_MEMBERSHIP = "episode_membership"
    EPISODE_EVENT = "episode_event"
    PROFILE = "profile"
    PROFILE_REVISION = "profile_revision"
    PROFILE_MEMORY = "profile_memory"
    PROFILE_REFRESH = "profile_refresh"
    MEMORY_CATEGORY = "memory_category"
    MEMORY_EMBEDDING = "memory_embedding"
    CORRECTION_REQUEST = "correction_request"
    CORRECTION_MEMORY = "correction_memory"
    # 8.4 step 2 (5.4 Phase 8.4 amendment section 17).
    RELEVANCE_ASSESSMENT = "relevance_assessment"


class RelevanceOutcome(StrEnum):
    """Relevance gate outcome (6.2.2 section 4.6); 5.4 Phase 8.4 amendment section 17."""

    PROCESS = "process"
    DEFER = "defer"
    REJECT = "reject"


class FactModality(StrEnum):
    """Modality of a fact proposal (6.2.3 section 5.6); 5.4 Phase 8.4 amendment section 18."""

    FACTUAL = "factual"
    INTENDED = "intended"
    POSSIBLE = "possible"
    CONDITIONAL = "conditional"


class ProposalStatus(StrEnum):
    """Fact proposal outcome (6.2.3 section 5.10); 5.4 Phase 8.4 amendment section 18."""

    EXTRACTED = "extracted"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


class DeletionAction(StrEnum):
    """Required handling of one ledger row (6.5.9 dependency inventory)."""

    DELETE = "delete"
    INVALIDATE = "invalidate"
    REFRESH = "refresh"


class DeletionTargetState(StrEnum):
    """Propagation progress of one ledger row (6.5.9)."""

    PENDING = "pending"
    PROPAGATED = "propagated"
    VERIFIED = "verified"
    FAILED = "failed"

    def can_move_to(self, state: "DeletionTargetState") -> bool:
        """Propagate, then verify; a failure can be retried, a verified row is final."""
        return (
            state
            in {
                DeletionTargetState.PENDING: (
                    DeletionTargetState.PROPAGATED,
                    DeletionTargetState.FAILED,
                ),
                DeletionTargetState.PROPAGATED: (
                    DeletionTargetState.VERIFIED,
                    DeletionTargetState.FAILED,
                ),
                DeletionTargetState.FAILED: (DeletionTargetState.PENDING,),
                DeletionTargetState.VERIFIED: (),
            }[self]
        )


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
