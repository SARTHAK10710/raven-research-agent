# 8.8 — Memory Retrieval

## 1. Objective

Implement a reliable retrieval system that retrieves relevant personal memories for a given user query or application request.

The retrieval system must identify relevant information from the user's authoritative memory records while preserving:

- User ownership.
- Temporal context.
- Confidence.
- Importance.
- Provenance.
- Historical and current distinctions.
- Entity and relationship context.

This plan covers personal memory retrieval only.

Document retrieval and document-grounded answer generation are separate capabilities implemented under plan 8.12.

## 2. Architecture references

Read:

- `PROJECT_ARCHITECTURE.md`
- `docs/architecture/`
- `docs/data-models/`
- `docs/algorithms/`
- `docs/technology/`
- `docs/technical-decisions.md`
- `docs/implementation-plans/phase-08-memory-engine/05-entity-and-relationship-management.md`
- `docs/implementation-plans/phase-08-memory-engine/06-memory-resolution.md`
- `docs/implementation-plans/phase-08-memory-engine/07-memory-storage-and-indexing.md`
- `docs/implementation-plans/phase-08-memory-engine/12-document-rag-pipeline.md`

Follow the approved retrieval algorithms and data models.

## 3. Retrieval architecture

Implement the following retrieval workflow:

1. Receive a retrieval request.
2. Validate the request and user ownership.
3. Normalize the query.
4. Identify relevant entities, topics, and temporal constraints.
5. Apply metadata and access filters.
6. Retrieve candidate memories using supported retrieval methods.
7. Combine and deduplicate candidate results.
8. Apply relevance and confidence evaluation.
9. Apply temporal and relationship-aware ranking.
10. Select the appropriate results.
11. Attach provenance and retrieval metadata.
12. Return a structured result.

Retrieval must never bypass user ownership or expose another user's memories.

## 4. Retrieval scope

The retrieval system must operate on authoritative personal memory data and the approved associated representations.

Eligible information includes:

- Atomic memories.
- Memory revisions where historical retrieval is appropriate.
- Memory categories.
- Entities and aliases.
- Entity relationships.
- Memory relationships.
- Episodes.
- Derived profiles.
- Memory provenance.
- Approved memory embeddings and keyword indexes.

Do not include document chunks in the personal memory result set by default.

Document chunks must be retrieved through the Document Intelligence pipeline in plan 8.12.

## 5. Query preprocessing

Normalize the retrieval request while preserving its intended meaning.

Where supported, identify:

- Important terms.
- Entities.
- Aliases.
- Topics.
- Temporal expressions.
- Contextual constraints.
- Requested information type.
- Relevant category hints.

Do not over-normalize queries in ways that remove meaningful context.

Preserve the original query for tracing and debugging, subject to privacy requirements.

## 6. Hybrid retrieval

Use the approved hybrid retrieval architecture.

### 6.1 Vector retrieval

Use pgvector to retrieve semantically relevant personal memories.

Vector similarity is a candidate-generation signal.

It is not proof that two memories are identical or that a retrieved statement is true.

### 6.2 Keyword retrieval

Use PostgreSQL full-text search and approved keyword retrieval methods to identify memories containing relevant terms.

Keyword retrieval is useful for exact names, terms, and specific references.

### 6.3 Metadata retrieval

Use structured metadata filters for:

- User ownership.
- Memory categories.
- Entities.
- Temporal constraints.
- Confidence.
- Importance.
- Memory lifecycle status.

### 6.4 Relationship-aware retrieval

Use approved entity and memory relationships to discover related context.

Relationship traversal must respect ownership, relationship validity, and temporal context.

Do not introduce graph database infrastructure for this capability.

## 7. Candidate aggregation and deduplication

Combine results from the available retrieval methods.

The aggregation process must:

- Identify duplicate result references.
- Preserve the strongest available evidence.
- Retain relevant retrieval-method metadata.
- Avoid returning the same memory multiple times.
- Preserve meaningful relationships between separate memories.

Do not merge distinct authoritative memories simply because their content is similar.

Memory resolution remains the responsibility of plan 8.6.

## 8. Ranking and filtering

Use the approved multifactor ranking strategy.

Relevant factors may include:

- Semantic relevance.
- Keyword relevance.
- Entity relevance.
- Context match.
- Importance.
- Confidence.
- Freshness.
- Temporal validity.
- Relationship relevance.
- Query-specific constraints.

Importance and confidence must remain separate.

A highly relevant but low-confidence memory must not be presented as a confirmed fact.

Historical information must not silently replace the current value.

Apply the approved ranking and filtering rules rather than inventing an unrelated scoring system.

## 9. Dynamic Top-K retrieval

Do not always return a fixed number of memories.

Select the result count according to:

- Query complexity.
- Retrieval confidence.
- Relevance distribution.
- Available evidence.
- Context requirements.
- Retrieval budget.

Use iterative retrieval when the initial results are insufficient and additional retrieval is justified.

Stop when:

- Sufficient relevant context has been obtained.
- Additional retrieval produces little value.
- The retrieval budget is exhausted.
- No additional relevant memories are available.

Do not increase retrieval volume merely to produce a larger result.

## 10. Temporal retrieval

Preserve temporal integrity.

Support queries that refer to:

- Current information.
- Historical information.
- Changes over time.
- Previous decisions.
- Past preferences.
- Time-bounded events.
- Progression of goals or projects.

The system must distinguish:

- When information was true.
- When Raven learned the information.
- When the record was created or updated.

Use the approved temporal data model.

Do not treat an old value as current simply because it has a high semantic similarity score.

## 11. Confidence and evidence filtering

Retrieval results must preserve their confidence and provenance.

Distinguish:

- Explicit memories.
- Inferred memories.
- Low-confidence candidates.
- Needs-review information.
- Rejected information.
- Active authoritative memories.
- Historical revisions.

Only records eligible under the approved lifecycle and retrieval policy may be returned as authoritative memory.

Low-confidence information may be returned as qualified context when appropriate, but must not be represented as confirmed fact.

## 12. Retrieval result contract

Return a structured result using the approved interface contract.

A logical result may include:

- Memory identity.
- Relevant content.
- Category.
- Entity references.
- Importance.
- Confidence.
- Explicit or inferred status.
- Temporal context.
- Provenance references.
- Retrieval method.
- Relevance metadata.
- Historical/current status.

Use exact field names and types from the approved data models and contracts.

Do not return internal database credentials, raw storage paths, or unnecessary sensitive metadata.

## 13. Personal memory and document retrieval boundary

Raven has two distinct retrieval domains:

### Personal memory retrieval

Owned by the Memory Engine's personal memory retrieval component.

Retrieves information about the user from authoritative personal memory records.

### Document retrieval

Owned by the Document Intelligence pipeline in plan 8.12.

Retrieves passages from uploaded documents using document-specific indexes and evidence references.

### Coordination

The Agent Orchestrator will determine whether a request needs:

- Personal memory only.
- Document retrieval only.
- Both personal memory and document retrieval.
- Neither, where another approved route is appropriate.

The Memory Engine may expose separate internal capabilities or interfaces for these retrieval domains.

Do not combine their indexes or silently treat document content as user memory.

If a future unified retrieval result contract is required, it must preserve typed source domains and provenance.

## 14. Performance and resource management

Optimize retrieval using measured performance.

Consider:

- Index usage.
- Query latency.
- Candidate count.
- Vector search cost.
- Keyword search cost.
- Relationship traversal cost.
- Database load.
- Retrieval budgets.

Avoid premature introduction of a separate search or vector database.

Maintain predictable retrieval behavior under concurrent requests.

## 15. Failure handling

Handle:

- Empty query.
- Invalid query.
- Unauthorized user.
- Missing indexes.
- Vector search failure.
- Keyword search failure.
- Database unavailability.
- Stale memory representations.
- Conflicting temporal values.
- Low-confidence results.
- Empty result sets.
- Retrieval timeout.

A partial retrieval failure must be represented accurately.

Do not report a complete result when an important retrieval method has failed.

If partial results are returned, include enough status information for the caller to understand their limitations.

## 16. Testing requirements

### Query tests

- Exact name lookup.
- Semantic lookup.
- Keyword lookup.
- Entity-based lookup.
- Category-based lookup.
- Temporal lookup.
- Historical lookup.
- Current-state lookup.
- Multi-entity query.
- Ambiguous query.

### Ranking tests

- Importance and confidence independence.
- Explicit versus inferred information.
- Freshness and temporal validity.
- Duplicate result removal.
- Relationship-aware retrieval.
- Low-confidence filtering.
- Dynamic Top-K behavior.

### Security and isolation tests

- Cross-user retrieval attempt.
- Unauthorized access.
- User-scoped vector search.
- User-scoped keyword search.
- Relationship traversal ownership.
- Historical revision access.

### Domain-boundary tests

- Document chunks do not appear in personal memory retrieval by default.
- Document retrieval remains available through plan 8.12.
- Document evidence is not represented as authoritative personal memory.
- Memory and document result types retain distinct provenance.
- Combined orchestration does not bypass domain-specific authorization.

### Reliability tests

- Vector search failure.
- Keyword search failure.
- Database failure.
- Partial retrieval.
- Timeout.
- Stale index.
- Empty result.
- High-volume candidate set.

## 17. Acceptance criteria

This plan is complete when:

1. Personal memory retrieval works end to end.
2. Hybrid vector, keyword, and metadata retrieval is supported.
3. Entity and relationship context is used appropriately.
4. Candidate aggregation and deduplication work.
5. Ranking preserves importance and confidence distinctions.
6. Temporal integrity is maintained.
7. Dynamic Top-K and retrieval budgets work.
8. Provenance is preserved.
9. User isolation is enforced.
10. Document chunks remain outside personal memory retrieval by default.
11. Failure behavior is tested.
12. Required retrieval quality and integration tests pass.

## 18. Out of scope

This plan does not implement:

- Document parsing.
- Document chunking.
- Document embedding generation.
- Document vector retrieval.
- Document keyword retrieval.
- Document reranking.
- Evidence selection from uploaded documents.
- Document-grounded answer assembly.
- Citation generation and validation.
- Cross-engine orchestration.

These responsibilities belong to plan 8.12 or the later Orchestrator and integration phases.

## 19. Claude Code execution instructions

Before implementation:

1. Inspect the existing retrieval components and repositories.
2. Read the approved retrieval algorithms and data models.
3. Inspect the personal memory and document indexing boundaries.
4. Identify existing vector and keyword search infrastructure.
5. Report any conflicting retrieval contracts or missing decisions.
6. Propose the minimum required implementation changes.

Do not silently combine personal memory and document retrieval.

After implementation, report:

- Files created or modified.
- Retrieval methods implemented.
- Ranking and filtering behavior.
- Provenance handling.
- Domain separation.
- Dependencies added.
- Tests executed and results.
- Acceptance criteria satisfied.
- Known limitations.

Do not automatically proceed to plan 8.9.
