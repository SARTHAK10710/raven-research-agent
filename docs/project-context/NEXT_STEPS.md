# Next Steps

## Current position

- **Phase:** 8 — Memory Engine Implementation
- **Subphase:** 8.2 — Database and Persistence: **approved 2026-11-11**, `IN_PROGRESS`. Step 1 (core Personal Memory persistence) implemented and tested, uncommitted on `feat/phase-8-2-persistence-foundation`. 8.1 `VERIFIED` and merged.
- **Next approved action:** continue 8.2 with step 2 (Document Intelligence tables) after the owner reviews step 1. Do not start 8.3.
- **Decision review:** [PHASE-8-2-ARCHITECTURE-DECISION-REVIEW.md](PHASE-8-2-ARCHITECTURE-DECISION-REVIEW.md) analyses all 15 open decisions, with a deep review of the Phase 8.2 blockers.

## Prerequisites before Phase 8.2

1. ~~User decides Decisions 1, 2, 4, 5 and 10~~ — **APPROVED** 2026-11-11 (recorded in [7.1 §23](../technical-decisions/01-baseline-technology-stack.md) and the Phase 8.2 amendment of [5.4](../data-models/phase-05-memory-engine-models.md)).
2. ~~User decides whether vector columns move to 8.7~~ — **APPROVED** 2026-11-11: 8.2 stores embedding metadata only; vector storage in 8.7 ([7.1 §23.5](../technical-decisions/01-baseline-technology-stack.md)).
3. ~~User decides outbox timing (Decision 9)~~ — **APPROVED** 2026-11-11: outbox in 8.3 ([7.1 §23.6](../technical-decisions/01-baseline-technology-stack.md)).
4. ~~Docker availability confirmed for PostgreSQL integration tests~~ — done 2026-11-11 (see `KNOWN_CONSTRAINTS.md`).
5. ~~The checkpoint correction, the decision review and the recorded approvals are merged~~ — done: PR #4, merge `ab50c48`.
6. ~~User explicitly approves starting 8.2~~ — **APPROVED** 2026-11-11.

## Phase 8.2 steps

| Step | Scope | Status |
|---|---|---|
| 1 | Dependencies, Docker Compose test database, shared kernel (`OwnerScope`, ids, vocabularies), engine and unit of work, migration `0001` (`pm_memory_source`, `pm_memory_candidate`, `pm_atomic_memory`, `pm_atomic_memory_revision`, `pm_provenance`), repositories, tests | Implemented and tested; uncommitted |
| 2 | Document Intelligence: `doc_document`, `doc_document_version`, `doc_extracted_representation`, `doc_chunk`, `doc_chunk_location`, `doc_embedding` (metadata), `doc_processing_operation`; object references; `pm_document_evidence_ref` (7.1 §23.3) | Next |
| 3+ | Entities, aliases, mentions, entity and memory relationships, Memory–Entity associations, episodes, profiles, categories, memory embedding metadata, deletion records (plan 8.2 §3.3) | Not started |

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
- **Objective:** Phase 8.2 (approved 2026-11-11), step 1: persistence foundation and core Personal Memory tables.
- **Work completed:**
  - Dependencies `sqlalchemy` 2.1.8, `alembic` 1.20.1, `psycopg[binary]` 3.3.8 (7.1 §23.2); `docker-compose.yml` with a dev/test-only `pgvector/pgvector:pg17` service on `127.0.0.1:55432`.
  - Shared kernel: `domain/identifiers.py` (`OwnerScope`, `new_id`), `domain/vocabulary.py` (all approved vocabularies).
  - `personal/domain/records.py` (frozen dataclasses with invariants) and `personal/application/ports.py` (repository protocols, unit of work).
  - `infrastructure/persistence/`: engine (pooling, `READ COMMITTED`, `hide_parameters`), error translation, unit of work, `pm_` models and repositories.
  - Alembic environment and migration `0001_personal_memory_core`: owner-scoped composite foreign keys with `RESTRICT`, vocabulary check constraints, append-only triggers on revisions and provenance.
  - New errors `RecordNotFoundError`, `ConcurrencyConflictError`; pool settings in `DatabaseSettings`.
- **Bug found by the tests and fixed:** Alembic applied the naming convention to the migration's explicit check-constraint names (doubled, one truncated with a hash). Fixed with `op.f()`; a new test compares deployed constraint names with the models.
- **Decisions made:** the owner approved the Memory Source processing states (5.4 amendment §11). `me_operation` deferred until a consumer defines it (7.1 §23.6 note); step 1 creates no `me_` table.
- **Files changed:** see [IMPLEMENTATION_STATE.md](IMPLEMENTATION_STATE.md) §8.2. Uncommitted on `feat/phase-8-2-persistence-foundation`.
- **Implementation status:** 8.2 `IN_PROGRESS` (step 1 tested). 8.2 acceptance criteria 2, 7, 8, 9 and 10 are met for Personal Memory core records only; criteria 3–6 and 11 need step 2.
- **Tests and results:** `uv sync --locked` ok; `uv run pytest --cov` → **162 passed** (136 unit, 26 integration against PostgreSQL 17 + pgvector), 98% coverage; with the database stopped, the 26 integration tests skip with a message; `ruff check`, `ruff format --check` clean; `mypy` strict clean (36 files).
- **Unresolved:** embedding model (before 8.7); language requirement (G6); Decisions 6–8 and 11–15; ratio-label wording (issue 9); `content_ref` stays optional until object storage (8.3); uv not on PATH on this machine.
- **Next action:** owner review and commit of step 1; then 8.2 step 2 (Document Intelligence tables).
- **Read next session:** `CLAUDE.md`, `PROJECT_STATUS.md`, `KNOWN_CONSTRAINTS.md`, this file, plan 8.2, 7.1 §23, the 5.4 Document Intelligence amendment (§3) and Phase 8.2 amendment, and `memory-engine/README.md`.
