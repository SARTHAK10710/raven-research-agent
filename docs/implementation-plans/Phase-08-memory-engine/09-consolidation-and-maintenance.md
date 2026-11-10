# Phase 8.9 — Consolidation & Maintenance Implementation Plan

## 1. Objective

Implement the Memory Engine's consolidation and maintenance capabilities.

The system must organize existing authoritative memories into higher-level representations while preserving original facts, historical revisions, provenance and temporal context.

It must also maintain memory quality by evaluating freshness, confidence, importance and retention utility.

### Primary objectives

- Group related memories into meaningful episodes.
- Generate higher-level semantic representations.
- Maintain derived user profiles where supported.
- Detect stale or outdated information.
- Evaluate memory freshness and retention utility.
- Apply configurable decay policies.
- Maintain memory relationships.
- Support scheduled and event-triggered consolidation.
- Ensure consolidation is idempotent.
- Preserve original memories and historical information.
- Provide auditable maintenance operations.

## 2. Architecture references

Claude Code must review:

1. `PROJECT_ARCHITECTURE.md`
2. `docs/architecture/` — Memory Engine architecture.
3. `docs/data-models/` — approved Memory Engine data models.
4. `docs/algorithms/memory/04-memory-consolidation-maintenance.md`
5. `docs/algorithms/memory/02-memory-resolution.md`
6. `docs/algorithms/shared/01-shared-algorithm-framework.md`
7. `docs/technology/01-baseline-technology-stack.md`
8. `docs/technology/02-database-and-storage-architecture.md`
9. `docs/technology/04-background-processing-and-messaging.md`
10. `docs/implementation-plans/phase-08-memory-engine/06-memory-resolution.md`
11. `docs/implementation-plans/phase-08-memory-engine/07-memory-storage-and-indexing.md`
12. `docs/implementation-plans/phase-08-memory-engine/08-memory-retrieval.md`

The approved Phase 5 models and Phase 6 algorithms are authoritative.

Do not introduce new memory lifecycle semantics or derived data models without identifying the architectural gap first.

## 3. Scope

### Included

- Episodic memory organization.
- Semantic memory consolidation.
- Derived profile generation.
- Memory relationship maintenance.
- Freshness evaluation.
- Importance and confidence maintenance.
- Retention utility evaluation.
- Configurable decay policies.
- Stale information detection.
- Consolidation scheduling.
- Event-triggered consolidation.
- Idempotent processing.
- Derived representation versioning.
- Maintenance observability and testing.

### Excluded

- Full memory forgetting and deletion execution.
- User-facing retrieval implementation.
- Agent orchestration.
- Document RAG.
- Generative response creation.

Forgetting and deletion belong to Phase 8.10.

Document RAG additions remain deferred until the final Phase 8 review.

## 4. Consolidation architecture

Implement the following logical components.

### 4.1 Consolidation Scheduler

Responsibilities:

- Identify eligible memories for consolidation.
- Trigger consolidation based on approved events or schedules.
- Prioritize pending work.
- Prevent unnecessary repeated processing.
- Support bounded background execution.
- Record consolidation jobs and outcomes.

Consolidation may be triggered by:

- New memory creation.
- Meaningful memory updates.
- Accumulation of related memories.
- Relevant entity relationship changes.
- Scheduled maintenance.
- Explicit maintenance requests.

Do not consolidate every memory after every ingestion event.

Use configurable thresholds and scheduling policies.

### 4.2 Memory Grouping Engine

Identify groups of related memories that may form meaningful episodes or higher-level representations.

Consider:

- Shared entities.
- Common projects.
- Temporal proximity.
- Related events.
- Semantic similarity.
- Existing memory relationships.
- Contextual relevance.

Grouping must not rely solely on vector similarity.

Do not combine unrelated facts simply because they share a person, organization or project.

### 4.3 Episodic Memory Manager

An episode represents a meaningful collection of related events or facts within a context.

Examples:

- A project development period.
- A job application process.
- A trip.
- A completed event.
- A sequence of related decisions.

Responsibilities:

- Identify potential episode membership.
- Create and maintain episode records.
- Associate atomic memories with episodes.
- Preserve temporal boundaries.
- Preserve source provenance.
- Support episode updates.
- Maintain membership consistency.

Use the approved Episode and Episode Membership models.

An episode must not replace its underlying atomic memories.

### 4.4 Semantic Consolidation Engine

Identify recurring information and derive higher-level representations from validated memories.

Examples:

Atomic memories:

- The user is developing Android applications.
- The user uses Kotlin.
- The user has worked with Jetpack Compose.

Potential semantic representation:

- The user has experience with Android development using Kotlin and Jetpack Compose.

Responsibilities:

- Identify supported patterns across memories.
- Generate structured semantic representations.
- Associate derived representations with supporting memories.
- Preserve evidence references.
- Track derived representation versions.
- Detect outdated derived information.
- Regenerate representations when their supporting facts change.

A derived semantic representation must never become more authoritative than its supporting evidence.

Do not discard the underlying atomic memories.

### 4.5 Derived Profile Manager

Maintain profile-level representations using the approved Derived Profile and Profile-Memory Association models.

Potential profile information includes:

- Stable preferences.
- Long-term goals.
- Recurring interests.
- Ongoing projects.
- Relevant professional context.
- Repeated behavioral patterns where sufficiently supported.

Requirements:

- Use only evidence-backed information.
- Associate profile attributes with supporting memories.
- Preserve confidence and provenance.
- Distinguish stable preferences from temporary states.
- Handle contradictions and updates.
- Track profile versions.
- Recompute affected profile information when supporting memories change.

Do not infer sensitive personal attributes or create unsupported personal classifications.

A profile is a derived view, not a replacement for the original memories.

### 4.6 Freshness Evaluator

Evaluate whether stored information is likely to remain current.

Consider:

- Source timestamp.
- Last confirmation.
- Fact category.
- Temporal nature.
- Known changes.
- Historical validity.
- Expected stability.

Different facts require different freshness policies.

Examples:

- A long-term preference may remain relevant for a long period.
- A temporary plan may become outdated quickly.
- A project status may change frequently.
- A historical event remains historically valid even when old.

Age alone must not invalidate a memory.

### 4.7 Retention Utility Evaluator

Evaluate the future usefulness of a memory.

Consider separately:

- Importance.
- Confidence.
- Freshness.
- Retrieval usefulness.
- Temporal validity.
- Supporting evidence.
- User-provided retention preferences where supported.

Do not collapse these dimensions into one unexplained score.

Retention utility helps maintenance prioritize memory organization and review.

It must not independently authorize deletion.

### 4.8 Decay Manager

Implement configurable decay policies where supported by the approved algorithms.

Decay must be applied according to memory type and context.

Requirements:

- Maintain category-specific policies.
- Consider importance and confidence.
- Consider freshness and confirmation.
- Preserve historically important facts.
- Avoid automatic deletion through decay.
- Record decay evaluation results.
- Support policy versioning.

A decrease in freshness or retention utility is not proof that a memory is false.

Decay is a maintenance signal, not a deletion command.

## 5. Consolidation workflow

Implement the following logical sequence:

1. Identify eligible memories.
2. Load relevant memory and entity context.
3. Identify potentially related groups.
4. Evaluate temporal and semantic relationships.
5. Determine whether episodic consolidation is appropriate.
6. Determine whether semantic consolidation is appropriate.
7. Generate or update derived representations.
8. Associate derived records with supporting memories.
9. Update profile representations where justified.
10. Evaluate freshness.
11. Evaluate retention utility.
12. Apply approved decay calculations.
13. Validate derived records.
14. Persist changes and processing history.
15. Mark consolidation work complete.

The process must preserve the original atomic memories and their revisions.

## 6. Consolidation triggers

Support the approved hybrid trigger strategy.

### Event-triggered

Examples:

- New important memory.
- Significant update.
- Several related memories becoming available.
- Meaningful relationship changes.

### Scheduled

Examples:

- Periodic profile maintenance.
- Episodic grouping.
- Freshness evaluation.
- Retention utility recalculation.
- Stale derived representation detection.

### Query-triggered

Where justified, a retrieval request may identify an opportunity for consolidation.

However, retrieval must not silently trigger expensive or unbounded maintenance work.

Any query-triggered consolidation must use controlled background processing.

## 7. Historical and temporal integrity

Consolidation must preserve historical context.

Examples:

- A project may have changed technologies.
- A goal may have been completed.
- A temporary preference may have changed.
- A relationship may no longer be current.

Do not merge all observations into one timeless representation.

Requirements:

- Preserve original timestamps.
- Preserve temporal validity where available.
- Distinguish current and historical states.
- Preserve supporting memory revisions.
- Record derived representation creation and update times.
- Mark derived representations stale when supporting facts materially change.

Historical facts should remain available according to their approved retention policies.

## 8. Derived data consistency

Episodes, semantic representations and profiles are derived from authoritative memories.

Implement reliable invalidation and regeneration.

When supporting memories change:

1. Identify affected derived representations.
2. Mark affected representations as stale.
3. Schedule appropriate recomputation.
4. Re-evaluate the supporting evidence.
5. Generate a new version where justified.
6. Preserve required historical derived versions.
7. Mark the new representation current.

Do not assume every source change requires complete profile regeneration.

Use targeted invalidation where practical.

All maintenance operations must be idempotent.

## 9. Persistence requirements

Use the approved Phase 8.2 persistence layer.

Reconcile implementation with the approved models, including:

- Episode.
- Episode Membership.
- Derived Profile.
- Profile-Memory Association.
- Memory Relationship.
- Atomic Memory.
- Memory revisions.
- Provenance.
- Processing history.

Requirements:

- Enforce ownership.
- Preserve supporting memory references.
- Preserve derived representation history where required.
- Maintain valid episode membership.
- Prevent duplicate consolidation operations.
- Support optimistic concurrency.
- Record maintenance policy versions.
- Keep derived records distinguishable from authoritative memories.

Do not introduce new persistence entities without documenting the model gap.

## 10. Failure handling

| Scenario | Expected behavior |
|---|---|
| No suitable memory group | Complete without consolidation |
| Insufficient evidence | Do not generate a derived fact |
| Contradictory supporting memories | Preserve conflict and defer unsupported derivation |
| Stale derived profile | Mark for controlled recomputation |
| Consolidation job repeated | Return or reuse existing result idempotently |
| Supporting memory updated | Invalidate affected derived representations |
| Missing supporting memory | Flag integrity issue |
| Concurrent maintenance | Apply approved concurrency controls |
| Database interruption | Roll back incomplete transactions |
| Worker unavailable | Retain pending job for bounded retry |
| Decay evaluation failure | Preserve authoritative memory unchanged |

A maintenance failure must never silently corrupt or delete an authoritative memory.

## 11. Testing requirements

### Unit tests

Test:

- Memory grouping.
- Episode eligibility.
- Episode membership.
- Semantic consolidation.
- Profile generation.
- Freshness evaluation.
- Retention utility evaluation.
- Decay calculations.
- Derived representation versioning.
- Invalidation logic.

### Component tests

Test:

- End-to-end episode creation.
- Episode updates.
- Semantic representation generation.
- Profile generation.
- Targeted profile recomputation.
- Scheduled maintenance.
- Event-triggered maintenance.
- Idempotent consolidation.

### Temporal and quality tests

Include:

- Stable preferences.
- Temporary plans.
- Completed goals.
- Changing project states.
- Historical events.
- Contradictory memories.
- Repeated supporting facts.
- Outdated derived profiles.
- Facts with missing timestamps.
- Changes to supporting memories.

Evaluate:

- Episode grouping quality.
- Derived fact support coverage.
- Profile correctness.
- Temporal correctness.
- Stale representation detection.
- Unjustified inference rate.
- Maintenance idempotency.

### Reliability tests

Test:

- Worker interruption.
- Duplicate scheduled jobs.
- Concurrent consolidation.
- Partial database failure.
- Reprocessing after recovery.
- Derived-data invalidation failures.

## 12. Observability

Record structured events for:

- Consolidation scheduled.
- Consolidation started.
- Memory group identified.
- Episode created or updated.
- Semantic representation generated.
- Profile updated.
- Freshness evaluated.
- Retention utility evaluated.
- Decay applied.
- Derived representation invalidated.
- Recalculation completed.
- Consolidation failed.

Track:

- Consolidation job count.
- Processing latency.
- Episode creation rate.
- Derived representation count.
- Profile recomputation count.
- Stale representation count.
- Failed maintenance jobs.
- Retry count.
- Unjustified derivation rate from evaluation.

Do not log full private memory content unnecessarily.

## 13. Acceptance criteria

Phase 8.9 is complete only when:

- [ ] Eligible memories can be grouped for consolidation.
- [ ] Episodic memories can be created and maintained.
- [ ] Atomic memories remain preserved.
- [ ] Semantic representations can be generated with evidence.
- [ ] Derived profiles can be generated using approved models.
- [ ] Supporting memory associations are preserved.
- [ ] Freshness is evaluated independently.
- [ ] Retention utility is evaluated independently.
- [ ] Decay policies are configurable.
- [ ] Decay does not automatically delete memories.
- [ ] Temporal and historical information is preserved.
- [ ] Stale derived representations can be invalidated.
- [ ] Derived representations can be recomputed.
- [ ] Scheduled and event-triggered processing works.
- [ ] Maintenance operations are idempotent.
- [ ] Failures do not corrupt authoritative memory.
- [ ] Unit and component tests pass.
- [ ] Quality evaluation is available.

## 14. Implementation constraints

Claude Code must:

1. Inspect the repository before modifications.
2. Reuse Phase 8.1–8.8 implementations.
3. Follow approved Phase 5 data models.
4. Follow Phase 6 consolidation algorithms.
5. Follow Phase 7 technology decisions.
6. Preserve atomic memories and historical revisions.
7. Keep derived representations separate from authoritative facts.
8. Keep importance, confidence, freshness and retention utility separate.
9. Avoid treating decay as deletion.
10. Preserve evidence and provenance.
11. Use bounded background processing.
12. Avoid generative LLM functionality.
13. Avoid implementing document RAG in this milestone.
14. Place source code inside `memory-engine/`.
15. Place tests inside `tests/`.
16. Do not proceed to Phase 8.10 automatically.

If an approved model cannot support a required derived representation, report the exact gap and recommendation before changing the schema.

## 15. Completion report

Claude Code must provide:

1. Summary of consolidation functionality.
2. Files created or modified.
3. Episode implementation details.
4. Semantic consolidation approach.
5. Derived profile implementation.
6. Freshness and retention utility policies.
7. Decay policy implementation.
8. Derived-data invalidation strategy.
9. Tests executed and exact results.
10. Quality evaluation results.
11. Known limitations.
12. Deviations from approved architecture.
13. Acceptance criteria status.

Clearly distinguish implemented maintenance behavior from quality claims that have not been validated.

## 16. Definition of done

Phase 8.9 is complete when Raven can organize related memories into evidence-backed episodes and derived semantic representations, maintain profile information, and evaluate freshness and retention utility without destroying original facts or historical context.

**Consolidation makes Raven's memory more organized and useful while preserving the original evidence that supports it.**
