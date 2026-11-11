# Next Steps

## Current position

- **Phase:** 8 — Memory Engine Implementation
- **Subphase:** 8.1 — Foundation and Project Setup (`VERIFIED`; commit `5a0d6e5` merged into `main` via PR #3, merge `6efd72d`)
- **Next approved action:** none. Phase 8.2 has **not started and is not approved**. Wait for the user.
- **Decision review:** [PHASE-8-2-ARCHITECTURE-DECISION-REVIEW.md](PHASE-8-2-ARCHITECTURE-DECISION-REVIEW.md) analyses all 15 open decisions, with a deep review of the Phase 8.2 blockers.

## Prerequisites before Phase 8.2

1. ~~User decides Decisions 1, 2, 4, 5 and 10~~ — **APPROVED** 2026-11-11 (recorded in [7.1 §23](../technical-decisions/01-baseline-technology-stack.md) and the Phase 8.2 amendment of [5.4](../data-models/phase-05-memory-engine-models.md)).
2. ~~User decides whether vector columns move to 8.7~~ — **APPROVED** 2026-11-11: 8.2 stores embedding metadata only; vector storage in 8.7 ([7.1 §23.5](../technical-decisions/01-baseline-technology-stack.md)).
3. ~~User decides outbox timing (Decision 9)~~ — **APPROVED** 2026-11-11: outbox in 8.3 ([7.1 §23.6](../technical-decisions/01-baseline-technology-stack.md)).
4. ~~Docker availability confirmed for PostgreSQL integration tests~~ — done 2026-11-11 (see `KNOWN_CONSTRAINTS.md`).
5. ~~The checkpoint correction, the decision review and the recorded approvals are merged~~ — done: PR #4, merge `ab50c48`.
6. User explicitly approves starting 8.2.

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

From the Memory Engine implementation-readiness review (2026-11-11). ⚑ = needs explicit approval (architecture, security, privacy or new infrastructure). Full analysis of each decision (options, trade-offs, dependencies, cost of delay, approval) is in the [Phase 8.2 architecture decision review](PHASE-8-2-ARCHITECTURE-DECISION-REVIEW.md) §4–5. The review also identifies specification gaps G1–G7, including undefined Atomic Memory lifecycle states (G1) and no stated language requirement (G6).

| # | Decision | Needed by | Recommendation |
|---|---|---|---|
| 1 | Code organization for Personal Memory vs Document Intelligence inside the package | 8.2 | **APPROVED** 2026-11-11: domain-first `personal/` and `documents/` (7.1 §23.1) |
| 2 | PostgreSQL driver; sync vs async database access | 8.2 | **APPROVED** 2026-11-11: psycopg 3 + synchronous SQLAlchemy 2.0 (7.1 §23.2) |
| 3 | Embedding model, dimension, similarity metric, index type | 8.7 | Timing **APPROVED** 2026-11-11 (vector storage in 8.7, metadata only in 8.2). Model still to be selected via evaluation before 8.7 |
| 4 | ⚑ Canonical vocabularies: memory relationship types (5.4.27 vs 6.3.8), supersession types (6.3.7), resolution outcomes (6.3) | 8.2, 8.6 | **APPROVED** 2026-11-11: four vocabularies plus Atomic Memory lifecycle states (5.4, Phase 8.2 Amendment) |
| 5 | Placement of Document Intelligence records (shared `memory` schema vs separate schema) | 8.2 | **APPROVED** 2026-11-11: `memory` schema, `pm_`/`doc_`/`me_` prefixes (7.1 §23.3) |
| 6 | ⚑ Document-to-memory authorization model (consent record, scope, expiry) | 8.4 document path, 8.12 | Per-request authorization record tied to user, document version and scope |
| 7 | ⚑ Sequence: run 8.12 before 8.11; 8.4's document-derived path after 8.12 | Plan order | Approve the reorder |
| 8 | ⚑ Local S3-compatible object storage for development and tests (new infrastructure) | 8.3 | Docker Compose S3-compatible service, development only |
| 9 | When to introduce Celery/RabbitMQ and the transactional outbox | 8.3 | **APPROVED** 2026-11-11: no outbox in 8.2; outbox table, publisher and Celery together in 8.3 (7.1 §23.6). Differs from the review's recommendation |
| 10 | Owner identity before an identity provider is chosen | 8.2 | **APPROVED** 2026-11-11: caller-supplied `OwnerScope`, opaque `owner_id` (7.1 §23.4) |
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
- **Objective:** Verify Phase 8.1 after merge, correct the checkpoint files, and review the 15 open decisions, with depth on the Phase 8.2 blockers.
- **Work completed:**
  - Verified commit `5a0d6e5` (31 files, no forbidden artifacts) and its merge into `main` via PR #3 (`6efd72d`).
  - Re-ran all checks.
  - Investigated the Windows mypy long-path failure (environmental; passes from a normal-length checkout).
  - Wrote the [decision review](PHASE-8-2-ARCHITECTURE-DECISION-REVIEW.md).
  - Corrected `PROJECT_STATUS`, `IMPLEMENTATION_STATE`, `NEXT_STEPS`, `TECHNOLOGY_DECISIONS` and `KNOWN_CONSTRAINTS`.
- **Files changed:** in this directory, 1 new file (the decision review) and updated context files; plus the approval records in `docs/technical-decisions/01-baseline-technology-stack.md`, `docs/data-models/phase-05-memory-engine-models.md`, `docs/data-models/Readme.md`, the Phase 8 Readme, plan 8.1 and plan 8.2, and `.claude/rules/coding-standards.md`. Uncommitted in the working tree of `feat/phase-8-1-foundation`, which is already merged, so landing these needs a new commit and pull request. No application code, dependencies or migrations changed.
- **Implementation status:** 8.1 `VERIFIED` and merged; 8.2–8.12 `NOT_STARTED`. **Phase 8.2 has not started.**
- **Tests and results:**
  - `uv sync --locked` → succeeded
  - `uv run pytest --cov` → 71 passed, 98% coverage
  - `uv run ruff check .` → clean; `uv run ruff format --check .` → clean
  - `uv run mypy` in this checkout → fails to load mypy's DLL (path length, reproduced)
  - fresh clone at a 109-character root → mypy strict clean (16 files), 71 passed
- **Decisions made:** the user **approved Decisions 1, 2, 4, 5 and 10** on 2026-11-11. They are recorded in 7.1 §23, the Phase 8.2 amendment of 5.4 (vocabularies and lifecycle states), the Phase 8 Readme §7.2, plan 8.2 §2.1 and a superseded-layout note in plan 8.1 §4.
- **Also approved:** deferring vector storage to 8.7, recorded in 7.1 §23.5, plan 8.2 §2.1, plan 8.7 §2.1 and the Phase 8 Readme §7.2.
- **Follow-up session (2026-11-11):** committed as PR #4 (`22cc9f1`). A later audit session merged PR #5 (status sync, long-path and redaction notes, ratio-label issue) into `main`; `main` was then merged into this branch, keeping this branch's text in conflicts and re-adding PR #5's notes. The owner then **approved Decision 9**: no outbox in 8.2; outbox table, publisher and Celery together in 8.3 (7.1 §23.6, plan 8.2 §2.1, Phase 8 Readme §7.2, coding standards; review §4 Decision 9 annotated). Open documentation issues 5 and 6 marked resolved by Decisions 5 and 1.
- **Unresolved:** embedding model selection (before 8.7); language requirement (G6); uv not on PATH on this machine; Decisions 6–8 and 11–15 per the review; ratio-label wording (`KNOWN_CONSTRAINTS.md` issue 9).
- **Docker:** Verified 2026-11-11: Docker Engine 29.9.3 (linux/amd64), Compose v5.5.1; a throwaway `pgvector/pgvector:pg17` container started, accepted connections (PostgreSQL 17.11), loaded `vector` 0.8.7 and ran a distance query, then was removed. Docker Desktop must be running.
- **Merged:** PR #4 into `main` as `ab50c48`.
- **Next action:** explicit owner approval to start Phase 8.2. All other prerequisites are met.
- **Read next session:** `CLAUDE.md`, this directory's `PROJECT_STATUS.md`, `ARCHITECTURE_SUMMARY.md`, `KNOWN_CONSTRAINTS.md`, `NEXT_STEPS.md`, the decision review, then plan 8.2 and the documents listed above.
