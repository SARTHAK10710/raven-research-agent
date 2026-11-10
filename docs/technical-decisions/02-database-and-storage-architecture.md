# Phase 7.2 — Database, Storage & Data Infrastructure Design

> **Document history:** This file contains the original Phase 7.2 specification, restored from commit `9a42f2c`, followed by the Document Intelligence and RAG Storage amendment from commit `c49d018`, appended at the end of this file. The amendment extends the original decisions; it does not replace them.

**Project:** Raven Research Agent  
**Phase:** 7 — Technology & Infrastructure Selection  
**Subphase:** 7.2 — Database, Storage & Data Infrastructure Design  
**Status:** Architecture specification  
**Primary Database:** PostgreSQL  
**Vector Extension:** pgvector  
**Object Storage:** S3-compatible storage  
**Optimization Priority:** Quality first

---

# 1. Purpose

This document defines how Raven will organize, store, access, protect and maintain its data infrastructure.

It translates the logical data models documented in Phase 5 into a practical storage architecture.

The infrastructure must support:

1. Memory Engine data.
2. Research Engine data.
3. Agent Orchestrator data.
4. Shared Infrastructure data.
5. Large documents and content.
6. Derived data and indexes.
7. Data retention and deletion.
8. Backup and recovery.
9. Transaction integrity.
10. Secure cross-engine communication.

The objective is to maintain reliable data storage without introducing unnecessary infrastructure complexity.

---

# 2. Database Architecture Decision

<badge color="success">Selected baseline</badge>

**Use one PostgreSQL deployment with logically separated database schemas.**

The initial Raven implementation will use one PostgreSQL database deployment.

Within that deployment, domain-specific schemas will establish ownership boundaries.

### Recommended logical structure

```text
PostgreSQL
│
└── raven
    │
    ├── memory
    │   ├── memory_sources
    │   ├── memory_candidates
    │   ├── atomic_memories
    │   ├── entities
    │   ├── relationships
    │   ├── episodes
    │   ├── profiles
    │   └── memory_metadata
    │
    ├── research
    │   ├── research_sessions
    │   ├── research_snapshots
    │   ├── research_sources
    │   ├── findings
    │   ├── evidence
    │   ├── comparisons
    │   └── research_metadata
    │
    ├── orchestrator
    │   ├── executions
    │   ├── tasks
    │   ├── dependencies
    │   ├── checkpoints
    │   ├── execution_events
    │   └── execution_results
    │
    └── shared
        ├── identities
        ├── authorization_metadata
        ├── configurations
        └── infrastructure_metadata
```

The names above are logical examples aligned with Phase 5. They are not finalized SQL table definitions.

## Why one deployment initially?

A single PostgreSQL deployment offers:

- Lower operational complexity.
- Simplified backup and recovery.
- Transactional reliability.
- Easier development.
- Shared connection management.
- Lower initial infrastructure costs.

It also allows Raven to establish ownership boundaries before introducing distributed database operations.

## Important distinction

One database deployment does not mean one shared business-data domain.

Each engine remains the authoritative owner of its own data.

---

# 3. Database Schema Ownership

Each logical schema must have a defined owner.

| Schema | Owner | Responsibility |
|---|---|---|
| `memory` | Memory Engine | Personal memory and its derived records |
| `research` | Research Engine | Research sessions, findings and evidence |
| `orchestrator` | Agent Orchestrator | Executions, tasks and workflow state |
| `shared` | Shared Infrastructure | Identity and infrastructure metadata |

## Ownership rules

1. Each engine owns writes to its schema.
2. Other engines must not directly modify its records.
3. Cross-engine access must use authorized interfaces.
4. Cross-engine references must preserve their originating owner.
5. Shared Infrastructure must not become an owner of Memory or Research business data.
6. Derived records must remain owned by the component responsible for generating them.

## Database permissions

Use separate database roles for application components where practical.

Illustrative roles:

```text
raven_memory_role
raven_research_role
raven_orchestrator_role
raven_shared_role
raven_migration_role
```

The migration role should have controlled schema-management permissions.

Application roles should receive only the permissions required by their responsibilities.

Avoid granting every component unrestricted access to every schema.

---

# 4. Cross-Engine Data Access

## Purpose

Allow engines to exchange information without violating domain ownership.

### Recommended approach

Use engine interfaces and typed references.

Example:

```text
Agent Orchestrator
        |
        v
Memory Engine Interface
        |
        v
Memory-owned records
```

```text
Agent Orchestrator
        |
        v
Research Engine Interface
        |
        v
Research-owned records
```

## Cross-engine access rules

- The Orchestrator requests information through engine interfaces.
- The Memory Engine controls memory retrieval and updates.
- The Research Engine controls research retrieval and updates.
- Engine interfaces validate access and ownership.
- The Orchestrator receives bounded result objects or references.
- Temporary execution context must follow explicit retention rules.

## Cross-domain references

A reference must preserve:

- Referenced record ID.
- Owning engine.
- Record type.
- User scope where applicable.
- Version or revision where required.

A reference must not imply permission to modify the referenced record.

## Referential integrity

Use database foreign keys for relationships within an ownership domain wherever appropriate.

For cross-engine relationships, use typed references and interface-level validation by default.

Do not introduce unrestricted cross-domain writes merely to simplify database queries.

---

# 5. Relational Data Modeling Strategy

PostgreSQL will store Raven's structured authoritative data.

The database should use relational structures for information that benefits from:

- Strong typing.
- Constraints.
- Relationships.
- Transactions.
- Indexed retrieval.
- Consistent updates.

## Storage principles

### Structured records

Use relational columns for stable and frequently queried attributes.

Examples:

- IDs.
- User scope.
- Status.
- Entity references.
- Timestamps.
- Importance.
- Confidence metadata references.
- Version numbers.

### JSONB

Use JSONB selectively for flexible or evolving metadata.

Appropriate examples:

- Optional extraction metadata.
- Source-specific metadata.
- Flexible contextual attributes.
- Processing configuration snapshots.
- Extensible result metadata.

### Avoid excessive JSONB

Do not place every field inside a JSONB object.

Fields that require frequent filtering, constraints, joins or indexing should generally use appropriate relational columns.

## Hybrid modeling

Use relational records for authoritative entities and JSONB for genuinely flexible attributes.

This preserves queryability without making the schema unnecessarily rigid.

---

# 6. Data Lifecycle Classes

Raven data will follow four logical lifecycle classes.

| Class | Description | Storage treatment |
|---|---|---|
| Authoritative | Original or authoritative business records | Durable PostgreSQL or object storage |
| Derived | Generated embeddings, profiles, summaries and indexes | Rebuildable where possible |
| Temporary | Short-lived processing content | Temporary storage with controlled expiration |
| Cached | Reusable performance data | Cache with invalidation and expiration rules |

## Authoritative data

Examples:

- Atomic memories.
- Research findings.
- Evidence records.
- Research snapshots.
- Execution and task state.

Authoritative data must not be silently replaced by derived information.

## Derived data

Examples:

- Embeddings.
- Search indexes.
- Derived profiles.
- Consolidated representations.

Derived data must retain references to its source records.

## Temporary data

Examples:

- Intermediate extraction content.
- Temporary document processing artifacts.
- Execution-scoped context.
- Temporary research page content.

Temporary content must have an explicit lifecycle.

## Cached data

Examples:

- Frequently accessed retrieval results.
- Configuration cache.
- Authorization-related cache.

Caches must support invalidation when authoritative records change or are deleted.

---

# 7. PostgreSQL Transaction Strategy

## Purpose

Maintain consistency when multiple related records must be created or updated together.

## Transaction principles

Use transactions for operations that require atomicity within an ownership boundary.

Examples:

- Creating a memory and its required relationships.
- Updating a research finding and its revision metadata.
- Creating an execution and its initial tasks.
- Recording a state transition and its associated event.

## Transaction boundaries

Prefer owner-scoped transactions.

A transaction should not casually span unrelated engine business operations.

For workflows involving multiple engines, use the Orchestrator's execution state and asynchronous coordination rather than assuming a single database transaction can make the complete workflow atomic.

## Consistency strategy

Use:

- ACID transactions.
- Foreign key constraints.
- Unique constraints.
- Check constraints.
- Optimistic concurrency.
- Version validation.
- Idempotency keys.
- Controlled retries.

## Optimistic concurrency

When updating an existing record:

1. Read its current version.
2. Prepare the update.
3. Verify that the version has not changed.
4. Apply the update.
5. Increment the version.
6. Handle conflicts through reload and re-evaluation.

Do not silently overwrite concurrent updates.

## Long-running workflows

Never keep a database transaction open for the duration of a long research task or background workflow.

Persist checkpoints and task states between operations.

---

# 8. Database Indexing Strategy

Indexes should reflect actual access patterns.

Do not index every field by default.

## Index categories

### 8.1 Ownership indexes

Support user-scoped retrieval and authorization-aware filtering.

Examples:

- `user_id`
- `owner_scope`
- `record_id`

### 8.2 Metadata indexes

Support filtering by:

- Status.
- Category.
- Type.
- Entity reference.
- Processing state.

### 8.3 Temporal indexes

Support queries involving:

- Created time.
- Updated time.
- Valid time.
- Transaction time.
- Publication time.
- Event time.

### 8.4 Relationship indexes

Support lookups by:

- Source record.
- Target record.
- Relationship type.
- Entity reference.

### 8.5 Operational indexes

Support:

- Execution lookup.
- Task status.
- Retry scheduling.
- Dependency resolution.
- Queue-related processing.

### 8.6 Search indexes

Support:

- PostgreSQL full-text search.
- pgvector similarity search.
- Metadata-filtered retrieval.

## Indexing rules

1. Index frequently filtered fields.
2. Use composite indexes only where query patterns justify them.
3. Consider partial indexes for selective status-based queries.
4. Monitor index size and write overhead.
5. Review query plans.
6. Revisit indexing after performance evaluation.
7. Preserve user isolation in retrieval queries.

Exact index definitions and vector index parameters will be determined during implementation and benchmarking.

---

# 9. Database Connection Management

## Purpose

Control the number of active database connections and prevent resource exhaustion.

## Recommended strategy

Use SQLAlchemy connection pooling as the initial application-level approach.

Configure:

- Pool size.
- Maximum overflow.
- Connection timeout.
- Connection health checks.
- Connection recycling where required.

These values must be established through workload testing.

## Future option

PgBouncer may be introduced if connection volume, deployment topology or worker concurrency justifies an additional connection-pooling layer.

It is not mandatory for the initial baseline.

## Safety requirements

- Do not share database sessions across concurrent tasks.
- Keep transaction scopes controlled.
- Close sessions reliably.
- Handle connection failures.
- Avoid unbounded worker concurrency.
- Monitor connection utilization.

---

# 10. Object Storage Architecture

## Purpose

Store large content separately from relational records.

**Selected approach:** S3-compatible object storage.

PostgreSQL stores object metadata and controlled references.

Object storage stores the actual content.

## Logical storage organization

```text
Raven Object Storage
│
├── memory/
│   ├── original-content/
│   ├── document-content/
│   └── archived-content/
│
├── research/
│   ├── source-content/
│   ├── extracted-content/
│   └── snapshots/
│
├── processing/
│   ├── temporary-documents/
│   └── intermediate-artifacts/
│
└── system/
    └── controlled-artifacts/
```

This is a logical organization. Physical buckets and prefixes may be adjusted according to the selected provider.

## Object metadata

For every stored object, maintain relevant metadata such as:

- Object ID.
- Owner scope.
- Owning engine.
- Object type.
- Storage reference.
- Content type.
- Content size.
- Checksum.
- Creation timestamp.
- Retention class.
- Lifecycle status.

## Object naming

Use opaque, non-sensitive identifiers.

Do not expose:

- User email addresses.
- Private memory content.
- Sensitive document titles.
- Authentication information.

in public object keys.

## Content integrity

- Calculate content checksums.
- Verify uploads.
- Detect corrupted objects.
- Preserve original content when required.
- Maintain metadata references.
- Handle partial uploads safely.

## Access control

Object access must be authorized through application-controlled operations.

Avoid making private memory or research objects publicly accessible.

---

# 11. Database and Object Storage Consistency

PostgreSQL and object storage do not share one ordinary ACID transaction.

Raven must handle operations that affect both systems carefully.

## Recommended workflow

Example: document upload.

1. Create an upload operation record.
2. Validate the user and document.
3. Upload the object.
4. Verify object integrity.
5. Persist the corresponding metadata and reference.
6. Mark the operation complete.
7. Reconcile incomplete operations.

## Failure scenarios

### Object upload succeeds, database write fails

The object may become orphaned.

Record and reconcile the incomplete operation. Remove the orphan only after verifying that no valid record references it.

### Database metadata is created, object upload fails

The metadata must remain in a non-usable or failed state until recovery completes.

Do not expose a missing object as a valid document.

### Partial upload

Use the storage provider's supported multipart upload lifecycle and cleanup process.

## Consistency principle

Use explicit operation state and reconciliation rather than assuming atomicity across PostgreSQL and object storage.

---

# 12. Deletion & Retention Infrastructure

Deletion is a critical Raven requirement because personal memory and research data may exist in several storage layers.

## Deletion scope

A deletion workflow may affect:

- PostgreSQL records.
- Object storage.
- Embeddings.
- Search indexes.
- Relationship records.
- Derived profiles.
- Cached results.
- Temporary processing data.
- Backups according to the applicable backup policy.

## Deletion workflow

```text
Deletion Request
       |
       v
Authorization Validation
       |
       v
Deletion Operation Created
       |
       v
Affected Records Identified
       |
       v
Deletion Propagation
       |
       +---- PostgreSQL
       |
       +---- Object Storage
       |
       +---- Vector Records
       |
       +---- Search Indexes
       |
       +---- Caches
       |
       +---- Derived Data
       |
       v
Deletion Verification
       |
       v
Completion or Reconciliation
```

## Deletion principles

1. Deletion must be authorized.
2. The operation must be idempotent.
3. A deletion operation must be traceable.
4. Unrelated records must remain untouched.
5. Derived data must be included.
6. Temporary copies must be accounted for.
7. Partial failures must remain visible.
8. Completion must not be claimed before required propagation is confirmed.

## Backup handling

Backup retention and deletion must be handled through an explicit policy.

Where physical removal from an existing backup is not practical, maintain deletion records or tombstones so restored data cannot reintroduce deleted information.

The restoration process must reapply applicable deletion state before restored data becomes accessible.

Exact retention durations will be determined by product, legal and operational requirements.

---

# 13. Backup & Recovery Architecture

## Purpose

Protect Raven against:

- Database corruption.
- Accidental deletion.
- Infrastructure failure.
- Storage failure.
- Deployment errors.
- Failed migrations.
- Operational mistakes.

## PostgreSQL backup strategy

The production backup design should support:

- Periodic database backups.
- Point-in-time recovery where supported.
- WAL archiving.
- Backup integrity verification.
- Restore testing.
- Controlled backup retention.

## Object storage backup strategy

The design should consider:

- Versioning where appropriate.
- Replication where justified.
- Lifecycle policies.
- Integrity checks.
- Recovery of deleted or overwritten content when permitted.

## Recovery requirements

1. Backups must be protected.
2. Restore operations must be access-controlled.
3. Recovery procedures must be documented.
4. Restore tests must be performed.
5. Database and object references must be reconciled.
6. Deletion tombstones must be reapplied.
7. Restored services must not expose incomplete or inconsistent data.

## Recovery objectives

Define the following during deployment planning:

- Recovery Point Objective (RPO).
- Recovery Time Objective (RTO).

These values depend on availability requirements and cost constraints. They are not finalized in this document.

---

# 14. Data Retention & Lifecycle Policies

Different data classes require different retention behavior.

| Data class | Retention principle |
|---|---|
| Authoritative memory | Retain according to memory lifecycle and user instructions |
| Research findings | Retain according to research retention policy |
| Research source metadata | Retain according to provenance requirements |
| Full source content | Temporary by default; selectively retain |
| Execution records | Retain according to operational and audit needs |
| Temporary processing data | Expire after its required lifecycle |
| Derived embeddings | Rebuild or update when source data changes |
| Cached data | Invalidate or expire when necessary |
| Backups | Follow controlled backup retention policy |

## Lifecycle requirements

- Retention policies must be explicit.
- Expiration must be traceable where necessary.
- Derived data must not outlive its source incorrectly.
- User deletion instructions must override ordinary retention where applicable, subject to legal obligations.
- Temporary data must not become permanent accidentally.

---

# 15. Database Migration Strategy

Database schemas will evolve as Raven develops.

Use Alembic for controlled schema migrations.

## Migration principles

1. Every schema change must have a migration.
2. Migrations must be version-controlled.
3. Migrations must be reviewed.
4. Production migrations must be backed by a recovery plan.
5. Destructive changes must be handled cautiously.
6. Schema changes must preserve existing data where required.
7. Cross-component contract compatibility must be considered.

## Migration workflow

```text
Schema Change
     |
     v
Migration Design
     |
     v
Migration Review
     |
     v
Development Validation
     |
     v
Backup / Recovery Check
     |
     v
Controlled Migration
     |
     v
Post-Migration Validation
     |
     v
Completion
```

## Compatibility

For changes affecting multiple components, prefer backward-compatible transitions where practical.

Do not assume all workers and application instances update simultaneously.

---

# 16. Performance & Scaling Strategy

The initial database architecture should be optimized using actual workload measurements.

## Initial optimization priorities

- Correct indexes.
- Efficient SQL queries.
- Bounded connection pools.
- Controlled worker concurrency.
- Efficient pagination.
- Appropriate transaction boundaries.
- Avoiding unnecessary joins.
- Efficient vector retrieval.
- Selective object retrieval.
- Monitoring slow queries.

## Scaling options

Introduce additional infrastructure only when justified.

| Requirement | Possible future solution |
|---|---|
| High relational workload | Read replicas or database scaling |
| High vector workload | Dedicated vector database |
| High search workload | Dedicated search engine |
| High connection volume | PgBouncer |
| Large data volume | Partitioning and archival |
| Independent engine scaling | Separate engine services and databases |
| High availability | Managed HA PostgreSQL or equivalent architecture |

These are future options, not current requirements.

---

# 17. Security Requirements

1. Enforce user-level isolation.
2. Use least-privilege database roles.
3. Encrypt data in transit.
4. Encrypt sensitive stored content at rest.
5. Protect database credentials.
6. Restrict network access.
7. Validate ownership on every private data operation.
8. Audit sensitive administrative actions.
9. Prevent unauthorized object access.
10. Avoid exposing raw object storage locations.
11. Protect backups.
12. Ensure deletion state survives recovery.
13. Avoid sensitive data in application logs.
14. Review database permissions during schema changes.

---

# 18. Infrastructure Failure Handling

| Failure | Required behavior |
|---|---|
| Database unavailable | Stop unsafe writes and apply controlled retry |
| Database timeout | Reconcile operation state before retrying |
| Object storage unavailable | Preserve operation state and retry safely |
| Object missing | Mark content unavailable and avoid false success |
| Vector index unavailable | Use permitted fallback retrieval or report degradation |
| Cache unavailable | Fall back to authoritative storage where safe |
| Migration failure | Stop affected deployment and follow recovery procedure |
| Partial deletion | Keep operation pending and reconcile remaining targets |
| Backup restoration | Reapply deletion state and validate references |

Failure handling must preserve data integrity rather than maximize apparent availability.

---

# 19. Evaluation Metrics

These metrics will be evaluated during Phase 12 and infrastructure performance testing.

| Area | Metric |
|---|---|
| Database | Query latency |
| Database | Transaction failure rate |
| Database | Connection utilization |
| Database | Deadlock frequency |
| Database | Slow query frequency |
| Storage | Object retrieval latency |
| Storage | Upload failure rate |
| Storage | Checksum verification failures |
| Indexing | Query performance |
| Deletion | Deletion propagation completion |
| Recovery | Restore success rate |
| Recovery | RPO and RTO compliance |
| Integrity | Orphaned object count |
| Integrity | Referential consistency |
| Security | Unauthorized access attempts |

Numerical targets will be established using measured workload requirements.

---

# 20. Decisions Finalized in Phase 7.2

| Decision | Selected approach | Status |
|---|---|---|
| Primary database | PostgreSQL | Selected |
| Initial database deployment | One deployment | Selected |
| Logical database organization | Domain-specific schemas | Selected |
| Memory data ownership | Memory schema | Selected |
| Research data ownership | Research schema | Selected |
| Orchestrator data ownership | Orchestrator schema | Selected |
| Shared infrastructure data | Shared schema | Selected |
| ORM | SQLAlchemy | Selected |
| Migrations | Alembic | Selected |
| Object storage | S3-compatible | Selected approach |
| Large content storage | Object storage | Selected |
| Metadata storage | PostgreSQL | Selected |
| Cross-engine access | Authorized interfaces | Selected |
| Transaction model | Owner-scoped transactions | Selected |
| Concurrency strategy | Optimistic concurrency where appropriate | Selected |
| Deletion | Explicit propagation and verification | Selected |
| Backup and recovery | Controlled backup and restoration strategy | Selected |
| Connection pooling | SQLAlchemy pooling initially | Selected |
| PgBouncer | Workload-dependent | Deferred |
| Database partitioning | Workload-dependent | Deferred |
| Dedicated database per engine | Scaling-dependent | Deferred |

---

# 21. Dependencies

This phase depends on:

- Phase 1 — Overall System Architecture.
- Phase 2 — Memory Engine Architecture.
- Phase 3 — Research Engine Architecture.
- Phase 4 — Agent Orchestrator Architecture.
- Phase 5 — Data Models & Database Design.
- Phase 7.1 — Baseline Technology Stack.

---

# 22. Phase 7.2 Completion Criteria

The specification is complete when:

- Database architecture is defined.
- Schema ownership is documented.
- Cross-engine access rules are defined.
- Relational storage strategy is established.
- Transaction boundaries are defined.
- Indexing principles are documented.
- Connection management is specified.
- Object storage organization is defined.
- Database and object consistency handling is documented.
- Deletion and retention policies are established.
- Backup and recovery requirements are defined.
- Migration principles are documented.
- Security and failure handling are documented.

**Status:** Infrastructure architecture specification documented. No database, storage bucket, migration, index or backup system is claimed to have been implemented or deployed.

---

# 23. Next Subphase

## Phase 7.3 — Vector Search & Embedding Infrastructure

The next document will define:

1. Embedding model selection criteria.
2. Embedding generation architecture.
3. Embedding lifecycle.
4. Vector storage organization.
5. pgvector indexing strategy.
6. Hybrid retrieval.
7. Similarity search.
8. Embedding versioning.
9. Model migration.
10. Vector deletion and recovery.

The objective is to establish a reliable semantic search foundation for Raven's Memory and Research Engines.

---

<!-- Amendment reapplied from commit c49d018. Its text is unchanged except for corrected documentation paths. -->

# Amendment — Document Intelligence and RAG Storage

**File:** `docs/technical-decisions/02-database-and-storage-architecture.md`  
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
