# Raven Memory Engine

The Memory Engine is one of Raven's three primary engines. It owns Raven's persistent knowledge in two **separate logical domains**:

- **Personal Memory** — facts, preferences, goals, decisions, events, entities and relationships about the user, built through ingestion → extraction → evaluation → resolution → storage → retrieval → consolidation, with explicit forgetting.
- **Document Intelligence** — uploaded PDF, DOCX and TXT documents: registration, versioning, extraction, structure-aware chunking, embeddings, hybrid retrieval, evidence selection and citations.

The two domains can share infrastructure (PostgreSQL, pgvector, object storage, workers) but never share records, retrieval workflows or lifecycle rules. Document chunks are not personal memories, and uploading a document never creates memories automatically.

> **Status:** Phase 8.1 foundation plus Phase 8.2 steps 1–5, PostgreSQL persistence for:
> - the core Personal Memory records (Memory Source, Memory Candidate, Atomic Memory with immutable revisions, Provenance);
> - Document Intelligence (documents, versions, extracted representations, chunks with locations, embedding metadata, processing operations), plus the document-evidence path into Personal Memory;
> - entities (private only), aliases, mentions with resolution history, entity and memory relationships, and memory–entity associations;
> - episodes with membership and a correctable event timeline, profiles with immutable revisions, supporting memories and refresh history, memory categories, and memory embedding metadata (no vectors);
> - source processing events, candidate evaluation history, correction requests, and deletion operations with a content-free ledger.
>
> Phase 8.3 step 1 adds owner-scoped object storage: a port in `memory_engine.domain.object_storage`, an in-memory fake, and a boto3 adapter for S3-compatible stores (SeaweedFS in development and tests).
>
> Phase 8.3 step 2 adds personal memory ingestion (`personal/application/ingestion.py`). Text and conversations are validated, normalized and stored, and registered idempotently as a `validated` Memory Source; remember and forget instructions are recorded.
>
> Phase 8.3 step 3 adds document ingestion (`documents/application/ingestion.py`). PDF, DOCX and TXT uploads are checked by content, stored, and registered as a document or a new version, with an `extraction` operation waiting for the document pipeline. Nothing is parsed here.
>
> Phase 8.3 step 4 adds the reliable handoff. Each registration writes a `me_outbox` row in the same transaction; `memory_engine.infrastructure.messaging.OutboxRelay` publishes it to RabbitMQ through Celery (`raven.memory` exchange; queues `memory.personal.extraction` and `memory.document.processing`) and only then moves the record to `queued`. Forget instructions get no handoff. Failed publishes back off and, after the configured attempts, wait as `failed` for an explicit retry. No consumer exists yet (8.4, 8.12).
>
> Phase 8.3 step 5 adds ingestion observability: one structured event per ingestion request and relay attempt, and metrics through the `Metrics` port in `memory_engine.observability` (a no-op by default until monitoring is deployed). The [8.3 acceptance review](../docs/project-context/PHASE-8-3-ACCEPTANCE-REVIEW.md) maps every plan §13 criterion to its tests.
>
> Not yet: extraction, parsing, chunking, embedding generation, entity resolution, consolidation, retrieval ranking, and the deletion workflow.

## Boundaries

| Relationship | Rule |
|---|---|
| Agent Orchestrator | Coordinates work and calls the Memory Engine through defined interfaces. It never manipulates Memory Engine records directly, and the Memory Engine never orchestrates other engines. |
| Research Engine | Owns external research. The Memory Engine does not perform external discovery. |
| Shared Infrastructure | Provides database, storage, messaging, identity and monitoring. It contains no Memory Engine business logic, and the Memory Engine owns all of its own data. |

Layering inside the package ([7.1 §23.1](../docs/technical-decisions/01-baseline-technology-stack.md)): domain packages hold business concepts and invariants and must not import FastAPI, database drivers, SQLAlchemy, Celery, storage SDKs or `memory_engine.infrastructure`; application code depends on ports, never on infrastructure. Unit tests enforce these rules.

## Package layout

```text
memory-engine/
├── pyproject.toml            # workspace member: raven-memory-engine
├── .env.example              # configuration template (placeholders only)
├── alembic.ini               # migration config; the URL comes from settings, never this file
├── migrations/               # Alembic environment and versions (schema from settings)
└── src/memory_engine/
    ├── config/               # Pydantic Settings: MemoryEngineSettings, load_settings()
    ├── domain/               # shared kernel: domain errors, OwnerScope, ids, vocabularies
    ├── exceptions/           # base, configuration, application, infrastructure errors
    ├── observability/        # JSON logging and correlation context
    ├── personal/
    │   ├── domain/           # MemorySource, MemoryCandidate, AtomicMemory, revisions, provenance,
    │   │                     #   DocumentEvidenceRef (the only link into documents)
    │   └── application/      # ports: repository protocols and the unit of work
    ├── documents/            # never imports personal/ (one-way dependency, tested)
    │   ├── domain/           # Document, DocumentVersion, ExtractedRepresentation, DocumentChunk,
    │   │                     #   ChunkLocation, DocumentEmbedding, ProcessingOperation, vocabularies
    │   └── application/      # ports: repository protocols and the unit of work
    └── infrastructure/
        ├── object_storage/   # in-memory fake and boto3 adapter for the storage port
        ├── messaging/        # Celery app, topology, publisher and outbox relay (the only
        │                     #   code that imports celery/kombu)
        └── persistence/      # engine, units of work, me_outbox; personal/ (pm_) and
                              #   documents/ (doc_) models and repositories
```

Persistence rules that the code and the database both enforce:
- **Ownership:** every row carries `owner_id` and every query filters on it, so another owner's record behaves exactly like a missing one.
- **Links:** child records reference parents through composite foreign keys (owner or version included) with `RESTRICT`, so there are no implicit cascades and a chunk can never mix two versions.
- **Vocabularies:** vocabulary columns have check constraints.
- **Immutability:** Atomic Memory revisions, provenance, extracted representations, chunks and chunk locations are append-only. Documents, versions, embeddings and operations may change only their status columns (database triggers).
- **Concurrency:** status changes and revisions are conditional updates on the expected current state.
- **Deletion:** once a document's deletion is requested, no derived content can be written for it (`DeletionInProgressError`). Active document evidence blocks deletion of the passage it cites until the deletion workflow marks it `source_deleted`.

Tests live in the repository-root `tests/memory_engine/`, not in this directory.

## Configuration

Settings come from environment variables prefixed `RAVEN_MEMORY__` (nested values use `__`). See [`.env.example`](.env.example).

- `RAVEN_MEMORY__ENVIRONMENT`, the `RAVEN_MEMORY__DATABASE__*` host, name, user and password, the object-storage settings and the `RAVEN_MEMORY__BROKER__*` host, virtual host, user and password are required. Missing or invalid values stop startup with a `ConfigurationError` that names the fields but never echoes their values.
- No `.env` file is read unless you pass one explicitly: `load_settings(".env")`.
- Database access uses psycopg 3 with synchronous SQLAlchemy. Pool size, overflow, recycle and connect timeout are configurable (`RAVEN_MEMORY__DATABASE__POOL_SIZE` and so on). The engine hides bound parameters in error messages, because they can contain personal memory content.

## Development setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12. Run every command from the **repository root**; the root `pyproject.toml` defines the uv workspace and one root `uv.lock` covers all members.

```bash
uv sync
```

```bash
uv run pytest
```

```bash
uv run pytest --cov
```

```bash
uv run ruff check .
```

```bash
uv run ruff format --check .
```

```bash
uv run mypy
```

`uv sync` creates `.venv/` at the repository root and installs this package in editable mode together with the development tools. To activate the environment manually, use `.venv\Scripts\activate` on Windows or `source .venv/bin/activate` elsewhere.

### Integration tests (real PostgreSQL, object storage and broker)

Integration tests are marked `integration`. They run against three services from the repository's `docker-compose.yml`, all for development and testing only (Docker Desktop must be running):
- PostgreSQL with pgvector (`postgres-test`);
- SeaweedFS as the S3-compatible store (`object-storage-test`);
- RabbitMQ as the handoff broker (`broker-test`, `127.0.0.1:55672`; override with `RAVEN_TEST_BROKER_URL`, whose virtual host must end in `_test` because the tests purge the handoff queues).

Without a service, its tests are skipped with a message, not failed.

```bash
docker compose up -d --wait postgres-test object-storage-test broker-test
```

```bash
uv run pytest -m integration
```

```bash
uv run pytest -m "not integration"
```

The tests use the `raven_memory_test` database on `127.0.0.1:55432`; override with `RAVEN_TEST_DATABASE_URL`. As a guard, the database name must end in `_test`, because the fixtures drop and recreate schemas. Each test runs inside a transaction that is rolled back.

### Migrations

```bash
uv run alembic -c memory-engine/alembic.ini upgrade head
```

The URL and schema come from the `RAVEN_MEMORY__` settings. Migration files freeze their vocabularies as literals, and a unit test checks they still match the domain enums. Name constraints in migrations with `op.f(...)`, or Alembic applies the naming convention a second time.

## Architecture documentation

- [Project context and status](../docs/project-context/README.md)
- [Memory Engine architecture](../docs/architecture/phase-02-memory-engine.md)
- [Data models](../docs/data-models/Readme.md)
- [Memory algorithms](../docs/algorithms/Readme.md)
- [Technology decisions](../docs/technical-decisions/Readme.md), including the approved Phase 8.1 setup decisions in §22 of `01-baseline-technology-stack.md`
- [Phase 8 implementation plans](../docs/implementation-plans/Phase-08-memory-engine/Readme.md)
