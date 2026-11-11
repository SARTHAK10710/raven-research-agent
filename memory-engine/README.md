# Raven Memory Engine

The Memory Engine is one of Raven's three primary engines. It owns Raven's persistent knowledge in two **separate logical domains**:

- **Personal Memory** — facts, preferences, goals, decisions, events, entities and relationships about the user, built through ingestion → extraction → evaluation → resolution → storage → retrieval → consolidation, with explicit forgetting.
- **Document Intelligence** — uploaded PDF, DOCX and TXT documents: registration, versioning, extraction, structure-aware chunking, embeddings, hybrid retrieval, evidence selection and citations.

The two domains can share infrastructure (PostgreSQL, pgvector, object storage, workers) but never share records, retrieval workflows or lifecycle rules. Document chunks are not personal memories, and uploading a document never creates memories automatically.

> **Status:** Phase 8.1 foundation plus Phase 8.2 step 1: PostgreSQL persistence for the core Personal Memory records (Memory Source, Memory Candidate, Atomic Memory with immutable revisions, Provenance), with owner-scoped repositories, a unit of work and the first Alembic migration. No ingestion, extraction, resolution, retrieval ranking, deletion workflow or Document Intelligence persistence exists yet.

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
    │   ├── domain/           # MemorySource, MemoryCandidate, AtomicMemory, revisions, provenance
    │   └── application/      # ports: repository protocols and the unit of work
    └── infrastructure/
        └── persistence/      # engine, unit of work, pm_ models and repositories
```

Persistence rules that the code and the database both enforce: every row carries `owner_id`, and every query filters on it, so another owner's record behaves exactly like a missing one. Child records reference parents through `(id, owner_id)` composite foreign keys with `RESTRICT` (no implicit cascades). Vocabulary columns have check constraints. Atomic Memory revisions and provenance are append-only (database triggers reject `UPDATE`). Revisions use optimistic concurrency on `revision_number`.

Tests live in the repository-root `tests/memory_engine/`, not in this directory.

## Configuration

Settings come from environment variables prefixed `RAVEN_MEMORY__` (nested values use `__`). See [`.env.example`](.env.example).

- `RAVEN_MEMORY__ENVIRONMENT` and the `RAVEN_MEMORY__DATABASE__*` host, name, user and password are required. Missing or invalid values stop startup with a `ConfigurationError` that names the fields but never echoes their values.
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

### Integration tests (real PostgreSQL)

Integration tests are marked `integration` and run against PostgreSQL with pgvector from the repository's `docker-compose.yml` (development and testing only; Docker Desktop must be running). Without the database they are skipped with a message, not failed.

```bash
docker compose up -d --wait postgres-test
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
