# Amendment — Document Processing, NLP and RAG Technologies

**File:** `docs/technology/05-nlp-and-machine-learning-stack.md`  
**Applies to:** Phase 7.5 — NLP and Machine Learning Stack

## 1. Purpose

Extend Raven's existing NLP and machine learning stack to support document intelligence and Retrieval-Augmented Generation (RAG).

The extension must support:

- PDF, DOCX and TXT document processing.
- Text extraction and normalization.
- Document structure preservation.
- Page and section identification.
- Table and list extraction where supported.
- Structure-aware document chunking.
- Embedding generation.
- Hybrid document retrieval.
- Evidence selection.
- Extractive answer assembly.
- Citation and provenance validation.

The existing constraint against generative LLM APIs and locally hosted generative LLMs remains unchanged.

## 2. Existing Technology Baseline

The following technologies remain part of the established baseline.

| Technology | Responsibility |
|---|---|
| spaCy | Conventional NLP and linguistic processing |
| scikit-learn | Statistical methods and classification |
| sentence-transformers ecosystem | Embedding generation |
| RapidFuzz | String similarity and fuzzy matching |
| dateparser | Date and time normalization |
| NumPy | Numerical operations |
| pandas | Structured data processing |

Document processing extends this stack through specialized extraction libraries.

## 3. Document Format Support

The initial document intelligence implementation should support:

| Format | Initial Support | Processing Requirement |
|---|---|---|
| PDF | Yes | Text extraction with page-level provenance |
| DOCX | Yes | Paragraph, heading, table and structural extraction where supported |
| TXT | Yes | Encoding validation and text normalization |
| Scanned PDF | Deferred | Requires OCR evaluation and explicit approval |
| Images | Deferred | Requires image extraction and OCR capability |
| Other formats | Deferred | Add only after evaluating requirements |

File type must be detected and validated using actual file content and format signatures where possible.

File extensions alone must not be trusted.

## 4. Document Parsing Technology

### 4.1 PDF Extraction

**Proposed library: pypdf**

Purpose:

- Extract text from text-based PDF files.
- Preserve page boundaries.
- Provide page-level source locations.
- Support document metadata extraction where available.

Limitations:

- Scanned PDFs may contain no extractable text.
- Complex layouts may produce incorrect reading order.
- Tables and multi-column layouts may require additional processing.
- Extracted text quality must be validated.

The library must be evaluated against Raven's representative PDF dataset before being finalized.

### 4.2 DOCX Extraction

**Proposed library: python-docx**

Purpose:

- Extract paragraphs.
- Identify headings and document structure.
- Extract tables.
- Preserve paragraph and table ordering where supported.
- Retain useful document metadata.

Limitations:

- Complex layouts may not be represented completely.
- Text boxes, embedded objects and advanced formatting may require additional extraction capabilities.
- Reading order and table structure must be validated.

### 4.3 TXT Processing

Use Python's standard text-processing capabilities for initial TXT support.

Requirements:

- Validate encoding.
- Handle UTF-8 and common encoding variations safely.
- Normalize line endings.
- Preserve meaningful paragraph boundaries.
- Avoid destructive normalization.
- Record decoding failures.

No additional dependency is required for basic TXT processing.

## 5. Document Parsing Selection Policy

The initial recommended parser baseline is:

| Format | Recommended Initial Choice | Status |
|---|---|---|
| PDF | pypdf | Proposed, requires evaluation |
| DOCX | python-docx | Proposed, requires evaluation |
| TXT | Python standard library | Recommended baseline |
| Scanned PDF OCR | None | Deferred |
| Advanced layout extraction | None | Deferred |

Do not install additional parser libraries without first checking whether the existing choices satisfy the requirements.

Additional libraries may be evaluated if representative documents demonstrate limitations.

Selection criteria:

- Extraction completeness.
- Reading-order accuracy.
- Page and section provenance.
- Table preservation.
- Performance.
- Memory consumption.
- Dependency maintenance.
- License compatibility.
- Security considerations.

## 6. OCR Strategy

OCR is not part of the initial mandatory document-processing baseline.

Scanned PDFs and image-based documents must be detected where possible.

When text extraction produces insufficient content:

1. Mark the document as requiring OCR or unsupported extraction.
2. Preserve the original document.
3. Record the extraction limitation.
4. Avoid creating misleading empty or incomplete chunks.
5. Return an appropriate processing status.

OCR technology must be evaluated separately before implementation.

Any OCR addition must consider:

- Text recognition accuracy.
- Language support.
- Page layout preservation.
- Table extraction.
- CPU and memory requirements.
- Processing time.
- Privacy and local processing requirements.
- Dependency and deployment complexity.

Do not silently introduce cloud OCR services or external document-processing APIs.

## 7. Text Normalization

Normalization must improve retrieval without destroying source meaning.

Permitted operations include:

- Whitespace normalization.
- Line-ending normalization.
- Unicode normalization where appropriate.
- Removal of extraction artifacts when safely identifiable.
- Consistent representation of extracted structures.
- Preservation of meaningful punctuation and formatting boundaries.

The following must be preserved:

- Names.
- Dates.
- Numerical values.
- Units.
- Currency.
- Technical terminology.
- Negation.
- Section relationships.
- Table row and column relationships.
- Source locations.

The original extracted representation must remain available for provenance and reprocessing.

## 8. Structure-Aware Chunking

Document chunking must respect document structure.

Recommended hierarchy:

1. Document.
2. Section.
3. Subsection.
4. Paragraph.
5. Sentence.
6. Token or character boundary when necessary.

Chunking should:

- Prefer natural semantic boundaries.
- Preserve section context.
- Avoid separating important definitions from their explanations.
- Preserve table context.
- Avoid unnecessarily small chunks.
- Avoid oversized chunks.
- Support configurable overlap.
- Preserve page and section references.

Chunk size and overlap must be evaluated using retrieval-quality datasets rather than selected arbitrarily.

Chunking configuration and algorithm version must be recorded.

## 9. Table and Structured Content Handling

Tables require special handling because flattening them into plain text can destroy relationships.

The processing pipeline should preserve, where supported:

- Table identity.
- Row order.
- Column headers.
- Cell values.
- Table location.
- Associated section context.

A retrieved table value must retain enough surrounding information to explain what the value represents.

Do not treat isolated numerical cells as independently meaningful evidence.

If a parser cannot reliably preserve a table, mark the limitation rather than presenting corrupted content as accurate.

## 10. Embedding Generation

Continue evaluating the sentence-transformers ecosystem for embedding generation.

Document embedding requirements:

- Generate embeddings from validated chunks.
- Preserve chunk and document version references.
- Record model and preprocessing versions.
- Validate vector dimensions.
- Reject invalid numerical values.
- Support batch processing.
- Support retries and idempotency.
- Track indexing status.

Memory and document embeddings must remain separate logical domains.

A shared embedding model is acceptable initially if evaluation demonstrates sufficient quality for both use cases.

Do not assume that identical models guarantee identical retrieval quality across different domains.

## 11. Retrieval and Ranking

Document retrieval must use a hybrid approach.

### Semantic retrieval

Use pgvector-backed embeddings to retrieve semantically relevant document chunks.

### Keyword retrieval

Use PostgreSQL Full-Text Search to retrieve exact terms, identifiers, names and numerical references.

### Candidate aggregation

Combine candidates using an evaluated fusion or ranking method.

### Optional reranking

A non-generative reranker may be evaluated when retrieval quality demonstrates a need.

Requirements:

- Must be evaluated using Raven-specific datasets.
- Must preserve the original candidates.
- Must preserve provenance.
- Must respect resource budgets.
- Must not modify source content.

Reranking remains optional until measurable improvement justifies it.

## 12. Evidence Selection and Answer Assembly

Raven must distinguish retrieval relevance from evidence sufficiency.

Retrieved chunks should be evaluated for:

- Direct support.
- Partial support.
- Contradiction.
- Contextual relevance.
- Insufficient evidence.

Answer assembly must rely on:

- Extractive methods.
- Conventional NLP.
- Deterministic templates.
- Structured comparison.
- Rule-based evidence aggregation.

The system must not use generative LLM APIs or locally hosted generative LLMs to produce answers.

For unsupported questions, Raven must explicitly communicate insufficient evidence.

For conflicting documents, preserve the conflict and its source references rather than silently selecting one answer.

## 13. Citation and Provenance

Every document-derived answer must retain references to its supporting source material.

Where available, citations should identify:

- Document.
- Document version.
- Page.
- Section.
- Chunk.
- Relevant source location.

Citation validation must confirm:

1. The document exists.
2. The document version matches the retrieved chunk.
3. The chunk belongs to that document version.
4. The source location is valid where applicable.
5. The cited content supports the associated statement.

Do not generate page numbers or locations that the extraction process did not establish.

## 14. Document-to-Memory Extraction

Document intelligence and personal memory extraction remain separate workflows.

A document upload must not automatically create personal memories.

Where explicitly authorized:

1. Retrieve relevant document chunks.
2. Extract candidate facts using the approved memory extraction algorithms.
3. Preserve document and chunk provenance.
4. Submit candidates to the normal evaluation workflow.
5. Apply existing duplicate and contradiction resolution.
6. Activate memories only through the authorized resolution process.

Document-derived memories must remain traceable to their source documents.

## 15. Model and Dependency Governance

All NLP and machine learning dependencies must be evaluated for:

- License compatibility.
- Security.
- Maintenance.
- Reproducibility.
- Resource consumption.
- Deployment requirements.
- Model provenance.
- Version compatibility.

Model and library upgrades must not silently invalidate existing processing outputs.

Record relevant parser, extraction, normalization, chunking and embedding versions.

Do not automatically train on user documents or personal memory data.

## 16. Testing and Evaluation

Document processing must be evaluated using representative datasets.

### Extraction metrics

- Text extraction completeness.
- Reading-order accuracy.
- Page attribution accuracy.
- Table extraction accuracy.
- Encoding correctness.

### Chunking metrics

- Boundary quality.
- Context preservation.
- Section attribution.
- Chunk size distribution.
- Overlap effectiveness.

### Retrieval metrics

- Precision@K.
- Recall@K.
- Mean Reciprocal Rank.
- Normalized Discounted Cumulative Gain.
- Evidence coverage.

### Answer and citation metrics

- Evidence support accuracy.
- Citation correctness.
- Unsupported-answer rate.
- Numerical accuracy.
- Conflict preservation.
- Version correctness.

Thresholds must be established during Phase 12 — Testing and Evaluation.

## 17. Security and Privacy

Document processing must enforce:

- User ownership.
- Authorization checks.
- File type validation.
- File size limits.
- Safe parser execution.
- Resource limits.
- Temporary artifact cleanup.
- Secure handling of malformed files.
- No cross-user retrieval.
- Deletion propagation.

Treat uploaded documents as untrusted input.

Do not execute embedded scripts, macros or active content during document processing.

## 18. Technology Decisions and Deferred Items

| Capability | Decision |
|---|---|
| spaCy | Existing baseline |
| scikit-learn | Existing baseline |
| sentence-transformers ecosystem | Existing baseline |
| RapidFuzz | Existing baseline |
| dateparser | Existing baseline |
| PDF parser | pypdf proposed |
| DOCX parser | python-docx proposed |
| TXT parser | Python standard library |
| OCR | Deferred |
| Advanced layout extraction | Deferred |
| Table extraction enhancement | Evaluate if needed |
| Non-generative reranker | Optional, evaluation required |
| Generative LLM APIs | Not permitted |
| Locally hosted generative LLMs | Not permitted |

Proposed libraries must be evaluated and approved before becoming mandatory project dependencies.

## 19. Acceptance Criteria

The NLP and machine learning architecture is ready for implementation when:

- PDF, DOCX and TXT support is defined.
- Parser limitations are explicitly handled.
- Original documents remain unchanged.
- Extracted content preserves available structure and provenance.
- Chunking preserves meaningful document boundaries.
- Embeddings retain document and version references.
- Hybrid retrieval is supported.
- Evidence selection distinguishes relevance from sufficiency.
- Answers preserve citations and source locations.
- Personal memory and document intelligence remain separate.
- OCR and optional reranking remain controlled technology decisions.
- No generative LLM dependency is introduced.
  
