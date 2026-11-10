# Phase 5 Amendment — Document Intelligence Data Models

## 1. Purpose

This amendment extends the Memory Engine data model to support document intelligence and Retrieval-Augmented Generation (RAG).

The existing personal memory model remains authoritative for user-related memories.

Document intelligence introduces a separate logical data domain for:

- Uploaded documents.
- Document versions.
- Extracted content.
- Document chunks.
- Chunk provenance.
- Document embeddings.
- Document processing operations.
- Document lifecycle and deletion dependencies.

The amendment must preserve the existing Memory Engine architecture and approved technology decisions.

It does not introduce a new engine or require a separate database deployment.

## 2. Data ownership

The Memory Engine owns both:

1. Personal memory records.
2. Document intelligence records.

However, the two domains must maintain separate logical models and processing lifecycles.

### Personal memory

Represents information about the user, including preferences, goals, decisions, events, relationships, knowledge, projects, and commitments.

### Document intelligence

Represents the content and structure of documents uploaded or authorized by the user.

Document content is not automatically personal memory.

Document chunks must never be treated as atomic memory records.

## 3. Document intelligence entities

The following are proposed logical entities. Their exact names, fields, and relationships must be reconciled with existing Phase 5 conventions before database implementation.

### 3.1 Document

Represents the identity of an uploaded document.

**Responsibilities:**

- Identify a document independently of its filename.
- Associate it with its owner.
- Maintain document-level metadata.
- Reference its current version where applicable.
- Track its lifecycle.
- Support document-level deletion.

**Logical attributes:**

| Attribute | Description |
|---|---|
| Document ID | Stable document identifier |
| User ID | Document owner |
| Title | Human-readable document title |
| Original filename | Uploaded filename |
| Detected media type | Validated file format |
| Created at | Registration timestamp |
| Updated at | Last metadata update |
| Current version ID | Reference to the applicable current version |
| Lifecycle status | Current document lifecycle state |

The document identifier must not depend on the original filename.

### 3.2 Document Version

Represents a specific content version of a document.

**Responsibilities:**

- Preserve historical document versions.
- Identify the exact source used during retrieval.
- Track version-specific extraction and indexing.
- Prevent updated documents from silently replacing historical content.

**Logical attributes:**

| Attribute | Description |
|---|---|
| Document Version ID | Unique version identifier |
| Document ID | Parent document |
| Version number | Version sequence |
| Object reference | Original file storage reference |
| Content checksum | Content integrity identifier |
| File size | Original file size |
| Detected media type | Validated format |
| Uploaded at | Upload timestamp |
| Processing status | Version processing state |
| Created at | Record creation timestamp |

A new upload that represents an update must create a distinct version according to the approved document-version policy.

The system must retain enough information to distinguish historical and current versions.

### 3.3 Extracted Document Representation

Represents content derived from a specific document version.

**Responsibilities:**

- Preserve extracted textual content.
- Preserve structural information.
- Associate extraction output with its source.
- Support downstream chunking.
- Track extraction metadata and failures.

**Logical attributes:**

| Attribute | Description |
|---|---|
| Extraction ID | Unique extraction identifier |
| Document Version ID | Source version |
| Extracted content reference | Text or durable content reference |
| Extraction method | Parser or extraction method |
| Extraction version | Parser or processing version |
| Structure metadata | Available headings, sections, tables, and layout |
| Extraction status | Processing status |
| Extracted at | Extraction timestamp |

Extracted content is derived data. The original uploaded document remains the authoritative source artifact.

The model must not require all extracted content to be stored directly in PostgreSQL if the approved storage architecture calls for object storage.

### 3.4 Document Chunk

Represents a retrieval unit derived from extracted document content.

**Responsibilities:**

- Divide extracted content into retrievable units.
- Preserve source ordering.
- Support vector and keyword retrieval.
- Maintain document-version provenance.
- Support citation generation.

**Logical attributes:**

| Attribute | Description |
|---|---|
| Chunk ID | Unique chunk identifier |
| Document Version ID | Source document version |
| Extraction ID | Source extraction |
| Chunk sequence | Position within the document |
| Content | Chunk text or content reference |
| Content checksum | Chunk integrity identifier |
| Chunking strategy | Strategy identifier |
| Chunking version | Chunking algorithm version |
| Created at | Chunk creation timestamp |

Chunking must preserve the relationship between each chunk and its original document version.

### 3.5 Chunk Location and Provenance

Represents the source location and evidence relationship of a document chunk.

**Responsibilities:**

- Identify where a chunk originated.
- Support page-level citations.
- Support section-level citations.
- Preserve structural location.
- Enable evidence verification.

**Logical attributes:**

| Attribute | Description |
|---|---|
| Location ID | Location record identifier |
| Chunk ID | Associated chunk |
| Document Version ID | Source version |
| Page number | Page reference, when available |
| Section or heading | Structural location |
| Start position | Starting content position, where available |
| End position | Ending content position, where available |
| Structural path | Hierarchical source location, where available |

Not every document format supports page numbers or the same location metadata.

Missing location metadata must remain explicitly unavailable rather than being fabricated.

### 3.6 Document Embedding Metadata

Represents the embedding information associated with a document chunk.

**Responsibilities:**

- Track embedding generation.
- Associate embeddings with the correct chunk and version.
- Support vector indexing.
- Track model and preprocessing versions.
- Support embedding regeneration and deletion.

**Logical attributes:**

| Attribute | Description |
|---|---|
| Embedding ID | Embedding record identifier |
| Chunk ID | Associated document chunk |
| Model identifier | Embedding model |
| Model version | Model version |
| Vector dimensions | Expected vector dimensions |
| Preprocessing version | Text preprocessing configuration |
| Created at | Embedding timestamp |
| Indexing status | Vector indexing state |

Embedding vectors must use the approved pgvector infrastructure initially.

Document embeddings and personal memory embeddings must remain logically distinct.

### 3.7 Document Processing Operation

Represents a processing operation performed on a document or document version.

**Responsibilities:**

- Track processing progress.
- Support retries.
- Record failures.
- Prevent duplicate work.
- Enable recovery.
- Support deletion coordination.

**Logical attributes:**

| Attribute | Description |
|---|---|
| Operation ID | Unique operation identifier |
| Document ID | Associated document |
| Document Version ID | Applicable version |
| Operation type | Parsing, chunking, embedding, indexing, deletion, etc. |
| Operation status | Current processing status |
| Idempotency reference | Retry and duplicate protection |
| Created at | Operation creation time |
| Updated at | Last status update |
| Error metadata | Structured failure information |

Exact operation types and statuses must follow the approved workflow contracts.

## 4. Personal memory model remains separate

The existing personal memory entities remain unchanged unless a separate approved amendment is required.

The document model must not replace or duplicate:

- Memory Source.
- Memory Candidate.
- Atomic Memory.
- Memory Revision.
- Entity.
- Entity Alias.
- Entity Mention.
- Entity Relationship.
- Memory Relationship.
- Episode.
- Episode Membership.
- Derived Profile.
- Profile-Memory Association.
- Memory Provenance.
- Memory Embedding Metadata.
- Category Assignment.
- Deletion Operation.
- Processing History.

The exact existing model names and relationships remain governed by the original Phase 5 specification.

## 5. Document-to-memory provenance

Document content may contribute evidence to a personal memory when the user explicitly authorizes extraction.

The relationship must be traceable.

A document-derived memory candidate must retain references to the relevant:

- Document.
- Document version.
- Extraction.
- Chunk.
- Source location, where available.
- Extraction method.

The exact provenance relationship must be reconciled with the existing Memory Provenance model.

Do not create a separate independent memory lifecycle for document-derived facts.

Document-derived facts must follow the normal workflow:

`Document Evidence → Memory Candidate → Evaluation → Resolution → Authoritative Memory`

Uploading or indexing a document must not automatically create personal memories.

## 6. Embedding domain separation

The system must support two logically separate embedding domains.

### Personal memory embeddings

Represent authoritative personal memory content.

### Document embeddings

Represent document chunks and support document retrieval.

Both domains may share PostgreSQL and pgvector infrastructure.

They must retain independent:

- Source associations.
- Ownership checks.
- Model metadata.
- Indexing status.
- Retrieval rules.
- Deletion dependencies.

Similarity across these domains must not be treated as proof that a document chunk is a personal memory.

## 7. Document lifecycle

A document version may pass through the following logical lifecycle:

`Registered → Validated → Stored → Parsing → Extracted → Chunked → Embedded → Indexed`

It may also enter:

- Failed.
- Retry pending.
- Deletion requested.
- Deleting.
- Deleted.

These states are conceptual and must be reconciled with the existing operation and lifecycle model.

A document must not be marked fully processed if required extraction or indexing operations remain incomplete.

## 8. Relationships

The proposed logical relationships are:

- One Document may have multiple Document Versions.
- One Document Version belongs to one Document.
- One Document Version may have multiple extraction operations or representations, according to the versioning policy.
- One Extracted Representation belongs to a Document Version.
- One Extracted Representation may produce multiple Document Chunks.
- One Document Chunk belongs to one Document Version.
- One Document Chunk may have one or more location references where required.
- One Document Chunk may have associated embedding representations.
- One Document may have multiple processing operations.
- A document-derived Memory Candidate may reference one or more supporting document chunks.
- An authoritative Memory may preserve provenance from its originating candidate and supporting sources.

Relationship cardinality must be confirmed against the existing data model and actual requirements.

Do not create unnecessary many-to-many relationships.

## 9. Deletion dependencies

Document deletion must cover the applicable dependency chain:

`Document → Versions → Original Objects → Extracted Representations → Chunks → Embeddings → Indexes → Caches → Pending Operations`

The system must also identify document-derived memory provenance.

Deleting a document must not automatically delete unrelated personal memories.

Where a memory depends exclusively on deleted evidence, the approved deletion and provenance policy must determine the appropriate action.

Deletion must be recoverable and idempotent.

## 10. Security and ownership

Every document and derived document representation must remain scoped to its authorized owner.

Ownership must propagate through:

- Document.
- Document Version.
- Extracted Representation.
- Document Chunk.
- Chunk Embedding.
- Processing Operation.
- Retrieval Result.

Do not rely only on client-provided identifiers for authorization.

Validate access through the approved ownership model.

Document content must be treated as untrusted input.

## 11. Storage strategy

Follow the approved Phase 7 storage architecture.

- PostgreSQL stores authoritative metadata and relational records.
- S3-compatible object storage stores original documents and large content artifacts where appropriate.
- pgvector stores approved vector representations.
- PostgreSQL full-text search supports keyword retrieval.

Do not introduce a separate document database or vector database as part of this amendment.

## 12. Schema implementation rules

Before implementing these logical entities:

1. Inspect existing Phase 5 data-model documents.
2. Identify any existing models that already support the proposed responsibilities.
3. Reuse existing models where appropriate.
4. Avoid duplicate entities.
5. Confirm relationship cardinality.
6. Confirm ownership enforcement.
7. Confirm lifecycle and deletion dependencies.
8. Update the approved data-model documentation.
9. Only then implement database migrations.

This amendment does not claim that these entities already exist in the database.

## 13. Acceptance criteria

The document intelligence data model is ready for implementation when:

1. Document identity is independent of filenames.
2. Document versions preserve historical content references.
3. Extracted content retains source-version provenance.
4. Document chunks retain source and location references.
5. Document embedding metadata is version-aware.
6. Processing operations support idempotency and recovery.
7. Document and personal memory models remain separate.
8. Document-derived memory provenance is traceable.
9. Deletion dependencies are discoverable.
10. User ownership is enforced throughout the model.
11. The model is consistent with the approved PostgreSQL and pgvector architecture.
12. All schema decisions are reconciled with the existing Phase 5 specification.

**Final principle:** Documents represent source material. Personal memories represent validated information about the user. Raven must preserve this distinction throughout the data lifecycle.
