# Raven Memory Engine

The Memory Engine is one of Raven's three primary engines. It owns Raven's persistent knowledge in two **separate logical domains**:

- **Personal Memory** — facts, preferences, goals, decisions, events, entities and relationships about the user, built through ingestion → extraction → evaluation → resolution → storage → retrieval → consolidation, with explicit forgetting.
- **Document Intelligence** — uploaded PDF, DOCX and TXT documents: registration, versioning, extraction, structure-aware chunking, embeddings, hybrid retrieval, evidence selection and citations.

The two domains can share infrastructure (PostgreSQL, pgvector, object storage, workers) but never share records, retrieval workflows or lifecycle rules. Document chunks are not personal memories, and uploading a document never creates memories automatically.

> **Status:** Phase 8.1 (foundation) only. This package currently provides validated configuration, the error hierarchy, structured logging and the domain-layer boundary. No ingestion, extraction, storage, retrieval or document processing exists yet.

## Boundaries

| Relationship | Rule |
|---|---|
| Agent Orchestrator | Coordinates work and calls the Memory Engine through defined interfaces. It never manipulates Memory Engine records directly, and the Memory Engine never orchestrates other engines. |
| Research Engine | Owns external research. The Memory Engine does not perform external discovery. |
| Shared Infrastructure | Provides database, storage, messaging, identity and monitoring. It contains no Memory Engine business logic, and the Memory Engine owns all of its own data. |

Layering inside the package: the `domain` layer holds business concepts and invariants and must not import FastAPI, database drivers, SQLAlchemy, Celery, storage SDKs or `memory_engine.infrastructure`. A unit test enforces this.

## Package layout (Phase 8.1)

```text
memory-engine/
├── pyproject.toml            # workspace member: raven-memory-engine
├── .env.example              # configuration template (placeholders only)
└── src/memory_engine/
    ├── config/               # Pydantic Settings: MemoryEngineSettings, load_settings()
    ├── domain/               # domain layer (Phase 8.1: domain errors only)
    ├── exceptions/           # base, configuration, application, infrastructure errors
    └── observability/        # JSON logging and correlation context
```

Tests live in the repository-root `tests/memory_engine/`, not in this directory.

## Configuration

Settings come from environment variables prefixed `RAVEN_MEMORY__` (nested values use `__`). See [`.env.example`](.env.example).

- `RAVEN_MEMORY__ENVIRONMENT` and the `RAVEN_MEMORY__DATABASE__*` host, name, user and password are required. Missing or invalid values stop startup with a `ConfigurationError` that names the fields but never echoes their values.
- No `.env` file is read unless you pass one explicitly: `load_settings(".env")`.
- Phase 8.1 validates database settings but does not connect to a database.

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

## Architecture documentation

- [Project context and status](../docs/project-context/README.md)
- [Memory Engine architecture](../docs/architecture/phase-02-memory-engine.md)
- [Data models](../docs/data-models/Readme.md)
- [Memory algorithms](../docs/algorithms/Readme.md)
- [Technology decisions](../docs/technical-decisions/Readme.md), including the approved Phase 8.1 setup decisions in §22 of `01-baseline-technology-stack.md`
- [Phase 8 implementation plans](../docs/implementation-plans/Phase-08-memory-engine/Readme.md)
