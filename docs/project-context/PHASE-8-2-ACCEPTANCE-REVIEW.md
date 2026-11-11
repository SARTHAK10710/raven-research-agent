# Phase 8.2 Acceptance Review

**Date:** 2026-11-11. **Reviewed:** branch `feat/phase-8-2-deletion-corrections-history` @ `42b35c3`. That is `main` (`b31a97e`, steps 1–3) plus step 4 ([PR #10](https://github.com/SARTHAK10710/raven-research-agent/pull/10)) and step 5 ([PR #11](https://github.com/SARTHAK10710/raven-research-agent/pull/11)); neither PR was merged when this review ran, so the checks must be repeated on `main` after the merges.

**Against:** [plan 8.2](../implementation-plans/Phase-08-memory-engine/02-database-and-persistence.md) §13 (testing requirements) and §14 (acceptance criteria); [5.4](../data-models/phase-05-memory-engine-models.md) (Decisions 5.4.1–5.4.34, Document Intelligence amendment, Phase 8.2 amendment); [7.1 §23](../technical-decisions/01-baseline-technology-stack.md); [7.2](../technical-decisions/02-database-and-storage-architecture.md) §3, §7, §9, §15, §17.

## Verdict

**Not yet `VERIFIED`** when first run. *(Update: A1–A4 have since been resolved, and 8.2 is `VERIFIED` as of 2026-11-11 on `main` @ `423b6fd`. See section 6.)* At first run, criteria 2–7, 9 and 11 were met. Criteria 1, 8 and 10 are partly met, and criterion 12 is met only for the tests that exist. Four items stand between 8.2 and `VERIFIED` (section 4): one design gap that needs a migration (A1), missing failure tests (A2), two deferrals that need the owner's acceptance (A3), and the re-run on merged `main` (A4).

## 1. Checks run

| Command | Result |
|---|---|
| `uv sync --locked` | ok |
| `uv run ruff check .`, `uv run ruff format --check .` | clean (132 files) |
| `uv run mypy` | strict, no issues in 62 files |
| `uv run pytest --cov` (PostgreSQL 17 + pgvector via Docker Compose) | **406 passed** (296 unit, 110 integration), 96% line+branch coverage |
| `uv run pytest -m integration` / `-m "not integration"` | 110 passed / 296 passed |

## 2. Acceptance criteria (plan 8.2 §14)

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Database foundation matches the approved Phase 5 and Phase 7 architecture | **Partly met** | Every 5.4 record has a table (section 3) except the Memory Consolidation Result, deferred to 8.9 with approval. All Document Intelligence records (amendment §3.1–3.7) exist. Schema, prefixes, `owner_id`, `RESTRICT` foreign keys, metadata-only embeddings and no outbox follow 7.1 §23. Gaps: A1 (no version check on episode edits; 7.2 §7 and 7.1 §23.2) and A3b (no least-privilege database roles; 7.2 §3, §17) |
| 2 | Personal memory persistence works with the approved models | **Met** | `test_personal_repositories.py`, `test_entity_repositories.py`, `test_derived_repositories.py`, `test_lifecycle_repositories.py` |
| 3 | Document identity and version persistence work | **Met** | `test_same_filename_creates_distinct_documents`, `test_new_version_becomes_current_and_history_is_kept`, `test_stale_version_update_is_rejected_and_writes_nothing` |
| 4 | Original document objects can be referenced securely | **Met (references only)** | Opaque, owner-partitioned object keys (`DocumentVersion.object_key_for`). Storing objects is 8.3 |
| 5 | Extracted content and chunk metadata can be persisted | **Met** | `test_representation_round_trip`, `test_chunks_keep_order_provenance_and_locations`, `test_a_chunk_never_mixes_versions`, `test_a_failed_extraction_records_failure_and_cannot_be_chunked` |
| 6 | Document and memory embeddings remain logically separate | **Met** | Separate tables (`doc_embedding`, `pm_memory_embedding`); `test_only_the_evidence_path_crosses_domains`; no vectors before 8.7 (7.1 §23.5) |
| 7 | User ownership is enforced | **Met** | Composite `(id, owner_id)` foreign keys on every child table (`test_foreign_keys_never_cascade_and_every_child_has_an_owner_key`); owner filters in SQL; cross-owner tests in every integration module, including `test_database_rejects_a_cross_owner_reference_even_without_the_repository` |
| 8 | Transactions and concurrency controls are tested | **Partly met** | Rollback (`test_failed_unit_of_work_rolls_back_everything`) and stale-write rejection (memories, versions, mentions, profiles, operations, sources, candidates, corrections, deletion ledger) are tested. All tests run in one connection, so no test has two transactions racing (A2). Episode edits can be lost (A1) |
| 9 | Migrations execute successfully | **Met** | `test_upgrade_downgrade_upgrade_round_trip`, `test_downgrade_to_step_one_keeps_personal_memory_intact`, `test_migrated_schema_matches_the_orm_models`, `test_deployed_constraint_names_equal_the_model_names` |
| 10 | Failure and recovery behavior is tested | **Partly met** | Tested: database unreachable (`test_connection_errors_become_persistence_errors`, plus the integration skip), duplicate key, rollback, failed extraction, retry, idempotency, stale worker, writes after deletion is requested. Not tested: commit failure, migration failure, two-transaction conflict (A2); object-storage failures wait for 8.3 (A3a) |
| 11 | Deletion dependencies can be identified | **Met** | `DocumentRepository.dependencies`, `dependent_memory_ids`, `profiles_supported_by`, `episodes_of_memory`, `memories_of_entity`, `open_for_memory`, `DeletionRepository.operations_for`; `test_deletion_dependencies_are_discoverable`; a unit test ties deletion target kinds to every `pm_` table |
| 12 | All required tests pass | **Met for existing tests** | 406 passed. The §13 list is not fully covered (section 5) |

## 3. Phase 5.4 records → tables

| Decision(s) | Record | Table(s) | Note |
|---|---|---|---|
| 5.4.1 | Memory Source | `pm_memory_source` | `content_ref` optional until object storage (8.3); recorded deviation |
| 5.4.2–5.4.3, 5.4.25 | Memory Candidate, evaluation history | `pm_memory_candidate`, `pm_candidate_evaluation` | |
| 5.4.4–5.4.7, 5.4.10–5.4.11 | Atomic Memory and revisions | `pm_atomic_memory`, `pm_atomic_memory_revision` | |
| 5.4.8, 5.4.12–5.4.14, 5.4.33–5.4.34 | Entity, alias, mention, resolution history | `pm_entity`, `pm_entity_alias`, `pm_entity_mention`, `pm_entity_resolution`, `pm_memory_entity` | Private entities only (Decision 11) |
| 5.4.15 | Entity Relationship | `pm_entity_relationship` | |
| 5.4.27 | Memory Relationship | `pm_memory_relationship` | |
| 5.4.16, 5.4.29–5.4.30 | Episode, membership, timeline | `pm_episode`, `pm_episode_membership`, `pm_episode_event` | A1 |
| 5.4.17, 5.4.31–5.4.32 | Derived Profile, associations, refresh history | `pm_profile`, `pm_profile_revision`, `pm_profile_memory`, `pm_profile_refresh` | |
| 5.4.18 | Provenance Record | `pm_provenance`, `pm_document_evidence_ref` | |
| 5.4.19–5.4.21 | Embedding metadata | `pm_memory_embedding` | Vectors in 8.7 |
| 5.4.9, 5.4.22 | Category assignment (multi-label) | `pm_memory_category` | |
| 5.4.23 | Consolidation Result | — | Deferred to 8.9 (approved, amendment §13) |
| 5.4.24 | Deletion Operation | `pm_deletion_operation`, `pm_deletion_target` | |
| 5.4.26 | Correction Request | `pm_correction_request`, `pm_correction_memory` | |
| 5.4.28 | Source Processing Event | `pm_source_processing_event` | |

## 4. Items before `VERIFIED`

**A1 — Episode edits can overwrite each other (design gap, needs a migration).** `EpisodeRepository.update` replaces title, summary and boundaries, but its only guard is the expected status. Two writers that read the same `active` episode both succeed, and the second silently overwrites the first. 7.2 §7 says "Do not silently overwrite concurrent updates", and 7.1 §23.2 asks for a version column on mutable rows. Every other repository that replaces content guards it: memories and profiles by revision number, versions by the current-version reference, and all status-only rows by expected status. **Proposed fix:** add a `version` column to `pm_episode` (migration `0006`), make `update` take `expected_version`, and add a test.

**A2 — Missing failure and concurrency tests (no design change).**
- Two transactions on separate connections updating the same row: one wins, and the other gets `ConcurrencyConflictError`. Today's conflict tests are sequential in one connection.
- A unit of work whose commit fails is rolled back and reports the failure (already listed as a known limitation).
- A failing migration leaves the schema at the previous revision.

**A3 — Deferrals that need the owner's acceptance.**
- **a. Object-storage failure tests** (plan §13: object storage unavailable, partial object upload). No object storage exists until 8.3 (Decision 8 is still open), so they move to 8.3.
- **b. Least-privilege database roles** (7.2 §3, §17; 7.1 §23.3 "written only by the Memory Engine role"). The migrations create no roles or grants, and tests use one database user. Plan 8.2 does not mention roles. **Proposed:** defer to the first deployment environment (7.8) and record it as a known constraint, rather than create roles in 8.2.

**A4 — Repeat on `main`.** Merge PR #10, then PR #11, and re-run the section 1 checks on `main`.

## 5. Plan 8.2 §13 testing requirements

| Requirement | Covered by |
|---|---|
| Model creation, constraints, foreign keys, unique constraints | Constraint tests in every integration module; `test_migrated_schema_matches_the_orm_models` |
| Ownership enforcement | Criterion 7 |
| Version relationships | Revision, document-version and profile-revision tests |
| Transaction rollback | `test_failed_unit_of_work_rolls_back_everything` |
| Optimistic concurrency | Stale-write tests (sequential; A2) |
| Migration execution | Criterion 9 |
| Repository behavior | All integration modules |
| Document registration, versions, original reference, representation, chunk order and provenance, embedding metadata, failed processing, retry and idempotency, isolation, deletion dependencies | `test_document_repositories.py` |
| Chunks not retrievable as memories; embeddings not confused; cross-user access rejected; version changes don't move references | `test_document_chunks_are_never_personal_memories`, `test_only_the_evidence_path_crosses_domains`, ownership tests, `test_a_new_version_does_not_move_existing_evidence` |
| Database unavailable | `test_connection_errors_become_persistence_errors` |
| Object storage unavailable; partial object upload | **Not tested** (A3a) |
| Database write failure | Duplicate-key and constraint tests; commit failure **not tested** (A2) |
| Worker interruption | `test_operation_retry_and_failure_are_recorded` (stale worker rejected; `retry_pending`) |
| Duplicate operation | `test_operations_are_idempotent_per_key`, `test_deletion_operations_are_idempotent_per_key` |
| Concurrent update | Sequential stale writes only (A2) |
| Migration failure | **Not tested** (A2) |

## 6. Follow-up (2026-11-11, same day)

The owner answered "Yes, fix A1–A2" to "Should I fix A1–A2 here, deferring A3 as proposed?".

| Item | Outcome |
|---|---|
| A1 | **Fixed.** Migration `0006_episode_version` adds `pm_episode.version` (≥ 1, existing rows start at 1) and recreates the episode guard trigger with `version` added. `EpisodeRepository.update` now takes `expected_version` and writes the next version; a stale writer gets `ConcurrencyConflictError`. Tests: `test_episode_updates_are_conditional_on_the_version`, `test_episode_versions_start_at_one`, `test_migration_0006_extends_the_episode_guard_from_0004` |
| A2 | **Fixed.** `test_racing_transactions_cannot_both_update_an_episode`: two real connections race, and the second blocks on the row lock and then gets `ConcurrencyConflictError`. `test_a_failed_commit_is_reported_rolled_back_and_closed`: a failed COMMIT raises `PersistenceError`, then rollback and close run. `test_a_failing_migration_leaves_the_previous_revision_intact`: 0005 fails part-way, and the schema stays at 0004 with nothing from 0005 left |
| A3 | **Accepted as deferrals** and recorded in [KNOWN_CONSTRAINTS.md](KNOWN_CONSTRAINTS.md): object-storage failure tests move to 8.3; least-privilege database roles move to the first deployment environment |
| A4 | **Done.** PR #10 merged (`977c3b7`), then PR #11 with step 5 and the A1–A2 fixes (`423b6fd`). On `main` @ `423b6fd`: `uv sync --locked` ok; ruff and format clean; mypy strict clean (63 files); `pytest --cov` **412 passed** (300 unit, 112 integration), 96% coverage, plus 3 further green runs; database stopped → 112 skipped |

**Checks after the fixes** (same branch, uncommitted changes): `uv sync --locked` ok; ruff and format clean; mypy strict clean (63 files); `uv run pytest --cov` **412 passed** (300 unit, 112 integration), 96% coverage, 6 consecutive runs green; database stopped → 112 skipped.

**Criteria now:** all twelve are met, given the accepted A3 deferrals, and A4 confirmed them on `main`. **Phase 8.2 is `VERIFIED` (2026-11-11).**

## 7. Other observations

- `CLAUDE.md` "Current phase" still described 8.1 as current and 8.2 as unapproved. Corrected in this review, since it is the first file every session reads.
- Recorded deviations remain valid and documented: no `me_operation` table (7.1 §23.6 note), optional `content_ref` (8.3), the `simple` full-text configuration (G6 open), and the evidence `*_ref` copies (7.1 §23.3 note).
- No secrets in the repository; the test database credentials in `docker-compose.yml` are local, test-only values.
