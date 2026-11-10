# Phase 8.11 — Memory Engine Integration & Testing Implementation Plan

## 1. Objective

Integrate and validate the complete Memory Engine implementation.

This milestone verifies that all previously implemented components operate together correctly, maintain data integrity and satisfy the approved architectural requirements.

The integration must validate the complete memory lifecycle:

- Ingestion.
- Extraction and evaluation.
- Entity and relationship management.
- Memory resolution.
- Authoritative storage and indexing.
- Memory retrieval.
- Consolidation and maintenance.
- Forgetting and deletion.

### Primary objectives

- Integrate all Memory Engine components.
- Validate internal interfaces and contracts.
- Verify end-to-end memory lifecycle workflows.
- Validate database and storage consistency.
- Verify ownership and privacy boundaries.
- Test asynchronous processing and recovery.
- Validate retrieval quality.
- Test deletion guarantees.
- Evaluate system reliability and performance.
- Produce a final Phase 8 implementation report.

## 2. Architecture references

Claude Code must review:

1. `PROJECT_ARCHITECTURE.md`
2. `docs/architecture/` — Memory Engine architecture.
3. `docs/data-models/` — approved Memory Engine data models.
4. `docs/algorithms/` — approved Memory Engine algorithms.
5. `docs/technology/` — approved technology decisions.
6. `docs/implementation-plans/phase-08-memory-engine/README.md`
7. `docs/implementation-plans/phase-08-memory-engine/01-foundation-and-project-setup.md`
8. `docs/implementation-plans/phase-08-memory-engine/02-database-and-persistence.md`
9. `docs/implementation-plans/phase-08-memory-engine/03-ingestion-pipeline.md`
10. `docs/implementation-plans/phase-08-memory-engine/04-extraction-and-evaluation.md`
11. `docs/implementation-plans/phase-08-memory-engine/05-entity-and-relationship-management.md`
12. `docs/implementation-plans/phase-08-memory-engine/06-memory-resolution.md`
13. `docs/implementation-plans/phase-08-memory-engine/07-memory-storage-and-indexing.md`
14. `docs/implementation-plans/phase-08-memory-engine/08-memory-retrieval.md`
15. `docs/implementation-plans/phase-08-memory-engine/09-consolidation-and-maintenance.md`
16. `docs/implementation-plans/phase-08-memory-engine/10-forgetting-and-deletion.md`

All approved architecture, data models, algorithms and technology decisions remain authoritative.

## 3. Scope

### Included

- Component integration.
- Internal interface validation.
- Data contract validation.
- End-to-end lifecycle testing.
- Database integration testing.
- Background processing integration.
- Ownership and authorization testing.
- Concurrency testing.
- Failure and recovery testing.
- Retrieval quality evaluation.
- Deletion verification.
- Performance benchmarking.
- Security validation.
- Regression testing.
- Final implementation documentation.

### Excluded

- Research Engine implementation.
- Agent Orchestrator implementation.
- Cross-engine integration.
- Production deployment.
- Document RAG extensions not yet incorporated into the approved Phase 8 architecture.

These will be handled in subsequent phases or after the final Phase 8 architecture review.

## 4. Integration architecture

Validate the integration of the following components.

### 4.1 Ingestion Pipeline

Verify:

- Supported inputs are accepted.
- Input validation works.
- Source metadata is preserved.
- Original content remains traceable.
- Ownership is enforced.
- Idempotency works.
- Accepted inputs are registered for extraction.

### 4.2 Extraction & Evaluation

Verify:

- Relevance Gate operates correctly.
- Atomic facts are extracted.
- Explicit and inferred information are distinguished.
- Importance and confidence remain independent.
- Candidate provenance is preserved.
- Invalid candidates are rejected safely.

### 4.3 Entity & Relationship Management

Verify:

- Entity identification works.
- Entity types follow approved models.
- Aliases and mentions are maintained.
- Entity relationships are persisted.
- Memory relationships are maintained.
- Ambiguous identities are not silently merged.

### 4.4 Memory Resolution

Verify:

- Duplicate candidates are identified.
- Related facts remain distinct where appropriate.
- Contradictions are detected.
- Corrections and updates are handled.
- Superseded revisions are preserved.
- Resolution operations are idempotent.

### 4.5 Memory Storage & Indexing

Verify:

- Authoritative memories are persisted.
- Immutable revisions are maintained.
- Provenance remains intact.
- Embeddings are generated and versioned.
- Vector indexing works.
- Keyword indexing works.
- Index failures do not corrupt authoritative records.
- Derived indexes can be reconciled.

### 4.6 Memory Retrieval

Verify:

- Hybrid retrieval works.
- Metadata filtering works.
- Entity-aware retrieval works.
- Ranking behaves as expected.
- Confidence and evidence filtering work.
- Dynamic Top-K selection works.
- Historical and current information are distinguished.
- Retrieval budgets are enforced.

### 4.7 Consolidation & Maintenance

Verify:

- Related memories can be grouped.
- Episodes are maintained.
- Semantic representations preserve supporting evidence.
- Derived profiles are maintained.
- Freshness and retention utility are evaluated separately.
- Decay does not automatically delete memories.
- Stale derived representations can be recomputed.

### 4.8 Forgetting & Deletion

Verify:

- Explicit forgetting instructions bypass normal extraction.
- Deletion scope is validated.
- Deletion dependencies are identified.
- Tombstones prevent reintroduction.
- Derived data is cleaned up.
- Indexes and caches are invalidated.
- Unrelated memories remain unaffected.
- Deletion remains effective after recovery.

## 5. End-to-end lifecycle testing

Implement complete workflows using realistic test data.

### Workflow A — Basic memory creation

1. Submit a user message.
2. Validate and register the input.
3. Run relevance evaluation.
4. Extract atomic facts.
5. Evaluate importance and confidence.
6. Generate memory candidates.
7. Identify entities.
8. Resolve candidates.
9. Persist authoritative memories.
10. Generate derived indexes.
11. Retrieve the newly created memories.

Expected result:

The system creates traceable authoritative memories and makes them retrievable through the approved retrieval interface.

### Workflow B — Duplicate memory handling

1. Submit an initial fact.
2. Allow it to become an authoritative memory.
3. Submit a paraphrased version of the same fact.
4. Run memory resolution.
5. Verify the approved duplicate handling outcome.

Expected result:

Unnecessary duplicate memories are avoided while preserving relevant source evidence.

### Workflow C — Memory correction

1. Create an authoritative memory.
2. Submit an explicit correction.
3. Identify the existing memory.
4. Evaluate the correction.
5. Create an appropriate new revision.
6. Verify historical revision preservation.
7. Retrieve current and historical states.

Expected result:

The corrected information becomes authoritative without destroying historical context.

### Workflow D — Contradictory information

1. Create an initial memory.
2. Submit a conflicting observation.
3. Evaluate entity, attribute and temporal context.
4. Apply the appropriate resolution outcome.
5. Verify that unresolved contradictions are not silently discarded.

Expected result:

The system preserves conflicting evidence and distinguishes genuine updates from unresolved contradictions.

### Workflow E — Entity relationship handling

1. Submit facts involving multiple entities.
2. Identify entities.
3. Register aliases and mentions.
4. Create supported relationships.
5. Retrieve memories using entity context.

Expected result:

Related information can be retrieved without incorrectly merging distinct entities.

### Workflow F — Memory retrieval

1. Create several related and unrelated memories.
2. Submit different query types.
3. Execute hybrid retrieval.
4. Apply contextual filters.
5. Rank candidates.
6. Evaluate Top-K selection.
7. Verify provenance and temporal information.

Expected result:

The retrieval system returns relevant evidence-backed memories while excluding unauthorized or irrelevant information.

### Workflow G — Consolidation

1. Create a collection of related memories.
2. Trigger consolidation.
3. Generate appropriate episode representations.
4. Generate supported semantic representations.
5. Update derived profiles where justified.
6. Modify one supporting memory.
7. Verify derived-data invalidation and recomputation.

Expected result:

Derived representations remain consistent with their supporting memories.

### Workflow H — Explicit forgetting

1. Create an authoritative memory.
2. Generate its embeddings and indexes.
3. Associate it with an episode or derived profile.
4. Submit an explicit forgetting request.
5. Generate the deletion plan.
6. Execute deletion.
7. Verify cleanup across required storage layers.
8. Attempt retrieval again.
9. Attempt stale background-job processing.

Expected result:

The forgotten information is no longer retrievable or reintroduced, while unrelated memories remain intact.

## 6. Integration contract validation

Validate all internal interfaces between Memory Engine components.

Requirements:

- Consistent identifiers.
- Compatible data models.
- Schema version handling.
- Explicit ownership context.
- Consistent timestamps.
- Consistent lifecycle states.
- Structured error responses.
- Idempotency support.
- Trace and correlation identifiers.
- Provenance propagation.

Do not introduce tightly coupled component dependencies.

Keep domain logic, application services and persistence boundaries consistent with Phase 8.1.

## 7. Database and storage integration

Validate:

- PostgreSQL connectivity.
- SQLAlchemy persistence.
- Alembic migrations.
- Schema ownership.
- Foreign-key integrity.
- Transaction boundaries.
- Optimistic concurrency.
- pgvector integration.
- PostgreSQL full-text search.
- Object storage references.
- Derived-data consistency.
- Deletion reconciliation.

Test database migration from a clean environment and from the preceding supported schema version.

Do not assume migration correctness based only on successful migration generation.

## 8. Background processing integration

Validate the approved RabbitMQ and Celery architecture.

Test:

- Task publication.
- Task consumption.
- Idempotent task execution.
- Retry behavior.
- Bounded backoff.
- Dead-letter handling.
- Failed task recovery.
- Processing status updates.
- Cooperative cancellation.
- Outbox reconciliation where implemented.

Verify that authoritative workflow state remains consistent with background task outcomes.

## 9. Security and privacy validation

Security is a release-blocking requirement.

Test:

### Ownership isolation

- Users cannot retrieve other users' memories.
- Users cannot access other users' entities.
- Users cannot access other users' source content.
- Users cannot modify another user's memory records.
- Users cannot delete another user's memories.

### Data protection

- Secrets are not exposed in logs.
- Sensitive content is not unnecessarily logged.
- Object storage references are access-controlled.
- Database operations enforce ownership.
- Background jobs preserve the correct user context.

### Deletion integrity

- Deleted memories cannot reappear.
- Stale jobs cannot recreate deleted records.
- Derived indexes cannot expose deleted information.
- Backup restoration reapplies deletion protection.

### Input safety

- Untrusted source content cannot bypass validation.
- Malformed files are rejected safely.
- Explicit instructions are routed through approved workflows.
- Source content cannot override system policies.

Do not treat a successful happy-path test as sufficient security validation.

## 10. Reliability and failure-injection testing

Simulate failures across the complete lifecycle.

Scenarios include:

- Database unavailable.
- Object storage unavailable.
- Message broker unavailable.
- Background worker termination.
- Embedding model unavailable.
- Partial persistence failure.
- Concurrent memory updates.
- Duplicate ingestion.
- Duplicate processing tasks.
- Stale indexing jobs.
- Interrupted consolidation.
- Interrupted deletion.
- Cache invalidation failure.

Verify:

- No false success reporting.
- No unintended duplicate authoritative records.
- No silent data corruption.
- Safe retries.
- Recoverable partial operations.
- Preservation of completed work.
- Accurate processing status.

## 11. Performance benchmarking

Measure performance using representative workloads.

### Ingestion

Measure:

- Request validation latency.
- Source registration latency.
- Persistence latency.
- Throughput.

### Extraction

Measure:

- Relevance Gate latency.
- Extraction latency.
- Candidate generation throughput.

### Resolution

Measure:

- Matching latency.
- Duplicate detection latency.
- Resolution throughput.

### Storage and indexing

Measure:

- Database write latency.
- Embedding generation latency.
- Vector indexing latency.
- Keyword indexing latency.

### Retrieval

Measure:

- Vector retrieval latency.
- Keyword retrieval latency.
- Hybrid retrieval latency.
- Ranking latency.
- End-to-end retrieval latency.

### Consolidation and deletion

Measure:

- Consolidation job duration.
- Profile recomputation duration.
- Deletion propagation duration.
- Reconciliation duration.

Performance targets must be established using representative workload assumptions.

Do not invent benchmark results or claim scalability without measurements.

## 12. Retrieval and extraction quality evaluation

Maintain representative evaluation datasets.

Evaluate extraction quality through:

- Precision.
- Recall.
- Atomicity.
- Classification accuracy.
- Confidence calibration.
- False memory creation rate.

Evaluate retrieval quality through:

- Precision@K.
- Recall@K.
- Mean Reciprocal Rank.
- nDCG@K.
- Evidence coverage.
- Temporal correctness.

Evaluate resolution quality through:

- Duplicate detection precision and recall.
- False merge rate.
- Contradiction detection quality.
- Correction handling accuracy.

Evaluate consolidation quality through:

- Episode grouping quality.
- Derived fact support coverage.
- Profile correctness.
- Temporal correctness.

All evaluation results must be reproducible and associated with dataset and model versions.

## 13. Regression testing

Maintain a regression suite covering all critical behaviors.

Every relevant change must be checked against:

- Memory ownership.
- Provenance.
- Historical revisions.
- Duplicate handling.
- Contradiction handling.
- Retrieval correctness.
- Temporal integrity.
- Consolidation consistency.
- Deletion propagation.
- Idempotency.
- Concurrency.
- Error recovery.

Regression tests must prevent previously resolved data integrity issues from returning.

## 14. Documentation and operational readiness

Update the Memory Engine documentation to reflect actual implemented behavior.

Document:

- Implemented components.
- Internal interfaces.
- Data models and migrations.
- Configuration.
- Background workers.
- Operational commands.
- Error handling.
- Logging and metrics.
- Known limitations.
- Recovery procedures.
- Testing commands.

Clearly distinguish implementation facts from planned capabilities.

Do not mark a capability complete unless it has been implemented and verified.

## 15. Acceptance criteria

Phase 8.11 is complete only when:

- [ ] All Memory Engine components are integrated.
- [ ] Internal interfaces and contracts are validated.
- [ ] Complete lifecycle workflows pass.
- [ ] Database migrations work.
- [ ] PostgreSQL and pgvector integration works.
- [ ] Background processing is reliable.
- [ ] Ownership and privacy tests pass.
- [ ] Concurrency tests pass.
- [ ] Failure recovery tests pass.
- [ ] Extraction quality evaluation is available.
- [ ] Resolution quality evaluation is available.
- [ ] Retrieval quality evaluation is available.
- [ ] Consolidation consistency is verified.
- [ ] Deletion propagation is verified.
- [ ] Regression tests pass.
- [ ] Performance benchmarks are documented.
- [ ] Operational documentation reflects actual implementation.
- [ ] No unresolved critical security or data integrity defects remain.

## 16. Implementation constraints

Claude Code must:

1. Inspect the repository before modifications.
2. Reuse all Phase 8 implementations.
3. Follow approved architecture, data models, algorithms and technology decisions.
4. Avoid redesigning already approved components without a documented reason.
5. Preserve ownership and privacy boundaries.
6. Preserve provenance and historical integrity.
7. Treat deletion verification as release-critical.
8. Run the full relevant test suite.
9. Record exact commands and results.
10. Distinguish passing tests from untested behavior.
11. Avoid generative LLM functionality.
12. Avoid implementing document RAG until the final Phase 8 review.
13. Place source code inside `memory-engine/`.
14. Place tests inside `tests/`.
15. Do not proceed to Research Engine implementation automatically.

Any architectural conflict or critical implementation gap must be reported with a recommended resolution.

## 17. Final completion report

Claude Code must provide a consolidated Phase 8 report containing:

### A. Implementation summary

- Components implemented.
- Files created or modified.
- Dependencies introduced.
- Database migrations.
- Background workers.
- Internal interfaces.

### B. Testing results

- Unit tests.
- Component tests.
- Integration tests.
- End-to-end tests.
- Security tests.
- Reliability tests.
- Regression tests.

### C. Quality evaluation

- Extraction metrics.
- Resolution metrics.
- Retrieval metrics.
- Consolidation metrics.

### D. Performance results

- Measured latency.
- Throughput.
- Resource usage.
- Identified bottlenecks.

### E. Reliability and privacy

- Ownership isolation.
- Failure recovery.
- Deletion verification.
- Known limitations.

### F. Completion status

Classify each capability as:

- Implemented and verified.
- Implemented but not fully evaluated.
- Partially implemented.
- Not implemented.
- Blocked.

Do not use a single completion percentage to conceal incomplete or unverified critical capabilities.

## 18. Definition of done

Phase 8.11 is complete when the Memory Engine operates as an integrated system and all critical lifecycle, security, privacy, data integrity and recovery requirements have been tested.

The implementation must have reproducible evidence of correctness and a documented list of remaining limitations.

**Phase 8 is complete only when the Memory Engine can reliably ingest, form, resolve, store, retrieve, maintain and forget memories as one coherent system.**
