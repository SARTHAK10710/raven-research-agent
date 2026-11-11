# Next Steps

## Current position

- **Phase:** 8 — Memory Engine Implementation
- **Subphase:** 8.2 — Database and Persistence: **`VERIFIED` 2026-11-11** and merged (`main` @ `423b6fd`; [acceptance review](PHASE-8-2-ACCEPTANCE-REVIEW.md)). 8.1 `VERIFIED` and merged.
- **Next approved action:** none. Phase 8.3 (Ingestion Pipeline, [plan](../implementation-plans/Phase-08-memory-engine/03-ingestion-pipeline.md)) needs the owner's explicit approval, and Decision 8 (local object storage ⚑) must be decided for it. Do not start 8.3 without approval.
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
| 1 | Dependencies, Docker Compose test database, shared kernel (`OwnerScope`, ids, vocabularies), engine and unit of work, migration `0001` (`pm_memory_source`, `pm_memory_candidate`, `pm_atomic_memory`, `pm_atomic_memory_revision`, `pm_provenance`), repositories, tests | Merged (PR #8) |
| 2 | Document Intelligence: `doc_document`, `doc_document_version`, `doc_extracted_representation`, `doc_chunk` (+ `simple` full-text index), `doc_chunk_location`, `doc_embedding` (metadata), `doc_processing_operation`; `pm_document_evidence_ref` and provenance citing it; migration `0002`; column-guard triggers; repositories and a document unit of work | Merged (PR #8) |
| 3 | Entities and relationships: `pm_entity` (private only), `pm_entity_alias`, `pm_entity_mention`, `pm_entity_resolution` (append-only history), `pm_entity_relationship`, `pm_memory_relationship`, `pm_memory_entity`; migration `0003`; entity, mention and relationship repositories | Merged (PR #9) |
| 4 | Episodes (`pm_episode`, `pm_episode_membership`, `pm_episode_event`), profiles (`pm_profile`, `pm_profile_revision`, `pm_profile_memory`, `pm_profile_refresh`), `pm_memory_category`, `pm_memory_embedding` (metadata); migration `0004`. No consolidation-result table (5.4.23; approved) | Merged (PR #10) |
| 5 | Source processing events, candidate evaluation history, correction requests, deletion operations and ledger (5.4.24–5.4.26, 5.4.28); migration `0005` | Merged (PR #11) |
| — | 8.2 acceptance review against plan 8.2 §14; fixes: migration `0006` (episode version), race, commit-failure and migration-failure tests | Merged (PR #11); A4 passed on `main`: **8.2 `VERIFIED`** ([review](PHASE-8-2-ACCEPTANCE-REVIEW.md)) |

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
| 11 | ⚑ Shared public entities (5.4.13): population and privacy | 8.5 | **APPROVED** 2026-11-11: private only; `scope` column present, `shared` rejected by a check until a curation process is approved (7.1 §23.7) |
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
- **Objective:** finish Phase 8.2: step 5, the acceptance review and its fixes, the merges, and verification on `main` (A4).
- **Work completed:**
  - Step 5 (`42b35c3`): processing events, candidate evaluations, correction requests, deletion operations and ledger; migration `0005`.
  - Acceptance review ([PHASE-8-2-ACCEPTANCE-REVIEW.md](PHASE-8-2-ACCEPTANCE-REVIEW.md)) and fixes (`1b58b77`):
    - A1: migration `0006_episode_version`, plus `EpisodeRepository.update(…, expected_version=)`;
    - A2: tests for racing connections, a failed commit and a failing migration;
    - A3: owner-accepted deferrals recorded in `KNOWN_CONSTRAINTS.md`;
    - `CLAUDE.md` "Current phase" corrected.
  - At the owner's request, merged PR #10 (`977c3b7`) and then PR #11 (`423b6fd`), and ran A4 on `main`.
  - This branch (`docs/phase-8-2-verified`, from `main`) records the `VERIFIED` status; uncommitted.
- **Bugs found by the tests and fixed this session:**
  - JSONB `None` is stored as JSON `null`, so the correction purge now uses `null()`;
  - a test depended on the order of two operations requested at the same instant;
  - concurrent episode edits could overwrite each other (A1).
- **Decisions made:** step-5 vocabularies and designs (5.4 amendment §14); the A3 deferrals (object-storage failure tests to 8.3, database roles to deployment).
- **Implementation status:** 8.1 and 8.2 `VERIFIED` and merged; 8.3–8.12 `NOT_STARTED`.
- **Tests and results (A4, `main` @ `423b6fd`):** `uv sync --locked` ok; `ruff check`, `ruff format --check` clean; `mypy` strict clean (63 files); `uv run pytest --cov` → **412 passed** (300 unit, 112 integration against PostgreSQL 17 + pgvector), 96% coverage, plus 3 further green runs; database stopped → 112 skipped.
- **Unresolved:** language requirement G6; Decision 8 (object storage, needed by 8.3); embedding model (before 8.7); Decisions 6, 7 and 12–15; ratio-label wording (issue 9); uv not on PATH on this machine; Docker Desktop on this machine can take several minutes to start.
- **Next action:** commit this status update (with approval); then the owner decides Decision 8 and whether to approve Phase 8.3.
- **Read next session:** `CLAUDE.md`, `PROJECT_STATUS.md`, `KNOWN_CONSTRAINTS.md`, this file, plan 8.3 ([03-ingestion-pipeline.md](../implementation-plans/Phase-08-memory-engine/03-ingestion-pipeline.md)), the [decision review](PHASE-8-2-ARCHITECTURE-DECISION-REVIEW.md) §4 (Decision 8), 7.1 §23.6 (outbox in 8.3), and `memory-engine/README.md`.
