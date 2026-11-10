# Phase 8.12 — Document Intelligence & RAG Pipeline Implementation Plan

## 1. Objective

Implement a Document Intelligence and Retrieval-Augmented Generation (RAG) pipeline within Raven's Memory Engine.

The pipeline must allow users to upload documents, preserve their original content, extract and structure information, create searchable document chunks, generate embeddings, and retrieve relevant passages when answering document-related questions.

Raven must be able to answer questions about uploaded documents while preserving traceability to the original source.

### Primary objectives

- Accept and register supported document formats.
- Extract text and structural information.
- Preserve original documents.
- Process document metadata.
- Segment documents into meaningful chunks.
- Maintain document-to-chunk relationships.
- Generate and store embeddings.
- Implement hybrid document retrieval.
- Rank and select relevant passages.
- Preserve page, section and source references.
- Produce evidence-grounded answers.
- Maintain document lifecycle and deletion consistency.
- Integrate document retrieval with the Agent Orchestrator in a later phase.

## 2. Architectural position

Document RAG is a first-class capability of the Memory Engine.

It is not a separate engine.

However, document retrieval and personal memory retrieval must remain logically independent.

### 2.1 Memory Retrieval

Responsible for retrieving:

- Personal facts.
- Preferences.
- Goals.
- Decisions.
- Relationships.
- Projects.
- Commitments.
- Episodic memories.
- Derived semantic memories.

Its authoritative records are the approved Memory Engine memory models.

### 2.2 Document Retrieval

Responsible for retrieving:

- Uploaded document content.
- Relevant passages.
- Sections.
- Tables and extracted structured content where supported.
- Document-specific evidence.
- Source locations and citations.

Its authoritative source is the original uploaded document.

### 2.3 Shared infrastructure

The two retrieval systems may share:

- PostgreSQL.
- pgvector.
- Embedding infrastructure.
- Keyword search infrastructure.
- Background workers.
- Object storage.
- Logging and monitoring.
- Authentication and authorization infrastructure.

However, they must not share authoritative records or lifecycle semantics merely because they use the same infrastructure.

**Document chunks must not automatically become personal memories.**

## 3. Architecture references

Claude Code must review:

1. `PROJECT_ARCHITECTURE.md`
2. `docs/architecture/` — Memory Engine architecture.
3. `docs/data-models/` — approved data models.
4. `docs/algorithms/` — approved algorithm specifications.
5. `docs/technology/01-baseline-technology-stack.md`
6. `docs/technology/02-database-and-storage-architecture.md`
7. `docs/technology/03-vector-search-and-embedding-infrastructure.md`
8. `docs/technology/04-background-processing-and-messaging.md`
9. `docs/technology/05-nlp-and-machine-learning-stack.md`
10. `docs/technology/07-observability-and-testing-infrastructure.md`
11. `docs/implementation-plans/phase-08-memory-engine/03-ingestion-pipeline.md`
12. `docs/implementation-plans/phase-08-memory-engine/07-memory-storage-and-indexing.md`
13. `docs/implementation-plans/phase-08-memory-engine/08-memory-retrieval.md`
14. `docs/implementation-plans/phase-08-memory-engine/10-forgetting-and-deletion.md`
15. `docs/implementation-plans/phase-08-memory-engine/11-memory-engine-integration-and-testing.md`

The final Phase 8 data-model and algorithm amendments must also be reviewed before implementation.

## 4. Scope

### Included

- Document registration.
- Document validation.
- Document metadata management.
- Original document preservation.
- Text extraction.
- Structural extraction.
- Page and section tracking.
- Document segmentation.
- Chunk generation.
- Chunk metadata management.
- Embedding generation.
- Vector indexing.
- Keyword indexing.
- Hybrid document retrieval.
- Candidate ranking.
- Evidence selection.
- Citation generation.
- Document lifecycle management.
- Document deletion propagation.
- Document retrieval evaluation.

### Excluded

- Independent generative LLM services.
- Automatic conversion of all document content into personal memories.
- Unrestricted document crawling.
- External web research.
- Research Engine implementation.
- Agent Orchestrator implementation.
- Production deployment.

The core Raven processing architecture continues to exclude generative LLM APIs and locally hosted generative LLMs.

## 5. Document processing architecture

Implement the following logical components.

### 5.1 Document Registration Service

Responsibilities:

- Receive document registration requests.
- Validate user ownership.
- Register document metadata.
- Generate or assign a stable document identifier.
- Associate the document with the correct user.
- Preserve the original source reference.
- Track document processing status.

A document must have an independent identity.

Its identity must not depend exclusively on its filename.

### 5.2 Document Validation Service

Support the approved document formats:

- PDF.
- DOCX.
- TXT.

Validation requirements:

- Validate actual file format.
- Check file integrity.
- Check configurable file-size limits.
- Reject unsupported formats.
- Detect malformed documents.
- Validate access permissions.
- Validate document ownership.
- Handle duplicate upload requests safely.

Do not trust file extensions or user-supplied MIME types alone.

### 5.3 Document Storage Service

Preserve original uploaded documents using the approved object storage architecture.

Requirements:

- Store original documents in controlled object storage.
- Maintain metadata and references in PostgreSQL.
- Use opaque identifiers.
- Enforce access control.
- Preserve checksums.
- Track storage status.
- Support document lifecycle operations.

Do not store large original files directly inside ordinary relational records unless the approved architecture explicitly requires it.

### 5.4 Document Text Extraction Service

Extract textual information from supported document formats.

#### PDF extraction

Extract:

- Page text.
- Page boundaries.
- Available text structure.
- Section information where detectable.
- Tables where supported.
- Relevant layout information.

#### DOCX extraction

Extract:

- Paragraphs.
- Headings.
- Tables.
- Document structure.
- Available metadata.

#### TXT extraction

Extract:

- Text content.
- Encoding information.
- Meaningful section boundaries where detectable.

Preserve the relationship between extracted content and its original document.

Do not assume every PDF contains extractable text.

### 5.5 OCR capability

Scanned documents may contain page images rather than selectable text.

The architecture must support OCR as an optional document-processing capability.

Requirements:

- Detect documents or pages with insufficient extractable text.
- Identify when OCR is required.
- Support an independently configurable OCR component.
- Preserve page references.
- Record OCR processing status.
- Preserve extraction provenance.
- Distinguish OCR-derived text from directly extracted text.

OCR technology selection and implementation must follow an explicit technology evaluation.

Do not claim scanned PDF support until OCR has actually been implemented and tested.

### 5.6 Document Structure Manager

Maintain document structure and source locations.

Where available, preserve:

- Page numbers.
- Section headings.
- Heading hierarchy.
- Paragraph boundaries.
- Table references.
- Source offsets.
- Extraction method.
- Relevant document metadata.

Structure preservation is important for producing meaningful chunks and accurate citations.

## 6. Document segmentation and chunking

Implement a document segmentation system that converts extracted content into manageable retrieval units.

### 6.1 Chunking strategy

Use structure-aware segmentation rather than relying exclusively on fixed character counts.

Consider:

- Document headings.
- Paragraph boundaries.
- Section boundaries.
- Page boundaries.
- Tables.
- Semantic continuity.
- Maximum chunk size.
- Token limits of the selected embedding model.

The objective is to preserve meaningful context while producing chunks suitable for embedding and retrieval.

### 6.2 Chunk metadata

Each chunk must preserve the information necessary to trace it to its source.

The logical chunk representation should include:

- Chunk identifier.
- Document identifier.
- Owner reference.
- Chunk content.
- Chunk sequence.
- Page number or page range.
- Section heading.
- Source offsets where available.
- Extraction method.
- Chunking version.
- Content checksum.
- Creation timestamp.
- Processing status.

Claude Code must reconcile these fields with the final approved Phase 5 document data models.

Do not independently create competing document models.

### 6.3 Chunk boundaries

Requirements:

- Avoid splitting meaningful sentences unnecessarily.
- Preserve section context.
- Avoid combining unrelated sections.
- Handle long paragraphs safely.
- Handle tables without losing their structure.
- Support configurable overlap where useful.
- Prevent excessive duplication between adjacent chunks.

Chunk size, overlap and segmentation parameters must be evaluated using Raven-specific retrieval datasets.

Do not hardcode arbitrary values without documenting their rationale.

### 6.4 Chunk versioning

Chunk representations are derived data.

If the original document or extraction process changes:

- Identify affected chunks.
- Mark stale chunks.
- Reprocess the relevant content.
- Generate new chunk versions.
- Update associated embeddings and indexes.
- Preserve enough metadata to identify which document version produced each chunk.

Do not silently associate old embeddings with new chunk content.

## 7. Document embedding pipeline

Use the approved sentence-transformers ecosystem.

Responsibilities:

- Prepare normalized chunk content.
- Generate embeddings.
- Validate dimensions.
- Validate numerical values.
- Record model metadata.
- Associate embeddings with document and chunk references.
- Support asynchronous embedding generation.

Track:

- Embedding model identifier.
- Model version.
- Embedding dimensions.
- Preprocessing version.
- Chunk version.
- Creation timestamp.

### Embedding requirements

- Use the same compatible embedding configuration during indexing and query processing.
- Keep document embeddings separate from personal memory embeddings at the logical data-model level.
- Preserve the authoritative chunk content independently.
- Support embedding regeneration.
- Support model-version migration.
- Handle embedding failures without losing original documents.

Do not assume that embeddings generated by incompatible models or dimensions can be compared directly.

## 8. Document indexing

### 8.1 Vector indexing

Use PostgreSQL and pgvector for the initial implementation.

Requirements:

- Store document chunk embeddings.
- Associate vectors with their chunk and document.
- Enforce owner-based filtering.
- Support document-specific retrieval.
- Support document collection filtering where approved.
- Handle stale embedding records.
- Support index reconciliation.

### 8.2 Keyword indexing

Use PostgreSQL full-text search as the initial keyword search mechanism.

Support:

- Exact terminology.
- Technical terms.
- Names.
- Identifiers.
- Section-specific text.
- Relevant document metadata.

### 8.3 Metadata indexing

Support filters such as:

- User ownership.
- Document identifier.
- Document type.
- Upload timestamp.
- Document status.
- Page references.
- Document collection where supported.

Do not introduce excessive indexes without measuring query performance.

## 9. Document retrieval architecture

Implement the following components.

### 9.1 Document Query Processor

Responsibilities:

- Validate the retrieval request.
- Normalize query text.
- Extract useful keywords.
- Preserve technical terminology.
- Identify document and collection filters.
- Prepare query embeddings where required.

Do not alter the meaning of the user's question.

### 9.2 Document Candidate Retriever

Retrieve relevant chunks using:

- Vector similarity.
- Keyword matching.
- Document metadata.
- Page and section filters.

Support both document-specific queries and queries across authorized document collections.

All queries must enforce user ownership.

### 9.3 Hybrid Retrieval Aggregator

Combine retrieval results from the available methods.

Responsibilities:

- Merge candidate chunks.
- Remove duplicate results.
- Preserve retrieval signals.
- Preserve source references.
- Apply eligibility filters.
- Prepare candidates for ranking.

Do not treat vector similarity as proof that a passage answers the question.

### 9.4 Document Reranker

Evaluate retrieved chunks using relevant signals.

Consider:

- Semantic relevance.
- Keyword relevance.
- Query-to-passage coverage.
- Section context.
- Document metadata.
- Evidence quality.
- Duplicate content.
- Temporal relevance where applicable.

Use an evaluated non-generative ranking or reranking approach.

The reranker must not fabricate evidence or change the source text.

### 9.5 Context Selection

Select a bounded set of passages suitable for evidence-grounded answer assembly.

Requirements:

- Preserve the most relevant evidence.
- Avoid excessive duplicate passages.
- Preserve useful context from surrounding sections.
- Maintain source diversity where appropriate.
- Respect processing and context budgets.
- Preserve page and section references.

Do not select passages solely because they have high similarity scores.

## 10. Evidence-grounded answer assembly

Raven must be able to produce answers based on retrieved document evidence.

However, the core architecture does not use generative LLM APIs or locally hosted generative LLMs.

Therefore, answer assembly must use:

- Structured evidence selection.
- Extractive answer techniques where applicable.
- Deterministic templates.
- Conventional NLP.
- Structured summaries where the underlying extraction method is reliable.

The system must distinguish:

- Directly supported statements.
- Extracted evidence.
- Inferences.
- Missing information.
- Conflicting evidence.

If the retrieved passages do not support an answer, Raven must state that the available document evidence is insufficient.

Do not fabricate an answer to satisfy the user's question.

Do not describe template-based or extractive output as unrestricted generative summarization.

## 11. Citation and provenance system

Every retrieved passage must retain a connection to its original document.

Citations should include, where available:

- Document title.
- Document identifier.
- Page number or page range.
- Section heading.
- Chunk reference.
- Source reference.

Example:

Question:

"What are the main limitations described in the report?"

A grounded result might contain:

- Limitation: Retrieval latency increases with the number of indexed records.
- Source: System Design Report.
- Location: Page 12, Performance Considerations.

The example is illustrative.

Requirements:

- Citation references must point to actual stored documents.
- Page numbers must reflect original document locations.
- Citations must remain valid after reprocessing where possible.
- Evidence must be associated with the exact chunk version used.
- Unavailable source locations must not be invented.

## 12. Relationship with personal memory extraction

Document content may contain information that is potentially useful as personal memory.

However, document retrieval and memory extraction must remain separate workflows.

### Default behavior

Uploading a document must not automatically convert all its contents into personal memories.

### Optional memory extraction

Where an explicit, authorized workflow requests memory extraction from a document:

1. Identify relevant document passages.
2. Preserve the source document and chunk references.
3. Generate atomic fact proposals.
4. Evaluate the facts using Phase 8.4.
5. Preserve document provenance.
6. Submit candidates through the normal memory resolution pipeline.
7. Apply the approved memory lifecycle.

A document passage must not become an authoritative personal memory merely because it was retrieved.

Document-derived memories must retain their original document evidence.

## 13. Document lifecycle management

Support document processing states using the approved document lifecycle model.

The logical lifecycle should distinguish:

- Uploaded.
- Validated.
- Processing.
- Text extraction completed.
- Chunking completed.
- Indexing pending.
- Indexed.
- Partially processed.
- Failed.
- Deletion requested.
- Deleted.

Use the exact approved status vocabulary where available.

A document may remain available as an original file even when indexing has failed.

The system must distinguish original document availability from search-index readiness.

## 14. Deletion and consistency

Document deletion must propagate across all relevant storage and derived representations.

The deletion workflow must account for:

- Original document objects.
- Extracted text.
- Document metadata.
- Document chunks.
- Chunk revisions.
- Embeddings.
- Vector indexes.
- Keyword indexes.
- Cached retrieval results.
- Pending extraction jobs.
- Pending embedding jobs.
- Derived memories explicitly created from document content.

Requirements:

- Reuse the approved Phase 8.10 deletion architecture.
- Enforce ownership.
- Use deletion operation tracking.
- Prevent stale jobs from recreating deleted content.
- Invalidate affected indexes and caches.
- Preserve deletion protection.
- Support reconciliation.
- Verify cleanup before reporting completion.

Deleting a document must not automatically delete independent personal memories that happen to mention the same topic.

However, memories explicitly derived from that document must be identifiable so that the approved deletion policy can be applied.

## 15. Failure handling

| Scenario | Expected behavior |
|---|---|
| Unsupported document | Reject safely |
| Corrupted document | Record extraction failure |
| PDF has no extractable text | Identify OCR requirement |
| OCR unavailable | Mark processing as unsupported or incomplete |
| DOCX parsing failure | Preserve original and record failure |
| Chunk generation failure | Preserve document and extraction result |
| Embedding service unavailable | Keep indexing pending |
| Vector index failure | Reconcile and retry |
| Keyword indexing failure | Preserve original document |
| No relevant retrieval results | Return no-evidence result |
| Conflicting passages | Preserve and report conflict |
| Unauthorized document access | Deny retrieval |
| Partial deletion | Keep deletion incomplete and reconcile |
| Stale processing job | Reject using lifecycle and deletion checks |

Partial processing must never be represented as fully indexed or fully searchable.

## 16. Testing requirements

### Unit tests

Test:

- Document validation.
- Metadata extraction.
- PDF text extraction.
- DOCX text extraction.
- TXT extraction.
- OCR requirement detection.
- Structural extraction.
- Chunk segmentation.
- Chunk metadata generation.
- Embedding validation.
- Citation construction.

### Component tests

Test:

- Document registration.
- Original document storage.
- Extraction pipeline.
- Chunk persistence.
- Embedding generation.
- Vector indexing.
- Keyword indexing.
- Hybrid retrieval.
- Reranking.
- Evidence selection.
- Answer assembly.

### Retrieval quality evaluation

Create representative evaluation documents and questions.

Include:

- Exact factual questions.
- Questions requiring multiple passages.
- Questions involving tables.
- Questions involving technical terminology.
- Questions involving section-specific information.
- Questions involving historical dates.
- Questions with conflicting passages.
- Questions whose answers are absent from the document.
- Questions spanning multiple uploaded documents.

Evaluate:

- Precision@K.
- Recall@K.
- Mean Reciprocal Rank.
- nDCG@K.
- Citation accuracy.
- Evidence coverage.
- Page-reference accuracy.
- Unsupported answer rate.
- Retrieval latency.

### Security tests

Test:

- Cross-user document retrieval.
- Unauthorized object storage access.
- Forged document identifiers.
- Unauthorized collection access.
- Private document leakage through logs.
- Document deletion authorization.

### Reliability tests

Test:

- Duplicate uploads.
- Interrupted extraction.
- Interrupted chunking.
- Embedding service failure.
- Indexing interruption.
- Duplicate background jobs.
- Document replacement.
- Concurrent document operations.
- Deletion during indexing.
- Backup restoration and deletion protection.

## 17. Observability

Record structured events for:

- Document registered.
- Document validated.
- Text extraction started.
- Text extraction completed.
- OCR required.
- OCR completed.
- Chunking completed.
- Embedding generation completed.
- Indexing completed.
- Document retrieval started.
- Retrieval candidates selected.
- Evidence assembled.
- Citation generated.
- Document deletion started.
- Document deletion verified.

Track:

- Documents processed.
- Extraction success rate.
- OCR usage.
- Chunk generation count.
- Embedding failure rate.
- Indexing latency.
- Retrieval latency.
- Citation accuracy.
- Empty-result rate.
- Unsupported answer rate.
- Deletion reconciliation failures.

Do not log full private document contents unnecessarily.

## 18. Acceptance criteria

Phase 8.12 is complete only when:

- [ ] PDF, DOCX and TXT documents can be registered.
- [ ] Original documents are preserved.
- [ ] File formats are validated.
- [ ] Text extraction works for supported formats.
- [ ] Document structure and page references are preserved where available.
- [ ] OCR requirements can be detected.
- [ ] OCR integration is implemented or explicitly documented as deferred.
- [ ] Documents can be segmented into meaningful chunks.
- [ ] Chunk provenance is preserved.
- [ ] Embeddings can be generated and versioned.
- [ ] pgvector indexing works.
- [ ] Keyword indexing works.
- [ ] Hybrid document retrieval works.
- [ ] Relevant passages can be reranked.
- [ ] Evidence-grounded answers can be assembled.
- [ ] Citations point to actual source locations.
- [ ] Insufficient evidence is reported honestly.
- [ ] Document retrieval is separate from personal memory retrieval.
- [ ] Optional document-to-memory extraction uses the approved memory pipeline.
- [ ] Document deletion propagates across required dependencies.
- [ ] User ownership is enforced.
- [ ] Unit, component and integration tests pass.
- [ ] Retrieval quality evaluation is available.

## 19. Implementation constraints

Claude Code must:

1. Inspect the existing repository before modifying files.
2. Reuse Phase 8.1–8.11 implementations.
3. Follow the final approved Phase 5 document data models.
4. Follow the approved Phase 6 retrieval and processing algorithms.
5. Follow Phase 7 technology decisions.
6. Preserve original document content.
7. Keep document chunks separate from authoritative personal memories.
8. Preserve document and chunk provenance.
9. Enforce ownership across every retrieval path.
10. Use hybrid retrieval.
11. Keep answer assembly evidence-grounded.
12. Avoid generative LLM APIs and locally hosted generative LLMs.
13. Avoid introducing a dedicated vector database without an approved architectural decision.
14. Avoid creating a separate Document Engine.
15. Reuse the approved deletion and recovery architecture.
16. Place implementation code inside `memory-engine/`.
17. Place tests inside `tests/`.
18. Do not proceed to Research Engine implementation automatically.

If an approved model, algorithm or technology decision cannot support a required capability, report the exact gap and recommend the smallest safe architectural change before modifying it.

## 20. Completion report

Claude Code must provide:

1. Summary of document processing functionality.
2. Files created or modified.
3. Document formats supported.
4. Extraction and OCR implementation status.
5. Chunking strategy.
6. Document data models used.
7. Embedding model and version.
8. Vector and keyword indexing approach.
9. Retrieval and reranking methods.
10. Citation and provenance implementation.
11. Memory extraction boundary.
12. Deletion propagation implementation.
13. Tests executed and exact results.
14. Retrieval quality evaluation.
15. Known limitations.
16. Deviations from approved specifications.
17. Acceptance criteria status.

Clearly distinguish text extraction, indexing, retrieval and answer assembly. These are separate capabilities and must not be reported as complete merely because document upload works.

## 21. Definition of done

Phase 8.12 is complete when Raven can accept supported documents, preserve their originals, extract and structure their content, index meaningful chunks, retrieve relevant evidence and produce traceable document-grounded answers.

Document knowledge must remain separate from personal memory unless it is deliberately processed through the approved memory extraction workflow.

**The result is a document intelligence capability that allows Raven to work with uploaded knowledge without compromising the integrity of its personal memory system.**
