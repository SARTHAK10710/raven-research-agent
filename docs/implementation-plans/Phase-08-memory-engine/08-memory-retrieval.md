# Phase 8.8 — Memory Retrieval Implementation Plan

## 1. Objective

Implement the Memory Engine's retrieval system.

The retrieval system receives a query and retrieves relevant authoritative memories using the approved hybrid retrieval architecture.

It must consider semantic relevance, keyword relevance, metadata, entities, relationships, temporal context, importance, confidence and evidence quality.

### Primary objectives

- Understand retrieval requests.
- Perform hybrid memory search.
- Apply ownership and metadata filters.
- Retrieve relevant entities and relationships.
- Rank candidate memories.
- Apply confidence and evidence filtering.
- Support dynamic Top-K selection.
- Support iterative retrieval.
- Enforce retrieval budgets.
- Return provenance-aware results.
- Preserve historical versus current context.
- Provide measurable retrieval quality.

## 2. Architecture references

Claude Code must review:

1. `PROJECT_ARCHITECTURE.md`
2. `docs/architecture/` — Memory Engine architecture.
3. `docs/data-models/` — approved Memory Engine data models.
4. `docs/algorithms/memory/03-memory-retrieval.md`
5. `docs/algorithms/shared/01-shared-algorithm-framework.md`
6. `docs/technology/01-baseline-technology-stack.md`
7. `docs/technology/02-database-and-storage-architecture.md`
8. `docs/technology/03-vector-search-and-embedding-infrastructure.md`
9. `docs/technology/05-nlp-and-machine-learning-stack.md`
10. `docs/implementation-plans/phase-08-memory-engine/06-memory-resolution.md`
11. `docs/implementation-plans/phase-08-memory-engine/07-memory-storage-and-indexing.md`

The approved retrieval algorithms and data models are authoritative.

## 3. Scope

### Included

- Retrieval request validation.
- Query preprocessing.
- Hybrid retrieval.
- Vector similarity search.
- Keyword retrieval.
- Metadata filtering.
- Entity-aware retrieval.
- Relationship-aware retrieval.
- Temporal filtering.
- Candidate aggregation and deduplication.
- Relevance ranking.
- Confidence and evidence filtering.
- Dynamic Top-K selection.
- Iterative retrieval.
- Retrieval budgets.
- Provenance-aware result construction.
- Retrieval quality evaluation.

### Excluded

- Memory consolidation.
- Profile generation.
- Forgetting and deletion execution.
- Agent orchestration.
- User-facing conversational response generation.
- Document RAG and document chunk retrieval.

Document RAG additions remain deferred until the final Phase 8 review.

## 4. Retrieval architecture

Implement the following logical components.

### 4.1 Retrieval Interface

Responsibilities:

- Accept retrieval requests from authorized internal callers.
- Validate query and context information.
- Pass requests to the retrieval application service.
- Return structured retrieval results.

The interface must not independently implement ranking or memory business logic.

### 4.2 Query Preprocessor

Responsibilities:

- Normalize query text.
- Identify useful keywords.
- Extract available entities and attributes.
- Preserve negation and qualifiers.
- Identify temporal constraints.
- Prepare query representations for hybrid retrieval.

Do not alter the meaning of the original query.

### 4.3 Retrieval Context Manager

Prepare retrieval context using available information.

Potential context includes:

- User identity.
- Current task or execution reference.
- Relevant entities.
- Project context.
- Time constraints.
- Memory categories.
- Historical or current information requirements.
- Explicit retrieval filters.

Context must be selectively applied.

Do not retrieve unrelated personal information merely because it exists.

### 4.4 Vector Retrieval

Use pgvector to retrieve semantically similar memories.

Responsibilities:

- Generate or obtain a query embedding.
- Search the approved embedding index.
- Apply relevant metadata and ownership filters.
- Return similarity information.
- Preserve memory and revision references.

Use the approved embedding model and preprocessing configuration.

Do not assume vector similarity proves factual relevance.

### 4.5 Keyword Retrieval

Use PostgreSQL full-text search to identify relevant memories through lexical matching.

Responsibilities:

- Search normalized memory content.
- Identify exact and partial keyword matches.
- Apply ownership and metadata filters.
- Return keyword relevance information.

Keyword retrieval is particularly useful for names, identifiers, technologies and exact phrases.

### 4.6 Metadata Retrieval

Support structured filtering using approved memory metadata.

Potential filters include:

- User ownership.
- Memory category.
- Importance.
- Confidence.
- Lifecycle state.
- Entity association.
- Source reference.
- Temporal validity.
- Creation and update timestamps.

Only retrieve memories accessible to the requesting user.

### 4.7 Entity and Relationship Retrieval

Use the approved entity and relationship models to identify contextual memories.

Examples:

A query about Raven may retrieve memories associated with:

- Raven as a project.
- Its technology stack.
- Related decisions.
- Associated commitments.
- Previous development milestones.

Entity relationships should expand retrieval only when they improve query relevance.

Avoid unrestricted graph traversal.

### 4.8 Candidate Aggregator

Combine retrieval candidates from the different retrieval methods.

Responsibilities:

- Merge candidate result sets.
- Deduplicate repeated memory references.
- Preserve retrieval signals.
- Preserve source and revision references.
- Apply eligibility filters.
- Prepare candidates for ranking.

Do not discard useful provenance while combining results.

## 5. Hybrid retrieval strategy

Implement the approved hybrid retrieval approach:

1. Vector retrieval.
2. Keyword retrieval.
3. Metadata filtering.
4. Entity and relationship retrieval.
5. Candidate aggregation.
6. Relevance ranking.

The implementation must not depend exclusively on vector search.

Different query types may benefit from different retrieval signals.

For example:

- Conceptual questions may benefit more from semantic retrieval.
- Exact project identifiers may benefit more from keyword retrieval.
- Time-specific questions may require metadata filtering.
- Relationship questions may require entity context.

The retrieval system should support configurable weighting based on evaluation.

Do not hardcode arbitrary weights without documenting their rationale and evaluating them against representative datasets.

## 6. Candidate eligibility and filtering

Before ranking, apply the required eligibility rules.

### Ownership

Only retrieve memories belonging to the authorized user.

### Lifecycle state

Exclude rejected, deleted or otherwise ineligible memories.

Use the approved lifecycle definitions.

### Confidence

Consider confidence and evidence quality when determining whether a memory can support an answer.

Low-confidence memories may be retained as contextual evidence but must not be presented as established facts.

### Temporal context

Distinguish:

- Current information.
- Historical information.
- Future plans.
- Expired or superseded information.
- Information with unknown temporal validity.

Do not assume that the newest observation always replaces an older historical fact.

### Evidence

Preserve the source references supporting retrieved memories.

Do not present unsupported derived information as verified.

## 7. Relevance ranking

Implement a ranking system using the approved retrieval algorithm.

Consider:

- Semantic similarity.
- Keyword relevance.
- Metadata match.
- Entity relevance.
- Relationship relevance.
- Importance.
- Confidence.
- Evidence quality.
- Temporal relevance.
- Freshness where appropriate.

Importance, confidence and relevance must remain separate concepts.

A highly important memory is not automatically relevant to every query.

A high-confidence memory is not automatically relevant either.

The ranking system must evaluate the complete retrieval context.

### Ranking requirements

- Use normalized or appropriately comparable retrieval signals.
- Avoid double-counting correlated signals.
- Preserve ranking explanations or contributing signals where practical.
- Support configurable ranking parameters.
- Make ranking deterministic where equivalent inputs and configuration are supplied.

## 8. Dynamic Top-K selection

Implement adaptive selection of the number of memories returned.

The system must not rely on one fixed Top-K value for every query.

Consider:

- Query complexity.
- Retrieval confidence.
- Candidate relevance distribution.
- Evidence diversity.
- Available retrieval budget.
- Whether additional results are likely to improve the answer.

Requirements:

- Set a configurable maximum result limit.
- Support a minimum useful result threshold.
- Avoid returning irrelevant memories merely to fill the result limit.
- Allow smaller result sets for simple queries.
- Allow broader result sets for complex queries.
- Preserve the reason for early stopping where practical.

Exact thresholds must be evaluated using representative retrieval datasets.

## 9. Iterative retrieval

Support controlled iterative retrieval when the initial result set is insufficient.

Example workflow:

1. Execute initial hybrid retrieval.
2. Evaluate result relevance and coverage.
3. Identify missing context.
4. Refine search terms or metadata filters.
5. Execute a bounded additional retrieval pass.
6. Merge and rerank results.
7. Stop when sufficient evidence is available or the budget is exhausted.

Iteration must be bounded.

Do not repeatedly execute equivalent searches without a meaningful refinement.

Preserve the original query and retrieval history for observability.

## 10. Retrieval budgets

Every retrieval request must operate within configurable resource limits.

Consider:

- Maximum retrieval iterations.
- Maximum candidate count.
- Maximum database queries.
- Maximum execution time.
- Embedding generation cost.
- Maximum returned result count.

Use early stopping when additional retrieval is unlikely to improve the result.

Budget exhaustion must produce a clear partial-result status rather than silently pretending retrieval was exhaustive.

## 11. Retrieval result contract

Return a structured retrieval result containing the approved model fields.

The logical output should preserve:

- Retrieval request identifier.
- User reference.
- Query reference.
- Retrieved memory identifiers.
- Relevant revision identifiers.
- Ranked relevance information.
- Confidence and evidence information.
- Source provenance.
- Temporal context.
- Entity references where relevant.
- Retrieval method information.
- Completion or partial-result status.

Claude Code must reconcile this contract with the approved Phase 5 data models and existing application interfaces.

Do not introduce a duplicate result model if an equivalent one already exists.

## 12. Historical and current memory handling

Retrieval must preserve temporal distinctions.

Examples:

Question:
"What technology is Raven currently using?"

Expected behavior:

Prefer the current authoritative information while accounting for superseded historical records.

Question:
"What technology did Raven originally use?"

Expected behavior:

Retrieve the relevant historical revision rather than returning only the current state.

Question:
"How has Raven's technology stack changed?"

Expected behavior:

Retrieve the relevant sequence of historical states and their temporal relationships.

Do not flatten a changing fact into one timeless value.

## 13. Failure handling

| Scenario | Expected behavior |
|---|---|
| Empty query | Reject with validation error |
| Query embedding failure | Use an approved fallback retrieval method where possible |
| Vector search unavailable | Continue with keyword and metadata retrieval where safe |
| Keyword search unavailable | Continue with other supported retrieval methods |
| No matching memories | Return an empty result with clear status |
| Low-confidence candidates | Preserve uncertainty or filter according to policy |
| Conflicting memories | Preserve conflicting evidence and temporal context |
| Database interruption | Return a controlled retrieval failure |
| Iteration budget exhausted | Return partial results with explicit status |
| Unauthorized user | Deny retrieval |
| Stale embedding | Exclude or handle according to approved consistency policy |

Partial retrieval must never be represented as exhaustive retrieval.

## 14. Testing requirements

### Unit tests

Test:

- Query preprocessing.
- Context filtering.
- Metadata filtering.
- Vector retrieval interface.
- Keyword retrieval interface.
- Candidate aggregation.
- Deduplication.
- Relevance ranking.
- Confidence filtering.
- Temporal filtering.
- Dynamic Top-K selection.
- Iterative retrieval.
- Budget enforcement.

### Component tests

Test:

- End-to-end hybrid retrieval.
- Entity-aware retrieval.
- Relationship-aware retrieval.
- Historical memory retrieval.
- Current memory retrieval.
- Result construction.
- Provenance preservation.

### Integration tests

Test:

- PostgreSQL full-text search.
- pgvector search.
- Metadata filtering.
- Combined retrieval queries.
- Ownership enforcement.
- Embedding model integration.

### Quality evaluation

Build representative query datasets covering:

- Exact fact retrieval.
- Semantic paraphrases.
- Project-specific queries.
- Preference retrieval.
- Historical queries.
- Current-state queries.
- Relationship queries.
- Multi-part questions.
- Ambiguous queries.
- Contradictory evidence.
- Queries with no relevant memories.

Evaluate:

- Precision@K.
- Recall@K.
- Mean Reciprocal Rank.
- nDCG@K.
- Retrieval latency.
- Evidence coverage.
- Temporal correctness.
- Unauthorized retrieval prevention.

Do not claim retrieval quality is production-ready solely because the implementation passes unit tests.

## 15. Observability

Record structured events for:

- Retrieval started.
- Query preprocessing completed.
- Vector retrieval completed.
- Keyword retrieval completed.
- Candidate aggregation completed.
- Ranking completed.
- Iteration started.
- Early stopping triggered.
- Budget exhausted.
- Retrieval completed.
- Retrieval failed.

Track:

- Retrieval latency.
- Candidate count.
- Results returned.
- Precision and recall from evaluation.
- Empty-result rate.
- Iteration count.
- Budget exhaustion rate.
- Vector and keyword retrieval failures.
- Retrieval quality by query category.

Do not log raw private memory content unnecessarily.

## 16. Acceptance criteria

Phase 8.8 is complete only when:

- [ ] Retrieval requests are validated.
- [ ] Query preprocessing works.
- [ ] Vector retrieval works.
- [ ] Keyword retrieval works.
- [ ] Metadata filtering works.
- [ ] Entity-aware retrieval works.
- [ ] Relationship-aware retrieval works.
- [ ] Hybrid candidate aggregation works.
- [ ] Duplicate results are removed safely.
- [ ] Relevance ranking is implemented.
- [ ] Confidence and evidence filtering are implemented.
- [ ] Temporal context is preserved.
- [ ] Dynamic Top-K selection works.
- [ ] Iterative retrieval is bounded.
- [ ] Retrieval budgets are enforced.
- [ ] Provenance is preserved in results.
- [ ] Historical and current information can be distinguished.
- [ ] Partial results are clearly identified.
- [ ] Ownership and authorization are enforced.
- [ ] Unit and integration tests pass.
- [ ] Retrieval quality evaluation is available.

## 17. Implementation constraints

Claude Code must:

1. Inspect the repository before modifications.
2. Reuse Phase 8.1–8.7 implementations.
3. Follow approved Phase 5 data models.
4. Follow Phase 6 retrieval algorithms.
5. Follow Phase 7 technology decisions.
6. Keep retrieval separate from response generation.
7. Keep relevance separate from importance and confidence.
8. Preserve provenance and temporal context.
9. Enforce ownership on every retrieval path.
10. Use bounded iterative retrieval.
11. Avoid unrestricted entity traversal.
12. Avoid generative LLM functionality.
13. Avoid implementing document RAG in this milestone.
14. Place source code inside `memory-engine/`.
15. Place tests inside `tests/`.
16. Do not proceed to Phase 8.9 automatically.

If an existing retrieval contract or model cannot support a required capability, report the gap before changing the architecture.

## 18. Completion report

Claude Code must provide:

1. Summary of retrieval functionality.
2. Files created or modified.
3. Retrieval methods implemented.
4. Ranking strategy.
5. Dynamic Top-K strategy.
6. Iterative retrieval and budget configuration.
7. Provenance and temporal handling.
8. Tests executed and exact results.
9. Retrieval evaluation results.
10. Known limitations.
11. Deviations from approved architecture.
12. Acceptance criteria status.

Clearly distinguish implementation completion from retrieval quality validation.

## 19. Definition of done

Phase 8.8 is complete when Raven can retrieve relevant, evidence-backed memories using hybrid search and contextual ranking while preserving ownership, confidence, provenance and temporal correctness.

**The output is a reliable retrieval interface that allows Raven and the Agent Orchestrator to access the right memories for a given task.**
