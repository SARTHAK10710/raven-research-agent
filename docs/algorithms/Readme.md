# Raven — Algorithms & Processing Design

## 1. Overview

This directory contains the algorithmic and processing specifications for **Raven**, an independent AI research agent.

Phase 6 translates the architecture and data models established in previous phases into detailed processing logic.

It defines how Raven:

- Ingests and processes information.
- Extracts and evaluates memories.
- Resolves duplicates, entities and contradictions.
- Retrieves relevant information.
- Consolidates and maintains memories.
- Processes uploaded documents.
- Extracts and preserves document structure.
- Generates document chunks and embeddings.
- Retrieves evidence from documents.
- Produces evidence-grounded document answers.
- Discovers and verifies external information.
- Manages research sessions and comparisons.
- Plans and coordinates agent execution.
- Handles failures, retries, cancellation and recovery.

The objective is to create implementation-ready specifications before development begins.

---

## 2. Design Objectives

All Raven algorithms must follow these objectives:

### 2.1 Correctness

Algorithms must prioritize accurate results over superficial speed improvements.

Important information must not be discarded, incorrectly merged or presented as verified without sufficient evidence.

### 2.2 Deterministic Processing

Use deterministic rules, conventional algorithms and explicit decision logic wherever practical.

For operations involving uncertainty, preserve confidence, provenance and review requirements rather than forcing an unsupported conclusion.

### 2.3 No Generative LLM Dependency

Core Raven processing must follow the established constraint against generative LLM APIs and locally hosted generative LLMs.

Processing should rely on:

- Rule-based methods.
- Conventional NLP techniques.
- Statistical methods.
- Embedding models.
- Similarity algorithms.
- Graph and relationship algorithms.
- Structured validation.
- Deterministic decision policies.
- Extractive processing and structured answer templates.

Non-generative models may be evaluated where appropriate.

### 2.4 Privacy and Security

Every processing operation must respect:

- User ownership.
- Authorization boundaries.
- Private and shared data classification.
- Data retention policies.
- Explicit forgetting and deletion.
- Secure handling of external content.
- Document-level access controls.

### 2.5 Resource Awareness

Algorithms must account for:

- Computational complexity.
- Processing time.
- Memory usage.
- Storage requirements.
- External service usage.
- Concurrency limits.
- Execution budgets.
- Embedding and retrieval costs.

### 2.6 Observability

Important processing operations must be traceable through:

- Operation identifiers.
- Input and output references.
- Processing states.
- Decision outcomes.
- Failure reasons.
- Timestamps.
- Relevant version information.

Sensitive content and secrets must not be unnecessarily exposed in logs.

---

## 3. Shared Algorithm Design Contract

Every major algorithm specification should define the following.

| Element | Description |
|---|---|
| Purpose | What the algorithm is responsible for |
| Inputs | Required information and dependencies |
| Preconditions | Conditions that must be satisfied before execution |
| Processing steps | Ordered algorithmic operations |
| Decision rules | Conditions and criteria used for decisions |
| Outputs | Expected results |
| State transitions | Changes to relevant record states |
| Failure handling | Errors, retries and recovery |
| Edge cases | Unusual or ambiguous scenarios |
| Complexity | Expected time and resource considerations |
| Acceptance criteria | Conditions used to verify correctness |

This contract ensures consistency across Memory, Research and Orchestrator algorithms.

---

## 4. Core Processing Principles

### 4.1 Ownership-Aware Processing

Each engine processes and modifies only the authoritative data it owns.

Cross-engine operations must use authorized interfaces and typed references.

### 4.2 Evidence-Aware Decisions

Similarity, frequency and statistical scores are signals, not proof.

Raven must distinguish:

- Similarity.
- Importance.
- Confidence.
- Source reliability.
- Verification status.
- Freshness.
- Evidence coverage.
- Provenance.

These dimensions must not be treated as interchangeable.

### 4.3 Idempotent Execution

Operations that may be retried must avoid duplicate side effects.

Repeated execution of the same logical operation must not create duplicate authoritative outcomes.

### 4.4 Bounded Processing

Algorithms must support appropriate limits for:

- Maximum processing time.
- Retrieval depth.
- Number of candidate records.
- Number of concurrent tasks.
- Retry attempts.
- External discovery operations.
- Resource consumption.

### 4.5 Historical and Current Information

Raven must preserve the distinction between:

- Historical information.
- Current information.
- Newly discovered information.
- Corrected information.
- Unverified information.

Historical information must not silently replace current information.

For documents, Raven must also preserve the distinction between historical and current document versions.

### 4.6 Graceful Degradation

When a component or dependency fails, Raven should preserve completed work and return partial results where appropriate.

A failed operation must never be silently represented as successful.

### 4.7 Source and Evidence Preservation

Document-derived information must retain its relationship to the original document.

Where available, preserve:

- Document identity.
- Document version.
- Extracted representation.
- Chunk identity.
- Page or section location.
- Processing and extraction metadata.

A retrieved passage must remain traceable to its source.

---

## 5. Phase 6 Documentation

Phase 6 is documented in twelve numbered subphases plus the Document Processing and RAG specification. Subphase numbers below are taken from each document's own header.

| Subphase | Document | Scope |
|---|---|---|
| 6.1 | `shared/01-shared-algorithm-framework.md` | Shared algorithm framework, scoring system and processing contract |
| 6.2 | `memory/01-memory-ingestion-extraction.md` | Memory ingestion, relevance gate and extraction (with an appended amendment on document parsing ownership, Decision 13) |
| 6.3 | `memory/02-memory-resolution.md` | Deduplication, entity resolution and contradiction handling |
| 6.4 | `memory/03-memory-retrieval.md` | Hybrid retrieval, ranking and context selection |
| 6.5 | `memory/04-memory-consolidation-maintenance.md` | Consolidation, maintenance, profiles and forgetting |
| — | `memory/05-document-processing-and-rag.md` | Document extraction, structure-aware chunking, embedding, hybrid retrieval, evidence selection, extractive answer assembly and citation validation |
| 6.6 | `research/01-query-understanding-discovery.md` | Query understanding and information discovery |
| 6.7 | `research/02-content-extraction-normalization.md` | Content extraction and fact normalization |
| 6.8 | `research/03-source-evaluation-verification.md` | Source evaluation and verification |
| 6.9 | `research/04-research-memory-session-lifecycle.md` | Research memory management and session lifecycle |
| 6.10 | `research/05-retrival-comparison-synthesis.md` | Research retrieval, comparison and synthesis |
| 6.11 | `orchestrator/01-intent-planning-routing.md` | Intent understanding, planning and routing |
| 6.12 | `orchestrator/02-result-validation-response-assembly` | Result validation and response assembly |

Paths are relative to `docs/algorithms/`.

*Numbering note:* an earlier version of this table assigned 6.11 to Document Processing and RAG. The orchestrator document now uses 6.11, and `memory/05-document-processing-and-rag.md` does not declare a subphase number, so its number is left unassigned here pending a decision. The file `orchestrator/02-result-validation-response-assembly` has no `.md` extension; it is referenced by its actual name.

Each document contains the algorithms and decision logic for its respective area.

### 5.1 Memory and Document Intelligence Boundaries

Memory processing and document intelligence are separate logical domains within the Memory Engine.

**Personal memory algorithms** process validated information about the user.

**Document intelligence algorithms** process uploaded documents and their derived representations.

The distinction must be preserved:

- Document chunks are not atomic personal memories.
- Document embeddings are logically separate from personal memory embeddings.
- Document retrieval does not automatically modify personal memory.
- Document-derived memory extraction requires explicit authorization.
- Document-derived facts must enter the normal memory candidate and resolution lifecycle.
- Deleting a document must account for its derived artifacts and provenance dependencies.

Both domains may reuse approved infrastructure such as PostgreSQL, pgvector and object storage.

---

## 6. Algorithm Evaluation Standards

Algorithms must be evaluated against more than whether they successfully execute.

### Memory Engine

- Extraction precision and recall.
- Duplicate detection quality.
- Entity resolution accuracy.
- Contradiction handling.
- Retrieval relevance.
- Memory freshness.
- Provenance completeness.
- Deletion completeness.

### Research Engine

- Discovery coverage.
- Extraction accuracy.
- Source reliability assessment.
- Evidence traceability.
- Verification quality.
- Freshness detection.
- Comparison correctness.

### Agent Orchestrator

- Intent classification accuracy.
- Routing correctness.
- Planning quality.
- Dependency handling.
- Scheduling efficiency.
- Recovery reliability.
- Cancellation correctness.
- Response completeness.

### Document Intelligence

- Document extraction completeness.
- Structural preservation.
- Reading-order accuracy.
- Chunking quality.
- Chunk provenance accuracy.
- Embedding consistency.
- Retrieval precision and recall.
- Evidence coverage.
- Citation correctness.
- Unsupported-answer rate.
- Document version correctness.
- Deletion propagation completeness.

Quantitative thresholds and evaluation datasets will be defined during the testing and evaluation phase.

---

## 7. Relationship With Previous Phases

Phase 6 depends on the specifications established in earlier phases.

| Previous Phase | Dependency |
|---|---|
| Phase 1 — System Architecture | System boundaries, responsibilities and communication |
| Phase 2 — Memory Engine Architecture | Memory processing responsibilities and policies |
| Phase 3 — Research Engine Architecture | Research processing responsibilities and policies |
| Phase 4 — Agent Orchestrator Architecture | Execution and coordination policies |
| Phase 5 — Data Models & Database Design | Entity definitions, ownership, relationships and lifecycle rules |

Phase 6 must refine these specifications into algorithmic detail without silently changing finalized architectural decisions.

Document Intelligence algorithms must follow the approved document models, versioning, provenance, embedding metadata and deletion relationships established in Phase 5.

If a genuine architectural conflict is discovered, it must be documented and resolved before implementation.

---

## 8. Implementation Readiness Criteria

A Phase 6 algorithm is considered complete when it has:

1. A clearly defined purpose and scope.
2. Defined inputs and outputs.
3. Detailed processing steps.
4. Explicit decision rules.
5. Pseudocode or equivalent structured logic.
6. Edge-case coverage.
7. Failure and recovery behaviour.
8. Security and privacy considerations.
9. Complexity and resource considerations.
10. Testable acceptance criteria.

For document intelligence algorithms, also verify:

- Source-document provenance.
- Document version handling.
- Chunk-location preservation.
- Evidence-grounded retrieval.
- Citation validation.
- Personal memory and document separation.
- Deletion dependencies.

Completion of Phase 6 means the algorithm specifications are ready for technology selection and implementation planning.

It does not mean the algorithms have already been implemented, benchmarked or tested.

---

## 9. Next Phase

**Phase 7 — Technology & Infrastructure Selection**

After Phase 6, Raven will evaluate and finalize:

- Programming languages and frameworks.
- Database technologies.
- Vector storage.
- Search infrastructure.
- Embedding models.
- Document parsing and extraction libraries.
- OCR capabilities, if required.
- Messaging and background processing.
- Infrastructure and deployment.
- Monitoring and observability.

Technology decisions must support the architecture, data models and algorithmic requirements already established.

---

**Project:** Raven  
**Repository:** `raven-research-agent`  
**Documentation:** Algorithms & Processing Design  
**Phase:** 6
