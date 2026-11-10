# Next Steps

## Current position

- **Phase:** 8 — Memory Engine Implementation
- **Subphase:** 8.1 — Foundation and Project Setup (`VERIFIED`, uncommitted on `feat/phase-8-1-foundation`)
- **Next approved action:** none. Phase 8.2 is **not yet approved**. Wait for the user.

## Prerequisites before Phase 8.2

1. User reviews and commits Phase 8.1 (then push and merge into `main`).
2. The decisions below that are marked "8.2" are settled.
3. User explicitly approves starting 8.2.

## Approved 8.1 decisions (implemented)

All **APPROVED** on 2026-11-11 and recorded in [7.1 §22](../technical-decisions/01-baseline-technology-stack.md); implemented in Phase 8.1:

| Decision | Approved choice |
|---|---|
| Python version | Python 3.12 |
| Type checker | mypy, strict mode |
| Project layout | uv workspace: root workspace config, `memory-engine/` member, one root `uv.lock` |
| Test location | Repository-root `tests/` (`tests/memory_engine/…`) |
| Configuration | Pydantic Settings (`pydantic-settings`) |

## Open decisions

From the Memory Engine implementation-readiness review (2026-11-11). ⚑ = needs explicit approval (architecture, security, privacy or new infrastructure).

| # | Decision | Needed by | Recommendation |
|---|---|---|---|
| 1 | Code organization for Personal Memory vs Document Intelligence inside the package | 8.2 | Domain-first `personal/` and `documents/` packages, keeping plan 8.1's feature module names inside each |
| 2 | PostgreSQL driver; sync vs async database access | 8.2 | psycopg 3 with sync SQLAlchemy initially |
| 3 | Embedding model, dimension, similarity metric, index type | 8.2 (vector columns) or 8.7 | Choose before 8.7; 8.2 creates embedding metadata only |
| 4 | ⚑ Canonical vocabularies: memory relationship types (5.4.27 vs 6.3.8), supersession types (6.3.7), resolution outcomes (6.3) | 8.2, 8.6 | Three separate enums; `ABOUT_ENTITY` modeled as the memory-entity link |
| 5 | Placement of Document Intelligence records (shared `memory` schema vs separate schema) | 8.2 | `memory` schema with separate, prefixed tables (7.2 amendment) |
| 6 | ⚑ Document-to-memory authorization model (consent record, scope, expiry) | 8.4 document path, 8.12 | Per-request authorization record tied to user, document version and scope |
| 7 | ⚑ Sequence: run 8.12 before 8.11; 8.4's document-derived path after 8.12 | Plan order | Approve the reorder |
| 8 | ⚑ Local S3-compatible object storage for development and tests (new infrastructure) | 8.3 | Docker Compose S3-compatible service, development only |
| 9 | When to introduce Celery/RabbitMQ and the transactional outbox | 8.3 | Outbox table in 8.2; Celery in 8.3 |
| 10 | Owner identity before an identity provider is chosen | 8.3 | Memory Engine accepts a validated owner scope from its caller |
| 11 | ⚑ Shared public entities (5.4.13): population and privacy | 8.5 | Private entities only at first |
| 12 | Derived-profile ownership (Phase 2 component 3 vs Phase 6 / plan 8.9) | 8.9 | Consolidation (8.9) |
| 13 | Document parsing appears in both 6.2.1 and the document pipeline | 8.3, 8.12 | Document pipeline owns parsing |
| 14 | spaCy pipeline; scoring thresholds and weights; evaluation datasets | 8.4–8.11 | Synthetic versioned datasets built with each subphase |
| 15 | ⚑ Approve pypdf and python-docx | 8.12 | Evaluate at 8.12 start |

## Required documentation for 8.2

- [Plan 8.2](../implementation-plans/Phase-08-memory-engine/02-database-and-persistence.md)
- [5 overview](../data-models/phase-05-data-models-overview.md), [5.4 memory models +amendment](../data-models/phase-05-memory-engine-models.md), [5.8–5.10 +amendment](../data-models/phase-05-relationships-and-lifecycle.md)
- [7.2 +amendment](../technical-decisions/02-database-and-storage-architecture.md); [7.3](../technical-decisions/03-vector-search-and-embedding-infrastructure.md) §9

## Session Handoff

*Overwrite this section at the end of every session that changes the repository.*

- **Date:** 2026-11-11
- **Objective:** Implement Phase 8.1 Foundation and Project Setup.
- **Work completed:** uv workspace (root `pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore`); `memory-engine` member package with config (Pydantic Settings), error hierarchy, domain errors, structured JSON logging with correlation context and redaction; 71 foundation tests in `tests/memory_engine/unit/`; `memory-engine/README.md`; context files updated.
- **Files changed:** 24 new files (listed in [IMPLEMENTATION_STATE.md](IMPLEMENTATION_STATE.md)) plus updates to `PROJECT_STATUS.md`, `IMPLEMENTATION_STATE.md`, `NEXT_STEPS.md`, `TECHNOLOGY_DECISIONS.md`, `KNOWN_CONSTRAINTS.md`, `.claude/rules/coding-standards.md` and `CLAUDE.md`. Uncommitted on `feat/phase-8-1-foundation`.
- **Implementation status:** 8.1 `VERIFIED`; 8.2–8.12 `NOT_STARTED`.
- **Tests and results:** `uv run pytest --cov` → 71 passed, 98% coverage; `uv run ruff check .` and `uv run ruff format --check .` → clean; `uv run mypy` (strict) → no issues in 16 files (run from a short-path environment, see limitations); `uv sync --locked` → succeeded.
- **Decisions made:** Ruff rule set E, W, F, I, B, UP, SIM, S, N, RUF (S101 allowed in tests); mypy strict with the Pydantic plugin over `memory-engine/src` and `tests`; hatchling build backend; JSON-only log format; `RAVEN_MEMORY__` environment prefix.
- **Unresolved:** the Open decisions table above; uv is not on PATH on this machine.
- **Next action:** user review and commit of 8.1; then settle decisions 1–5 and approve 8.2.
- **Read next session:** `CLAUDE.md`, this directory's `PROJECT_STATUS.md`, `ARCHITECTURE_SUMMARY.md`, `KNOWN_CONSTRAINTS.md`, `NEXT_STEPS.md`, then plan 8.2 and the documents listed above.
