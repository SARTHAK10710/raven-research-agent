# Amendment — Document Intelligence and RAG Storage

**File:** `docs/technology/02-database-and-storage-architecture.md`  
**Applies to:** Phase 7.2 — Database and Storage Architecture

## 1. Purpose

Extend Raven's existing database and storage architecture to support document intelligence and Retrieval-Augmented Generation (RAG).

The extension must support:

- Original document storage.
- Document version management.
- Extracted document content.
- Structure-aware document chunks.
- Chunk metadata and provenance.
- Document processing operations.
- Document embedding metadata.
- Document retrieval and citation references.
- Document lifecycle and deletion.

This amendment extends the existing PostgreSQL and S3-compatible object storage architecture. It does not introduce another primary database.

## 2. Storage Architecture

Raven will retain its existing hybrid storage architecture.

| Storage | Responsibility |
|---|---|
| PostgreSQL | Structured records, metadata, relationships, processing states and references |
| S3-compatible object storage | Original documents and large extracted artifacts |
| pgvector | Vector representations for semantic retrieval |
| PostgreSQL Full-Text Search | Keyword-based document retrieval |

PostgreSQL remains the authoritative source for document metadata, ownership, versions and processing state.

Object storage holds large binary content and artifacts. Database records maintain references to these objects.

## 3. Document Data Ownership

Document intelligence belongs to the Memory Engine but remains logically separate from personal memory.

The Memory Engine owns:

- Document registration.
- Document metadata.
- Document versions.
- Extracted representations.
- Document chunks.
- Chunk provenance.
- Document embedding metadata.
- Document processing operations.
- Document retrieval lifecycle.

The existing `memory` logical schema will initially contain the document intelligence records, subject to reconciliation with the approved Phase 5 data models.

No separate document database is required for the initial architecture.

## 4. Document Storage Strategy

### 4.1 Original Documents

Store original uploaded files in S3-compatible object storage.

PostgreSQL should retain:

- Document identifier.
- User identifier.
- Original filename.
- Detected file type.
- MIME type.
- File size.
- Object storage reference.
- Content checksum.
- Upload timestamp.
- Document lifecycle status.
- Retention metadata.

Original files must remain distinguishable from extracted and transformed content.

### 4.2 Document Versions

Each materially different document revision must have a separate version identity.

A document version should preserve:

- Version identifier.
- Parent document identifier.
- Version number or equivalent revision identity.
- Original object reference.
- Content checksum.
- Upload or ingestion timestamp.
- Processing status.
- Extraction metadata.

A new version must not silently overwrite the previous version.

Document retrieval must use version-consistent content, chunks and embeddings.

### 4.3 Extracted Representations

Extracted document content may be stored in object storage when its size or retention requirements justify it.

PostgreSQL should retain the representation metadata and object reference.

The system must preserve the relationship between:

Original Document → Document Version → Extracted Representation.

Extraction must not modify the original uploaded file.

### 4.4 Document Chunks

Document chunks are structured retrieval units derived from extracted representations.

Their metadata should support:

- Chunk identifier.
- Document identifier.
- Document version identifier.
- Extracted representation identifier.
- Chunk sequence.
- Section heading or hierarchy.
- Page or location information, where available.
- Character or token offsets, where available.
- Content checksum.
- Processing status.
- Chunking strategy and version.

Chunk content may be stored in PostgreSQL or object storage depending on measured size and access requirements.

The initial implementation should prefer the simplest approach that supports reliable retrieval, provenance and deletion.

## 5. Separation of Memory and Document Storage

Personal memories and document chunks must remain separate logical data domains.

| Personal Memory | Document Intelligence |
|---|---|
| Atomic facts | Document chunks |
| Memory candidates | Extracted representations |
| Memory revisions | Document versions |
| Memory relationships | Document structure and chunk relationships |
| Memory embeddings | Document chunk embeddings |
| Memory retrieval | Document retrieval |

Important rules:

1. A document chunk must never be treated as an atomic personal memory.
2. Document uploads must not automatically create personal memories.
3. Document-derived facts must enter the authorized memory extraction and evaluation pipeline.
4. Personal memory retrieval must not return document chunks by default.
5. Document retrieval must preserve document and version provenance.
6. Both domains may share PostgreSQL and pgvector infrastructure without sharing logical ownership.

## 6. Database and Object Storage Consistency

PostgreSQL and object storage do not provide a single shared ACID transaction.

Raven must therefore use controlled processing operations to manage consistency.

Recommended approach:

1. Register a document processing operation.
2. Validate ownership and file metadata.
3. Store the original object.
4. Verify the stored object's checksum and reference.
5. Persist or finalize the corresponding database records.
6. Update processing state.
7. Reconcile incomplete operations after failures.

The implementation must handle:

- Object upload succeeds but database persistence fails.
- Database operation is created but object upload fails.
- Worker crashes during extraction.
- Duplicate processing requests.
- Partial document deletion.
- Stale processing jobs.

Use idempotency keys and reconciliation operations to prevent duplicate or orphaned artifacts.

## 7. Document Embedding Storage

Document chunk embeddings are derived data.

Their lifecycle must be separate from personal memory embeddings.

Store sufficient metadata to identify:

- Document identifier.
- Document version.
- Chunk identifier.
- Embedding model.
- Model version.
- Embedding dimensions.
- Preprocessing version.
- Generation timestamp.
- Indexing status.

The vector itself may be stored in the existing pgvector infrastructure.

A document embedding must never be considered authoritative content. The original document and its extracted representation remain the source of truth.

## 8. Indexing Strategy

The existing PostgreSQL indexing strategy should be extended to cover document retrieval.

Evaluate indexes for:

- User and ownership identifiers.
- Document identifiers.
- Document versions.
- Processing states.
- Document lifecycle states.
- Chunk sequence and location.
- Document metadata.
- Embedding references.
- Processing operation identifiers.

Use PostgreSQL Full-Text Search for lexical retrieval and pgvector for semantic retrieval.

Hybrid retrieval must apply user ownership and document access filters before returning results.

Exact index definitions and vector index parameters should be determined through implementation and workload evaluation.

## 9. Document Deletion and Retention

Document deletion must account for the complete dependency chain.

The deletion process must consider:

1. Original document objects.
2. Document versions.
3. Extracted representations.
4. Document chunks.
5. Document embeddings.
6. Full-text and vector index entries.
7. Cached retrieval results.
8. Pending extraction and embedding jobs.
9. Temporary processing artifacts.
10. Document-derived personal memory records.

Deleting a document must not automatically delete unrelated personal memories that happen to discuss the same subject.

Where personal memories were explicitly derived from a document, their provenance must be evaluated by the established deletion policy.

Backup retention and tombstone handling must follow the existing Raven deletion architecture.

## 10. Backup and Recovery

Document intelligence must be included in the existing backup and recovery strategy.

Recovery must account for:

- PostgreSQL metadata.
- Object storage references and objects.
- Document versions.
- Extracted representations.
- Chunk records.
- Embedding metadata.
- Deletion tombstones.
- Processing operation state.

After restoration, Raven must reconcile object references, indexing state and deletion tombstones.

Derived embeddings and indexes may be regenerated when necessary, provided the authoritative source content remains available and regeneration is permitted.

## 11. Implementation Constraints

The initial architecture must:

- Retain PostgreSQL as the primary relational database.
- Retain S3-compatible object storage.
- Reuse the existing pgvector infrastructure.
- Preserve separate personal memory and document intelligence ownership.
- Avoid introducing a dedicated document database.
- Avoid introducing a separate vector database without measured justification.
- Preserve document versioning and provenance.
- Enforce user-level authorization throughout retrieval and processing.
- Support idempotent processing and deletion.

## 12. Decisions Deferred

The following decisions require implementation evidence:

- Exact document chunk storage location.
- Exact extracted-text artifact format.
- Object storage lifecycle configuration.
- Whether document content should be partitioned.
- Exact PostgreSQL indexes.
- pgvector index configuration.
- Backup retention periods.
- RPO and RTO targets.

These decisions must not be guessed or presented as finalized.

## 13. Acceptance Criteria

The database and storage architecture is ready for implementation when:

- Original documents can be stored independently of extracted content.
- Document versions can be identified and retrieved.
- Extracted representations preserve document provenance.
- Chunks retain page, section or location metadata where available.
- Document embeddings remain separate from personal memory embeddings.
- User ownership is enforced on all document operations.
- Database and object storage inconsistencies can be reconciled.
- Deletion covers the document dependency chain.
- Backup restoration respects deletion tombstones.
- The existing PostgreSQL architecture supports document intelligence without introducing unnecessary infrastructure.
