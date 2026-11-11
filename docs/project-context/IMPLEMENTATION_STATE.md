# Implementation State

Actual implementation progress, recorded only from verified repository state.

Status values: `NOT_STARTED` · `INSPECTION` · `IN_PROGRESS` · `IMPLEMENTED` · `TESTING` · `VERIFIED` · `BLOCKED`. `VERIFIED` requires executed test evidence against the subphase's acceptance criteria; generated code is never verified by itself.

**Baseline:** `main` @ `423b6fd` (PR #11 merged 8.2 step 5 and the acceptance-review fixes; PR #10 merged step 4 as `977c3b7`; PR #9 step 3; PR #8 steps 1–2).

## Summary

| Subphase | Status | Commit |
|---|---|---|
| 8.1 Foundation and project setup | `VERIFIED` | `5a0d6e5`, merged in `6efd72d` (PR #3) |
| 8.2 Database and persistence | `VERIFIED` (2026-11-11) | Steps 1–2 `d2346b6`, `e7fc443` (PR #8); step 3 `7a62cd4` (PR #9); step 4 `38411e1` (PR #10, `977c3b7`); step 5 `42b35c3` and review fixes `1b58b77` (PR #11, `423b6fd`) |
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
| Status | `VERIFIED` (2026-11-11) — approved 2026-11-11; all five steps and the acceptance-review fixes are merged. Every plan 8.2 §14 criterion is met with executed checks on `main` @ `423b6fd` (A4), with two owner-accepted deferrals ([acceptance review](PHASE-8-2-ACCEPTANCE-REVIEW.md)) |
| Verification on `main` (A4) | `uv sync --locked` ok; `ruff check`, `ruff format --check` clean; `mypy` strict clean (63 files); `uv run pytest --cov` **412 passed** (300 unit, 112 integration against PostgreSQL 17 + pgvector), 96% coverage, plus 3 further green runs; database stopped → 112 skipped |
| Files created (review fixes) | `migrations/versions/20261111_0006_episode_version.py`; `integration/test_concurrency_and_failures.py`; `docs/project-context/PHASE-8-2-ACCEPTANCE-REVIEW.md` |
| Files created (step 5) | `migrations/versions/20261111_0005_processing_corrections_deletion.py`; `personal/domain/lifecycle.py`; `infrastructure/persistence/personal/{lifecycle_models,lifecycle_repositories}.py`. Tests: `unit/test_lifecycle_records.py`, `integration/test_lifecycle_repositories.py` |
| Files modified (step 5) | `domain/vocabulary.py` (8 vocabularies); `personal/domain/__init__.py`; `personal/application/ports.py` (processing, evaluation, correction and deletion ports); `infrastructure/persistence/unit_of_work.py`; `migrations/env.py`; tests `unit/test_persistence_definitions.py`, `integration/test_migrations.py`. No new dependencies |
| Migration (step 5) | `0005_processing_deletion`: `pm_source_processing_event` and `pm_candidate_evaluation` (append-only, `seq` ordering), `pm_correction_request`, `pm_correction_memory` (base and applied revision foreign keys), `pm_deletion_operation` (unique per owner and idempotency key), `pm_deletion_target` (ledger, no foreign key to targets); `me_guard_columns` triggers on all six and, new, on `pm_memory_source` and `pm_memory_candidate` |
| Tests (step 5) | **406 passed, 0 failed** (296 unit, 110 integration), 96% coverage; Ruff clean; mypy strict clean (62 files) |
| Files created (step 4) | `migrations/versions/20261111_0004_episodes_profiles_categories.py`; `personal/domain/derived.py`; `infrastructure/persistence/personal/{derived_models,derived_repositories}.py`. Tests: `unit/test_derived_records.py`, `integration/test_derived_repositories.py` |
| Files modified (step 4) | `domain/vocabulary.py` (8 vocabularies; `EmbeddingStatus` moved here); `documents/domain/vocabulary.py` (re-exports `EmbeddingStatus`); `personal/domain/__init__.py`; `personal/application/ports.py` (episode, profile, category, memory-embedding ports); `infrastructure/persistence/unit_of_work.py`; `migrations/env.py`; tests `unit/test_persistence_definitions.py`, `integration/test_migrations.py`. No new dependencies |
| Migration (step 4) | `0004_episodes_profiles`: `pm_episode`, `pm_episode_membership`, `pm_episode_event`, `pm_profile`, `pm_profile_revision`, `pm_profile_memory`, `pm_profile_refresh` (`seq` ordering), `pm_memory_category`, `pm_memory_embedding` (metadata only, no vector column); partial unique indexes for current rows; a deferrable `pm_profile` → current-revision foreign key; `me_guard_columns` triggers on all nine |
| Tests (step 4) | **340 passed, 0 failed** (252 unit, 88 integration), 96% coverage; database stopped → 88 skipped; Ruff clean; mypy strict clean (57 files) |
| Files created (step 3) | `migrations/versions/20261111_0003_entities_and_relationships.py`; `personal/domain/entities.py`; `infrastructure/persistence/personal/{entity_models,entity_repositories}.py`. Tests: `unit/test_entity_records.py`, `integration/test_entity_repositories.py` |
| Files modified (step 3) | `domain/vocabulary.py` (7 vocabularies); `personal/domain/__init__.py`; `personal/application/ports.py` (entity, mention, relationship ports); `infrastructure/persistence/{database,unit_of_work}.py` (shared `conditional_update`; new repositories); `persistence/documents/repositories.py` (uses the shared helper); `migrations/env.py`; tests `unit/test_persistence_definitions.py`, `integration/test_migrations.py`. No new dependencies |
| Migration (step 3) | `0003_entities_and_relationships`: `pm_entity` (private only), `pm_entity_alias`, `pm_entity_mention`, `pm_entity_resolution` (append-only, `seq` ordering), `pm_entity_relationship`, `pm_memory_relationship` (partial unique indexes for current rows), `pm_memory_entity`; `me_guard_columns` triggers on all seven |
| Tests (step 3) | **288 passed, 0 failed** (217 unit, 71 integration), 97% coverage; Ruff clean; mypy strict clean (52 files) |
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
| Commit | Step 1 `d2346b6` and step 2 `e7fc443`: merged into `main` through PR #8 (`0743e02`). Step 3 `7a62cd4`: merged through PR #9 (`b31a97e`). Step 4 `38411e1`: PR #10 (`977c3b7`). Step 5 `42b35c3` and review fixes `1b58b77`: PR #11 (`423b6fd`) |

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

**Acceptance review (2026-11-11, on the step-5 branch before PRs #10 and #11 merged):** see [PHASE-8-2-ACCEPTANCE-REVIEW.md](PHASE-8-2-ACCEPTANCE-REVIEW.md). Criteria 2–7, 9 and 11 met. 1, 8 and 10 partly met, and 12 met for the existing 406 tests. Not yet `VERIFIED`. Follow-up, the same day:
- A1 fixed: migration `0006_episode_version` adds `pm_episode.version`, and `EpisodeRepository.update` takes `expected_version`.
- A2 fixed: new tests for two racing connections, a failed commit and a failing migration (`integration/test_concurrency_and_failures.py`, plus a unit test).
- A3 deferrals accepted by the owner (recorded in `KNOWN_CONSTRAINTS.md`).
- After the fixes: **412 passed** (300 unit, 112 integration), 96% coverage, 6 runs green; mypy strict clean (63 files). Committed as `1b58b77`.
- **A4 done:** PRs #10 and #11 merged, and the checks re-run on `main` @ `423b6fd` with the same results. 8.2 is `VERIFIED`.

**Step 5 decisions and findings (recorded):**
- The owner approved the processing-event, evaluation, correction and deletion vocabularies and designs (5.4 Phase 8.2 amendment §14), and stacking step 5 on the unmerged step-4 branch.
- The deletion ledger names records by kind and identifier without foreign keys, so it outlives purged records and can be replayed after a restore. A unit test keeps the target kinds equal to the `pm_` tables.
- `pm_memory_source` and `pm_memory_candidate` are now column-guarded: only their state columns (and the source's content reference) can change.
- Bug caught by the step 5 tests: SQLAlchemy stores Python `None` in a JSONB column as the JSON value `null`, not SQL `NULL`, so purging a correction request did not clear its content. The database check rejected it; the purge now writes `null()`.
- A test relied on the order of two operations requested at the same instant (a tie broken by random UUIDs) and failed intermittently. It now uses distinct times; the suite then passed 6 runs in a row.
- Every record type in plan 8.2 §3 now has persistence, except consolidation results, which wait for 8.9 (approved). Whether that fully satisfies criterion 1 (matches Phase 5 and 7) is for the acceptance review to check.

**Step 4 decisions and findings (recorded):**
- The owner approved the episode, profile, refresh, category and embedding-purpose vocabularies, episode membership without a role, and no consolidation-result table until 8.9 defines one (5.4 Phase 8.2 amendment §13).
- A profile and its current revision reference each other; the foreign key from `pm_profile` to the current revision is deferrable, and profile writes defer it, then check it immediately before returning.
- Bug caught by the step 4 tests: `SET CONSTRAINTS ALL IMMEDIATE` lasts for the rest of the transaction, so a second profile created in the same unit of work failed. Fixed by deferring at the start of every profile write, with a test.
- Criterion 1 now covers everything except the step 5 records (deletion operations, correction requests, candidate evaluation history, source processing events).

**Step 3 decisions and findings (recorded):**
- Decision 11 ⚑ approved: entities are private only (7.1 §23.7). Entity, mention and resolution vocabularies approved (5.4 Phase 8.2 amendment §12).
- Bugs caught by the step 3 tests: a check that compared two possibly-NULL columns with `IS DISTINCT FROM` (false for NULL/NULL), and resolution history order that was unstable within one transaction. Both are fixed with tests.
- Criterion 1 (database foundation matches Phase 5) now covers the core, document, entity and relationship models; episodes, profiles, categories, consolidation and memory embedding metadata (step 4) and the deletion, correction, evaluation and processing records (step 5) remain.

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
- Consolidation results have no table until 8.9 defines a result type.
- Deletion records store operations and their ledger; nothing performs a deletion yet (plan 8.10). Candidate propositions and other content columns are not yet purgeable through a repository; 8.10 adds the purge paths (and widens the column guards where needed).
- Ledger rows are owner-scoped but, by design, not checked against the records they name.
- Entity persistence stores and protects decisions; it does not make them. Entity resolution itself (6.3.4) is Phase 8.5.
- Likewise, episode, profile and category persistence records outcomes only: episode detection, profile generation and refresh logic (consolidation) are 8.9, and memory embedding vectors are 8.7.
- Integration tests need Docker Desktop running; without it they skip, so a green run without the database does not cover persistence.
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
