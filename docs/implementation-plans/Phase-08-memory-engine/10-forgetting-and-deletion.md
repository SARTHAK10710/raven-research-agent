# 8.10 — Forgetting and Deletion

## 1. Objective

Implement a reliable, auditable, and recoverable forgetting and deletion system for the Memory Engine.

The system must support deletion across two separate information domains:

1. Personal memory.
2. Document intelligence.

Deletion must propagate to applicable authoritative records, derived data, indexes, cached representations, and pending processing operations.

The system must preserve ownership boundaries and avoid deleting unrelated information.

## 2. Architecture references

Read:

- `PROJECT_ARCHITECTURE.md`
- `docs/architecture/`
- `docs/data-models/`
- `docs/algorithms/`
- `docs/technical-decisions/`
- `docs/technical-decisions/Readme.md`
- `docs/implementation-plans/Phase-08-memory-engine/02-database-and-persistence.md`
- `docs/implementation-plans/Phase-08-memory-engine/05-entity-and-relationship-management.md`
- `docs/implementation-plans/Phase-08-memory-engine/06-memory-resolution.md`
- `docs/implementation-plans/Phase-08-memory-engine/07-memory-storage-and-indexing.md`
- `docs/implementation-plans/Phase-08-memory-engine/12-document-rag-pipeline.md`

Follow the approved deletion and lifecycle models.

## 3. Deletion principles

The deletion system must follow these principles:

- User ownership must always be verified.
- Deletion must be idempotent.
- Deletion must be traceable.
- Deletion must propagate to applicable derived data.
- Unrelated information must remain intact.
- Partial failures must be recoverable.
- Pending operations must not recreate deleted data.
- Backups must respect approved retention and recovery policies.
- Completion must not be reported before required deletion checks pass.

A deletion request is a high-priority operation and must not be blocked behind ordinary memory extraction or document processing.

## 4. Deletion request types

Support the deletion scopes approved by the data model and API contracts.

Logical deletion requests may include:

### Personal memory

- Delete a specific memory.
- Forget a specific fact.
- Delete a group of related memories.
- Delete an applicable memory source.
- Delete a user's personal memory data within an authorized scope.

### Document intelligence

- Delete a specific document.
- Delete a specific document version where supported.
- Delete document-derived processing artifacts.
- Delete document retrieval representations.
- Delete document-derived personal memories where explicitly included in the deletion request or required by the approved policy.

The exact API contract and supported deletion scopes must follow the approved architecture.

## 5. Deletion lifecycle

Implement deletion as a controlled workflow:

1. Receive the deletion request.
2. Authenticate the requesting user.
3. Validate ownership and authorization.
4. Determine the requested deletion scope.
5. Discover dependent records and derived data.
6. Create or register the deletion operation.
7. Mark the operation as requested or pending.
8. Prevent conflicting new processing.
9. Execute deletion across applicable storage and indexes.
10. Reconcile incomplete operations.
11. Verify deletion completion.
12. Record the final outcome.

Deletion operations must be recoverable after worker interruptions or service failures.

## 6. Personal memory deletion

The deletion dependency graph must account for the approved personal memory models.

Potential dependencies include:

- Authoritative memory records.
- Memory revisions.
- Memory candidates where applicable.
- Source references.
- Provenance.
- Entity mentions.
- Entity relationships.
- Memory relationships.
- Episode membership.
- Derived profiles and associations.
- Memory embeddings.
- Keyword indexes.
- Cached retrieval results.
- Pending memory-processing jobs.

Deleting a memory must not automatically delete unrelated memories simply because they reference the same entity or topic.

Where a derived profile or episode contains information from a deleted memory, apply the approved recomputation or deletion policy.

## 7. Document deletion

Deleting a document must account for the complete document-processing lifecycle.

### 7.1 Original documents

Delete or invalidate applicable:

- Original document objects.
- Document versions.
- Object-storage references.
- Upload artifacts.
- Temporary files.
- Retained copies governed by the document's deletion policy.

The system must verify that the applicable object references are no longer accessible.

### 7.2 Extracted content

Delete applicable:

- Extracted text.
- Structural extraction output.
- Table and layout artifacts.
- OCR output, if generated.
- Temporary parser artifacts.
- Intermediate representations.

Derived content must not remain retrievable after the applicable deletion has completed.

### 7.3 Document chunks

Delete applicable:

- Chunk records.
- Chunk text.
- Chunk metadata.
- Page and section references.
- Chunk ordering records.
- Chunk checksums.
- Version-specific chunk associations.

Do not leave orphaned chunks that can still appear in retrieval results.

### 7.4 Document embeddings and indexes

Delete or invalidate applicable:

- Chunk embeddings.
- Vector index entries.
- Full-text search entries.
- Keyword indexes.
- Cached document retrieval results.
- Cached evidence selections.
- Other derived search representations.

A document deletion must not leave an accessible embedding that can retrieve deleted content.

### 7.5 Pending operations

Cancel or invalidate applicable:

- Parsing jobs.
- OCR jobs.
- Chunking jobs.
- Embedding jobs.
- Indexing jobs.
- Retrieval-related background operations.
- Retry and scheduled processing operations.

A stale worker must not recreate deleted document artifacts after deletion has been requested.

Every worker must validate the applicable document lifecycle state before committing results.

## 8. Document-derived personal memories

Document-derived memories require special handling.

A document may have contributed evidence to an independently persisted personal memory.

Deleting the source document must not silently delete every personal memory that happens to discuss the same topic.

The system must distinguish:

1. Personal memories independently established through user messages or other sources.
2. Personal memories explicitly derived from the document.
3. Memories supported by multiple independent sources.
4. Memories whose only supporting evidence is the deleted document.

Where the provenance model supports it:

- Identify affected memory candidates and authoritative memories.
- Determine whether other valid evidence remains.
- Apply the approved provenance and deletion policy.
- Re-evaluate affected memories when necessary.
- Preserve unrelated independent memories.
- Remove unsupported derived claims when required by the approved policy.

Do not invent automatic deletion behavior where the approved policy is ambiguous. Report the ambiguity and request an architectural decision.

## 9. Deletion across storage systems

The system must account for:

- PostgreSQL records.
- Object storage.
- pgvector.
- Full-text search indexes.
- Cached results.
- Background-processing queues.
- Temporary files.
- Other approved derived stores.

PostgreSQL and object storage do not share a single ACID transaction.

Use the approved multi-stage deletion and reconciliation design.

A failed deletion in one system must not cause the entire operation to be incorrectly marked complete.

## 10. Deletion state and idempotency

Use the approved deletion-operation model and lifecycle.

Conceptual states may include:

- Requested.
- Validating.
- Planned.
- In progress.
- Partially completed.
- Retry required.
- Verification pending.
- Completed.
- Failed.
- Cancelled, where permitted.

Exact persisted state values must follow the approved data model.

Requirements:

- Repeated deletion requests must not cause inconsistent state.
- Retried operations must not recreate deleted records.
- Each dependency must be identifiable.
- Each deletion stage must be traceable.
- A completed operation must have verification evidence.

## 11. Concurrency and stale workers

Deletion must be safe when other operations are running concurrently.

Examples:

- Memory extraction is in progress.
- Document parsing is in progress.
- Embedding generation is in progress.
- A document is being re-uploaded.
- Indexing is in progress.
- A retrieval request is already running.

Requirements:

- Establish the deletion state before allowing conflicting work to commit.
- Use the approved ownership and concurrency controls.
- Validate operation and document or memory versions before committing worker output.
- Cancel pending work where possible.
- Ensure non-interruptible work cannot reintroduce deleted data.
- Make cleanup idempotent.

A worker that finishes after deletion has started must revalidate the source lifecycle before persisting derived data.

## 12. Backup and recovery

Deletion must follow the approved backup and disaster-recovery architecture.

Where immediate physical removal from retained backups is not technically supported:

- Apply the approved backup retention policy.
- Maintain deletion tombstones or equivalent durable deletion records.
- Prevent deleted records from being reintroduced during restore.
- Reapply applicable deletion operations after recovery.
- Verify that restored systems do not expose deleted content.

Do not claim that deletion is complete across every backup copy unless the approved retention and verification process supports that claim.

## 13. Security and privacy

Implement:

- Authentication.
- Ownership validation.
- Authorization for deletion scope.
- Protection against cross-user deletion.
- Secure object deletion.
- Safe operation logging.
- Restricted access to deletion metadata.
- Auditability without unnecessary content retention.

Deletion logs must not unnecessarily preserve the sensitive content that the user asked to delete.

## 14. Observability

Track:

- Deletion request count.
- Deletion scope.
- Processing duration.
- Dependency count.
- Completed stages.
- Failed stages.
- Retry count.
- Verification outcome.
- Stale worker conflicts.
- Orphaned artifact detection.

Use the approved correlation identifiers.

Avoid logging full memory contents or document contents.

## 15. Testing requirements

### Personal memory deletion tests

- Delete one memory.
- Delete a memory with revisions.
- Delete related derived data.
- Delete an applicable source.
- Delete with entity relationships.
- Delete with episode and profile dependencies.
- Delete with multiple provenance sources.
- Duplicate deletion request.
- Cross-user deletion attempt.

### Document deletion tests

- Delete an uploaded document.
- Delete a document with multiple versions.
- Delete original object-storage content.
- Delete extracted text.
- Delete chunks.
- Delete embeddings.
- Delete full-text index entries.
- Invalidate cached retrieval results.
- Cancel pending parsing.
- Cancel pending OCR where supported.
- Cancel pending chunking.
- Cancel pending embedding and indexing.
- Retry after partial deletion.
- Cross-user deletion attempt.

### Document-derived memory tests

- Delete a document whose content produced a candidate.
- Delete a document that supports an active memory.
- Preserve an independently supported memory.
- Re-evaluate a memory with multiple sources.
- Handle a memory supported only by the deleted document.
- Verify that unrelated memories remain intact.

### Reliability tests

- Database unavailable.
- Object storage unavailable.
- Vector index unavailable.
- Worker interruption.
- Concurrent deletion.
- Stale worker completion.
- Repeated deletion.
- Restore with deletion tombstones.
- Partial deletion recovery.
- Verification failure.

## 16. Acceptance criteria

This plan is complete when:

1. Deletion requests are authenticated and authorized.
2. Personal memory deletion propagates across applicable dependencies.
3. Document deletion propagates across originals and derived artifacts.
4. Document embeddings and search indexes are removed or invalidated.
5. Pending jobs cannot recreate deleted content.
6. Document-derived personal memories are handled according to provenance and approved policy.
7. Unrelated personal memories are preserved.
8. Deletion operations are idempotent.
9. Partial failures can be recovered.
10. Backup restoration respects deletion records.
11. Completion is supported by verification evidence.
12. Required privacy, security, and reliability tests pass.

## 17. Out of scope

This plan does not implement:

- General document parsing.
- OCR.
- Chunking.
- Embedding generation.
- Normal document retrieval.
- Memory extraction.
- Full backup infrastructure.
- Cross-engine deletion orchestration beyond the approved Memory Engine interface.

## 18. Claude Code execution instructions

Before implementation:

1. Inspect existing deletion and lifecycle implementations.
2. Read the approved Phase 5 data models and Phase 6 lifecycle algorithms.
3. Inspect object-storage, vector-index, and background-worker integrations.
4. Reconcile document-derived memory provenance and deletion behavior.
5. Identify any unresolved backup, retention, or cross-source deletion policies.
6. Propose the minimum required changes.

Do not silently invent deletion semantics or claim physical deletion from systems that cannot verify it.

After implementation, report:

- Files created or modified.
- Deletion scopes supported.
- Dependency discovery behavior.
- Storage and index cleanup.
- Pending-job handling.
- Backup and recovery behavior.
- Tests executed and results.
- Verification evidence.
- Known limitations.

Do not automatically proceed to plan 8.11.
