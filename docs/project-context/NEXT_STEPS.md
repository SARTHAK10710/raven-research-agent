# Next Steps

## Current position

- **Phase:** 8 — Memory Engine Implementation
- **Subphase:** 8.2 — Database and Persistence: **approved 2026-11-11**, `IN_PROGRESS`. Step 1 committed (`d2346b6`, PR #7). Step 2 (Document Intelligence persistence) implemented and tested, uncommitted on `feat/phase-8-2-document-persistence`. 8.1 `VERIFIED` and merged.
- **Next approved action:** continue 8.2 with step 3 after the owner reviews step 2. Do not start 8.3.
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
| 1 | Dependencies, Docker Compose test database, shared kernel (`OwnerScope`, ids, vocabularies), engine and unit of work, migration `0001` (`pm_memory_source`, `pm_memory_candidate`, `pm_atomic_memory`, `pm_atomic_memory_revision`, `pm_provenance`), repositories, tests | Committed `d2346b6` (PR #7) |
| 2 | Document Intelligence: `doc_document`, `doc_document_version`, `doc_extracted_representation`, `doc_chunk` (+ `simple` full-text index), `doc_chunk_location`, `doc_embedding` (metadata), `doc_processing_operation`; `pm_document_evidence_ref` and provenance citing it; migration `0002`; column-guard triggers; repositories and a document unit of work | Implemented and tested; uncommitted |
| 3+ | Entities, aliases, mentions, entity and memory relationships, Memory–Entity associations, episodes, profiles, categories, memory embedding metadata, deletion records (plan 8.2 §3.3) | Next |

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
- **Objective:** Phase 8.2 step 2: Document Intelligence persistence and the document-evidence path into Personal Memory. (Step 1 was committed as `d2346b6`, PR #7.)
- **Work completed:**
  - `documents/domain` (records with invariants, vocabularies) and `documents/application/ports.py`; `DocumentEvidenceRef` and `DocumentEvidenceStatus` on the Personal Memory side; `ProvenanceRecord.document_evidence_id`.
  - `infrastructure/persistence/documents/` models and repositories: registration, versioning with a current-version pointer checked optimistically, representations, chunks with ordered locations, embedding metadata, idempotent processing operations, deletion-dependency discovery, a deletion guard (`DeletionInProgressError`).
  - Personal side: `SqlAlchemyDocumentEvidenceRepository` (add, list, memories citing a document, `mark_source_deleted`); provenance validates document evidence.
  - Shared unit-of-work base; separate Personal and Document units of work.
  - Migration `0002_document_intelligence`: 7 `doc_` tables, `pm_document_evidence_ref`, `pm_provenance.document_evidence_id`, `simple` full-text column and GIN index, `me_guard_columns` triggers (status-only updates; append-only content).
- **Bugs found by the tests and fixed:** (1) the active-evidence check used `=`, which is NULL, and therefore passing, when a link is missing; it now uses `IS NOT DISTINCT FROM`. (2) Chunk locations came back in random-ID order; they now carry an `ordinal`.
- **Decisions made:** the owner approved the document, version, extraction, embedding and operation vocabularies and the `simple` full-text configuration (5.4 Document Intelligence amendment §14). Implementation detail recorded in 7.1 §23.3: evidence keeps opaque `*_ref` copies alongside the foreign-key columns, so `RESTRICT` and "keep the identifiers" can both hold.
- **Files changed:** see [IMPLEMENTATION_STATE.md](IMPLEMENTATION_STATE.md) §8.2. Uncommitted on `feat/phase-8-2-document-persistence` (stacked on step 1).
- **Implementation status:** 8.2 `IN_PROGRESS`. Plan 8.2 §14 criteria 2–11 are now met for the records built so far; 1 and 12 wait for the remaining 8.2 models (step 3+).
- **Tests and results:** `uv sync --locked` ok; `uv run pytest --cov` → **225 passed** (169 unit, 56 integration against PostgreSQL 17 + pgvector), 97% coverage; database stopped → 56 integration tests skipped with a message; `ruff check`, `ruff format --check` clean; `mypy` strict clean (47 files).
- **Unresolved:** language requirement G6 (the `simple` configuration is a placeholder); object storage (8.3), so object keys are not yet backed by stored files; embedding model (before 8.7); Decisions 6–8 and 11–15; ratio-label wording (issue 9); uv not on PATH on this machine.
- **Next action:** owner review and commit of step 2; then 8.2 step 3 (entities, relationships, episodes, profiles, categories, memory embedding metadata, deletion records).
- **Read next session:** `CLAUDE.md`, `PROJECT_STATUS.md`, `KNOWN_CONSTRAINTS.md`, this file, plan 8.2 §3.3 and §12, 7.1 §23, the 5.4 sections for entities, relationships, episodes and profiles plus the Phase 8.2 amendment, and `memory-engine/README.md`.
