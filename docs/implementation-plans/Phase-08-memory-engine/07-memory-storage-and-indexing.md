# 8.7 — Memory Storage and Indexing

## 1. Objective

Implement reliable storage and indexing for the Memory Engine.

This plan covers two distinct data domains:

1. **Personal memory storage and indexing:** authoritative memories, revisions, relationships, metadata, and their retrieval indexes.
2. **Document intelligence storage and indexing:** document chunks, provenance, embeddings, and document retrieval indexes.

Both domains may share approved infrastructure, but they must maintain independent ownership, retrieval boundaries, and lifecycle management.

The implementation must follow the approved Phase 5 data models, Phase 6 algorithms, and Phase 7 technology decisions.

## 2. Architecture references

Read:

- `PROJECT_ARCHITECTURE.md`
- `docs/architecture/`
- `docs/data-models/`
- `docs/algorithms/`
- `docs/technology/`
- `docs/technical-decisions.md`
- `docs/implementation-plans/phase-08-memory-engine/02-database-and-persistence.md`
- `docs/implementation-plans/phase-08-memory-engine/04-extraction-and-evaluation.md`
- `docs/implementation-plans/phase-08-memory-engine/06-memory-resolution.md`
- `docs/implementation-plans/phase-08-memory-engine/08-memory-retrieval.md`
- `docs/implementation-plans/phase-08-memory-engine/12-document-rag-pipeline.md`

## 3. Storage architecture

Use the approved baseline:

- PostgreSQL for authoritative relational records.
- SQLAlchemy for ORM and persistence.
- Alembic for schema migrations.
- pgvector for vector storage.
- PostgreSQL full-text search for keyword retrieval.
- S3-compatible object storage for large source documents and artifacts.

Do not introduce a dedicated vector database without an approved decision supported by workload measurements.

## 4. Personal memory storage

### 4.1 Authoritative memory records

Persist only memories that have passed the approved extraction and resolution lifecycle.

Support the approved data models for:

- Memory sources.
- Memory candidates.
- Atomic memories.
- Memory revisions.
- Category assignments.
- Entities and aliases.
- Entity mentions.
- Entity relationships.
- Memory relationships.
- Episodes and episode membership.
- Derived profiles and their associations.
- Provenance.
- Embedding metadata.
- Processing history.
- Deletion operations.

Use the exact approved model definitions and relationships from Phase 5.

Do not create new authoritative entities or fields merely to simplify implementation.

### 4.2 Revision history

Preserve the approved memory revision history.

Updates must not silently overwrite historical information.

Support:

- Revision identity.
- Revision ordering.
- Relevant timestamps.
- Source provenance.
- Version relationships.
- Current-state identification.

Historical and current values must remain distinguishable.

### 4.3 Memory ownership

Every personal memory must be scoped to its owning user.

Storage and repository operations must enforce ownership.

No retrieval index or cached representation may bypass the ownership rules of the authoritative database.

## 5. Document intelligence storage

Document records and chunks are not personal memory records.

Their persistence and indexing must follow the document models approved through Phase 5 and plan 8.2.

The document domain must support:

- Document identity.
- Document versions.
- Original document references.
- Extracted content.
- Document chunks.
- Chunk ordering.
- Page and section metadata.
- Chunk provenance.
- Document embedding metadata.
- Indexing status.
- Document lifecycle and deletion references.

Document chunks must remain traceable to the original document version and location.

Do not insert document chunks into the authoritative atomic-memory collection.

Do not use personal memory categories to classify document chunks.

## 6. Indexing boundaries

Maintain independent logical indexes for personal memory and document intelligence.

### 6.1 Personal memory indexes

Support indexing for:

- User ownership.
- Memory identity.
- Memory categories.
- Entities.
- Relationships.
- Temporal attributes.
- Confidence and importance metadata.
- Memory embeddings.
- Keyword search.
- Retrieval status.

### 6.2 Document indexes

Support indexing for:

- User ownership.
- Document identity.
- Document version.
- Chunk identity.
- Chunk sequence.
- Page and section location.
- Document metadata.
- Chunk embeddings.
- Keyword search.
- Processing and indexing status.

The document index must retain sufficient metadata to retrieve and cite the correct source passage.

### 6.3 Shared infrastructure

Both logical domains may use the same PostgreSQL deployment and pgvector extension.

Sharing infrastructure does not permit:

- Mixing retrieval results without explicit coordination.
- Ignoring domain ownership.
- Reusing incompatible embedding representations.
- Bypassing source-specific deletion.
- Treating a document chunk as a personal memory.

## 7. Embedding generation and persistence

Embedding generation must follow the approved Phase 7 model-selection and algorithm decisions.

Embeddings are derived data.

The authoritative source content must remain independently stored.

### 7.1 Personal memory embeddings

Memory embeddings must be associated with their authoritative memory and applicable revision.

Track the approved metadata, including:

- Model identifier.
- Model version.
- Vector dimensions.
- Preprocessing configuration.
- Creation timestamp.
- Indexing status.

Regenerate embeddings when required by the approved memory update lifecycle.

### 7.2 Document chunk embeddings

Document chunk embeddings must reference the correct:

- Document.
- Document version.
- Chunk.
- Embedding model.
- Model version.
- Preprocessing configuration.

Embedding a new document version must not silently replace the embeddings belonging to an older version.

The document processing pipeline in plan 8.12 owns document chunk embedding generation and indexing.

### 7.3 Embedding validation

Before persistence, validate:

- Expected vector dimensions.
- Finite numeric values.
- Correct source association.
- Correct model metadata.
- Correct ownership.
- Valid processing state.

Failed embedding generation must not corrupt authoritative source records.

## 8. Keyword and vector indexing

Use the approved PostgreSQL full-text and pgvector capabilities.

### Vector indexing

Support similarity search over the correct logical domain.

Memory retrieval must search personal memory representations.

Document retrieval must search document chunk representations.

### Keyword indexing

Use PostgreSQL full-text search for relevant textual representations.

Preserve language and text-normalization metadata where required by the approved design.

### Hybrid retrieval compatibility

The indexing architecture must support future hybrid retrieval that combines:

- Vector similarity.
- Keyword relevance.
- Metadata filtering.
- Entity or relationship signals where applicable.

Retrieval and ranking behavior belongs to plan 8.8 for personal memory and plan 8.12 for document intelligence.

Similarity is a retrieval signal, not proof of identity or truth.

## 9. Index consistency

Indexing must remain consistent with authoritative records.

Implement a recoverable indexing workflow using the approved background-processing and operation-management architecture.

Requirements:

- Durable indexing state.
- Idempotent index operations.
- Retryable failures.
- Stale-index detection.
- Reconciliation.
- Correct version association.
- Deletion propagation.
- Model-version tracking.

If an index update fails, the authoritative source must remain intact and the indexing state must accurately indicate incomplete work.

Do not silently report a record as fully indexed when required indexing operations have failed.

## 10. Derived-data lifecycle

Treat embeddings, search indexes, cached representations, and other derived structures as dependent data.

When an authoritative memory or document changes:

1. Identify affected derived representations.
2. Mark stale representations appropriately.
3. Schedule the required update.
4. Regenerate or remove affected representations.
5. Verify indexing consistency.
6. Record completion.

Do not allow stale document chunks or embeddings to be presented as belonging to a newer document version.

Do not allow stale memory embeddings to silently represent a newer memory revision.

## 11. Deletion compatibility

This plan must make all derived data discoverable for the full deletion process in plan 8.10.

### Personal memory deletion dependencies

- Authoritative memory.
- Revisions.
- Embeddings.
- Keyword indexes.
- Relationship-derived representations.
- Cached retrieval results.
- Applicable derived profiles and episodes.

### Document deletion dependencies

- Original document objects.
- Document versions.
- Extracted content.
- Chunks.
- Chunk embeddings.
- Keyword indexes.
- Cached document retrieval results.
- Pending processing operations.
- Document-derived personal memory references.

Deletion must respect ownership and dependency boundaries.

Deleting a document must not automatically delete unrelated personal memories.

## 12. Performance considerations

Begin with the approved PostgreSQL and pgvector architecture.

Do not prematurely introduce:

- A dedicated vector database.
- A separate search platform.
- Distributed indexing infrastructure.
- Multiple database deployments.

Evaluate performance using representative Raven workloads.

Any change to indexing strategy or infrastructure must be documented and justified by measurements.

## 13. Testing requirements

### Personal memory storage tests

- Memory persistence.
- Revision history.
- Category associations.
- Entity relationships.
- Provenance persistence.
- Embedding association.
- User isolation.
- Index consistency.

### Document storage and indexing tests

- Document version persistence.
- Chunk ordering.
- Page and section provenance.
- Chunk embedding association.
- Correct version association.
- Keyword index consistency.
- Vector index consistency.
- Failed indexing recovery.
- Duplicate indexing operations.
- Document deletion dependencies.

### Isolation tests

- Document chunks do not appear in personal memory retrieval.
- Memory embeddings are not interpreted as document embeddings.
- Cross-user indexing queries are rejected.
- Document updates preserve historical version associations.
- Deletion in one domain does not silently corrupt the other.

### Failure tests

- Embedding generation failure.
- Database write failure.
- Index update failure.
- Worker interruption.
- Duplicate indexing request.
- Stale index.
- Deleted source.
- Concurrent updates.

## 14. Acceptance criteria

This plan is complete when:

1. Authoritative personal memories are persisted correctly.
2. Memory revision history is preserved.
3. Personal memory metadata and relationships are indexed.
4. Personal memory embeddings are stored with correct metadata.
5. Document chunks are persisted independently.
6. Document chunk provenance is preserved.
7. Document embeddings are stored with correct version references.
8. Memory and document indexes remain logically separate.
9. Hybrid retrieval infrastructure is available for both domains.
10. Indexing failures can be recovered.
11. Deletion dependencies can be identified.
12. Ownership and isolation tests pass.
13. Required integration tests pass.

## 15. Out of scope

This plan does not implement:

- Personal memory retrieval ranking.
- Document parsing.
- OCR.
- Document chunking.
- Document answer assembly.
- Full deletion orchestration.
- Cross-engine retrieval coordination.
- Dedicated external vector database deployment.

These responsibilities belong to their respective plans.

## 16. Claude Code execution instructions

Before implementation:

1. Inspect the existing persistence and indexing implementation.
2. Read the approved Phase 5 data models and Phase 7 technology decisions.
3. Identify reusable repositories, vector infrastructure, and indexing workers.
4. Reconcile personal memory and document indexing boundaries.
5. Identify any schema or migration gaps.
6. Propose the minimum required changes.

Do not silently introduce new schemas, model fields, or dependencies.

After implementation, report:

- Files created or modified.
- Storage and indexing components implemented.
- Embedding metadata and model handling.
- Indexing recovery behavior.
- Dependencies added.
- Migrations created.
- Tests executed and results.
- Acceptance criteria satisfied.
- Known limitations.

Do not automatically proceed to plan 8.8.
