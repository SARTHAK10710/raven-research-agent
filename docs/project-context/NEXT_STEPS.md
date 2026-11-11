# Next Steps

## Current position

- **Phase:** 8 — Memory Engine Implementation
- **Subphase:** 8.2 — Database and Persistence: **approved 2026-11-11**, `IN_PROGRESS`. Steps 1–2 merged (PR #8), step 3 merged (PR #9, `b31a97e`). Step 4 (episodes, profiles, categories, memory embedding metadata) implemented and tested, uncommitted on `feat/phase-8-2-episodes-profiles` (branched from `main`). 8.1 `VERIFIED` and merged.
- **Next approved action:** continue 8.2 with step 5 after the owner reviews step 4. Do not start 8.3.
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
| 4 | Episodes (`pm_episode`, `pm_episode_membership`, `pm_episode_event`), profiles (`pm_profile`, `pm_profile_revision`, `pm_profile_memory`, `pm_profile_refresh`), `pm_memory_category`, `pm_memory_embedding` (metadata); migration `0004`. No consolidation-result table (5.4.23; approved) | Implemented and tested; uncommitted |
| 5 | Deletion operations, correction requests, candidate evaluation history, source processing events (5.4.24–5.4.26, 5.4.28) | Next |

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
- **Objective:** Phase 8.2 step 4: episodes, profiles, categories and memory embedding metadata. Branched from `main` @ `b31a97e` after PR #9 merged step 3.
- **Work completed:**
  - Vocabularies in the shared kernel: `EpisodeStatus`, `TemporalPrecision`, `ProfileType`, `ProfileStatus`, `RefreshTrigger`, `RefreshOutcome` (with `resulting_status()`), `MemoryCategory`, `EmbeddingPurpose`. `EmbeddingStatus` moved there from Document Intelligence, which re-exports it.
  - `personal/domain/derived.py`: `Episode`, `EpisodeMembership`, `EpisodeEvent`, `Profile`, `ProfileRevision`, `ProfileSupport`, `ProfileRefresh`, `CategoryAssignment`, `MemoryEmbedding`.
  - Ports and `infrastructure/persistence/personal/derived_{models,repositories}.py`: episodes (members, timeline with corrections), profiles (create, revisions, `apply_refresh`, history, `profiles_supported_by`), categories (assign, close, current/history, `memories_in`), memory embedding metadata.
  - Migration `0004_episodes_profiles`: 9 `pm_` tables, `me_guard_columns` triggers, partial unique indexes, and a deferrable profile ↔ current-revision foreign key.
- **Bug found by the tests and fixed:** `SET CONSTRAINTS ALL IMMEDIATE` lasts for the whole transaction, so a second profile created in the same unit of work failed. Each profile write now defers first and checks immediately at the end.
- **Decisions made:** the owner approved the step-4 vocabularies, no membership role, and no consolidation-result table until 8.9 defines a type (5.4 Phase 8.2 amendment §13).
- **Files changed:** see [IMPLEMENTATION_STATE.md](IMPLEMENTATION_STATE.md) §8.2. Uncommitted on `feat/phase-8-2-episodes-profiles`.
- **Implementation status:** 8.2 `IN_PROGRESS`; steps 1–3 merged, step 4 tested, step 5 remains.
- **Tests and results:** `uv sync --locked` ok; `uv run pytest --cov` → **340 passed** (252 unit, 88 integration against PostgreSQL 17 + pgvector), 96% coverage; database stopped → 88 skipped with a message; `ruff check`, `ruff format --check` clean; `mypy` strict clean (57 files).
- **Unresolved:** language requirement G6; object storage (8.3); embedding model (before 8.7); Decisions 6–8 and 12–15; ratio-label wording (issue 9); uv not on PATH on this machine.
- **Next action:** owner review, commit and pull request for step 4; then 8.2 step 5 (deletion, correction, evaluation and processing-history records), then the 8.2 acceptance review.
- **Read next session:** `CLAUDE.md`, `PROJECT_STATUS.md`, `KNOWN_CONSTRAINTS.md`, this file, plan 8.2 §12–14, 7.1 §23, 5.4 Decisions 5.4.24–5.4.26 and 5.4.28, 5.10 (deletion and lifecycle), 6.5.8–6.5.9, and `memory-engine/README.md`.
