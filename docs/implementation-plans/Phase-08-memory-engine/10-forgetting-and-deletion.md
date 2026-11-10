# Phase 8.10 — Forgetting & Deletion Implementation Plan

## 1. Objective

Implement the Memory Engine's forgetting and deletion management capabilities.

The deletion system must accept authorized forgetting requests, identify the information affected, determine its dependencies and propagate deletion across authoritative records and derived representations.

It must preserve unrelated memories and prevent deleted information from reappearing through indexes, caches, background jobs or backup restoration.

### Primary objectives

- Process explicit forgetting instructions.
- Support targeted memory deletion.
- Identify related and dependent records.
- Propagate deletion across storage layers.
- Remove or invalidate embeddings and indexes.
- Invalidate affected derived representations.
- Handle asynchronous deletion safely.
- Maintain deletion operation state.
- Prevent deleted information from being reintroduced.
- Support deletion reconciliation.
- Enforce privacy and ownership boundaries.
- Provide verifiable deletion outcomes.

## 2. Architecture references

Claude Code must review:

1. `PROJECT_ARCHITECTURE.md`
2. `docs/architecture/` — Memory Engine architecture.
3. `docs/data-models/` — approved Memory Engine data models.
4. `docs/algorithms/memory/04-memory-consolidation-maintenance.md`
5. `docs/algorithms/memory/02-memory-resolution.md`
6. `docs/algorithms/shared/01-shared-algorithm-framework.md`
7. `docs/technology/02-database-and-storage-architecture.md`
8. `docs/technology/03-vector-search-and-embedding-infrastructure.md`
9. `docs/technology/04-background-processing-and-messaging.md`
10. `docs/technology/06-api-security-and-internal-communication.md`
11. `docs/implementation-plans/phase-08-memory-engine/02-database-and-persistence.md`
12. `docs/implementation-plans/phase-08-memory-engine/07-memory-storage-and-indexing.md`
13. `docs/implementation-plans/phase-08-memory-engine/09-consolidation-and-maintenance.md`

The approved Phase 5 deletion, retention, provenance and lifecycle models are authoritative.

Do not introduce a new deletion architecture or retention policy without identifying the exact gap.

## 3. Scope

### Included

- Explicit forgetting instruction handling.
- Deletion request validation.
- Target identification.
- Ownership and authorization checks.
- Dependency discovery.
- Deletion planning.
- Deletion operation tracking.
- Authoritative memory deletion.
- Revision and candidate cleanup.
- Entity and relationship cleanup.
- Episode and profile invalidation.
- Embedding deletion.
- Vector and keyword index cleanup.
- Cache invalidation.
- Background task cancellation or suppression where appropriate.
- Deletion retries and reconciliation.
- Backup restoration safeguards.
- Deletion verification.
- Security and reliability testing.

### Excluded

- User-facing conversation response generation.
- Global account deletion unless explicitly supported by the approved architecture.
- Legal or regulatory retention policy design.
- Infrastructure-wide backup destruction policy beyond the approved deletion guarantees.
- Document RAG deletion extensions that have not yet been incorporated into the final Phase 8 review.

Document RAG-specific deletion dependencies will be added during the final Phase 8 architecture review.

## 4. Deletion architecture

Implement the following logical components.

### 4.1 Forgetting Request Handler

Responsibilities:

- Receive an explicit forgetting instruction.
- Identify the requested deletion scope.
- Validate the request.
- Verify the authenticated user.
- Resolve the target memory or information reference.
- Create a deletion operation.
- Initiate the deletion workflow.

Forgetting requests must bypass ordinary memory relevance evaluation and extraction.

An explicit forgetting instruction must never be converted into a normal memory candidate.

### 4.2 Deletion Scope Resolver

Determine what information the user intends to forget.

Supported scopes must follow the approved deletion model.

Potential targets include:

- Individual memory.
- Related memory group.
- Specific fact.
- Memory associated with an entity.
- A defined memory collection.

Do not assume that forgetting one fact authorizes deleting every memory associated with the same entity.

For example:

If the user asks Raven to forget their previous project technology, Raven must not automatically delete unrelated project goals, decisions or commitments.

Ambiguous requests must be resolved safely.

Where the target cannot be established reliably, request clarification rather than performing broad deletion.

### 4.3 Dependency Discovery Engine

Identify records and derived representations that depend on the deletion target.

Potential dependencies include:

- Atomic memories.
- Memory revisions.
- Memory candidates.
- Source associations.
- Provenance references.
- Entity mentions.
- Entity relationships.
- Memory relationships.
- Episodes and episode memberships.
- Derived profiles.
- Profile-memory associations.
- Embeddings.
- Vector indexes.
- Keyword indexes.
- Cached retrieval results.
- Pending processing jobs.

The dependency graph must be based on actual stored relationships and approved data models.

Do not delete unrelated information simply because it is connected to the same user or entity.

### 4.4 Deletion Planner

Create a deterministic deletion plan before executing destructive operations.

The plan must identify:

- Target records.
- Dependent records.
- Required cleanup operations.
- Storage locations.
- Indexes and caches affected.
- Background jobs requiring invalidation.
- Operations that can execute independently.
- Operations that require ordering.
- Expected verification checks.

The deletion planner must distinguish authoritative records from derived data.

### 4.5 Deletion Executor

Execute the approved deletion plan.

Responsibilities:

- Remove or invalidate authoritative records according to the approved lifecycle.
- Remove dependent records where required.
- Remove derived representations.
- Propagate deletion to indexes and caches.
- Handle asynchronous cleanup.
- Record operation outcomes.
- Support safe retries.

Deletion must be scoped to the authenticated user's authorized information.

### 4.6 Deletion State Manager

Use the approved Deletion Operation model.

Maintain explicit operation states.

At minimum, the implementation must distinguish:

- Request accepted.
- Deletion planned.
- Deletion in progress.
- Partial failure.
- Reconciliation required.
- Completed.
- Failed.

Use the exact approved status vocabulary where already defined.

Do not introduce conflicting lifecycle states.

### 4.7 Deletion Verification Engine

Verify that deletion has propagated to all required locations.

Verification must consider:

- Authoritative records.
- Historical revisions.
- Candidates.
- Entity associations.
- Derived profiles.
- Episodes.
- Embeddings.
- Vector indexes.
- Keyword indexes.
- Caches.
- Pending processing tasks.
- Applicable object storage references.

A deletion operation must not be reported as fully complete while required cleanup remains unresolved.

## 5. Deletion workflow

Implement the following logical sequence:

1. Receive an explicit forgetting request.
2. Authenticate the requesting user.
3. Validate the deletion request.
4. Resolve the intended deletion scope.
5. Verify ownership of the target.
6. Create a deletion operation record.
7. Identify authoritative target records.
8. Discover dependent records and derived representations.
9. Construct a deletion plan.
10. Validate that the plan does not include unauthorized or unrelated records.
11. Establish the required deletion protection or tombstone.
12. Execute authoritative deletion operations.
13. Propagate deletion to dependent records.
14. Remove or invalidate embeddings and indexes.
15. Invalidate affected episodes and derived profiles.
16. Suppress or cancel pending processing that could reintroduce deleted information.
17. Reconcile incomplete operations.
18. Verify deletion outcomes.
19. Mark the operation complete only when required checks pass.
20. Preserve the minimum permitted deletion-operation audit information.

The workflow must be recoverable after interruption.

## 6. Deletion consistency and ordering

Deletion crosses multiple storage and processing boundaries.

PostgreSQL, object storage, background workers, vector indexes and caches do not share one atomic transaction.

Therefore, implement a controlled multi-stage deletion workflow.

### Required principles

- Create the deletion operation before executing destructive work.
- Persist the deletion protection state.
- Prevent normal retrieval from returning information under deletion.
- Make each cleanup operation idempotent.
- Track completion independently for each required dependency.
- Retry failed operations within bounded limits.
- Support reconciliation after process or worker failure.
- Do not mark deletion complete prematurely.

Use the approved messaging and transaction architecture.

Where appropriate, use transactional outbox patterns for reliable background task publication.

## 7. Tombstones and deletion protection

Implement the approved deletion tombstone strategy.

A tombstone acts as a durable signal that information must remain deleted or excluded.

Requirements:

- Associate tombstones with the correct deletion scope.
- Preserve the minimum identifiers necessary to enforce deletion.
- Prevent deleted records from being reactivated.
- Prevent stale background jobs from recreating deleted information.
- Apply tombstones during backup restoration.
- Support safe reconciliation.

Tombstones must not contain the original sensitive content unnecessarily.

Do not remove deletion protection while dependent cleanup remains incomplete.

## 8. Dependency-specific deletion

### 8.1 Authoritative memories and revisions

Remove or invalidate all memory records within the approved deletion scope.

Ensure historical revisions cannot continue to appear in retrieval results.

### 8.2 Candidates and processing records

Identify pending or unprocessed candidates derived from deleted information.

Prevent them from becoming active memories after deletion.

Preserve only the minimum operational information needed for safe processing and auditing.

### 8.3 Entities and relationships

Remove entity mentions and relationships that are exclusively dependent on deleted information.

Do not automatically delete an entity if unrelated memories still reference it.

### 8.4 Episodes

Re-evaluate episode membership after deleting supporting memories.

Remove or rebuild affected episodes where required.

Do not leave an episode presenting deleted information as current evidence.

### 8.5 Derived profiles

Identify profile attributes supported by deleted memories.

Invalidate affected derived representations and recompute them from remaining valid evidence.

Do not delete unrelated profile attributes.

### 8.6 Embeddings and indexes

Remove affected embedding records.

Update vector indexes.

Update keyword indexes.

Invalidate stale search representations.

Verify that deleted information cannot be retrieved through alternative search paths.

### 8.7 Caches

Invalidate cached results containing deleted information.

Use appropriate invalidation identifiers and versioning.

Do not rely only on cache expiration for explicit deletion.

### 8.8 Object storage

Remove original content objects only when the deletion scope and approved retention policy require it.

Verify that object references are no longer accessible.

Handle storage failures through tracked retries and reconciliation.

## 9. Concurrency and race-condition handling

Deletion must take priority over normal memory creation and indexing when both operations affect the same information.

Consider these scenarios:

- A memory is being updated while deletion is requested.
- An embedding job is running during deletion.
- A stale extraction job attempts to recreate a deleted memory.
- A background consolidation job is processing a target memory.
- A retrieval request begins while deletion is underway.

Required safeguards:

1. Establish deletion protection before dependent cleanup.
2. Check deletion state before committing relevant background work.
3. Prevent stale jobs from reintroducing deleted records.
4. Cancel or invalidate affected jobs where possible.
5. Apply tombstone checks during persistence.
6. Reconcile operations after concurrent changes.
7. Verify the final state.

Deletion must not be defeated by a delayed retry or stale worker.

## 10. Backup and restoration safeguards

Follow the approved Phase 7 backup and recovery architecture.

Deletion protection must survive backup restoration.

Requirements:

- Maintain deletion records or tombstones outside the restoration point where necessary.
- Reapply deletion protection after restoring database backups.
- Reconcile restored records against completed deletion operations.
- Rebuild affected derived indexes only from valid remaining records.
- Prevent deleted information from reappearing after recovery.

The exact backup retention and infrastructure-level destruction policies remain governed by the approved infrastructure and applicable retention requirements.

Do not claim that removing a live database record immediately removes every historical backup copy.

The implementation must clearly document what is and is not covered by the deletion guarantee.

## 11. Failure handling

| Scenario | Expected behavior |
|---|---|
| Ambiguous deletion request | Request clarification |
| Unauthorized target | Deny deletion |
| Target not found | Return a safe not-found result |
| Partial deletion | Record incomplete operation and reconcile |
| Object storage unavailable | Preserve deletion state and retry |
| Vector cleanup failure | Keep deletion incomplete and retry |
| Cache invalidation failure | Record and reconcile |
| Background job running | Cancel or invalidate safely |
| Stale job attempts recreation | Reject using deletion protection |
| Database interruption | Recover from persisted deletion operation |
| Worker interruption | Resume incomplete operations |
| Backup restored | Reapply deletion tombstones |
| Verification failure | Do not report completion |

Do not convert a partial deletion into a successful deletion response.

## 12. Testing requirements

### Unit tests

Test:

- Forgetting request validation.
- Deletion scope resolution.
- Ownership validation.
- Dependency discovery.
- Deletion plan construction.
- Tombstone creation.
- Operation state transitions.
- Idempotent deletion actions.
- Verification logic.

### Component tests

Test:

- Individual memory deletion.
- Related memory deletion.
- Revision deletion.
- Candidate invalidation.
- Entity mention cleanup.
- Relationship cleanup.
- Episode invalidation.
- Profile recomputation.
- Embedding deletion.
- Vector index cleanup.
- Keyword index cleanup.
- Cache invalidation.

### Security tests

Test:

- Cross-user deletion attempts.
- Unauthorized target references.
- Overly broad deletion scopes.
- Tombstone tampering.
- Unauthorized deletion operation access.
- Sensitive information leakage through deletion logs.

### Reliability tests

Test:

- Partial cleanup failures.
- Duplicate deletion requests.
- Concurrent deletion requests.
- Database interruption.
- Object storage interruption.
- Worker restart.
- Delayed background jobs.
- Stale indexing jobs.
- Backup restoration with tombstone reapplication.
- Reconciliation after incomplete operations.

### Critical regression tests

Verify that:

- Deleted information cannot be retrieved.
- Deleted information cannot be reactivated by stale jobs.
- Unrelated memories remain available.
- Historical revisions within the deletion scope are no longer accessible.
- Deletion remains effective after recovery and reindexing.

## 13. Observability and auditability

Record structured deletion events for:

- Forgetting request received.
- Target resolved.
- Deletion plan created.
- Deletion protection established.
- Authoritative records removed.
- Derived data invalidated.
- Index cleanup completed.
- Cache cleanup completed.
- Reconciliation started.
- Verification completed.
- Deletion failed.

Maintain the minimum necessary audit information:

- Deletion operation identifier.
- Authorized owner reference.
- Operation timestamps.
- Scope classification.
- Processing status.
- Cleanup stage outcomes.
- Verification result.

Do not retain deleted source content in deletion audit records.

Do not log sensitive content merely to prove that deletion occurred.

## 14. Acceptance criteria

Phase 8.10 is complete only when:

- [ ] Explicit forgetting requests are recognized.
- [ ] Forgetting bypasses ordinary extraction.
- [ ] Deletion scope is validated.
- [ ] User ownership is enforced.
- [ ] Dependency discovery works.
- [ ] Deletion plans are generated and validated.
- [ ] Deletion operations are tracked.
- [ ] Tombstone or equivalent deletion protection is implemented.
- [ ] Authoritative memories and revisions are handled.
- [ ] Dependent candidates and relationships are handled.
- [ ] Episodes and profiles are invalidated or recomputed.
- [ ] Embeddings and indexes are cleaned up.
- [ ] Caches are invalidated.
- [ ] Pending jobs cannot recreate deleted information.
- [ ] Partial failures can be reconciled.
- [ ] Backup restoration safeguards are implemented.
- [ ] Deletion verification is available.
- [ ] Unrelated memories remain unaffected.
- [ ] Security and reliability tests pass.
- [ ] Deletion completion is never reported prematurely.

## 15. Implementation constraints

Claude Code must:

1. Inspect the repository before modifying files.
2. Reuse Phase 8.1–8.9 implementations.
3. Follow approved Phase 5 deletion models.
4. Follow Phase 6 deletion and lifecycle algorithms.
5. Follow Phase 7 storage and backup decisions.
6. Enforce ownership at every deletion boundary.
7. Treat deletion as a multi-stage recoverable operation.
8. Implement idempotent cleanup.
9. Preserve tombstone protection.
10. Prevent stale jobs from recreating deleted information.
11. Preserve unrelated memories.
12. Avoid claiming complete backup destruction unless the infrastructure actually guarantees it.
13. Avoid generative LLM functionality.
14. Avoid implementing document RAG deletion extensions in this milestone.
15. Place source code inside `memory-engine/`.
16. Place tests inside `tests/`.
17. Do not proceed to Phase 8.11 automatically.

If an approved data model cannot support a required deletion dependency, report the exact gap and recommend the smallest safe change before modifying the architecture.

## 16. Completion report

Claude Code must provide:

1. Summary of deletion functionality.
2. Files created or modified.
3. Deletion models and interfaces used.
4. Deletion scope resolution approach.
5. Dependency discovery implementation.
6. Tombstone implementation.
7. Derived-data cleanup behavior.
8. Background job suppression strategy.
9. Reconciliation and verification behavior.
10. Backup restoration safeguards.
11. Tests executed and exact results.
12. Known limitations.
13. Deviations from approved specifications.
14. Acceptance criteria status.

Clearly distinguish deletion from live systems, deletion from derived indexes and caches, and any backup-retention limitations.

## 17. Definition of done

Phase 8.10 is complete when Raven can safely process an authorized forgetting request, identify and clean up all required dependent representations, prevent deleted information from reappearing, and verify the result without affecting unrelated memories.

**A deletion request is complete only when every required deletion dependency has been accounted for and verified.**
