# Phase 5 Amendment — Relationships and Lifecycle

## 1. Purpose

This amendment extends Raven's existing relationship and lifecycle specifications to support Document Intelligence and RAG.

It defines:

- Document entity relationships.
- Document version history.
- Extraction and chunk relationships.
- Embedding and indexing dependencies.
- Document-to-memory provenance.
- Processing lifecycle.
- Deletion propagation.
- Concurrency and recovery requirements.

The existing personal memory lifecycle remains unchanged except where an explicit provenance relationship to document evidence is required.

This amendment does not introduce a new engine or change the ownership boundaries established in Phase 1.

## 2. Ownership boundaries

The Memory Engine owns:

1. Personal memory lifecycle.
2. Document intelligence lifecycle.

These are separate logical domains.

| Domain | Authoritative information |
|---|---|
| Personal memory | Validated memories about the user |
| Document intelligence | Uploaded documents and their derived representations |

The Memory Engine owns both domains, but document content must not automatically become personal memory.

The Research Engine continues to own external research sessions and findings.

The Agent Orchestrator continues to own cross-engine coordination and execution state.

## 3. Document entity relationships

The proposed logical relationship structure is:

```text
Document
   |
   | 1:N
   v
Document Version
   |
   | 1:N
   v
Extracted Representation
   |
   | 1:N
   v
Document Chunk
   |
   | 1:N where required
   v
Chunk Location / Provenance

Document Chunk
   |
   | 1:N where multiple representations are supported
   v
Document Embedding Metadata

Document / Document Version
   |
   | 1:N
   v
Document Processing Operation
```

The exact cardinalities must be reconciled with the existing Phase 5 data models before implementation.

Avoid introducing unnecessary relationships or duplicate entities.

### 3.1 Document → Document Version

One logical document may have multiple versions.

Each version belongs to one document.

Requirements:

- A document has a stable identity.
- Each version has a distinct identity.
- Version ordering is deterministic.
- Historical versions remain distinguishable.
- The current version reference is maintained consistently.
- Version updates do not overwrite historical source content.

A document version must remain independently identifiable even when the original filename remains unchanged.

### 3.2 Document Version → Extracted Representation

A document version may have one or more extracted representations according to the approved extraction and reprocessing policy.

Each representation must identify:

- Its source document version.
- Extraction method.
- Extraction version.
- Processing timestamp.
- Extraction status.
- Relevant structural metadata.

Reprocessing with a different parser or configuration must not silently overwrite the previous extraction result if historical comparison or recovery requires it.

### 3.3 Extracted Representation → Document Chunk

An extracted representation may produce multiple chunks.

Each chunk must identify its source representation and document version.

Requirements:

- Preserve chunk ordering.
- Preserve source text.
- Preserve structural location.
- Preserve chunking strategy and version.
- Preserve content integrity information.
- Support reprocessing without mixing different document versions.

Chunks are derived retrieval units, not authoritative personal memories.

### 3.4 Document Chunk → Chunk Location

A chunk may have one or more source-location references where required.

Location metadata may include:

- Page number.
- Section heading.
- Structural path.
- Character offsets.
- Other format-specific source positions.

Not every format provides every location field.

Missing location information must remain explicitly unavailable.

### 3.5 Document Chunk → Document Embedding

A document chunk may have one or more embedding representations when supported by the approved model and indexing strategy.

Each embedding must identify:

- Source chunk.
- Source document version.
- Model identifier.
- Model version.
- Vector dimensions.
- Preprocessing configuration.
- Creation timestamp.
- Indexing status.

Embedding metadata must not become detached from its source chunk.

### 3.6 Document → Processing Operations

A document or its version may have multiple processing operations.

Examples:

- Validation.
- Parsing.
- OCR, if supported.
- Structure extraction.
- Chunking.
- Embedding.
- Indexing.
- Deletion.

Each operation must be independently traceable and support idempotency.

## 4. Personal memory relationships remain separate

The existing personal memory relationships remain governed by the original Phase 5 specifications.

These include:

- Memory Source → Memory Candidate.
- Memory Candidate → Atomic Memory, through the approved resolution lifecycle.
- Atomic Memory → Memory Revision.
- Entity → Entity Alias.
- Entity → Entity Mention.
- Entity → Entity Relationship.
- Memory → Entity Relationship.
- Memory → Memory Relationship.
- Episode → Episode Membership.
- Derived Profile → Profile-Memory Association.
- Memory → Embedding Metadata.
- Memory → Provenance.

The document amendment must not duplicate or replace these relationships.

## 5. Document-to-memory provenance

A document may contribute evidence to a personal memory when the user explicitly authorizes extraction.

The logical relationship is:

```text
Document
   |
   v
Document Version
   |
   v
Extracted Representation
   |
   v
Document Chunk
   |
   v
Memory Candidate
   |
   v
Memory Resolution
   |
   v
Atomic Memory
```

The relationship between document evidence and a memory candidate must be traceable.

Where the approved provenance model supports it, preserve:

- Document identity.
- Document version.
- Extracted representation.
- Chunk identity.
- Source location.
- Extraction method.
- Evidence reference.

An authoritative memory may have multiple supporting sources.

Document-derived evidence must not bypass memory evaluation or resolution.

### 5.1 Multiple evidence sources

A memory may be supported by:

- A user message.
- Conversation history.
- One document.
- Multiple documents.
- A combination of independent sources.

The provenance model must distinguish the source of each supporting claim.

The existence of multiple references does not automatically mean that they represent independent corroboration.

### 5.2 Document deletion and memory provenance

When a document is deleted, the system must identify memories whose provenance references that document.

The system must distinguish:

1. Memories supported only by the deleted document.
2. Memories supported by the document and independent sources.
3. Memories established independently of the document.

Apply the approved deletion and evidence policy.

Do not automatically delete unrelated memories because they discuss the same subject.

If the existing provenance model cannot support this distinction, document the required schema amendment before implementation.

## 6. Document lifecycle

### 6.1 Document lifecycle

The document lifecycle represents the overall document's availability and deletion state.

Conceptual lifecycle:

```text
Registered
    |
    v
Available
    |
    v
Deletion Requested
    |
    v
Deleting
    |
    v
Deleted
```

A document may also enter a failure or restricted state where supported by the approved lifecycle model.

The document lifecycle must remain distinct from processing status.

A document can be available while some optional derived processing remains incomplete.

### 6.2 Document version lifecycle

A document version has its own processing and indexing state.

Conceptual progression:

```text
Uploaded
   |
   v
Validated
   |
   v
Stored
   |
   v
Parsing
   |
   v
Extracted
   |
   v
Chunked
   |
   v
Embedded
   |
   v
Indexed
```

Possible alternative states:

- Validation failed.
- Extraction failed.
- Retry pending.
- Processing interrupted.
- Indexing incomplete.
- Superseded.
- Deletion requested.
- Deleted.

These are logical states. Exact persisted values must follow the approved data model and workflow contracts.

### 6.3 Processing operation lifecycle

Processing operations must be durable and recoverable.

Conceptual states:

```text
Created
   |
   v
Queued
   |
   v
Running
   |
   +------> Completed
   |
   +------> Failed
   |
   +------> Retry Pending
   |
   +------> Cancellation Requested
                 |
                 v
              Cancelled
```

A retry must not duplicate completed work.

A worker must validate the source document and version before committing its result.

## 7. Version management

Document versioning must preserve historical content and retrieval correctness.

Requirements:

- A new version receives a distinct identifier.
- Historical versions remain distinguishable.
- Extraction output is associated with the correct version.
- Chunks are version-specific.
- Embeddings are version-specific through their source chunk.
- Retrieval results identify the version used.
- Updating a document must not silently change existing citations.
- The current version reference must be updated consistently.

A retrieval result generated from an older version must not be presented as evidence from the latest version.

Historical version retrieval must follow the applicable authorization and retention policy.

## 8. Indexing lifecycle

Document indexing is derived from document extraction and chunking.

Conceptual flow:

```text
Document Chunk
     |
     v
Embedding Generation
     |
     v
Vector Validation
     |
     v
Vector Indexing
     |
     v
Keyword Indexing
     |
     v
Index Verification
```

The system must track indexing status independently from document registration.

A document version must not be reported as fully indexed if required indexing operations remain incomplete.

### 8.1 Index consistency

When a document version or chunk changes:

1. Identify affected representations.
2. Mark stale indexes.
3. Schedule required reprocessing.
4. Regenerate affected embeddings where necessary.
5. Update vector and keyword indexes.
6. Verify consistency.
7. Record completion.

Do not allow stale index results to masquerade as current-version evidence.

### 8.2 Personal memory indexing

Personal memory embeddings and indexes retain their existing lifecycle.

Document indexing must not silently update personal memory embeddings or indexes.

The two domains may share PostgreSQL and pgvector infrastructure while retaining separate logical ownership.

## 9. Deletion lifecycle

Deletion must propagate across the complete dependency graph.

### 9.1 Document deletion

Conceptual dependency chain:

```text
Document
   |
   +---- Document Versions
   |          |
   |          +---- Original Objects
   |          |
   |          +---- Extracted Representations
   |          |             |
   |          |             +---- Document Chunks
   |          |                        |
   |          |                        +---- Chunk Locations
   |          |                        |
   |          |                        +---- Embeddings
   |          |                        |
   |          |                        +---- Vector Indexes
   |          |                        |
   |          |                        +---- Keyword Indexes
   |          |
   |          +---- Processing Operations
   |
   +---- Cached Retrieval Results
   |
   +---- Document-Derived Memory Provenance
```

All applicable dependencies must be discovered before deletion is considered complete.

### 9.2 Memory deletion

Personal memory deletion continues to follow the approved memory dependency model.

Where a memory references document evidence, evaluate the provenance dependency without automatically deleting independent sources or unrelated memories.

### 9.3 Pending operations

Deletion must prevent pending workers from recreating derived artifacts.

Before committing processing results, workers must validate:

- Document lifecycle state.
- Document version.
- Operation state.
- Ownership.
- Relevant deletion state.

Stale operations must be safely rejected or cancelled.

### 9.4 Backup recovery

The deletion model must be compatible with the approved backup architecture.

Maintain durable deletion records or tombstones as required.

After restoration, reapply applicable deletion operations before exposing restored content.

Do not claim physical deletion from retained backups unless the approved retention policy supports that guarantee.

## 10. Concurrency and consistency

Document processing and deletion may run concurrently.

Examples:

- A document is being parsed while deletion is requested.
- An embedding job is running while a document version changes.
- An indexing job finishes after a newer version is uploaded.
- A retrieval request overlaps with document deletion.

Requirements:

- Use approved transaction boundaries.
- Validate source versions before committing derived output.
- Use idempotent operations.
- Detect stale updates.
- Prevent deleted sources from being reintroduced.
- Preserve completed work where appropriate.
- Reconcile partial failures.

Do not hold long-running database transactions open during parsing, embedding, or other lengthy operations.

## 11. Ownership and isolation

Ownership must be enforced across the entire document dependency graph.

The system must validate authorization when accessing:

- Documents.
- Versions.
- Extracted content.
- Chunks.
- Embeddings.
- Retrieval results.
- Processing operations.
- Deletion operations.

Derived artifacts must not become accessible merely because their parent identifiers are known.

Cross-user access must be rejected even when two users upload identical content.

## 12. Data retention and cleanup

Retention policies must distinguish:

- Original documents.
- Historical document versions.
- Extracted content.
- Chunks.
- Embeddings.
- Processing metadata.
- Deletion audit records.
- Backup copies.

Derived data must not outlive its authorized source indefinitely.

Cleanup must respect the approved retention and deletion policies.

Do not introduce automatic deletion based only on document age without an approved retention decision.

## 13. Implementation constraints

Before implementation:

1. Inspect existing Phase 5 relationship definitions.
2. Identify overlapping or already-supported entities.
3. Reconcile proposed document relationships with existing provenance models.
4. Confirm cardinalities.
5. Confirm lifecycle states.
6. Confirm deletion dependencies.
7. Confirm ownership propagation.
8. Update the approved data-model specification.
9. Implement migrations only after schema reconciliation.

Do not silently introduce duplicate relationships or lifecycle fields.

## 14. Acceptance criteria

The relationship and lifecycle model is ready for implementation when:

1. Document identity and version relationships are defined.
2. Extraction and chunk relationships are traceable.
3. Chunk location and provenance are preserved.
4. Embeddings reference the correct source chunk and version.
5. Processing operations support recovery and idempotency.
6. Document and personal memory lifecycles remain separate.
7. Document-derived memory provenance is traceable.
8. Document deletion dependencies are discoverable.
9. Stale processing operations cannot recreate deleted content.
10. Historical versions cannot be confused with current versions.
11. Ownership is enforced across derived artifacts.
12. Backup restoration respects deletion records.
13. The model is consistent with the approved Phase 5 and Phase 7 architecture.

**Final principle:** Every derived document representation must remain traceable to its source version, and every personal memory must remain traceable to the evidence that supports it.
