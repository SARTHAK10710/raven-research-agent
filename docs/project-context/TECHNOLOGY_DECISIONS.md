# Technology Decisions

A summary of Phase 7 ([docs/technical-decisions](../technical-decisions/Readme.md)). The source documents are authoritative.

**Installed in the repository:** the Phase 8.1 and Phase 8.2 dependencies (merged), declared in `pyproject.toml` files and locked in the root `uv.lock`. The embedding model is still pending ([decision review](PHASE-8-2-ARCHITECTURE-DECISION-REVIEW.md), Decision 3). "Approved" below means selected in the specifications, not installed. Each dependency is added only in the subphase that needs it.

## Approved Phase 8.1 project setup decisions

Approved by the project owner on 2026-11-11. Recorded in [7.1 §22](../technical-decisions/01-baseline-technology-stack.md).

| Decision | Choice | Status |
|---|---|---|
| Python version | Python 3.12. `requires-python` range begins at 3.12; development and CI on 3.12 | **APPROVED** |
| Type checker | mypy, strict mode. Pyright is not used | **APPROVED** |
| Project layout | uv workspace: root owns the workspace configuration, `memory-engine/` is a member, one root `uv.lock`. No per-member lockfiles. Not microservices | **APPROVED** |
| Test location | Repository-root `tests/`, organized by engine and test type (for example `tests/memory_engine/unit/`) | **APPROVED** |
| Configuration | Pydantic Settings (`pydantic-settings`), validated environment-based configuration | **APPROVED** |

## Approved Phase 8.2 decisions

Approved by the project owner on 2026-11-11. Recorded in [7.1 §23](../technical-decisions/01-baseline-technology-stack.md) and the Phase 8.2 amendment of [5.4](../data-models/phase-05-memory-engine-models.md). Phase 8.2 was approved and started on 2026-11-11 (step 1 implemented).

| # | Decision | Choice | Status |
|---|---|---|---|
| 1 | Package layout | Domain-first `personal/` and `documents/` (each `domain` + `application`), shared kernel `domain/`, `infrastructure/`, `interfaces/`; one-way `personal → documents.api` | **APPROVED** |
| 2 | Database driver and access | psycopg 3 + synchronous SQLAlchemy 2.0; engine per process; short owner-scoped units of work | **APPROVED** |
| 4 | Vocabularies | Entity relationships, memory relationships, revision change types, Atomic Memory lifecycle states, Memory–Entity associations | **APPROVED** |
| 5 | Document record placement | `memory` schema; `pm_`/`doc_`/`me_` prefixes; no implicit cascades; guarded evidence references | **APPROVED** |
| 10 | Owner identity | Caller-supplied `OwnerScope`; opaque `owner_id`; no Memory Engine user table | **APPROVED** |
| 3 (timing only) | Vector storage timing | 8.2 creates embedding metadata only; vector tables and indexes in 8.7 after the model is selected (7.1 §23.5) | **APPROVED** |
| 9 | Outbox and Celery timing | No outbox in 8.2; outbox table, publisher, RabbitMQ and Celery together in 8.3 (7.1 §23.6) | **APPROVED** |

## Approved Phase 8.3 prerequisite decisions

Approved by the project owner on 2026-11-11 (Decisions 8 and 13) and 2026-11-12 (step 4). Recorded in [7.1 §24](../technical-decisions/01-baseline-technology-stack.md). Decision 8 is implemented (8.3 step 1); the step-4 decisions are implemented and merged (PR #19, `db13113`).

| # | Decision | Choice | Status |
|---|---|---|---|
| 8 ⚑ | Local object storage (development and tests) | Storage port; in-memory fake for unit tests; **SeaweedFS** (Apache-2.0) in Docker Compose for integration tests and local development; **boto3** client. Production provider still deferred | **APPROVED** |
| 13 ⚑ | Document parsing ownership | The document pipeline (8.12) parses PDF/DOCX/TXT; ingestion (8.3) validates, stores, registers and hands off; memory ingestion parses messages and conversations only (6.2 amendment) | **APPROVED** |
| 8.3 step 4 ⚑ | Reliable handoff (7.1 §24.3) | `me_outbox` in the registration transaction; exchange `raven.memory`, queues `memory.document.processing` / `memory.personal.extraction`; 7.4 §7 envelope v1 (ids and object keys only); Celery `send_task` with publisher confirms; `queued` only after the broker confirms; forget instructions get no handoff; bounded retries (10 attempts, 2 s doubling to 5 min, jitter) then `failed` until an explicit retry; test broker `rabbitmq:4.3.7-alpine` (MPL-2.0); `celery` and `kombu` added | **APPROVED** 2026-11-12 |
| 8.3 step 5 | Ingestion observability (7.1 §24.4) | Metrics port (no-op default, in-memory for tests, OpenTelemetry adapter when monitoring is deployed); no new dependency; bounded labels; owner id in logs only; authentication tests deferred to the Entry layer | **APPROVED** 2026-11-12 |

## Dependency timing

| When | Dependencies | Installed? |
|---|---|---|
| Phase 8.1 — runtime | `pydantic`, `pydantic-settings` | Yes — 2.14.3, 2.16.2 (locked) |
| Phase 8.1 — development | `pytest`, `pytest-cov`, `ruff`, `mypy` | Yes — 9.2.0, 7.1.0, 0.17.4, 2.4.1 (locked) |
| Phase 8.2 | `SQLAlchemy` 2.x, `alembic`, `psycopg[binary]` (psycopg 3, approved 2026-11-11) | Yes — 2.1.8, 1.20.1, 3.3.8 (locked, merged). Transitive: `mako`, `markupsafe`, `tzdata`. Test database: `pgvector/pgvector:pg17` via `docker-compose.yml` (dev/test only) |
| Phase 8.3 (approved 2026-11-11, Decision 8) | `boto3` (object-storage client); SeaweedFS container for integration tests and local development | Yes (8.3 step 1, merged in PR #16): `boto3` 1.44.0 (Apache-2.0). Transitive: `botocore` 1.44.0, `s3transfer` 0.19.3 (Apache-2.0), `jmespath` 1.1.0, `urllib3` 2.8.0, `six` 1.17.0 (MIT), `python-dateutil` 2.9.0.post0 (Apache-2.0/BSD). Image `chrislusf/seaweedfs:4.51` (Apache-2.0) in `docker-compose.yml`. No stubs package: mypy treats boto3 as untyped, confined to the S3 adapter |
| Phase 8.3 step 4 (approved 2026-11-12, 7.1 §24.3) | `celery` (worker framework and publisher), `kombu` (declared: tests consume with it); RabbitMQ container for integration tests and local development | Yes (8.3 step 4, merged in PR #19): `celery` 5.7.0, `kombu` 5.7.0 (BSD-3-Clause). Transitive: `amqp` 5.4.2, `billiard` 4.3.2, `vine` 5.1.0 (BSD-3-Clause), `click` 8.5.1, `click-didyoumean` 0.3.1, `click-plugins` 1.1.1.2, `click-repl` 0.4.1 (BSD/MIT), `prompt-toolkit` 3.0.53, `wcwidth` 0.9.4, `tzlocal` 5.4.5 (BSD/MIT). Image `rabbitmq:4.3.7-alpine` (MPL-2.0). Untyped for mypy; confined to `infrastructure/messaging` (boundary test) |
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
| Embedding model, dimension, metric, index type | Not chosen. Needed before Phase 8.7 creates vector storage (vector columns deferred to 8.7, approved 2026-11-11) |

Set during Phase 8.1 implementation (7.1 §22.2): Ruff rules `E, W, F, I, B, UP, SIM, S, N, RUF` (line length 100; `S101` allowed in tests); mypy `strict = true` with the `pydantic.mypy` plugin over `memory-engine/src` and `tests`; build backend `hatchling` (build time only, not a runtime or dev dependency).

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
| Messaging | Queue names and topology beyond the ingestion handoff (settled in 7.1 §24.3), worker concurrency, final retry counts, dead-letter routing and retention, outbox cleanup, payload limits, production broker hosting and TLS | 7.4 §22 |
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
