# Phase 7.3 — Vector Search & Embedding Infrastructure

## 1. Purpose

This document defines Raven's vector search and embedding infrastructure.

It establishes how Raven converts textual information into numerical representations, stores those representations, retrieves semantically relevant information, and maintains consistency between source records and their embeddings.

The design covers both:

- **Memory Engine:** Semantic retrieval of personal memories, entities, episodes, and related information.
- **Research Engine:** Semantic retrieval of research findings, evidence, source content, and historical research.

The objective is to improve retrieval quality without treating semantic similarity as proof of factual identity or correctness.

This document defines the architectural direction. Exact embedding models, vector index parameters, and production performance thresholds will be selected through evaluation.

---

## 2. Architectural Principles

Raven's embedding infrastructure follows these principles:

1. Retrieval quality takes priority over raw search speed.
2. Embeddings are derived data, not authoritative records.
3. Original source content must remain available independently of embeddings.
4. Memory and Research retain ownership of their respective embedding data.
5. User isolation must apply to vector retrieval.
6. Similarity scores are signals, not proof of identity or correctness.
7. Vector search must work alongside keyword, metadata, and relationship-based retrieval.
8. Embedding model versions must be traceable.
9. Updates and deletions must propagate to derived vector records.
10. Vector infrastructure must support recovery and re-indexing.
11. Generative LLM APIs and locally hosted generative LLMs are not part of Raven's core processing architecture.

---

## 3. Understanding Embeddings

An embedding is a numerical representation of information.

An embedding model converts text into a vector: a list of numerical values representing semantic characteristics of that text.

For example:

- "I prefer working in the morning."
- "My most productive hours are early in the day."

These sentences use different words but communicate similar ideas. An embedding model may represent them with vectors that are close to one another in vector space.

This allows Raven to retrieve conceptually related information even when the wording differs.

### 3.1 What embeddings are useful for

Embeddings can support:

- Semantic memory retrieval.
- Similar research finding discovery.
- Related document and content-block retrieval.
- Candidate generation for duplicate detection.
- Entity and concept matching.
- Query-to-content matching.

### 3.2 What embeddings cannot establish independently

Embeddings cannot reliably establish:

- Whether two statements refer to the same real-world event.
- Whether a memory is factually correct.
- Whether a research claim is verified.
- Whether two numerical values are comparable.
- Whether two entities are identical.
- Whether a newer statement supersedes an older statement.

These decisions require additional context, evidence, deterministic rules, and domain-specific validation.

**Architectural rule:** Semantic similarity may identify candidates for further evaluation. It must not independently authorize merging, updating, deleting, or promoting authoritative records.

---

## 4. Vector Infrastructure Architecture

Raven will initially use PostgreSQL with pgvector for vector storage and retrieval.

The logical architecture is:

1. Memory Engine and Research Engine generate embedding requests.
2. The embedding pipeline prepares eligible text.
3. A selected embedding model generates vectors.
4. The pipeline validates the generated vectors.
5. Vector records and associated metadata are persisted.
6. pgvector provides similarity search.
7. Engine-specific retrieval algorithms combine vector results with other retrieval signals.
8. The owning engine validates and returns results.

The vector infrastructure is shared at the technical level, but the business data remains separated by engine ownership.

### 4.1 Logical architecture

```text
Memory Engine                    Research Engine
     |                                  |
     v                                  v
Memory Embedding Pipeline       Research Embedding Pipeline
     |                                  |
     +---------------+------------------+
                     |
                     v
              Embedding Model
                     |
                     v
             Vector Validation
                     |
                     v
              Vector Storage
                (pgvector)
                     |
                     v
             Vector Retrieval
                     |
          +----------+----------+
          |                     |
          v                     v
   Memory Retrieval      Research Retrieval
          |                     |
          v                     v
   Memory Results        Research Results
```

This represents logical responsibilities, not a requirement to deploy separate services.

---

## 5. Embedding Model Selection

The exact embedding model is not finalized in this phase.

Raven will evaluate candidate embedding models before selecting a production default.

### 5.1 Selection criteria

Evaluate models using:

- Semantic retrieval quality.
- Performance on short and long text.
- Retrieval quality for conversational language.
- Support for technical terminology.
- Multilingual capabilities where required.
- Embedding dimensionality.
- Inference latency.
- Memory and CPU requirements.
- Deployment and licensing restrictions.
- Model availability and maintenance.
- Reproducibility and version stability.
- Suitability for local or self-hosted inference.

Model selection must be based on Raven-specific evaluation datasets rather than general benchmark rankings alone.

### 5.2 Model configuration

Every embedding model configuration must record:

- Model identifier.
- Model version or immutable revision.
- Embedding dimension.
- Tokenizer or preprocessing configuration.
- Maximum supported input length.
- Normalization behavior.
- Similarity metric compatibility.
- Deployment configuration.
- Creation and activation timestamps.

Model identifiers must not be treated as sufficient version information if the underlying model can change without changing its public name.

### 5.3 Model selection policy

- Use a stable, versioned model configuration.
- Avoid silently changing the model behind an existing identifier.
- Preserve the model version used to generate each vector.
- Evaluate model changes before production activation.
- Do not assume vectors from different models are directly comparable.
- Re-embedding must follow a controlled migration process.

---

## 6. Embedding Generation Pipeline

Embedding generation must follow a controlled processing pipeline.

### 6.1 Processing stages

1. Receive an embedding request from the owning engine.
2. Validate ownership and authorization.
3. Retrieve the eligible source content.
4. Normalize the text without changing its meaning.
5. Apply the appropriate segmentation or chunking strategy.
6. Check model input limits.
7. Generate the embedding.
8. Validate vector dimensions and numerical values.
9. Associate the vector with its source record and model version.
10. Persist vector data and metadata.
11. Update embedding lifecycle status.
12. Record the processing outcome.

### 6.2 Input normalization

Normalization may include:

- Removing irrelevant formatting artifacts.
- Standardizing whitespace.
- Preserving meaningful punctuation.
- Preserving negation.
- Preserving dates, units, and numerical values.
- Preserving important entity names.
- Retaining relevant context.

Normalization must not remove information that changes the meaning of the source.

For example, the following statements must remain distinguishable:

- "I prefer coffee."
- "I do not prefer coffee."

### 6.3 Chunking and segmentation

Long content may need to be divided into smaller segments before embedding.

Chunking decisions must consider:

- Maximum model input length.
- Semantic completeness.
- Context preservation.
- Source structure.
- Retrieval granularity.
- Overlap requirements.

Raven should prefer semantically meaningful segments rather than arbitrary fixed-length text fragments wherever practical.

Every segment must retain a reference to its original source and its position or structural location.

### 6.4 Vector validation

Before persistence, validate:

- Expected vector dimension.
- Finite numerical values.
- No invalid numerical values such as NaN or infinity.
- Model version association.
- Source record association.
- Ownership and access scope.
- Successful generation status.

An invalid vector must not become an active searchable vector record.

---

## 7. Memory Engine Embedding Strategy

The Memory Engine owns memory-related embeddings.

### 7.1 Primary embedding

Each eligible Atomic Memory should have one primary embedding representation.

This is the default semantic retrieval representation for that memory.

The embedding must reference:

- Atomic Memory ID.
- User ownership scope.
- Embedding model and version.
- Vector dimension.
- Source revision or content version.
- Embedding lifecycle status.
- Generation timestamp.

### 7.2 Additional representations

Additional embeddings may be generated selectively when they provide meaningful retrieval value.

Potential examples:

- A memory's concise semantic representation.
- A longer contextual representation.
- A specialized representation for a particular retrieval task.

Additional representations must not be generated indiscriminately.

The Memory Engine's established architecture remains authoritative: one primary embedding with selective additional representations.

### 7.3 Related memory structures

Embeddings may also be generated for eligible:

- Entity descriptions.
- Episode summaries.
- Derived semantic representations.
- Profile information, where justified by retrieval requirements.

These embeddings remain derived records and must reference the underlying authoritative records.

An embedding for a derived profile must not replace the atomic memories from which the profile was generated.

### 7.4 Memory-specific rules

- Important memories receive higher processing priority.
- Routine embedding generation may run asynchronously.
- Explicitly requested important memories should not be silently left without a retrievable representation.
- Memory revisions must trigger embedding freshness evaluation.
- Superseded memories must retain their historical retrieval eligibility according to query context.
- Deleted memories must not remain available through vector search.

---

## 8. Research Engine Embedding Strategy

The Research Engine owns research-related embeddings.

### 8.1 Eligible research content

Embeddings may be generated for:

- Research findings.
- Evidence-bearing content blocks.
- Relevant source excerpts.
- Research session summaries.
- Structured research conclusions, where useful.

Full webpages or complete documents should not automatically be embedded as one large record.

The embedding strategy should support retrieval at a useful evidence level.

### 8.2 Research-specific metadata

Each research embedding should retain references to:

- Research session ID.
- Snapshot ID, where applicable.
- Source ID.
- Finding or content-block ID.
- Publication timestamp, where known.
- Relevant event or effective time, where known.
- Research context.
- Model identifier and version.
- Source ownership and access scope.

### 8.3 Research-specific rules

- Historical and current research must remain distinguishable.
- Updated findings must not silently overwrite historical evidence.
- Embeddings must retain references to the exact research record or snapshot they represent.
- Source reliability and fact confidence must not be replaced by embedding similarity.
- Repeated or syndicated content must not become independent corroboration simply because it has separate vector records.

---

## 9. Vector Storage Design

### 9.1 Initial storage technology

The initial vector storage technology is:

**PostgreSQL + pgvector**

This aligns with Raven's initial database architecture and avoids introducing a dedicated vector database before workload requirements justify it.

### 9.2 Logical separation

Memory and Research vectors must remain logically separated through engine ownership, schema boundaries, access controls, and metadata.

The physical storage design may use separate tables or other appropriately isolated structures.

The exact physical table layout is an implementation-level decision within the established ownership boundaries.

### 9.3 Vector record metadata

A vector record should conceptually contain:

| Field | Purpose |
|---|---|
| `id` | Unique vector record identifier |
| `owner_scope` | Ownership and access boundary |
| `source_record_id` | Reference to the original record |
| `source_record_type` | Type of source record |
| `source_version` | Version of the source content |
| `embedding_model_id` | Model identifier |
| `embedding_model_version` | Immutable model version |
| `embedding_dimension` | Expected vector dimension |
| `embedding_type` | Primary or additional representation |
| `vector` | Numerical embedding |
| `status` | Lifecycle status |
| `created_at` | Generation timestamp |
| `updated_at` | Last update timestamp |

This is a logical record specification, not a finalized SQL schema.

### 9.4 Storage rules

- Vector records are derived from authoritative source records.
- Source references must remain valid.
- Ownership must be enforced at retrieval time.
- Model and source versions must be traceable.
- Invalid or stale vectors must not be treated as current.
- Deleted source records must not remain searchable.
- Vector data must be recoverable from the authoritative source and model configuration where feasible.

---

## 10. Similarity Metrics and Vector Indexing

### 10.1 Similarity metrics

Potential similarity measures include:

- Cosine similarity.
- Dot product.
- Euclidean distance (L2).

The appropriate metric depends on the selected embedding model and its training and normalization characteristics.

Raven must not choose a similarity metric solely because it is commonly used.

The selected model's compatibility and Raven's retrieval evaluation must guide the final choice.

### 10.2 Index selection

pgvector supports different approximate and exact search approaches.

The main candidates for evaluation include:

- HNSW.
- IVFFlat.
- Exact vector search for smaller datasets or reference evaluation.

HNSW is a reasonable initial candidate for evaluation because it can provide efficient approximate nearest-neighbor retrieval.

However, the production index type and parameters must be selected using Raven's own workload and quality measurements.

### 10.3 Index selection criteria

Evaluate:

- Recall at K.
- Query latency.
- Index construction time.
- Index size.
- Insert and update overhead.
- Filtering performance.
- Memory consumption.
- Operational complexity.

Do not sacrifice retrieval quality without measuring the impact.

### 10.4 Index configuration

The following remain configurable or deferred:

- Index type.
- Distance operator.
- HNSW parameters.
- IVFFlat parameters.
- Probe/search settings.
- Vector filtering strategy.
- Index rebuild policy.

No production numerical values are finalized in this document.

---

## 11. Hybrid Retrieval Architecture

Vector search must not become Raven's only retrieval mechanism.

Raven uses hybrid retrieval combining:

1. Vector similarity search.
2. Keyword search.
3. Structured metadata filtering.
4. Temporal filtering.
5. Entity-based retrieval.
6. Relationship-aware retrieval.

### 11.1 Retrieval flow

1. Receive a normalized query.
2. Determine the retrieval context.
3. Apply authorization and ownership filters.
4. Select appropriate retrieval methods.
5. Execute vector and non-vector retrieval.
6. Combine candidate results.
7. Remove invalid, deleted, or inaccessible records.
8. Apply contextual and temporal validation.
9. Rank candidates using engine-specific algorithms.
10. Return evidence-backed results.

### 11.2 Candidate ranking

Vector similarity is one input to ranking.

Other ranking dimensions may include:

- Query relevance.
- Metadata compatibility.
- Temporal relevance.
- Importance.
- Fact confidence.
- Source reliability, for research.
- Freshness.
- Relationship relevance.
- Evidence quality.

These dimensions remain separate and are evaluated according to the owning engine's algorithms.

### 11.3 Similarity is not truth

A high similarity score does not establish:

- Duplicate identity.
- Factual correctness.
- Source reliability.
- Contradiction.
- Supersession.
- Authorization to modify an existing record.

The Memory Engine's resolution algorithms and Research Engine's verification algorithms remain responsible for these decisions.

---

## 12. Embedding Lifecycle Management

Embedding lifecycle must remain synchronized with the lifecycle of the underlying source record.

### 12.1 Creation

When a new eligible record is created:

1. The owning engine determines embedding eligibility.
2. An embedding request is generated.
3. The pipeline processes the source content.
4. The vector is validated.
5. The vector is persisted.
6. The embedding status is updated.

### 12.2 Update

When source content changes:

1. The source record receives a new version.
2. The previous embedding is marked stale or superseded.
3. A new embedding is generated.
4. The new vector is validated and persisted.
5. Search eligibility is updated according to the successful version.
6. The previous version remains available only where historical retrieval policy permits it.

A stale embedding must not silently represent the latest source content.

### 12.3 Deletion

When a source record is deleted:

- Its active vector must become ineligible for retrieval.
- Associated additional embeddings must be identified.
- Search indexes must be updated.
- Cached retrieval results must be invalidated.
- Deletion status must be traceable.
- Backup restoration must reapply applicable deletion records.

Vector deletion is part of the owning engine's deletion workflow, not an independent user-facing operation.

### 12.4 Reconciliation

Periodic or event-driven reconciliation should identify:

- Source records without required embeddings.
- Embeddings with missing source records.
- Stale embeddings.
- Incorrect model versions.
- Invalid vector dimensions.
- Duplicate active vector records.
- Deleted sources with active searchable vectors.

Reconciliation must be idempotent and ownership-safe.

---

## 13. Embedding Model Migration

Changing an embedding model can make existing vectors incompatible with newly generated vectors.

Raven therefore requires a controlled migration process.

### 13.1 Migration stages

1. Register the new model and immutable version.
2. Evaluate it against a representative retrieval dataset.
3. Generate new embeddings without immediately replacing the active version.
4. Validate vector dimensions and metadata.
5. Backfill existing eligible records.
6. Compare retrieval quality between old and new model versions.
7. Validate performance and filtering behavior.
8. Switch retrieval to the new model under controlled configuration.
9. Retain the previous version temporarily for rollback.
10. Retire old vectors only after successful migration and retention checks.

### 13.2 Migration rules

- Never compare incompatible embedding spaces as though they were equivalent.
- Never silently mix incompatible model versions in one ranking space.
- Preserve source-to-vector traceability.
- Support partial migration recovery.
- Avoid blocking all retrieval during backfill.
- Maintain deletion and access-control guarantees throughout migration.

---

## 14. Background Processing and Prioritization

Embedding generation may be immediate or asynchronous depending on the importance and operational requirements of the source record.

### Higher-priority processing

Examples include:

- Explicitly requested important memories.
- Critical source updates.
- User-requested research that requires semantic retrieval.
- Re-embedding required to maintain correctness after a model migration.

### Asynchronous processing

Examples include:

- Routine memory embeddings.
- Large research document backfills.
- Historical content re-indexing.
- Additional optional representations.
- Maintenance and reconciliation jobs.

Priority must not override authorization, deletion, or data-integrity requirements.

A failed embedding job must not be reported as successful merely because the source record was successfully stored.

---

## 15. Failure Handling and Recovery

### 15.1 Model unavailable

- Record the failure.
- Apply bounded retries where appropriate.
- Preserve the source record.
- Keep embedding status distinguishable from source persistence status.
- Use keyword and metadata retrieval where possible.

### 15.2 Invalid embedding

- Reject the vector.
- Preserve the source.
- Record validation failure.
- Retry only when the failure is recoverable.

### 15.3 Vector database unavailable

- Do not falsely report vector persistence.
- Preserve source data.
- Queue recoverable work.
- Use non-vector retrieval where available.
- Reconcile once storage becomes available.

### 15.4 Partial migration failure

- Preserve old active vectors.
- Record migration progress.
- Retry failed records independently.
- Do not activate an incomplete model migration unless explicitly approved by the migration policy.

### 15.5 Stale or orphaned vectors

- Mark invalid records as ineligible.
- Reconcile against authoritative source records.
- Rebuild or remove derived records through the owning engine's controlled workflow.

---

## 16. Privacy and Security

Vector data can reveal information about the original content.

It must receive protections appropriate to the sensitivity of its source.

Requirements:

- Enforce user-level access boundaries.
- Apply authorization filters before returning results.
- Prevent cross-user vector retrieval.
- Do not expose raw vectors through ordinary user-facing APIs.
- Restrict embedding generation to authorized source content.
- Apply deletion and retention rules to vector records.
- Avoid sensitive content in operational logs.
- Protect model configuration and infrastructure credentials.
- Ensure shared canonical data cannot accidentally expose private user associations.

A vector's existence does not grant permission to access its source record.

---

## 17. Evaluation and Performance Metrics

Vector infrastructure must be evaluated using retrieval quality and operational metrics.

### 17.1 Retrieval quality

- Recall@K.
- Precision@K.
- Mean Reciprocal Rank (MRR).
- Normalized Discounted Cumulative Gain (nDCG).
- Relevant-result coverage.
- False-positive candidate rate.

### 17.2 Operational performance

- Embedding generation latency.
- Vector search latency.
- Embedding job success rate.
- Backfill completion rate.
- Index size.
- Storage growth.
- Queue delay.
- Reconciliation failure rate.

### 17.3 Data integrity

- Stale vector rate.
- Orphaned vector rate.
- Missing required embedding rate.
- Invalid vector rate.
- Deletion propagation success.
- Source-to-vector version consistency.

### 17.4 Evaluation policy

Metrics must be measured separately for Memory and Research where their workloads differ.

Numerical targets, benchmark datasets, and acceptance thresholds will be finalized during Phase 12 — Testing & Evaluation.

---

## 18. Finalized Decisions

The following architectural decisions are established:

1. PostgreSQL with pgvector is the initial vector storage technology.
2. Memory and Research retain ownership of their own embeddings.
3. Embeddings are derived data, never authoritative records.
4. Source records remain independently available.
5. Hybrid retrieval combines vector, keyword, metadata, temporal, entity, and relationship signals.
6. Similarity is a candidate-generation and ranking signal, not proof.
7. Model identifiers and versions must be traceable.
8. Embedding generation supports immediate and asynchronous processing.
9. Source updates and deletions trigger controlled embedding lifecycle operations.
10. Model migration uses a controlled backfill and evaluation process.
11. Vector retrieval must enforce ownership and authorization.
12. Keyword and metadata retrieval provide fallback paths when vector search is unavailable.
13. Retrieval quality takes priority over raw speed.
14. No generative LLM APIs or locally hosted generative LLMs are introduced into Raven's core processing architecture.

---

## 19. Deferred Decisions

The following decisions require evaluation or implementation evidence:

- Exact embedding model and immutable revision.
- Embedding dimensionality.
- Model hosting and inference deployment.
- Similarity metric.
- HNSW versus IVFFlat production choice.
- Index parameters.
- Chunk sizes and overlap policies.
- Exact vector table structure.
- Embedding batch sizes.
- Concurrency limits.
- Retrieval thresholds and ranking weights.
- Production latency and quality targets.
- Dedicated vector database adoption, if ever required.

Deferred does not mean unresolved architectural ownership. These decisions must remain consistent with the principles and boundaries defined here.

---

## 20. Completion Criteria

Phase 7.3 is architecturally specified when:

- Embedding responsibilities are defined.
- Memory and Research ownership is clear.
- Model selection criteria are documented.
- Generation and validation pipelines are defined.
- Vector storage architecture is established.
- Hybrid retrieval requirements are documented.
- Lifecycle and migration policies are defined.
- Privacy and deletion requirements are covered.
- Failure handling and evaluation metrics are specified.

**Status:** Architecture specification complete.

**Important:** This document does not claim that embedding models, pgvector tables, indexes, pipelines, or evaluation tests have been implemented or deployed.

---

## 21. Next Phase

**Phase 7.4 — Background Processing & Messaging Infrastructure**

This will define RabbitMQ, Celery, asynchronous job processing, task delivery guarantees, idempotency, retries, scheduling, dead-letter handling, and coordination between Raven's engines and workers.
