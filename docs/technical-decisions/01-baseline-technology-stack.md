# Phase 7.1 — Baseline Technology Stack

**Project:** Raven Research Agent  
**Phase:** 7 — Technology & Infrastructure Selection  
**Subphase:** 7.1 — Baseline Technology Stack  
**Status:** Recommended technology specification  
**Optimization Priority:** Quality first

---

## 1. Purpose

This document establishes the recommended baseline technology stack for Raven.

The stack must support the three primary engines:

1. Memory Engine.
2. Research Engine.
3. Agent Orchestrator.

It must also support shared infrastructure, persistence, asynchronous processing, security, observability and deployment.

The technology stack must implement the existing architecture rather than introduce unnecessary architectural changes.

---

## 2. Application Architecture

**Decision: Modular Monolith with Independent Background Workers**

Raven will initially use a modular monolithic application architecture.

The three engines will have independent logical modules, interfaces and data ownership.

Background workers will handle asynchronous and long-running operations.

### Why this architecture?

A microservices architecture would introduce additional complexity before Raven has established its workload and scaling requirements.

Starting with a modular monolith provides:

- Simpler development.
- Easier debugging.
- Lower infrastructure costs.
- Simpler transactions.
- Clear module boundaries.
- A path toward future service separation.

### Logical architecture

```text
Raven Application
│
├── API Layer
│
├── Agent Orchestrator
│
├── Memory Engine
│
├── Research Engine
│
├── Shared Infrastructure
│
└── Background Workers
```

### Architectural constraints

- Each engine owns its business logic.
- Each engine owns its domain data.
- Cross-engine operations use defined interfaces.
- Shared infrastructure must not contain engine-specific business logic.
- Physical service separation can be introduced when justified.

---

## 3. Programming Language

<badge color="success">Selected baseline</badge>

**Python**

Python is the primary implementation language for Raven.

### Rationale

Python provides a mature ecosystem for:

- Natural language processing.
- Statistical processing.
- Machine learning.
- Embeddings.
- Document extraction.
- Information retrieval.
- Data normalization.
- Background processing.

Using one primary language also reduces integration complexity across the three engines.

### Requirements

- Use a supported stable Python release.
- Use type annotations.
- Pin dependencies.
- Maintain reproducible environments.
- Apply automated linting and formatting.
- Separate application logic from infrastructure adapters.

---

## 4. Backend Framework

<badge color="success">Selected baseline</badge>

**FastAPI**

FastAPI will provide Raven's application API layer.

### Responsibilities

- Request handling.
- Input validation.
- Authentication integration.
- API routing.
- Response serialization.
- OpenAPI documentation.
- Error handling.
- Health endpoints.

### Design rules

- Keep business logic outside API route handlers.
- Use explicit request and response schemas.
- Validate all external inputs.
- Apply authorization before private data access.
- Version public API contracts.
- Support correlation IDs.
- Handle long-running operations asynchronously.

---

## 5. Data Validation

**Selected technology: Pydantic**

Pydantic will define and validate application-level data contracts.

It will be used for:

- API request schemas.
- API response schemas.
- Internal engine contracts.
- Configuration validation.
- Message payload validation.
- Structured result validation.

Database constraints remain necessary. Pydantic validation is not a replacement for database integrity.

---

## 6. Primary Database

<badge color="success">Selected baseline</badge>

**PostgreSQL**

PostgreSQL will be Raven's primary relational database.

### Responsibilities

- Memory records.
- Memory candidates.
- Entities and relationships.
- Research sessions.
- Research findings.
- Evidence metadata.
- Execution records.
- Task dependencies.
- Processing events.
- Identity and authorization metadata.

### Rationale

PostgreSQL provides:

- ACID transactions.
- Referential integrity.
- Foreign keys.
- JSONB.
- Indexing.
- Concurrency control.
- Mature backup and recovery.
- A strong migration ecosystem.

### Database access technologies

| Responsibility | Technology |
|---|---|
| Relational access | SQLAlchemy |
| Schema migrations | Alembic |
| Application validation | Pydantic |

### Ownership

A shared PostgreSQL deployment does not imply shared business ownership.

| Domain | Authoritative owner |
|---|---|
| Memory records | Memory Engine |
| Research records | Research Engine |
| Execution and task records | Agent Orchestrator |
| Identity and shared infrastructure metadata | Shared Infrastructure |

---

## 7. Vector Search

<badge color="success">Selected baseline</badge>

**pgvector**

Raven will initially use pgvector alongside PostgreSQL.

### Responsibilities

- Memory semantic retrieval.
- Memory similarity detection.
- Entity matching signals.
- Research finding retrieval.
- Semantic research discovery.

### Important rules

- Embeddings are derived data.
- Original records remain authoritative.
- Similarity is not proof of identity.
- Semantic matching must consider metadata and context.
- Embedding model and version must be recorded.
- Deletion must propagate to vector records.

A dedicated vector database is deferred until workload measurements justify it.

---

## 8. Object Storage

**Selected approach: S3-compatible object storage**

Object storage will handle large content that should not be stored directly in relational database rows.

### Examples

- Uploaded documents.
- Original document content.
- Archived research source content.
- Extracted document artifacts.
- Selectively retained snapshots.

### Storage rules

- PostgreSQL stores metadata and references.
- Object storage stores large content.
- Objects must have controlled identifiers.
- Access must be owner-scoped.
- Sensitive content must be encrypted.
- Retention and deletion policies must be enforced.

The initial deployment should use one object storage provider.

---

## 9. Background Processing

**Selected technologies: RabbitMQ + Celery**

### RabbitMQ

Responsible for message delivery and routing.

### Celery

Responsible for executing background tasks.

### Workloads

- Memory extraction.
- Embedding generation.
- Memory consolidation.
- Research extraction.
- Source verification.
- Long-running research.
- Scheduled maintenance.
- Deletion propagation.
- Recovery operations.

### Reliability requirements

- Idempotent task execution.
- Bounded retries.
- Durable messaging for critical tasks.
- Dead-letter handling.
- Task correlation IDs.
- State reconciliation.
- Graceful worker shutdown.

Message delivery does not guarantee exactly-once business execution. Raven must protect business operations through idempotency and state management.

---

## 10. NLP & Machine Learning

Raven will use conventional NLP and non-generative machine learning.

### Recommended libraries

| Library | Responsibility |
|---|---|
| spaCy | Tokenization, linguistic processing and entity recognition |
| scikit-learn | Classification, clustering and statistical ML |
| sentence-transformers | Embedding models |
| NumPy | Numerical processing |
| pandas | Structured data processing |
| RapidFuzz | Fuzzy matching |
| dateparser | Temporal expression parsing |

These are baseline candidates. Individual algorithms should use only the libraries they need.

### Processing hierarchy

1. Deterministic rules.
2. Conventional NLP.
3. Statistical processing.
4. Non-generative machine learning.
5. Deterministic validation before authoritative state changes.

### Constraints

- No generative LLM APIs in core Raven processing.
- No locally hosted generative LLMs in core Raven processing.
- Embeddings are permitted.
- ML predictions are signals, not authoritative decisions.
- Uncertain outputs must be qualified.

---

## 11. Search Infrastructure

The initial search architecture will use:

| Requirement | Technology |
|---|---|
| Structured search | PostgreSQL |
| Keyword search | PostgreSQL full-text search |
| Semantic search | pgvector |
| Fuzzy matching | RapidFuzz |
| Entity relationships | PostgreSQL |
| Temporal filtering | PostgreSQL |

A dedicated search engine is not initially required.

---

## 12. API & Internal Communication

### External communication

**REST with OpenAPI**

Used for client-facing and external API interactions.

### Internal communication

Hybrid communication:

- Synchronous request-response for short operations.
- Asynchronous messaging for long-running operations.

### Requirements

- Versioned contracts.
- Request validation.
- User scope.
- Execution and task references.
- Timeout handling.
- Error handling.
- Idempotency.
- Authorization.
- Correlation IDs.

---

## 13. Authentication

**Selected approach: OpenID Connect-compatible identity provider**

Raven should integrate an established identity provider rather than implement authentication infrastructure from scratch.

The specific provider remains deferred until deployment and identity requirements are finalized.

### Requirements

- Authentication.
- User identity.
- Authorization.
- Token validation.
- Session management.
- User-level data isolation.
- Revocation support.
- Access auditing.

---

## 14. Observability

Recommended baseline:

| Technology | Responsibility |
|---|---|
| OpenTelemetry | Tracing and instrumentation |
| Prometheus | Metrics collection |
| Grafana | Dashboards and visualization |

Structured application logging will be integrated with a centralized logging solution selected for the deployment environment.

### Monitoring requirements

- Request latency.
- Engine processing duration.
- Queue depth.
- Worker health.
- Database performance.
- Error rates.
- Retry rates.
- Failed tasks.
- Execution completion.
- Resource utilization.

Sensitive user information must not be unnecessarily exposed in logs.

---

## 15. Testing & Code Quality

| Technology | Responsibility |
|---|---|
| pytest | Unit and integration tests |
| HTTPX | API testing |
| pytest-cov | Coverage reporting |
| Ruff | Linting and formatting |
| mypy (strict mode) | Static type checking — selected for Phase 8.1; see §22 |
| uv (workspace) | Dependency and environment management — uv workspace with one root `uv.lock`; see §22 |

Testing must cover correctness, security, data integrity, concurrency and failure recovery.

Code coverage alone is not sufficient to establish algorithm quality.

---

## 16. Containerization

**Selected technologies: Docker and Docker Compose**

Docker provides reproducible environments.

Docker Compose will support local development of the application and its dependencies.

### Initial components

- Raven API.
- Background workers.
- PostgreSQL.
- RabbitMQ.
- Object storage.
- Monitoring components as required.

Production orchestration will be determined separately.

Kubernetes is not required for the initial baseline.

---

## 17. Baseline Technology Decision Table

| Component | Technology | Status |
|---|---|---|
| Programming language | Python | Selected |
| Python runtime version | Python 3.12 | Selected (§22) |
| Backend | FastAPI | Selected |
| Validation | Pydantic | Selected |
| Configuration | Pydantic Settings (`pydantic-settings`) | Selected (§22) |
| Database | PostgreSQL | Selected |
| ORM | SQLAlchemy | Selected |
| Migrations | Alembic | Selected |
| Vector storage | pgvector | Selected |
| Object storage | S3-compatible | Selected approach |
| Message broker | RabbitMQ | Selected |
| Background workers | Celery | Selected |
| NLP | spaCy | Selected baseline |
| Statistical ML | scikit-learn | Selected baseline |
| Embeddings | sentence-transformers ecosystem | Selected ecosystem |
| Fuzzy matching | RapidFuzz | Selected baseline |
| API | REST/OpenAPI | Selected |
| Authentication | OIDC-compatible provider | Selected approach |
| Tracing | OpenTelemetry | Selected |
| Metrics | Prometheus | Selected |
| Dashboards | Grafana | Selected |
| Testing | pytest | Selected |
| HTTP testing | HTTPX | Selected |
| Linting | Ruff | Selected |
| Type checking | mypy, strict mode | Selected (§22); previously pending implementation tooling review |
| Dependency management | uv | Selected |
| Project layout | uv workspace: root workspace configuration, engine packages as members, one root `uv.lock` | Selected (§22) |
| Test location | Repository-root `tests/` | Selected (§22) |
| Containers | Docker | Selected |
| Local orchestration | Docker Compose | Selected |

---

## 18. Deferred Decisions

The following decisions require additional evaluation.

| Decision | Reason |
|---|---|
| Exact embedding model | Requires retrieval benchmarking |
| Exact embedding dimensions | Depends on model selection |
| Authentication provider | Depends on deployment requirements |
| Cloud provider | Depends on infrastructure requirements |
| OCR technology | Depends on document processing needs |
| Production hosting | Depends on availability and scaling |
| Dedicated vector database | Depends on measured workload |
| Dedicated search engine | Depends on search performance |
| Production orchestration | Depends on operational complexity |

Deferred decisions must be revisited before the affected implementation depends on them.

---

## 19. Technology Selection Constraints

1. Quality and correctness take priority.
2. PostgreSQL is the initial relational source of truth.
3. pgvector is the initial vector search solution.
4. Engine data ownership must be maintained.
5. Long-running workloads must support asynchronous execution.
6. Critical operations must be idempotent.
7. Sensitive data must be access-controlled.
8. Core processing must not use generative LLMs.
9. New infrastructure must have a measurable justification.
10. Dependencies and versions must be managed and reviewed.

---

## 20. Completion Criteria

This document is complete when:

- The application architecture is selected.
- The primary programming language is selected.
- The API framework is selected.
- The primary database is selected.
- The vector storage approach is selected.
- The object storage approach is selected.
- Background processing technologies are selected.
- The NLP and ML ecosystem is documented.
- Authentication and observability approaches are documented.
- Deferred technology decisions are identified.

**Status:** Baseline technology specification documented. This does not claim any component has been installed, implemented, tested or deployed.

---

## 21. Next Subphase

**Phase 7.2 — Database, Storage & Data Infrastructure Design**

This will define:

1. PostgreSQL organization.
2. Domain-level ownership.
3. Relational data access.
4. Transaction boundaries.
5. Indexing strategy.
6. Connection pooling.
7. Object storage organization.
8. Backup and recovery.
9. Retention.
10. Deletion infrastructure.

---

## 22. Approved Project Setup Decisions (Phase 8.1)

**Status:** Approved by the project owner on 2026-11-11, before Phase 8.1 implementation.

These decisions resolve the tooling choices that §3, §15 and §17 left open. They do not change Raven's architecture: the modular monolith, the three primary engines, Shared Infrastructure, and all ownership boundaries remain as specified above.

| # | Decision | Approved choice | Details |
|---|---|---|---|
| 1 | Python version | **Python 3.12** | Python 3.12 is the runtime baseline. Projects declare a `requires-python` range beginning at 3.12 (`>=3.12`). Development and CI run on 3.12. Adopting a newer version requires first verifying support across the dependency stack, in particular the later NLP and embedding libraries. |
| 2 | Type checker | **mypy, strict mode** | mypy is the only static type checker; Pyright is not introduced as a second one. Strict mode is enabled, and mypy runs as a Phase 8.1 quality check. |
| 3 | Project layout | **uv workspace** | The repository root owns the workspace configuration (root `pyproject.toml`, no application code). `memory-engine/` is a workspace member with its own `pyproject.toml`. One root `uv.lock` manages the whole workspace; members do not keep independent lockfiles. Other engines join as members when they are implemented. A workspace is a code and dependency organization only. It does not imply microservices or independent deployment. |
| 4 | Test location | **Repository-root `tests/`** | Tests live under the existing root `tests/` directory, organized by engine and test type as implementation develops (for example `tests/memory_engine/unit/`, `tests/memory_engine/integration/`). Directories are created when they have content. Tests are not placed in `memory-engine/tests/`. |
| 5 | Configuration | **Pydantic Settings (`pydantic-settings`)** | Validated, environment-based configuration using Pydantic Settings, the official Pydantic package for settings in Pydantic v2. Existing secret-handling, environment-variable and logging requirements apply ([7.8](08-deployment-and-environment-architecture.md) §6–7). |

### 22.1 Dependency timing

| When | Dependencies |
|---|---|
| Phase 8.1 — runtime | `pydantic`, `pydantic-settings` |
| Phase 8.1 — development | `pytest`, `pytest-cov`, `ruff`, `mypy` |
| Phase 8.2 — added with database persistence | `SQLAlchemy`, `Alembic`, PostgreSQL driver (driver choice and sync vs async access are decided in 8.2) |
| When required | `HTTPX` (when API or HTTP testing is needed); OpenTelemetry API and SDK (when instrumentation is implemented) |

These remain approved baseline technologies (§17). This schedule only controls when each dependency is introduced. No dependency is added merely because it appears in the technology roadmap.

### 22.2 Not decided here

- PostgreSQL driver and sync vs async database access (Phase 8.2). *Decided in §23.*
- Ruff rule selection and detailed mypy configuration beyond strict mode (Phase 8.1 implementation).
- Exact dependency versions, which are pinned through the root `uv.lock` during implementation.

---

## 23. Approved Phase 8.2 Decisions

**Status:** Approved by the project owner on 2026-11-11, before Phase 8.2 implementation. Analysis and alternatives: [Phase 8.2 architecture decision review](../project-context/PHASE-8-2-ARCHITECTURE-DECISION-REVIEW.md) §4–5.

These decisions do not change Raven's architecture: the three primary engines, the modular monolith, Shared Infrastructure, and the separation of Personal Memory and Document Intelligence remain as specified. Decision 4 (relationship vocabularies and Atomic Memory lifecycle states) is a data-model decision and is recorded in the Phase 5.4 data model ([`phase-05-memory-engine-models.md`](../data-models/phase-05-memory-engine-models.md), "Phase 8.2 Amendment").

### 23.1 Decision 1 — Memory Engine package layout

Domain-first packages, each layered into domain and application:

| Package | Responsibility |
|---|---|
| `memory_engine.domain` | Shared kernel (existing): domain errors, identifiers, `OwnerScope`, temporal value objects, typed references, shared vocabulary enums |
| `memory_engine.personal.{domain,application}` | Personal Memory domain model and use cases (ingestion, extraction, entities, resolution, storage, retrieval, consolidation, deletion), with their ports; `personal/api.py` public facade |
| `memory_engine.documents.{domain,application}` | Document Intelligence domain model and use cases (registration, parsing, chunking, indexing, retrieval, evidence, lifecycle), with their ports; `documents/api.py` public facade |
| `memory_engine.infrastructure` | Adapters: `persistence/` (engine, sessions, unit of work, operations, per-domain ORM models and repositories; the outbox from Phase 8.3, §23.6), later `object_storage/`, `embeddings/`, `tasks/` |
| `memory_engine.interfaces` | Contracts used by the Orchestrator (commands, queries, results) |
| `config`, `exceptions`, `observability` | Engine-wide (existing) |

Packages are created only when they have content. This replaces the feature-first tree proposed in plan 8.1 §4; its feature names become modules inside `personal/application/`.

**Import rules (enforced by tests):**
- Domain packages import only the standard library, the shared kernel and `exceptions`.
- Application packages never import `infrastructure`.
- `documents` never imports `personal`. `personal.application` may use `documents.api` only, for authorized document-to-memory extraction.
- `interfaces` imports only the public facades and the shared kernel.

### 23.2 Decision 2 — PostgreSQL driver and access pattern

- **Driver:** psycopg 3 (`postgresql+psycopg` dialect). Its LGPL-3.0 licence is to be reviewed before production.
- **Access:** synchronous SQLAlchemy 2.0 ORM; a `Session` per unit of work; no asynchronous database access initially. psycopg 3 also supports async, so a later move needs no driver change, but it requires a measured need and approval.
- **Pooling:** one engine per process with `QueuePool` and `pool_pre_ping`. Celery prefork children create their own engine after fork. Pool sizes are configurable and tuned by measurement (7.2 §9).
- **Transactions:** short, owner-scoped units of work at `READ COMMITTED`; optimistic concurrency via a version column on mutable authoritative rows; immutable revision rows; from Phase 8.3, outbox rows written in the same transaction as the business change (§23.6); no transaction held across parsing, embedding or network calls.
- **Testing:** repository-port fakes in unit tests; real PostgreSQL with pgvector via Docker Compose in integration tests, with transactional rollback; migrations tested upgrade → downgrade → upgrade.
- **Dependencies when 8.2 starts:** `SQLAlchemy` 2.x, `alembic`, `psycopg[binary]`. The `pgvector` Python package follows with vector storage.

### 23.3 Decision 5 — Placement of Document Intelligence records

- All Memory Engine tables live in the existing `memory` schema (7.2; 7.2 amendment §3), owned and written only by the Memory Engine role.
- Table prefixes: `pm_` for Personal Memory, `doc_` for Document Intelligence, `me_` for shared engine plumbing (operations and idempotency in 8.2; the outbox in 8.3, §23.6).
- Document records: `doc_document`, `doc_document_version` (immutable), `doc_extracted_representation`, `doc_chunk` (text in PostgreSQL for full-text search), `doc_chunk_location`, `doc_embedding` (metadata), `doc_processing_operation`. Original files and large extracted artifacts live in object storage under opaque, owner-partitioned keys.
- Every owned row carries `owner_id`, including chunks and embeddings, so isolation is enforced in SQL before ranking.
- No implicit `ON DELETE CASCADE` on user data in either domain. Deletion runs as explicit, verified workflow steps, and foreign keys use `RESTRICT`.
- Personal-memory provenance references document evidence through `pm_document_evidence_ref` (document, version, nullable chunk, location) with `RESTRICT` foreign keys. The deletion workflow marks such references `source_deleted` before removing document data. Document deletion never deletes independent personal memories.
- **Implementation note (2026-11-11, 8.2 step 2):** "keep the identifiers" and "`RESTRICT` foreign keys" cannot apply to the same columns, or the document could never be deleted. `pm_document_evidence_ref` therefore stores linked columns with foreign keys, cleared on `source_deleted`, plus opaque `*_ref` copies with no foreign key that are kept permanently. Details and the other step-2 schema decisions: [5.4 Document Intelligence amendment §14](../data-models/phase-05-memory-engine-models.md).

### 23.4 Decision 10 — Owner identity

- The Memory Engine does not authenticate users and keeps no user table. Callers (the Entry layer through the Orchestrator) pass a validated `OwnerScope` carrying an opaque owner identifier (UUID).
- Every owned row stores `owner_id` without a foreign key to a Memory Engine user table; identity records remain owned by Shared Infrastructure (5.7).
- Every repository method requires an `OwnerScope` and filters by it in SQL.

### 23.5 Vector storage timing (Decision 3, deferral only)

Approved on 2026-11-11.

- **Phase 8.2** creates embedding **metadata** tables only, for both domains: source reference, model identifier and revision, dimension, preprocessing and normalization configuration, lifecycle status (Decision 5.4.20), and timestamps. It creates **no vector columns, vector tables or vector indexes**.
- **Phase 8.7** creates the vector payload tables (for example `pm_embedding_vector`, `doc_embedding_vector`), the pgvector extension objects and the vector indexes. This happens after the embedding model is selected through a Raven-specific evaluation ([decision review](../project-context/PHASE-8-2-ARCHITECTURE-DECISION-REVIEW.md) §5.3).
- The vector dimension, similarity metric and index type follow the selected model and are not fixed earlier.

### 23.6 Decision 9 — Transactional outbox and Celery timing

Approved on 2026-11-11.

- **Phase 8.2** creates no outbox table. Nothing in 8.2 publishes to a broker, and an unused table would contradict the rule against placeholder structures. Operation and idempotency tables (`me_` prefix) stay in 8.2, because plan 8.2 §4.6 requires durable operation state.
- **Implementation note (2026-11-11, 8.2 step 1):** no specification defines a generic `me_operation` table's columns, and its first consumers are ingestion idempotency (plan 8.3) and document processing (8.2 step 2, where `doc_processing_operation` is specified). Step 1 therefore creates no `me_` table; the same no-placeholder rule applies. Document processing operations use `doc_processing_operation`; a shared `me_operation` is introduced only when a consumer and its columns are defined.
- **Phase 8.3** introduces the outbox table (`me_outbox`), its publisher, RabbitMQ and Celery together, with their tests, when ingestion first publishes work. Outbox rows are then written in the same transaction as the business change (7.4 §9; §23.2).
- This differs from the [decision review](../project-context/PHASE-8-2-ARCHITECTURE-DECISION-REVIEW.md) recommendation (outbox table in 8.2). The trade-off it names, a schema change in 8.3, is accepted.

### 23.7 Decision 11 — Shared public entities ⚑ (privacy)

Approved on 2026-11-11.

- Entities are **private only** for now. Every entity has an owner, and `pm_entity.scope` exists, but a check constraint (`ck_pm_entity_private_only`) and the domain model reject `shared`. Shared entities are the only data that would be visible across users, so they stay disabled until a curation process with its own privacy review is approved (decision review §4, Decision 11).
- Enabling shared entities later requires that approval, plus a migration that relaxes the check and the owner requirement and adds cross-user isolation rules (5.4.13: private relationships may reference shared entities, never the reverse).

### 23.8 Not decided here

- The embedding model itself, with its dimension, metric and index type (Decision 3). It must be selected, with approval, before Phase 8.7 creates vector storage.
- The language-scope requirement (gap G6), and Decisions 6–8 and 12–15, per the decision review.
