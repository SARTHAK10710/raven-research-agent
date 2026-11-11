# Phase 8.3 Acceptance Review

**Date:** 2026-11-12. **Reviewed:** branch `feat/phase-8-3-observability-acceptance` (step 5, uncommitted) on top of `main` @ `4af8a92`, which holds steps 1–4 ([PR #16](https://github.com/SARTHAK10710/raven-research-agent/pull/16)–[PR #19](https://github.com/SARTHAK10710/raven-research-agent/pull/19)) and the status sync ([PR #20](https://github.com/SARTHAK10710/raven-research-agent/pull/20)). Step 5 was merged through [PR #21](https://github.com/SARTHAK10710/raven-research-agent/pull/21) (`1851f53`), and the checks were repeated on that `main` (section 7).

**Against:** [plan 8.3](../implementation-plans/Phase-08-memory-engine/03-ingestion-pipeline.md) §11 (observability), §12 (testing requirements) and §13 (acceptance criteria); [7.1 §23.6 and §24](../technical-decisions/01-baseline-technology-stack.md); [7.4](../technical-decisions/04-background-processing-and-messaging.md) §7, §9, §11–§12; [7.7](../technical-decisions/07-observability-and-testing-infrastructure.md) §5–§7 and §18.

## Verdict

**Every plan 8.3 §13 criterion is met**, with one owner-accepted deferral (D1).

**Update (2026-11-12): 8.3 is `VERIFIED`.** Step 5 is merged (R1), and the checks passed on the merged `main` @ `1851f53` (R2; section 7).

## 1. Checks run

| Command | Result |
|---|---|
| `uv sync --locked` | ok |
| `uv run ruff check .`, `uv run ruff format --check .` | clean (165 files) |
| `uv run mypy` | strict, no issues in 91 files |
| `uv run pytest --cov`, with `docker compose up -d --wait postgres-test object-storage-test broker-test` | **652 passed** (473 unit, 179 integration), 97% line+branch coverage; 3 green runs |
| Same, all three services stopped | 474 passed, 178 skipped: every integration test skips with a message; the unreachable-store test needs no service |

## 2. Acceptance criteria (plan 8.3 §13)

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Personal memory inputs are validated and normalized | **Met** | `unit/test_ingestion_preparation.py` (schema, encoding, size, control characters, timestamps, speakers, order); `test_text_is_stored_and_registered_but_not_processed`, `test_conversation_keeps_messages_separate_and_ordered` |
| 2 | Original source information is preserved | **Met** | Original and normalized content are stored separately, with the checksum and the source reference and timestamp (`test_text_is_stored_and_registered_but_not_processed`). For documents, the original stays readable through the handoff's object key (`test_each_supported_format_is_stored_registered_and_queued_for_handoff`) |
| 3 | Explicit remember and forget instructions are routed correctly | **Met** | Remember: high priority, carried in the handoff envelope (`test_a_personal_handoff_references_content_and_never_carries_it`). Forget: recorded and never handed to extraction, against the database and a real broker (`test_a_forget_instruction_is_never_handed_to_extraction`, `test_registrations_reach_their_queues_as_celery_tasks`). Executing a forget instruction is plan 8.10's job; the source is held as `validated` until then (owner decision, step 2) |
| 4 | Supported document formats are validated | **Met** | Detection by content, not by extension or declared type: `unit/test_document_formats.py`, `test_rejected_uploads_store_and_register_nothing`, and PDF, DOCX and TXT end to end (`test_each_supported_format_…`) |
| 5 | Original documents are securely stored | **Met for the development scope** | Keys are opaque and owner-partitioned, and every call is owner-checked. SHA-256 and size are verified on `put`, and a mismatch is deleted (`test_object_storage_s3.py`). Encryption at rest is a production-provider concern, still deferred (KNOWN_CONSTRAINTS) |
| 6 | Document and version records are registered correctly | **Met** | `test_an_upload_is_stored_registered_and_handed_an_operation`, `test_a_new_version_is_added_to_a_named_document`, `test_identical_content_uploaded_again_is_a_separate_document`, `test_a_document_being_deleted_takes_no_new_version` |
| 7 | Processing operations are traceable | **Met** | The `extraction` operation has an idempotency key. Its outbox message carries the operation, version and document ids. Ingestion and handoff events carry the record ids and the message, task and correlation ids (`test_handoff_attempts_latency_and_backlog_are_measured`, `test_document_registrations_are_counted_by_kind`) |
| 8 | Document processing is handed off reliably | **Met** | Transactional outbox and confirmed publish, then `queued` (`test_outbox_relay.py`, `test_broker_handoff.py`). Recovery when the broker is down, at least once with the same message id, and abandonment when an operation was cancelled |
| 9 | Idempotency and retry behavior are tested | **Met** | Duplicate requests, a reused key with different content, and lost races (steps 2–3). No duplicate handoff (`test_retried_registrations_never_duplicate_the_handoff`). Retry after a failure and after partial completion (`test_ingestion_acceptance.py`) |
| 10 | Ownership and security checks pass | **Met, with D1** | Every service and repository call is owner-scoped. A caller whose scope does not own the request stores, registers and hands off nothing (`test_an_unauthorized_caller_stores_registers_and_hands_off_nothing`). The relay writes only under each row's owner. No content, filenames or idempotency keys reach logs, and no identifiers reach metric labels (`test_personal_outcomes_are_counted_and_logged_without_content`). Authentication itself is D1 |
| 11 | Failure states are accurately reported | **Met** | Every outcome is classified into the plan §9 states (`observability/ingestion.py`; `test_every_failure_is_classified_and_re_raised`). Records reach `queued` only after the broker confirms; versions stay `stored` (`test_relay_hands_a_document_to_the_pipeline_without_claiming_progress`). Broken telemetry never changes an outcome |
| 12 | Required tests pass | **Met** | Section 3; 652 passed |

## 3. Plan 8.3 §12 testing requirements

| Requirement | Test(s) |
|---|---|
| **12.1** Valid text | `test_text_is_stored_and_registered_but_not_processed` |
| Invalid request; empty content; invalid encoding; missing metadata | `test_invalid_or_unsupported_input_is_rejected` (reasons such as `EMPTY_CONTENT`, `INVALID_ENCODING`, `TEXT_REQUIRED`, `MESSAGES_REQUIRED`, `INVALID_SPEAKER`, `NAIVE_TIMESTAMP`), `test_rejected_and_foreign_requests_store_nothing` |
| Unauthorized request | Scope mismatch: `test_an_unauthorized_caller_stores_registers_and_hands_off_nothing`. Authentication: **D1** |
| Ownership mismatch | `test_rejected_and_foreign_requests_store_nothing`, `test_idempotency_keys_are_per_owner` |
| Explicit remember; explicit forget | `test_explicit_instructions_are_high_priority`, `test_a_forget_instruction_is_never_handed_to_extraction` |
| Duplicate request; retry after failure | `test_a_retry_returns_the_same_source_without_storing_again`, `test_a_retry_after_a_failure_registers_and_hands_off_once` |
| **12.2** Valid PDF, DOCX, TXT | `test_each_supported_format_is_stored_registered_and_queued_for_handoff[pdf/docx/txt]`, `test_supported_formats_are_detected_from_content` |
| Invalid content; extension mismatch; oversized; empty; malformed | `test_unsupported_damaged_or_empty_files_are_rejected`, `test_extension_and_declared_type_must_match_the_content`, `test_rejected_uploads_store_and_register_nothing` |
| Duplicate upload; identical file as a separate document | `test_a_retry_returns_the_same_registration`, `test_identical_content_uploaded_again_is_a_separate_document` |
| Storage failure; database registration failure | `test_a_storage_outage_registers_nothing`, `test_a_failed_registration_removes_the_stored_original` |
| Handoff failure | `test_a_failed_publish_is_recoverable_and_never_marks_the_source_queued`, `test_an_unreachable_broker_leaves_the_handoff_recoverable` |
| Retry after partial completion | `test_a_retry_after_partial_completion_registers_one_document` |
| Cross-user access attempt | `test_uploads_are_owner_scoped`, `test_relay_writes_each_owner_in_its_own_scope` |
| **12.3** Successful registration and handoff | `test_relay_hands_a_document_to_the_pipeline_without_claiming_progress`, `test_registrations_reach_their_queues_as_celery_tasks` |
| Operation traceable; original reference valid | `test_each_supported_format_…`, `test_document_registrations_are_counted_by_kind` |
| Failed handoff recoverable | `test_exhausted_attempts_fail_visibly_until_an_explicit_retry`, `test_a_commit_failure_after_publishing_republishes_the_same_message` |
| No duplicate registration on retry | `test_retried_registrations_never_duplicate_the_handoff`, `test_a_second_handoff_of_the_same_subject_is_refused` |
| Not falsely marked complete | `test_relay_hands_a_document_to_the_pipeline_without_claiming_progress` (version stays `stored`) |
| Personal memory and document ingestion separate | `test_personal_and_document_ingestion_stay_separate` |

## 4. Plan 8.3 §11 observability

All metrics go through the `Metrics` port. The default recorder is a no-op; the OpenTelemetry adapter waits for monitoring to be deployed (owner decision, step 5).

| Item | Where |
|---|---|
| Ingestion requests; accepted and rejected; validation and storage failures; duplicates | `memory_ingestion_requests_total{input,outcome}`, `memory_ingestion_rejections_total{input,reason}`; one `ingestion.<outcome>` event per request |
| Document registration | `memory_document_registrations_total{kind=document,version}` |
| Processing handoff; handoff failures; retry counts | `memory_handoff_attempts_total{kind,outcome}`; `handoff.<outcome>` events with attempts and error code |
| Processing latency | `memory_ingestion_duration_seconds{input,outcome}`; `memory_handoff_latency_seconds{kind}` (registration to confirmed publish) |
| Outbox backlog (7.7 §7.5) | `memory_outbox_pending`, `memory_outbox_failed`, `memory_outbox_oldest_pending_age_seconds` |
| Correlation (7.7 §5) | Record ids on ingestion events. Handoff events carry `message_id`, `task_id` and `correlation_id`, and `user_scope` is the opaque owner id (owner decision) |
| Privacy (7.7 §18) | No content, filenames or idempotency keys in events. Labels are bounded words and codes, so no identifier can become a label (tested) |

## 5. Deferral (owner-accepted)

- **D1: authentication tests.** Phase 8 has no authentication layer: the Entry layer is out of scope, and callers pass an `OwnerScope`. The owner accepted on 2026-11-12 that "unauthorized request" is covered as an owner-scope mismatch, and that authentication tests move to the Entry layer.

## 6. Known limitations (not §13 gaps)

- No consumer yet: 8.4 and 8.12 register the tasks. The relay process is not deployed or scheduled (7.8).
- No dead-letter queue and no outbox cleanup (7.4 §13, §22). Plan 8.10 must remove a subject's outbox rows when deleting it.
- No malware scanning (owner-accepted, step 3).
- No encryption at rest in the development object store.
- The test broker has no TLS (127.0.0.1 only).
- Metrics go to a no-op recorder until monitoring is deployed.

## 7. Items before `VERIFIED` (resolved)

| # | Item | Result |
|---|---|---|
| R1 | Merge step 5 | Done: [PR #21](https://github.com/SARTHAK10710/raven-research-agent/pull/21), merge commit `1851f53` |
| R2 | Re-run the checks on the merged `main` | Done on `main` @ `1851f53`: `uv sync --locked` ok; ruff and format clean; mypy strict clean (91 files); `uv run pytest --cov` with all three services: 652 passed, 0 failed, 0 skipped, 97% coverage. 8.3 marked `VERIFIED` |
