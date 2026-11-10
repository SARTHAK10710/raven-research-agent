# Phase 6.9 — Research Memory Management & Session Lifecycle Algorithms

**Project:** Raven Research Agent  
**Phase:** 6 — Algorithms & Processing Design  
**Subphase:** 6.9 — Research Memory Management & Session Lifecycle  
**Status:** Architecture and algorithm specification  
**Optimization Priority:** Quality first  
**Processing Approach:** Hybrid — deterministic rules, conventional NLP/statistical methods, and selective non-generative ML

---

## 1. Purpose

Research should not disappear when an individual execution finishes.

Raven must preserve useful research so that future requests can:

- Retrieve previously discovered findings.
- Continue an existing investigation.
- Refresh outdated information.
- Compare current findings with historical findings.
- Identify changes in previously researched entities.
- Avoid unnecessary repeated discovery.
- Preserve the evidence and sources behind previous conclusions.

The Research Engine therefore requires a persistent research lifecycle.

This phase defines the algorithms responsible for managing research sessions, snapshots, findings, sources, evidence, updates, retention, and recovery.

### Core principles

1. Research sessions have persistent identities.
2. Research snapshots preserve the state of findings at a particular point in time.
3. New research must not silently overwrite historical snapshots.
4. Materially changed research objectives should create linked sessions.
5. Incremental updates should preserve unchanged findings.
6. Every finding must retain its evidence and provenance.
7. Research history must distinguish historical truth from current applicability.
8. Research data remains owned by the Research Engine.
9. Retention and deletion must follow explicit lifecycle policies.
10. Failed updates must not corrupt previously valid research.

---

# 2. Algorithm Inventory

This document defines nine algorithms.

| ID | Algorithm | Primary responsibility |
|---|---|---|
| 6.9.1 | Research Session Creation & Identity | Create and identify research sessions |
| 6.9.2 | Research Session Matching & Linking | Identify related existing sessions |
| 6.9.3 | Research Snapshot Creation | Preserve point-in-time research state |
| 6.9.4 | Incremental Research Updates | Update only affected research |
| 6.9.5 | Finding & Evidence Persistence | Persist research results and provenance |
| 6.9.6 | Historical Version Management | Preserve changes across research versions |
| 6.9.7 | Research Retention & Expiration | Manage research lifecycle and retention |
| 6.9.8 | Research Session Deduplication & Integrity | Prevent duplication and maintain consistency |
| 6.9.9 | Research Recovery & Reconciliation | Recover interrupted research operations |

---

# 3. 6.9.1 — Research Session Creation & Identity

## Purpose

Create a persistent identity for every distinct research objective.

A research session represents an investigation, not merely an individual search request.

Multiple executions may contribute to the same research session.

For example:

Initial request:
"Research Company X."

Follow-up:
"Find its latest funding information."

Further follow-up:
"Compare its current products with its competitors."

These requests may belong to one continuing research session if they retain the same overall objective.

## Session identity principles

A research session should contain:

- Unique session identifier.
- User ownership.
- Research objective.
- Primary entities.
- Research scope.
- Research intent.
- Creation timestamp.
- Last activity timestamp.
- Current status.
- Latest snapshot reference.
- Session version.

The session identity must remain stable across incremental updates.

## Session states

- `CREATED`
- `ACTIVE`
- `PARTIALLY_COMPLETE`
- `COMPLETE`
- `PAUSED`
- `FAILED`
- `CANCELLED`
- `ARCHIVED`

## Algorithm

**Input:**

- Research request.
- Enriched query.
- Research plan.
- User and execution context.
- Existing session reference, if available.

**Output:**

- Research session.
- Session identity.
- Initial session metadata.
- Session creation status.

### Processing steps

1. Receive the research request.
2. Validate user and execution ownership.
3. Determine whether an existing session reference was supplied.
4. Validate the referenced session.
5. If no suitable session exists, generate a unique session ID.
6. Record the research objective and scope.
7. Store primary entity references.
8. Initialize session state.
9. Create the initial session version.
10. Return the session reference.

### Pseudocode

```text
FUNCTION create_research_session(request):

    validate_request(request)

    validate_user_scope(request.user_id)

    IF request.existing_session_reference:
        session = validate_existing_session(
            request.existing_session_reference
        )

        IF session.is_valid:
            RETURN session

    session_id = generate_unique_session_id()

    session = create_session_record(
        session_id,
        request.user_id,
        request.research_objective,
        request.scope,
        request.entities
    )

    set_session_status(session, ACTIVE)

    RETURN session
```

## Safeguards

- Session identity must be independent of execution identity.
- Different users must not share private research sessions.
- A new execution must not automatically create a new session.
- A session must not be reused solely because two queries have similar wording.
- Session creation must be idempotent where the same creation request is retried.

---

# 4. 6.9.2 — Research Session Matching & Linking

## Purpose

Determine whether a new research request should continue an existing session or create a linked new session.

This is essential for research continuity.

## Matching dimensions

Evaluate:

1. Research objective similarity.
2. Entity identity.
3. Attribute overlap.
4. Scope compatibility.
5. Temporal compatibility.
6. Research intent.
7. Existing session status.
8. Explicit user reference.

## Session relationship types

- `CONTINUES`
- `UPDATES`
- `EXTENDS`
- `RELATED_TO`
- `COMPARISON_WITH`
- `SUPERSEDES`
- `DUPLICATES`

## Matching outcomes

- `EXISTING_SESSION_MATCH`
- `PARTIAL_SESSION_MATCH`
- `RELATED_SESSION_FOUND`
- `NEW_SESSION_REQUIRED`
- `NEEDS_REVIEW`

## Algorithm

**Input:**

- New research request.
- Existing session references.
- Research objective.
- Entity and attribute references.
- Scope and temporal context.

**Output:**

- Matching session reference.
- Session relationship recommendation.
- Matching rationale.

### Processing steps

1. Identify explicit session references.
2. Search for sessions belonging to the same user.
3. Compare research objectives.
4. Compare entity identity.
5. Compare requested attributes.
6. Compare temporal and geographic scope.
7. Evaluate whether the request continues the existing objective.
8. Identify related but distinct sessions.
9. Determine whether to reuse or create a new session.
10. Record the relationship when applicable.

### Pseudocode

```text
FUNCTION match_research_session(request):

    IF request.explicit_session_reference:
        RETURN validate_explicit_session_reference(request)

    sessions = find_user_scoped_sessions(request.user_id)

    candidates = []

    FOR EACH session IN sessions:

        objective_match = compare_objectives(request, session)

        entity_match = compare_entities(request, session)

        scope_match = compare_scope(request, session)

        temporal_match = compare_temporal_context(
            request,
            session
        )

        candidates.append(
            evaluate_session_match(
                objective_match,
                entity_match,
                scope_match,
                temporal_match
            )
        )

    decision = determine_session_relationship(candidates)

    RETURN decision
```

## Important decision rules

### Continue the same session

When the request:

- Clearly references the existing investigation.
- Updates information within the same objective.
- Adds relevant attributes to an ongoing investigation.
- Requests a follow-up that naturally extends the existing research.

### Create a linked new session

When the request:

- Changes the research objective materially.
- Introduces a distinct investigation.
- Requires a separate historical record.
- Changes scope so significantly that combining findings would be misleading.

### Ask for clarification

When multiple sessions are plausible and choosing the wrong session would materially affect the result.

---

# 5. 6.9.3 — Research Snapshot Creation

## Purpose

Preserve a point-in-time representation of a research session.

Snapshots allow Raven to compare research across different executions and time periods.

A snapshot must preserve the state of research at the time it was created.

## Snapshot contents

A snapshot should reference:

- Research session.
- Snapshot identifier.
- Snapshot version.
- Research objective at that point.
- Included findings.
- Evidence references.
- Source references.
- Verification states.
- Research completion status.
- Creation timestamp.
- Processing version.

Snapshots should primarily use references to existing records rather than duplicating large amounts of source content.

## Snapshot states

- `CREATED`
- `VALIDATED`
- `PARTIALLY_COMPLETE`
- `SUPERSEDED`
- `INVALIDATED`

Invalidation means the snapshot should no longer be treated as a valid current representation. It does not mean its historical record must be erased.

## Algorithm

**Input:**

- Research session.
- Completed or partially completed findings.
- Evidence references.
- Source records.
- Verification metadata.

**Output:**

- Research snapshot.
- Snapshot version.
- Snapshot completeness status.

### Processing steps

1. Load the research session.
2. Validate session ownership.
3. Retrieve eligible findings.
4. Retrieve associated source and evidence references.
5. Capture verification and confidence states.
6. Capture research completion status.
7. Assign a new snapshot version.
8. Create the snapshot record.
9. Validate snapshot references.
10. Update the session's latest snapshot reference.

### Pseudocode

```text
FUNCTION create_research_snapshot(session):

    validate_session(session)

    findings = retrieve_session_findings(session)

    evidence = retrieve_finding_evidence(findings)

    sources = retrieve_finding_sources(findings)

    verification = retrieve_verification_states(findings)

    version = generate_next_snapshot_version(session)

    snapshot = create_snapshot(
        session,
        findings,
        evidence,
        sources,
        verification,
        version
    )

    validate_snapshot_integrity(snapshot)

    update_latest_snapshot_reference(session, snapshot)

    RETURN snapshot
```

## Snapshot safeguards

- Do not overwrite older snapshots.
- Preserve partially completed snapshots when useful.
- Do not mark incomplete research as complete.
- Preserve historical verification states.
- Snapshot references must resolve to the intended records.
- A new snapshot must not silently change the contents of an older snapshot.

---

# 6. 6.9.4 — Incremental Research Updates

## Purpose

Update existing research without repeating the entire investigation unnecessarily.

A new research request may require refreshing only a subset of previously stored findings.

For example, if Raven previously researched:

- Company products.
- Company headquarters.
- Funding history.
- Current pricing.

A later request asking for updated pricing should not automatically repeat every research task.

## Update categories

- `NEW_FINDING`
- `UPDATED_FINDING`
- `UNCHANGED_FINDING`
- `SUPERSEDED_FINDING`
- `CONFLICTING_FINDING`
- `REQUIRES_REVALIDATION`
- `NO_LONGER_IN_SCOPE`

## Algorithm

**Input:**

- Existing research session.
- Latest snapshot.
- New research request.
- New candidate findings.
- Existing evidence references.

**Output:**

- Incremental update plan.
- Updated findings.
- Unchanged finding references.
- Conflict and revalidation records.

### Processing steps

1. Load the latest valid snapshot.
2. Validate session and snapshot ownership.
3. Compare the new objective with the existing scope.
4. Identify requested attributes.
5. Retrieve relevant existing findings.
6. Compare new findings with existing records.
7. Identify new, unchanged, updated, and conflicting findings.
8. Revalidate time-sensitive information where necessary.
9. Preserve unchanged findings.
10. Create revisions for material changes.
11. Generate a new snapshot after validation.

### Pseudocode

```text
FUNCTION update_research_incrementally(session, new_findings):

    snapshot = load_latest_valid_snapshot(session)

    validate_snapshot(snapshot)

    existing_findings = load_snapshot_findings(snapshot)

    update_plan = compare_finding_sets(
        existing_findings,
        new_findings
    )

    FOR EACH change IN update_plan:

        IF change.type == UNCHANGED:
            preserve_existing_reference(change)

        ELSE IF change.type == NEW:
            create_new_finding(change)

        ELSE IF change.type == UPDATED:
            create_finding_revision(change)

        ELSE IF change.type == CONFLICT:
            create_conflict_record(change)

        ELSE IF change.type == REVALIDATION:
            schedule_revalidation(change)

    validate_incremental_update(update_plan)

    RETURN update_plan
```

## Important rules

- Do not overwrite historical findings.
- Do not treat newer publication dates as automatic proof of correctness.
- Preserve the previous finding and its evidence.
- Update only the relevant parts of the research.
- Revalidate dependent conclusions when source findings change.
- A partial update must remain marked as partial until its requirements are satisfied.

---

# 7. 6.9.5 — Finding & Evidence Persistence

## Purpose

Persist research findings, sources, and evidence in a consistent and traceable manner.

The Research Engine owns these records.

The Orchestrator may receive references and structured outputs but does not become the owner of research findings.

## Persistence requirements

Each persisted finding should retain:

- Finding identity.
- Research session reference.
- Snapshot association.
- Source references.
- Evidence references.
- Verification status.
- Confidence classification.
- Temporal context.
- Processing version.
- Record lifecycle state.

Sources and evidence should remain independently identifiable.

## Persistence strategy

Use a controlled write process:

1. Validate records.
2. Validate ownership.
3. Validate references.
4. Persist source and evidence records.
5. Persist findings.
6. Persist snapshot associations.
7. Verify consistency.
8. Commit the operation.

The exact transaction and storage implementation is deferred to infrastructure selection.

## Algorithm

**Input:**

- Qualified findings.
- Source records.
- Evidence records.
- Research session.
- Snapshot context.

**Output:**

- Persisted records.
- Record references.
- Persistence status.

### Processing steps

1. Validate research session.
2. Validate user ownership.
3. Validate finding structure.
4. Validate source references.
5. Validate evidence references.
6. Check idempotency.
7. Persist missing source and evidence records.
8. Persist findings and their associations.
9. Persist snapshot membership.
10. Verify record integrity.
11. Return persistence results.

### Pseudocode

```text
FUNCTION persist_research_results(session, results):

    validate_session_ownership(session)

    validate_research_results(results)

    operation = begin_persistence_operation()

    FOR EACH source IN results.sources:
        persist_source_if_missing(source)

    FOR EACH evidence IN results.evidence:
        persist_evidence_if_missing(evidence)

    FOR EACH finding IN results.findings:
        persist_finding_idempotently(finding)

    persist_snapshot_associations(results)

    integrity = verify_persisted_references(results)

    IF NOT integrity.valid:
        recover_or_rollback(operation)
        RETURN PERSISTENCE_FAILED

    commit_persistence_operation(operation)

    RETURN PERSISTED
```

## Safeguards

- Avoid duplicate records on retry.
- Do not persist findings without valid session ownership.
- Do not lose evidence references.
- Do not report persistence success before verification.
- Preserve partial persistence status where full recovery is not possible.

---

# 8. 6.9.6 — Historical Version Management

## Purpose

Maintain the historical evolution of research findings and conclusions.

Research information can change over time.

For example:

- Product pricing changes.
- A company announces new funding.
- A reported statistic is corrected.
- A source updates an earlier article.
- A previous conclusion is invalidated by new evidence.

Raven must preserve the historical record instead of silently replacing it.

## Versioning model

Use:

- Stable finding identity.
- Immutable finding revisions.
- Snapshot versions.
- Supersession relationships.
- Valid-time context.
- Transaction-time context.

### Valid time

The period during which the finding describes the real-world state.

### Transaction time

The period during which Raven stored or recognized the finding.

These two timelines may differ.

For example, a report published in November may describe a company event that occurred in September.

## Algorithm

**Input:**

- Existing finding.
- New finding.
- Existing revision history.
- Evidence and temporal metadata.

**Output:**

- New finding revision.
- Supersession relationship.
- Updated historical timeline.

### Processing steps

1. Identify the existing finding.
2. Compare new and existing values.
3. Determine whether the change is material.
4. Evaluate temporal context.
5. Identify whether the new finding corrects, updates, or supersedes the previous finding.
6. Preserve the previous revision.
7. Create a new revision.
8. Record the relationship.
9. Update the current finding reference.
10. Validate historical consistency.

### Pseudocode

```text
FUNCTION manage_finding_version(existing, incoming):

    validate_finding_identity(existing, incoming)

    comparison = compare_finding_versions(
        existing,
        incoming
    )

    IF comparison.is_identical:
        RETURN NO_CHANGE

    relationship = classify_version_relationship(
        existing,
        incoming
    )

    preserve_existing_revision(existing)

    new_revision = create_finding_revision(
        incoming,
        relationship
    )

    link_revision_history(
        existing,
        new_revision
    )

    validate_temporal_consistency(new_revision)

    RETURN new_revision
```

## Historical integrity rules

- Never silently overwrite a historical finding.
- Preserve source and evidence references for each revision.
- Distinguish corrections from genuine real-world changes.
- Preserve the previous validity period.
- Maintain the distinction between what was known at a particular time and what is known now.
- Historical queries must be able to retrieve appropriate previous versions.

---

# 9. 6.9.7 — Research Retention & Expiration

## Purpose

Determine how research records should be retained over time.

Not every piece of retrieved content requires permanent storage.

However, important findings and their evidence must remain traceable according to the applicable retention policy.

## Data retention categories

| Data type | Default retention approach |
|---|---|
| Research session metadata | Persistent |
| Research snapshots | Persistent according to retention policy |
| Qualified findings | Persistent |
| Source URLs and metadata | Persistent |
| Evidence excerpts | Selective persistence |
| Full retrieved webpage content | Temporary by default |
| Temporary parser output | Temporary |
| Intermediate extraction artifacts | Temporary unless needed |
| Verification records | Retained with associated findings |
| Failed execution artifacts | Limited retention based on recovery needs |

## Retention dimensions

Evaluate:

- Research importance.
- Historical value.
- User instructions.
- Legal and operational constraints.
- Research reuse potential.
- Data sensitivity.
- Storage policy.
- Dependency relationships.

## Algorithm

**Input:**

- Research record.
- Record category.
- Retention policy.
- User instructions.
- Dependency references.

**Output:**

- Retention classification.
- Expiration recommendation.
- Lifecycle action.

### Processing steps

1. Identify the record type.
2. Retrieve the applicable retention policy.
3. Evaluate research importance and historical value.
4. Identify dependencies.
5. Check explicit user instructions.
6. Check applicable preservation requirements.
7. Determine whether the record should remain active, archived, expired, or eligible for deletion.
8. Record the decision.
9. Trigger cleanup only when authorized.

### Pseudocode

```text
FUNCTION evaluate_research_retention(record):

    policy = get_retention_policy(record.type)

    dependencies = find_record_dependencies(record)

    IF record.has_explicit_preservation_instruction:
        RETURN RETAIN

    IF dependencies.require_record:
        RETURN RETAIN_OR_RESTRUCTURE_DEPENDENCIES

    decision = apply_retention_policy(
        record,
        policy
    )

    RETURN decision
```

## Retention safeguards

- Do not delete findings merely because they are old.
- Do not remove evidence required to understand a historical conclusion.
- Full source content may be temporary while its metadata and selected evidence remain persistent.
- Expiration must not silently break snapshot integrity.
- Explicit deletion requests must use the controlled deletion workflow.
- Backup and archive policies must be respected.

---

# 10. 6.9.8 — Research Session Deduplication & Integrity

## Purpose

Prevent unnecessary duplication and ensure that session records, snapshots, findings, and evidence remain internally consistent.

## Deduplication dimensions

- Same user and research objective.
- Same entity and scope.
- Same source URL or publication.
- Same underlying content.
- Same finding and contextual attributes.
- Same evidence origin.

Deduplication must not merge genuinely different investigations.

## Integrity checks

- Session ownership.
- Snapshot references.
- Finding-to-session associations.
- Finding-to-evidence references.
- Source references.
- Version ordering.
- Temporal consistency.
- Session status consistency.
- Supersession relationships.

## Algorithm

**Input:**

- Research session.
- Snapshot records.
- Findings.
- Source and evidence references.
- Integrity rules.

**Output:**

- Duplicate candidates.
- Integrity findings.
- Repair or reconciliation recommendations.

### Processing steps

1. Load the session and associated records.
2. Validate user ownership.
3. Check for duplicate session references.
4. Check duplicate source records.
5. Check equivalent findings.
6. Compare context before merging or linking records.
7. Validate snapshot membership.
8. Validate evidence relationships.
9. Detect orphaned or inconsistent records.
10. Produce an integrity report.
11. Trigger safe repairs where permitted.

### Pseudocode

```text
FUNCTION validate_research_integrity(session):

    validate_session_ownership(session)

    records = load_session_records(session)

    duplicates = identify_duplicate_records(records)

    references = validate_all_references(records)

    versions = validate_version_ordering(records)

    temporal = validate_temporal_relationships(records)

    issues = collect_integrity_issues(
        duplicates,
        references,
        versions,
        temporal
    )

    RETURN {
        issues,
        repair_recommendations
    }
```

## Safeguards

- Similar findings must not automatically be merged.
- Historical snapshots must remain immutable.
- Independent sources must retain independent identities.
- Repairs must be idempotent.
- Destructive merges require sufficient identity and context evidence.
- Unresolved ambiguity must be preserved for review.

---

# 11. 6.9.9 — Research Recovery & Reconciliation

## Purpose

Recover research operations interrupted by failures, timeouts, cancellations, or partial persistence.

The Research Engine must preserve completed work and continue safely where possible.

## Common failure cases

- Research execution interrupted.
- Source retrieval partially completed.
- Extraction succeeds but persistence fails.
- Snapshot creation fails.
- Verification is interrupted.
- Incremental update conflicts with a newer version.
- A source becomes unavailable during refresh.
- Duplicate operations execute concurrently.
- A previous snapshot becomes inconsistent with updated records.

## Algorithm

**Input:**

- Research session.
- Operation status.
- Latest valid snapshot.
- Checkpoint.
- Processing history.
- Current record versions.

**Output:**

- Recovery decision.
- Reconciled research state.
- Updated operation status.
- Recovery report.

### Processing steps

1. Identify the interrupted operation.
2. Validate session ownership.
3. Load the latest valid checkpoint.
4. Identify successfully completed subtasks.
5. Preserve valid completed results.
6. Identify failed or incomplete operations.
7. Check for newer source or finding versions.
8. Resume only necessary work.
9. Revalidate affected findings.
10. Reconcile persistence and snapshot state.
11. Verify the recovered session.
12. Record the recovery outcome.

### Pseudocode

```text
FUNCTION recover_research_session(session):

    validate_session(session)

    checkpoint = load_latest_valid_checkpoint(session)

    completed = identify_completed_work(checkpoint)

    incomplete = identify_incomplete_work(session)

    preserve_completed_results(completed)

    FOR EACH task IN incomplete:

        IF task.has_newer_valid_result:
            reconcile_with_newer_result(task)
        ELSE:
            resume_task(task)

    validate_recovered_records(session)

    update_session_status(session)

    RETURN recovery_result
```

## Recovery safeguards

- Do not rerun completed work unnecessarily.
- Do not overwrite newer valid results.
- Preserve previous snapshots.
- Use idempotency for persistence and update operations.
- Do not mark a session complete while required work remains incomplete.
- Keep recovery status distinct from successful research completion.

---

# 12. Research Session Lifecycle

The following lifecycle summarizes how the algorithms work together.

```text
Research Request
       |
       v
Session Matching
       |
       +---- Existing Session ----+
       |                          |
       v                          v
Create New Session          Continue Existing
       |                          |
       +------------+-------------+
                    |
                    v
             Research Execution
                    |
                    v
          Findings & Evidence
                    |
                    v
              Verification
                    |
                    v
             Persistence
                    |
                    v
          Snapshot Creation
                    |
                    v
            Session Update
                    |
          +---------+---------+
          |                   |
          v                   v
     More Research         Complete
          |                   |
          v                   v
     New Snapshot          Retention
```

This is a logical lifecycle, not an implementation-specific execution diagram.

---

# 13. Research Persistence Data Contract

The following is a conceptual contract.

```text
ResearchSession:
    session_id
    user_id
    research_objective
    primary_entities
    research_scope
    status
    latest_snapshot_id
    session_version
    created_at
    updated_at

ResearchSnapshot:
    snapshot_id
    session_id
    snapshot_version
    finding_references
    source_references
    evidence_references
    verification_state
    completion_status
    created_at

FindingRevision:
    revision_id
    finding_id
    session_id
    snapshot_id
    revision_number
    finding_data
    evidence_references
    valid_time
    transaction_time
    revision_relationship
    created_at
```

These are logical contracts, not finalized database schemas.

The Research Engine remains the owner of these records.

---

# 14. Security & Privacy Requirements

1. Research sessions must be user-scoped.
2. Cross-session references must be validated.
3. Snapshot access must follow session ownership.
4. Research records must not expose private Memory Engine content.
5. Source and evidence references must preserve their access boundaries.
6. Retention decisions must follow applicable policies.
7. Explicit deletion must propagate through dependent records.
8. Recovery operations must preserve deletion state.
9. Historical snapshots must not bypass authorization.
10. Logs must not unnecessarily duplicate sensitive source content.

---

# 15. Evaluation Metrics

These metrics will be evaluated during Phase 12.

| Area | Metric |
|---|---|
| Session management | Correct session matching rate |
| Session management | Incorrect session reuse rate |
| Linking | Session relationship accuracy |
| Snapshots | Snapshot integrity |
| Updates | Incremental update precision |
| Updates | Unnecessary rediscovery rate |
| Persistence | Persistence success rate |
| Versioning | Historical version integrity |
| Retention | Incorrect expiration rate |
| Deduplication | Duplicate detection accuracy |
| Integrity | Orphaned record rate |
| Recovery | Recovery success rate |
| Reliability | Data loss rate |
| Consistency | Snapshot-to-finding consistency |

Numerical targets will be established during Phase 12.

---

# 16. Dependencies

This phase depends on:

- Phase 3 — Research Engine Architecture.
- Phase 5.3 — Core Entities & Relationships.
- Phase 5.5 — Research Engine Data Models.
- Phase 5.8–5.10 — Relationships, Lifecycle, Retention, and Deletion.
- Phase 6.1 — Shared Algorithm Framework.
- Phase 6.6 — Query Understanding & Information Discovery.
- Phase 6.7 — Content Extraction & Fact Normalization.
- Phase 6.8 — Source Evaluation & Verification.

---

# 17. Phase 6.9 Completion Criteria

The specification is complete when:

- Research sessions have persistent identities.
- Related requests can continue existing sessions.
- Distinct objectives can create linked sessions.
- Snapshots preserve point-in-time research state.
- Incremental updates preserve unchanged findings.
- Sources and evidence remain traceable.
- Historical revisions are preserved.
- Retention and expiration policies are defined.
- Deduplication does not destroy distinct research.
- Recovery preserves valid completed work.
- Research ownership and privacy boundaries are enforced.

**Completion status:** Specification complete when documented and reviewed. Persistence implementation, recovery implementation, and testing remain future work.

---

# 18. Next Algorithm Group

**Phase 6.10 — Research Retrieval, Comparison & Synthesis**

The next document will define:

1. Research query retrieval.
2. Session and snapshot selection.
3. Finding retrieval.
4. Evidence-aware ranking.
5. Cross-source comparison.
6. Attribute comparison.
7. Timeline and trend analysis.
8. Research synthesis.
9. Final research output validation.

Phase 6.9 defines how research is stored and maintained. Phase 6.10 defines how Raven retrieves that research and turns it into useful answers.

**Important:** This document specifies intended algorithms. It does not claim that session storage, snapshots, persistence, retention, or recovery mechanisms have been implemented.
