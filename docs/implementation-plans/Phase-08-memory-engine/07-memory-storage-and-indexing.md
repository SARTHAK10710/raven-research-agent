# Phase 8.7 — Memory Storage & Indexing Implementation Plan

## 1. Objective

Implement the Memory Engine's authoritative memory storage and indexing capabilities.

This milestone receives resolved memory operations from Phase 8.6 and ensures that authoritative memories, revisions, metadata, relationships and derived search representations are stored consistently.

The system must support efficient future retrieval without compromising data integrity or provenance.

### Primary objectives

- Persist authoritative memory records.
- Maintain immutable memory revisions.
- Store memory metadata and category assignments.
- Maintain entity and memory relationships.
- Generate and manage memory embeddings.
- Implement vector and keyword indexing.
- Support metadata-based filtering.
- Maintain consistency between authoritative records and derived indexes.
- Support ownership, concurrency and idempotency.
- Prepare storage for Phase 8.8 retrieval.

## 2. Architecture references

Claude Code must review:

1. `PROJECT_ARCHITECTURE.md`
2. `docs/architecture/` — Memory Engine architecture.
3. `docs/data-models/` — approved Memory Engine data models.
4. `docs/algorithms/memory/03-memory-retrieval.md`
5. `docs/algorithms/memory/02-memory-resolution.md`
6. `docs/technology/01-baseline-technology-stack.md`
7. `docs/technology/02-database-and-storage-architecture.md`
8. `docs/technology/03-vector-search-and-embedding-infrastructure.md`
9. `docs/technology/07-observability-and-testing-infrastructure.md`
10. `docs/implementation-plans/phase-08-memory-engine/02-database-and-persistence.md`
11. `docs/implementation-plans/phase-08-memory-engine/06-memory-resolution.md`

The Phase 5 data models and Phase 7 technology decisions are authoritative.

Do not introduce a new database or redefine the approved memory storage architecture without identifying the architectural gap.

## 3. Scope

### Included

- Authoritative memory persistence.
- Memory revision persistence.
- Metadata storage.
- Category assignment persistence.
- Relationship persistence.
- Provenance persistence.
- Embedding generation integration.
- Embedding metadata management.
- Vector indexing.
- Keyword indexing.
- Metadata indexing.
- Index consistency.
- Index update and rebuild operations.
- Storage and indexing tests.

### Excluded

- User-facing memory retrieval and ranking.
- Dynamic Top-K selection.
- Iterative retrieval.
- Memory consolidation.
- Profile generation.
- Forgetting and deletion execution.
- Document chunk retrieval and document RAG.

These capabilities belong to later milestones or the final Phase 8 review.

## 4. Storage architecture

Follow the approved storage design:

- PostgreSQL is the authoritative structured data store.
- The `memory` schema owns Memory Engine records.
- pgvector provides the initial vector storage capability.
- PostgreSQL full-text search provides the initial keyword retrieval foundation.
- Object storage preserves large original source content.
- Embeddings and indexes are derived data, not authoritative memory records.

Do not introduce a dedicated vector database at this stage.

Any future migration to a separate vector database must be justified by measured workload requirements.

## 5. Authoritative memory storage

Implement persistence for the approved memory data models.

The implementation must reconcile its operations with the existing model inventory, including:

- Atomic Memory.
- Memory revisions.
- Memory Source.
- Memory Candidate.
- Category assignments.
- Entity associations.
- Memory relationships.
- Provenance.
- Embedding metadata.
- Processing history.

Use the exact approved entity names and relationships from the Phase 5 specifications.

### Requirements

- Maintain stable identifiers.
- Enforce user ownership.
- Validate foreign-key relationships.
- Preserve source provenance.
- Maintain revision history.
- Preserve current versus historical memory states.
- Support transactional updates.
- Prevent unintended duplicate records.
- Enforce approved lifecycle states.

### Important distinction

An accepted candidate is not automatically an authoritative active memory.

Only candidates with an approved resolution outcome may be persisted or updated as authoritative memories.

The storage layer must enforce this boundary through its application interfaces and validation rules.

## 6. Memory revision management

Implement the approved revision model.

Requirements:

- Preserve previous revisions.
- Create new revisions for approved updates.
- Associate revisions with their source evidence.
- Track revision creation timestamps.
- Preserve relevant temporal information.
- Identify the current authoritative revision.
- Support revision history retrieval internally.

Do not overwrite historical revision content.

Do not create unnecessary revisions for repeated idempotent operations.

A revision must represent a meaningful approved change.

## 7. Metadata and category indexing

Implement indexes for commonly used metadata fields.

Follow the approved Phase 7 database indexing strategy.

Potential indexing dimensions include:

- User ownership.
- Memory identifier.
- Entity identifier.
- Category.
- Lifecycle state.
- Importance.
- Confidence.
- Source reference.
- Creation timestamp.
- Update timestamp.
- Temporal validity.
- Relationship references.

Requirements:

- Enforce ownership filtering in all relevant queries.
- Support efficient metadata filtering.
- Avoid excessive index creation.
- Use composite indexes only when justified by query patterns.
- Preserve database migration compatibility.

Do not create indexes for every field without measuring their usefulness.

## 8. Embedding generation and lifecycle

Implement memory embedding generation using the approved sentence-transformers ecosystem.

Embeddings are derived representations of authoritative memory content.

They must never replace the original memory record.

### 8.1 Embedding input preparation

Prepare memory content for embedding using deterministic preprocessing.

Requirements:

- Normalize supported text.
- Preserve meaningful context.
- Avoid removing qualifiers that change meaning.
- Use consistent preprocessing across indexing and retrieval.
- Respect ownership and access boundaries.

### 8.2 Embedding generation

Implement an embedding service responsible for:

- Loading the approved embedding model.
- Generating embeddings.
- Validating output dimensions.
- Checking for invalid or non-finite values.
- Recording model metadata.
- Handling model failures.

Model selection must be based on Raven-specific evaluation rather than assumptions about model quality.

### 8.3 Embedding metadata

Preserve the approved embedding metadata, including:

- Memory reference.
- Model identifier.
- Model version.
- Embedding dimensions.
- Preprocessing version.
- Creation timestamp.
- Relevant lifecycle state.

Follow the Phase 5 data model.

### 8.4 Embedding priority

Follow the approved hybrid embedding strategy:

- Important memories may receive priority embedding generation.
- Routine memories may be processed asynchronously.
- Updated memories require appropriate embedding refresh.
- Embedding failures must not corrupt authoritative memory records.

### 8.5 Embedding consistency

When a memory revision changes:

- Mark the previous embedding as stale where appropriate.
- Generate a new embedding for the current revision.
- Ensure the index does not incorrectly represent an older revision as current.
- Preserve model-version metadata.

Do not silently overwrite embedding metadata in a way that destroys the ability to identify which revision was embedded.

## 9. Vector indexing

Use PostgreSQL with pgvector.

Implement the initial vector storage and indexing foundation.

Requirements:

- Store embeddings using the approved vector representation.
- Associate vectors with the correct memory and revision.
- Enforce ownership through the authoritative memory relationship.
- Support metadata-compatible search queries.
- Validate vector dimensions.
- Handle invalid embedding values.
- Support index maintenance.

### Index selection

Evaluate the available pgvector index approaches, including:

- HNSW.
- IVFFlat.

Do not assume one index type is automatically superior for Raven.

Record the selected initial approach and the reasons for it.

Defer detailed index parameters until benchmark data is available.

## 10. Keyword indexing

Implement PostgreSQL full-text search as the initial keyword search mechanism.

Requirements:

- Normalize searchable memory text.
- Maintain the keyword representation.
- Support language-aware configuration where appropriate.
- Associate searchable text with authoritative memory records.
- Respect ownership and lifecycle filtering.
- Update indexes when the authoritative memory revision changes.

Do not assume keyword matching alone is sufficient for semantic retrieval.

## 11. Index consistency and maintenance

Indexes are derived data.

The authoritative memory record must remain valid even when a derived index is temporarily unavailable.

Implement reliable index maintenance.

### Required behavior

- Track pending indexing operations.
- Handle embedding generation failures.
- Support retryable indexing jobs.
- Detect stale embeddings.
- Rebuild derived indexes where necessary.
- Prevent duplicate index records.
- Support reconciliation between authoritative records and indexes.

### Update consistency

When a memory changes:

1. Persist the authoritative memory change.
2. Register the required derived-data update.
3. Generate the updated embedding.
4. Update vector and keyword indexes.
5. Verify index state.
6. Mark indexing complete.

Use the approved asynchronous processing and idempotency architecture.

Do not assume that a database transaction and a background queue publication are automatically atomic.

Use the approved transactional outbox or equivalent reliable handoff approach where appropriate.

## 12. Concurrency and integrity

Implement the approved concurrency controls.

Requirements:

- Optimistic concurrency for memory updates.
- Revision conflict detection.
- Idempotent indexing operations.
- Stable ownership enforcement.
- Referential integrity.
- Transactional persistence for authoritative memory changes.
- Safe retries.
- Stale derived-data detection.

An indexing failure must never cause an authoritative memory update to be falsely reported as unsuccessful if the authoritative transaction already committed.

The system must distinguish:

- Memory persistence status.
- Embedding generation status.
- Indexing status.

## 13. Failure handling

| Scenario | Expected behavior |
|---|---|
| Memory persistence failure | Roll back the authoritative transaction |
| Duplicate persistence request | Resolve idempotently |
| Revision conflict | Reload and re-evaluate |
| Embedding model unavailable | Preserve memory and retry indexing |
| Invalid embedding dimensions | Reject derived representation |
| Vector index failure | Record failure and reconcile |
| Keyword indexing failure | Preserve authoritative memory |
| Partial index update | Mark derived data incomplete |
| Stale embedding | Schedule regeneration |
| Queue publication failure | Recover through reliable handoff |
| Database interruption | Preserve integrity and recover safely |

Do not delete authoritative memories because an embedding or index operation failed.

## 14. Testing requirements

### Unit tests

Test:

- Memory persistence validation.
- Revision creation.
- Metadata handling.
- Category assignment.
- Embedding preprocessing.
- Embedding output validation.
- Index operation construction.
- Idempotency behavior.

### Component tests

Test:

- Authoritative memory persistence.
- Revision history.
- Embedding generation.
- Embedding metadata persistence.
- Vector indexing.
- Keyword indexing.
- Metadata indexing.
- Index update operations.
- Index reconciliation.

### Integration tests

Test:

- PostgreSQL and pgvector integration.
- SQLAlchemy persistence.
- Alembic migration compatibility.
- Background indexing jobs.
- Transactional outbox or approved reliable handoff.
- Ownership filtering.
- Revision-to-embedding consistency.

### Reliability tests

Test:

- Embedding service interruption.
- Index update failure.
- Duplicate indexing jobs.
- Concurrent memory updates.
- Stale embedding detection.
- Index rebuild.
- Database restart during indexing.

## 15. Observability

Record structured events for:

- Memory persisted.
- Revision created.
- Embedding generation started.
- Embedding generation completed.
- Embedding generation failed.
- Vector index updated.
- Keyword index updated.
- Index reconciliation started.
- Index reconciliation completed.
- Indexing failed.

Track:

- Authoritative memory persistence latency.
- Embedding generation latency.
- Embedding failure rate.
- Indexing queue depth.
- Indexing completion latency.
- Stale embedding count.
- Index reconciliation failures.
- Index update retry count.

Do not log raw memory content or embedding vectors.

## 16. Acceptance criteria

Phase 8.7 is complete only when:

- [ ] Authoritative memories can be persisted.
- [ ] Immutable revision history is maintained.
- [ ] Ownership and referential integrity are enforced.
- [ ] Metadata and category assignments are indexed.
- [ ] Approved relationships are persisted.
- [ ] Provenance remains traceable.
- [ ] Memory embeddings can be generated.
- [ ] Embedding metadata is stored.
- [ ] pgvector integration works.
- [ ] Keyword indexing works.
- [ ] Index updates are idempotent.
- [ ] Stale embeddings can be identified.
- [ ] Derived-data failures do not corrupt authoritative memory.
- [ ] Index reconciliation is available.
- [ ] Concurrency and failure handling are tested.
- [ ] Unit and integration tests pass.
- [ ] No out-of-scope retrieval or deletion functionality has been introduced.

## 17. Implementation constraints

Claude Code must:

1. Inspect the repository before modifications.
2. Reuse Phase 8.1–8.6 implementations.
3. Follow approved Phase 5 data models.
4. Follow Phase 6 algorithms.
5. Follow Phase 7 technology decisions.
6. Use PostgreSQL and pgvector initially.
7. Keep authoritative records separate from derived indexes.
8. Preserve immutable revisions.
9. Preserve provenance and ownership.
10. Keep embedding generation separate from authoritative memory persistence.
11. Avoid introducing a dedicated vector database without an approved decision.
12. Avoid generative LLM functionality.
13. Avoid implementing document RAG in this milestone.
14. Place source code inside `memory-engine/`.
15. Place tests inside `tests/`.
16. Do not proceed to Phase 8.8 automatically.

If an approved model or persistence capability is insufficient, report the gap and recommend a change before modifying the schema.

## 18. Completion report

Claude Code must provide:

1. Summary of storage functionality.
2. Files created or modified.
3. Database migrations introduced.
4. Memory and revision persistence details.
5. Embedding model and version.
6. Vector indexing implementation.
7. Keyword indexing implementation.
8. Index consistency and recovery approach.
9. Tests executed and exact results.
10. Known limitations.
11. Deviations from approved specifications.
12. Acceptance criteria status.

Clearly distinguish authoritative storage completion from derived-index completion.

## 19. Definition of done

Phase 8.7 is complete when Raven can persist authoritative memories and their revisions while maintaining reliable metadata, vector and keyword indexes that can be used by the retrieval system.

**Authoritative memory data remains the source of truth. Embeddings and indexes remain rebuildable derived data.**
