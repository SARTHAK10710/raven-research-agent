# Phase 8.4 — Extraction & Evaluation Implementation Plan

## 1. Objective

Implement the Memory Engine's extraction and evaluation pipeline.

This pipeline consumes validated ingestion records from Phase 8.3 and identifies potentially useful information that can become structured memory.

It is responsible for:

- Determining whether incoming content is relevant for memory formation.
- Extracting atomic facts.
- Identifying explicit and inferred information.
- Evaluating importance and confidence independently.
- Preserving evidence and provenance.
- Validating extracted facts.
- Preparing memory candidates for downstream processing.

The pipeline must prioritize correctness and traceability over extraction volume.

## 2. Architecture references

Claude Code must review:

1. `PROJECT_ARCHITECTURE.md`
2. `docs/architecture/` — Memory Engine architecture.
3. `docs/data-models/` — approved Memory Engine data models.
4. `docs/algorithms/memory/01-memory-ingestion-extraction.md`
5. `docs/algorithms/shared/01-shared-algorithm-framework.md`
6. `docs/technology/01-baseline-technology-stack.md`
7. `docs/technology/05-nlp-and-machine-learning-stack.md`
8. `docs/implementation-plans/phase-08-memory-engine/01-foundation-and-project-setup.md`
9. `docs/implementation-plans/phase-08-memory-engine/02-database-and-persistence.md`
10. `docs/implementation-plans/phase-08-memory-engine/03-ingestion-pipeline.md`

The approved algorithms and data models are authoritative.

Do not independently redefine memory categories, candidate states or confidence semantics.

## 3. Scope

### Included

- Relevance Gate.
- Content preprocessing for extraction.
- Atomic fact extraction.
- Fact classification.
- Explicit and inferred memory identification.
- Importance evaluation.
- Confidence evaluation.
- Evidence and provenance association.
- Candidate generation.
- Candidate validation.
- Extraction quality tests.

### Excluded

- Entity resolution and relationship management.
- Duplicate and contradiction resolution.
- Final memory activation.
- Embedding generation.
- Vector indexing.
- Memory retrieval.
- Consolidation and maintenance.
- Forgetting and deletion execution.
- Document RAG and document question answering.

These belong to subsequent milestones or the final Phase 8 architecture review.

## 4. Extraction pipeline architecture

Implement the following logical components.

### 4.1 Content Preprocessor

Responsibilities:

- Consume validated ingestion records.
- Retrieve source content using authorized content references.
- Normalize content for extraction.
- Preserve source boundaries and metadata.
- Identify relevant content segments.
- Preserve speaker and timestamp information where available.

The preprocessor must not modify the authoritative original source.

### 4.2 Relevance Gate

The Relevance Gate determines whether incoming information is worth processing further.

It should distinguish:

- Potentially useful personal information.
- Preferences.
- Goals and intentions.
- Decisions.
- Important events.
- Relationships.
- Knowledge.
- Projects.
- Commitments.
- Temporary or low-value conversational content.
- Irrelevant or unusable content.

Use the approved two-stage extraction approach:

**Stage 1 — Lightweight relevance assessment**

Quickly assess whether the source contains potentially useful information.

**Stage 2 — Detailed extraction**

Only relevant content proceeds to detailed extraction and evaluation.

Explicit remember instructions should receive priority.

Explicit forget instructions must bypass ordinary extraction and relevance evaluation and be routed to the dedicated forgetting workflow.

Repetition alone must not make otherwise irrelevant content important.

### 4.3 Atomic Fact Extractor

Extract information into small, independently understandable facts.

Each fact should express one meaningful proposition wherever possible.

For example:

Input:

"I am working on Raven, using Python and PostgreSQL, and I want to improve its memory retrieval."

Potential atomic facts:

- The user is working on a project named Raven.
- The project uses Python.
- The project uses PostgreSQL.
- The user wants to improve Raven's memory retrieval.

The example is illustrative. Actual extracted facts must be supported by source evidence.

Requirements:

- Avoid combining unrelated facts.
- Preserve important qualifiers.
- Preserve dates and temporal context.
- Preserve negation.
- Preserve uncertainty.
- Avoid inventing missing information.
- Avoid converting possibilities into confirmed facts.
- Avoid removing context that changes meaning.

### 4.4 Fact Classification

Classify extracted facts using the approved memory categories:

- Personal preferences.
- Goals.
- Decisions.
- Important events.
- Relationships.
- Knowledge.
- Projects.
- Commitments.

Support multiple category assignments where justified.

Classification must not force a fact into an unsuitable category.

### 4.5 Explicit and Inferred Classification

Distinguish information explicitly provided by the user from information inferred through processing.

**Explicit information**

Information directly stated or intentionally provided.

**Inferred information**

Information derived from available evidence but not directly stated.

Inferred memories must preserve:

- Evidence references.
- Confidence.
- Inference method or basis.
- Relevant source information.

Use the approved candidate lifecycle:

- `candidate`
- `active`
- `needs_review`
- `rejected`

Do not automatically activate uncertain inferences.

Repetition of an inference does not independently establish that it is true.

### 4.6 Importance Evaluation

Importance and confidence must be evaluated independently.

Importance measures the potential long-term usefulness of a memory.

Consider:

- Long-term relevance.
- User-stated importance.
- Future usefulness.
- Relationship to ongoing goals.
- Commitments and decisions.
- Relevance to recurring activities.
- Potential impact on future interactions.

Do not treat message length, emotional intensity or repetition as sufficient evidence of importance.

Use the approved importance representation from the existing data model.

Do not introduce a competing scoring system without documenting the conflict.

### 4.7 Confidence Evaluation

Confidence measures how strongly the available evidence supports an extracted fact.

Consider:

- Directness of the statement.
- Source reliability.
- Clarity of language.
- Ambiguity.
- Contradictory evidence.
- Temporal context.
- Whether the fact is explicitly stated or inferred.

Explicit statements should generally have stronger evidential support than weak inferences, but explicit statements can still be ambiguous or contradictory.

Do not automatically assign maximum confidence to every explicit statement.

Preserve confidence independently from importance.

### 4.8 Candidate Generator

Convert validated extraction results into memory candidates.

Responsibilities:

- Construct candidate records.
- Associate candidates with source records.
- Attach evidence and provenance.
- Preserve category assignments.
- Store importance and confidence.
- Preserve temporal information.
- Record extraction metadata.
- Assign the appropriate initial lifecycle state.

Candidate generation must follow the approved Phase 5 data models.

Do not create authoritative active memories directly in this milestone.

### 4.9 Candidate Validator

Before persistence, validate:

- Required fields.
- Fact completeness.
- Evidence references.
- Source ownership.
- Category validity.
- Confidence representation.
- Importance representation.
- Temporal consistency.
- Candidate lifecycle state.

Reject or flag invalid candidates instead of silently modifying their meaning.

## 5. Processing approach

Follow the approved hybrid processing architecture.

The extraction pipeline may use:

- Deterministic rules.
- Conventional NLP.
- Statistical classification.
- Non-generative machine learning.
- Linguistic pattern detection.
- Entity and date recognition where relevant.

Approved technology candidates include:

- spaCy.
- scikit-learn.
- NumPy.
- pandas.
- RapidFuzz where applicable.

Model and algorithm selection must be justified through evaluation.

### Important constraints

- No generative LLM APIs.
- No locally hosted generative LLMs.
- No dependency on external generative AI services.
- ML predictions are signals, not authoritative decisions.
- Deterministic validation is required before candidate persistence.
- Do not automatically train models on private user data.

## 6. Extraction data flow

Implement the following sequence:

1. Receive a validated ingestion record.
2. Retrieve its original content through an authorized reference.
3. Preprocess the content.
4. Run the lightweight Relevance Gate.
5. Reject or skip irrelevant content with an auditable reason.
6. Perform detailed extraction on relevant content.
7. Generate atomic fact proposals.
8. Classify each fact.
9. Determine whether the fact is explicit or inferred.
10. Evaluate importance.
11. Evaluate confidence.
12. Attach source evidence and provenance.
13. Validate the candidate.
14. Persist valid memory candidates.
15. Register extraction results and processing status.
16. Hand off candidates to the next appropriate processing stage.

A source may produce:

- Zero candidates.
- One candidate.
- Multiple candidates.

Do not force the generation of a memory candidate from every source.

## 7. Provenance and evidence

Every candidate must be traceable to its originating source.

Preserve relevant references such as:

- Source identifier.
- Ingestion identifier.
- User identifier.
- Source timestamp.
- Evidence location, where available.
- Original content reference.
- Extraction method.
- Processing timestamp.

For conversation-derived facts, preserve speaker and message references where available.

For document-derived facts, preserve available source references and page information. Detailed document chunking and RAG are deferred to the final Phase 8 review.

The system must be able to explain why a candidate was generated and what evidence supports it.

## 8. Persistence requirements

Use the approved persistence layer from Phase 8.2.

Persist candidates using the approved candidate data model.

Requirements:

- Enforce user ownership.
- Preserve source references.
- Preserve category assignments.
- Preserve confidence and importance independently.
- Preserve explicit/inferred classification.
- Maintain lifecycle state.
- Record processing history.
- Support transactional consistency for related database changes.
- Ensure idempotent processing of repeated extraction jobs.

Do not duplicate the original source content inside every candidate.

Use references to authoritative source records.

## 9. Failure handling

Handle the following scenarios:

| Scenario | Expected behavior |
|---|---|
| Empty source content | Skip or reject with a clear reason |
| Irrelevant source | Record relevance decision and stop extraction |
| Extraction produces no facts | Complete without creating candidates |
| Ambiguous statement | Preserve uncertainty or flag for review |
| Conflicting statements | Preserve evidence; defer resolution |
| Low-confidence inference | Keep as candidate or require review |
| Missing provenance | Reject candidate persistence |
| Invalid candidate | Reject with validation details |
| NLP model unavailable | Fail safely or use an approved fallback |
| Duplicate processing job | Prevent unintended duplicate candidates |
| Database failure | Preserve processing failure information and support retry |

Do not resolve contradictions or merge duplicate memories here. Those responsibilities belong to Phase 8.6.

## 10. Testing requirements

### Unit tests

Test:

- Content preprocessing.
- Relevance classification.
- Atomic fact generation.
- Fact classification.
- Explicit versus inferred detection.
- Importance evaluation.
- Confidence evaluation.
- Candidate construction.
- Candidate validation.

### Component tests

Test:

- End-to-end extraction from an ingestion record.
- Candidate persistence.
- Provenance association.
- User ownership validation.
- Processing status transitions.
- Idempotent extraction jobs.

### Quality evaluation

Create representative evaluation examples for:

- Explicit preferences.
- Goals.
- Decisions.
- Important events.
- Relationships.
- Knowledge.
- Projects.
- Commitments.
- Temporary statements.
- Ambiguous language.
- Negation.
- Tentative plans.
- Corrections.
- Inferred facts.
- Contradictory information.

Evaluate:

- Extraction precision.
- Extraction recall.
- Atomicity.
- Classification accuracy.
- Confidence calibration.
- Provenance completeness.
- False memory creation.

Quality thresholds should be defined using representative evaluation datasets rather than arbitrary assumptions.

Do not claim extraction quality is production-ready solely because unit tests pass.

## 11. Observability

Record structured processing events for:

- Extraction started.
- Relevance assessment completed.
- Source rejected as irrelevant.
- Fact proposals generated.
- Candidates validated.
- Candidates persisted.
- Candidate rejected.
- Extraction failed.

Track useful metrics:

- Sources processed.
- Relevance rejection rate.
- Candidate generation rate.
- Candidate validation failure rate.
- Extraction processing latency.
- Retry rate.
- Duplicate processing rate.

Do not log full source content or unnecessary sensitive information.

## 12. Acceptance criteria

Phase 8.4 is complete only when:

- [ ] Validated ingestion records can enter the extraction pipeline.
- [ ] The lightweight Relevance Gate is implemented.
- [ ] Detailed extraction is performed only on relevant content.
- [ ] Atomic facts are generated.
- [ ] Facts are classified using approved categories.
- [ ] Explicit and inferred information are distinguished.
- [ ] Importance and confidence are evaluated independently.
- [ ] Evidence and provenance are preserved.
- [ ] Validated memory candidates are persisted.
- [ ] Uncertain inferences are not automatically treated as authoritative memories.
- [ ] Duplicate extraction jobs are handled safely.
- [ ] Failures are recorded and recoverable.
- [ ] Unit and component tests pass.
- [ ] Extraction quality evaluation is available.
- [ ] No out-of-scope memory resolution or retrieval functionality has been introduced.

## 13. Implementation constraints

Claude Code must:

1. Inspect the existing repository before changes.
2. Reuse Phase 8.1, 8.2 and 8.3 implementations.
3. Follow approved architecture, models and algorithms.
4. Avoid duplicate domain models.
5. Keep extraction logic separate from persistence.
6. Keep importance separate from confidence.
7. Preserve explicit versus inferred distinctions.
8. Avoid generative LLM functionality.
9. Avoid implementing document RAG in this milestone.
10. Place implementation code inside `memory-engine/`.
11. Place tests inside `tests/`.
12. Do not proceed to Phase 8.5 automatically.

If existing architecture documents leave an implementation-critical detail unresolved, report it with a recommendation before making an architectural change.

## 14. Completion report

Claude Code must report:

1. Implemented extraction components.
2. Files created or modified.
3. Dependencies introduced.
4. Algorithms and classification methods used.
5. Candidate data models used.
6. Provenance implementation.
7. Tests executed and exact results.
8. Quality evaluation results.
9. Known limitations.
10. Deviations from approved specifications.
11. Acceptance criteria status.

Clearly distinguish tested behavior from unverified assumptions.

## 15. Definition of done

Phase 8.4 is complete when Raven can transform validated source information into structured, evidence-backed memory candidates while preserving uncertainty, provenance, importance and confidence.

**The output of this milestone is a set of validated memory candidates, not final authoritative memories.**
