# Implementation State

Actual implementation progress, recorded only from verified repository state.

Status values: `NOT_STARTED` · `INSPECTION` · `IN_PROGRESS` · `IMPLEMENTED` · `TESTING` · `VERIFIED` · `BLOCKED`. `VERIFIED` requires executed test evidence against the subphase's acceptance criteria; generated code is never verified by itself.

**Baseline:** `main` @ `ab50c48` (PR #4); PR #6 (status docs) and PR #7 (8.2 step 1, `d2346b6`) open and stacked; 8.2 step 2 uncommitted on `feat/phase-8-2-document-persistence`.

## Summary

| Subphase | Status | Commit |
|---|---|---|
| 8.1 Foundation and project setup | `VERIFIED` | `5a0d6e5`, merged in `6efd72d` (PR #3) |
| 8.2 Database and persistence | `IN_PROGRESS` (steps 1–2 tested) | Step 1 `d2346b6` (PR #7); step 2 uncommitted on `feat/phase-8-2-document-persistence` |
| 8.3 Ingestion pipeline | `NOT_STARTED` | — |
| 8.4 Extraction and evaluation | `NOT_STARTED` | — |
| 8.5 Entity and relationship management | `NOT_STARTED` | — |
| 8.6 Memory resolution | `NOT_STARTED` | — |
| 8.7 Memory storage and indexing | `NOT_STARTED` | — |
| 8.8 Memory retrieval | `NOT_STARTED` | — |
| 8.9 Consolidation and maintenance | `NOT_STARTED` | — |
| 8.10 Forgetting and deletion | `NOT_STARTED` | — |
| 8.11 Integration and testing | `NOT_STARTED` | — |
| 8.12 Document RAG pipeline | `NOT_STARTED` | — |

## 8.1 — Foundation and project setup

| Field | Value |
|---|---|
| Status | `VERIFIED` (2026-11-11) — every plan 8.1 §15 acceptance criterion met with executed checks; re-verified after merge on 2026-11-11 (same results) |
| Files created (24) | Root: `pyproject.toml` (uv workspace + Ruff, mypy, pytest, coverage config), `uv.lock`, `.python-version`, `.gitignore`. `memory-engine/`: `pyproject.toml`, `README.md`, `.env.example`, `src/memory_engine/` (`__init__.py`, `py.typed`, `config/{__init__,settings}.py`, `domain/{__init__,errors}.py`, `exceptions/{__init__,base}.py`, `observability/{__init__,context,logging}.py`). `tests/memory_engine/`: `conftest.py`, `unit/test_{package,config,exceptions,domain_boundary,logging}.py` |
| Files modified | None outside the files above, apart from these context files |
| Dependencies introduced | Runtime: `pydantic` 2.14.3, `pydantic-settings` 2.16.2. Dev: `pytest` 9.2.0, `pytest-cov` 7.1.0, `ruff` 0.17.4, `mypy` 2.4.1. 22 locked packages in total including transitive. Build backend: `hatchling` (build time only) |
| Tests executed | `uv run pytest --cov`; `uv run ruff check .`; `uv run ruff format --check .`; `uv run mypy`; `uv sync --locked` |
| Tests passed / failed | pytest **71 passed, 0 failed** (98% line+branch coverage); Ruff lint and format clean; mypy strict **no issues in 16 files**; locked sync succeeded |
| Commit | `5a0d6e5` on `feat/phase-8-1-foundation` (31 files: 24 added, 7 modified); pushed; merged into `main` via PR #3 as `6efd72d` |

**What exists:** validated configuration (`RAVEN_MEMORY__` prefix, required environment and database settings, secrets as `SecretStr`, no implicit `.env`, sanitized `ConfigurationError`); error hierarchy (base, configuration, application/authorization, infrastructure/persistence, plus domain/validation/ownership in `domain/errors.py`); JSON logging on the `raven.memory_engine` logger with correlation context, redaction and exception type/code only; a source-scanning test enforcing the domain boundary.

**Deviations from plan 8.1 (deliberate, recorded):**
- No object-storage configuration placeholders (plan §6): nothing consumes them yet; added when object storage is implemented (8.2/8.3).
- `load_settings` does not chain the original Pydantic error, because it embeds raw input values (possibly secrets); a field-and-type summary is kept instead.
- Feature-specific error types (ingestion, extraction, resolution, retrieval, deletion) are added in the subphases that raise them.

**Known limitations:**
- On Windows, a repository at a very long path cannot load mypy's compiled DLLs from `.venv` ("filename or extension is too long"), even with long paths enabled. Investigated on 2026-11-11: it fails at a 180-character repository root (mypyc extension paths reach 256–263 characters), and passes from a fresh clone at a 109-character root with an ordinary in-tree `.venv` (mypy strict clean, 71 tests passed). Environmental, not a project defect.
- uv was installed for this machine with `pip install --user uv` (0.13.7); its `Scripts` directory is not on PATH.
- `tests/.gitkeep` and `memory-engine/.gitkeep` remain although the directories now have content.
- On Windows, a default `git clone` fails checkout because several `docs/implementation-plans/Phase-08-memory-engine/` and `docs/technical-decisions/03-…` paths exceed 260 characters at deep locations. Workaround: `git config core.longpaths true` (or clone to a short path).
- Log redaction matches key substrings, so any `extra` field containing `session` (for example a future `research_session_id`) or `token` is redacted. Revisit when such identifiers are logged.

## 8.2 — Database and persistence

| Field | Value |
|---|---|
| Status | `IN_PROGRESS` — approved 2026-11-11. Step 1 committed (`d2346b6`, PR #7); step 2 (Document Intelligence persistence) implemented and tested, uncommitted; step 3+ not started |
| Files created (step 1) | Root: `docker-compose.yml`. `memory-engine/`: `alembic.ini`, `migrations/{env.py,script.py.mako,versions/20261111_0001_personal_memory_core.py}`, `src/memory_engine/domain/{identifiers,vocabulary}.py`, `personal/{__init__,domain/__init__,domain/records,application/__init__,application/ports}.py`, `infrastructure/{__init__,persistence/__init__,persistence/base,persistence/database,persistence/unit_of_work,persistence/personal/__init__,persistence/personal/models,persistence/personal/repositories}.py`. Tests: `unit/test_{personal_records,persistence_definitions}.py`, `integration/{conftest,test_migrations,test_personal_repositories}.py` |
| Files created (step 2) | `memory-engine/migrations/versions/20261111_0002_document_intelligence.py`; `src/memory_engine/documents/{__init__,domain/__init__,domain/records,domain/vocabulary,application/__init__,application/ports}.py`; `infrastructure/persistence/documents/{__init__,models,repositories}.py`. Tests: `unit/test_document_records.py`, `integration/test_document_repositories.py` |
| Files modified (step 2) | `domain/vocabulary.py` (`DocumentEvidenceStatus`); `personal/domain/{__init__,records}.py` (`DocumentEvidenceRef`, provenance evidence link); `personal/application/ports.py` (`DocumentEvidenceRepository`); `exceptions/{__init__,base}.py` (`DeletionInProgressError`); `infrastructure/persistence/{__init__,base,unit_of_work}.py`; `persistence/personal/{models,repositories}.py`; `migrations/env.py`; tests `unit/test_{persistence_definitions,personal_records,domain_boundary,exceptions}.py`, `integration/{conftest,test_migrations}.py`. No new dependencies |
| Migration (step 2) | `0002_document_intelligence`: 7 `doc_` tables, `pm_document_evidence_ref`, `pm_provenance.document_evidence_id`, `simple` full-text vector + GIN index, `me_guard_columns` triggers on 8 tables. Tested upgrade → downgrade → upgrade and downgrade to `0001` |
| Tests (step 2) | **225 passed, 0 failed** (169 unit, 56 integration), 97% coverage; database stopped → 56 skipped; Ruff clean; mypy strict clean (47 files) |
| Files modified (step 1) | Root `pyproject.toml` (mypy `explicit_package_bases`, marker text), `uv.lock`; `memory-engine/{pyproject.toml,.env.example,README.md}`; `config/settings.py` (pool settings); `exceptions/{__init__,base}.py` (`RecordNotFoundError`, `ConcurrencyConflictError`); tests `unit/test_{config,exceptions,domain_boundary}.py` |
| Dependencies introduced | Runtime: `sqlalchemy` 2.1.8, `alembic` 1.20.1 (+ `mako` 1.4.3, `markupsafe` 3.0.4), `psycopg[binary]` 3.3.8, `tzdata` 2026.6. Dev: none |
| Migrations | `0001_personal_memory_core`: 5 `pm_` tables, composite `(id, owner_id)` foreign keys with `RESTRICT`, vocabulary/score/temporal check constraints, append-only triggers on `pm_atomic_memory_revision` and `pm_provenance`. Tested upgrade → downgrade → upgrade |
| Tests executed | `uv sync --locked`; `uv run pytest --cov` (with `docker compose up -d --wait postgres-test`); `uv run pytest -m integration` with the database stopped; `uv run ruff check .`; `uv run ruff format --check .`; `uv run mypy` |
| Tests passed / failed | **162 passed, 0 failed** (136 unit, 26 integration), 98% line+branch coverage; database stopped → 26 skipped with message; Ruff clean; mypy strict clean (36 files) |
| Commit | Step 1: `d2346b6` (PR #7, open, stacked on PR #6). Step 2: — (uncommitted on `feat/phase-8-2-document-persistence`) |

**Plan 8.2 §14 acceptance criteria, after step 2** (met for the records built so far):
- 2: personal memory persistence (step 1).
- 3: document identity is independent of the filename, and versions keep their history.
- 4: originals are referenced by opaque, owner-partitioned object keys. Storage itself arrives in 8.3.
- 5: extracted content and chunk metadata, with locations, are persisted.
- 6: document embedding metadata is separate from personal memory, and only the evidence path crosses domains (tested).
- 7: ownership is enforced in SQL and by composite foreign keys, for both domains.
- 8: transactions, optimistic concurrency and conditional status changes are tested.
- 9: migrations execute and reverse.
- 10: failure behavior is tested: rollback, stale update, duplicate key, failed extraction, retry, idempotency, a stale worker after deletion is requested, and the database unreachable.
- 11: deletion dependencies, including citing memories, are discoverable.

Not yet: 1 and 12 for the full model (entities, relationships, episodes, profiles and the rest, step 3+). Object-storage failure tests (plan 8.2 §13) wait for object storage in 8.3.

**Step 2 deviations and decisions (recorded):**
- Document vocabularies and the `simple` full-text configuration were approved by the owner (5.4 Document Intelligence amendment §14).
- Evidence rows keep opaque `*_ref` identifiers next to the foreign-key columns, so `RESTRICT` and permanent provenance can both hold (7.1 §23.3 note).
- Bugs caught by the step 2 tests: a NULL-passing check constraint on evidence links, and unordered chunk locations. Both are fixed with tests.

**Deviations and decisions (recorded):**
- Memory Source processing states were undefined; the owner approved a vocabulary derived from 6.2 (5.4 amendment §11).
- No `me_operation` table: no specification or consumer in step 1 (7.1 §23.6 implementation note).
- `MemorySource.content_ref` is optional until object storage exists (8.3); `content_sha256` is stored when known.
- Revisions, not a separate version column, carry optimistic concurrency for Atomic Memory (`revision_number` checked in a conditional `UPDATE`).

**Known limitations:**
- Entities, relationships, episodes, profiles, categories, memory embedding metadata and deletion records are not yet persisted (8.2 step 3+).
- Integration tests need Docker Desktop running; without it they skip, so a green run without the database does not cover persistence.
- The commit-failure path of the unit of work is not exercised by a test.
- Full-text search uses the language-neutral `simple` configuration until the language requirement (G6) is decided.
- Object keys are recorded but nothing is stored yet (object storage is 8.3).

## 8.3–8.12

`NOT_STARTED`. No files, dependencies or tests.

## Non-implementation repository changes

These are documentation changes, tracked here so they are not mistaken for implementation progress.

| Change | State | Branch / commit |
|---|---|---|
| Restore overwritten specs 5.4, 5.8–5.10, 7.2, 7.3 with amendments appended; move the 7.5 amendment to file 05; correct doc paths; update stale top-level docs | Merged into `main` (PR #1); validated against Git originals | `83e174e`, merged in `f6abef0` |
| Project-context system (`CLAUDE.md`, `.claude/rules/`, `docs/project-context/`) | Merged into `main` (PR #1) | `83e174e`, merged in `f6abef0` |
| Record approved 8.1 setup decisions in 7.1 §22, 7.7, technical-decisions Readme, Phase 8 Readme and plan 8.1 | Merged into `main` (PR #1) | `83e174e`, merged in `f6abef0` |
| Record PR #1 merge in status files | Merged into `main` (PR #2) | `de7ed06`, merged in `2c35fb3` |
| Phase 8.1 checkpoint correction, [Phase 8.2 architecture decision review](PHASE-8-2-ARCHITECTURE-DECISION-REVIEW.md), and the approved Decisions 1, 2, 4, 5, 10 recorded in 7.1 §23, the 5.4 Phase 8.2 amendment and plans 8.1/8.2 | Merged into `main` (PR #4) | `22cc9f1` and `38a338e`, merged in `ab50c48` |
| Sync status files with the PR #3 merge; record audit findings (long-path clone, log redaction, ratio-label wording) | Merged into `main` (PR #5) | `c9544af` |
