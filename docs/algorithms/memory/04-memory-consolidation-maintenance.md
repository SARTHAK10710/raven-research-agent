# Phase 6.5 — Memory Consolidation & Maintenance Algorithms

**Project:** Raven Research Agent  
**Phase:** 6 — Algorithms & Processing Design  
**Subphase:** 6.5 — Memory Consolidation & Maintenance  
**Status:** Architecture and algorithm specification  
**Optimization Priority:** Quality first  
**Processing Approach:** Hybrid — deterministic rules, conventional NLP/statistical methods, and selective non-generative ML

---

## 1. Purpose

The Memory Engine continuously accumulates information. Without maintenance, this can lead to:

- Outdated information being treated as current.
- Repeated or overlapping memories.
- Disconnected facts that should be understood together.
- Derived conclusions becoming inconsistent with their underlying facts.
- Profiles becoming stale.
- Unnecessary storage and indexing overhead.
- Deleted information remaining in secondary storage or derived records.

This phase defines the algorithms responsible for keeping the Memory Engine accurate, consistent, useful, and maintainable over time.

The objective is not simply to reduce the number of stored memories. It is to preserve valuable information, improve its organization, identify outdated information, and safely remove information when required.

### Core principles

1. Atomic memories remain the authoritative factual records.
2. Episodes and semantic conclusions are derived representations.
3. Importance, confidence, freshness, and retention utility are separate dimensions.
4. Memory decay does not automatically authorize deletion.
5. Historical information may remain valuable even when it is no longer current.
6. Explicit forgetting and deletion requests take priority over routine maintenance.
7. Every destructive operation must be traceable, authorized, and recoverable where appropriate.
8. Consolidation must be idempotent.
9. Derived records must retain references to their underlying evidence.
10. Quality and data integrity take priority over storage or processing efficiency.

---

# 2. Algorithm Inventory

This phase defines ten algorithms.

| ID | Algorithm | Primary responsibility |
|---|---|---|
| 6.5.1 | Memory Lifecycle & Maintenance Scheduling | Decide when maintenance should run |
| 6.5.2 | Memory Decay & Freshness Evaluation | Evaluate how current a memory remains |
| 6.5.3 | Importance-Based Retention | Determine whether information should remain retained |
| 6.5.4 | Episodic Memory Formation | Group related atomic memories into episodes |
| 6.5.5 | Semantic Memory Consolidation | Derive higher-level knowledge from atomic memories |
| 6.5.6 | Derived Profile Generation & Refresh | Maintain user and project profiles |
| 6.5.7 | Stale Memory Detection & Revalidation | Identify information requiring review |
| 6.5.8 | Memory Forgetting & Deletion Orchestration | Coordinate forgetting and deletion requests |
| 6.5.9 | Deletion Propagation & Verification | Remove information across dependent storage |
| 6.5.10 | Consolidation Integrity & Recovery | Protect maintenance operations against failure |

---

# 3. 6.5.1 — Memory Lifecycle & Maintenance Scheduling

## Purpose

Determine when a memory or group of memories should undergo maintenance.

Maintenance must not depend exclusively on a fixed schedule. Some events require immediate processing, while other operations can run periodically.

## Trigger categories

### A. Event-driven triggers

Examples:

- A new important memory is promoted.
- An existing memory is updated or corrected.
- A memory is superseded.
- An entity relationship changes.
- A meaningful contradiction is resolved.
- A deletion request is received.
- A source is corrected or invalidated.

### B. Scheduled triggers

Examples:

- Freshness evaluation.
- Stale-memory detection.
- Profile refresh.
- Episode formation.
- Semantic consolidation.
- Retention evaluation.
- Index consistency checks.

### C. On-demand triggers

Examples:

- A user requests an updated profile.
- A retrieval operation detects stale information.
- A project context needs consolidation.
- An explicit maintenance operation is requested.

## Processing strategy

Use a hybrid scheduler.

| Maintenance type | Preferred trigger |
|---|---|
| Explicit deletion | Immediate |
| Critical correction | Event-driven |
| Important memory consolidation | Event-driven |
| Profile refresh | Event-driven and scheduled |
| Freshness evaluation | Scheduled and on-demand |
| Episode formation | Event-driven and scheduled |
| Semantic consolidation | Scheduled and event-driven |
| Index consistency | Scheduled |
| Recovery and reconciliation | Event-driven and scheduled |

## Algorithm

**Input:**

- Memory lifecycle events.
- Maintenance configuration.
- Memory metadata.
- Pending maintenance jobs.
- Resource availability.

**Output:**

- Maintenance job.
- Selected maintenance operation.
- Priority.
- Execution scope.
- Scheduling decision.

### Processing steps

1. Receive a maintenance trigger.
2. Validate the trigger and its ownership context.
3. Identify affected memories, entities, episodes, or profiles.
4. Determine the maintenance operation required.
5. Check whether an equivalent operation is already pending or running.
6. Deduplicate equivalent jobs using an idempotency key.
7. Assign priority based on correctness impact, urgency, and dependencies.
8. Schedule the job within configured resource limits.
9. Record its execution status.
10. Preserve enough state to resume safely after interruption.

### Pseudocode

```text
FUNCTION schedule_maintenance(trigger):

    validate_trigger(trigger)

    IF trigger.type == EXPLICIT_DELETION:
        RETURN schedule_deletion_immediately(trigger)

    scope = identify_affected_scope(trigger)

    operations = determine_required_operations(
        trigger,
        scope
    )

    FOR EACH operation IN operations:

        key = generate_idempotency_key(
            operation,
            scope,
            trigger.version
        )

        IF equivalent_job_exists(key):
            continue

        priority = calculate_maintenance_priority(
            operation,
            trigger,
            scope
        )

        create_maintenance_job(
            operation,
            scope,
            priority,
            key
        )

    RETURN scheduling_result
```

## Acceptance criteria

- Duplicate maintenance jobs are not unnecessarily created.
- Explicit deletion does not wait for routine maintenance.
- Jobs preserve user and ownership boundaries.
- Failed jobs can resume without repeating completed destructive work.
- Resource limits are respected.

---

# 4. 6.5.2 — Memory Decay & Freshness Evaluation

## Purpose

Evaluate how current and useful a memory remains over time.

A memory's age alone does not establish that it is outdated.

For example:

- A user's educational qualification may remain valid for years.
- A temporary travel plan may become outdated within days.
- A long-term preference may change gradually.
- A historical event remains historically true even when it is old.

Therefore, freshness must depend on memory type and temporal context.

## Independent evaluation dimensions

The algorithm evaluates:

1. **Age:** How much time has passed since the relevant update or observation?
2. **Freshness:** How current is the information for its intended use?
3. **Confidence:** How strongly is the information supported?
4. **Importance:** How valuable is the information?
5. **Temporal sensitivity:** How quickly can this type of information become outdated?

These dimensions must not be collapsed into one universal score.

## Freshness model

A configurable decay function can be used as an initial signal:

\[
F(t)=e^{-\lambda t}
\]

Where:

- \(F(t)\) is the decay signal.
- \(t\) is elapsed time.
- \(\lambda\) is the configurable decay rate.

The decay rate should depend on the memory's category and context.

This is a conceptual model, not a finalized universal scoring formula.

### Example

| Memory type | Expected freshness behavior |
|---|---|
| Long-term preference | Slow decay |
| Educational qualification | Very slow decay |
| Current project status | Moderate decay |
| Temporary plan | Faster decay |
| Short-term availability | Very fast decay |
| Historical event | Historical validity does not decay |

## Algorithm

**Input:**

- Atomic memory.
- Last update timestamp.
- Memory category.
- Temporal context.
- Configured decay policy.
- Existing confidence and importance metadata.

**Output:**

- Freshness evaluation.
- Staleness classification.
- Revalidation recommendation.
- Evaluation metadata.

### Processing steps

1. Retrieve the memory and its current revision.
2. Identify its category and temporal sensitivity.
3. Calculate elapsed time.
4. Apply the appropriate freshness policy.
5. Check for newer related memories.
6. Check whether the memory has been superseded.
7. Distinguish historical validity from current applicability.
8. Assign a freshness classification.
9. Recommend retention, revalidation, historical classification, or review.
10. Store the evaluation result.

### Freshness classifications

- `CURRENT`
- `POTENTIALLY_STALE`
- `STALE`
- `HISTORICAL`
- `SUPERSEDED`
- `REQUIRES_REVALIDATION`
- `UNKNOWN`

### Pseudocode

```text
FUNCTION evaluate_freshness(memory):

    validate_memory_access(memory)

    category = identify_memory_category(memory)

    policy = get_freshness_policy(category)

    age = calculate_elapsed_time(
        memory.last_relevant_update
    )

    decay_signal = calculate_decay(
        age,
        policy.decay_rate
    )

    newer_records = find_newer_related_memories(memory)

    IF memory.status == SUPERSEDED:
        classification = SUPERSEDED

    ELSE IF memory.is_historical:
        classification = HISTORICAL

    ELSE IF newer_records_materially_change(memory):
        classification = REQUIRES_REVALIDATION

    ELSE:
        classification = classify_freshness(
            decay_signal,
            policy,
            memory.context
        )

    RETURN freshness_evaluation
```

## Critical restriction

**Freshness decay must never independently delete a memory.**

A stale memory can still be historically important, useful for comparisons, or necessary for understanding later decisions.

---

# 5. 6.5.3 — Importance-Based Retention

## Purpose

Determine how a memory should be retained based on its long-term value and operational importance.

The Memory Engine should avoid treating every memory equally.

However, importance alone cannot determine whether a memory is true, current, or safe to retain.

## Retention dimensions

Evaluate independently:

- Importance.
- Confidence.
- Freshness.
- Retrieval utility.
- Historical value.
- User instructions.
- Retention policy.
- Dependency relationships.

## Retention classifications

| Classification | Meaning |
|---|---|
| `ACTIVE` | Useful for current context |
| `RETAINED` | Valuable long-term information |
| `HISTORICAL` | No longer current but historically useful |
| `REQUIRES_REVIEW` | Value or validity is uncertain |
| `INACTIVE` | Not currently needed but retained |
| `ELIGIBLE_FOR_EXPIRY_REVIEW` | May be removed under an applicable retention policy |

These are logical lifecycle classifications. They do not necessarily correspond to physical storage locations.

## Algorithm

**Input:**

- Memory record.
- Importance score.
- Confidence score.
- Freshness evaluation.
- Retrieval usage signals.
- User retention instructions.
- Applicable retention policy.

**Output:**

- Retention classification.
- Retention rationale.
- Recommended lifecycle action.

### Processing steps

1. Validate ownership and memory status.
2. Retrieve current importance and confidence evaluations.
3. Retrieve freshness and temporal information.
4. Evaluate historical and retrieval value.
5. Check explicit user retention instructions.
6. Check dependencies from episodes, profiles, and semantic conclusions.
7. Apply retention policy.
8. Assign a retention classification.
9. Record the decision and rationale.

### Pseudocode

```text
FUNCTION evaluate_retention(memory):

    validate_memory_access(memory)

    IF memory.has_explicit_retention_instruction:
        RETURN RETAINED

    importance = memory.importance
    confidence = memory.confidence
    freshness = get_freshness(memory)

    historical_value = evaluate_historical_value(memory)

    dependency_value = check_derived_dependencies(memory)

    IF memory.status == DELETED:
        RETURN EXCLUDE_FROM_RETENTION

    IF memory.is_superseded:
        IF historical_value == HIGH:
            RETURN HISTORICAL

    IF memory.confidence == INSUFFICIENT:
        RETURN REQUIRES_REVIEW

    RETURN apply_retention_policy(
        importance,
        confidence,
        freshness,
        historical_value,
        dependency_value
    )
```

## Important safeguards

- Low importance does not automatically mean deletion.
- Low retrieval frequency does not prove that information is useless.
- High importance does not make an uncertain memory reliable.
- Historical records should remain available when appropriate.
- Explicit user deletion overrides ordinary retention decisions, subject to applicable preservation constraints.

---

# 6. 6.5.4 — Episodic Memory Formation

## Purpose

Group related atomic memories into meaningful episodes.

An episode represents a collection of related events, observations, decisions, or activities.

Atomic memories remain independently identifiable and authoritative.

An episode provides additional context and temporal organization.

## Example

Suppose Raven has these atomic memories:

- User started a new internship.
- User joined the mobile application development team.
- User worked with React Native.
- User completed an assigned feature.
- User received feedback from a supervisor.

These facts may be grouped into an internship episode.

The episode does not replace the underlying atomic memories.

## Grouping dimensions

Evaluate:

1. Entity overlap.
2. Project or activity relationship.
3. Temporal proximity.
4. Context similarity.
5. Event sequence.
6. Relationship types.
7. Shared source context.

Temporal proximity alone must not be enough to create an episode.

## Algorithm

**Input:**

- Eligible atomic memories.
- Entity references.
- Timestamps and valid-time information.
- Memory relationships.
- Existing episodes.

**Output:**

- New episode or updated episode.
- Episode membership records.
- Timeline information.
- Provenance references.

### Processing steps

1. Select eligible atomic memories.
2. Identify shared entities and context.
3. Find related existing episodes.
4. Evaluate temporal and semantic compatibility.
5. Determine whether memories belong to an existing episode.
6. Create a new episode when appropriate.
7. Create or update independent membership records.
8. Preserve event ordering and timestamps.
9. Recalculate episode boundaries.
10. Validate that no unrelated memories were included.

### Pseudocode

```text
FUNCTION form_episodes(memory_batch):

    eligible = filter_eligible_atomic_memories(
        memory_batch
    )

    groups = group_by_shared_context(eligible)

    FOR EACH group IN groups:

        candidates = find_related_episodes(group)

        episode = evaluate_episode_match(
            group,
            candidates
        )

        IF episode.match_is_valid:
            update_episode_membership(episode, group)

        ELSE:
            episode = create_episode(group)

        validate_episode_membership(episode)

    RETURN episode_results
```

## Episode integrity rules

- Each membership record references an existing atomic memory.
- A memory may participate in more than one episode when justified.
- Episode membership does not change the underlying atomic fact.
- Episode boundaries are recalculated when relevant memories change.
- Removing one memory must not automatically delete unrelated episode members.
- Deleted memories must be removed from episode representations.

---

# 7. 6.5.5 — Semantic Memory Consolidation

## Purpose

Derive higher-level knowledge from multiple related atomic memories.

Semantic consolidation identifies recurring patterns, stable facts, and meaningful relationships.

It must not introduce unsupported facts.

## Example

Atomic memories:

- User repeatedly works on Android projects.
- User has experience with Kotlin.
- User has built applications using Jetpack Compose.
- User has worked with Android APIs.

Possible derived knowledge:

- User has practical Android application development experience.

The derived conclusion must reference its supporting atomic memories.

## Processing approach

Use:

- Deterministic rules.
- Structured attribute aggregation.
- Conventional NLP.
- Statistical pattern detection.
- Non-generative semantic similarity.
- Confidence and evidence evaluation.

No generative LLM API or locally hosted generative LLM is part of this algorithm.

## Algorithm

**Input:**

- Related atomic memories.
- Existing semantic records.
- Entity and relationship information.
- Provenance references.
- Confidence metadata.

**Output:**

- New or updated semantic memory.
- Supporting memory references.
- Confidence evaluation.
- Consolidation metadata.

### Processing steps

1. Select eligible related atomic memories.
2. Group records by entity, topic, project, or attribute.
3. Identify recurring patterns or consistent attributes.
4. Detect contradictory or incompatible evidence.
5. Determine whether a conclusion is supported.
6. Generate a structured derived representation.
7. Link it to all supporting atomic memories.
8. Calculate confidence based on evidence quality and consistency.
9. Compare with existing semantic records.
10. Create, update, or mark for review.
11. Preserve the underlying atomic memories.

### Pseudocode

```text
FUNCTION consolidate_semantic_memory(memory_group):

    validate_memory_group(memory_group)

    evidence = collect_supporting_memories(memory_group)

    patterns = identify_supported_patterns(evidence)

    contradictions = detect_evidence_conflicts(evidence)

    IF contradictions.require_review:
        RETURN NEEDS_REVIEW

    conclusions = derive_structured_conclusions(patterns)

    FOR EACH conclusion IN conclusions:

        confidence = evaluate_evidence_support(
            conclusion,
            evidence
        )

        IF confidence < required_confidence:
            preserve_as_unconfirmed(conclusion)
            continue

        existing = find_matching_semantic_record(conclusion)

        IF existing:
            update_derived_record(
                existing,
                conclusion,
                evidence
            )
        ELSE:
            create_derived_record(
                conclusion,
                evidence
            )

    RETURN consolidation_result
```

## Semantic memory safeguards

- Semantic conclusions are derived records, not replacements for atomic memories.
- Every conclusion must preserve supporting references.
- Contradictory evidence must remain visible.
- A conclusion must be invalidated or recalculated when its supporting memories materially change.
- A derived conclusion must never silently become an explicit user statement.
- Confidence must reflect the underlying evidence.
- Unsupported generalizations must be rejected.

---

# 8. 6.5.6 — Derived Profile Generation & Refresh

## Purpose

Maintain useful, structured profiles based on existing memories.

Profiles provide a summarized representation of relevant information about a user, project, entity, or recurring context.

They are derived data and must not become independent sources of truth.

## Profile categories

Examples:

- User profile.
- Preference profile.
- Project profile.
- Skill and knowledge profile.
- Relationship context.
- Work context.

## Profile architecture

A profile contains:

- Profile identity.
- Profile scope.
- Structured attributes.
- Supporting memory references.
- Confidence metadata.
- Last refresh timestamp.
- Source version information.
- Profile version.
- Current status.

## Algorithm

**Input:**

- Existing profile.
- Relevant atomic memories.
- Semantic memory records.
- Memory updates and corrections.
- Profile schema.

**Output:**

- New or updated profile.
- Supporting references.
- Refresh metadata.
- Conflict or review status.

### Processing steps

1. Identify the profile scope.
2. Retrieve relevant active and historical memories as appropriate.
3. Compare source memory versions with the profile's recorded versions.
4. Identify newly added, updated, superseded, or deleted memories.
5. Recalculate affected profile attributes.
6. Detect conflicting information.
7. Preserve attributes that remain valid.
8. Remove or revise attributes that are no longer supported.
9. Update provenance and version metadata.
10. Commit the new profile version.
11. Record the refresh outcome.

### Pseudocode

```text
FUNCTION refresh_profile(profile_id):

    profile = load_profile(profile_id)

    validate_profile_scope(profile)

    changed_memories = find_changed_source_memories(
        profile.source_versions
    )

    IF changed_memories.is_empty:
        RETURN NO_CHANGE

    affected_attributes = identify_affected_attributes(
        changed_memories,
        profile
    )

    FOR EACH attribute IN affected_attributes:

        evidence = retrieve_attribute_evidence(attribute)

        result = recompute_profile_attribute(evidence)

        IF result.has_unresolved_conflict:
            mark_attribute_for_review(attribute)
        ELSE:
            update_attribute_with_provenance(
                profile,
                attribute,
                result
            )

    update_profile_version(profile)

    validate_profile_integrity(profile)

    RETURN profile
```

## Profile safeguards

- Profiles must preserve references to their source memories.
- A deleted source must not continue supporting a profile attribute.
- Conflicts must not be resolved by arbitrary selection.
- Profile refreshes must be versioned.
- Partial refresh failures must not silently produce a profile marked fully current.
- A profile must be reproducible from its eligible source records and defined processing rules.

---

# 9. 6.5.7 — Stale Memory Detection & Revalidation

## Purpose

Identify memories that may no longer accurately represent current circumstances.

This algorithm is different from freshness scoring.

Freshness evaluation estimates currentness. Stale-memory detection identifies records that need further investigation or revalidation.

## Detection signals

- Old update timestamp relative to category policy.
- Newer related memories.
- Changed entity attributes.
- Conflicting observations.
- Expired temporary context.
- Changed project status.
- Source corrections.
- Failed verification.
- Explicit user correction.

## Algorithm

**Input:**

- Active memories.
- Freshness evaluations.
- Related memory records.
- Entity updates.
- Temporal metadata.
- Source and correction events.

**Output:**

- Stale-memory candidates.
- Revalidation recommendations.
- Historical classification recommendations.
- Supersession recommendations.

### Processing steps

1. Select eligible active memories.
2. Check freshness evaluations.
3. Identify newer related observations.
4. Compare temporal validity.
5. Identify conflicts and changed attributes.
6. Evaluate whether the old record remains historically valid.
7. Determine whether revalidation is needed.
8. Mark the memory for review without destructive modification.
9. Trigger the appropriate update or resolution workflow.
10. Preserve the previous version.

### Pseudocode

```text
FUNCTION detect_stale_memories(memory_batch):

    results = []

    FOR EACH memory IN memory_batch:

        freshness = evaluate_freshness(memory)

        newer = find_newer_related_memories(memory)

        conflicts = find_material_conflicts(memory)

        IF memory.is_deleted:
            continue

        IF freshness == STALE
           OR newer.materially_changes(memory)
           OR conflicts.require_review:

            recommendation = determine_revalidation_action(
                memory,
                newer,
                conflicts
            )

            mark_for_review(memory, recommendation)

            results.append(memory)

    RETURN results
```

## Possible actions

- Keep current.
- Revalidate.
- Update through correction workflow.
- Mark as historical.
- Supersede.
- Retain with uncertainty.
- Escalate for review.

A stale-memory signal is not authorization to overwrite or delete the memory.

---

# 10. 6.5.8 — Memory Forgetting & Deletion Orchestration

## Purpose

Coordinate safe forgetting and deletion across the Memory Engine.

This algorithm is particularly important because information can exist in multiple forms:

- Atomic memories.
- Memory candidates.
- Episodes.
- Semantic conclusions.
- Derived profiles.
- Entity relationships.
- Embeddings.
- Search indexes.
- Caches.
- Archived content.
- Temporary processing data.
- Backups.

Deleting only the primary record is insufficient.

## Distinguish forgetting from deletion

### A. Policy-driven forgetting

A memory may become inactive, historical, expired, or no longer relevant.

This is a lifecycle decision.

It does not necessarily mean the information must be physically erased.

### B. Explicit user-requested deletion

A user explicitly asks Raven to forget or delete information.

This must enter the deletion workflow and must not be treated as an ordinary low-priority maintenance task.

### C. Other authorized deletion

A deletion may also be required by an authorized account, administrative, or system-level operation.

The authorization and scope must be validated.

## Deletion operation states

- `REQUESTED`
- `VALIDATING`
- `APPROVED`
- `IN_PROGRESS`
- `PROPAGATING`
- `VERIFYING`
- `COMPLETED`
- `PARTIALLY_COMPLETED`
- `FAILED`
- `REQUIRES_RECONCILIATION`

## Algorithm

**Input:**

- Deletion or forgetting request.
- User and ownership context.
- Target memory references or query criteria.
- Authorization context.
- Retention constraints.

**Output:**

- Deletion operation.
- Affected record inventory.
- Propagation plan.
- Operation status.

### Processing steps

1. Receive the request.
2. Identify the requesting identity.
3. Validate authorization.
4. Determine whether the request is policy-driven forgetting or explicit deletion.
5. Identify the exact target scope.
6. Resolve affected memories and derived dependencies.
7. Build a deletion dependency inventory.
8. Create a durable deletion operation record.
9. Establish a deletion version or tombstone.
10. Dispatch deletion propagation.
11. Verify affected storage and derived representations.
12. Record completion or unresolved failures.

### Pseudocode

```text
FUNCTION orchestrate_memory_forgetting(request):

    validate_request(request)

    authorization = validate_deletion_authorization(request)

    IF NOT authorization.allowed:
        RETURN ACCESS_DENIED

    IF request.type == POLICY_FORGETTING:
        RETURN apply_lifecycle_policy(request)

    targets = resolve_deletion_targets(request)

    dependencies = find_all_dependent_records(targets)

    operation = create_deletion_operation(
        request,
        targets,
        dependencies
    )

    create_deletion_tombstones(operation)

    dispatch_deletion_propagation(operation)

    RETURN operation.status
```

## Deletion safety rules

- Never delete records belonging to another user.
- Do not use fuzzy similarity alone to determine destructive deletion scope.
- Ambiguous targets must be resolved before destructive action.
- Preserve unrelated records.
- Deletion operations must be idempotent.
- Partial failures must remain visible.
- Do not report deletion as complete before verification.
- Explicit deletion must take priority over ordinary consolidation jobs.
- Derived records must not retain deleted information.

---

# 11. 6.5.9 — Deletion Propagation & Verification

## Purpose

Ensure deletion reaches every relevant representation of the target information.

This algorithm is responsible for propagation and confirmation.

## Dependency inventory

Deletion must consider:

| Data representation | Required handling |
|---|---|
| Memory candidates | Delete or invalidate affected candidates |
| Atomic memories | Delete or tombstone target records |
| Memory revisions | Apply the defined deletion policy |
| Episodes | Remove affected membership and revise episode |
| Semantic conclusions | Recalculate or invalidate affected conclusions |
| Profiles | Remove unsupported attributes and refresh |
| Memory relationships | Remove affected relationships |
| Entity mentions | Remove or invalidate affected mentions |
| Embeddings | Delete affected vectors |
| Vector indexes | Remove affected indexed entries |
| Keyword indexes | Remove affected entries |
| Search caches | Invalidate affected cached results |
| Archive content | Apply applicable deletion policy |
| Temporary processing data | Remove affected temporary copies |
| Backups | Apply backup lifecycle and deletion reconciliation policy |

## Deletion strategy

Use a hybrid strategy:

1. Durable deletion operation record.
2. Tombstone or deletion marker.
3. Owner-controlled propagation.
4. Independent verification.
5. Reconciliation of failed components.
6. Backup restoration safeguards.

A tombstone prevents deleted records from being reintroduced through delayed processing or restoration.

## Algorithm

**Input:**

- Deletion operation.
- Target references.
- Dependency inventory.
- Storage and indexing interfaces.
- Deletion policy.

**Output:**

- Propagation results.
- Verification results.
- Final deletion status.

### Processing steps

1. Load the deletion operation.
2. Validate the operation and target scope.
3. Retrieve its dependency inventory.
4. Mark targets as unavailable for normal retrieval.
5. Propagate deletion to authoritative records.
6. Propagate deletion to derived records.
7. Remove associated embeddings and index entries.
8. Invalidate affected caches.
9. Apply the configured archive and backup handling policy.
10. Verify every required target.
11. Retry or reconcile failed components.
12. Complete only when required verification conditions are met.

### Pseudocode

```text
FUNCTION propagate_and_verify_deletion(operation):

    validate_operation(operation)

    mark_targets_unavailable(operation.targets)

    FOR EACH dependency IN operation.dependencies:

        result = delete_or_invalidate(dependency)

        record_propagation_result(
            operation,
            dependency,
            result
        )

    invalidate_affected_caches(operation)

    reconcile_backup_deletion_state(operation)

    verification = verify_deletion_scope(operation)

    IF verification.all_required_targets_confirmed:
        mark_operation_completed(operation)

    ELSE IF verification.retryable_failures_exist:
        mark_operation_requires_reconciliation(operation)

    ELSE:
        mark_operation_partially_completed(operation)

    RETURN operation.status
```

## Backup handling

Backups require special treatment because they may contain older copies of deleted information.

The architecture must ensure that restoring a backup does not silently reintroduce deleted memories.

Use a durable deletion ledger or equivalent mechanism that can be replayed after restoration.

Backup retention and physical purge timing must follow the applicable operational and legal policies. Do not assume that deleting a live record automatically erases every backup copy immediately.

## Verification requirements

A deletion operation is not complete merely because the primary database record was removed.

Verification must cover all required representations and dependencies.

Where a storage system cannot immediately confirm physical erasure, the operation must report the actual state rather than claiming complete deletion.

---

# 12. 6.5.10 — Consolidation Integrity & Recovery

## Purpose

Protect consolidation and maintenance operations from partial writes, concurrency issues, duplicate processing, and inconsistent derived data.

## Common failure cases

- Consolidation job interrupted midway.
- Duplicate maintenance jobs execute concurrently.
- Source memory changes during consolidation.
- A profile refresh uses stale source versions.
- Embedding generation fails.
- An index update succeeds while the primary update fails.
- Deletion propagation is partially completed.
- A backup restoration reintroduces previously deleted information.
- Episode membership references a missing memory.
- Semantic conclusions reference outdated evidence.

## Algorithm

**Input:**

- Maintenance job.
- Source record versions.
- Existing derived records.
- Checkpoints.
- Operation history.
- Validation rules.

**Output:**

- Verified maintenance result.
- Recovery checkpoint.
- Reconciliation job where needed.
- Final operation status.

### Processing steps

1. Load the maintenance job.
2. Validate its execution state.
3. Check idempotency and concurrency constraints.
4. Capture source record versions.
5. Execute the maintenance operation.
6. Validate generated or updated records.
7. Check whether source versions changed during processing.
8. Reject or re-evaluate stale derived output.
9. Persist valid results.
10. Record a checkpoint.
11. Verify derived-data consistency.
12. Mark the job complete or schedule recovery.

### Pseudocode

```text
FUNCTION execute_maintenance_safely(job):

    validate_job(job)

    IF job.already_completed:
        RETURN EXISTING_RESULT

    checkpoint = load_latest_checkpoint(job)

    source_versions = capture_source_versions(job.scope)

    result = execute_operation(job, checkpoint)

    validate_result(result)

    IF source_versions_changed(job.scope):
        result = re_evaluate_against_latest_sources(result)

    IF NOT result.is_valid:
        rollback_or_invalidate_partial_output(result)

        RETURN NEEDS_RECOVERY

    persist_result(result)

    save_checkpoint(job, result)

    verify_derived_consistency(result)

    mark_job_completed(job)

    RETURN result
```

## Recovery principles

- Preserve successfully completed work.
- Retry only failed or incomplete steps.
- Do not duplicate destructive operations.
- Use optimistic concurrency and version validation.
- Do not publish derived records before validation.
- Rebuild derived data from authoritative sources when necessary.
- Preserve deletion tombstones during recovery.
- Never restore a deleted record into active retrieval.

---

# 13. Shared Maintenance Data Contract

Maintenance operations should expose a consistent conceptual contract.

```text
MaintenanceOperation:
    operation_id
    user_id
    operation_type
    target_scope
    target_references
    trigger_type
    priority
    idempotency_key
    source_versions
    status
    checkpoint_reference
    created_at
    started_at
    completed_at
    processing_version
    error_reference
    result_reference
```

This is a logical contract, not a finalized database schema.

Operation-specific fields may be added where needed.

## Required operational properties

Every maintenance operation must support:

- Ownership validation.
- Idempotency.
- Version awareness.
- Bounded execution.
- Status tracking.
- Checkpointing where necessary.
- Failure classification.
- Recovery or reconciliation.
- Provenance.
- Auditability.

---

# 14. Security & Privacy Requirements

1. Maintenance jobs must enforce user-level data isolation.
2. Cross-user shared entities must not expose private memory content.
3. Deletion must validate the requester's authority.
4. Destructive operations must have a traceable operation record.
5. Sensitive memory content must not be exposed in operational logs.
6. Derived records must inherit appropriate access restrictions.
7. Temporary maintenance outputs must follow their defined retention policy.
8. Embeddings and indexes must be treated as potentially sensitive derived data.
9. Backup restoration must respect deletion records.
10. Failed deletion propagation must remain visible until reconciled.

---

# 15. Evaluation Metrics

The following metrics will be evaluated during Phase 12.

| Area | Metric |
|---|---|
| Scheduling | Duplicate maintenance job rate |
| Scheduling | Job completion rate |
| Freshness | Stale-memory detection precision and recall |
| Retention | Incorrect retention decision rate |
| Episodes | Episode membership accuracy |
| Episodes | Unrelated-memory grouping rate |
| Semantic consolidation | Evidence support accuracy |
| Semantic consolidation | Unsupported conclusion rate |
| Profiles | Profile freshness |
| Profiles | Source-to-profile consistency |
| Forgetting | Deletion propagation completeness |
| Forgetting | Deletion verification success |
| Recovery | Recovery success rate |
| Integrity | Orphaned derived-record rate |
| Efficiency | Maintenance processing cost |

Numerical acceptance targets will be established during Phase 12 evaluation. They are not assumed to be finalized here.

---

# 16. Dependencies

This phase depends on:

- Phase 2 — Memory Engine Architecture.
- Phase 5.3 — Core Entities & Relationships.
- Phase 5.4 — Memory Engine Data Models.
- Phase 5.8–5.10 — Relationships, Lifecycle, Retention, and Deletion.
- Phase 6.1 — Shared Algorithm Framework.
- Phase 6.2 — Memory Ingestion & Extraction.
- Phase 6.3 — Memory Resolution.
- Phase 6.4 — Memory Retrieval.

---

# 17. Phase 6.5 Completion Criteria

The algorithm specification is considered complete when:

- Maintenance scheduling is defined.
- Freshness and decay are independently evaluated.
- Retention decisions preserve historical value.
- Episode formation preserves atomic memory authority.
- Semantic consolidation preserves evidence references.
- Profiles can be incrementally refreshed.
- Stale memories can be detected without destructive automatic changes.
- Explicit forgetting enters a controlled deletion workflow.
- Deletion propagation covers derived and secondary representations.
- Backup restoration cannot silently reintroduce deleted memories.
- Consolidation operations support idempotency and recovery.
- Security and privacy constraints are defined.

**Completion status:** Specification complete when documented and reviewed. Implementation, numerical calibration, database realization, and test verification remain future work.

---

# 18. Memory Engine Algorithm Design — Overall Status

The Memory Engine algorithm design is organized into four major groups:

| Phase | Algorithm group | File |
|---|---|---|
| 6.2 | Memory Ingestion & Extraction | `01-memory-ingestion-extraction.md` |
| 6.3 | Memory Resolution | `02-memory-resolution.md` |
| 6.4 | Memory Retrieval | `03-memory-retrieval.md` |
| 6.5 | Memory Consolidation & Maintenance | `04-memory-consolidation-maintenance.md` |

The Memory Engine algorithm design is architecturally covered once all algorithms in these four documents have been completed and reviewed.

The next stage is **Phase 6.6 — Research Engine Algorithms**, beginning with query understanding, research decomposition, and information discovery.

**Important:** This document specifies intended behavior. It does not claim that the algorithms, database structures, background jobs, deletion mechanisms, or tests have been implemented.
