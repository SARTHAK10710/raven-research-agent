# 8.2 — Database and Persistence

## 1. Objective

Implement the Memory Engine's persistence layer using the approved Raven data architecture.

This plan covers persistence for:

1. Personal memory records.
2. Document intelligence records.
3. Their associated metadata, provenance, relationships, and derived data.

Personal memory and document intelligence must remain separate logical domains, even when they share PostgreSQL, pgvector, object storage, and background-processing infrastructure.

The implementation must follow the approved Phase 5 data models and Phase 7 technology decisions. This plan does not authorize inventing or silently changing the underlying data model.

## 2. Architecture references

Read and reconcile the following before implementation:

- `PROJECT_ARCHITECTURE.md`
- `docs/architecture/`
- `docs/data-models/`
- `docs/technical-decisions/Readme.md`
- `docs/technical-decisions/01-baseline-technology-stack.md`
- `docs/technical-decisions/02-database-and-storage-architecture.md`
- `docs/technical-decisions/03-vector-search-and-embedding-infrastructure.md`
- `docs/technical-decisions/04-background-processing-and-messaging.md`

Relevant data-model specifications include:

- Memory Engine models.
- Research Engine models.
- Orchestrator models.
- Shared infrastructure models.
- Relationships and lifecycle.

If the existing specifications do not define a required document entity or relationship, identify the gap and propose an amendment before implementing it.

### 2.1 Approved decisions for this plan

Approved on 2026-11-11. Follow these; they take precedence over earlier open wording in this plan.

| Decision | Source |
|---|---|
| Package layout (`personal/`, `documents/`, shared kernel, `infrastructure/persistence/`) | `01-baseline-technology-stack.md` §23.1 |
| psycopg 3 + synchronous SQLAlchemy 2.0; pooling, transactions, testing | `01-baseline-technology-stack.md` §23.2 |
| `memory` schema; `pm_` / `doc_` / `me_` prefixes; seven `doc_` tables; no implicit cascades; guarded evidence references | `01-baseline-technology-stack.md` §23.3 |
| `OwnerScope` and opaque `owner_id` on every owned row | `01-baseline-technology-stack.md` §23.4 |
| Relationship vocabularies, revision change types, Atomic Memory lifecycle states | `phase-05-memory-engine-models.md`, Phase 8.2 Amendment |
| Embedding **metadata** only in this plan; no vector columns, tables or indexes. Vector storage is created in plan 8.7 after the embedding model is selected | `01-baseline-technology-stack.md` §23.5 |

**Not yet decided:** the embedding model itself (needed before plan 8.7).

## 3. Persistence architecture

### 3.1 Database

Use the approved baseline:

- PostgreSQL as the primary relational database.
- SQLAlchemy as the ORM.
- Alembic for database migrations.
- pgvector for vector storage.
- Pydantic for validation at application boundaries.

Use the existing PostgreSQL deployment and logical schema ownership defined in Phase 7:

- `memory`
- `research`
- `orchestrator`
- `shared`

Do not introduce another database deployment or a separate document database without an approved architectural decision.

### 3.2 Ownership boundaries

The Memory Engine owns its personal memory and document intelligence records.

The Memory Engine must not directly own Research Engine or Orchestrator business records.

Cross-engine references must follow the approved interface and typed-reference boundaries.

### 3.3 Personal memory and document separation

Maintain separate logical persistence domains for:

**Personal memory**
- Memory sources.
- Memory candidates.
- Atomic memories.
- Memory revisions.
- Entities and aliases.
- Entity and memory relationships.
- Episodes and episode membership.
- Derived profiles and associations.
- Memory provenance.
- Memory embedding metadata.
- Category assignments.
- Processing and deletion records.

**Document intelligence**
- Document identity and ownership.
- Document versions.
- Original object-storage references.
- Extracted document representations.
- Document chunks.
- Chunk location and provenance.
- Document embedding metadata.
- Document processing status and operation history.
- Document indexing and deletion dependencies.

These are logical responsibilities, not permission to create duplicate or conflicting tables.

Before creating document-specific tables, reconcile the proposed entities with the existing Phase 5 data-model specifications. Use their approved names and relationships where available.

Do not represent a document chunk as an atomic personal memory.

## 4. Document persistence model

### 4.1 Document identity

A document must have a stable identity independent of its file versions.

The persistence design must support:

- Unique document identity.
- User ownership.
- Document metadata.
- Original filename and detected format.
- Creation and registration timestamps.
- Current processing state.
- Current version reference.
- Retention and deletion state.

A filename must not be treated as a unique document identifier.

### 4.2 Document versions

A document version represents a specific uploaded or updated content state.

The design must preserve:

- Version identity.
- Parent document reference.
- Content checksum.
- Original file reference.
- Detected media type.
- File size.
- Upload timestamp.
- Extraction status.
- Version-specific processing metadata.

An updated document must not silently overwrite the historical version.

The system must be able to distinguish content retrieved from an older version from content retrieved from the current version.

### 4.3 Extracted content

Extracted content is derived from the original document.

The persistence design must support:

- Extracted text.
- Structural information.
- Page and section references.
- Table or layout references where extraction supports them.
- Extraction method and version.
- Extraction status.
- Links to the source document version.

Original documents remain authoritative source artifacts. Extracted content is derived data and must retain a traceable relationship to its source.

### 4.4 Document chunks

Chunks are derived retrieval units created from extracted content.

The model must support:

- Stable chunk identity.
- Parent document and version references.
- Chunk sequence or ordering.
- Extracted text.
- Page, section, or location metadata.
- Chunking strategy and version.
- Content checksum.
- Creation timestamp.
- Indexing state.

Chunk boundaries must not destroy source-location information.

The same source passage must be traceable back to its original document version and location.

### 4.5 Document embedding metadata

Document chunk embeddings must be logically separate from personal memory embeddings.

Track the applicable:

- Source chunk reference.
- Embedding model identifier.
- Model version.
- Vector dimensions.
- Preprocessing configuration.
- Creation timestamp.
- Indexing status.

Use the approved pgvector infrastructure initially.

Do not introduce a dedicated vector database unless workload measurements and an architectural decision justify it.

### 4.6 Document processing operations

Document processing must have durable operation state.

Support tracking:

- Registration.
- File validation.
- Extraction.
- Structure processing.
- Chunking.
- Embedding.
- Indexing.
- Retry and failure.
- Deletion.

Operation records must support idempotency and recovery after worker interruption.

Exact entity names and status values must follow the approved data-model and algorithm specifications.

## 5. Object storage

Use the approved S3-compatible object-storage architecture for original documents and other large binary artifacts.

PostgreSQL stores metadata and object references rather than unnecessarily storing large document binaries.

Object references must support:

- Opaque object identifiers.
- Ownership validation.
- Content checksums.
- Media-type metadata.
- Access-control enforcement.
- Lifecycle and deletion state.

Do not expose raw storage credentials or unrestricted object paths through public APIs.

### 5.1 Database and object-storage consistency

PostgreSQL and object storage do not share a single ACID transaction.

Implement a recoverable workflow:

1. Register the intended operation.
2. Validate ownership and file metadata.
3. Store the object.
4. Persist or finalize the database reference.
5. Verify the relationship.
6. Record completion.
7. Reconcile incomplete operations.

Failed uploads or incomplete registrations must not create silently inconsistent records.

Use the approved operation and reconciliation patterns.

## 6. Database relationships and integrity

Implement the relationships defined in Phase 5.

Enforce:

- Primary keys.
- Foreign keys where appropriate.
- Unique constraints.
- Ownership constraints.
- Valid relationship types.
- Required fields.
- Referential integrity.
- Version relationships.
- Provenance relationships.
- Valid lifecycle transitions.

Avoid unnecessary cross-schema coupling.

Do not introduce a graph database for entity relationships.

## 7. Repository and persistence layer

Implement a clear separation between:

- Domain models.
- Persistence models.
- Repository interfaces.
- Repository implementations.
- Transaction management.
- Database session management.

Repositories must enforce the ownership and access boundaries of the Memory Engine.

Application services should not depend directly on raw SQL or ORM implementation details where repository abstractions are appropriate.

Avoid creating excessive abstraction layers that do not provide a meaningful architectural benefit.

## 8. Transactions and concurrency

Follow the approved transaction and concurrency architecture.

Requirements:

- Keep transactions short.
- Never hold database transactions open during long-running document extraction or embedding operations.
- Use optimistic concurrency where specified.
- Detect stale updates and version conflicts.
- Use idempotency for retriable operations.
- Preserve immutable revision history where required.
- Ensure atomicity for related authoritative state changes.
- Prevent concurrent processing from silently corrupting document or memory state.

Long-running operations must be represented through durable workflow state rather than long database transactions.

## 9. Indexing foundation

Implement only the indexes required by the approved models and current implementation stages.

Consider:

- User and ownership lookups.
- Document identity and version lookups.
- Memory identity and revision lookups.
- Relationship traversal.
- Temporal queries.
- Processing status.
- Idempotency keys.
- Deletion operation lookup.
- Document chunk lookup.
- Vector retrieval.
- Full-text retrieval.

Keep memory and document retrieval logically separate.

Document chunk indexes must not cause document chunks to appear as personal memory records.

Do not prematurely optimize index parameters without representative workload measurements.

## 10. Embedding persistence

Embedding vectors are derived data.

The authoritative source must remain independently stored.

Maintain separate logical indexing and lifecycle for:

- Personal memory embeddings.
- Document chunk embeddings.

The shared pgvector infrastructure may be reused, but retrieval, ownership, model metadata, and deletion must preserve domain boundaries.

Embedding generation and indexing must be recoverable.

If embedding generation fails, the original memory or document must remain intact and its processing state must accurately reflect the failure or pending work.

## 11. Migrations

Use Alembic for schema migrations.

Requirements:

- Version-controlled migrations.
- Reversible migrations where safely possible.
- Explicit handling of destructive changes.
- Backward compatibility where required.
- Migration testing.
- No silent data loss.
- Clear migration documentation.

Before generating migrations, reconcile the ORM definitions with the approved Phase 5 models.

Do not generate tables simply because a proposed implementation class exists.

## 12. Deletion and retention compatibility

This plan establishes persistence support for deletion and retention.

The full deletion workflow belongs to plan 8.10.

The persistence design must allow deletion to cover:

**Personal memory**
- Authoritative memories.
- Revisions.
- Candidates.
- Relationships.
- Episodes and derived profiles.
- Embeddings and indexes.
- Applicable provenance and processing records.

**Document intelligence**
- Original document objects.
- Document versions.
- Extracted representations.
- Chunks.
- Embeddings.
- Search indexes.
- Cached retrieval data.
- Pending document-processing operations.
- Document-derived memory references.

Deletion of a document must not automatically delete unrelated personal memories merely because they discuss the same subject.

Where a personal memory was explicitly derived from a document, preserve the provenance relationship so the deletion policy can evaluate the dependency.

Backup retention and tombstone reapplication must follow the approved lifecycle policy.

## 13. Testing requirements

### Database tests

- Model creation and constraints.
- Foreign-key integrity.
- Unique constraints.
- Ownership enforcement.
- Version relationships.
- Transaction rollback.
- Optimistic concurrency.
- Migration execution.
- Repository behavior.

### Document persistence tests

- Document registration.
- Multiple versions of one document.
- Original object reference persistence.
- Extracted representation persistence.
- Chunk ordering and provenance.
- Embedding metadata persistence.
- Failed processing state.
- Retry and idempotency.
- User isolation.
- Deletion dependency discovery.

### Memory and document isolation tests

- Document chunks cannot be retrieved as personal memories by default.
- Personal memory embeddings cannot be confused with document embeddings.
- Cross-user document access is rejected.
- Cross-user memory access is rejected.
- Document version changes do not silently modify historical retrieval references.

### Failure tests

- Database unavailable.
- Object storage unavailable.
- Partial object upload.
- Database write failure.
- Worker interruption.
- Duplicate operation.
- Concurrent update.
- Migration failure.

## 14. Acceptance criteria

This plan is complete when:

1. The database foundation matches the approved Phase 5 and Phase 7 architecture.
2. Personal memory persistence works with the approved data models.
3. Document identity and version persistence work.
4. Original document objects can be referenced securely.
5. Extracted content and chunk metadata can be persisted.
6. Document and memory embeddings remain logically separate.
7. User ownership is enforced.
8. Transactions and concurrency controls are tested.
9. Migrations execute successfully.
10. Failure and recovery behavior is tested.
11. Deletion dependencies can be identified.
12. All required tests pass.

## 15. Out of scope

This plan does not implement:

- The complete ingestion pipeline.
- Memory extraction and evaluation.
- Memory resolution.
- Document parsing and OCR.
- Document chunking algorithms.
- Embedding generation.
- Hybrid document retrieval.
- Evidence selection and answer assembly.
- Full deletion orchestration.

These responsibilities belong to their respective implementation plans.

## 16. Claude Code execution instructions

Before implementation:

1. Inspect the repository and existing database configuration.
2. Read the referenced Phase 5 and Phase 7 specifications.
3. Identify existing models, migrations, repositories, and shared infrastructure.
4. Reconcile document persistence requirements with the approved data models.
5. Report missing or conflicting schema decisions.
6. Propose the minimum required changes.

Do not silently invent schema entities or alter approved models.

After implementation, report:

- Files created or modified.
- Models and relationships implemented.
- Migrations created.
- Dependencies added.
- Tests executed and results.
- Acceptance criteria satisfied.
- Known limitations and unresolved decisions.

Do not automatically proceed to plan 8.3.
