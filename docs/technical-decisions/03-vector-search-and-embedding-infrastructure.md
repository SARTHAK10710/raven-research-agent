# Amendment — Document Embeddings and Hybrid Retrieval

**File:** `docs/technology/03-vector-search-and-embedding-infrastructure.md`  
**Applies to:** Phase 7.3 — Vector Search and Embedding Infrastructure

## 1. Purpose

Extend Raven's existing vector search and embedding architecture to support document intelligence and Retrieval-Augmented Generation (RAG).

The extension must support:

- Document chunk embeddings.
- Semantic document retrieval.
- Hybrid vector and keyword retrieval.
- Document version-aware indexing.
- Evidence and provenance preservation.
- Independent embedding lifecycle management.
- Document deletion and re-indexing.

This amendment extends the existing pgvector architecture without introducing another vector database.

## 2. Vector Infrastructure

Raven will continue using:

- PostgreSQL as the primary relational database.
- pgvector for vector storage and similarity search.
- PostgreSQL Full-Text Search for keyword retrieval.

A shared PostgreSQL deployment is acceptable, but personal memory and document embeddings must remain logically separate.

The infrastructure may be shared. Ownership, lifecycle and retrieval policies must not be shared indiscriminately.

## 3. Separate Embedding Domains

Raven will maintain two distinct logical embedding domains within the Memory Engine.

### 3.1 Personal Memory Embeddings

These represent validated personal memories.

They support:

- Semantic memory retrieval.
- Similarity-based candidate discovery.
- Entity and relationship-aware retrieval.
- Context selection.
- Memory consolidation workflows.

Memory embeddings must remain associated with their authoritative memory records and revisions.

### 3.2 Document Chunk Embeddings

These represent chunks extracted from uploaded documents.

They support:

- Semantic document search.
- Evidence retrieval.
- Document question answering.
- Relevant passage identification.
- Document comparison.
- Citation generation.

Each document chunk embedding must retain references to:

- Document identifier.
- Document version identifier.
- Chunk identifier.
- Extracted representation identifier, where applicable.
- Embedding model and version.
- Preprocessing version.
- Generation timestamp.
- Indexing status.

### 3.3 Separation Rules

1. Memory embeddings must not be mixed with document chunk embeddings in an unfiltered retrieval operation.
2. Document chunks must not be treated as personal memories.
3. Each embedding must be traceable to its authoritative source.
4. Each embedding domain must have independent indexing and deletion lifecycle management.
5. A shared pgvector deployment must enforce logical separation through schema, metadata, access controls and query filters.
6. A future unified retrieval interface must preserve source type and provenance.

## 4. Embedding Model Selection

Raven will continue evaluating the sentence-transformers ecosystem for embedding generation.

Model selection must consider:

- Semantic retrieval quality.
- Document retrieval quality.
- Memory retrieval quality.
- Embedding dimensions.
- Model size.
- CPU and GPU requirements.
- Inference latency.
- Storage overhead.
- Language support.
- Licensing and deployment restrictions.

A model must be evaluated against Raven-specific datasets before being finalized.

Do not assume that one embedding model is optimal for both memory and document retrieval.

A shared model may be used initially if evaluation demonstrates acceptable quality. Separate models may be introduced when measurable differences justify the additional operational complexity.

## 5. Embedding Metadata and Versioning

Every embedding must preserve sufficient metadata to reproduce or identify its generation process.

Required metadata should include:

- Embedding identifier.
- Source domain.
- Source record identifier.
- Source version identifier, where applicable.
- Model name.
- Model version.
- Embedding dimensions.
- Preprocessing version.
- Normalization configuration.
- Generation timestamp.
- Indexing status.

Document embeddings must additionally preserve document and chunk references.

A change in model or preprocessing configuration must not silently make existing embeddings appear equivalent to newly generated embeddings.

## 6. Document Embedding Pipeline

The document embedding pipeline should follow this sequence:

1. Receive an extracted document representation.
2. Validate document ownership and processing state.
3. Retrieve the approved document version.
4. Load the associated chunks.
5. Validate chunk content and metadata.
6. Normalize content according to the approved preprocessing policy.
7. Generate embeddings.
8. Validate vector dimensions and numerical values.
9. Persist embedding metadata and vector data.
10. Update indexing state.
11. Make successfully indexed chunks eligible for retrieval.

The pipeline must support:

- Idempotent processing.
- Partial failures.
- Retry handling.
- Model version tracking.
- Document version consistency.
- Deletion propagation.
- Re-indexing.

A failed embedding operation must not mark the document as fully indexed.

## 7. Hybrid Retrieval

Document retrieval must combine semantic and lexical search.

### 7.1 Vector Retrieval

Use pgvector to identify semantically relevant document chunks.

Similarity scores should be treated as ranking signals, not proof that a chunk supports an answer.

### 7.2 Keyword Retrieval

Use PostgreSQL Full-Text Search to identify chunks containing relevant terms.

Keyword retrieval is important for:

- Exact names.
- Technical terminology.
- Identifiers.
- Numerical values.
- Dates.
- Product names.
- Domain-specific expressions.

### 7.3 Metadata Filtering

Apply filters for:

- User ownership.
- Document access permissions.
- Document identifier.
- Document version.
- Document type.
- Processing status.
- Other relevant document metadata.

Authorization and ownership constraints must be enforced before results are returned.

### 7.4 Candidate Aggregation

Combine vector and keyword candidates using an evaluated ranking or fusion strategy.

The implementation should:

- Remove duplicate chunk results.
- Preserve retrieval source information.
- Retain document and version references.
- Preserve original similarity and keyword scores.
- Apply access and lifecycle filters.
- Avoid mixing unrelated document versions.

The exact ranking and fusion algorithm will be finalized through evaluation.

## 8. Personal Memory and Document Retrieval

Personal memory retrieval and document retrieval must remain separate operations.

| Personal Memory Retrieval | Document Retrieval |
|---|---|
| Retrieves validated personal memories | Retrieves document chunks |
| Uses memory embeddings | Uses document chunk embeddings |
| Uses memory metadata and relationships | Uses document metadata and structure |
| Returns memory provenance | Returns document and chunk provenance |
| Supports memory context construction | Supports evidence selection and citation |

The Orchestrator may request either or both retrieval domains depending on the user's intent.

A future combined internal result envelope is acceptable only if it preserves:

- Source domain.
- Source identifier.
- Version identity.
- Provenance.
- Confidence or ranking metadata.
- Verification status where applicable.

A document retrieval result must never be silently converted into an authoritative personal memory.

## 9. Reranking

A secondary reranking stage may be evaluated for document retrieval.

Its purpose is to improve the ordering of retrieved chunks based on query relevance.

A reranker must:

- Be evaluated on Raven-specific document retrieval datasets.
- Preserve the original retrieval candidates.
- Avoid modifying source content.
- Preserve document provenance.
- Operate within configured resource budgets.

Reranking is optional and must not become a mandatory dependency without evidence of measurable improvement.

No generative LLM-based reranking is permitted under the existing Raven processing constraint.

## 10. Indexing and Lifecycle Management

Document embedding and indexing state must remain aligned with document versions.

Important cases include:

- New document upload.
- New document version.
- Reprocessing after parser changes.
- Embedding model changes.
- Preprocessing changes.
- Failed embedding generation.
- Partial indexing.
- Document deletion.

When a document version changes, embeddings from an older version must not be silently returned as current-version evidence.

Older versions may remain retrievable when explicitly requested or permitted by the applicable retention policy.

## 11. Model Migration

Embedding model migration must be controlled.

Recommended process:

1. Select and evaluate the replacement model.
2. Record the new model and preprocessing versions.
3. Generate new embeddings without immediately invalidating the old ones.
4. Validate retrieval quality.
5. Compare performance against the existing model.
6. Switch retrieval to the new embedding version after validation.
7. Retain or remove old embeddings according to the migration and retention policy.

Do not mix embeddings from incompatible models or dimensions in a single similarity operation.

## 12. Deletion Propagation

Document deletion must remove or invalidate:

- Document chunk embeddings.
- Associated vector index entries.
- Keyword search entries.
- Cached retrieval results.
- Pending embedding tasks.
- Temporary embedding artifacts.

Personal memory embeddings must not be deleted merely because they discuss the same topic as the deleted document.

Explicitly document-derived memories must follow the established provenance-aware deletion policy.

Deletion must be idempotent and independently verifiable.

## 13. Performance and Index Evaluation

The initial implementation should use pgvector.

Evaluate:

- Exact versus approximate nearest-neighbour search.
- HNSW versus IVFFlat where appropriate.
- Index construction cost.
- Query latency.
- Recall and retrieval quality.
- Memory and document workload interference.
- Filtering performance.
- Storage overhead.
- Concurrent query performance.

Index parameters must be selected using measured workload data rather than assumptions.

A dedicated vector database must remain deferred until measured scale or workload requirements justify it.

## 14. Security and Privacy

Vector retrieval must enforce the same authorization boundaries as the underlying records.

Requirements:

- User-scoped retrieval.
- Document-level access checks.
- No cross-user vector leakage.
- No retrieval of deleted content.
- Secure handling of embedding metadata.
- Controlled model access.
- Sensitive information excluded from unnecessary logs.

Embeddings must be treated as derived user data, not anonymous public data.

## 15. Acceptance Criteria

The vector and embedding architecture is ready for implementation when:

- Personal memory and document embeddings are logically separated.
- Both domains can reuse the existing pgvector infrastructure.
- Document embeddings preserve document version and chunk provenance.
- Embedding model and preprocessing versions are recorded.
- Hybrid vector and keyword retrieval are supported.
- Authorization filters are enforced.
- Indexing is idempotent and recoverable.
- Document version changes cannot silently return stale evidence.
- Deletion propagates to document vectors and indexes.
- Model migration can be performed without uncontrolled mixing of incompatible vectors.
- No unnecessary vector database dependency is introduced.
