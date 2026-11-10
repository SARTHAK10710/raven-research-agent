# Raven — Technology & Infrastructure

## 1. Overview

This directory contains the technology and infrastructure specifications for **Raven**, an independent AI research agent.

Phase 7 translates the finalized architecture, data models and algorithmic specifications into concrete technology recommendations.

It defines the technologies required to build, operate and maintain:

- Memory Engine.
- Research Engine.
- Agent Orchestrator.
- Shared Infrastructure.
- Document Intelligence and RAG capabilities.

The objective is to establish a practical, secure, maintainable and scalable technology foundation before implementation begins.

Technology recommendations must remain aligned with the architectural decisions established in previous phases.

---

## 2. Technology Selection Principles

All technology decisions must follow these principles.

### 2.1 Correctness First

Technology must support reliable processing, data integrity and evidence traceability.

Performance improvements must not compromise correctness.

### 2.2 Simplicity

Prefer established technologies and existing infrastructure over unnecessary additional services.

Avoid introducing separate databases, brokers or infrastructure components without measurable justification.

### 2.3 Modularity

Technology choices must preserve clear boundaries between Memory, Research, Orchestrator and Shared Infrastructure.

### 2.4 Privacy and Security

All components must support:

- User-level ownership.
- Authorization.
- Secure data handling.
- Controlled access.
- Retention and deletion.
- Auditability.

### 2.5 Resource Efficiency

Technology selection must consider:

- CPU and memory consumption.
- Storage overhead.
- Processing latency.
- Infrastructure cost.
- Concurrency.
- Operational complexity.

### 2.6 No Generative LLM Dependency

Core Raven processing must not depend on generative LLM APIs or locally hosted generative LLMs.

The approved direction relies on:

- Deterministic algorithms.
- Conventional NLP.
- Statistical methods.
- Embedding models.
- Similarity algorithms.
- Structured validation.
- Extractive processing.
- Rule-based decision logic.

### 2.7 Evidence and Provenance

Technologies must preserve source references, version information and processing metadata.

This is particularly important for external research and document intelligence.

---

## 3. Technology Documentation

Phase 7 is divided into eight technology specifications.

| Subphase | Document | Scope |
|---|---|---|
| 7.1 | `01-baseline-technology-stack.md` | Programming language, frameworks and core development tools |
| 7.2 | `02-database-and-storage-architecture.md` | PostgreSQL, logical schemas, object storage, persistence and lifecycle |
| 7.3 | `03-vector-search-and-embedding-infrastructure.md` | pgvector, embedding generation, vector search and hybrid retrieval |
| 7.4 | `04-background-processing-and-messaging.md` | RabbitMQ, Celery, asynchronous processing and task reliability |
| 7.5 | `05-NLP-and-machine-learning-stack.md` | NLP, conventional ML, document parsing, extraction, chunking and evidence processing |
| 7.6 | `06-api-security-and-internal-communication.md` | FastAPI, API contracts, authentication and authorization |
| 7.7 | `07-observability-and-testing-infrastructure.md` | Logging, metrics, tracing, testing and quality evaluation |
| 7.8 | `08-deployment-and-environment-architecture.md` | Docker, environments, deployment, configuration and recovery |

Each document defines technology recommendations, selection rationale, constraints, dependencies and implementation considerations.

---

## 4. Baseline Technology Stack

The initial technology direction is:

| Area | Technology |
|---|---|
| Primary language | Python 3.12 |
| Backend framework | FastAPI |
| Data validation | Pydantic |
| Configuration | Pydantic Settings (`pydantic-settings`) |
| Primary database | PostgreSQL |
| ORM | SQLAlchemy |
| Database migrations | Alembic |
| Vector storage | pgvector |
| Object storage | S3-compatible storage |
| Message broker | RabbitMQ |
| Background processing | Celery |
| NLP | spaCy |
| Conventional ML | scikit-learn |
| Embeddings | sentence-transformers ecosystem |
| Similarity matching | RapidFuzz |
| Date normalization | dateparser |
| Numerical processing | NumPy |
| Structured data processing | pandas |
| API documentation | OpenAPI |
| Observability | OpenTelemetry |
| Metrics | Prometheus |
| Dashboards | Grafana |
| Testing | pytest, HTTPX, pytest-cov |
| Code quality | Ruff, mypy (strict mode) |
| Environment management | uv (workspace, one root `uv.lock`) |
| Test location | Repository-root `tests/` |

The Python version, type checker, project layout, test location and configuration choices were approved for Phase 8.1 on 2026-11-11; see `01-baseline-technology-stack.md` §22, which also records when each dependency is introduced.
| Containerization | Docker, Docker Compose |

Document parsing recommendations are maintained in `05-NLP-and-machine-learning-stack.md`.

The initial proposed document parsers are:

- pypdf for PDF text extraction.
- python-docx for DOCX extraction.
- Python standard library for TXT processing.

These parser choices require evaluation before becoming mandatory dependencies.

OCR and advanced layout extraction remain deferred.

---

## 5. Document Intelligence and RAG

Raven supports a separate Document Intelligence capability within the Memory Engine.

Its purpose is to process uploaded documents and retrieve evidence from their contents.

The document intelligence pipeline includes:

1. Document validation and registration.
2. Original document storage.
3. Document version management.
4. Text and structure extraction.
5. Content normalization.
6. Structure-aware chunking.
7. Embedding generation.
8. Hybrid vector and keyword indexing.
9. Evidence retrieval.
10. Evidence selection.
11. Extractive answer assembly.
12. Citation and provenance validation.
13. Document lifecycle and deletion.

### 5.1 Storage

Document originals and large extracted artifacts use S3-compatible object storage.

PostgreSQL maintains structured metadata, ownership, versions, processing state and references.

### 5.2 Embeddings

Document chunk embeddings use the existing pgvector infrastructure.

They remain logically separate from personal memory embeddings.

### 5.3 Retrieval

Document retrieval combines:

- Semantic vector search.
- PostgreSQL Full-Text Search.
- Metadata filtering.
- Evidence selection.
- Optional evaluated reranking.

### 5.4 Answer Assembly

Answers must be based on retrieved evidence and use extractive processing, conventional NLP and deterministic methods.

Generative LLM APIs and locally hosted generative LLMs remain outside the approved architecture.

### 5.5 Separation from Personal Memory

Document chunks are not personal memories.

Document uploads do not automatically create personal memory records.

Document-derived facts must enter the authorized memory extraction and evaluation lifecycle.

---

## 6. Technology Ownership and Boundaries

Technology selection must respect engine ownership.

| Component | Technology Responsibility |
|---|---|
| Memory Engine | Memory persistence, extraction, resolution, retrieval, document intelligence and deletion |
| Research Engine | External discovery, extraction, verification, research storage and comparison |
| Agent Orchestrator | Intent processing, planning, routing, execution and workflow coordination |
| Shared Infrastructure | Database, object storage, messaging, identity, logging, monitoring and deployment |

Shared infrastructure may be reused across engines, but business logic and authoritative data ownership must remain separate.

---

## 7. Technology Decisions and Deferred Evaluations

Some technology decisions are intentionally deferred until implementation evidence is available.

These include:

- Dedicated vector database selection.
- Exact embedding model.
- Embedding model migration strategy.
- OCR engine selection.
- Advanced PDF layout extraction.
- Specialized table extraction libraries.
- Document reranking model.
- Exact chunk size and overlap.
- Database partitioning.
- Advanced caching.
- PgBouncer configuration.
- Infrastructure scaling strategy.

A deferred decision must not be treated as an approved dependency.

New technologies should be introduced only when requirements, evaluation results or measured workload justify them.

---

## 8. Relationship With Previous Phases

Phase 7 depends on:

| Previous Phase | Dependency |
|---|---|
| Phase 1 — System Architecture | System boundaries, communication and ownership |
| Phase 2 — Memory Engine Architecture | Memory responsibilities and processing policies |
| Phase 3 — Research Engine Architecture | Research responsibilities and verification policies |
| Phase 4 — Agent Orchestrator Architecture | Workflow execution and coordination |
| Phase 5 — Data Models & Database Design | Entities, relationships, storage and lifecycle |
| Phase 6 — Algorithms & Processing Design | Processing algorithms and decision logic |

Technology selection must support these decisions rather than silently changing them.

Any genuine architectural conflict must be documented and resolved before implementation.

---

## 9. Implementation Readiness Criteria

Phase 7 is considered complete when:

1. The baseline technology stack is documented.
2. Database and storage technologies are defined.
3. Vector search and embedding infrastructure are defined.
4. Background processing and messaging are defined.
5. NLP and conventional ML technologies are documented.
6. Document processing requirements and parser recommendations are documented.
7. API security and internal communication are defined.
8. Observability and testing infrastructure are defined.
9. Deployment and environment architecture are defined.
10. Deferred decisions are clearly identified.
11. Technology choices align with the architecture, data models and algorithms.
12. Implementation dependencies and constraints are documented.

Completion of Phase 7 means the technology specifications are ready to guide implementation planning.

It does not mean the technologies have already been installed, configured, deployed or benchmarked.

---

## 10. Next Phase

**Phase 8 — Memory Engine Implementation**

The implementation phase will begin by establishing the Memory Engine foundation and then progressively implementing:

- Database and persistence.
- Memory ingestion.
- Extraction and evaluation.
- Entity and relationship management.
- Memory resolution.
- Storage and indexing.
- Retrieval.
- Consolidation and maintenance.
- Forgetting and deletion.
- Document Intelligence and RAG.
- Integration and testing.

Implementation must follow the approved architecture, data models, algorithms and technology specifications.

---

**Project:** Raven  
**Repository:** `raven-research-agent`  
**Documentation:** Technology & Infrastructure  
**Phase:** 7
