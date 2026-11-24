# Phase 8.4 Acceptance Review (personal path)

**Date:** 2026-11-22.

**Reviewed:** branch `feat/phase-8-4-acceptance` (step 6, uncommitted) on top of `main` @ `5386654`. That `main` holds steps 1–5:
- [PR #24](https://github.com/SARTHAK10710/raven-research-agent/pull/24) to [PR #27](https://github.com/SARTHAK10710/raven-research-agent/pull/27);
- [PR #28](https://github.com/SARTHAK10710/raven-research-agent/pull/28).

**Against:**
- [plan 8.4](../implementation-plans/Phase-08-memory-engine/04-extraction-and-evaluation.md) §13–§16 and its amendment;
- [7.1 §25](../technical-decisions/01-baseline-technology-stack.md);
- [7.7](../technical-decisions/07-observability-and-testing-infrastructure.md) §4–§7, §13.1 and §18.

The amendment limits this review to the personal-memory path. The document-derived path is reviewed when it is completed after plan 8.12 (deferral D1).

## Verdict

**Every plan 8.4 §16 criterion in scope for the personal path is met**, with one owner-accepted deferral (D1: the document-derived path).

The owner decided on 2026-11-22 (step 6) that 8.4 becomes **`VERIFIED` for the personal path** once:
- step 6 is merged (R1);
- the checks pass on the merged `main` (R2; section 7).

**Update (2026-11-24): 8.4 is `VERIFIED` for the personal path.** Step 6 is merged ([PR #29](https://github.com/SARTHAK10710/raven-research-agent/pull/29), `71adeb9`; R1), and the checks passed on that `main` (R2; section 7).

## 1. Checks run

| Command | Result |
|---|---|
| `uv sync --locked` | ok |
| `uv run ruff check .`, `uv run ruff format --check .` | clean (200 files) |
| `uv run mypy` | strict, no issues in 122 source files |
| `uv run pytest --cov` with PostgreSQL, SeaweedFS and RabbitMQ | **962 passed** (739 unit and quality, 223 integration), 98% line+branch coverage; 3 green runs |
| Same, all three services stopped | 740 passed, 222 skipped: every integration test that needs a service skips with a message |
| End-to-end quality set v1 (30 cases, 27 facts; labels owner-reviewed before the first run) | precision 0.962 (25/26), recall 0.926 (25/27), status agreement 24/25; gates 0.80 / 0.70 |
| Per-dataset floors (0.85) | language, relevance, extraction, evaluation and candidate sets all pass (95 quality tests) |

## 2. Acceptance criteria (plan 8.4 §16)

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | The relevance gate works | **Met** | Per-sentence decisions roll up to the source and are stored without text (`unit/test_relevance_gate.py`; `integration/test_relevance_gate.py`). Relevance dataset v1: 34 of 36 outcomes, every labelled reason exact. End-to-end set: 5 of 6 nothing-to-remember inputs produce no candidate (e2e-022 is a known miss) |
| 2 | Atomic fact candidates can be extracted | **Met** | `test_atomic_facts_reach_the_candidate_store_with_their_structure`; extraction dataset v1 24/24 (a regression set). **End-to-end set (labels owner-reviewed before the first run): fact precision 0.962, recall 0.926**, against gates of 0.80 and 0.70 |
| 3 | Memory categories are assigned correctly | **Met** | Rule-based, multi-label, evidence-only (7.1 §25.9): `test_categories_follow_the_evidence`. Candidate dataset v1 22/22, including the eight 6.2.6 §8.4 examples (a specification check; one rule changed after its first run) |
| 4 | Explicit and inferred information remain distinguishable | **Met, with limitation L1** | The origin is `explicit`, `inferred` or `unresolved`, with a reason and evidence locations (`test_an_inferred_proposal_keeps_its_evidence`, `test_inferred_candidates_keep_their_evidence`). Unresolved origins are never validated (domain and generator). Nothing generates inferences yet (L1) |
| 5 | Importance and confidence are evaluated independently | **Met** | Separate rule tables and separate columns, plus extraction confidence (`test_dimensions_are_independent`, `test_scores_context_and_provenance_stay_separate`, `test_evaluated_candidates_keep_independent_scores_and_origin`) |
| 6 | Provenance is preserved | **Met** | Each candidate references its Memory Source (composite owner key) and keeps its segment and sentence location, its method versions and the origin's evidence. The gate's decision and the run summary are stored on the source; the evaluation history is in `pm_candidate_evaluation` (`test_extraction_ends_in_validated_candidates_and_a_resolution_handoff`) |
| 7 | Document-derived extraction requires authorization | **Deferred (D1)** | The document path is disabled until 8.12 and Decision 6 |
| 8 | Document evidence is traceable to version and location | **Deferred (D1)** | As 7 |
| 9 | Candidates enter the normal memory resolution workflow | **Met for 8.4's side (L2)** | Candidates stay in the candidate lifecycle; nothing is merged, resolved or activated. Validated candidates are handed to resolution through the transactional outbox (`personal_resolution`), published while still due and abandoned when not (`test_a_resolution_handoff_whose_candidates_left_validated_is_abandoned`). The consumer is plan 8.6 (L2) |
| 10 | No automatic document-to-memory conversion on upload | **Holds; formal review with D1** | Ingestion never creates a Memory Source from a document (8.3 review). The personal pipeline reads only Memory Sources, and `documents` never imports `personal` (`test_document_intelligence_never_imports_personal_memory`) |
| 11 | No generative LLM dependency is introduced | **Met** | spaCy and deterministic rules only. `unit/test_dependency_policy.py` checks the locked dependency set against a list of generative-model clients and runtimes |
| 12 | Required tests pass | **Met** | Section 1 and section 3 |

## 3. Plan 8.4 §15 testing requirements (personal path)

| Requirement | Evidence |
|---|---|
| Explicit preference | cand-001, e2e-025, e2e-013; `test_a_valid_proposal_becomes_a_validated_candidate` |
| Goal extraction | cand-002, cand-009, e2e-002, e2e-021 |
| Decision extraction | cand-003, cand-010, e2e-003 |
| Commitment extraction | cand-008, cand-020, e2e-004, e2e-029 |
| Multi-fact input | e2e-001, e2e-013 (both facts found); cand-016; e2e-026 is a granularity miss (L4) |
| Irrelevant content | Relevance dataset v1; e2e-006, -007, -019, -024, -030 produce nothing; `test_a_gated_source_stops_with_the_gate_reason` |
| Hypothetical statements | `test_a_hypothetical_life_event_is_rejected_not_protected`; e2e-008 stays `conditional`; a lost condition goes to review (`CONDITION_LOST`) |
| Third-party information | cand-005, cand-013, e2e-010, e2e-020: subjects kept, never assigned to the user (`THIRD_PARTY_STATEMENT`) |
| Ambiguous statements | `test_reported_and_ambiguous_statements_go_to_review`, cand-014, e2e-011. e2e-012 produced no candidate: a recall miss (L4) |
| Inferred versus explicit classification | Criterion 4 |
| Importance and confidence independence | Criterion 5 |

**Integrity tests (§15):**

| Requirement | Evidence |
|---|---|
| Candidate provenance remains available | Criterion 6 |
| Document chunks are not converted into personal memories | Criterion 10; the personal pipeline has no document input |
| Upload alone does not create personal memory | 8.3 review, criterion 10 |
| Document extraction uses the normal candidate lifecycle | D1 |
| Extraction does not bypass memory resolution | The extraction transaction writes only the processing events, the relevance decision, candidates, their evaluations and the outbox; it has no write path to Atomic Memories (`personal/application/extraction.py`) |
| Rejected candidates are not treated as active memories | Rejected proposals are never stored (`test_rejected_proposals_are_counted_never_stored`) |
| User ownership is enforced | `test_a_source_of_another_owner_is_never_seen`, `test_a_message_naming_another_owner_finds_nothing`, `test_a_proposal_of_another_owner_or_source_is_rejected`, `test_a_decision_is_owner_scoped` |

## 4. Observability (step 6; 7.1 §25.10)

Per run, through the `Metrics` port (no-op by default), with labels limited to states and codes:
- runs and their duration, by input and outcome;
- reason and error codes, by outcome;
- candidates, by status;
- rejected proposals, by reason.

One `extraction.<outcome>` event per handled message carries:
- ids, codes and counts;
- the duration and `user_scope`;
- never content.

A telemetry failure never changes the outcome.

Evidence:
- `test_a_run_records_bounded_metrics_and_one_event`, `test_an_invalid_message_is_counted_without_an_input`, `test_telemetry_failure_never_changes_the_outcome`;
- `test_run_metrics_map_the_summary_to_bounded_labels`, `test_run_metrics_carry_reason_and_error_codes`.

## 5. Deferral (owner-accepted)

- **D1, document-derived path:** plan 8.4 §4.2, §10–§11, the document-derived tests of §15 and criteria 7, 8 and 10.
  - It follows plan 8.12 and Decision 6 (amendment, 2026-11-12).
  - 8.4 is `VERIFIED` for the personal path only (owner, 2026-11-22).

## 6. Known limitations (not §16 gaps)

- **L1:** no inference generator. In practice every origin is `explicit` or `unresolved`.
- **L2:** no resolution consumer until plan 8.6. `personal_resolution` messages wait in their queue. No production pipeline is assembled or deployed; the stages are composed in tests.
- **L3:** every weight and threshold is uncalibrated: relevance, extraction, evaluation, and the 0.85 / 0.80 / 0.70 quality gates.
  - Four datasets were labelled by the same author as the rules.
  - The end-to-end set was owner-reviewed before its first run.
- **L4:** end-to-end misses, kept visible rather than tuned away:
  - e2e-012: an unresolved reported claim produced no candidate;
  - e2e-022: transient trivia became a candidate;
  - e2e-026: a reason clause stayed inside its fact;
  - e2e-005: went to review for a pronoun.
- **L5:** English only (G6). Deferred sources are not re-queued, and there is no reconciliation sweep.

## 7. Items before `VERIFIED` (resolved)

- **R1:** merge step 6. Done: [PR #29](https://github.com/SARTHAK10710/raven-research-agent/pull/29), merge commit `71adeb9`.
- **R2:** repeat the checks on the merged `main`. Done 2026-11-24 on `main` @ `71adeb9`: `uv sync --locked` ok; Ruff check and format clean; mypy strict clean (122 files); `uv run pytest --cov` with all three services **962 passed** (739 unit and quality, 223 integration), 98% coverage, 3 green runs.
