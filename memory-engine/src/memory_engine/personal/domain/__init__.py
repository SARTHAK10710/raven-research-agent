"""Personal Memory domain model: records and their invariants, no infrastructure."""

from memory_engine.personal.domain.derived import (
    CategoryAssignment,
    Episode,
    EpisodeEvent,
    EpisodeMembership,
    MemoryEmbedding,
    Profile,
    ProfileRefresh,
    ProfileRevision,
    ProfileSupport,
)
from memory_engine.personal.domain.entities import (
    Entity,
    EntityAlias,
    EntityMention,
    EntityRelationship,
    EntityResolutionRecord,
    MemoryEntityAssociation,
    MemoryRelationship,
    ordered_pair,
)
from memory_engine.personal.domain.evaluation import (
    EvaluatedProposal,
    OriginClassification,
    ProposalEvaluation,
)
from memory_engine.personal.domain.facts import FactProposal
from memory_engine.personal.domain.lifecycle import (
    CandidateEvaluation,
    CorrectionRequest,
    CorrectionTarget,
    DeletionOperation,
    DeletionTarget,
    SourceProcessingEvent,
)
from memory_engine.personal.domain.records import (
    AtomicMemory,
    AtomicMemoryRevision,
    DocumentEvidenceRef,
    MemoryCandidate,
    MemorySource,
    ProvenanceRecord,
)
from memory_engine.personal.domain.relevance import RelevanceAssessment, UnitAssessment

__all__ = [
    "AtomicMemory",
    "AtomicMemoryRevision",
    "CandidateEvaluation",
    "CategoryAssignment",
    "CorrectionRequest",
    "CorrectionTarget",
    "DeletionOperation",
    "DeletionTarget",
    "DocumentEvidenceRef",
    "Entity",
    "EntityAlias",
    "EntityMention",
    "EntityRelationship",
    "EntityResolutionRecord",
    "Episode",
    "EpisodeEvent",
    "EpisodeMembership",
    "EvaluatedProposal",
    "FactProposal",
    "MemoryCandidate",
    "MemoryEmbedding",
    "MemoryEntityAssociation",
    "MemoryRelationship",
    "MemorySource",
    "OriginClassification",
    "Profile",
    "ProfileRefresh",
    "ProfileRevision",
    "ProfileSupport",
    "ProposalEvaluation",
    "ProvenanceRecord",
    "RelevanceAssessment",
    "SourceProcessingEvent",
    "UnitAssessment",
    "ordered_pair",
]
