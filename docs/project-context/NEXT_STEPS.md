# Next Steps

## Current position

- **Phase:** 8 — Memory Engine Implementation
- **Subphase:** 8.1 — Foundation and Project Setup (`INSPECTION`)
- **Next approved action:** none. Phase 8.1 implementation is **not yet approved**. Wait for the user.

## Prerequisites before 8.1 implementation

1. User explicitly approves starting 8.1. (The documentation recovery and context system are merged into `main` via PR #1, merge commit `f6abef0`.)

## Approved 8.1 decisions

All **APPROVED** on 2026-11-11 and recorded in [7.1 §22](../technical-decisions/01-baseline-technology-stack.md), the [Phase 8 Readme §7.1](../implementation-plans/Phase-08-memory-engine/Readme.md) and [plan 8.1 §5](../implementation-plans/Phase-08-memory-engine/01-foundation-and-project-setup.md):

| Decision | Approved choice |
|---|---|
| Python version | Python 3.12 |
| Type checker | mypy, strict mode |
| Project layout | uv workspace: root workspace config, `memory-engine/` member, one root `uv.lock` |
| Test location | Repository-root `tests/` (`tests/memory_engine/…`) |
| Configuration | Pydantic Settings (`pydantic-settings`) |

Dependency timing: 8.1 adds `pydantic`, `pydantic-settings`, and for development `pytest`, `pytest-cov`, `ruff`, `mypy`. SQLAlchemy, Alembic and the PostgreSQL driver come in 8.2. HTTPX and OpenTelemetry are added only when required.

## Still open (not blocking the start of 8.1)

| Item | Recommendation | Needed by |
|---|---|---|
| Code organization for Personal Memory vs Document Intelligence inside the package | Domain-first `personal/` and `documents/`, created only when needed | Before the first domain code (8.2/8.3) |
| Ruff rule selection; mypy settings beyond strict mode | Set during 8.1 | 8.1 implementation |
| PostgreSQL driver; sync vs async database access | — | 8.2 |

## Required documentation for 8.1

- [Plan 8.1](../implementation-plans/Phase-08-memory-engine/01-foundation-and-project-setup.md)
- [7.1 §22](../technical-decisions/01-baseline-technology-stack.md) (approved setup decisions and dependency timing)
- [7.1 baseline](../technical-decisions/01-baseline-technology-stack.md)
- [7.7](../technical-decisions/07-observability-and-testing-infrastructure.md) §3, §6, §10–12, §17
- [7.8](../technical-decisions/08-deployment-and-environment-architecture.md) §4, §6–7

## Session Handoff

*Overwrite this section at the end of every session that changes the repository.*

- **Date:** 2026-11-11
- **Objective:** Recover overwritten specifications, establish the persistent project-context system, and record the approved Phase 8.1 setup decisions.
- **Work completed:**
  - Restored 5.4, 5.8–5.10, 7.2 and 7.3 from Git (originals byte-identical), with amendments appended; moved the 7.5 amendment from file 03 to file 05.
  - Corrected 86 broken documentation paths and fixed the data-model, algorithm and architecture index tables.
  - Updated `README.md`, `PROJECT_ARCHITECTURE.md` and `docs/architecture/Readme.md`.
  - Created `CLAUDE.md`, `.claude/rules/` (4 files) and `docs/project-context/` (7 files); labeled five Raven engineering conventions; added the UI / Entry Layer status row.
  - Recorded the five approved 8.1 decisions and dependency timing in 7.1 §22, the Phase 8 Readme §7.1 and plan 8.1, and aligned 7.7 and the technical-decisions Readme (mypy strict).
- **Files changed:** commit `83e174e` — 27 modified documentation files and 12 new context files (39 total), plus status-file follow-ups. Merged into `main` via PR #1 (merge commit `f6abef0`). No application code.
- **Implementation status:** no implementation. 8.1 at `INSPECTION`; nothing installed.
- **Tests:** none exist. Documentation validation: restored originals diffed against Git blobs (identical); Markdown links and anchors checked.
- **Decisions made:** amendments are appended to their original specifications; path references corrected to match existing filenames (no renames); Python 3.12, mypy strict, uv workspace, root `tests/`, Pydantic Settings approved.
- **Unresolved:** the "Still open" table above, and the open documentation issues in [KNOWN_CONSTRAINTS.md](KNOWN_CONSTRAINTS.md#open-documentation-issues).
- **Next action:** explicit user approval to start 8.1.
- **Read next session:** `CLAUDE.md`, this directory's `PROJECT_STATUS.md`, `ARCHITECTURE_SUMMARY.md`, `KNOWN_CONSTRAINTS.md`, `NEXT_STEPS.md`, then Plan 8.1 and 7.1 §22.
