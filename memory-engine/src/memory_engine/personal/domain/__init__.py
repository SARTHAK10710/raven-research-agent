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
from memory_engine.personal.domain.records import (
    AtomicMemory,
    AtomicMemoryRevision,
    DocumentEvidenceRef,
    MemoryCandidate,
    MemorySource,
    ProvenanceRecord,
)

__all__ = [
    "AtomicMemory",
    "AtomicMemoryRevision",
    "CategoryAssignment",
    "DocumentEvidenceRef",
    "Entity",
    "EntityAlias",
    "EntityMention",
    "EntityRelationship",
    "EntityResolutionRecord",
    "Episode",
    "EpisodeEvent",
    "EpisodeMembership",
    "MemoryCandidate",
    "MemoryEmbedding",
    "MemoryEntityAssociation",
    "MemoryRelationship",
    "MemorySource",
    "Profile",
    "ProfileRefresh",
    "ProfileRevision",
    "ProfileSupport",
    "ProvenanceRecord",
    "ordered_pair",
]
