# Technology Decisions

A summary of Phase 7 ([docs/technical-decisions](../technical-decisions/Readme.md)). The source documents are authoritative.

**Installed in the repository:** nothing. There is no `pyproject.toml`, lockfile or environment. "Approved" below means selected in the specifications, not installed. Each dependency is added only in the subphase that needs it.

## Approved Phase 8.1 project setup decisions

Approved by the project owner on 2026-11-11. Recorded in [7.1 §22](../technical-decisions/01-baseline-technology-stack.md).

| Decision | Choice | Status |
|---|---|---|
| Python version | Python 3.12. `requires-python` range begins at 3.12; development and CI on 3.12 | **APPROVED** |
| Type checker | mypy, strict mode. Pyright is not used | **APPROVED** |
| Project layout | uv workspace: root owns the workspace configuration, `memory-engine/` is a member, one root `uv.lock`. No per-member lockfiles. Not microservices | **APPROVED** |
| Test location | Repository-root `tests/`, organized by engine and test type (for example `tests/memory_engine/unit/`) | **APPROVED** |
| Configuration | Pydantic Settings (`pydantic-settings`), validated environment-based configuration | **APPROVED** |

## Dependency timing

| When | Dependencies | Installed? |
|---|---|---|
| Phase 8.1 — runtime | `pydantic`, `pydantic-settings` | No |
| Phase 8.1 — development | `pytest`, `pytest-cov`, `ruff`, `mypy` | No |
| Phase 8.2 | `SQLAlchemy`, `Alembic`, PostgreSQL driver (choice pending, see below) | No |
| When required | `HTTPX` (API/HTTP testing); OpenTelemetry API/SDK (instrumentation) | No |
| Later milestones | NLP, embedding, messaging and storage libraries, in the subphase that needs them | No |

## Approved baseline

| Area | Technology | Source |
|---|---|---|
| Language | Python 3.12 | 7.1 §3, §22 |
| Application architecture | Modular monolith with independent background workers | 7.1 §2, 7.8 §3 |
| API framework | FastAPI, REST/OpenAPI, routes under `/api/v1/` | 7.1 §4, 7.6 §17 |
| Validation | Pydantic | 7.1 §5 |
| Configuration | Pydantic Settings (`pydantic-settings`) | 7.1 §22 |
| Primary database | PostgreSQL: one deployment, domain schemas | 7.2 §20 |
| ORM and migrations | SQLAlchemy (with its connection pooling), Alembic | 7.2 §20 |
| Vector storage | pgvector | 7.3 §18 |
| Keyword search | PostgreSQL full-text search | 7.1 §11 |
| Object storage | S3-compatible | 7.2 §20 |
| Messaging and workers | RabbitMQ, Celery; transactional outbox recommended | 7.4 §21 |
| NLP | spaCy | 7.5 §17 |
| Statistical ML | scikit-learn | 7.5 §17 |
| Embeddings | sentence-transformers ecosystem | 7.5 §17 |
| Fuzzy matching | RapidFuzz | 7.5 §17 |
| Temporal parsing | dateparser | 7.5 §17 |
| Numerical and tabular | NumPy, pandas | 7.5 §17 |
| TXT processing | Python standard library | 7.5 amendment §18 |
| Authentication | OIDC-compatible identity provider (approach; provider deferred) | 7.6 §17 |
| Observability | OpenTelemetry, Prometheus, Grafana; standard `logging` with structured output | 7.7 §19 |
| Testing | pytest, HTTPX, pytest-cov | 7.7 §19 |
| Lint and format | Ruff | 7.7 §19 |
| Type checking | mypy, strict mode | 7.1 §22 |
| Environment and dependencies | uv workspace, one root `uv.lock` | 7.1 §15, §22 |
| Test location | Repository-root `tests/` | 7.1 §22 |
| Containers | Docker, Docker Compose (local) | 7.8 §20 |

## Pending selection

| Decision | Status |
|---|---|
| PostgreSQL driver; sync vs async SQLAlchemy | Not specified. Needed by 8.2 |
| Ruff rule selection; detailed mypy configuration beyond strict mode | Set during 8.1 implementation (7.1 §22.2) |

## Proposed — requires evaluation before approval

| Technology | Purpose | Source |
|---|---|---|
| pypdf | PDF text extraction | technical-decisions Readme §4, 7.5 amendment §18 |
| python-docx | DOCX extraction | technical-decisions Readme §4, 7.5 amendment §18 |
| Non-generative reranker | Optional document reranking | 7.5 amendment §18 |
| Table extraction enhancement | Only if needed | 7.5 amendment §18 |

`pydantic-settings` is now approved for 8.1 (see above). OpenTelemetry packages are deferred until instrumentation is implemented; they are not part of 8.1.

## Deferred

| Area | Deferred items | Source |
|---|---|---|
| Embeddings and search | Exact embedding model and revision, dimensions, similarity metric, HNSW vs IVFFlat, index parameters, chunk size and overlap, batch sizes, retrieval thresholds and weights, reranking model | 7.3 §19, 7.5 |
| NLP and ML | spaCy pipelines and models, classifiers and features, CPU/GPU, model serving and registry, confidence thresholds, evaluation targets | 7.5 §18 |
| Documents | OCR, advanced layout extraction, chunk storage location, extracted-text artifact format | 7.5 amendment §18, 7.2 amendment §12 |
| Database | PgBouncer, partitioning, dedicated database per engine, exact indexes | 7.2 §20 |
| Messaging | Queue names and topology, worker concurrency, retry counts, dead-letter retention, payload limits | 7.4 §22 |
| Security and API | Identity provider, token policy, roles, exact endpoints, internal transport and authentication, rate limits, file-size limits, upload scanning, secrets provider | 7.6 §18 |
| Operations | Log, trace and metrics backends, alerting, CI provider, coverage thresholds, load and security tooling | 7.7 §20 |
| Deployment | Cloud and hosting, production orchestration, backup frequency and retention, RPO/RTO, HA, scaling thresholds | 7.8 §21 |

A deferred decision is never an approved dependency.

## Not permitted

| Technology | Rule |
|---|---|
| Generative LLM APIs | Not permitted in Raven processing |
| Locally hosted generative LLMs | Not permitted in Raven processing |
| Dedicated vector database | Only with measured workload justification and an approved decision |
| Separate document database or "Document Engine" | Not permitted; Document Intelligence stays in the Memory Engine on PostgreSQL |
| Dedicated search engine | Only with measured justification |
| Microservice split, Kubernetes | Not required initially; needs an approved decision |
