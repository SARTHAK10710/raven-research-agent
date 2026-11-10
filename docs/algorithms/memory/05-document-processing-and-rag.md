# Document Processing and RAG Algorithms

## 1. Objective

Define the algorithms and processing policies required to implement Document Intelligence and Retrieval-Augmented Generation (RAG) within Raven's Memory Engine.

The system must support:

- Document validation and registration.
- Content extraction.
- Structural analysis.
- Structure-aware chunking.
- Embedding generation.
- Hybrid document retrieval.
- Evidence selection.
- Extractive answer assembly.
- Citation generation and validation.
- Document lifecycle management.
- Deletion propagation.

The objective is to retrieve relevant information from uploaded documents and produce answers that remain grounded in verifiable source evidence.

## 2. Architectural principles

The document intelligence pipeline follows these principles:

1. Original documents remain authoritative source artifacts.
2. Extracted text and chunks are derived representations.
3. Every chunk must retain source-document provenance.
4. Document retrieval remains separate from personal memory retrieval.
5. Embeddings are retrieval signals, not evidence of truth.
6. Retrieval must respect document ownership and versioning.
7. Answers must be supported by retrieved evidence.
8. Unsupported information must not be fabricated.
9. Deletion must propagate across derived representations.
10. Processing must be recoverable and idempotent.

The core architecture must not depend on generative LLM APIs or locally hosted generative LLMs.

Use deterministic algorithms, conventional NLP, embedding models, statistical methods, extractive processing, and structured templates.

## 3. Overall processing pipeline

The document intelligence pipeline consists of the following stages:

```text
Document Upload
      |
      v
Document Validation
      |
      v
Document Registration
      |
      v
Original File Storage
      |
      v
Content Extraction
      |
      v
Structure Extraction
      |
      v
Content Normalization
      |
      v
Structure-Aware Chunking
      |
      v
Chunk Validation
      |
      v
Embedding Generation
      |
      v
Hybrid Indexing
      |
      v
Document Retrieval
      |
      v
Candidate Aggregation
      |
      v
Evidence Selection
      |
      v
Extractive Answer Assembly
      |
      v
Citation Validation
      |
      v
Response
```

Each stage must have independently traceable processing status.

A failure in one stage must not silently mark subsequent stages as completed.

## 4. Document validation

### 4.1 Input validation

Before processing a document, validate:

- User ownership.
- File presence.
- Actual file format.
- Detected media type.
- File size.
- File integrity.
- Supported format.
- Upload authorization.

Do not rely exclusively on the filename extension.

### 4.2 Content integrity

Calculate and retain a content checksum.

Use the checksum to:

- Verify stored content integrity.
- Detect identical file content.
- Support idempotent processing.
- Detect unexpected content changes.

A matching checksum must not automatically merge two distinct document identities.

### 4.3 Document registration

Register the document and its version before starting expensive processing.

Persist:

- Document identity.
- User ownership.
- Version identity.
- Original object reference.
- Content checksum.
- File metadata.
- Registration timestamp.
- Processing operation.

Document registration and document processing completion are separate states.

## 5. Content extraction

### 5.1 Supported formats

Initial supported formats:

- PDF.
- DOCX.
- TXT.

Format-specific extraction must preserve as much useful structure as the source supports.

### 5.2 PDF extraction

Extract:

- Text.
- Page boundaries.
- Available paragraph structure.
- Heading information where detectable.
- Table information where supported.
- Source-location metadata.

Preserve page references for citation.

PDF extraction must handle:

- Multi-page files.
- Empty pages.
- Mixed text and image pages.
- Incorrect reading order.
- Extraction failures.
- Malformed documents.

### 5.3 DOCX extraction

Extract:

- Paragraphs.
- Headings.
- Lists.
- Tables.
- Document order.
- Available structural hierarchy.

Preserve relationships between headings and their associated content.

### 5.4 TXT extraction

Extract text while preserving:

- Line ordering.
- Paragraph boundaries.
- Encoding information where available.
- Original content references.

### 5.5 OCR

OCR may be used for scanned or image-based documents.

However, OCR must remain an optional capability until its implementation and technology dependencies are explicitly approved.

When OCR is unavailable:

- Identify the extraction limitation.
- Preserve the original document.
- Record the failure or unsupported-content state.
- Do not invent extracted text.

When OCR is implemented, preserve:

- OCR engine and version.
- Extraction timestamp.
- Confidence information where available.
- Page or image location.
- Relevant processing metadata.

OCR output must not automatically be treated as perfectly accurate.

## 6. Structural extraction

The purpose of structural extraction is to preserve document organization before chunking.

Identify where possible:

- Document title.
- Headings.
- Subheadings.
- Paragraphs.
- Lists.
- Tables.
- Page boundaries.
- Sections.
- Content order.

Represent extracted content as an ordered structure.

A logical representation may be:

```text
Document
  Section
    Subsection
      Paragraph
      Paragraph
      Table
  Section
    Paragraph
```

This representation is conceptual and does not require a specific storage format.

Preserving document hierarchy improves chunking and later evidence interpretation.

## 7. Content normalization

Normalize extracted content without changing its meaning.

Operations may include:

- Whitespace normalization.
- Encoding normalization.
- Removal of extraction artifacts.
- Standardization of line endings.
- Paragraph boundary normalization.
- Unicode normalization where appropriate.

Preserve:

- Original content.
- Structural hierarchy.
- Numerical values.
- Units.
- Dates.
- Currency.
- Names.
- Important punctuation.
- Source locations.

Do not remove information that changes the meaning of a statement.

For example, a percentage, negative sign, decimal point, or measurement unit must not be discarded.

## 8. Structure-aware chunking

### 8.1 Objective

Divide extracted document content into retrieval units while preserving meaningful context and source provenance.

Chunking must not split content arbitrarily when meaningful structural boundaries are available.

### 8.2 Chunking priority

Use the following boundary preference:

1. Document section boundaries.
2. Subsection boundaries.
3. Paragraph boundaries.
4. Sentence boundaries.
5. Token or character limits.

The exact strategy must respect the approved chunk-size and overlap configuration.

### 8.3 Chunk generation

For each chunk:

1. Identify its parent section.
2. Collect eligible content.
3. Check the configured size limit.
4. Split oversized content at the best available boundary.
5. Preserve ordering.
6. Attach source-location metadata.
7. Calculate the content checksum.
8. Assign a stable chunk identity.
9. Persist the chunk and its provenance.

### 8.4 Chunk overlap

Overlapping chunks may be used when context preservation requires it.

Overlap must be configurable and evaluated against retrieval quality.

Avoid excessive overlap because it can produce duplicate evidence and unnecessary embedding costs.

### 8.5 Table handling

Tables must preserve the relationship between:

- Headers.
- Rows.
- Columns.
- Cell values.
- Associated section or page.

Do not convert a table into disconnected values without preserving their meaning.

Where the extraction method cannot reliably interpret a table, mark the limitation rather than producing misleading structured content.

### 8.6 Chunk metadata

Every chunk must retain, where available:

- Chunk ID.
- Document ID.
- Document version ID.
- Extraction ID.
- Chunk sequence.
- Section title.
- Page reference.
- Structural location.
- Chunking strategy.
- Chunking version.
- Content checksum.

### 8.7 Chunk validation

Validate:

- Non-empty content.
- Correct source association.
- Valid sequence.
- Correct document version.
- Size constraints.
- Provenance availability.
- No accidental cross-document mixing.

A chunk must never contain content from two unrelated document versions.

## 9. Embedding generation

### 9.1 Purpose

Generate vector representations of document chunks to support semantic retrieval.

Use the approved sentence-transformers ecosystem and embedding infrastructure.

### 9.2 Processing steps

1. Retrieve the validated chunk.
2. Normalize its embedding input.
3. Select the approved embedding model.
4. Generate the vector.
5. Validate vector dimensions.
6. Validate numeric values.
7. Record model metadata.
8. Persist the embedding.
9. Submit it for vector indexing.
10. Record indexing status.

### 9.3 Embedding metadata

Track:

- Model identifier.
- Model version.
- Vector dimensions.
- Preprocessing version.
- Creation timestamp.
- Chunk reference.
- Document version reference.

### 9.4 Embedding failures

If embedding generation fails:

- Preserve the original document.
- Preserve extracted content.
- Preserve validated chunks.
- Record the failure.
- Allow controlled retries.
- Prevent duplicate embedding operations.

Embedding generation must be idempotent under the approved processing contract.

### 9.5 Model consistency

A query embedding and document embedding must use compatible model representations.

Model changes must follow a controlled migration strategy.

Do not mix incompatible vector dimensions or preprocessing configurations in the same retrieval operation.

## 10. Hybrid indexing

Support two complementary retrieval mechanisms.

### 10.1 Vector indexing

Use pgvector to index document chunk embeddings.

Vector similarity helps identify semantically related passages even when query wording differs from the original text.

### 10.2 Keyword indexing

Use PostgreSQL full-text search for lexical matching.

Keyword retrieval is especially useful for:

- Exact terminology.
- Names.
- Technical terms.
- Identifiers.
- Numerical references.
- Specific phrases.

### 10.3 Metadata indexing

Support filters for:

- User ownership.
- Document identity.
- Document version.
- Chunk identity.
- Page or section.
- Document type.
- Document lifecycle status.

### 10.4 Index consistency

Index entries must reference the correct chunk and document version.

If a document version changes, stale entries must not silently appear as current evidence.

Indexing failures must remain observable and recoverable.

## 11. Document query understanding

Before retrieval, normalize the user's question.

Identify, where supported:

- Query terms.
- Entities.
- Relevant document references.
- Version constraints.
- Page or section constraints.
- Dates.
- Numerical constraints.
- Requested comparison.
- Requested answer format.

Preserve the original question.

Do not rewrite the query in a way that removes important constraints.

### 11.1 Query types

Support logical query categories such as:

- Factual lookup.
- Definition lookup.
- Explanation.
- Numerical lookup.
- Comparison.
- Multi-document comparison.
- Historical document lookup.
- Summary of selected passages.

These categories guide retrieval and answer assembly. They do not authorize unsupported content generation.

## 12. Hybrid document retrieval

### 12.1 Retrieval workflow

1. Validate user authorization.
2. Normalize the query.
3. Identify relevant documents and versions.
4. Apply metadata filters.
5. Retrieve vector candidates.
6. Retrieve keyword candidates.
7. Aggregate candidates.
8. Remove duplicate references.
9. Apply relevance ranking.
10. Select evidence candidates.

### 12.2 Candidate aggregation

Combine vector and keyword retrieval results.

Preserve:

- Chunk identity.
- Document identity.
- Version identity.
- Source location.
- Retrieval method.
- Retrieval score.
- Provenance.

Do not merge different source passages simply because they have similar content.

### 12.3 Ranking

Ranking may consider:

- Semantic similarity.
- Keyword relevance.
- Query-term coverage.
- Document and version constraints.
- Source location.
- Evidence completeness.
- Duplicate overlap.
- Query intent.

The ranking method must be evaluated using Raven-specific retrieval datasets.

### 12.4 Reranking

A conventional cross-encoder reranker may be evaluated where it provides measurable benefit.

A reranker must:

- Operate on retrieved candidates.
- Preserve source references.
- Return a deterministic, testable ranking output under its configured model.
- Respect retrieval budgets.
- Not create unsupported facts.

Do not add a reranker dependency automatically without evaluating its quality and resource cost.

### 12.5 Retrieval stopping

Stop retrieval when:

- Sufficient relevant evidence is available.
- Additional retrieval has low expected value.
- The retrieval budget is exhausted.
- No additional relevant candidates exist.

Do not retrieve excessive context without justification.

## 13. Evidence selection

Evidence selection determines which retrieved passages can support an answer.

For each candidate passage, evaluate:

- Relevance to the question.
- Directness of support.
- Source location availability.
- Document version.
- Passage completeness.
- Conflicting evidence.
- Extraction reliability.

Select the smallest sufficient evidence set that supports the requested answer.

Avoid including irrelevant passages simply because they have high vector similarity.

### 13.1 Evidence classification

Classify evidence conceptually as:

- Directly supporting.
- Partially supporting.
- Contradicting.
- Contextual.
- Irrelevant.
- Insufficient.

The classification must be supported by deterministic or conventional NLP methods and validated logic.

If the system cannot reliably determine whether a passage supports a claim, it must not present that claim as verified.

## 14. Extractive answer assembly

### 14.1 Architectural constraint

Raven's core answer assembly must not depend on generative LLM APIs or locally hosted generative LLMs.

Use:

- Extractive sentence selection.
- Conventional NLP.
- Deterministic templates.
- Structured result composition.
- Rule-based formatting.

### 14.2 Answer assembly workflow

1. Receive the user's question.
2. Retrieve candidate evidence.
3. Select supporting passages.
4. Extract relevant sentences or structured values.
5. Organize evidence by question requirement.
6. Preserve qualifications and units.
7. Identify conflicts.
8. Apply a deterministic answer template.
9. Attach citations.
10. Validate the final response.

### 14.3 Numerical answers

For numerical questions:

- Preserve the original value.
- Preserve the unit.
- Preserve the relevant date or period.
- Preserve currency where applicable.
- Avoid unsupported calculations.
- Show the source evidence.

If a calculation is required, use deterministic arithmetic over validated extracted values.

### 14.4 Comparison answers

For comparison questions:

1. Identify the entities or attributes being compared.
2. Retrieve evidence for each.
3. Verify that contexts are comparable.
4. Normalize units only where conversion is valid.
5. Identify missing attributes.
6. Present the comparison.
7. Attach citations to the relevant values.

Do not compare incompatible periods, currencies, units, or product variants without explicitly explaining the difference.

### 14.5 Summary answers

A summary may be constructed by selecting representative sentences and grouping them by document section or topic.

The system must:

- Preserve the source's meaning.
- Avoid introducing unsupported conclusions.
- Preserve important exceptions.
- Preserve conflicting evidence.
- Attach source references.

If the requested summary cannot be produced reliably through extractive processing, communicate the limitation.

## 15. Citation generation and validation

### 15.1 Citation requirements

Every document-grounded factual statement must be traceable to supporting evidence.

A citation should identify, where available:

- Document title.
- Document ID.
- Document version.
- Page number.
- Section.
- Chunk or evidence reference.

### 15.2 Citation generation

Generate citations from stored provenance metadata.

Never fabricate:

- Page numbers.
- Section headings.
- Document versions.
- Source references.
- Supporting passages.

### 15.3 Citation validation

Before returning the answer:

1. Verify that the cited document exists.
2. Verify that the user is authorized to access it.
3. Verify that the version matches the retrieved evidence.
4. Verify that the chunk exists.
5. Verify that the source location is valid where available.
6. Verify that the citation supports the associated claim.
7. Reject or qualify unsupported claims.

If citation validation fails, do not silently return a fabricated citation.

## 16. Insufficient evidence and conflicting documents

### 16.1 Insufficient evidence

When retrieved evidence is insufficient:

- State that the document does not provide enough information.
- Identify the missing information where possible.
- Avoid guessing.
- Do not fabricate an answer.

### 16.2 Conflicting evidence

When documents contain conflicting information:

- Preserve both source references.
- Identify document versions.
- Compare timestamps or validity context where available.
- Avoid selecting a winner solely based on retrieval score.
- Report the conflict when it cannot be resolved.

A newer document is not automatically authoritative unless the source context supports that interpretation.

## 17. Personal memory and document retrieval separation

Document RAG and personal memory retrieval are separate capabilities.

Personal memory retrieval operates on authoritative memory records.

Document retrieval operates on document chunks and evidence.

The Orchestrator may request either or both.

Document retrieval must not:

- Automatically create personal memories.
- Update memory records.
- Change memory confidence.
- Bypass the memory candidate lifecycle.

Document-derived memory extraction must use the separately authorized workflow defined in the Memory Engine extraction algorithms.

## 18. Document lifecycle and deletion

Document deletion must cover:

- Original files.
- Document versions.
- Extracted representations.
- OCR artifacts, where applicable.
- Chunks.
- Chunk embeddings.
- Vector indexes.
- Keyword indexes.
- Cached retrieval results.
- Cached evidence.
- Pending processing operations.

Deleting a document must invalidate its applicable derived retrieval data.

Workers must verify document lifecycle and version state before committing new derived content.

Document-derived personal memory provenance must be evaluated separately.

Unrelated personal memories must not be deleted automatically.

## 19. Idempotency and recovery

Every processing stage must support safe retries.

Requirements:

- Durable operation identity.
- Idempotent processing.
- Duplicate detection.
- Retry limits.
- Failure metadata.
- Version validation.
- Stale-job rejection.
- Partial recovery.
- Deletion awareness.

A worker must not recreate content from a deleted document.

A timeout must not be interpreted as proof that an operation failed.

## 20. Quality evaluation

Evaluate the document intelligence pipeline using Raven-specific datasets.

### Parsing quality

- Text extraction completeness.
- Structural preservation.
- Reading-order accuracy.
- Page-location accuracy.
- Table extraction quality where supported.

### Chunking quality

- Boundary quality.
- Context preservation.
- Source-location accuracy.
- Chunk completeness.
- Duplicate overlap.

### Retrieval quality

- Precision.
- Recall.
- Ranking quality.
- Evidence coverage.
- Version correctness.

### Answer quality

- Evidence support.
- Numerical accuracy.
- Citation correctness.
- Unsupported-answer rate.
- Conflict preservation.
- Completeness.

### Deletion quality

- Dependency coverage.
- Index invalidation.
- Cache invalidation.
- Stale-job prevention.
- Post-deletion retrieval verification.

Do not claim quality metrics without executing the relevant evaluation.

## 21. Performance and resource budgets

Measure:

- Parsing duration.
- Chunking duration.
- Embedding throughput.
- Indexing latency.
- Retrieval latency.
- Evidence-selection latency.
- Answer-assembly latency.
- Storage utilization.
- Worker utilization.

Separate upload response latency from background processing completion.

Apply configurable limits to:

- File size.
- Number of chunks.
- Embedding batches.
- Retrieval candidates.
- Retrieval iterations.
- Processing retries.
- Resource consumption.

Do not introduce a separate vector database or distributed processing platform without workload evidence.

## 22. Security requirements

- Enforce user ownership.
- Validate document access on retrieval.
- Treat document contents as untrusted data.
- Do not execute embedded scripts or macros.
- Protect object-storage references.
- Avoid exposing sensitive document content in logs.
- Prevent cross-user vector and keyword retrieval.
- Validate document lifecycle before returning cached results.
- Enforce authorization during deletion.

## 23. Observability

Record the lifecycle of each document processing operation.

Use the approved correlation identifiers and document references.

Measure:

- Upload success and failure.
- Parsing success and failure.
- Extraction completeness.
- Chunk count.
- Embedding status.
- Indexing status.
- Retrieval latency.
- Evidence selection.
- Citation validation.
- Deletion completion.
- Retry counts.

Do not log complete document contents unnecessarily.

## 24. Acceptance criteria

The document intelligence algorithm specification is satisfied when the implementation supports:

1. Reliable document registration and validation.
2. Supported-format content extraction.
3. Structural extraction.
4. Structure-aware chunking.
5. Source-location preservation.
6. Embedding generation and validation.
7. Hybrid vector and keyword retrieval.
8. Evidence selection.
9. Extractive answer assembly.
10. Citation generation and validation.
11. Insufficient-evidence handling.
12. Conflict preservation.
13. Document-version correctness.
14. Personal memory and document retrieval separation.
15. Idempotent processing and recovery.
16. Complete deletion propagation.
17. User isolation.
18. Quality and performance evaluation.

## 25. Final architectural principle

Raven must be able to answer questions from documents without losing the connection between an answer and its original evidence.

Every extracted passage must retain its source.

Every retrieval result must retain its version.

Every factual answer must be supported by evidence.

Every deletion must account for derived representations.

Document intelligence must remain separate from personal memory while sharing the approved Memory Engine infrastructure.
