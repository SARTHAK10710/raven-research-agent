"""Document Intelligence domain model: records and invariants, no infrastructure."""

from memory_engine.documents.domain.records import (
    ChunkLocation,
    Document,
    DocumentChunk,
    DocumentDependencies,
    DocumentEmbedding,
    DocumentVersion,
    ExtractedRepresentation,
    ProcessingOperation,
)

__all__ = [
    "ChunkLocation",
    "Document",
    "DocumentChunk",
    "DocumentDependencies",
    "DocumentEmbedding",
    "DocumentVersion",
    "ExtractedRepresentation",
    "ProcessingOperation",
]
