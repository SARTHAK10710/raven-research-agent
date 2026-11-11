# Next Steps

## Current position

- **Phase:** 8 — Memory Engine Implementation
- **Subphase:** 8.3 — Ingestion Pipeline ([plan](../implementation-plans/Phase-08-memory-engine/03-ingestion-pipeline.md)): **`VERIFIED` 2026-11-12**: all five steps merged (PRs #16–#19, #21; `main` @ `1851f53`) ([PHASE-8-3-ACCEPTANCE-REVIEW.md](PHASE-8-3-ACCEPTANCE-REVIEW.md)). 8.1 and 8.2 `VERIFIED` and merged.
- **Next approved action:** 8.4 step 1 (extraction worker), starting with its open questions. 8.4 was approved on 2026-11-12.
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
| 1 | **Object storage:** the storage port, an in-memory fake, the SeaweedFS service in `docker-compose.yml`, a boto3 adapter with checksum verification and multipart-upload cleanup; the object-storage failure tests deferred from 8.2 (store unavailable, partial upload) (Decision 8, 7.1 §24.1) | **Settled 2026-11-11:** port in the shared kernel; `chrislusf/seaweedfs:4.51`; one engine bucket with owner checks; required settings. **Merged (PR #16)** |
| 2 | **Personal memory ingestion:** the request contract (`schema_version`), validation (schema, encoding, size, control characters), normalization (timestamps, speakers, conversation order), original content in object storage plus a `pm_memory_source` row, an idempotent ingestion operation, processing events, and recording remember/forget instructions (plan 8.3 §5, §7–9) | **Settled 2026-11-11:** extend `pm_memory_source` (migration `0007`); forget recorded, never extracted; 256 KiB text, 1,000 messages / 4 MiB per conversation; application dataclasses for the contract. **Merged (PR #17)** |
| 3 | **Document ingestion:** actual-format detection (PDF, DOCX, TXT), size limits, checksum, the original in object storage, registration of the document and version, a `doc_processing_operation`, the re-upload policy; no parsing (Decision 13; plan 8.3 §6) | **Settled 2026-11-11:** standard-library detection; 25 MiB limit; no malware scan (deferral recorded); caller decides new document vs new version. **Merged (PR #18)** |
| 4 | **Reliable handoff:** the `me_outbox` table written in the same transaction as each registration, a publisher, RabbitMQ in `docker-compose.yml`, Celery wiring; handoff messages to the document pipeline (8.12) and to extraction (8.4); recovery of failed publishing (7.1 §23.6; 7.4) | **Settled 2026-11-12** (7.1 §24.3): exchange `raven.memory`, two queues, no DLQ yet; 7.4 §7 envelope v1; Celery `send_task` with confirms; `queued` after the broker confirms; no handoff for forget; bounded retries then `failed`; `rabbitmq:4.3.7-alpine`; `celery`, `kombu`. **Merged (PR #19)** |
| 5 | **Observability and acceptance:** ingestion events and metrics (plan 8.3 §11), the remaining plan §12 tests, and an acceptance review against plan 8.3 §13 | **Settled 2026-11-12** (7.1 §24.4): metrics port with no-op default, OpenTelemetry later; owner id in logs only; unauthorized as scope mismatch (D1). **Merged (PR #21)**; 8.3 `VERIFIED`; review: [PHASE-8-3-ACCEPTANCE-REVIEW.md](PHASE-8-3-ACCEPTANCE-REVIEW.md) |

## Phase 8.4 steps (approved 2026-11-12, personal path)

Approved with 8.4 ([7.1 §25](../technical-decisions/01-baseline-technology-stack.md)). The document-derived path follows plan 8.12 (Decision 7).

| Step | Scope | Open questions to settle at the start of the step |
|---|---|---|
| 1 | **Extraction worker:** the Celery consumer for `memory.personal.extraction` (envelope validation, idempotency, Memory Source `queued` → `processing` → outcome), the English-language check, the spaCy dependency, the synthetic dataset scaffold | Task retry and failure policy (Celery retries vs a reprocessing record); which source states mark failure, deferral and completion; language detection method; how the spaCy model is installed (direct wheel); dataset schema |
| 2 | **Relevance gate** (6.2.2): `PROCESS` / `DEFER` / `REJECT` with reason codes; protection rules | Initial dimensions and weights (uncalibrated defaults); where a deferral is recorded; reason-code vocabulary |
| 3 | **Atomic fact extraction** (6.2.3): segmentation, speaker attribution, statement classification, negation, conditions, time and quantities | Fact representation inside the candidate (subject, predicate, object); pattern coverage; coreference scope |
| 4 | **Evaluation and classification** (6.2.4–6.2.5): independent importance and confidence; explicit, inferred or unresolved | Initial scoring rules and thresholds; method versioning |
| 5 | **Candidate generation** (6.2.6): validation, persistence with provenance and evaluation history, category assignment, handoff to resolution (8.6) | Where candidate categories live (no candidate category column exists); the resolution handoff (a new outbox kind and queue, or polling) |
| 6 | **Observability and acceptance:** extraction events and metrics, dataset evaluation, the acceptance review against plan 8.4 §16 (personal path) | Quality thresholds for the dataset evaluation |

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
| 7 | ⚑ Sequence: run 8.12 before 8.11; 8.4's document-derived path after 8.12 | Plan order | **APPROVED** 2026-11-12: personal path of 8.4 now, document path after 8.12, 8.11 last (7.1 §25.1) |
| 8 | ⚑ Local S3-compatible object storage for development and tests (new infrastructure) | 8.3 | **APPROVED** 2026-11-11: storage port, in-memory fake for unit tests, SeaweedFS in Docker Compose for integration tests and development, boto3 client; implemented in 8.3 (7.1 §24.1) |
| 9 | When to introduce Celery/RabbitMQ and the transactional outbox | 8.3 | **APPROVED** 2026-11-11: no outbox in 8.2; outbox table, publisher and Celery together in 8.3 (7.1 §23.6). Differs from the review's recommendation |
| 10 | Owner identity before an identity provider is chosen | 8.2 | **APPROVED** 2026-11-11: caller-supplied `OwnerScope`, opaque `owner_id` (7.1 §23.4) |
| 11 | ⚑ Shared public entities (5.4.13): population and privacy | 8.5 | **APPROVED** 2026-11-11: private only; `scope` column present, `shared` rejected by a check until a curation process is approved (7.1 §23.7) |
| 12 | Derived-profile ownership (Phase 2 component 3 vs Phase 6 / plan 8.9) | 8.9 | Consolidation (8.9) |
| 13 | Document parsing appears in both 6.2.1 and the document pipeline | 8.3, 8.12 | **APPROVED** 2026-11-11: the document pipeline owns parsing; ingestion validates, stores, registers and hands off (7.1 §24.2; 6.2 amendment) |
| 14 | spaCy pipeline; scoring thresholds and weights; evaluation datasets | 8.4–8.11 | **APPROVED** 2026-11-12: spaCy 3.8 + `en_core_web_sm` 3.8.0, English first; datasets per capability. Thresholds and weights still to calibrate (7.1 §25.3) |
| 15 | ⚑ Approve pypdf and python-docx | 8.12 | Evaluate at 8.12 start |

## Required documentation for 8.2

- [Plan 8.2](../implementation-plans/Phase-08-memory-engine/02-database-and-persistence.md)
- [5 overview](../data-models/phase-05-data-models-overview.md), [5.4 memory models +amendment](../data-models/phase-05-memory-engine-models.md), [5.8–5.10 +amendment](../data-models/phase-05-relationships-and-lifecycle.md)
- [7.2 +amendment](../technical-decisions/02-database-and-storage-architecture.md); [7.3](../technical-decisions/03-vector-search-and-embedding-infrastructure.md) §9

## Session Handoff

*Overwrite this section at the end of every session that changes the repository.*

- **Date:** 2026-11-12
- **Objective:** close Phase 8.3. Done: **8.3 is `VERIFIED`** on `main` @ `1851f53`.
- **Work completed this session (all merged):**
  - Step 4, reliable handoff: `me_outbox`, RabbitMQ `broker-test`, Celery publisher and outbox relay (PR #19, `db13113`; status sync PR #20, `4af8a92`).
  - Step 5, observability and the acceptance review: the `Metrics` port, `observe_ingestion`, relay handoff metrics and backlog gauges, the remaining plan §12 tests, and [PHASE-8-3-ACCEPTANCE-REVIEW.md](PHASE-8-3-ACCEPTANCE-REVIEW.md) ([PR #21](https://github.com/SARTHAK10710/raven-research-agent/pull/21), `1851f53`).
  - This docs change records 8.3 as `VERIFIED`.
  - Phase 8.4 approved (personal path) with Decision 7, G6 (English first) and Decision 14 (spaCy + `en_core_web_sm`), and its six steps recorded (7.1 §25; branch `docs/phase-8-4-approval`).
- **Decisions made (owner, 2026-11-12):**
  - step 4 is in 7.1 §24.3;
  - step 5 is in 7.1 §24.4;
  - deferral D1 (authentication tests move to the Entry layer) is accepted.
- **Verification on merged `main` @ `1851f53`:** `uv sync --locked` ok; ruff and format clean; mypy strict clean (91 files); `uv run pytest --cov` with all three services: 652 passed, 0 failed, 0 skipped, 97% coverage.
- **Implementation status:** 8.1, 8.2 and 8.3 `VERIFIED`; 8.4–8.12 `NOT_STARTED`.
- **Unresolved:**
  - no consumers until 8.4 and 8.12; the relay process and metrics export are not deployed (7.7 §20, 7.8);
  - no dead-letter queue or outbox cleanup; 8.10 deletion must remove a subject's outbox rows;
  - no encryption at rest in the development store; no malware scanning; test broker without TLS;
  - G6; Decision 6; embedding model; Decisions 7, 12, 14 and 15; ratio-label wording;
  - on this machine: uv not on PATH, Docker Desktop can take minutes to start, the SeaweedFS image once needed a re-pull, and Python defaults to cp1252 (script doc edits with UTF-8).
- **Next action:** 8.4 was approved on 2026-11-12 (personal path; see 7.1 §25). Start step 1 (extraction worker) with its open questions.
- **Read next session:** `CLAUDE.md`, `PROJECT_STATUS.md`, `KNOWN_CONSTRAINTS.md`, this file, plan 8.4 with its 2026-11-12 amendment, 7.1 §25, algorithm 6.2 (`docs/algorithms/memory/01-memory-ingestion-extraction.md`) §4–§8, 7.5 §3.1, `domain/handoff.py`, `personal/domain/records.py` (`MemoryCandidate`) and `personal/domain/lifecycle.py` (`CandidateEvaluation`).
