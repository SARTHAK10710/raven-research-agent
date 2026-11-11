# 8.4 — Extraction and Evaluation

## 1. Objective

Implement the Memory Engine's extraction and evaluation pipeline.

The pipeline converts eligible source content into structured memory candidates, evaluates their quality, and prepares them for the memory resolution process.

Supported source domains:

1. Personal memory inputs, including user messages and conversation history.
2. Explicitly authorized document-derived extraction.

The extraction pipeline must distinguish between information contained in a document and information that represents durable personal context about the user.

Uploading or indexing a document must never automatically create personal memories.

## 2. Architecture references

Read the following before implementation:

- `PROJECT_ARCHITECTURE.md`
- `docs/architecture/`
- `docs/data-models/`
- `docs/algorithms/`
- `docs/technical-decisions/`
- `docs/technical-decisions/Readme.md`
- `docs/implementation-plans/Phase-08-memory-engine/03-ingestion-pipeline.md`
- `docs/implementation-plans/Phase-08-memory-engine/05-entity-and-relationship-management.md`
- `docs/implementation-plans/Phase-08-memory-engine/06-memory-resolution.md`
- `docs/implementation-plans/Phase-08-memory-engine/12-document-rag-pipeline.md`

Follow the approved extraction, provenance, and candidate models.

## 3. Extraction architecture

Implement the following pipeline:

1. Receive eligible source content.
2. Validate source ownership and permissions.
3. Apply the relevance gate.
4. Extract atomic fact proposals.
5. Normalize extracted facts.
6. Classify the information.
7. Determine explicit or inferred status.
8. Evaluate importance and confidence independently.
9. Attach provenance and supporting evidence.
10. Validate the candidate.
11. Persist eligible candidates.
12. Hand off candidates for memory resolution.

The pipeline must not directly activate a memory without the approved resolution process.

## 4. Supported extraction sources

### 4.1 Personal memory sources

Examples:

- User-provided text.
- Conversation messages.
- Explicit remember instructions.
- Eligible conversation history.
- Other approved personal memory sources.

### 4.2 Document-derived sources

Documents may provide evidence for personal memory extraction when an authorized extraction operation is explicitly requested or approved.

Examples:

- A user asks Raven to remember a preference described in an uploaded document.
- A user asks Raven to extract their project goals from a project document.
- A user explicitly requests that relevant personal commitments from a document be considered for memory.

A document being available for search does not itself authorize personal memory extraction.

Document-derived extraction must use the document processing outputs created by plan 8.12.

## 5. Relevance gate

Apply a lightweight relevance gate before detailed extraction.

The relevance gate determines whether source content is likely to contain information worth considering as personal memory.

Potentially relevant information includes:

- Personal preferences.
- Goals.
- Decisions.
- Important events.
- Relationships.
- Knowledge relevant to the user's ongoing context.
- Projects.
- Commitments.

The relevance gate must distinguish:

- Information about the user.
- General factual information.
- Information about third parties.
- Hypothetical examples.
- Instructions contained within untrusted documents.
- Temporary or irrelevant content.

General information in a document must not be treated as a fact about the user merely because the user uploaded the document.

## 6. Atomic fact extraction

Extract candidate facts in atomic form wherever practical.

Each candidate should express one independently understandable proposition.

Preserve:

- Subject.
- Predicate or relationship.
- Object or value.
- Relevant context.
- Time information.
- Source evidence.
- Confidence.
- Explicit or inferred classification.

Do not combine unrelated facts into one memory candidate.

Do not remove qualifications that change the meaning of the original statement.

## 7. Memory classification

Support the approved memory categories:

- Personal preferences.
- Goals.
- Decisions.
- Important events.
- Relationships.
- Knowledge.
- Projects.
- Commitments.

Categories may be multi-label where the approved data model permits.

Do not create a new category merely because information originated from a document.

Source type and memory category represent different concepts.

For example:

- Source type: document-derived.
- Memory category: project.

## 8. Explicit and inferred information

### 8.1 Explicit information

Explicit information is directly stated by the user or explicitly selected by the user for memory extraction.

It must retain its source and evidence.

### 8.2 Inferred information

Inferred information is derived from evidence but is not directly stated.

It must include:

- Inference status.
- Supporting evidence.
- Source references.
- Confidence.
- Extraction method.
- Relevant context.

Inferred candidates must not be presented as confirmed facts.

Use the approved candidate lifecycle, including states such as:

- Candidate.
- Active.
- Needs review.
- Rejected.

Exact persisted state values must follow the Phase 5 data models.

Weak inferences must remain candidates or be rejected.

Repetition alone must not automatically promote an inference.

## 9. Importance and confidence evaluation

Importance and confidence must remain independent dimensions.

### Importance

Importance estimates how useful or consequential a memory may be for future interactions.

### Confidence

Confidence estimates how strongly the available evidence supports the extracted proposition.

Do not increase confidence merely because a memory appears important.

Do not treat a highly confident but irrelevant fact as an important memory.

Document-derived candidates must also account for:

- Whether the document actually supports the claim.
- Whether the document describes the user or a third party.
- Whether the document is current.
- Whether the relevant statement is qualified or hypothetical.
- Whether the source is incomplete or ambiguous.

## 10. Document evidence and provenance

Every document-derived memory candidate must preserve enough information to trace the claim to its source.

Where available, preserve:

- `document_id`.
- `document_version_id`.
- `chunk_id`.
- Page number.
- Section or heading.
- Character or structural location.
- Source excerpt or evidence reference.
- Extraction method.
- Extraction timestamp.
- Model or processing version, where applicable.

These are logical provenance references. Exact field names must follow the approved Phase 5 data model and document-processing contracts.

The original document version remains the source of truth.

Do not retain only a generated summary when the original evidence reference is available.

A candidate derived from a document must remain distinguishable from a candidate derived directly from a user message.

## 11. Document extraction authorization

Document-to-memory extraction must be controlled.

Before extraction:

1. Verify the requesting user's identity.
2. Verify ownership or authorized access to the document.
3. Verify the requested extraction scope.
4. Identify the applicable document version.
5. Retrieve relevant extracted content and evidence.
6. Apply the normal relevance and evaluation pipeline.
7. Persist eligible memory candidates with provenance.

Do not automatically run personal memory extraction on every uploaded document.

Do not treat text inside a document as an instruction to change Raven's memory, access controls, or system behavior.

Document contents are untrusted data.

## 12. Processing methods

Use the approved hybrid processing approach:

- Deterministic rules.
- Conventional NLP.
- Statistical methods.
- Conventional machine learning.
- Embedding-based signals where appropriate.
- Deterministic validation.

The core Raven processing architecture must not depend on generative LLM APIs or locally hosted generative LLMs.

Machine learning outputs must be treated as signals rather than authoritative decisions.

Critical validation and memory state transitions must remain deterministic and auditable.

## 13. Candidate persistence and handoff

After evaluation:

1. Validate the candidate structure.
2. Verify provenance.
3. Verify user ownership.
4. Check required fields.
5. Apply confidence and quality rules.
6. Persist eligible candidates.
7. Record processing metadata.
8. Hand off to the memory resolution process.

The extraction pipeline must not independently decide that a candidate replaces an existing memory.

Duplicate detection, contradiction resolution, updates, and supersession belong to plan 8.6.

## 14. Failure handling

Handle:

- Empty or irrelevant content.
- Unsupported source type.
- Missing provenance.
- Low-confidence extraction.
- Conflicting evidence.
- Malformed document extraction output.
- Missing document version.
- Unauthorized document access.
- Deleted source document.
- Interrupted extraction.
- Duplicate extraction requests.
- Extraction model or NLP component failure.

Failed extraction must not produce an authoritative memory.

Retries must be idempotent.

If the original document has been deleted or access has been revoked, do not continue processing stale content without validating the applicable lifecycle and authorization state.

## 15. Testing requirements

### Personal memory extraction tests

- Explicit preference.
- Goal extraction.
- Decision extraction.
- Commitment extraction.
- Multi-fact input.
- Irrelevant content.
- Hypothetical statements.
- Third-party information.
- Ambiguous statements.
- Inferred versus explicit classification.
- Importance and confidence independence.

### Document-derived extraction tests

- Authorized document extraction request.
- Unauthorized document access.
- Document with personal facts.
- Document with general knowledge.
- Document containing third-party information.
- Hypothetical claims.
- Conflicting statements.
- Outdated document version.
- Missing page or section provenance.
- Deleted document.
- Duplicate extraction operation.
- Low-confidence candidate.
- Document content containing malicious or misleading instructions.

### Integrity tests

- Candidate provenance remains available.
- Document chunks are not converted directly into personal memories.
- Upload alone does not create personal memory.
- Document extraction uses the normal candidate lifecycle.
- Extraction does not bypass memory resolution.
- Rejected candidates are not treated as active memories.
- User ownership is enforced.

## 16. Acceptance criteria

This plan is complete when:

1. The relevance gate works.
2. Atomic fact candidates can be extracted.
3. Memory categories are assigned correctly.
4. Explicit and inferred information remain distinguishable.
5. Importance and confidence are evaluated independently.
6. Provenance is preserved.
7. Document-derived extraction requires authorization.
8. Document evidence is traceable to the correct document version and location.
9. Candidates enter the normal memory resolution workflow.
10. No automatic document-to-memory conversion occurs on upload.
11. No generative LLM dependency is introduced.
12. Required tests pass.

## 17. Out of scope

This plan does not implement:

- Entity resolution.
- Duplicate memory resolution.
- Contradiction resolution.
- Final memory activation.
- Memory storage and indexing.
- Personal memory retrieval.
- Document parsing.
- OCR.
- Document chunking.
- Document embedding generation.
- Document hybrid retrieval.
- Document answer assembly.

These responsibilities belong to their dedicated plans.

## 18. Claude Code execution instructions

Before implementation:

1. Inspect the existing extraction pipeline and relevant models.
2. Read the approved algorithm and data-model specifications.
3. Identify existing NLP and machine-learning dependencies.
4. Reconcile document provenance requirements with the approved schemas.
5. Report any missing or conflicting decisions.
6. Propose the minimum required changes.

Do not silently add new model fields, extraction categories, or dependencies.

After implementation, report:

- Files created or modified.
- Extraction methods implemented.
- Candidate lifecycle behavior.
- Document provenance implementation.
- Dependencies added.
- Tests executed and results.
- Acceptance criteria satisfied.
- Known limitations.

Do not automatically proceed to plan 8.5.

---

## Amendment — Scope, language and NLP stack (approved 2026-11-12)

Recorded in [7.1 §25](../../technical-decisions/01-baseline-technology-stack.md). It extends this plan; it does not replace it.

- **Personal path first.** This plan is implemented now for personal-memory sources (§4.1). The document-derived path (§4.2, §10, §11, and the document-derived tests in §15) stays disabled until plan 8.12 exists and Decision 6 (document-to-memory authorization) is approved. That path is completed after 8.12 (Decision 7).
- **English first.** Non-English sources are deferred with a reason code, never extracted with English rules (gap G6).
- **NLP stack.** spaCy 3.8 with `en_core_web_sm` 3.8.0, plus deterministic rules (Decision 14).
- **Acceptance.** Criteria 7, 8 and 10 (§16) and the document-derived tests are reviewed when the document path is completed. The personal-path acceptance review covers the rest. Criterion 10 (no automatic document-to-memory conversion on upload) already holds: ingestion never creates a Memory Source from a document (8.3 acceptance review).
