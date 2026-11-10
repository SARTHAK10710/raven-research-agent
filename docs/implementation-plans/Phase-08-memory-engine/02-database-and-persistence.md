# Phase 8.2 — Database & Persistence

## 1. Objective

Implement the Memory Engine's database and persistence foundation.

This milestone translates the approved Memory Engine data models into working database models, migrations, repositories, and transaction-management capabilities.

The implementation must preserve:

- Memory Engine data ownership.
- User-level data isolation.
- Referential integrity.
- Provenance.
- Temporal history.
- Version management.
- Controlled updates.
- Deletion lifecycle requirements.
- Idempotency and concurrency safety.

**Implementation location:** `memory-engine/`

**Implementation plan location:** `docs/implementation-plans/phase-08-memory-engine/02-database-and-persistence.md`

---

## 2. Architecture References

Claude Code must read these documents before implementation.

### Data Models

- `docs/data-models/`
- Memory Engine Data Models.
- Core Entities & Relationships.
- Relationships and Lifecycle.
- Shared Infrastructure Data Models.

Pay particular attention to the approved Memory Engine model decisions covering:

- Memory Sources.
- Memory Candidates.
- Atomic Memories.
- Memory Revisions.
- Entities and Aliases.
- Entity Mentions.
- Entity Relationships.
- Memory Relationships.
- Episodes and Episode Memberships.
- Derived Profiles.
- Provenance.
- Embedding Metadata.
- Category Assignments.
- Deletion Operations.
- Processing Events.

### Architecture

- `docs/architecture/`
- Memory Engine ownership and boundaries.
- User isolation.
- Data lifecycle and deletion requirements.

### Algorithms

- `docs/algorithms/memory/`
- `docs/algorithms/shared/`

### Technology

- `docs/technology/01-baseline-technology-stack.md`
- `docs/technology/02-database-and-storage-architecture.md`
- `docs/technology/03-vector-search-and-embedding-infrastructure.md`

### Central Decisions

- `docs/technical-decisions.md`

If any referenced model or decision is missing or ambiguous, report it rather than silently designing a replacement.

---

## 3. Technology Requirements

Use the approved database stack:

| Responsibility | Technology |
|---|---|
| Relational database | PostgreSQL |
| ORM | SQLAlchemy |
| Migration management | Alembic |
| Database validation | Pydantic where appropriate |
| Primary language | Python |
| Testing | pytest |

Use the versions and dependency conventions established in Phase 8.1.

Do not introduce a second ORM or migration framework.

---

## 4. Database Ownership and Boundaries

The Memory Engine owns its authoritative memory-related records.

It must not directly own or modify:

- Research Engine records.
- Orchestrator execution records.
- Shared identity records.
- Shared infrastructure configuration.

Cross-engine access must use approved interfaces and typed references.

### 4.1 Database organization

The approved initial database architecture uses PostgreSQL with logical separation between:

- `memory`
- `research`
- `orchestrator`
- `shared`

The Memory Engine's records must remain within its designated ownership boundary.

Claude Code must inspect the existing database structure before deciding how to initialize or access these schemas.

Do not create duplicate databases or schemas without architectural justification.

### 4.2 Database access

- Use controlled database sessions.
- Use parameterized queries through SQLAlchemy.
- Enforce ownership at the persistence boundary.
- Avoid unrestricted database access from application modules.
- Keep transaction boundaries explicit.
- Do not expose internal database sessions through public engine interfaces.

---

## 5. Database Model Implementation

Implement the approved Memory Engine entities using SQLAlchemy.

The implementation must follow the existing data-model specifications.

### 5.1 Core model groups

**Source and ingestion records**

- Memory Source.
- Source Processing History.

**Memory records**

- Memory Candidate.
- Atomic Memory.
- Memory Revision.
- Memory Category Assignment.
- Memory Correction Request, where required.

**Entity records**

- Entity.
- Entity Alias.
- Entity Mention.
- Entity Resolution History.
- Entity Relationship.

**Memory relationship records**

- Memory Relationship.

**Episodic and profile records**

- Episode.
- Episode Membership.
- Episode Milestone, where required.
- Derived Profile.
- Profile-Memory Association.
- Profile Refresh History.

**Provenance and derived data**

- Provenance Records.
- Embedding Metadata.
- Consolidation Results, where required.

**Lifecycle records**

- Deletion Operation.
- Processing Events.
- Relevant maintenance and reconciliation records.

This inventory must be reconciled against the actual approved data-model documents before implementation.

Do not create a table merely because a concept appears in this list. Follow the exact ownership and persistence decisions in the approved specifications.

### 5.2 Model design requirements

Each model must define appropriate:

- Primary key.
- Foreign keys.
- Ownership scope.
- Required fields.
- Optional fields.
- Data types.
- Constraints.
- Relationships.
- Timestamps.
- Version fields.
- Lifecycle status.
- Index requirements.

Use opaque unique identifiers according to the approved data model conventions.

Do not assume that every entity requires every common metadata field. Apply the model-specific specification.

---

## 6. User Isolation and Ownership

User isolation is a non-negotiable requirement.

### Requirements

1. Private memory records must be scoped to their owner.
2. Queries must enforce ownership.
3. Relationships must not accidentally connect private records across users.
4. Repository methods must validate ownership context.
5. Entity resolution must respect private and shared entity boundaries.
6. Cross-user data access must be rejected.
7. Shared canonical entities must not expose private user associations.
8. Ownership must never be determined from an untrusted request field alone.

### Testing

Create tests that attempt:

- Accessing another user's Atomic Memory.
- Accessing another user's Memory Candidate.
- Linking records belonging to different users.
- Retrieving private entity associations.
- Updating or deleting another user's records.

All unauthorized operations must fail safely.

---

## 7. Relationships and Referential Integrity

Implement the approved relationship structure.

### Requirements

- Foreign keys for appropriate ownership and containment relationships.
- Independent records for complex relationships and history.
- Association records for many-to-many relationships.
- Typed references for cross-engine relationships.
- Appropriate uniqueness constraints.
- Controlled deletion behavior.

### Important distinction

Do not automatically use cascading deletion for every relationship.

Some relationships require coordinated lifecycle processing, historical preservation, or explicit deletion workflows.

Database cascade behavior must not bypass the Memory Engine's deletion architecture.

---

## 8. Temporal and Version Management

The Memory Engine must preserve historical changes.

### 8.1 Versioning

Implement the approved model of:

- Mutable current records where specified.
- Immutable revision history.
- Version identifiers.
- Controlled updates.
- Version conflict detection.

### 8.2 Temporal information

Where required, preserve:

- Valid time: when a fact applies in the real world.
- Transaction time: when Raven recorded or changed the fact.

These are separate concepts.

Do not use database creation timestamps as substitutes for real-world event timestamps.

### 8.3 Historical records

Updates and corrections must not silently erase historical information.

Historical records must remain retrievable according to the approved lifecycle and retrieval policies.

---

## 9. Repository and Persistence Layer

Implement a repository layer for controlled database access.

Repositories should provide domain-oriented persistence operations.

Potential repository boundaries:

- Source Repository.
- Candidate Repository.
- Atomic Memory Repository.
- Revision Repository.
- Entity Repository.
- Relationship Repository.
- Episode Repository.
- Profile Repository.
- Provenance Repository.
- Embedding Metadata Repository.
- Deletion Operation Repository.

The final grouping should follow the actual domain structure and avoid unnecessary fragmentation.

### Repository responsibilities

- Create records.
- Retrieve records.
- Update permitted fields.
- Persist revisions.
- Query by ownership.
- Validate relationship references.
- Handle optimistic concurrency.
- Support transaction-aware operations.

### Repository restrictions

Repositories must not:

- Perform memory extraction.
- Decide whether two facts are duplicates.
- Independently resolve contradictions.
- Generate embeddings.
- Perform final memory ranking.
- Bypass domain validation.

Those responsibilities belong to later milestones.

---

## 10. Transaction Management

Use SQLAlchemy transaction management with PostgreSQL ACID guarantees.

### Requirements

- Keep transactions short.
- Commit related authoritative changes atomically where appropriate.
- Roll back failed transactions.
- Avoid holding transactions open during external operations.
- Avoid holding transactions open during expensive NLP or embedding computation.
- Make retryable operations idempotent.
- Preserve transaction boundaries across repository and service layers.

### 10.1 Optimistic concurrency

Use version-based concurrency protection where required.

If two operations attempt to update the same record:

1. Validate the expected version.
2. Detect a version conflict.
3. Reject stale writes.
4. Reload the current record.
5. Re-evaluate the operation.
6. Apply a new update only after validation.

Never silently overwrite a newer memory revision.

### 10.2 Transaction ownership

Application services should coordinate transactions.

Repositories should participate in the intended transaction rather than independently committing every operation.

---

## 11. Indexing Foundation

Create indexes based on the approved logical indexing strategy.

Potential index categories:

- Primary keys.
- User ownership.
- Record lifecycle status.
- Entity references.
- Temporal fields.
- Relationship lookups.
- Frequently queried metadata.
- Operational reconciliation fields.

### Indexing rules

- Avoid indexing every column.
- Use composite indexes where query patterns justify them.
- Validate uniqueness constraints.
- Consider partial indexes for eligible active records.
- Measure index overhead.
- Document the reason for each non-obvious index.

Vector indexes and embedding generation are covered by later milestones.

Do not implement the complete vector search system here.

---

## 12. Database Migrations

Use Alembic for all database schema changes.

### Requirements

- Initialize or reuse the existing Alembic configuration.
- Establish a clear migration history.
- Use descriptive migration names.
- Review generated migrations.
- Preserve existing data.
- Validate foreign keys and constraints.
- Test fresh database creation.
- Test upgrades from the previous schema.
- Document migration dependencies.

### Migration safety

Never blindly accept autogenerated destructive migrations.

Review:

- Dropped columns.
- Renamed columns.
- Data type changes.
- Foreign key changes.
- Index changes.
- Constraint changes.

Prefer backward-compatible migrations.

Do not claim a migration is reversible unless its downgrade behavior has been verified.

---

## 13. Persistence of Derived Data

Derived data must remain distinguishable from authoritative memory records.

Examples:

- Embedding metadata.
- Derived profiles.
- Semantic consolidation results.
- Search-related metadata.

Requirements:

- Preserve source record references.
- Track generation or processing versions where required.
- Support stale-state detection.
- Allow regeneration when appropriate.
- Avoid treating derived data as the only authoritative copy.

Vector values and pgvector index implementation belong to the vector-related implementation work, not the initial relational persistence scope of this milestone.

---

## 14. Deletion and Retention Compatibility

This milestone must prepare the database for the approved deletion architecture.

Requirements:

- Lifecycle status fields where specified.
- Deletion operation records.
- Referential integrity.
- Identification of dependent records.
- Support for deletion propagation.
- Support for reconciliation.
- Appropriate retention metadata.

Do not implement the full deletion workflow yet.

That belongs to Phase 8.10.

Do not use database cascade deletion as a substitute for coordinated deletion of embeddings, indexes, archives, caches, and backups.

---

## 15. Testing Requirements

### 15.1 Model tests

Test:

- Model construction.
- Required fields.
- Data types.
- Constraints.
- Unique identifiers.
- Foreign keys.
- Relationship integrity.

### 15.2 Repository tests

Test:

- Create operations.
- Read operations.
- Update operations.
- Ownership filtering.
- Version handling.
- Transaction rollback.
- Missing records.
- Invalid references.

### 15.3 Isolation tests

Test cross-user access attempts and unauthorized relationship creation.

### 15.4 Migration tests

Test:

- Fresh database initialization.
- Upgrade from previous schema.
- Migration consistency.
- Constraint creation.
- Index creation.

### 15.5 Concurrency tests

Test:

- Concurrent updates.
- Stale version updates.
- Duplicate operations.
- Transaction conflicts.

### 15.6 Integrity tests

Test that failed persistence does not produce false success and that authoritative records remain consistent.

Use an isolated PostgreSQL test database for integration tests.

SQLite-only tests are not sufficient to validate PostgreSQL-specific behavior.

---

## 16. Expected Deliverables

At completion, the repository should contain:

- SQLAlchemy Memory Engine models.
- Database connection and session management.
- Repository implementations.
- Transaction management conventions.
- Alembic migration configuration.
- Initial database migrations.
- Appropriate indexes and constraints.
- Ownership enforcement.
- Version and temporal support.
- Persistence tests.
- Migration tests.
- Documentation of implemented persistence behavior.

The exact file layout must follow the established `memory-engine/` structure.

---

## 17. Acceptance Criteria

Phase 8.2 is complete only when:

### Database

- [ ] PostgreSQL connection works.
- [ ] SQLAlchemy models represent approved data models.
- [ ] Alembic migrations run successfully.
- [ ] Fresh database initialization works.
- [ ] Foreign keys and constraints are validated.

### Ownership

- [ ] User-level isolation is enforced.
- [ ] Cross-user access tests fail safely.
- [ ] Engine ownership boundaries are preserved.

### Persistence

- [ ] Repositories support required operations.
- [ ] Transactions behave correctly.
- [ ] Failed transactions roll back.
- [ ] Optimistic concurrency is implemented where specified.
- [ ] Historical versions are preserved.

### Quality

- [ ] Repository tests pass.
- [ ] PostgreSQL integration tests pass.
- [ ] Migration tests pass.
- [ ] Relevant linting and type checks pass.
- [ ] No destructive schema behavior is introduced without approval.

### Documentation

- [ ] Implemented models are documented.
- [ ] Migration procedures are documented.
- [ ] Known limitations are reported.

---

## 18. Out of Scope

Do not implement:

- Ingestion algorithms.
- Fact extraction.
- Relevance evaluation.
- Entity resolution algorithms.
- Duplicate detection.
- Contradiction detection.
- Memory ranking.
- Embedding generation.
- Vector indexing.
- Hybrid retrieval.
- Episodic consolidation.
- Profile generation.
- Full forgetting and deletion orchestration.
- Production deployment.

These belong to later milestones.

---

## 19. Claude Code Execution Instructions

1. Inspect the existing database configuration before changing anything.
2. Read the exact approved Memory Engine data models.
3. Reconcile the model inventory against the source documents.
4. Report ambiguities before implementing them.
5. Reuse existing database infrastructure where compatible.
6. Implement only the persistence scope of this milestone.
7. Do not invent additional business entities.
8. Do not modify Research or Orchestrator-owned records directly.
9. Do not introduce another ORM or migration framework.
10. Test using PostgreSQL.
11. Report actual migration and test results.
12. Do not proceed automatically to Phase 8.3.

Any major conflict involving data ownership, deletion, historical preservation, or security must be reported before implementation.

---

## 20. Completion Report

Claude Code must report:

- Files created.
- Files modified.
- SQLAlchemy models implemented.
- Repositories implemented.
- Database constraints and indexes.
- Migrations created and executed.
- Ownership and isolation tests.
- Transaction and concurrency tests.
- PostgreSQL integration test results.
- Linting and type-checking results.
- Known limitations.
- Unresolved issues.
- Acceptance criteria status.

**Status:** Planned.

**Next milestone:** Phase 8.3 — Ingestion Pipeline.
