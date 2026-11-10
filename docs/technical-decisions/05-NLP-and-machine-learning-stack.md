# Phase 7.5 — NLP & Machine Learning Stack

> **Document history:** This file contains the original Phase 7.5 specification (unchanged since commit `80dbd98`), followed by the Document Processing, NLP and RAG Technologies amendment from commit `71511d5`, appended at the end of this file. That amendment was previously committed into `03-vector-search-and-embedding-infrastructure.md` by mistake and has been moved here. The amendment extends the original decisions; it does not replace them.

## 1. Purpose

This document defines Raven's Natural Language Processing (NLP) and Machine Learning (ML) architecture.

It establishes the technologies, processing responsibilities, model boundaries, inference workflows, evaluation requirements, and integration patterns used by the Memory Engine, Research Engine, and Agent Orchestrator.

Raven uses a hybrid approach combining:

- Deterministic algorithms and rules.
- Conventional NLP techniques.
- Statistical methods.
- Selective non-generative machine learning.
- Embedding models.

The primary objective is to extract, classify, normalize, evaluate, and retrieve information reliably.

**Core constraint:** Raven's core processing architecture will not use generative LLM APIs or locally hosted generative LLMs.

---

## 2. Architectural Principles

The NLP and ML stack follows these principles:

1. Quality and correctness take priority over processing speed.
2. ML predictions are signals, not authoritative decisions.
3. Deterministic validation must protect important state transitions.
4. Every model must have a clearly defined responsibility.
5. Model versions and configurations must be traceable.
6. Uncertainty must be preserved rather than hidden.
7. Models must be evaluated using Raven-specific datasets.
8. Model outputs must not bypass ownership, privacy, or authorization boundaries.
9. Embedding generation and generative text generation are different capabilities.
10. Models must be replaceable without redesigning the entire architecture.
11. Expensive ML operations should be used selectively.
12. No single model should become a dependency for every processing operation.

---

## 3. Technology Stack

The initial recommended stack is:

| Technology | Primary responsibility |
|---|---|
| spaCy | NLP pipeline, tokenization, linguistic processing, entity recognition |
| scikit-learn | Classification, statistical ML, feature-based prediction |
| sentence-transformers ecosystem | Embedding generation and semantic representations |
| RapidFuzz | Fuzzy string matching |
| dateparser | Date and time expression parsing |
| NumPy | Numerical computation |
| pandas | Dataset preparation and evaluation |
| Python | Primary implementation language |

These technologies form the initial baseline, not a requirement to use every library in every engine.

### 3.1 spaCy

<text>**Purpose:** Conventional NLP processing.</text>

Potential responsibilities:

- Tokenization.
- Sentence segmentation.
- Part-of-speech tagging.
- Lemmatization.
- Named entity recognition.
- Dependency parsing where useful.
- Rule-based matching.
- Text processing pipelines.

spaCy is particularly useful for extracting structured linguistic information from natural language.

It must not be treated as a complete factual understanding system.

### 3.2 scikit-learn

<text>**Purpose:** Conventional statistical machine learning.</text>

Potential responsibilities:

- Text classification.
- Feature-based classification.
- Similarity and clustering experiments.
- Classification evaluation.
- Baseline predictive models.
- Statistical feature analysis.

Models should remain interpretable and testable where possible.

### 3.3 sentence-transformers ecosystem

<text>**Purpose:** Semantic embedding generation.</text>

Potential responsibilities:

- Text embeddings.
- Semantic similarity.
- Query-to-document representations.
- Candidate retrieval.
- Related-content discovery.

Embeddings are numerical representations, not generated answers.

The embedding model selection process is defined in Phase 7.3.

### 3.4 RapidFuzz

<text>**Purpose:** Efficient fuzzy string matching.</text>

Potential responsibilities:

- Name matching.
- Alias matching.
- Approximate text matching.
- Candidate generation for entity resolution.
- Duplicate detection signals.

Fuzzy matching alone must never authorize a destructive merge.

### 3.5 dateparser

<text>**Purpose:** Date and time expression parsing.</text>

Potential responsibilities:

- Extracting date expressions.
- Parsing relative dates.
- Normalizing date representations.
- Supporting temporal interpretation.

Ambiguous dates must retain uncertainty and contextual information.

### 3.6 NumPy and pandas

NumPy supports numerical operations and feature calculations.

pandas supports:

- Dataset preparation.
- Evaluation data processing.
- Metrics aggregation.
- Error analysis.
- Experiment comparisons.

Neither library should become a substitute for authoritative database storage.

---

## 4. Processing Architecture

Raven uses a layered NLP and ML processing architecture.

### Layer 1 — Input Validation

Responsibilities:

- Validate incoming data.
- Check ownership and authorization.
- Validate supported input types.
- Enforce size and format limits.
- Preserve original source content.

This layer is deterministic.

### Layer 2 — Text Normalization

Responsibilities:

- Normalize whitespace.
- Identify text segments.
- Preserve sentence boundaries.
- Normalize safe formatting variations.
- Preserve dates, units, numbers, negation, and meaningful punctuation.

This layer combines deterministic processing and conventional NLP.

### Layer 3 — Linguistic Processing

Responsibilities:

- Tokenization.
- Sentence segmentation.
- Lemmatization.
- Part-of-speech tagging.
- Named entity recognition.
- Rule-based pattern detection.

spaCy is the initial recommended library.

### Layer 4 — Feature Extraction

Responsibilities:

- Extract linguistic features.
- Identify entity and attribute candidates.
- Detect temporal expressions.
- Extract keyword and structural signals.
- Prepare features for classification.

### Layer 5 — Statistical and ML Processing

Responsibilities:

- Classification.
- Semantic similarity.
- Confidence estimation.
- Candidate ranking.
- Clustering where appropriate.

Use scikit-learn and the sentence-transformers ecosystem where suitable.

### Layer 6 — Decision and Validation

Responsibilities:

- Evaluate predictions.
- Apply deterministic constraints.
- Preserve uncertainty.
- Validate evidence and context.
- Authorize state transitions through the owning engine.

ML output must not directly modify authoritative records without the required validation.

---

## 5. Memory Engine NLP & ML Responsibilities

The Memory Engine uses NLP and ML to extract and organize information from user-provided content.

### 5.1 Memory ingestion and extraction

Potential techniques:

- Tokenization.
- Sentence segmentation.
- Named entity recognition.
- Linguistic feature extraction.
- Rule-based fact pattern detection.
- Classification of information types.
- Temporal expression parsing.

The extraction pipeline must preserve:

- Speaker identity.
- Original wording.
- Negation.
- Modality.
- Attribution.
- Temporal context.
- Uncertainty.

For example:

"I might move to Bangalore next year."

This must not automatically become:

"The user lives in Bangalore."

The original statement expresses a possibility about a future event, not a confirmed current fact.

### 5.2 Memory classification

Classification may identify categories such as:

- Personal Preferences.
- Goals.
- Decisions.
- Important Events.
- Relationships.
- Knowledge.
- Projects.
- Commitments.

Classification outputs must remain distinguishable from explicit user statements.

### 5.3 Importance and confidence estimation

NLP and ML may provide signals for:

- Personal relevance.
- Information density.
- Temporal significance.
- Contextual significance.
- Candidate importance.
- Extraction confidence.

Importance and confidence remain separate dimensions.

A high importance score must not compensate for low factual confidence.

### 5.4 Entity resolution

Potential techniques:

- Named entity recognition.
- Exact matching.
- Normalized string matching.
- Fuzzy matching.
- Semantic similarity.
- Context and attribute comparison.

Entity resolution must use the Memory Engine's established resolution workflow.

A similar name does not prove that two mentions refer to the same entity.

### 5.5 Memory retrieval

Potential techniques:

- Embedding generation.
- Semantic similarity.
- Keyword matching.
- Feature-based ranking.
- Query classification.

The retrieval architecture remains hybrid. Vector similarity is not the only retrieval signal.

### 5.6 Consolidation and maintenance

Potential techniques:

- Similarity-based candidate grouping.
- Statistical relevance signals.
- Temporal feature analysis.
- Classification of candidate relationships.

Derived conclusions must retain references to their original memories.

---

## 6. Research Engine NLP & ML Responsibilities

The Research Engine uses NLP and ML to process external information and improve evidence retrieval.

### 6.1 Query understanding

Potential techniques:

- Tokenization.
- Keyword extraction.
- Entity recognition.
- Query classification.
- Temporal expression parsing.
- Attribute identification.

The Research Engine must preserve the user's original query.

### 6.2 Content extraction

Potential techniques:

- Sentence segmentation.
- Named entity recognition.
- Text normalization.
- Table and document structure extraction.
- Keyword extraction.
- Statistical feature extraction.

The extraction pipeline must preserve source attribution and original content references.

### 6.3 Fact and claim extraction

NLP may identify candidate:

- Facts.
- Claims.
- Opinions.
- Predictions.
- Estimates.
- Statistics.
- Events.
- Definitions.
- Relationships.

The classification of a statement does not establish that the statement is true.

### 6.4 Source and evidence evaluation

Statistical and ML signals may support:

- Source relevance.
- Content similarity.
- Evidence candidate ranking.
- Duplicate or syndicated content detection.
- Temporal relevance.

Source reliability and fact confidence must remain separate.

### 6.5 Research retrieval

Potential techniques:

- Semantic embeddings.
- Keyword search.
- Entity matching.
- Attribute matching.
- Temporal filtering.
- Feature-based ranking.

Research retrieval must preserve source and evidence references.

---

## 7. Agent Orchestrator NLP & ML Responsibilities

The Orchestrator may use conventional NLP and statistical classification to support request understanding.

Potential responsibilities:

- Intent classification.
- Entity and reference extraction.
- Query complexity estimation.
- Task category prediction.
- Priority signals.
- Routing confidence estimation.

### 7.1 Intent classification

The Orchestrator may classify requests into categories such as:

- Memory retrieval.
- Memory update.
- Research.
- Research refresh.
- Comparison.
- Multi-step workflow.
- Direct response.
- Clarification required.

Classification must be validated against the actual request and available context.

### 7.2 Routing decisions

ML may suggest a destination engine.

However, the final routing decision must respect capability ownership.

For example:

- Historical personal information belongs to the Memory Engine.
- External information discovery belongs to the Research Engine.
- Cross-engine coordination belongs to the Orchestrator.

An ML classifier cannot override these boundaries.

### 7.3 Confidence and ambiguity

When intent confidence is insufficient:

- Use additional authorized context.
- Evaluate alternative interpretations.
- Apply deterministic routing rules.
- Ask for clarification when necessary.

Do not force a low-confidence classification into a definitive routing decision.

---

## 8. Rule-Based and ML Decision Boundaries

Raven must clearly distinguish which operations can use ML and which require deterministic control.

| Operation | Primary approach |
|---|---|
| Input validation | Deterministic |
| Authorization | Deterministic |
| Ownership validation | Deterministic |
| Text normalization | Hybrid |
| Entity extraction | NLP + validation |
| Memory classification | Hybrid |
| Importance estimation | Hybrid |
| Confidence estimation | Hybrid |
| Semantic similarity | Embedding model |
| Entity matching | Hybrid |
| Duplicate detection | Hybrid |
| Contradiction detection | Hybrid |
| Research source evaluation | Hybrid |
| Final verification qualification | Evidence rules + validation |
| Task state transitions | Deterministic |
| Deletion propagation | Deterministic |
| Idempotency | Deterministic |
| Final result validation | Deterministic controls |

This table describes the primary approach, not an exclusive implementation method.

### 8.1 Non-negotiable deterministic controls

The following operations must never depend solely on an ML prediction:

- Authorization.
- User isolation.
- Data ownership.
- Deletion.
- Database integrity.
- Task lifecycle transitions.
- Idempotency.
- Final persistence validation.
- Security policy enforcement.

---

## 9. Model Output and Confidence Management

Every ML-derived output must carry sufficient metadata for interpretation and traceability.

Conceptual metadata:

| Field | Purpose |
|---|---|
| `model_id` | Model identifier |
| `model_version` | Model version |
| `operation_type` | Processing operation |
| `input_reference` | Input record reference |
| `output_reference` | Result reference |
| `score_type` | Meaning of the score |
| `score_value` | Calculated value, where applicable |
| `scoring_method` | Scoring method |
| `evaluated_at` | Evaluation timestamp |
| `calibration_status` | Whether calibration has been evaluated |

### 9.1 Confidence is not universal

A confidence score from one model or task cannot automatically be compared with another.

For example:

- Extraction confidence.
- Entity matching confidence.
- Source reliability.
- Fact confidence.
- Intent classification confidence.

These are different measurements.

### 9.2 Calibration

Model confidence must be evaluated against labelled data where possible.

A score of 0.90 must not automatically be interpreted as a 90% probability of truth.

Calibration status and evaluation methodology must be documented.

### 9.3 Uncertainty handling

Possible outcomes include:

- High confidence.
- Medium confidence.
- Low confidence.
- Insufficient evidence.
- Ambiguous.
- Needs review.

Low-confidence outputs may be retained as candidates when appropriate, but must not silently become authoritative facts.

---

## 10. Model Registry and Version Management

Raven should maintain a controlled model registry.

The registry must record:

- Model identifier.
- Model version.
- Model purpose.
- Model family.
- Input requirements.
- Output format.
- Embedding dimension, where applicable.
- Preprocessing configuration.
- Evaluation results.
- Activation status.
- Deployment configuration.
- Creation and retirement timestamps.

### 10.1 Versioning policy

- Production model versions must be identifiable.
- Model changes must be evaluated before activation.
- Model outputs must retain version references.
- Rollback must be possible where practical.
- Incompatible embedding versions must not be mixed.
- Reprocessing after model changes must be controlled.

### 10.2 Model replacement

A model should be replaceable without changing the ownership boundaries or core business contracts.

For example, replacing one entity recognition model should not require redesigning the Memory Engine's entity data model.

---

## 11. Training and Evaluation Data

Raven must establish dedicated evaluation datasets for its important NLP and ML operations.

Potential datasets include:

### Memory

- Atomic fact extraction examples.
- Explicit versus inferred statements.
- Memory category classification.
- Importance evaluation.
- Entity resolution pairs.
- Duplicate and contradiction examples.
- Retrieval relevance judgements.

### Research

- Query intent examples.
- Research query decomposition examples.
- Entity and attribute extraction.
- Fact and claim classification.
- Source relevance examples.
- Evidence quality examples.
- Contradiction examples.
- Research retrieval relevance judgements.

### Orchestrator

- Intent classification examples.
- Routing examples.
- Ambiguous request examples.
- Task complexity examples.
- Dependency identification examples.

### 11.1 Dataset governance

Evaluation data must:

- Respect privacy and authorization.
- Avoid unnecessary personal information.
- Include representative edge cases.
- Preserve annotation definitions.
- Record dataset versions.
- Support repeatable evaluation.
- Separate training, validation, and test data where model training is used.

### 11.2 User data policy

User data must not automatically become model training data.

Any future training or fine-tuning workflow requires a separate privacy, consent, security, and governance decision.

---

## 12. Model Evaluation Metrics

Different operations require different metrics.

### 12.1 Classification

- Precision.
- Recall.
- F1 score.
- Confusion matrix.
- Class-specific error rates.

### 12.2 Entity recognition and extraction

- Entity precision.
- Entity recall.
- Entity F1.
- Extraction completeness.
- Boundary accuracy.
- Attribution accuracy.
- Negation preservation.

### 12.3 Entity resolution

- Match precision.
- Match recall.
- False merge rate.
- False split rate.
- Ambiguous-match rate.

False merges must receive particular attention because they can corrupt authoritative memory relationships.

### 12.4 Embedding and retrieval

- Recall@K.
- Precision@K.
- MRR.
- nDCG.
- Retrieval latency.

### 12.5 Confidence and calibration

- Calibration error.
- Brier score where applicable.
- Reliability diagrams.
- Error rates by confidence category.

### 12.6 Evaluation policy

No universal target is finalized here.

Targets must be selected according to the risk and impact of each operation during Phase 12 — Testing & Evaluation.

---

## 13. Inference Architecture

NLP and ML inference must be separated logically from the business logic that consumes the outputs.

### 13.1 Inference responsibilities

An inference component may:

- Load a configured model.
- Validate input.
- Execute inference.
- Validate output format.
- Return model metadata.
- Record processing duration and status.

It must not independently authorize changes to authoritative engine records.

### 13.2 Execution modes

Raven may use:

- In-process inference for lightweight operations.
- Dedicated inference workers for resource-intensive operations.
- Asynchronous inference for batch processing.
- Controlled batch inference for backfills.

The exact deployment model depends on workload measurements.

### 13.3 Resource management

Inference must account for:

- CPU usage.
- Memory consumption.
- Model loading time.
- Batch size.
- Concurrency.
- Queue delay.
- Latency.
- Failure recovery.

Resource-heavy inference must not exhaust capacity needed for critical application operations.

---

## 14. Security and Privacy

NLP and ML processing must follow Raven's security and privacy architecture.

Requirements:

- Process only authorized input.
- Maintain user isolation.
- Avoid unnecessary copies of sensitive text.
- Protect model artifacts and configuration.
- Avoid sensitive data in logs.
- Restrict access to evaluation datasets.
- Apply retention and deletion rules to derived outputs.
- Prevent unauthorized training-data use.
- Validate outputs before persistence.
- Preserve provenance and model version information.

Embeddings and model-derived metadata must be protected according to the sensitivity of their source information.

---

## 15. Failure Handling

### 15.1 Model unavailable

- Record the failure.
- Retry where appropriate.
- Preserve the source record.
- Use deterministic fallback processing if suitable.
- Mark unsupported operations clearly.

### 15.2 Invalid model output

- Reject invalid output.
- Preserve original input.
- Record validation failure.
- Do not update authoritative records.

### 15.3 Low-confidence output

- Preserve uncertainty.
- Retain as a candidate where appropriate.
- Request additional evidence or review when needed.
- Avoid automatic destructive action.

### 15.4 Model version incompatibility

- Reject incompatible output.
- Prevent mixed embedding spaces.
- Route through the controlled migration process.
- Preserve existing valid representations.

### 15.5 Resource exhaustion

- Apply bounded concurrency.
- Use background queues where appropriate.
- Apply backpressure.
- Preserve task state.
- Retry only when safe.

---

## 16. Testing Requirements

The NLP and ML stack must eventually be tested for:

### Functional correctness

- Text normalization.
- Entity recognition.
- Classification.
- Temporal extraction.
- Embedding generation.
- Model output validation.

### Semantic correctness

- Negation preservation.
- Speaker attribution.
- Temporal context.
- Ambiguous entity handling.
- Explicit versus inferred classification.
- Candidate versus authoritative record separation.

### Reliability

- Model unavailability.
- Invalid outputs.
- Version changes.
- Repeated inference.
- Partial processing failures.

### Privacy and security

- User isolation.
- Authorized model input.
- Evaluation dataset access.
- Sensitive information in logs.
- Derived-data deletion.

### Performance

- Inference latency.
- Memory usage.
- Batch throughput.
- Concurrent processing.
- Model loading overhead.

---

## 17. Finalized Decisions

The following architectural decisions are established:

1. Python is the primary implementation language.
2. spaCy is the initial conventional NLP baseline.
3. scikit-learn is the initial statistical ML baseline.
4. The sentence-transformers ecosystem is the initial embedding baseline.
5. RapidFuzz supports fuzzy string matching.
6. dateparser supports temporal expression parsing.
7. NumPy and pandas support numerical processing and evaluation.
8. NLP and ML use a hybrid processing architecture.
9. ML outputs are signals, not authoritative decisions.
10. Deterministic validation protects important state transitions.
11. Confidence dimensions remain operation-specific.
12. Model and version metadata must be traceable.
13. Raven-specific evaluation datasets are required.
14. Model changes must follow controlled evaluation and migration.
15. User data is not automatically used for model training.
16. Generative LLM APIs and locally hosted generative LLMs are excluded from core Raven processing.
17. Correctness, privacy, and reliability take priority over raw inference speed.

---

## 18. Deferred Decisions

The following decisions require evaluation or implementation evidence:

- Exact spaCy pipelines and model packages.
- Exact embedding model and immutable revision.
- Classification algorithms and feature sets.
- Entity recognition model configuration.
- Whether specific ML components require custom training.
- Inference deployment topology.
- CPU/GPU requirements.
- Model serving technology.
- Batch sizes and concurrency.
- Model-specific confidence thresholds.
- Dataset size and annotation workflow.
- Evaluation targets.
- Model registry implementation.
- Model artifact storage.

These choices must remain consistent with the architecture and processing boundaries established in this document.

---

## 19. Completion Criteria

Phase 7.5 is architecturally specified when:

- The NLP and ML technology stack is documented.
- Engine-specific responsibilities are defined.
- Deterministic and ML decision boundaries are clear.
- Model output and confidence handling are specified.
- Model versioning and evaluation requirements are established.
- Inference responsibilities are documented.
- Privacy and security requirements are defined.
- Failure and recovery behavior is specified.

**Status:** Architecture specification complete.

**Important:** This document does not claim that NLP pipelines, ML models, inference services, training datasets, or evaluation tests have been implemented or deployed.

---

## 20. Next Phase

**Phase 7.6 — API, Security & Internal Communication**

This will define FastAPI boundaries, API contracts, authentication, authorization, service-to-service communication, request validation, versioning, rate limits, and security controls.

---

<!-- Amendment reapplied from commit 71511d5. Its text is unchanged except for corrected documentation paths. -->

# Amendment — Document Processing, NLP and RAG Technologies

**File:** `docs/technical-decisions/05-NLP-and-machine-learning-stack.md`  
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
  
