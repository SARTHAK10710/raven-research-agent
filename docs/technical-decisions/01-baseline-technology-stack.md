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
- The language-scope requirement (gap G6), and Decisions 6–8 and 12–15, per the decision review. (Decisions 8 and 13 were later settled in §24.1 and §24.2.)

---

## 24. Approved Phase 8.3 Prerequisite Decisions

### 24.1 Decision 8 — Local object storage for development and tests ⚑ (new infrastructure)

**Status:** Approved by the project owner on 2026-11-11, before Phase 8.3. Analysis: [decision review](../project-context/PHASE-8-2-ARCHITECTURE-DECISION-REVIEW.md) §4, Decision 8. Nothing is implemented yet; Phase 8.3 implements it once 8.3 is approved.

This decision covers development and tests only. It does not choose the production object-storage provider, which stays deferred (§8; 7.8 §21), and it does not change the approved S3-compatible approach (§8; 7.2 §10).

- **Storage port.** Object storage sits behind a Memory Engine port, and application code depends only on the port. *Corrected 2026-11-11 (8.3 step 1, owner-approved):* the port lives in the shared kernel, `memory_engine.domain.object_storage`, because application code may not import `infrastructure` (§23.1) and both domains use it. The adapters live in `memory_engine.infrastructure.object_storage`. The earlier text placed the port in `infrastructure`.
- **Layout (8.3 step 1, owner-approved):**
  - one bucket for the Memory Engine (for example `raven-memory`), provisioned outside the application, which never creates buckets;
  - keys are owner-partitioned (`documents/{owner}/…`, `memory-sources/{owner}/…`), and every call checks the key's owner segment against the caller's `OwnerScope`;
  - the settings `RAVEN_MEMORY__OBJECT_STORAGE__*` are required.
- **Unit tests** use an in-memory fake that implements the port. No container or disk is needed.
- **Integration tests and local development** use **SeaweedFS** (Apache-2.0) as an S3-compatible service in `docker-compose.yml`, beside `postgres-test`. It runs as a single container serving the S3 API, bound to `127.0.0.1`, with development-only credentials and synthetic data only (7.8 §4, §7.2). The image tag is pinned to an exact version, and its licence is re-checked, when 8.3 adds the service. *(Done in 8.3 step 1: `chrislusf/seaweedfs:4.51`, released 2026-10-25, Apache-2.0, checked 2026-11-11.)*
- **Python client:** **boto3** (Apache-2.0), synchronous like the rest of the stack (§23.2), and pointed at any S3-compatible endpoint by configuration. It is added as a dependency in 8.3, not earlier (§22.1 dependency timing).
- **Rejected:**
  - a cloud bucket for development: cost, and data leaving the machine;
  - a fake-only approach: it would leave multipart, partial-upload and error behaviour untested (7.2 §11; plan 8.2 §13, deferred to 8.3);
  - MinIO: community images stopped in October 2025, and the repository was archived in April 2026;
  - LocalStack: its free image requires an account and auth token since March 2026;
  - Garage: viable, but AGPL-3.0 and needs a bootstrap step;
  - minio-py: tied to the archived MinIO project.
- **Consequences for 8.3:**
  - object keys stay opaque and owner-partitioned (`DocumentVersion.object_key_for`; 7.2 §10);
  - writes follow the operation-state and reconciliation workflow of 7.2 §11;
  - the object-storage failure tests deferred from 8.2 (unavailable store, partial upload) run against the SeaweedFS container;
  - integration tests skip with a message when the container is not running, as they already do for PostgreSQL.

### 24.2 Decision 13 — Document parsing ownership ⚑ (reinterprets an approved algorithm)

**Status:** Approved by the project owner on 2026-11-11, before Phase 8.3. Analysis: [decision review](../project-context/PHASE-8-2-ARCHITECTURE-DECISION-REVIEW.md) §4, Decision 13 (gap G5). The algorithm text is amended in [6.2 "Amendment — Document parsing ownership"](../algorithms/memory/01-memory-ingestion-extraction.md).

- **The document pipeline (Document Intelligence, plan 8.12) owns parsing** of PDF, DOCX and TXT uploads: text extraction, parsing status and normalized content. That gives one hardened parser and one extracted representation per document version.
- **Ingestion (plan 8.3)** owns acceptance:
  - it verifies the actual format, size limits and checksum, and runs the approved pre-parse security checks;
  - it stores the original in object storage and registers the document and version;
  - it hands off processing to the document pipeline (plan 8.3 §6, which already assigns parsing to 8.12).
- **Memory ingestion** parses messages and conversations only. A document upload creates no Memory Source and no memories.
- **Document text reaches Personal Memory** only through the authorized document-to-memory path. Its authorization model is Decision 6, which is still open, so that path stays disabled until Decision 6 is approved. The one-way `personal → documents.api` dependency (§23.1) is unchanged.
- **Rejected:**
  - parsing in both places: duplicate code, twice the attack surface for malformed files, and extractions that can disagree;
  - memory ingestion owning parsing: it would put document processing inside Personal Memory, against the domain separation in §23.1.

### 24.3 Phase 8.3 step 4 — Reliable handoff: outbox, RabbitMQ and Celery ⚑ (new infrastructure and dependencies)

**Status:** Approved by the project owner on 2026-11-12, at the start of 8.3 step 4. Settles the step-4 open questions and part of the 7.4 §22 deferrals (queue names and routing keys) for the ingestion handoff only.

- **Topology:** one durable direct exchange `raven.memory`; queue `memory.document.processing` (routing key `document.extraction.requested`, task `memory.document.extraction`) for the document pipeline (8.12) and queue `memory.personal.extraction` (routing key `personal.extraction.requested`, task `memory.personal.extraction`) for extraction (8.4). No dead-letter queue yet: dead-letter routing and retention are settled with the consumers (7.4 §13, §22).
- **Message contract:** the 7.4 §7 task envelope as JSON, `schema_version` "1", `message_type` "command"; the payload holds identifiers and object keys only, never content. Additive changes keep the version; any other change bumps it; consumers reject unknown versions. The contract lives in the shared kernel (`memory_engine.domain.handoff`).
- **Publishing:** Celery `send_task`, the envelope as the single argument and the outbox id as the Celery task id, with publisher confirms. Celery does not retry; the outbox does.
- **When a record becomes `queued`:** only after the broker confirms. Registration writes the record and its `me_outbox` row in one transaction (Memory Source `validated`, extraction operation `created`); the relay publishes and, in one transaction, marks the row published and moves the record to `queued` (with a `pm_source_processing_event` for a Memory Source).
- **Forget instructions:** no outbox row and no message; the source stays `validated` until plan 8.10 handles it.
- **Retries:** bounded. Each failure counts an attempt and records an error code; the next try follows exponential backoff with jitter (2 s doubling, capped at 5 min); after 10 attempts the row becomes `failed` and is retried only through an explicit `retry_failed`. All values are configurable, because 7.4 §22 defers them.
- **Broker for development and tests:** `rabbitmq:4.3.7-alpine` (MPL-2.0, checked 2026-11-12) as `broker-test` in `docker-compose.yml`, on 127.0.0.1 only, tmpfs, test-only credentials, no management plugin. Production broker hosting, TLS and credentials stay deferred (7.8).
- **New runtime dependencies:** `celery>=5.7,<6` and `kombu>=5.7,<6` (BSD-3-Clause; kombu declared because tests use it directly). Both untyped for mypy, and confined to `memory_engine.infrastructure.messaging` (a boundary test enforces it).
- **Implementation choices (8.3 step 4, reported to the owner):**
  - The relay runs as its own loop (`OutboxRelay.run_forever`), one message per transaction, claiming rows with `FOR UPDATE SKIP LOCKED`; not as a Celery beat task, which would need a third queue. It stops a batch at the first publish failure.
  - `me_outbox` has no foreign key to its subject, which lives in either domain (only the evidence path may cross them). Plan 8.10 deletion must remove a subject's outbox rows.
  - If the subject no longer waits for handoff (for example, a cancelled operation), the row becomes `failed` with `SUBJECT_NOT_PENDING` and nothing is published.
  - Published rows are kept; an outbox cleanup policy is still deferred (7.4 §22).

### 24.4 Phase 8.3 step 5 — Ingestion observability

**Status:** Approved by the project owner on 2026-11-12, at the start of 8.3 step 5. Applies 7.7 §4–§7 and §18 to plan 8.3 §11 without deploying monitoring (7.7 §20 and 7.8 still defer backends and deployment).

- **Metrics port, no new dependency:** application code records counters, durations and gauges through `memory_engine.observability.metrics.Metrics`. The default recorder is a no-op; an in-memory recorder serves tests. An OpenTelemetry adapter implementing the same port is added when monitoring is deployed (7.7 §19: OpenTelemetry and Prometheus remain the selected technologies).
- **Bounded labels:** only `input`, `outcome`, `reason` and `kind`, with values that are short lowercase words or UPPER_SNAKE_CASE codes. Identifiers can never become labels (7.7 §7.7).
- **Events:** one structured `ingestion.<outcome>` event per request and one `handoff.<outcome>` event per relay attempt, with record ids, the message, task and correlation ids, codes and durations. Never content, filenames or caller-supplied idempotency keys.
- **Owner in logs:** events carry `user_scope`, the opaque owner id. Log retention stays deferred (7.7 §20).
- **"Unauthorized request" (plan 8.3 §12.1):** covered as an owner-scope mismatch. Authentication tests move to the Entry layer, which Phase 8 does not include (deferral D1 in the [8.3 acceptance review](../project-context/PHASE-8-3-ACCEPTANCE-REVIEW.md)).

---

## 25. Approved Phase 8.4 Decisions

Approved by the project owner on 2026-11-12, when Phase 8.4 (Extraction and Evaluation) was approved.

### 25.1 Decision 7 — Plan order and the scope of 8.4 ⚑

- **8.4 now covers the personal-memory path only.** It consumes the `memory.personal.extraction` handoff (§24.3) and runs 6.2.2–6.2.6 on Memory Sources.
- **The document-derived path of 8.4 stays disabled** until plan 8.12 has produced parsed, chunked documents. It is completed after 8.12, together with Decision 6 (the document-to-memory authorization model), which is settled at that point.
- **Plan order:** 8.1 → … → 8.10 (personal) → 8.12 → the 8.4 document path and 8.10 document deletion → 8.11 last. This replaces the order in the Phase 8 Readme §6, which plan 8.11 and plan 8.4 §4.2 contradicted (8.11 tests documents end to end, and 8.4 consumes 8.12's outputs).
- **Rejected:** building the document path now against stubbed 8.12 outputs (tests would rest on invented data).

### 25.2 Gap G6 — Language scope: English first

- Extraction rules and the NLP model handle **English**. Non-English sources are detected and **deferred** with a reason code; they are never silently dropped and never run through English rules.
- Multilingual support needs a separate approval. It also bears on the embedding model (Decision 3, before 8.7) and on document keyword search, which stays on the language-neutral `simple` configuration.

### 25.3 Decision 14 — Conventional NLP stack

- **spaCy 3.8** (MIT) with the **`en_core_web_sm` 3.8.0** model (MIT, CPU only), pinned as a direct wheel in `uv.lock`. Deterministic rules run on top of its sentence split, part-of-speech tags, dependency parse and named entities (7.5 §3.1; 6.2.3 §5.4).
- Both are new runtime dependencies. They are approved here and added in the 8.4 step that first needs them, with their licence and version checked again at that time.
- Generative models remain prohibited. Model outputs are signals; validation and state transitions stay deterministic (6.2 §2.4).
- **Datasets:** versioned synthetic datasets under `tests/memory_engine/quality/data/`, one per capability, created with the step that first needs them (decision review, Decision 14). Thresholds and weights start as configurable, uncalibrated defaults and are recorded as such.

### 25.4 Phase 8.4 steps (personal path)

1. **Extraction worker:** the Celery consumer for `memory.personal.extraction` (envelope validation, idempotency, Memory Source status transitions), the language check, the NLP dependency and the synthetic dataset scaffold.
2. **Relevance gate** (6.2.2).
3. **Atomic fact extraction** and statement classification (6.2.3).
4. **Evaluation** (6.2.4) and **explicit/inferred classification** (6.2.5).
5. **Candidate generation and validation** (6.2.6): persistence with provenance and evaluation history, category assignment, and the handoff to resolution (8.6).
6. **Observability, dataset evaluation and the acceptance review** (plan 8.4 §15–§16, personal path).

Each step settles its own open questions with the owner at its start.

### 25.5 Phase 8.4 step 1 — Extraction worker

**Status:** Approved by the project owner on 2026-11-12, at the start of 8.4 step 1.

- **Atomic outcome:** the pipeline runs in memory. One transaction then writes the candidates and moves the source `queued` → `processing` → outcome, conditional on `queued`. A crash leaves nothing partial, and a duplicate delivery does nothing.
  - **Transient failures** (database, object storage) are retried by the Celery task with exponential backoff: 5 retries, 2 s doubling to 5 min, configurable.
  - **When the retries run out,** the source becomes `processing_failed` with the error code.
  - **Explicit reprocess:** `processing_failed` → `validated`, and the same handoff is re-armed.
- **Deferral:** a new source state `deferred` and a `reason_code` on processing events, required exactly for deferral and rejection (5.4 §16; migration `0009`).
- **Language check:** a deterministic heuristic with no new dependency.
  - A text is not English when most of its letters are outside the Latin script, or when a text of six words or more has a low share of English function words.
  - Shorter Latin-script texts count as English.
  - The thresholds are configurable and checked against `tests/memory_engine/quality/data/language/v1.jsonl`.
- **Datasets:** versioned JSON Lines, `tests/memory_engine/quality/data/<capability>/v<N>.jsonl` (`schema_version`, `id`, `input`, `expected`, `notes`), validated by a loader test.
- **spaCy:** not added in step 1, which does not use it. It arrives in the first step whose code imports it, as §25.3 requires.
- **Known limitation:** if the database is down for the whole retry window, the task cannot record the failure and the source stays `queued`. A reconciliation sweep is not built yet.

### 25.6 Phase 8.4 step 2 — Relevance gate

**Status:** Approved by the project owner on 2026-11-12, at the start of 8.4 step 2.

- **Unit:** each sentence of each user-authored message. Assistant turns give context only.
  - **Roll-up:** any `process` sentence → extraction continues with those sentences; otherwise any deferral → source `deferred`; otherwise `rejected`.
  - **Reason codes:** `SMALL_TALK`, `QUESTION_ONLY`, `HYPOTHETICAL`, `GENERAL_KNOWLEDGE`, `THIRD_PARTY_ONLY`, `LOW_INFORMATION`, `NOT_PERSONALLY_RELEVANT`, `NO_USER_CONTENT` (reject); `AMBIGUOUS_RELEVANCE`, `ANALYSIS_UNAVAILABLE` (defer).
  - **Protection codes:** `EXPLICIT_REMEMBER`, `REMEMBER_PHRASE`, `CORRECTION`, `SIGNIFICANT_EVENT`.
- **Record:** `pm_relevance_assessment` (5.4 §17), append-only, in the source's outcome transaction.
- **Scoring:** a weighted mean of five signals, each in [0, 1].
  - Signals: personal relevance, long-term utility, temporal significance, contextual significance (conversations only), information density.
  - Signals that cannot be evaluated are left out and the weights renormalized; they are never counted as zero.
  - Default weights 0.35 / 0.2 / 0.15 / 0.15 / 0.15. `process` at 0.5 or above, `defer` from 0.3, `reject` below.
  - Explicit protection runs first; then small talk, questions and hypotheticals are rejected; then significant life events are protected.
  - All values are configurable (`RelevanceSettings`) and uncalibrated.
  - An analyzer failure defers the source with `ANALYSIS_UNAVAILABLE` (6.2.2 §4.10).
- **spaCy 3.8.18 with `en_core_web_sm` 3.8.0** arrives in this step.
  - It sits behind the `SentenceAnalyzer` port; only `memory_engine.infrastructure.nlp` imports it (tested).
  - The model is a pinned wheel in `tool.uv.sources`.
  - Licences re-checked 2026-11-12: spaCy and the model are MIT; the transitive packages are MIT, BSD, Apache-2.0, MPL-2.0 or ISC.
- **Quality:** relevance dataset v1 (36 cases, labelled by intent). 34 of 36 outcomes match. Both misses are deferrals where a reviewer would reject, the conservative direction 6.2.2 AC-10 asks for.

### 25.7 Phase 8.4 step 3 — Atomic fact extraction

**Status:** Approved by the project owner on 2026-11-12, at the start of 8.4 step 3.

- **Representation:** in-memory `FactProposal` records (5.4 §18), stored only as candidates in step 5. The proposition restates the clause in the third person ("The user prefers window seats.") and keeps any condition. The exact original sentence is kept alongside.
- **Method:** dependency-parse rules over the gate's spaCy parse. Each of these is one proposal:
  - the root clause;
  - each coordinated clause;
  - each comma-separated participial clause.

  Objects and prepositional details stay attached to their verb, so connected attributes keep their shared meaning. Conditions ("if", "unless", "provided") stay in the proposition and make it `conditional`. Reported speech ("say/tell/mention/claim") is attributed to the reporter. Under "I think/believe ..." the inner clause becomes `possible`, and the frame itself is not a fact. Negation comes from `neg`, "never" and "no longer". Dates and quantities are kept as written; relative times are never resolved.
- **References:** first person only.
  - "I/me" → "the user", "my" → "the user's", "we/us" → "the user and others", "our" → "the user's".
  - Third-person pronouns are kept as written and listed as unresolved, and the proposal needs review.
- **Confidence:** 1.0 minus penalties: no subject 0.4, no verb 0.4, unresolved reference 0.3, nothing beyond subject and verb 0.2, long sentence (over 30 tokens) 0.1.
  - Below 0.5 the proposal needs review; below 0.2 it is rejected.
  - The values are configurable (`FactExtractionSettings`) and uncalibrated.
- **Failures:**
  - a sentence that fails is recorded and the others are kept;
  - questions yield no proposal;
  - an empty result is not a failure.
- **Quality:** extraction dataset v1 has 24 cases, and all 24 match. The labels were written after inspecting how the sentences parse, so this set is a regression check on the agreed conventions, not an unbiased measure. Step 6 needs a held-out set.
