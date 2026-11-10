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
| mypy or Pyright | Static type checking |
| uv | Dependency and environment management |

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
| Backend | FastAPI | Selected |
| Validation | Pydantic | Selected |
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
| Type checking | mypy or Pyright | Selection pending implementation tooling review |
| Dependency management | uv | Selected |
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
