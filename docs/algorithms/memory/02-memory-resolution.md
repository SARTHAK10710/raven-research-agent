# Raven — Memory Resolution

**Project:** Raven  
**Engine:** Memory Engine  
**Phase:** 6.3 — Memory Resolution  
**File:** `02-memory-resolution.md`  
**Directory:** `docs/algorithms/memory/`  
**Status:** Algorithm Specification

---

# 1. Purpose

Memory Resolution defines how Raven processes validated memory candidates in relation to existing memories.

The purpose is to prevent unnecessary duplication, resolve entity references, identify contradictions, handle corrections, maintain historical versions and determine whether a candidate should create a new memory or modify an existing one.

A new candidate must never automatically overwrite an existing memory.

Raven must evaluate the relationship between the new candidate and existing information before making an authoritative change.

## 1.1 Phase 6.3 Responsibilities

- Candidate intake.
- Existing memory matching.
- Exact duplicate detection.
- Semantic similarity analysis.
- Entity resolution.
- Alias management.
- Contradiction detection.
- Memory corrections and updates.
- Historical version management.
- Memory relationship management.
- Resolution decisions.
- Safe promotion into authoritative memory.

## 1.2 Core Resolution Outcomes

A candidate may result in one of the following:

| Outcome | Meaning |
|---|---|
| `CREATE_NEW` | Create a new independent memory |
| `MERGE` | Combine compatible information |
| `UPDATE_EXISTING` | Update an existing memory |
| `LINK_EXISTING` | Link related information without merging |
| `SUPERSEDE` | Replace the current state while preserving history |
| `NEEDS_REVIEW` | Require additional evidence or review |
| `REJECT` | Reject an invalid or unsupported candidate |
| `NO_CHANGE` | Existing information already represents the candidate |

These outcomes must remain distinguishable.

## 1.3 Processing Flow

```text
Validated Memory Candidate
          |
          v
6.3.1 Candidate Intake & Preparation
          |
          v
6.3.2 Duplicate Memory Detection
          |
          v
6.3.3 Semantic Similarity & Matching
          |
          v
6.3.4 Entity Resolution
          |
          v
6.3.5 Contradiction Detection
          |
          v
6.3.6 Memory Update & Correction
          |
          v
6.3.7 Supersession & Version Management
          |
          v
6.3.8 Memory Relationship Resolution
          |
          v
6.3.9 Resolution Decision & Promotion
          |
          v
Authoritative Memory State
```

This is a logical dependency flow, not a requirement that every candidate execute every algorithm. Raven should skip unnecessary stages when their conditions do not apply.

---

# 2. Shared Resolution Principles

## 2.1 Similarity Is Not Identity

Two memories can be semantically similar without representing the same information.

Example:

- "I am learning Python."
- "I am learning Java."

They are structurally similar but describe different activities.

Similarity must identify potential matches, not authorize merging.

## 2.2 Preserve Historical Information

When information changes, Raven must preserve the previous state where historical retention applies.

Example:

- Previous: The user works at Company A.
- New: The user now works at Company B.

The new information must not silently erase the previous employment record.

## 2.3 Distinguish Different Relationship Types

Raven must distinguish:

- Duplicate.
- Similar.
- Related.
- Contradictory.
- Corrective.
- Updated.
- Superseding.
- Supporting.
- Derived.

These relationships have different meanings and processing requirements.

## 2.4 Evidence Before Modification

An existing memory may only be changed through an authorized resolution decision.

The decision must consider:

- Source evidence.
- User attribution.
- Temporal context.
- Fact confidence.
- Importance.
- Existing memory history.
- Contradiction status.
- Resolution confidence.

## 2.5 Ownership and Isolation

Memory resolution must respect user ownership boundaries.

Private user memories must never be merged across different users.

Shared canonical entities may be referenced by multiple users, but private user-specific facts must remain separately owned.

## 2.6 Quality-First Resolution

When the system cannot confidently determine whether two records should be merged or updated, it must preserve both and request review rather than risk destroying information.

---

# Algorithm 6.3.1 — Candidate Intake & Preparation

**Algorithm ID:** 6.3.1  
**Status:** Specification

## 3. Purpose

Receive validated memory candidates from Phase 6.2 and prepare them for comparison against existing memories.

## 3.1 Responsibilities

- Validate candidate status.
- Verify ownership.
- Validate provenance.
- Confirm candidate completeness.
- Identify relevant entities and attributes.
- Prepare comparison features.
- Retrieve authorized existing memory references.
- Assign resolution operation identifiers.

## 3.2 Input Contract

- `candidate_id`
- `user_id`
- `proposition`
- `category`
- `importance`
- `confidence`
- `origin_type`
- `context`
- `temporal_information`
- `source_references`
- `provenance`
- `candidate_status`
- `version`

## 3.3 Processing Rules

1. Accept only candidates produced by the approved Phase 6.2 pipeline.
2. Validate candidate ownership.
3. Confirm that required provenance exists.
4. Preserve original candidate content.
5. Extract comparison features without modifying the proposition.
6. Identify relevant memory categories and temporal context.
7. Retrieve only authorized existing memories.
8. Prepare the candidate for duplicate and similarity analysis.

Invalid candidates must not enter resolution.

## 3.4 Output

A prepared resolution package containing:

- Candidate reference.
- Ownership scope.
- Comparison representation.
- Entity references.
- Context.
- Temporal information.
- Source evidence.
- Existing memory references.
- Resolution operation identifier.

## 3.5 Pseudocode

```text
FUNCTION prepare_candidate(candidate):

    validate_candidate(candidate)

    IF candidate.status != VALIDATED:
        RETURN REJECT

    verify_ownership(candidate)

    validate_provenance(candidate)

    features = extract_comparison_features(candidate)

    existing_memories = retrieve_authorized_memories(
        candidate.user_id,
        features
    )

    RETURN create_resolution_package(
        candidate,
        features,
        existing_memories
    )
```

## 3.6 Acceptance Criteria

- AC-01: Only validated candidates enter resolution.
- AC-02: Ownership is verified.
- AC-03: Provenance is preserved.
- AC-04: Existing memories are retrieved within authorized scope.
- AC-05: Candidate content remains unchanged.
- AC-06: Resolution operations are traceable.

**Specification status:** COMPLETE.

---

# Algorithm 6.3.2 — Duplicate Memory Detection

**Algorithm ID:** 6.3.2  
**Status:** Specification

## 4. Purpose

Identify whether a new candidate represents information already stored in memory.

The objective is to prevent redundant memory creation while preserving legitimate repeated events and separate pieces of evidence.

## 4.1 Duplicate Types

### Exact Duplicate

Two records represent the same proposition with equivalent meaning and context.

Example:

- "I prefer dark mode."
- "I prefer dark mode."

### Normalized Duplicate

Two records differ in wording but express the same proposition.

Example:

- "I am studying computer science."
- "I study computer science."

### Semantic Duplicate

Two differently worded propositions express the same underlying information.

Example:

- "My preferred programming language is Kotlin."
- "I like using Kotlin the most."

### Non-Duplicate Similar Information

Example:

- "I am learning Kotlin."
- "I want to learn Java."

These are related but not duplicates.

## 4.2 Detection Signals

Use a hybrid approach:

- Exact content comparison.
- Normalized text comparison.
- Structured subject-predicate-object comparison.
- Entity and attribute matching.
- Semantic similarity.
- Temporal context.
- Source attribution.
- Negation and modality comparison.

## 4.3 Important Constraints

Two records must not be considered duplicates merely because:

- They mention the same entity.
- They share a category.
- Their embeddings are similar.
- They discuss the same project.
- They have similar wording.

Negation, temporal context, modality and subject identity must be considered.

## 4.4 Processing Algorithm

1. Receive prepared candidate.
2. Identify possible matching memories.
3. Compare normalized propositions.
4. Compare structured attributes.
5. Compare subject and entity references.
6. Compare temporal context.
7. Evaluate semantic similarity.
8. Determine duplicate classification.
9. Record evidence and confidence.
10. Return duplicate, non-duplicate or uncertain outcome.

## 4.5 Output

Possible outcomes:

- `EXACT_DUPLICATE`
- `NORMALIZED_DUPLICATE`
- `SEMANTIC_DUPLICATE`
- `NOT_DUPLICATE`
- `UNCERTAIN_MATCH`

A duplicate result must identify the matching memory reference.

## 4.6 Resolution Rules

- Exact duplicates may be treated as no-change candidates after provenance is preserved.
- Normalized duplicates may be linked to existing memories.
- Semantic duplicates require stronger contextual validation.
- Separate source evidence may be attached to an existing memory without creating a duplicate memory.
- Repeated events must not be collapsed merely because their descriptions are similar.

## 4.7 Pseudocode

```text
FUNCTION detect_duplicate(candidate, existing_memories):

    matches = find_candidate_matches(candidate, existing_memories)

    FOR EACH memory IN matches:

        exact = compare_exact_content(candidate, memory)

        normalized = compare_normalized_content(candidate, memory)

        structured = compare_fact_attributes(candidate, memory)

        temporal = compare_temporal_context(candidate, memory)

        semantic = compare_semantic_similarity(candidate, memory)

        IF exact AND context_is_compatible(candidate, memory):
            RETURN EXACT_DUPLICATE(memory.id)

        IF normalized AND structured AND temporal:
            RETURN NORMALIZED_DUPLICATE(memory.id)

        IF semantic AND structured AND context_is_compatible(
            candidate,
            memory
        ):
            RETURN SEMANTIC_DUPLICATE(memory.id)

    RETURN NOT_DUPLICATE
```

## 4.8 Acceptance Criteria

- AC-01: Exact duplicates can be detected.
- AC-02: Normalized duplicates can be detected.
- AC-03: Semantic duplicates require contextual validation.
- AC-04: Similar but distinct facts are not merged.
- AC-05: Negation is considered.
- AC-06: Temporal context is considered.
- AC-07: Source evidence is preserved.
- AC-08: Uncertain matches are not automatically merged.

**Specification status:** COMPLETE.

---

# Algorithm 6.3.3 — Semantic Similarity & Matching

**Algorithm ID:** 6.3.3  
**Status:** Specification

## 5. Purpose

Identify existing memories that are meaningfully related to a new candidate.

This algorithm generates potential matches for downstream resolution.

It does not independently determine whether records should be merged or updated.

## 5.1 Responsibilities

- Generate candidate matches.
- Compare semantic meaning.
- Compare structured attributes.
- Evaluate contextual compatibility.
- Identify related memory clusters.
- Rank potential matches.
- Provide matching evidence.

## 5.2 Matching Approach

Use hybrid matching:

**Lexical matching**
- Token overlap.
- Keyword matching.
- Normalized text.
- Phrase matching.

**Structured matching**
- Subject.
- Predicate.
- Object.
- Category.
- Context.
- Temporal information.

**Semantic matching**
- Embedding similarity.
- Semantic feature comparison.
- Context-aware ranking.

## 5.3 Matching Dimensions

| Dimension | Purpose |
|---|---|
| Semantic similarity | Similarity in meaning |
| Entity similarity | Similarity of referenced entities |
| Attribute similarity | Similarity of properties |
| Context similarity | Similarity of surrounding circumstances |
| Temporal compatibility | Compatibility of time references |
| Relationship similarity | Similarity of expressed relationships |

## 5.4 Matching Scores

A configurable ranking function may combine the matching dimensions.

\[
M = w_sS + w_eE + w_aA + w_cC + w_tT
\]

Where:

- \(S\): Semantic similarity.
- \(E\): Entity similarity.
- \(A\): Attribute similarity.
- \(C\): Context similarity.
- \(T\): Temporal compatibility.

The weights and thresholds must be calibrated during implementation.

The resulting score is a matching signal, not proof of identity or duplication.

## 5.5 Processing Algorithm

1. Receive candidate.
2. Generate initial memory search features.
3. Retrieve possible matches.
4. Apply lexical matching.
5. Apply structured comparison.
6. Apply semantic similarity.
7. Evaluate context and temporal compatibility.
8. Rank candidate matches.
9. Return top relevant matches with evidence.
10. Pass matching information to entity and contradiction resolution.

## 5.6 Pseudocode

```text
FUNCTION match_related_memories(candidate):

    search_features = generate_search_features(candidate)

    matches = retrieve_possible_matches(search_features)

    ranked_matches = []

    FOR EACH memory IN matches:

        semantic = calculate_semantic_similarity(candidate, memory)

        entity = compare_entities(candidate, memory)

        attributes = compare_attributes(candidate, memory)

        context = compare_context(candidate, memory)

        temporal = compare_temporal_compatibility(candidate, memory)

        score = rank_match(
            semantic,
            entity,
            attributes,
            context,
            temporal
        )

        ranked_matches.append(memory, score)

    RETURN rank_and_filter_matches(ranked_matches)
```

## 5.7 Acceptance Criteria

- AC-01: Related memories can be identified.
- AC-02: Lexical and semantic matching are supported.
- AC-03: Structured attributes contribute to matching.
- AC-04: Temporal incompatibility is considered.
- AC-05: Similarity is not treated as proof of duplication.
- AC-06: Match results are ranked.
- AC-07: Matching evidence is retained.
- AC-08: Thresholds are configurable and evaluable.

**Specification status:** COMPLETE.

---

# Algorithm 6.3.4 — Entity Resolution

**Algorithm ID:** 6.3.4  
**Status:** Specification

## 6. Purpose

Determine whether different mentions or references identify the same real-world or conceptual entity.

Entity resolution prevents Raven from creating unnecessary separate entities for the same person, organization, project or other identifiable object.

## 6.1 Entity Types

Initial conceptual entity types:

- Person.
- Organization.
- Project.
- Product.
- Place.
- Institution.
- Technology.
- Event.
- Other identifiable entities.

## 6.2 Resolution Stages

### Stage 1 — Mention Identification

Identify entity mentions in extracted facts.

Example:

- "OpenAI."
- "Open AI."
- "The company behind ChatGPT."

### Stage 2 — Candidate Generation

Retrieve possible canonical entity matches using:

- Name.
- Aliases.
- Entity type.
- Context.
- External identifiers where available.
- Related facts.

### Stage 3 — Candidate Evaluation

Compare:

- Name similarity.
- Entity type.
- Context.
- Attributes.
- Relationships.
- Available identifiers.
- Temporal consistency.

### Stage 4 — Resolution Decision

Possible outcomes:

- Match an existing entity.
- Create a new entity.
- Preserve unresolved mention.
- Require review.

## 6.3 Entity Scope

Raven must distinguish:

**Private user-scoped entities**

Entities or references that exist only within a user's memory context.

**Shared canonical entities**

Public or globally reusable entities that can be referenced by multiple users.

Private facts must never be placed inside shared canonical entity records.

## 6.4 Alias Management

An entity may have multiple names or aliases.

Example:

Canonical entity: Company X

Aliases:
- Company X Ltd.
- Company X.
- CX.

Aliases must be independently manageable and retain provenance.

An alias must not automatically establish entity identity without sufficient supporting evidence.

## 6.5 Processing Algorithm

1. Receive entity mention.
2. Identify entity type.
3. Generate possible canonical matches.
4. Compare names and aliases.
5. Compare contextual attributes.
6. Compare available identifiers.
7. Evaluate resolution confidence.
8. Select match, new entity, unresolved or review.
9. Record resolution evidence.
10. Maintain alias relationships where justified.

## 6.6 Pseudocode

```text
FUNCTION resolve_entity(mention):

    entity_type = identify_entity_type(mention)

    matches = find_entity_candidates(
        mention.name,
        entity_type,
        mention.context
    )

    FOR EACH entity IN matches:

        score = evaluate_entity_match(
            mention,
            entity
        )

        IF score.meets_match_policy:
            RETURN MATCH_EXISTING_ENTITY(entity.id)

    IF evidence_is_insufficient(mention):
        RETURN UNRESOLVED

    RETURN CREATE_NEW_ENTITY
```

## 6.7 Acceptance Criteria

- AC-01: Entity mentions are identifiable.
- AC-02: Possible canonical entities can be retrieved.
- AC-03: Name similarity alone does not guarantee a match.
- AC-04: Entity types are considered.
- AC-05: Contextual attributes contribute to resolution.
- AC-06: Aliases are maintained separately.
- AC-07: Uncertain matches can remain unresolved.
- AC-08: Private and shared entity scopes remain isolated.
- AC-09: Resolution decisions retain provenance.

**Specification status:** COMPLETE.

---

# Algorithm 6.3.5 — Contradiction Detection

**Algorithm ID:** 6.3.5  
**Status:** Specification

## 7. Purpose

Identify whether a new candidate conflicts with existing memory information.

Contradictions must be detected before an existing memory is updated or superseded.

The algorithm must distinguish genuine contradictions from normal changes over time.

## 7.1 Contradiction Types

### Direct Contradiction

- "I work at Company A."
- "I do not work at Company A."

### Attribute Contradiction

- "My preferred language is Java."
- "My preferred language is Kotlin."

This may be a contradiction or a preference change depending on temporal context.

### Temporal Change

- "I live in Delhi."
- "I moved to Bangalore."

These statements may describe different periods rather than conflicting facts.

### Numeric Contradiction

- "The project budget is ₹50,000."
- "The project budget is ₹75,000."

The difference may represent an update rather than a contradiction.

### Source Conflict

Two sources provide incompatible information about the same proposition.

### Contextual Conflict

Two propositions appear inconsistent but may apply to different situations.

## 7.2 Contradiction Evaluation

Consider:

- Subject identity.
- Predicate.
- Object or value.
- Context.
- Temporal information.
- Source attribution.
- Negation.
- Modality.
- Fact confidence.
- Source reliability.

## 7.3 Contradiction vs Change

A contradiction must not be assumed merely because two values differ.

Example:

"I used to work at Company A, but now I work at Company B."

This is a temporal progression.

Example:

"I work at Company A" and "I work at Company B."

Without further context, this may be a conflict, simultaneous employment or incomplete information.

Raven must not guess.

## 7.4 Processing Algorithm

1. Receive candidate and matched memories.
2. Identify shared subjects and predicates.
3. Compare values and attributes.
4. Compare temporal context.
5. Compare modality and negation.
6. Compare source evidence.
7. Identify conflict type.
8. Distinguish temporal progression from genuine conflict.
9. Assign contradiction confidence.
10. Produce resolution recommendation.

## 7.5 Output Types

- `NO_CONFLICT`
- `DIRECT_CONTRADICTION`
- `ATTRIBUTE_CONFLICT`
- `TEMPORAL_CHANGE`
- `SOURCE_CONFLICT`
- `CONTEXTUAL_CONFLICT`
- `UNCERTAIN_CONFLICT`

## 7.6 Pseudocode

```text
FUNCTION detect_contradiction(candidate, existing_memory):

    IF subjects_are_different(candidate, existing_memory):
        RETURN NO_CONFLICT

    IF predicates_are_incompatible(candidate, existing_memory):

        IF temporal_progression_is_supported(
            candidate,
            existing_memory
        ):
            RETURN TEMPORAL_CHANGE

        IF context_explains_difference(candidate, existing_memory):
            RETURN CONTEXTUAL_CONFLICT

        IF evidence_supports_conflict(candidate, existing_memory):
            RETURN DIRECT_CONTRADICTION

        RETURN UNCERTAIN_CONFLICT

    RETURN NO_CONFLICT
```

## 7.7 Acceptance Criteria

- AC-01: Direct contradictions can be detected.
- AC-02: Attribute conflicts can be identified.
- AC-03: Temporal changes are distinguished from contradictions.
- AC-04: Negation is considered.
- AC-05: Source attribution is considered.
- AC-06: Contextual differences are considered.
- AC-07: Uncertain conflicts can require review.
- AC-08: Contradictory information is not silently overwritten.

**Specification status:** COMPLETE.

---

# Algorithm 6.3.6 — Memory Update & Correction

**Algorithm ID:** 6.3.6  
**Status:** Specification

## 8. Purpose

Determine how new information should modify or correct an existing memory.

This algorithm handles changes to memory content while preserving source evidence and historical integrity.

## 8.1 Update Types

### Direct Correction

The user explicitly corrects earlier information.

Example:

"I told you my graduation year was 2024, but it was actually 2025."

### Attribute Update

An existing attribute changes.

Example:

"My preferred programming language is now Kotlin."

### Context Update

Additional context changes how an existing memory should be interpreted.

### Partial Update

Only one attribute changes while the remaining memory information stays valid.

### No-Change Update

The new information does not require changing the existing memory.

## 8.2 Update Rules

1. Identify the target memory.
2. Validate evidence.
3. Confirm ownership.
4. Determine the scope of change.
5. Preserve unchanged attributes.
6. Create a new revision when required.
7. Preserve historical information.
8. Record correction provenance.
9. Prevent unauthorized overwrites.
10. Apply concurrency controls.

## 8.3 Update Decision

| Situation | Expected behaviour |
|---|---|
| Explicit correction | Apply correction through controlled revision |
| Clear attribute change | Update affected attribute |
| Additional context | Extend or link context |
| Uncertain change | Require review |
| Unrelated information | Create separate memory |
| No actual change | No-change outcome |
| Conflicting evidence | Preserve conflict for review |

## 8.4 Pseudocode

```text
FUNCTION update_existing_memory(candidate, existing_memory):

    validate_ownership(candidate, existing_memory)

    validate_supporting_evidence(candidate)

    change = identify_memory_change(
        candidate,
        existing_memory
    )

    IF change.is_unrelated:
        RETURN CREATE_NEW

    IF change.is_ambiguous:
        RETURN NEEDS_REVIEW

    IF change.is_identical:
        RETURN NO_CHANGE

    IF change.is_supported:

        preserve_current_revision(existing_memory)

        create_new_revision(
            existing_memory,
            candidate
        )

        RETURN UPDATE_EXISTING

    RETURN NEEDS_REVIEW
```

## 8.5 Acceptance Criteria

- AC-01: Corrections are distinguishable from unrelated new facts.
- AC-02: Only affected attributes are updated.
- AC-03: Previous revisions are preserved.
- AC-04: Evidence supports every update.
- AC-05: Ambiguous updates require review.
- AC-06: No-change outcomes are supported.
- AC-07: Concurrent updates cannot silently overwrite one another.
- AC-08: Update history is traceable.

**Specification status:** COMPLETE.

---

# Algorithm 6.3.7 — Supersession & Version Management

**Algorithm ID:** 6.3.7  
**Status:** Specification

## 9. Purpose

Manage historical versions when a memory changes, becomes outdated or is replaced by new information.

The objective is to preserve the history of information while maintaining a clear current representation.

## 9.1 Versioning Principles

- Existing revisions must not be silently overwritten.
- Every material update must be traceable.
- Current and historical states must be distinguishable.
- Valid time and transaction time must remain separate where applicable.
- Historical information must not be represented as current.
- Supersession must retain the relationship between old and new records.

## 9.2 Supersession Types

| Type | Meaning |
|---|---|
| `UPDATED_BY` | A newer revision updates an earlier one |
| `SUPERSEDED_BY` | A newer memory replaces the current representation |
| `CORRECTED_BY` | A correction replaces an inaccurate representation |
| `EXPIRED` | A time-limited memory is no longer current |
| `RETRACTED` | A previous assertion has been withdrawn |

## 9.3 Temporal Model

Where useful, maintain:

**Valid time:** When the information was true in the real world.

**Transaction time:** When Raven recorded the information.

Example:

A user changes jobs on 1 August but tells Raven on 5 August.

- Valid time begins: 1 August.
- Transaction time begins: 5 August.

The system must preserve this distinction where the evidence supports it.

## 9.4 Processing Algorithm

1. Receive an authorized memory update.
2. Identify the current revision.
3. Validate the new information.
4. Determine the effective time.
5. Preserve the existing revision.
6. Create a new revision.
7. Link previous and current revisions.
8. Update the current-state reference.
9. Record supersession reason.
10. Verify version consistency.

## 9.5 Pseudocode

```text
FUNCTION manage_memory_version(existing, update):

    validate_update(update)

    IF update.is_not_material:
        RETURN NO_NEW_VERSION

    current_revision = load_current_revision(existing)

    preserve_revision(current_revision)

    new_revision = create_revision(
        update,
        current_revision
    )

    link_revisions(
        current_revision,
        new_revision
    )

    update_current_revision_reference(new_revision)

    RETURN VERSION_CREATED
```

## 9.6 Acceptance Criteria

- AC-01: Material updates create traceable revisions.
- AC-02: Previous revisions remain distinguishable.
- AC-03: Current state is identifiable.
- AC-04: Supersession relationships are preserved.
- AC-05: Valid time and transaction time are distinguishable where available.
- AC-06: Historical information is not presented as current.
- AC-07: Version conflicts are detected.
- AC-08: Version operations are idempotent.

**Specification status:** COMPLETE.

---

# Algorithm 6.3.8 — Memory Relationship Resolution

**Algorithm ID:** 6.3.8  
**Status:** Specification

## 10. Purpose

Identify and maintain meaningful relationships between memory records.

Memory relationships allow Raven to retrieve connected information without combining unrelated facts into a single memory.

## 10.1 Supported Relationship Types

Initial relationship types:

| Relationship | Meaning |
|---|---|
| `RELATED_TO` | General association |
| `SUPPORTS` | One memory supports another |
| `CONTRADICTS` | Memories contain conflicting information |
| `UPDATES` | One memory updates another |
| `SUPERSEDES` | One memory replaces an earlier representation |
| `PART_OF` | One memory is part of a larger context |
| `DERIVED_FROM` | One memory was derived from another |
| `DEPENDS_ON` | One memory depends on another |
| `ABOUT_ENTITY` | Memory concerns an entity |

## 10.2 Relationship Representation

Relationships should be independent records.

Conceptual attributes:

- `relationship_id`
- `source_memory_id`
- `target_memory_id`
- `relationship_type`
- `confidence`
- `provenance`
- `valid_time`
- `created_at`
- `status`

## 10.3 Relationship Rules

- A relationship must have valid source and target references.
- Relationship types must be explicit.
- Relationship provenance must be preserved.
- Relationships must respect user ownership.
- Unsupported relationships must not be invented.
- Cycles must be handled according to relationship semantics.
- Deletion and supersession must propagate to dependent relationships.

## 10.4 Processing Algorithm

1. Receive resolved memory records.
2. Identify potential relationships.
3. Compare semantic and structural context.
4. Determine relationship type.
5. Validate source and target.
6. Estimate relationship confidence.
7. Create or update relationship record.
8. Preserve provenance.
9. Validate ownership and integrity.

## 10.5 Pseudocode

```text
FUNCTION resolve_memory_relationships(memory):

    related = find_related_memories(memory)

    relationships = []

    FOR EACH target IN related:

        relationship_type = classify_relationship(
            memory,
            target
        )

        IF relationship_type IS SUPPORTED:

            relationship = create_relationship(
                memory.id,
                target.id,
                relationship_type
            )

            validate_relationship(relationship)

            relationships.append(relationship)

    RETURN relationships
```

## 10.6 Acceptance Criteria

- AC-01: Supported relationship types can be created.
- AC-02: Relationships retain source and target references.
- AC-03: Relationship provenance is preserved.
- AC-04: Ownership boundaries are enforced.
- AC-05: Unsupported relationships are not created.
- AC-06: Updates and supersession relationships are maintained.
- AC-07: Relationship deletion follows lifecycle policies.
- AC-08: Relationship records are independently traceable.

**Specification status:** COMPLETE.

---

# Algorithm 6.3.9 — Resolution Decision & Promotion

**Algorithm ID:** 6.3.9  
**Status:** Specification

## 11. Purpose

Determine the final resolution outcome for a validated memory candidate.

This algorithm combines the outputs of duplicate detection, semantic matching, entity resolution, contradiction detection, update handling, version management and relationship resolution.

It determines whether the candidate should create a new memory, update an existing memory, merge compatible information, remain under review or be rejected.

## 11.1 Responsibilities

- Aggregate resolution evidence.
- Evaluate matching and contradiction results.
- Select the appropriate resolution outcome.
- Validate authorization.
- Enforce ownership and integrity constraints.
- Coordinate the appropriate memory operation.
- Ensure safe promotion.
- Record the resolution decision.
- Verify successful persistence.

## 11.2 Resolution Decision Matrix

| Condition | Resolution |
|---|---|
| Exact duplicate | `NO_CHANGE` |
| Normalized duplicate | `NO_CHANGE` or attach additional evidence |
| Compatible additional information | `MERGE` |
| Clear correction | `UPDATE_EXISTING` |
| Confirmed temporal change | `SUPERSEDE` |
| Related but independent information | `LINK_EXISTING` or `CREATE_NEW` |
| Genuine unresolved contradiction | `NEEDS_REVIEW` |
| Ambiguous entity match | `NEEDS_REVIEW` |
| Invalid candidate | `REJECT` |
| No relevant existing memory | `CREATE_NEW` |

## 11.3 Promotion Requirements

Before an authoritative memory operation:

1. Candidate validation must be complete.
2. Ownership must be confirmed.
3. Evidence must be available.
4. Resolution outcome must be justified.
5. Relevant conflicts must be resolved or preserved.
6. Required revisions must be created.
7. Relationships must be valid.
8. The operation must be idempotent.
9. Persistence must be confirmed.

A successful resolution decision is not the same as successful persistence.

Raven must not report a memory operation as completed until the storage operation is confirmed.

## 11.4 Transaction and Consistency Requirements

- Use owner-controlled write operations.
- Apply optimistic concurrency where appropriate.
- Verify current memory version before modification.
- Preserve completed operations during recovery.
- Use idempotency keys to prevent duplicate writes.
- Avoid partial updates that leave inconsistent relationships.
- Record operation status.
- Reconcile uncertain outcomes before retrying.

The exact transaction implementation is deferred to technology and infrastructure design.

## 11.5 Pseudocode

```text
FUNCTION resolve_and_promote(candidate, resolution_results):

    validate_candidate(candidate)

    validate_ownership(candidate)

    IF candidate.is_invalid:
        RETURN REJECT

    IF resolution_results.exact_duplicate:
        RETURN NO_CHANGE

    IF resolution_results.requires_review:
        RETURN NEEDS_REVIEW

    IF resolution_results.clear_correction:
        outcome = UPDATE_EXISTING

    ELSE IF resolution_results.temporal_change:
        outcome = SUPERSEDE

    ELSE IF resolution_results.compatible_information:
        outcome = MERGE

    ELSE IF resolution_results.related_memory_exists:
        outcome = LINK_EXISTING

    ELSE:
        outcome = CREATE_NEW

    validate_resolution_outcome(outcome)

    operation = execute_authorized_memory_operation(
        candidate,
        outcome
    )

    IF operation.persistence_confirmed:
        record_resolution_success(operation)
        RETURN operation.result

    RETURN RECOVERY_REQUIRED
```

## 11.6 Resolution Audit

Every resolution decision should preserve:

- Resolution identifier.
- Candidate identifier.
- Existing memory references.
- Resolution outcome.
- Supporting evidence.
- Matching results.
- Contradiction results.
- Entity resolution results.
- Decision rationale.
- Processing version.
- Operation status.
- Timestamp.

## 11.7 Acceptance Criteria

- AC-01: All resolution outcomes are distinguishable.
- AC-02: Exact duplicates do not create redundant memories.
- AC-03: Compatible information can be merged safely.
- AC-04: Corrections update the appropriate memory.
- AC-05: Historical information is preserved.
- AC-06: Contradictions are not silently overwritten.
- AC-07: Related memories can remain independent.
- AC-08: Ownership is verified before writes.
- AC-09: Memory operations are idempotent.
- AC-10: Version conflicts are detected.
- AC-11: Persistence must be confirmed before reporting success.
- AC-12: Resolution decisions are auditable.
- AC-13: Failed operations can recover safely.
- AC-14: Uncertain outcomes can require review.

**Specification status:** COMPLETE.

---

# 12. Cross-Algorithm Data Flow

| Algorithm | Input | Output |
|---|---|---|
| 6.3.1 Candidate Intake | Validated candidate | Prepared resolution package |
| 6.3.2 Duplicate Detection | Candidate and existing memories | Duplicate result |
| 6.3.3 Semantic Matching | Candidate and memory search results | Ranked matches |
| 6.3.4 Entity Resolution | Entity mentions | Canonical entity references or unresolved results |
| 6.3.5 Contradiction Detection | Candidate and matched memories | Conflict classification |
| 6.3.6 Memory Update | Candidate and existing memory | Update decision |
| 6.3.7 Version Management | Authorized update | Version and supersession records |
| 6.3.8 Relationship Resolution | Related memory records | Relationship records |
| 6.3.9 Resolution Decision | All relevant results | Final resolution outcome |

---

# 13. Shared Security and Privacy Requirements

1. Enforce user ownership for every memory operation.
2. Never merge private memories across users.
3. Validate access before retrieving comparison candidates.
4. Preserve source evidence and provenance.
5. Protect historical memory versions.
6. Validate all entity references.
7. Prevent unauthorized memory modification.
8. Apply deletion policies to associated records.
9. Avoid exposing private content in operational logs.
10. Treat external identifiers and content as untrusted until validated.

---

# 14. Performance and Resource Considerations

Quality takes priority over processing speed and cost.

Optimization should consider:

- Efficient candidate retrieval.
- Metadata and temporal filtering.
- Hybrid lexical and semantic matching.
- Avoiding unnecessary embedding comparisons.
- Reusing valid resolution results.
- Bounded candidate matching.
- Controlled concurrency.
- Idempotent resolution operations.

Exact thresholds, embedding models, search indexes and performance targets will be finalized during implementation and evaluation.

---

# 15. Evaluation Metrics

| Area | Metrics |
|---|---|
| Duplicate detection | Precision, recall, false merge rate |
| Semantic matching | Match precision, match recall, ranking quality |
| Entity resolution | Entity matching accuracy, false identity rate |
| Contradiction detection | Conflict precision, conflict recall |
| Updates | Correction accuracy, unintended overwrite rate |
| Version management | Version integrity, historical preservation |
| Relationships | Relationship accuracy, invalid relationship rate |
| Promotion | Resolution accuracy, persistence success |
| Reliability | Retry success, recovery success, idempotency |

False merges and incorrect overwrites must be treated as high-severity failures.

Numerical acceptance targets will be established during Phase 12.

---

# 16. Phase 6.3 Completion Criteria

Phase 6.3 is architecturally specified when:

- All nine algorithms have defined inputs and outputs.
- Duplicate detection and semantic similarity are distinct.
- Entity identity is not based on name similarity alone.
- Contradictions are distinguished from temporal changes.
- Corrections preserve previous information.
- Versioning and supersession are defined.
- Memory relationships are independently represented.
- Resolution decisions are traceable.
- Promotion follows ownership and persistence rules.
- Failure and recovery behaviour is documented.

| Algorithm | Specification status |
|---|---|
| 6.3.1 — Candidate Intake & Preparation | COMPLETE |
| 6.3.2 — Duplicate Memory Detection | COMPLETE |
| 6.3.3 — Semantic Similarity & Matching | COMPLETE |
| 6.3.4 — Entity Resolution | COMPLETE |
| 6.3.5 — Contradiction Detection | COMPLETE |
| 6.3.6 — Memory Update & Correction | COMPLETE |
| 6.3.7 — Supersession & Version Management | COMPLETE |
| 6.3.8 — Memory Relationship Resolution | COMPLETE |
| 6.3.9 — Resolution Decision & Promotion | COMPLETE |

**Important:** COMPLETE means specification complete. No implementation, database migration, model calibration or test execution is implied.

---

# 17. Dependencies

Phase 6.3 depends on:

- Phase 1 — Overall System Architecture.
- Phase 2 — Memory Engine Architecture.
- Phase 5.1 — Overall Data Architecture.
- Phase 5.2 — Data Ownership & Boundaries.
- Phase 5.3 — Core Entities & Relationships.
- Phase 5.4 — Memory Engine Data Models.
- Phase 5.8 — Database Relationships & Indexing.
- Phase 5.9 — Consistency, Transactions & Versioning.
- Phase 5.10 — Retention, Deletion & Migration.
- Phase 6.1 — Shared Algorithm Framework & Scoring System.
- Phase 6.2 — Memory Ingestion & Extraction.

---

# 18. Next Phase

**Phase 6.4 — Memory Retrieval**

The next phase will define how Raven retrieves relevant memories for a user request.

It will cover:

- Query understanding.
- Query normalization.
- Memory search.
- Hybrid retrieval.
- Semantic and keyword search.
- Context-aware filtering.
- Ranking and scoring.
- Relationship-aware retrieval.
- Temporal retrieval.
- Confidence and evidence filtering.
- Dynamic Top-K selection.
- Iterative retrieval.
- Retrieval budgets and early stopping.
- Evidence-backed retrieval results.

Phase 6.4 will consume the authoritative memory structures maintained by the previous phases.

---

**Project:** Raven  
**Engine:** Memory Engine  
**Phase:** 6.3 — Memory Resolution  
**Document:** `02-memory-resolution.md`  
**Status:** ALL NINE ALGORITHM SPECIFICATIONS COMPLETE
