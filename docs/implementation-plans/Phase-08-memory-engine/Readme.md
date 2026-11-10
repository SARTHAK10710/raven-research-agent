# Phase 8 — Memory Engine Implementation

## 1. Purpose

Phase 8 implements Raven's Memory Engine based on the architecture, data models, algorithms, and technology decisions documented in earlier phases.

The Memory Engine is responsible for:

- Ingesting and validating user-provided information.
- Extracting and evaluating potential memories.
- Managing entities and relationships.
- Resolving duplicates, updates, and contradictions.
- Persisting and indexing authoritative memories.
- Retrieving relevant personal memories.
- Consolidating and maintaining memory.
- Managing explicit forgetting and deletion.
- Processing documents and enabling evidence-grounded document retrieval through a dedicated RAG pipeline.

Phase 8 implements both **personal memory capabilities** and **document intelligence capabilities**. These are related but distinct domains and must not be treated as interchangeable.

## 2. Implementation scope

Phase 8 has twelve implementation plans.

| Plan | Document | Responsibility |
|---|---|---|
| 8.1 | `01-foundation-and-project-setup.md` | Establish the Memory Engine project foundation |
| 8.2 | `02-database-and-persistence.md` | Implement database models and persistence |
| 8.3 | `03-ingestion-pipeline.md` | Validate and register incoming information |
| 8.4 | `04-extraction-and-evaluation.md` | Extract and evaluate memory candidates |
| 8.5 | `05-entity-and-relationship-management.md` | Manage entities, aliases, and relationships |
| 8.6 | `06-memory-resolution.md` | Resolve duplicates, updates, and contradictions |
| 8.7 | `07-memory-storage-and-indexing.md` | Persist and index authoritative memories |
| 8.8 | `08-memory-retrieval.md` | Retrieve relevant personal memories |
| 8.9 | `09-consolidation-and-maintenance.md` | Consolidate and maintain personal memories |
| 8.10 | `10-forgetting-and-deletion.md` | Implement reliable deletion and forgetting |
| 8.11 | `11-memory-engine-integration-and-testing.md` | Integrate and validate the Memory Engine |
| 8.12 | `12-document-rag-pipeline.md` | Implement document processing and RAG |

## 3. Architecture references

Implementation must follow the existing architectural source of truth.

Before implementing a capability, Claude Code must inspect the relevant documents, including:

- `PROJECT_ARCHITECTURE.md`
- `docs/architecture/`
- `docs/data-models/`
- `docs/algorithms/`
- `docs/technical-decisions/`
- `docs/technical-decisions/Readme.md`

The implementation plans explain how to implement the approved architecture. They do not independently authorize changes to architectural decisions.

If a conflict, missing definition, or ambiguity is discovered, Claude Code must report it rather than silently inventing a new design.

## 4. Personal memory and document intelligence boundaries

Raven supports two distinct information domains within the Memory Engine.

### 4.1 Personal memory

Personal memory represents information about the user and their ongoing context.

Examples include:

- Preferences.
- Goals.
- Decisions.
- Important events.
- Relationships.
- Knowledge.
- Projects.
- Commitments.

Personal memory follows the established lifecycle:

`Ingestion → Extraction → Evaluation → Resolution → Storage → Retrieval → Consolidation`

Only validated and resolved information becomes authoritative personal memory.

### 4.2 Document intelligence

Document intelligence allows users to upload documents and retrieve relevant information from their contents.

The document pipeline follows:

`Document Registration → Parsing → Structure Extraction → Chunking → Embedding → Indexing → Retrieval → Evidence Selection → Answer Assembly`

Document content must remain distinct from personal memory.

Important boundaries:

- Uploading a document does not automatically create personal memories.
- Document chunks are not atomic personal memory records.
- Document embeddings and personal memory embeddings are logically separate.
- Document retrieval must preserve document, version, chunk, and location provenance.
- Document-derived facts can enter personal memory only through an explicit, authorized extraction workflow using the normal memory candidate and resolution process.
- Document retrieval must not silently alter personal memory.
- The Orchestrator will decide when to retrieve personal memory, documents, or both.

### 4.3 Shared infrastructure

Both capabilities may reuse approved infrastructure, including:

- PostgreSQL.
- pgvector.
- Object storage.
- Background workers.
- Shared logging and observability.
- Common security and authorization mechanisms.

Sharing infrastructure does not mean sharing business ownership or mixing authoritative records.

## 5. Implementation principles

### 5.1 Architecture ownership

- Memory Engine owns personal memory processing and document intelligence.
- Research Engine owns external research workflows and research-specific records.
- Agent Orchestrator owns task coordination and cross-engine execution.
- Shared Infrastructure provides reusable technical capabilities.
- No engine should take ownership of another engine's business logic.

### 5.2 Correctness before optimization

Correctness, privacy, security, data integrity, and traceability take priority over performance.

Optimization must follow measured bottlenecks rather than premature complexity.

### 5.3 No generative LLM dependency

The core Raven processing architecture must not depend on generative LLM APIs or locally hosted generative LLMs.

Use the approved combination of:

- Deterministic rules.
- Conventional NLP.
- Statistical methods.
- Embedding models.
- Conventional machine learning.
- Extractive processing.
- Deterministic answer templates.

Machine learning outputs are signals, not authoritative decisions. Deterministic validation must protect critical state changes.

### 5.4 Provenance and evidence

Every authoritative memory must retain appropriate provenance.

Document-derived answers must preserve evidence references, including the relevant document, version, chunk, and page or section location where available.

The system must distinguish:

- Verified information.
- Inferred information.
- Low-confidence information.
- Conflicting information.
- Missing or inaccessible evidence.

### 5.5 User isolation and privacy

- Enforce user-level ownership and authorization.
- Prevent cross-user retrieval and data access.
- Avoid exposing sensitive document content in logs.
- Apply deletion and retention policies across primary and derived data.
- Do not train models automatically on user data.

### 5.6 Idempotency and recovery

Operations that may be retried must be designed for idempotency.

The system must handle:

- Duplicate ingestion requests.
- Worker retries.
- Interrupted processing.
- Partial failures.
- Concurrent updates.
- Stale background jobs.
- Indexing failures.
- Deletion retries.

A timeout must not be interpreted as proof that an operation failed.

## 6. Implementation sequence

The implementation plans should be executed in dependency order.

1. Foundation and project setup.
2. Database and persistence.
3. Ingestion pipeline.
4. Extraction and evaluation.
5. Entity and relationship management.
6. Memory resolution.
7. Memory storage and indexing.
8. Memory retrieval.
9. Consolidation and maintenance.
10. Forgetting and deletion.
11. Integration and testing.
12. Document intelligence and RAG.

Some tasks may require iterative integration, but later plans must not be considered complete merely because their code has been created.

Each plan must pass its own acceptance criteria before the phase is considered complete.

## 7. Source-code placement

Implementation plans belong inside:

`docs/implementation-plans/Phase-08-memory-engine/`

Actual source code belongs in the existing:

`memory-engine/`

Tests belong in the appropriate locations under the repository-root:

`tests/`

Memory Engine tests are organized by engine and test type (for example `tests/memory_engine/unit/` and `tests/memory_engine/integration/`), not in `memory-engine/tests/`.

Do not place implementation source code inside the documentation or implementation-plan directories.

Claude Code must inspect the existing repository before proposing or creating package structures. Reuse existing conventions and avoid unnecessary restructuring.

### 7.1 Approved project setup decisions

Approved on 2026-11-11 and recorded in [`docs/technical-decisions/01-baseline-technology-stack.md`](../../technical-decisions/01-baseline-technology-stack.md) §22:

| Decision | Approved choice |
|---|---|
| Python version | Python 3.12 (`requires-python` range beginning at 3.12; development and CI on 3.12) |
| Type checker | mypy in strict mode (Pyright is not used) |
| Project layout | uv workspace: the repository root owns the workspace configuration, `memory-engine/` is a workspace member, and one root `uv.lock` manages all members |
| Test location | Repository-root `tests/` |
| Configuration | Pydantic Settings (`pydantic-settings`), with validated environment-based configuration |

The uv workspace organizes code and dependencies only. It does not change the modular-monolith architecture or imply independent deployment.

**Dependency timing:**

| When | Dependencies |
|---|---|
| Phase 8.1 | Runtime: `pydantic`, `pydantic-settings`. Development: `pytest`, `pytest-cov`, `ruff`, `mypy` |
| Phase 8.2 | `SQLAlchemy`, `Alembic`, PostgreSQL driver |
| When required | `HTTPX` (API/HTTP testing), OpenTelemetry API/SDK (instrumentation) |

Later milestones add their own dependencies (NLP, embeddings, messaging, storage) only when they need them.

## 8. Testing and quality requirements

The Memory Engine must be validated at multiple levels:

- Unit tests.
- Component tests.
- Database integration tests.
- Background-worker tests.
- End-to-end workflow tests.
- Authorization and isolation tests.
- Failure and recovery tests.
- Data integrity tests.
- Retrieval quality tests.
- Document evidence and citation tests.
- Deletion propagation tests.
- Performance tests.

Tests must validate behavior and correctness, not merely successful imports or API responses.

### Important quality checks

- Duplicate ingestion must not create duplicate authoritative memories.
- Contradictory information must not silently overwrite existing facts.
- Historical and current values must remain distinguishable.
- Low-confidence inferences must not be presented as confirmed facts.
- Document chunks must not enter personal memory accidentally.
- Document answers must be traceable to supporting evidence.
- Cross-user data access must be prevented.
- Deletion must propagate to applicable derived data.
- Failed processing must not be reported as successful.

## 9. Definition of done

Phase 8 is complete only when:

1. All twelve implementation plans have been implemented or explicitly dispositioned through an approved scope decision.
2. Personal memory ingestion and retrieval work end to end.
3. Memory resolution preserves history and handles conflicts safely.
4. Consolidation and maintenance operate without corrupting authoritative records.
5. Forgetting and deletion propagate across applicable data and indexes.
6. Document ingestion, parsing, chunking, indexing, and retrieval work end to end.
7. Document answers preserve evidence and citation provenance.
8. Personal memory and document intelligence remain separate domains.
9. User isolation and authorization are tested.
10. Required integration, quality, and failure tests pass.
11. Documentation reflects the actual implementation.
12. Known limitations and deferred work are recorded.

No capability should be marked complete without test evidence.

## 10. Implementation reporting requirements

After completing each implementation plan, Claude Code must report:

- Files created or modified.
- Dependencies added or changed.
- Database migrations created, if applicable.
- Tests executed.
- Exact test commands and results.
- Acceptance criteria satisfied.
- Known limitations.
- Architectural deviations or unresolved decisions.
- Any security, privacy, or data-integrity concerns.

Claude Code must not automatically proceed to the next implementation plan unless explicitly instructed.

## 11. Out of scope

Unless separately approved, Phase 8 does not include:

- Building the user interface.
- Implementing the Research Engine.
- Implementing the Agent Orchestrator.
- Cross-engine workflow orchestration.
- Deploying the complete Raven platform.
- Introducing a dedicated external vector database without workload evidence.
- Adding generative LLM dependencies.
- Automatically converting every uploaded document into personal memories.

These capabilities belong to their respective phases or require a separate architectural decision.

## 12. Final implementation objective

The objective of Phase 8 is to deliver a reliable Memory Engine that can maintain useful personal context and provide evidence-grounded access to user documents.

The system must know the difference between what it remembers about a user and what a document says.

It must preserve the source, context, confidence, history, and ownership of information throughout its lifecycle.

**Correctness, trustworthiness, privacy, and traceability are the primary measures of success.**
