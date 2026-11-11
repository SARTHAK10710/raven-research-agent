# Next Steps

## Current position

- **Phase:** 8 — Memory Engine Implementation
- **Subphase:** 8.3 — Ingestion Pipeline ([plan](../implementation-plans/Phase-08-memory-engine/03-ingestion-pipeline.md)): **approved 2026-11-11**, `IN_PROGRESS`. Step 1 (object storage) is implemented and tested, uncommitted on `feat/phase-8-3-object-storage`. 8.1 and 8.2 `VERIFIED` and merged.
- **Next approved action:** owner review of step 1; step 2 starts when the owner says so, beginning with its open questions. Do not start 8.4.
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

## Phase 8.3 steps (proposed 2026-11-11)

Ordered so each step builds on the previous one. All of them are persistence-backed application services; plan 8.3 defines no HTTP endpoints, and the Entry layer stays out of Phase 8 scope.

| Step | Scope | Open questions to settle at the start of the step |
|---|---|---|
| 1 | **Object storage:** the storage port, an in-memory fake, the SeaweedFS service in `docker-compose.yml`, a boto3 adapter with checksum verification and multipart-upload cleanup; the object-storage failure tests deferred from 8.2 (store unavailable, partial upload) (Decision 8, 7.1 §24.1) | **Settled 2026-11-11:** port in the shared kernel; `chrislusf/seaweedfs:4.51`; one engine bucket with owner checks; required settings. **Implemented and tested; uncommitted** |
| 2 | **Personal memory ingestion:** the request contract (`schema_version`), validation (schema, encoding, size, control characters), normalization (timestamps, speakers, conversation order), original content in object storage plus a `pm_memory_source` row, an idempotent ingestion operation, processing events, and recording remember/forget instructions (plan 8.3 §5, §7–9) | Where the ingestion operation and idempotency live (a `pm_` table or a shared `me_operation`); how `instruction_type` is stored; forget handling until 8.10 exists; text size limits |
| 3 | **Document ingestion:** actual-format detection (PDF, DOCX, TXT), size limits, checksum, the original in object storage, registration of the document and version, a `doc_processing_operation`, the re-upload policy; no parsing (Decision 13; plan 8.3 §6) | Detection approach (standard-library signature checks or a library); file-size limit (deferred, 7.6 §18); malware scanning (no approved tool); new document vs new version on re-upload |
| 4 | **Reliable handoff:** the `me_outbox` table written in the same transaction as each registration, a publisher, RabbitMQ in `docker-compose.yml`, Celery wiring; handoff messages to the document pipeline (8.12) and to extraction (8.4); recovery of failed publishing (7.1 §23.6; 7.4) | Queue names and routing keys (deferred, 7.4 §22); message contract and versioning; Celery `send_task` or plain kombu for publishing; RabbitMQ image tag |
| 5 | **Observability and acceptance:** ingestion events and metrics (plan 8.3 §11), the remaining plan §12 tests, and an acceptance review against plan 8.3 §13 | — |

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
| 8 | ⚑ Local S3-compatible object storage for development and tests (new infrastructure) | 8.3 | **APPROVED** 2026-11-11: storage port, in-memory fake for unit tests, SeaweedFS in Docker Compose for integration tests and development, boto3 client; implemented in 8.3 (7.1 §24.1) |
| 9 | When to introduce Celery/RabbitMQ and the transactional outbox | 8.3 | **APPROVED** 2026-11-11: no outbox in 8.2; outbox table, publisher and Celery together in 8.3 (7.1 §23.6). Differs from the review's recommendation |
| 10 | Owner identity before an identity provider is chosen | 8.2 | **APPROVED** 2026-11-11: caller-supplied `OwnerScope`, opaque `owner_id` (7.1 §23.4) |
| 11 | ⚑ Shared public entities (5.4.13): population and privacy | 8.5 | **APPROVED** 2026-11-11: private only; `scope` column present, `shared` rejected by a check until a curation process is approved (7.1 §23.7) |
| 12 | Derived-profile ownership (Phase 2 component 3 vs Phase 6 / plan 8.9) | 8.9 | Consolidation (8.9) |
| 13 | Document parsing appears in both 6.2.1 and the document pipeline | 8.3, 8.12 | **APPROVED** 2026-11-11: the document pipeline owns parsing; ingestion validates, stores, registers and hands off (7.1 §24.2; 6.2 amendment) |
| 14 | spaCy pipeline; scoring thresholds and weights; evaluation datasets | 8.4–8.11 | Synthetic versioned datasets built with each subphase |
| 15 | ⚑ Approve pypdf and python-docx | 8.12 | Evaluate at 8.12 start |

## Required documentation for 8.2

- [Plan 8.2](../implementation-plans/Phase-08-memory-engine/02-database-and-persistence.md)
- [5 overview](../data-models/phase-05-data-models-overview.md), [5.4 memory models +amendment](../data-models/phase-05-memory-engine-models.md), [5.8–5.10 +amendment](../data-models/phase-05-relationships-and-lifecycle.md)
- [7.2 +amendment](../technical-decisions/02-database-and-storage-architecture.md); [7.3](../technical-decisions/03-vector-search-and-embedding-infrastructure.md) §9

## Session Handoff

*Overwrite this section at the end of every session that changes the repository.*

- **Date:** 2026-11-11
- **Objective:** Phase 8.3 step 1, object storage. Branch `feat/phase-8-3-object-storage` from `main` @ `ea12c7a`; uncommitted.
- **Work completed:**
  - port and key rules in the shared kernel (`domain/object_storage.py`): opaque owner-partitioned keys, owner check on every call;
  - `InMemoryObjectStorage` fake and `S3ObjectStorage` (boto3), which streams with a SHA-256 and size check, re-checks the checksum on read, aborts failed multipart uploads, and offers `abort_incomplete_uploads`;
  - `ObjectStorageError` and `ObjectIntegrityError`; required `ObjectStorageSettings`;
  - SeaweedFS 4.51 as `object-storage-test` (`127.0.0.1:58333`, test-only keys in `docker/seaweedfs/s3.json`).
  - A smoke check confirmed that SeaweedFS supports metadata, multipart uploads, listing and aborting uploads, and 404/`NoSuchKey`.
- **Decisions made (owner):**
  - the port lives in the shared kernel; 7.1 §24.1 is corrected, since application code may not import infrastructure;
  - image 4.51;
  - one engine bucket, never created by the application;
  - required settings.
- **Tests and results:**
  - `uv sync --locked` ok; ruff and format clean; mypy strict clean (69 files);
  - `uv run pytest --cov`: **453 passed** (333 unit, 120 integration against PostgreSQL and SeaweedFS), 97% coverage, 3 green runs;
  - services stopped: 119 skipped, and the unreachable-store test passes without services.
- **Implementation status:** 8.3 `IN_PROGRESS`; step 1 tested; steps 2–5 to do.
- **Unresolved:**
  - for later steps: queue topology, file-size limits, malware scanning, the ingestion-operation table and forget handling;
  - no encryption at rest in the development store (production concern; 7.1 §8);
  - G6; Decision 6; embedding model; Decisions 7, 12, 14 and 15; ratio-label wording;
  - on this machine: uv not on PATH, and Docker Desktop can take minutes to start.
- **Next action:** owner review; commit and PR for step 1 (with approval); then step 2 (personal memory ingestion), starting with its open questions.
- **Read next session:** `CLAUDE.md`, `PROJECT_STATUS.md`, `KNOWN_CONSTRAINTS.md`, this file, plan 8.3 §5 and §7–9, 6.2.1 (text and conversation inputs), 5.4.1 and 5.4.28, 7.1 §24, 7.2 §10–11, `domain/object_storage.py`, and `memory-engine/README.md`.
- **Earlier this session (all merged):**
  - Phase 8.2 completed and `VERIFIED` (PRs #10, #11, #12; `main` @ `c936fe3`): 412 tests passed on `main`.
  - Decision 8, local object storage: SeaweedFS and boto3 (PR #13).
  - Decision 13, document parsing ownership: the document pipeline parses (PR #14).
  - Phase 8.3 approved, with the five-step breakdown (PR #15).
