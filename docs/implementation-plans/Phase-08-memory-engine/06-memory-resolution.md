# Phase 8.6 — Memory Resolution Implementation Plan

## 1. Objective

Implement the Memory Engine's memory resolution system.

The resolution system receives validated memory candidates from Phase 8.4, along with relevant entity and relationship information from Phase 8.5, and determines how each candidate should relate to existing memories.

It must identify whether an incoming candidate:

- Represents a new memory.
- Duplicates an existing memory.
- Is related to an existing memory.
- Supports an existing memory.
- Corrects an existing memory.
- Updates an existing memory.
- Contradicts an existing memory.
- Supersedes an existing memory.
- Requires manual or deferred review.
- Does not require any change.

### Primary objectives

- Detect potential duplicate memories.
- Identify related memories.
- Detect contradictions.
- Identify corrections and updates.
- Preserve historical information.
- Prevent unintended memory duplication.
- Resolve candidates using evidence and context.
- Maintain provenance and revision history.
- Produce explicit resolution decisions.
- Support safe, idempotent processing.

## 2. Architecture references

Claude Code must review:

1. `PROJECT_ARCHITECTURE.md`
2. `docs/architecture/` — Memory Engine architecture.
3. `docs/data-models/` — approved Memory Engine data models.
4. `docs/algorithms/memory/02-memory-resolution.md`
5. `docs/algorithms/memory/01-memory-ingestion-extraction.md`
6. `docs/algorithms/shared/01-shared-algorithm-framework.md`
7. `docs/technical-decisions/01-baseline-technology-stack.md`
8. `docs/technical-decisions/02-database-and-storage-architecture.md`
9. `docs/technical-decisions/03-vector-search-and-embedding-infrastructure.md`
10. `docs/implementation-plans/Phase-08-memory-engine/02-database-and-persistence.md`
11. `docs/implementation-plans/Phase-08-memory-engine/04-extraction-and-evaluation.md`
12. `docs/implementation-plans/Phase-08-memory-engine/05-entity-and-relationship-management.md`

The approved Phase 5 models and Phase 6 algorithms are authoritative.

Do not redefine memory revision, candidate lifecycle or relationship semantics independently.

## 3. Scope

### Included

- Candidate-to-memory matching.
- Duplicate detection.
- Related-memory detection.
- Contradiction detection.
- Correction detection.
- Update and progression detection.
- Supersession decisions.
- Resolution decision generation.
- Historical revision preservation.
- Provenance preservation.
- Transactional resolution.
- Concurrency and idempotency controls.
- Resolution quality evaluation.

### Excluded

- Memory retrieval and ranking.
- Final vector indexing.
- Memory consolidation.
- Profile generation.
- Forgetting and deletion execution.
- Document RAG.
- Generative response creation.

These capabilities belong to later milestones or the final Phase 8 architecture review.

## 4. Resolution architecture

Implement the following logical components.

### 4.1 Candidate Matching Engine

Responsibilities:

- Receive a validated memory candidate.
- Identify potentially related existing memories.
- Retrieve relevant entity and relationship context.
- Compare candidate content with existing facts.
- Filter candidates using ownership and temporal context.
- Return potential matches for evaluation.

Use the approved hybrid matching strategy.

Potential matching signals include:

- Semantic similarity.
- Keyword similarity.
- Entity overlap.
- Attribute overlap.
- Temporal compatibility.
- Contextual similarity.
- Existing memory relationships.

Similarity scores must not independently trigger destructive changes.

### 4.2 Duplicate Detection

Determine whether an incoming candidate expresses substantially the same fact as an existing memory.

Consider:

- Meaning.
- Entities.
- Attributes.
- Values.
- Context.
- Temporal information.
- Negation.
- Qualifiers.

Examples:

Existing memory:
"The user is developing Raven using Python."

Incoming candidate:
"Raven is being developed in Python."

These may represent duplicate information.

However:

Existing memory:
"The user plans to learn Python."

Incoming candidate:
"The user is developing Raven using Python."

These are related but not duplicates.

The system must distinguish duplicate facts from facts that merely share similar terminology.

### 4.3 Related Memory Detection

Identify memories that share meaningful context without expressing the same fact.

Examples:

- A project and its technology stack.
- A user goal and a related commitment.
- A decision and the event that resulted from it.

Related memories should remain separate unless the approved resolution policy establishes otherwise.

Create relationship records where supported.

### 4.4 Contradiction Detection

Identify candidate facts that conflict with existing memories.

Consider:

- Different values for the same attribute.
- Conflicting dates.
- Opposing statements.
- Negation.
- Changes in status.
- Different temporal contexts.
- Incompatible entity references.

Example:

Existing memory:
"The user is using PostgreSQL for Raven."

Incoming candidate:
"The user is using MongoDB for Raven."

This should trigger contextual evaluation rather than automatic rejection.

The two statements may represent a genuine technology change, a comparison, a temporary experiment or a contradiction.

Do not assume that different values always indicate a contradiction.

### 4.5 Correction Detection

Identify explicit corrections to previously stored information.

Examples:

- "I previously said Raven used MySQL, but it actually uses PostgreSQL."
- "The earlier date was incorrect."
- "That person is not the project owner."

Explicit corrections must receive high processing priority.

Requirements:

- Identify the original memory being corrected.
- Preserve the correction's source.
- Create a new revision or apply the approved correction lifecycle.
- Preserve the previous version.
- Record the resolution decision.
- Avoid silently overwriting historical information.

### 4.6 Update and Progression Detection

Identify when a new memory reflects a legitimate change in an existing fact.

Examples:

- A project moves from planning to development.
- A goal changes its target date.
- A user changes their technology stack.
- A commitment is completed.
- A previously tentative plan becomes confirmed.

Distinguish changes over time from contradictory observations.

Preserve historical state where the approved data model supports revisions and temporal validity.

### 4.7 Resolution Decision Engine

Produce one of the approved resolution outcomes:

- `CREATE_NEW`
- `MERGE`
- `UPDATE_EXISTING`
- `LINK_EXISTING`
- `SUPERSEDE`
- `NEEDS_REVIEW`
- `REJECT`
- `NO_CHANGE`

Use these outcomes according to the approved algorithm specification.

Do not invent additional outcome values without identifying an actual model gap.

The decision must include its supporting evidence and relevant existing memory references.

## 5. Resolution workflow

Implement the following logical sequence:

1. Receive a validated memory candidate.
2. Verify its ownership and lifecycle state.
3. Retrieve relevant existing memories.
4. Retrieve associated entities and relationships.
5. Generate potential matching candidates.
6. Compare meaning and factual attributes.
7. Evaluate temporal compatibility.
8. Evaluate duplicate likelihood.
9. Evaluate related-memory relationships.
10. Evaluate possible contradictions.
11. Evaluate corrections and updates.
12. Select an appropriate resolution outcome.
13. Validate the proposed change.
14. Persist the resolution transactionally.
15. Preserve previous revisions and provenance.
16. Record the resolution event.
17. Return the resolution result.

If the available evidence is insufficient, use `NEEDS_REVIEW` rather than making an unsupported decision.

## 6. Matching strategy

Use the approved hybrid matching approach.

### Semantic similarity

Use embeddings to identify potentially similar memories.

The embedding system must use the approved technology architecture.

### Keyword similarity

Use lexical matching and normalized text comparison to identify overlapping facts.

### Entity matching

Use entities and aliases managed by Phase 8.5.

### Attribute matching

Compare meaningful attributes, including:

- Subject.
- Predicate.
- Object or value.
- Context.
- Temporal scope.
- Qualifiers.

### Temporal compatibility

Consider whether the candidate and existing memory refer to:

- The same time period.
- Different time periods.
- Current versus historical states.
- Planned versus completed events.

### Contextual evaluation

Consider the surrounding evidence and source information before selecting a resolution outcome.

No single similarity metric should determine memory identity.

## 7. Memory history and revisions

Memory resolution must preserve historical information.

When an existing memory is corrected, updated or superseded:

- Preserve the previous revision.
- Record the new revision.
- Preserve source references.
- Record the reason for the change.
- Preserve applicable temporal information.
- Maintain the relationship between revisions.

Use the approved immutable revision model.

Do not physically overwrite historical revisions.

The current authoritative state must be distinguishable from previous observations and revisions.

## 8. Resolution confidence and review

Resolution confidence must be distinct from the confidence of the original extracted fact.

The implementation must evaluate the strength of the resolution decision using the available evidence.

Examples:

- Strong duplicate evidence may justify a merge.
- A clear explicit correction may justify an update.
- Conflicting temporal contexts may justify separate memories.
- Ambiguous identity may require review.
- Weak similarity alone must not justify merging.

Use the existing review and lifecycle mechanisms.

Do not introduce arbitrary confidence thresholds without documenting their evaluation basis.

## 9. Persistence and transaction safety

Use the approved Phase 8.2 persistence layer.

Requirements:

- Validate all referenced memory and candidate records.
- Enforce ownership.
- Preserve revision history.
- Maintain valid memory relationships.
- Apply resolution changes transactionally.
- Prevent duplicate resolution events.
- Support optimistic concurrency.
- Detect stale revisions.
- Handle concurrent candidates safely.
- Preserve provenance.

### Concurrency handling

If two candidates attempt to modify the same memory concurrently:

1. Detect the version conflict.
2. Reload the latest authoritative revision.
3. Re-evaluate the proposed resolution.
4. Retry only when safe.
5. Otherwise mark the candidate for review.

Never silently apply an update against stale memory state.

### Idempotency

Repeated processing of the same candidate must not create duplicate revisions, relationships or resolution events.

## 10. Failure handling

| Scenario | Expected behavior |
|---|---|
| No matching memory | Evaluate `CREATE_NEW` |
| Strong duplicate evidence | Evaluate `MERGE` |
| Related but distinct fact | Evaluate `LINK_EXISTING` |
| Contradictory values | Evaluate contextual resolution or `NEEDS_REVIEW` |
| Explicit correction | Evaluate `UPDATE_EXISTING` |
| Historical change | Evaluate `SUPERSEDE` where appropriate |
| Insufficient evidence | `NEEDS_REVIEW` |
| Invalid candidate | `REJECT` |
| Candidate already resolved | `NO_CHANGE` or return existing result |
| Concurrent revision conflict | Reload and re-evaluate |
| Database failure | Roll back and record recoverable failure |
| Missing provenance | Prevent unsupported authoritative changes |

Do not convert every contradiction into an update.

Do not convert every similar fact into a merge.

## 11. Testing requirements

### Unit tests

Test:

- Candidate matching.
- Duplicate detection.
- Related-memory detection.
- Contradiction detection.
- Correction detection.
- Update detection.
- Temporal compatibility.
- Resolution outcome selection.
- Resolution confidence.
- Revision creation.

### Component tests

Test:

- Candidate-to-memory resolution.
- Existing memory merge.
- Memory update.
- Memory supersession.
- Relationship creation.
- Revision preservation.
- Provenance association.
- Transaction rollback.
- Idempotent resolution.

### Concurrency tests

Test:

- Two candidates updating the same memory.
- Concurrent duplicate resolution.
- Stale revision updates.
- Retry after version conflict.
- Concurrent resolution of related memories.

### Quality evaluation

Create representative datasets covering:

- Exact duplicates.
- Paraphrased duplicates.
- Related but distinct facts.
- Contradictory values.
- Explicit corrections.
- Historical changes.
- Temporary states.
- Different temporal contexts.
- Negation.
- Ambiguous entities.
- Similar names with different identities.
- Tentative versus confirmed information.

Evaluate:

- Duplicate detection precision.
- Duplicate detection recall.
- False merge rate.
- Contradiction detection quality.
- Correction detection quality.
- Temporal resolution accuracy.
- Revision integrity.
- Provenance completeness.

False merges should receive particular attention because they can corrupt multiple memories.

## 12. Observability

Record structured events for:

- Resolution started.
- Potential matches identified.
- Duplicate detected.
- Contradiction detected.
- Correction identified.
- Resolution decision selected.
- Revision created.
- Memory linked.
- Review required.
- Resolution failed.

Track:

- Candidates resolved.
- Duplicate detection rate.
- Merge rate.
- Update rate.
- Supersession rate.
- Review rate.
- False merge rate from evaluation.
- Concurrency conflict rate.
- Resolution processing latency.

Do not log private memory content unnecessarily.

## 13. Acceptance criteria

Phase 8.6 is complete only when:

- [ ] Candidates can be matched against existing memories.
- [ ] Hybrid matching is implemented.
- [ ] Duplicate and related facts are distinguished.
- [ ] Contradictions can be detected.
- [ ] Corrections can be recognized.
- [ ] Updates and temporal progression can be identified.
- [ ] Resolution decisions follow the approved outcomes.
- [ ] Ambiguous decisions can be deferred for review.
- [ ] Historical revisions are preserved.
- [ ] Provenance is retained.
- [ ] Concurrent changes are handled safely.
- [ ] Resolution is idempotent.
- [ ] Database transactions preserve integrity.
- [ ] Unit and component tests pass.
- [ ] Resolution quality evaluation is available.
- [ ] False merge risks are evaluated.

## 14. Implementation constraints

Claude Code must:

1. Inspect the existing repository before modifying files.
2. Reuse Phase 8.1–8.5 implementations.
3. Follow the approved Phase 5 data models.
4. Follow the Phase 6 memory resolution algorithms.
5. Use the existing candidate and revision models.
6. Keep matching separate from resolution decisions.
7. Never treat similarity as proof of identity.
8. Preserve historical revisions.
9. Preserve provenance.
10. Enforce ownership and concurrency controls.
11. Avoid generative LLM functionality.
12. Avoid implementing document RAG in this milestone.
13. Place implementation code inside `memory-engine/`.
14. Place tests inside `tests/`.
15. Do not proceed to Phase 8.7 automatically.

If the approved data model cannot represent a required resolution operation, report the gap before changing the schema.

## 15. Completion report

Claude Code must provide:

1. Summary of resolution functionality.
2. Files created or modified.
3. Matching methods implemented.
4. Resolution outcomes implemented.
5. Revision and history handling.
6. Concurrency and idempotency handling.
7. Tests executed and exact results.
8. Quality evaluation results.
9. Known limitations.
10. Deviations from architecture.
11. Acceptance criteria status.

Clearly distinguish implemented resolution behavior from evaluation results that have not yet been validated.

## 16. Definition of done

Phase 8.6 is complete when Raven can evaluate new memory candidates against existing memories and make evidence-backed decisions about duplication, relationships, corrections, contradictions and historical updates without silently destroying or corrupting existing information.

**The output is a reliable resolution layer that determines how candidate memories become part of Raven's authoritative memory system.**
