# 8.11 — Memory Engine Integration and Testing

## 1. Objective

Integrate and validate the complete Memory Engine implementation.

Phase 8 must deliver two distinct but interoperable capabilities:

1. Personal Memory Engine.
2. Document Intelligence and Retrieval-Augmented Generation (RAG).

Both capabilities must operate under the same Memory Engine ownership while maintaining separate data models, processing pipelines, retrieval domains, and lifecycle rules.

This plan validates that all implemented components work together reliably and meet the approved architecture, security, quality, and data-integrity requirements.

## 2. Architecture references

Read:

- `PROJECT_ARCHITECTURE.md`
- `docs/architecture/`
- `docs/data-models/`
- `docs/algorithms/`
- `docs/technology/`
- `docs/technical-decisions.md`
- `docs/implementation-plans/phase-08-memory-engine/README.md`
- Plans 8.1 through 8.10.
- `docs/implementation-plans/phase-08-memory-engine/12-document-rag-pipeline.md`

All tests must validate the approved specifications rather than silently changing them.

## 3. Integration architecture

Validate the following capabilities.

### Personal memory

- Foundation and configuration.
- Database and persistence.
- Ingestion.
- Extraction and evaluation.
- Entity and relationship management.
- Memory resolution.
- Memory storage and indexing.
- Memory retrieval.
- Consolidation and maintenance.
- Forgetting and deletion.

### Document intelligence

- Document registration.
- Original file storage.
- Document versioning.
- Parsing and structure extraction.
- Chunking.
- Embedding generation.
- Hybrid indexing.
- Document retrieval.
- Evidence selection.
- Answer assembly.
- Citation and provenance validation.
- Document lifecycle and deletion.

### Shared infrastructure

Validate the approved shared infrastructure used by both capabilities:

- PostgreSQL.
- SQLAlchemy.
- Alembic.
- pgvector.
- Object storage.
- RabbitMQ and Celery where implemented.
- Logging and observability.
- Configuration and security.
- Background processing.

Shared infrastructure must not collapse the separate business responsibilities of the two domains.

## 4. Personal memory end-to-end testing

Validate the complete personal memory lifecycle:

`Input → Ingestion → Relevance Gate → Extraction → Evaluation → Candidate → Resolution → Storage → Indexing → Retrieval → Consolidation`

Test the following scenarios.

### 4.1 Basic memory lifecycle

- User submits a preference.
- User submits a goal.
- User submits a decision.
- User submits an important event.
- User submits a commitment.
- Raven extracts eligible facts.
- Candidates are evaluated.
- Valid candidates enter memory resolution.
- Approved memories are persisted.
- Relevant memories can be retrieved.

### 4.2 Memory updates and contradictions

- User corrects an existing fact.
- User changes a preference.
- User updates a goal.
- Two sources provide conflicting information.
- A new fact supersedes an old fact.
- Historical information remains available where appropriate.
- Current information is correctly identified.

### 4.3 Entity and relationship integration

- Entity extraction and registration.
- Alias handling.
- Entity-to-memory relationships.
- Entity-to-entity relationships.
- Memory-to-memory relationships.
- Duplicate entity handling.
- Ambiguous entity handling.

### 4.4 Consolidation

- Episodic grouping.
- Semantic consolidation.
- Derived profile updates.
- Freshness evaluation.
- Retention utility evaluation.
- Derived-data consistency.
- Provenance preservation.

### 4.5 Forgetting

- Delete one memory.
- Delete related derived data.
- Remove applicable embeddings and indexes.
- Handle concurrent operations.
- Recover partial deletion.
- Verify deletion completion.

## 5. Document intelligence end-to-end testing

Validate the complete document lifecycle:

`Upload → Validation → Registration → Storage → Parsing → Structure Extraction → Chunking → Embedding → Indexing → Retrieval → Evidence Selection → Answer Assembly → Citation Validation`

### 5.1 Document upload and registration

Test:

- Valid PDF upload.
- Valid DOCX upload.
- Valid TXT upload.
- Invalid file content.
- Unsupported format.
- Extension and actual-format mismatch.
- Oversized file.
- Duplicate request.
- Identical content uploaded as a distinct document.
- Multiple versions of a document.
- Ownership enforcement.
- Original object-storage reference.

Verify that successful registration does not falsely imply that parsing or indexing has completed.

### 5.2 Parsing and structure extraction

Test:

- Text-based PDF.
- Multi-page PDF.
- DOCX with headings.
- DOCX with lists.
- TXT document.
- Empty document.
- Malformed document.
- Tables where supported.
- Document with mixed structural content.
- Extraction failure.
- Worker interruption.

Verify that source location and document-version provenance are retained.

Scanned-document OCR must be tested only if the OCR capability has been explicitly selected and implemented.

### 5.3 Chunking

Test:

- Short document.
- Long document.
- Multiple sections.
- Heading-aware boundaries.
- Paragraph boundaries.
- Page boundaries.
- Table-related content where supported.
- Overlapping chunks where configured.
- Chunk ordering.
- Chunk provenance.
- Chunk size constraints.
- Duplicate processing.

Ensure that chunking does not silently discard meaningful source content or destroy citation locations.

### 5.4 Embedding and indexing

Test:

- Successful embedding generation.
- Embedding dimension validation.
- Invalid vector values.
- Embedding model metadata.
- Repeated embedding requests.
- Failed embedding generation.
- Vector indexing.
- Full-text indexing.
- Partial indexing failure.
- Index reconciliation.
- Document version changes.
- Stale index detection.

Document embeddings must remain separate from personal memory embeddings at the logical level.

### 5.5 Document retrieval

Test:

- Exact keyword query.
- Semantic query.
- Metadata-filtered retrieval.
- Document-specific retrieval.
- Version-specific retrieval.
- Page-specific evidence.
- Multi-document retrieval.
- Hybrid retrieval.
- Duplicate candidate aggregation.
- Ranking and filtering.
- No relevant results.
- Retrieval timeout.
- Vector search failure.
- Keyword search failure.

Retrieval must respect ownership and document lifecycle state.

### 5.6 Evidence selection and answer assembly

Validate that document-grounded answers:

- Use retrieved document evidence.
- Preserve relevant qualifications.
- Preserve numerical values and units.
- Preserve dates and version context.
- Avoid unsupported claims.
- Distinguish conflicting passages.
- Indicate when evidence is insufficient.
- Preserve page, section, or other source-location references.
- Provide citations linked to the correct document version.

The answer-generation design must follow the approved non-generative processing architecture.

Use extractive methods, conventional NLP, deterministic templates, and evidence-selection logic.

Do not introduce generative LLM APIs or locally hosted generative LLMs.

### 5.7 Citation validation

Test:

- Citation points to the correct document.
- Citation points to the correct version.
- Citation points to the correct chunk.
- Page and section references are accurate where available.
- Deleted sources cannot be cited as currently accessible evidence.
- Unsupported claims do not receive fabricated citations.
- Missing location metadata is reported honestly.
- Multiple supporting passages can be represented.

## 6. Personal memory and document boundary tests

This is a critical Phase 8 acceptance area.

Validate:

1. Uploading a document does not automatically create personal memories.
2. Document chunks are not stored as atomic memories.
3. Document embeddings are not treated as memory embeddings.
4. Personal memory retrieval does not return document chunks by default.
5. Document retrieval does not silently modify personal memory.
6. Document-derived memory extraction requires an authorized workflow.
7. Document-derived candidates preserve document provenance.
8. Document-derived candidates use the normal memory resolution lifecycle.
9. Deleting a document does not automatically delete unrelated personal memories.
10. Deleting a document invalidates its applicable retrieval artifacts.
11. Both domains enforce user ownership.
12. A future unified retrieval interface preserves source-domain identity.

## 7. Deletion integration tests

Validate deletion across the complete personal memory and document lifecycles.

### Personal memory

- Authoritative memory.
- Revisions.
- Candidates.
- Provenance.
- Relationships.
- Episodes.
- Derived profiles.
- Embeddings.
- Keyword indexes.
- Cached retrieval results.
- Pending jobs.

### Documents

- Original files.
- Document versions.
- Extracted text.
- Structural representations.
- OCR artifacts, where applicable.
- Chunks.
- Chunk embeddings.
- Vector indexes.
- Keyword indexes.
- Cached document retrieval results.
- Pending parsing, chunking, embedding, and indexing jobs.

### Derived personal memories

Test:

- Document-derived candidate deletion.
- Memory with only one supporting document.
- Memory with multiple independent sources.
- Memory supported by both a document and user message.
- Preservation of independent personal memories.
- Re-evaluation of affected memories where required.

### Recovery

Test:

- Partial deletion.
- Worker interruption.
- Retry.
- Stale worker completion.
- Database restoration.
- Tombstone reapplication.
- Post-recovery verification.

Do not report successful deletion unless the required verification process passes.

## 8. Security and privacy testing

Validate:

- User isolation.
- Authentication and authorization.
- Document ownership.
- Memory ownership.
- Cross-user retrieval prevention.
- Cross-user deletion prevention.
- Secure object-storage access.
- Safe file handling.
- Malformed input handling.
- Untrusted document content handling.
- Sensitive-data protection in logs.
- Deletion authorization.
- Pending-job authorization checks.

No user must be able to retrieve or modify another user's private memories or documents.

## 9. Reliability and failure injection

Test failures across the complete pipeline.

Examples:

- PostgreSQL unavailable.
- Object storage unavailable.
- RabbitMQ unavailable.
- Background worker terminated.
- Parsing failure.
- Embedding failure.
- Vector indexing failure.
- Full-text indexing failure.
- Database transaction failure.
- Duplicate message delivery.
- Timeout.
- Concurrent update.
- Stale processing operation.
- Partial deletion.
- Service restart.

Validate:

- Bounded retries.
- Idempotency.
- Recoverable operation state.
- Accurate error reporting.
- No false completion.
- No silent data loss.
- No unauthorized data recreation.
- Preservation of completed work where appropriate.

## 10. Quality evaluation

### Personal memory quality

Evaluate:

- Extraction precision.
- Extraction recall.
- Candidate quality.
- Duplicate detection.
- Contradiction handling.
- Confidence calibration.
- Retrieval relevance.
- Temporal correctness.
- Provenance completeness.
- Deletion correctness.

### Document intelligence quality

Evaluate:

- Parsing completeness.
- Structure preservation.
- Chunk quality.
- Chunk provenance accuracy.
- Embedding consistency.
- Retrieval relevance.
- Evidence coverage.
- Citation correctness.
- Unsupported-answer rate.
- Version correctness.

Use representative and documented test datasets.

Do not claim quality metrics without actually running the evaluation.

## 11. Performance testing

Measure:

- Memory ingestion latency.
- Memory retrieval latency.
- Document upload latency.
- Document processing duration.
- Parsing throughput.
- Chunking throughput.
- Embedding throughput.
- Indexing latency.
- Document retrieval latency.
- Deletion duration.
- Database resource utilization.
- Worker utilization.

Separate synchronous request latency from background-processing completion time.

Establish baselines before introducing optimizations.

Do not add infrastructure solely to improve an unmeasured hypothetical bottleneck.

## 12. Observability

Validate logs, metrics, and traces across both domains.

Use the approved correlation identifiers.

Track:

- Request IDs.
- Execution IDs.
- Task IDs.
- Message IDs.
- Correlation IDs.
- Trace and span IDs.
- Memory IDs.
- Document IDs.
- Document version IDs.
- Processing operation IDs.

Metrics must distinguish personal memory processing from document processing.

Avoid logging full personal memory content or document content.

## 13. Documentation and implementation verification

Verify that documentation matches the actual implementation.

Update relevant documentation to reflect:

- Implemented components.
- Actual API contracts.
- Actual models and migrations.
- Processing behavior.
- Supported formats.
- OCR support or limitations.
- Retrieval behavior.
- Citation behavior.
- Deletion guarantees.
- Security controls.
- Known limitations.

Do not mark a feature implemented simply because its plan exists.

## 14. Acceptance criteria

Phase 8 integration and testing is complete when:

1. The personal memory lifecycle works end to end.
2. Memory resolution preserves history and handles conflicts safely.
3. Memory retrieval is relevant and provenance-aware.
4. Consolidation preserves authoritative data and source references.
5. Personal memory deletion propagates correctly.
6. Document upload and registration work.
7. Document parsing and chunking work for the supported formats.
8. Document indexing works.
9. Document retrieval returns relevant evidence.
10. Answer assembly uses the approved non-generative architecture.
11. Citations preserve document and version provenance.
12. Personal memory and document intelligence remain separate domains.
13. Authorized document-to-memory extraction works through the normal candidate lifecycle.
14. Document deletion propagates to applicable derived data.
15. User isolation and authorization tests pass.
16. Failure and recovery tests pass.
17. Required quality evaluations are completed.
18. Performance baselines are documented.
19. Documentation matches the actual implementation.
20. All required acceptance tests pass.

## 15. Final Phase 8 completion report

Claude Code must produce a final report containing:

### Implementation summary

- Components implemented.
- Source-code locations.
- Database models and migrations.
- API and internal contracts.
- Background-processing components.
- Personal memory capabilities.
- Document intelligence capabilities.

### Verification summary

- Test commands.
- Test results.
- Coverage results.
- Quality evaluation results.
- Performance baselines.
- Security and isolation results.
- Deletion verification results.

### Limitations

- Unsupported formats.
- OCR limitations.
- Retrieval limitations.
- Known performance bottlenecks.
- Deferred capabilities.
- Outstanding architectural decisions.

### Completion status

Classify each capability as:

- Complete and verified.
- Implemented but not fully verified.
- Partially implemented.
- Deferred.
- Blocked.

Do not label Phase 8 complete if a critical security, privacy, data-integrity, or acceptance requirement remains unresolved.

## 16. Claude Code execution instructions

Before integration:

1. Inspect the existing Memory Engine implementation.
2. Read all Phase 8 implementation plans.
3. Review the actual tests and migrations.
4. Identify missing integration points.
5. Identify architecture deviations.
6. Prepare an integration and test execution plan.

Do not rewrite functioning components unnecessarily.

Do not introduce generative LLM dependencies.

Do not mark tests as passing without executing them.

After completing the work, produce the final Phase 8 report described above.

Do not automatically proceed to Phase 9.
