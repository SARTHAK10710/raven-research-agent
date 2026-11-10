# Phase 5 — Data Models & Database Design
## File 6: Database Relationships, Consistency, Retention & Migration

**File:** `phase-05-relationships-and-lifecycle.md`  
**Phase:** 5 — Data Models & Database Design  
**Status:** Architecture Finalized  
**Scope:** Phase 5.8, 5.9 and 5.10

---

# 1. Purpose

This document defines how Raven's data entities relate to one another, how data consistency is maintained, and how records evolve throughout their lifecycle.

It covers:

- Database relationships and logical integrity.
- Indexing and retrieval access patterns.
- Transactions and consistency boundaries.
- Concurrency and version management.
- Data retention and deletion.
- Schema evolution and migration.

This document builds on the ownership boundaries and entity models established in the previous Phase 5 documents.

**Important:** This is a logical database architecture. The specific database, vector store, search engine, transaction implementation and migration tooling will be selected during Phase 7.

---

# 2. Phase 5.8 — Database Relationships & Indexing

## Decision 5.8.1 — Logical Relationships Must Preserve Data Ownership

Raven will maintain explicit relationships between entities without transferring ownership between engines.

Examples:

- A Memory Source can be associated with multiple Memory Candidates.
- An Atomic Memory can reference one or more sources.
- An Episode can contain multiple Atomic Memories.
- A Research Finding can reference multiple Evidence Records.
- A Task can depend on multiple other Tasks.
- An Execution can contain multiple Tasks.

The originating engine remains responsible for its authoritative records.

**Rules:**

1. Every relationship must identify the records it connects.
2. Cross-engine references must identify the owning domain.
3. A relationship must not grant write access to another engine's records.
4. Relationship creation and removal must follow the ownership rules of the relevant records.
5. Deletion and updates must account for dependent relationships.

## Decision 5.8.2 — Hybrid Relationship Representation

Raven will use a hybrid relationship model.

**Direct references** will represent simple ownership and containment relationships.

Examples:
- Execution → Tasks.
- Research Session → Snapshots.
- Memory Source → Processing state.

**Independent relationship records** will represent relationships that have their own meaning, history, attributes or lifecycle.

Examples:
- Entity → Entity relationships.
- Atomic Memory → Atomic Memory relationships.
- Profile → Atomic Memory associations.
- Research Session → Research Session relationships.
- Task → Task dependencies.

This avoids creating unnecessary relationship records while preserving important relationship history and metadata.

## Decision 5.8.3 — Referential Integrity

Every reference must resolve to a valid record or an explicitly handled lifecycle state.

Raven must prevent:

- References to nonexistent records.
- Unauthorized cross-user references.
- Relationships that violate domain ownership.
- Accidental access to deleted records.
- Silent loss of important dependencies.

When a referenced record is deleted, dependent records must follow the applicable deletion policy.

A missing or inaccessible reference must never be treated as proof that the original information never existed.

## Decision 5.8.4 — Cross-Engine Reference Integrity

Cross-engine relationships will use the typed reference contract established in Phase 5.3.

Conceptual reference attributes:

- `record_id`
- `owner_domain`
- `record_type`
- `user_scope`
- `version`, where required

The receiving engine must validate the reference and access permissions through the owning engine's authorized interface.

**Important distinction:**

A valid reference identifies a record. It does not authorize access to that record.

Cross-engine references must not bypass user isolation, privacy rules or deletion controls.

## Decision 5.8.5 — Logical Indexing Strategy

Raven will use multiple logical indexing strategies because different data types require different retrieval methods.

| Index category | Purpose |
|---|---|
| Ownership and metadata | Retrieve records by owner, user scope, type and status |
| Temporal | Retrieve records by creation, update and valid-time ranges |
| Relationship | Traverse entity, memory, research and task relationships |
| Keyword | Support exact terms and text-based retrieval |
| Vector | Support semantic similarity retrieval |
| Operational | Retrieve executions, tasks, events and processing states |

These are logical index categories, not commitments to specific database technologies.

Indexing must support the access patterns of each engine rather than forcing every entity into one universal indexing strategy.

## Decision 5.8.6 — User and Ownership Filtering

User isolation must be enforced before or during retrieval, not merely after results are returned.

Every private-data retrieval operation must respect:

- User ownership.
- Record visibility.
- Domain permissions.
- Authorization policies.
- Deletion and retention states.

Shared records must be explicitly classified as shared.

A record without a user identifier must never automatically be considered public.

## Decision 5.8.7 — Hybrid Search and Retrieval

Memory retrieval will combine:

- Vector similarity.
- Metadata filtering.
- Keyword matching.
- Relationship traversal.
- Temporal relevance.

Research retrieval will combine:

- Session and snapshot lookup.
- Source and finding lookup.
- Keyword and metadata search.
- Evidence relationships.
- Attribute and context matching.

The Orchestrator will retrieve execution and task information using identifiers, lifecycle states, dependencies and execution context.

Each engine owns its retrieval logic. The Orchestrator coordinates retrieval but does not independently redefine engine-specific search semantics.

## Decision 5.8.8 — Indexes Are Derived Data

Indexes are not authoritative records.

They must be rebuildable or recoverable from authoritative data and the required source information.

When authoritative data changes:

1. The relevant index must be updated or invalidated.
2. Stale index entries must not silently appear as current.
3. Deletion must propagate to applicable indexes.
4. Failed index updates must be observable and recoverable.
5. Retrieval must respect deletion and authorization state even if an index is temporarily stale.

The exact index-refresh mechanism will be selected during implementation and infrastructure design.

---

# 3. Phase 5.9 — Consistency, Transactions & Versioning

## Decision 5.9.1 — Single Authoritative Owner

Every authoritative business record must have exactly one owning component.

The owner is responsible for:

- Creating the record.
- Updating the record.
- Validating changes.
- Maintaining its lifecycle.
- Managing revisions.
- Enforcing access rules.
- Handling deletion.

Other engines may request operations through authorized interfaces but cannot directly modify the owner's authoritative records.

This is a fundamental Raven data-integrity rule.

## Decision 5.9.2 — Owner-Scoped Transaction Boundaries

Transactions should remain within the ownership boundary of the component performing the operation.

For example:

- Memory operations are controlled by the Memory Engine.
- Research operations are controlled by the Research Engine.
- Execution and task-state operations are controlled by the Orchestrator.
- Identity and infrastructure configuration operations are controlled by Shared Infrastructure.

Raven will not assume that every cross-engine workflow can or should execute as one global database transaction.

When a workflow spans multiple components, it must use coordinated operations with explicit progress, failure handling and recovery.

A partial cross-engine operation must be detectable and recoverable.

## Decision 5.9.3 — Hybrid Consistency Model

Raven will use a hybrid consistency approach.

**Strong consistency is required where correctness or security depends on immediate agreement**, including:

- Authorization decisions.
- User ownership checks.
- Explicit forgetting and deletion access restrictions.
- Critical record ownership changes.
- Sensitive lifecycle transitions.
- Version-conflict validation.

**Eventual consistency is acceptable for derived or operational data**, including:

- Search indexes.
- Embedding refreshes.
- Derived profiles.
- Non-critical analytics.
- Cache refreshes.
- Routine background processing.

Eventual consistency must never weaken privacy, authorization or deletion guarantees.

## Decision 5.9.4 — Optimistic Concurrency by Default

Raven will use optimistic concurrency as its default logical concurrency strategy.

When updating a record:

1. Read its current version.
2. Prepare the update.
3. Verify that the version has not changed.
4. Apply the update and increment the version.
5. If a conflict is detected, reload the latest state.
6. Re-evaluate the intended change before retrying.

Raven must not silently overwrite a newer update with an older one.

Sensitive operations, deletion and other high-risk changes may require stricter coordination.

The exact locking or concurrency mechanism will be decided during implementation.

## Decision 5.9.5 — Versioned Authoritative Records

Records that require historical traceability must preserve their revisions.

This is particularly important for:

- Atomic Memories.
- Memory Candidates when material evaluation changes occur.
- Research Snapshots.
- Research Findings when material corrections occur.
- Derived Profiles.
- Important configuration changes.
- Records with meaningful provenance changes.

A current record represents the latest accepted state.

A revision represents a previous or newly accepted version of that record.

Updates must not erase history when the history is necessary for correction, auditability or temporal interpretation.

Not every operational record requires a complete immutable revision history.

## Decision 5.9.6 — Bitemporal Data Integrity

Where applicable, Raven will preserve two different timelines:

**Valid Time:** When the information was true in the real world.

**Transaction Time:** When Raven learned, recorded or changed the information.

This is important when:

- A user corrects an old memory.
- A preference changes over time.
- A research finding is updated.
- An event is recorded after it occurred.
- A relationship changes historically.

Raven must distinguish between:

- What was believed at a particular time.
- What is currently believed.
- When the underlying information was actually valid.

Bitemporal tracking will be applied where meaningful, not forced onto every operational entity.

## Decision 5.9.7 — Idempotent Operations

Operations that may be retried must be designed to avoid unintended duplicate effects.

Examples:

- Memory ingestion.
- Candidate promotion.
- Embedding generation.
- Research extraction.
- Snapshot creation.
- Task execution.
- Deletion propagation.
- Index updates.

Repeated execution of the same logical operation must not create duplicate authoritative outcomes.

Where appropriate, operations should carry stable identifiers or idempotency keys.

Retries must preserve the original operation context.

## Decision 5.9.8 — Safe Failure and Recovery

A failed operation must not be reported as successfully completed.

Raven must distinguish:

- Successful completion.
- Partial completion.
- Failure.
- Retry in progress.
- Cancellation.
- Unknown outcome requiring reconciliation.

A timeout does not prove that an operation failed.

Before retrying an operation with an uncertain outcome, Raven must reconcile its state using the relevant operation, execution or task identifier.

Recovery must preserve completed work and avoid repeating successful side effects.

## Decision 5.9.9 — Derived Data Consistency

Derived records must preserve references to their authoritative inputs.

Examples include:

- Memory embeddings.
- Derived profiles.
- Consolidated memory representations.
- Research summaries.
- Search indexes.
- Orchestrator context snapshots.
- Cached retrieval results.

When source records change:

1. Identify affected derived records.
2. Determine whether they require refresh or invalidation.
3. Prevent stale derived data from being represented as current.
4. Record failures that prevent successful refresh.
5. Retry or rebuild when safe.

Derived data must never silently override authoritative information.

## Decision 5.9.10 — Cross-Component Coordination

Cross-component workflows must be coordinated through explicit operations and observable state.

For example, deleting a memory may involve:

1. Memory Engine validating the deletion request.
2. Memory Engine marking the affected information inaccessible according to policy.
3. Dependent memory records being identified.
4. Related embeddings and indexes being invalidated or deleted.
5. Applicable cached and derived data being processed.
6. Completion or partial failure being recorded.

The workflow must support retries and reconciliation.

The exact event-delivery, transaction and orchestration mechanisms remain implementation decisions.

---

# 4. Phase 5.10 — Retention, Deletion & Migration

## Decision 5.10.1 — Retention Based on Data Classification

Raven will use the four data lifecycle classes established in Phase 5.1.

| Data class | Retention approach |
|---|---|
| Authoritative | Retained according to domain policy and applicable user or legal requirements |
| Derived | Retained while useful and valid; refreshed or removed when sources change |
| Temporary | Retained only for its operational purpose |
| Cached | Retained for performance; invalidated when stale or unauthorized |

Retention must consider:

- Data sensitivity.
- User expectations.
- Operational usefulness.
- Legal and regulatory requirements.
- Storage cost.
- Deletion obligations.
- Dependencies on other records.

Exact retention periods will be configurable and established during implementation.

## Decision 5.10.2 — Memory Data Retention

Memory data must follow the Memory Engine's lifecycle and forgetting policies.

The Memory Engine may retain:

- Validated Atomic Memories.
- Relevant provenance.
- Entity and relationship records.
- Episodes.
- Derived profiles.
- Required historical revisions.

However, raw source content must not be retained indefinitely by default.

Retention of source content should depend on its purpose, sensitivity, user expectations and applicable policy.

Derived memories must not remain accessible after their required source information has been explicitly forgotten or deleted.

## Decision 5.10.3 — Research Data Retention

Research data will use differentiated retention.

**Normally retained where useful:**

- Research Session metadata.
- Research Snapshot metadata.
- Source URLs and metadata.
- Structured Research Findings.
- Evidence references.
- Relevant excerpts.
- Comparison results.
- Research conclusions.
- Session relationships.

**Temporary by default:**

- Full extracted webpage content.
- Temporary processing files.
- Intermediate extraction outputs.
- Unnecessary raw response data.

Complete source snapshots may be retained selectively when required for reproducibility, verification or an explicit user requirement.

Retention must respect source permissions, privacy and applicable legal requirements.

## Decision 5.10.4 — Temporary Execution Data Retention

The Orchestrator must distinguish durable execution history from temporary execution context.

Temporary data may include:

- Intermediate context snapshots.
- Temporary task payloads.
- Scratch results.
- Temporary files.
- Short-lived processing artifacts.

Execution records, important task transitions and checkpoints may be retained for operational recovery and audit purposes according to policy.

Temporary data must be cleaned up after its purpose ends or its retention period expires.

Cleanup must not remove information required to recover an incomplete execution.

## Decision 5.10.5 — Explicit Forgetting and Deletion

Explicit user forgetting or deletion requests must take priority over ordinary retention and maintenance workflows, subject to applicable legal obligations.

The Memory Engine must identify all affected information, including:

- Atomic Memories.
- Memory Candidates where applicable.
- Episodes.
- Entity relationships.
- Derived profiles.
- Provenance records.
- Embeddings.
- Search indexes.
- Cached results.
- Derived summaries.
- Retained source content where applicable.

Deletion must propagate to all relevant dependent data.

Deleting one memory must not unintentionally delete unrelated memories or independently owned shared records.

## Decision 5.10.6 — Deletion Propagation and Verification

Deletion must be coordinated, idempotent and observable.

The deletion process must:

1. Validate the request and ownership.
2. Identify affected authoritative records.
3. Apply the required access restriction promptly.
4. Identify dependent derived and cached records.
5. Propagate deletion or invalidation.
6. Track outstanding operations.
7. Verify completion where possible.
8. Record failures and support safe retries.

During propagation, records that must no longer be accessible must remain inaccessible even if physical cleanup is still pending.

A deletion operation must not be reported as fully completed while required deletion steps remain unresolved.

## Decision 5.10.7 — Backup Retention and Restoration Safety

Backups must follow a defined retention and recovery policy.

Where backups cannot be immediately modified, Raven must ensure that deleted information is not reintroduced into active systems after restoration.

Restoration procedures must include a deletion-reconciliation step or an equivalent control.

Backup retention must not become a loophole that allows forgotten information to become accessible again.

The exact backup retention period, backup format and deletion mechanism will be finalized during infrastructure design.

## Decision 5.10.8 — Schema Versioning

Raven's data schemas must be versioned.

Schema changes may include:

- Adding fields.
- Removing obsolete fields.
- Changing validation rules.
- Introducing new entity types.
- Changing relationship representations.
- Modifying lifecycle states.
- Updating provenance structures.

Each schema version must have a clearly defined compatibility and migration path.

A schema change must not silently reinterpret existing data.

## Decision 5.10.9 — Controlled Data Migrations

Data migrations must be planned and executed through controlled processes.

A migration should include:

1. Source schema identification.
2. Target schema definition.
3. Transformation rules.
4. Data validation.
5. Referential integrity checks.
6. Ownership and user-scope checks.
7. Migration progress tracking.
8. Failure handling.
9. Reconciliation.
10. Completion verification.

Migrations must preserve provenance, record identity and important historical information wherever applicable.

## Decision 5.10.10 — Backward Compatibility and Rollback

Where practical, schema changes should support a controlled transition between versions.

Raven should prefer migration strategies that allow existing and updated components to coexist temporarily when necessary.

Before a migration:

- Validate the migration plan.
- Identify affected records.
- Establish a recovery point.
- Define expected outcomes.
- Define failure and rollback conditions.

If rollback is unsafe because the migration has introduced irreversible changes, the recovery plan must use a corrective migration or another controlled restoration strategy.

A migration must never be assumed successful merely because the process completed without an execution error.

## Decision 5.10.11 — Migration and Deletion Must Respect Ownership

Migrations must be executed by or under the authority of the component that owns the affected records.

Cross-engine migrations must coordinate with the relevant owners.

Shared Infrastructure may provide migration tooling and operational support, but it does not gain ownership of engine-specific data.

The same ownership rules apply to deletion, backup restoration and data recovery.

---

# 5. Cross-Phase Architectural Invariants

The following principles are mandatory across Raven's data architecture.

1. **Single ownership:** Every authoritative business record has one owner.
2. **User isolation:** Private user data remains isolated.
3. **Reference integrity:** References must resolve or follow an explicit lifecycle policy.
4. **No implicit authorization:** A reference does not grant access.
5. **Provenance:** Important derived information retains source references.
6. **Temporal integrity:** Historical and current information remain distinguishable.
7. **Version integrity:** Important updates must not silently overwrite history.
8. **Idempotency:** Retries must not create unintended duplicate effects.
9. **Deletion integrity:** Forgotten information must not reappear through indexes, caches, derived data or backup restoration.
10. **Derived-data integrity:** Derived records never become more authoritative than their sources.
11. **Recovery:** Partial operations must be observable and reconcilable.
12. **Migration safety:** Schema changes must preserve ownership, provenance and referential integrity.
13. **Privacy:** Logs and operational records must not expose unnecessary sensitive content or secrets.
14. **Auditability:** Important changes and lifecycle transitions must be traceable.

---

# 6. Decisions Deferred to Later Phases

The following are deliberately not finalized in Phase 5.

| Area | Planned phase |
|---|---|
| Database technology selection | Phase 7 |
| Vector database selection | Phase 7 |
| Search infrastructure selection | Phase 7 |
| Physical schema and field types | Implementation design |
| Actual index definitions | Implementation design |
| Transaction implementation | Implementation design |
| Event delivery mechanism | Implementation design |
| Migration tooling | Phase 7 / implementation |
| Backup and disaster recovery infrastructure | Phase 7 / deployment |
| Exact retention durations | Policy and implementation |
| Performance benchmarks | Phase 12–13 |

These decisions must remain consistent with the ownership, consistency, privacy and lifecycle rules finalized here.

---

# 7. Phase 5 Completion Summary

Phase 5 establishes the logical data architecture for Raven.

It defines:

- Overall data architecture.
- Data ownership and boundaries.
- Core entities and relationships.
- Memory Engine data models.
- Research Engine data models.
- Agent Orchestrator data models.
- Shared Infrastructure data models.
- Database relationships and indexing.
- Consistency, transactions and versioning.
- Retention, deletion and migration.

**Phase 5 architectural status: COMPLETE.**

This completion means the logical architecture and data-model decisions are documented. It does not mean database schemas, migrations, indexes, application code or tests have been implemented.

The next phase is:

**Phase 6 — Algorithms & Processing Design**

Phase 6 will translate the finalized architecture into detailed processing logic, algorithms, workflows, edge-case handling and implementation-ready specifications.

---

**End of File 6**
