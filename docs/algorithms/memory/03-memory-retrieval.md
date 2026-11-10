# Raven — Memory Retrieval

**Project:** Raven  
**Engine:** Memory Engine  
**Phase:** 6.4 — Memory Retrieval  
**File:** `03-memory-retrieval.md`  
**Directory:** `docs/algorithms/memory/`  
**Status:** Algorithm Specification

---

# 1. Purpose

Memory Retrieval defines how Raven identifies, searches, ranks and returns relevant information from its authoritative memory records.

Its objective is to retrieve the most useful information for a given user request while preserving contextual accuracy, temporal correctness, evidence and confidence.

Memory retrieval must not simply return the memories with the highest semantic similarity.

It must consider:

- User intent.
- Query context.
- Memory relevance.
- Entity relationships.
- Temporal information.
- Memory importance.
- Fact confidence.
- Memory freshness.
- Provenance.
- Memory lifecycle state.

The retrieval system must avoid returning outdated, unrelated, contradictory or insufficiently supported information as confirmed current facts.

## 1.1 Responsibilities

Phase 6.4 is responsible for:

1. Understanding memory retrieval queries.
2. Normalizing retrieval queries.
3. Identifying relevant entities and attributes.
4. Selecting retrieval strategies.
5. Performing hybrid memory search.
6. Applying context and temporal filters.
7. Retrieving related memories.
8. Ranking candidate memories.
9. Evaluating evidence and confidence.
10. Determining retrieval depth.
11. Expanding retrieval when necessary.
12. Assembling structured retrieval results.
13. Validating output provenance and relevance.

## 1.2 Core Retrieval Principle

**Retrieve the right information, not merely the most similar information.**

For example, consider the stored memories:

- The user previously worked at Company A.
- The user currently works at Company B.
- The user wants to work at Company C.

If the user asks:

"Where do I currently work?"

Raven must prioritize Company B.

It must not return Company A simply because it appears frequently in historical conversations or Company C because it is semantically related to the query.

## 1.3 Retrieval Architecture

```text
User Query
    |
    v
6.4.1 Query Understanding & Normalization
    |
    v
6.4.2 Retrieval Strategy Selection
    |
    v
6.4.3 Hybrid Memory Search
    |
    v
6.4.4 Context & Temporal Filtering
    |
    v
6.4.5 Relationship-Aware Retrieval
    |
    v
6.4.6 Memory Ranking & Scoring
    |
    v
6.4.7 Evidence & Confidence Filtering
    |
    v
6.4.8 Dynamic Top-K & Retrieval Expansion
    |
    v
6.4.9 Retrieval Assembly & Output Validation
    |
    v
Structured Memory Retrieval Result
```

Not every query needs every retrieval stage. The orchestrator and retrieval strategy must avoid unnecessary processing for simple requests.

---

# 2. Shared Retrieval Principles

## 2.1 Hybrid Retrieval

Raven must support multiple retrieval methods:

- Semantic search.
- Keyword search.
- Metadata filtering.
- Structured attribute search.
- Entity-based search.
- Relationship-based search.
- Temporal search.

No single retrieval method is sufficient for every query.

## 2.2 Context-Aware Retrieval

A memory must be interpreted within its context.

For example:

"I am learning Python for my internship."

and:

"I want to learn Python for my personal project."

Both mention Python, but their contexts differ.

## 2.3 Temporal Correctness

Raven must distinguish:

- Current information.
- Historical information.
- Future intentions.
- Expired information.
- Superseded information.
- Time-bound commitments.

Historical facts must not be presented as current facts.

## 2.4 Evidence-Aware Retrieval

Every retrieved memory must retain its provenance.

The system must be able to identify why a memory was retrieved and which evidence supports it.

## 2.5 Confidence-Aware Retrieval

A highly relevant memory with weak evidence must not automatically be presented as a confirmed fact.

Confidence and relevance must remain separate.

## 2.6 User Isolation

All retrieval must operate within authorized ownership boundaries.

Private memories belonging to another user must never appear in the retrieval results.

## 2.7 Quality Before Retrieval Speed

Retrieval optimization must not compromise:

- Ownership.
- Temporal correctness.
- Evidence integrity.
- Confidence.
- Data consistency.

---

# Algorithm 6.4.1 — Query Understanding & Normalization

**Algorithm ID:** 6.4.1  
**Status:** Specification

## 3. Purpose

This algorithm interprets the user's request and transforms it into a structured retrieval query.

The objective is to understand what information the user wants, which entities or attributes are involved, and what context is required.

A retrieval query may request:

- A specific fact.
- A historical event.
- A current preference.
- A project detail.
- A relationship.
- A collection of memories.
- A comparison between previous and current information.

## 3.1 Responsibilities

- Query classification.
- Intent identification.
- Entity identification.
- Attribute identification.
- Temporal expression identification.
- Context identification.
- Keyword extraction.
- Query normalization.
- Ambiguity identification.
- Retrieval constraint generation.

## 3.2 Query Categories

| Category | Example |
|---|---|
| Direct fact | "What programming language am I learning?" |
| Historical | "Where did I work last year?" |
| Current state | "What is my current project?" |
| Preference | "What kind of food do I prefer?" |
| Goal | "What career goal did I mention?" |
| Relationship | "Who is the person I mentioned from Company X?" |
| Project context | "What technology stack did I choose for Raven?" |
| Temporal comparison | "What changed in my career plans?" |
| Multi-fact | "Summarize everything I told you about my internship." |
| Contextual | "What was the decision we made earlier?" |

## 3.3 Input Contract

| Attribute | Purpose |
|---|---|
| `query_id` | Unique retrieval query identifier |
| `user_id` | Requesting user |
| `original_query` | Original user request |
| `conversation_context` | Relevant current conversation context |
| `request_timestamp` | Query timestamp |
| `access_scope` | Authorized retrieval scope |
| `schema_version` | Query contract version |

## 3.4 Query Representation

Raven should convert a query into a structured representation.

Conceptual fields:

- `query_intent`
- `entities`
- `attributes`
- `keywords`
- `context`
- `temporal_constraints`
- `requested_memory_types`
- `retrieval_depth`
- `ambiguity_status`

Example:

User query:

"What was my previous internship company?"

Structured representation:

| Field | Value |
|---|---|
| Intent | Historical fact retrieval |
| Entity | User |
| Attribute | Internship company |
| Temporal constraint | Previous |
| Context | Professional experience |
| Requested result | Organization name |

## 3.5 Query Processing

**Step 1 — Receive Query**

Receive the user's request and authorized user context.

**Step 2 — Identify Intent**

Determine whether the user wants a fact, history, preference, goal, relationship or broader memory summary.

**Step 3 — Identify Entities**

Identify referenced people, organizations, projects, products and other entities.

**Step 4 — Identify Attributes**

Determine which properties are being requested.

**Step 5 — Identify Temporal Constraints**

Identify expressions such as:

- Currently.
- Previously.
- Last year.
- Recently.
- Before.
- After.
- Since.
- Until.
- During a particular period.

**Step 6 — Extract Context**

Identify the relevant project, event, relationship or subject context.

**Step 7 — Normalize Query**

Prepare normalized query terms and structured filters.

**Step 8 — Detect Ambiguity**

If multiple interpretations materially change the answer, mark the query as ambiguous.

Do not silently select an unsupported interpretation.

**Step 9 — Generate Retrieval Query**

Produce the structured query for Algorithm 6.4.2.

## 3.6 Pseudocode

```text
FUNCTION understand_query(user_query, user_context):

    query = initialize_retrieval_query(user_query)

    query.intent = classify_query_intent(user_query)

    query.entities = identify_entities(user_query)

    query.attributes = identify_requested_attributes(user_query)

    query.keywords = extract_keywords(user_query)

    query.temporal_constraints = extract_temporal_constraints(
        user_query
    )

    query.context = identify_query_context(
        user_query,
        user_context
    )

    query.ambiguity_status = evaluate_query_ambiguity(query)

    RETURN normalize_retrieval_query(query)
```

## 3.7 Output Contract

- Query identifier.
- User scope.
- Original query.
- Normalized query.
- Intent.
- Entities.
- Attributes.
- Keywords.
- Context.
- Temporal constraints.
- Ambiguity status.
- Requested retrieval depth.

## 3.8 Failure Handling

| Failure | Expected behaviour |
|---|---|
| Unrecognized intent | Use a safe general retrieval strategy |
| Ambiguous entity | Mark ambiguity |
| Missing temporal reference | Avoid inventing a date |
| Incomplete context | Use available context or request clarification |
| Query normalization failure | Retain original query |
| Unauthorized request | Reject retrieval |

## 3.9 Acceptance Criteria

- AC-01: Query intent can be identified.
- AC-02: Relevant entities can be extracted.
- AC-03: Requested attributes can be identified.
- AC-04: Temporal constraints are preserved.
- AC-05: Context is retained.
- AC-06: Ambiguous queries are identifiable.
- AC-07: Original query remains available.
- AC-08: Unauthorized requests are rejected.

**Specification status:** COMPLETE.

---

# Algorithm 6.4.2 — Retrieval Strategy Selection

**Algorithm ID:** 6.4.2  
**Status:** Specification

## 4. Purpose

Select the appropriate retrieval methods based on the structured query produced by Algorithm 6.4.1.

Different queries require different retrieval strategies.

For example:

- An exact project name may benefit from keyword and metadata search.
- A broad conceptual question may benefit from semantic search.
- A request about a previous event requires temporal filtering.
- A request involving multiple related memories may require relationship-aware retrieval.

## 4.1 Responsibilities

- Identify retrieval requirements.
- Select search methods.
- Select relevant memory categories.
- Determine temporal filtering requirements.
- Identify relationship expansion requirements.
- Estimate retrieval complexity.
- Select initial retrieval depth.
- Apply resource and access constraints.

## 4.2 Available Retrieval Methods

| Method | Suitable use |
|---|---|
| Semantic search | Conceptual and meaning-based queries |
| Keyword search | Exact names, phrases and technical terms |
| Metadata search | Categories, ownership and status |
| Structured search | Specific subjects, attributes and values |
| Entity search | People, companies, projects and products |
| Temporal search | Historical and time-sensitive queries |
| Relationship search | Connected memories and contextual exploration |

## 4.3 Strategy Selection Examples

| User query | Recommended strategy |
|---|---|
| "What is my current project?" | Structured + semantic + temporal |
| "What was my internship company?" | Keyword + entity + temporal |
| "What technologies did I use in Raven?" | Entity + relationship + semantic |
| "What do I prefer?" | Semantic + category filtering |
| "What changed in my goals?" | Temporal + relationship + structured |
| "What did I decide about the database?" | Keyword + project context + decision category |

## 4.4 Adaptive Retrieval

Raven should select retrieval methods based on query complexity.

Simple queries should avoid unnecessary retrieval operations.

Complex queries may combine multiple retrieval methods.

The selection process must account for:

- Query specificity.
- Required precision.
- Available context.
- Memory category.
- Temporal requirements.
- Expected retrieval depth.
- Resource constraints.

## 4.5 Processing Algorithm

1. Receive structured query.
2. Determine query complexity.
3. Identify relevant memory categories.
4. Identify exact-match requirements.
5. Identify semantic search requirements.
6. Determine temporal filters.
7. Determine relationship expansion requirements.
8. Select retrieval methods.
9. Set initial retrieval depth.
10. Generate retrieval execution plan.

## 4.6 Pseudocode

```text
FUNCTION select_retrieval_strategy(query):

    strategy = initialize_strategy()

    IF query.requires_exact_identifier:
        strategy.add(KEYWORD_SEARCH)

    IF query.requires_conceptual_matching:
        strategy.add(SEMANTIC_SEARCH)

    IF query.has_structured_attributes:
        strategy.add(STRUCTURED_SEARCH)

    IF query.references_entities:
        strategy.add(ENTITY_SEARCH)

    IF query.has_temporal_constraints:
        strategy.add(TEMPORAL_FILTERING)

    IF query.requires_connected_context:
        strategy.add(RELATIONSHIP_SEARCH)

    strategy = optimize_strategy_for_query(
        strategy,
        query.complexity
    )

    RETURN strategy
```

## 4.7 Output Contract

- Query identifier.
- Selected retrieval methods.
- Category filters.
- Entity filters.
- Temporal constraints.
- Relationship requirements.
- Initial retrieval depth.
- Execution priority.
- Resource budget.

## 4.8 Acceptance Criteria

- AC-01: Retrieval strategy reflects query intent.
- AC-02: Exact queries can use keyword search.
- AC-03: Conceptual queries can use semantic search.
- AC-04: Structured attributes can be filtered.
- AC-05: Temporal queries receive appropriate filtering.
- AC-06: Related-memory retrieval can be enabled.
- AC-07: Simple queries avoid unnecessary processing.
- AC-08: Strategy decisions are traceable.

**Specification status:** COMPLETE.

---

# Algorithm 6.4.3 — Hybrid Memory Search

**Algorithm ID:** 6.4.3  
**Status:** Specification

## 5. Purpose

Search authoritative memory records using multiple retrieval methods.

The objective is to identify a sufficiently broad set of potentially relevant memories without relying on a single search technique.

## 5.1 Responsibilities

- Execute semantic search.
- Execute keyword search.
- Execute metadata filtering.
- Execute structured attribute search.
- Execute entity-based search.
- Retrieve candidate memories.
- Preserve source references.
- Combine search results.
- Remove unintended duplicate search results.

## 5.2 Retrieval Sources

### Semantic Index

Used for meaning-based similarity.

Examples:

- "What are my career ambitions?"
- "What professional direction did I discuss?"

### Keyword Index

Used for exact words, names and phrases.

Examples:

- Project names.
- Company names.
- Technology names.
- Specific dates or identifiers.

### Structured Metadata

Used for:

- Memory categories.
- User scope.
- Memory status.
- Importance.
- Temporal information.
- Entity references.

### Relationship Index

Used for linked memory records and associated entities.

## 5.3 Hybrid Search Architecture

```text
Normalized Query
       |
       +------------------+
       |                  |
       v                  v
 Semantic Search      Keyword Search
       |                  |
       v                  v
 Semantic Results     Keyword Results
       |                  |
       +---------+--------+
                 |
                 v
         Structured Filtering
                 |
                 v
          Result Combination
                 |
                 v
          Candidate Memories
```

Entity and relationship search may operate alongside these methods when selected by the retrieval strategy.

## 5.4 Result Combination

Search results from different retrieval methods must be combined without assuming that their raw scores are directly comparable.

Possible combination approaches:

- Rank-based fusion.
- Normalized ranking signals.
- Weighted retrieval scores after calibration.

The final combination method will be selected during implementation and evaluation.

## 5.5 Search Constraints

Search must respect:

- User ownership.
- Authorization.
- Memory lifecycle state.
- Category filters.
- Temporal constraints.
- Data retention.
- Privacy restrictions.

Historical or superseded records may be retrieved when the query explicitly requests historical information.

They must not be treated as current memories.

## 5.6 Processing Algorithm

1. Receive retrieval plan.
2. Execute selected search methods.
3. Retrieve authorized memory references.
4. Apply metadata constraints.
5. Apply category filters.
6. Combine search results.
7. Deduplicate repeated search references.
8. Preserve retrieval method provenance.
9. Return candidate memory records.

## 5.7 Pseudocode

```text
FUNCTION hybrid_memory_search(query, strategy):

    results = []

    IF strategy.includes(SEMANTIC_SEARCH):
        results += semantic_search(query)

    IF strategy.includes(KEYWORD_SEARCH):
        results += keyword_search(query)

    IF strategy.includes(STRUCTURED_SEARCH):
        results += structured_search(query)

    IF strategy.includes(ENTITY_SEARCH):
        results += entity_search(query)

    results = enforce_user_scope(results, query.user_id)

    results = apply_authorized_filters(results, query)

    results = combine_search_results(results)

    results = deduplicate_result_references(results)

    RETURN results
```

## 5.8 Acceptance Criteria

- AC-01: Semantic search is supported.
- AC-02: Keyword search is supported.
- AC-03: Structured filtering is supported.
- AC-04: Entity-based search is supported.
- AC-05: Search results retain provenance.
- AC-06: User isolation is enforced.
- AC-07: Different search scores are not blindly combined.
- AC-08: Repeated search references are deduplicated.
- AC-09: Historical records are distinguishable from current records.

**Specification status:** COMPLETE.

---

# Algorithm 6.4.4 — Context & Temporal Filtering

**Algorithm ID:** 6.4.4  
**Status:** Specification

## 6. Purpose

Filter retrieved memory candidates based on their context, temporal validity and lifecycle state.

Its objective is to ensure that Raven retrieves information appropriate to the user's actual request.

## 6.1 Responsibilities

- Apply contextual filters.
- Apply temporal filters.
- Identify current and historical information.
- Exclude invalid memory states.
- Preserve relevant historical information.
- Identify expired information.
- Evaluate context compatibility.

## 6.2 Context Filtering

Consider:

- Project.
- Organization.
- Person.
- Event.
- Preference.
- Goal.
- Activity.
- Geographic context.
- Professional or personal context.

Example:

The user has discussed two different projects.

A query about Raven must not return an unrelated project merely because both involve AI.

## 6.3 Temporal Filtering

Raven must support:

- Current memories.
- Historical memories.
- Future intentions.
- Time-bound events.
- Recurring events.
- Expired commitments.
- Superseded versions.

### Valid Time

When the information was true in the real world.

### Transaction Time

When Raven recorded the information.

These must remain distinguishable where available.

## 6.4 Lifecycle Filtering

Retrieval must distinguish:

| Memory state | Retrieval behaviour |
|---|---|
| Active | Eligible for normal retrieval |
| Historical | Retrieve when relevant to historical queries |
| Superseded | Retrieve when history or change is requested |
| Expired | Retrieve only when historical context is relevant |
| Deleted | Must not be returned |
| Pending or candidate | Must not be treated as authoritative memory |

Actual lifecycle values must remain aligned with Phase 5.4 and the Memory Engine lifecycle model.

## 6.5 Processing Algorithm

1. Receive candidate memories.
2. Validate ownership and lifecycle.
3. Apply category and context constraints.
4. Apply temporal constraints.
5. Identify current versus historical records.
6. Exclude deleted records.
7. Exclude unvalidated candidates.
8. Preserve historical records when requested.
9. Return filtered memories.

## 6.6 Pseudocode

```text
FUNCTION filter_memory_context(memories, query):

    filtered = []

    FOR EACH memory IN memories:

        IF NOT authorized_for_user(memory, query.user_id):
            CONTINUE

        IF memory.status == DELETED:
            CONTINUE

        IF memory.status == CANDIDATE:
            CONTINUE

        IF NOT context_is_compatible(memory, query):
            CONTINUE

        IF NOT temporal_constraints_match(memory, query):
            CONTINUE

        filtered.append(memory)

    RETURN filtered
```

## 6.7 Acceptance Criteria

- AC-01: User ownership is enforced.
- AC-02: Contextually incompatible memories are filtered.
- AC-03: Current and historical memories are distinguished.
- AC-04: Superseded memories can be retrieved for historical queries.
- AC-05: Deleted memories are never returned.
- AC-06: Unvalidated candidates are not treated as authoritative.
- AC-07: Relative temporal queries are interpreted using available timestamps.
- AC-08: Missing temporal information is not invented.

**Specification status:** COMPLETE.

---

# Algorithm 6.4.5 — Relationship-Aware Retrieval

**Algorithm ID:** 6.4.5  
**Status:** Specification

## 7. Purpose

Retrieve additional memories connected to an initial result through known memory relationships.

Its objective is to provide useful surrounding context when a single memory is insufficient to answer a query.

## 7.1 Responsibilities

- Identify relevant memory relationships.
- Retrieve connected memories.
- Evaluate relationship types.
- Control relationship expansion.
- Preserve relationship provenance.
- Prevent irrelevant graph expansion.

## 7.2 Relationship Types

Use the relationship types defined in Phase 6.3 and Phase 5.4.

Examples:

- `RELATED_TO`
- `SUPPORTS`
- `CONTRADICTS`
- `UPDATES`
- `SUPERSEDES`
- `PART_OF`
- `DERIVED_FROM`
- `DEPENDS_ON`
- `ABOUT_ENTITY`

## 7.3 Retrieval Examples

Initial memory:

"The user is building Raven."

Related memories may include:

- Raven's technology stack.
- Raven's architecture decisions.
- Raven's current development phase.
- Raven's project goals.

These memories may improve the answer when the query asks for broader project context.

However, a simple question about Raven's programming language may not require retrieving every associated project memory.

## 7.4 Relationship Expansion Rules

- Expand only when relationships are relevant to the query.
- Prefer direct and meaningful relationships.
- Respect user ownership.
- Limit traversal depth.
- Avoid repeated traversal.
- Preserve relationship direction.
- Distinguish supporting information from contradictory information.
- Do not treat all connected memories as equally relevant.

## 7.5 Processing Algorithm

1. Receive initial retrieved memories.
2. Identify relevant relationships.
3. Determine which relationship types support the query.
4. Retrieve connected memory references.
5. Validate ownership and lifecycle.
6. Evaluate contextual relevance.
7. Limit expansion according to retrieval budget.
8. Add relevant memories to the result set.
9. Preserve relationship provenance.

## 7.6 Pseudocode

```text
FUNCTION retrieve_related_memories(initial_results, query):

    expanded = []

    FOR EACH memory IN initial_results:

        relationships = find_memory_relationships(memory)

        FOR EACH relationship IN relationships:

            IF NOT relationship_relevant_to_query(
                relationship,
                query
            ):
                CONTINUE

            related_memory = retrieve_target_memory(relationship)

            IF NOT authorized_for_user(related_memory, query.user_id):
                CONTINUE

            IF context_is_compatible(related_memory, query):
                expanded.append(related_memory)

    RETURN deduplicate_and_rank(expanded)
```

## 7.7 Acceptance Criteria

- AC-01: Related memories can be retrieved.
- AC-02: Relationship types influence expansion.
- AC-03: Irrelevant relationships are excluded.
- AC-04: Traversal is bounded.
- AC-05: Repeated memories are deduplicated.
- AC-06: Relationship provenance is preserved.
- AC-07: Ownership and lifecycle restrictions are enforced.
- AC-08: Contradictory relationships remain identifiable.

**Specification status:** COMPLETE.

---

# Algorithm 6.4.6 — Memory Ranking & Scoring

**Algorithm ID:** 6.4.6  
**Status:** Specification

## 8. Purpose

Rank retrieved memory candidates according to their usefulness for the current query.

The objective is to prioritize memories that best match the requested information while considering context, temporal relevance, importance and evidence quality.

Semantic similarity alone must not determine the final ranking.

## 8.1 Responsibilities

- Calculate retrieval relevance.
- Consider query-memory similarity.
- Consider contextual compatibility.
- Consider temporal relevance.
- Consider memory importance.
- Consider fact confidence.
- Consider freshness.
- Consider evidence quality.
- Rank retrieved memories.

## 8.2 Ranking Dimensions

| Dimension | Purpose |
|---|---|
| Query relevance | How closely the memory answers the query |
| Semantic similarity | Meaning-based similarity |
| Context compatibility | Whether the memory belongs to the correct context |
| Temporal relevance | Whether its time period matches the request |
| Importance | Long-term value of the memory |
| Fact confidence | Strength of evidence supporting the fact |
| Freshness | Currentness of the information |
| Relationship relevance | Value of its connection to other memories |

## 8.3 Ranking Model

A conceptual ranking function may be represented as:

\[
S_r =
w_qQ +
w_sS +
w_cC +
w_tT +
w_iI +
w_fF +
w_nN +
w_rR
\]

Where:

- \(Q\): Query relevance.
- \(S\): Semantic similarity.
- \(C\): Context compatibility.
- \(T\): Temporal relevance.
- \(I\): Memory importance.
- \(F\): Fact confidence.
- \(N\): Freshness.
- \(R\): Relationship relevance.
- \(w\): Configurable weights.

This is a conceptual ranking model.

Weights must be calibrated and validated during implementation.

Not every dimension must apply to every query.

For example, freshness should not dominate a query asking for a historical event.

## 8.4 Query-Specific Ranking

### Current-State Query

Prioritize:

- Current validity.
- Temporal relevance.
- Fact confidence.
- Context compatibility.

### Historical Query

Prioritize:

- Historical time match.
- Valid-time information.
- Source evidence.
- Context compatibility.

### Preference Query

Prioritize:

- Preference category.
- Current validity.
- Repeated independent evidence where relevant.
- Explicitness and confidence.

### Project Query

Prioritize:

- Project entity match.
- Project context.
- Related decisions.
- Current project state.
- Relevant historical revisions when requested.

## 8.5 Ranking Rules

1. Contextually incompatible memories must not rank highly simply because of semantic similarity.
2. Superseded memories must not outrank current memories for current-state queries.
3. Historical memories may rank highly for historical queries.
4. Importance must not override query relevance.
5. Low-confidence information must not be presented as established fact.
6. Missing scores must not automatically become zero.
7. Conflicting information must remain distinguishable.
8. Ranking decisions must be traceable.

## 8.6 Processing Algorithm

1. Receive filtered memory candidates.
2. Calculate query relevance.
3. Calculate semantic similarity.
4. Evaluate context compatibility.
5. Evaluate temporal relevance.
6. Retrieve importance and confidence metadata.
7. Evaluate freshness where applicable.
8. Evaluate relationship relevance.
9. Apply query-specific ranking policy.
10. Rank candidates.
11. Preserve score explanations.

## 8.7 Pseudocode

```text
FUNCTION rank_memories(memories, query):

    ranked = []

    FOR EACH memory IN memories:

        relevance = evaluate_query_relevance(memory, query)

        semantic = evaluate_semantic_similarity(memory, query)

        context = evaluate_context_compatibility(memory, query)

        temporal = evaluate_temporal_relevance(memory, query)

        importance = memory.importance

        confidence = memory.fact_confidence

        freshness = evaluate_freshness(memory, query)

        relationship = evaluate_relationship_relevance(
            memory,
            query
        )

        score = calculate_query_specific_ranking(
            relevance,
            semantic,
            context,
            temporal,
            importance,
            confidence,
            freshness,
            relationship
        )

        ranked.append(memory, score)

    RETURN sort_by_ranking(ranked)
```

## 8.8 Acceptance Criteria

- AC-01: Memories are ranked by query relevance.
- AC-02: Context compatibility affects ranking.
- AC-03: Temporal relevance is query-specific.
- AC-04: Importance and confidence remain separate.
- AC-05: Historical and current queries use different ranking policies.
- AC-06: Low-confidence information is not presented as confirmed.
- AC-07: Ranking decisions are explainable.
- AC-08: Missing score values are handled explicitly.

**Specification status:** COMPLETE.

---

# Algorithm 6.4.7 — Evidence & Confidence Filtering

**Algorithm ID:** 6.4.7  
**Status:** Specification

## 9. Purpose

Evaluate whether retrieved memories have sufficient evidence and confidence to be included in the final retrieval result.

This algorithm prevents Raven from presenting weakly supported, outdated or ambiguous information as established fact.

## 9.1 Responsibilities

- Validate provenance.
- Evaluate evidence completeness.
- Evaluate fact confidence.
- Identify uncertain information.
- Identify unsupported conclusions.
- Identify source conflicts.
- Determine whether a result can be returned.
- Preserve uncertainty in retrieval output.

## 9.2 Evidence Requirements

A retrieved memory should retain:

- Original source reference.
- Supporting text or evidence reference where available.
- Speaker attribution.
- Source timestamp.
- Extraction history.
- Evaluation metadata.
- Resolution history where relevant.

## 9.3 Confidence Levels

Conceptual confidence categories:

| Level | Meaning |
|---|---|
| Very High | Strong and direct supporting evidence |
| High | Good supporting evidence with limited uncertainty |
| Medium | Reasonable support with some ambiguity |
| Low | Weak or incomplete evidence |
| Insufficient | Not enough evidence to support the proposition |

These are conceptual categories.

Numerical boundaries must be calibrated during evaluation.

## 9.4 Filtering Rules

### Strong Evidence

Include normally when relevant.

### Moderate Evidence

Include when appropriate, preserving any uncertainty.

### Weak Evidence

Include only when useful and clearly qualified, or exclude according to the query's requirements.

### Insufficient Evidence

Do not present as an established fact.

### Contradictory Evidence

Preserve conflicting results and their temporal or source context.

Do not silently select one unless the resolution history supports that decision.

## 9.5 Explicit and Inferred Memories

Explicit memories and inferred memories must remain distinguishable.

An inferred memory must retain:

- Supporting evidence.
- Inference confidence.
- Classification provenance.
- Review status.

A low-confidence inference must not be presented as an explicit user statement.

## 9.6 Processing Algorithm

1. Receive ranked memories.
2. Validate source references.
3. Validate provenance.
4. Inspect fact confidence.
5. Inspect inference confidence where applicable.
6. Check lifecycle state.
7. Identify contradictions.
8. Apply confidence policy.
9. Determine whether to include, qualify or exclude.
10. Return evidence-qualified results.

## 9.7 Pseudocode

```text
FUNCTION filter_evidence_and_confidence(memories, query):

    accepted = []

    FOR EACH memory IN memories:

        IF NOT validate_provenance(memory):
            CONTINUE

        IF memory.status == DELETED:
            CONTINUE

        confidence = evaluate_retrieval_confidence(memory)

        IF confidence == INSUFFICIENT:
            CONTINUE

        IF memory.has_unresolved_conflict:
            mark_as_conflicting(memory)

        IF memory.origin_type == INFERRED:
            preserve_inference_label(memory)

        IF confidence == LOW:
            mark_uncertainty(memory)

        accepted.append(memory)

    RETURN accepted
```

## 9.8 Acceptance Criteria

- AC-01: Provenance is validated.
- AC-02: Evidence completeness is considered.
- AC-03: Confidence levels are preserved.
- AC-04: Inferred memories remain identifiable.
- AC-05: Low-confidence information is qualified.
- AC-06: Insufficiently supported information is not presented as confirmed.
- AC-07: Conflicting evidence remains distinguishable.
- AC-08: Deleted memories are excluded.
- AC-09: Filtering decisions are traceable.

**Specification status:** COMPLETE.

---

# Algorithm 6.4.8 — Dynamic Top-K & Retrieval Expansion

**Algorithm ID:** 6.4.8  
**Status:** Specification

## 10. Purpose

Determine how many memories Raven should retrieve and whether additional retrieval operations are necessary.

A fixed number of retrieved memories is not appropriate for every query.

A simple fact question may require one memory, whereas a project summary may require multiple connected memories.

## 10.1 Responsibilities

- Determine initial retrieval depth.
- Adapt result count.
- Identify insufficient result coverage.
- Expand retrieval when necessary.
- Control retrieval budgets.
- Prevent unnecessary search operations.
- Apply early stopping.
- Preserve retrieval completeness information.

## 10.2 Dynamic Top-K

Top-K represents the number of memory candidates retrieved or retained for further processing.

The appropriate value depends on:

- Query complexity.
- Number of requested facts.
- Required retrieval depth.
- Available relevant memories.
- Confidence of current results.
- Contextual coverage.
- Contradiction presence.
- Resource budget.

## 10.3 Query Complexity

| Query complexity | Example | Retrieval behaviour |
|---|---|---|
| Simple | "What language am I learning?" | Small result set |
| Moderate | "What is my current project stack?" | Multiple relevant memories |
| Complex | "Summarize my Raven architecture decisions." | Broader retrieval |
| Historical comparison | "How have my career goals changed?" | Multiple time periods and revisions |

## 10.4 Retrieval Expansion Conditions

Additional retrieval may be required when:

- Too few relevant results are found.
- Important requested attributes are missing.
- Multiple related memories are necessary.
- Contradictory evidence needs examination.
- Contextual coverage is insufficient.
- Confidence is too low to answer reliably.

## 10.5 Early Stopping

Retrieval may stop when:

- Required information has been found.
- Evidence coverage is sufficient.
- Relevant result ranking is stable.
- Additional search is unlikely to materially improve the answer.
- The retrieval budget is exhausted.

A search budget must not force Raven to claim completeness when information is missing.

## 10.6 Processing Algorithm

1. Receive ranked and evidence-filtered results.
2. Determine requested information coverage.
3. Compare result count against query requirements.
4. Identify missing attributes or context.
5. Determine whether relationship expansion is required.
6. Determine whether more search is useful.
7. Expand retrieval using an adjusted strategy.
8. Re-rank additional results.
9. Stop when sufficient coverage is achieved or the budget is exhausted.
10. Record retrieval completeness.

## 10.7 Pseudocode

```text
FUNCTION dynamic_retrieval(query, initial_results, budget):

    results = initial_results

    WHILE budget.has_remaining_capacity:

        coverage = evaluate_query_coverage(
            query,
            results
        )

        IF coverage.is_sufficient:
            BREAK

        missing = identify_missing_information(
            query,
            results
        )

        IF NOT additional_retrieval_is_useful(missing):
            BREAK

        expanded = retrieve_additional_memories(
            query,
            missing
        )

        results = combine_and_rank(results, expanded)

        budget.consume()

    completeness = evaluate_query_coverage(query, results)

    RETURN results, completeness
```

## 10.8 Acceptance Criteria

- AC-01: Retrieval depth adapts to query complexity.
- AC-02: Simple queries avoid excessive retrieval.
- AC-03: Complex queries can expand retrieval.
- AC-04: Missing information can trigger additional search.
- AC-05: Retrieval budgets are respected.
- AC-06: Early stopping is supported.
- AC-07: Budget exhaustion is distinguishable from complete retrieval.
- AC-08: Additional results are re-ranked.
- AC-09: Retrieval completeness is recorded.

**Specification status:** COMPLETE.

---

# Algorithm 6.4.9 — Retrieval Assembly & Output Validation

**Algorithm ID:** 6.4.9  
**Status:** Specification

## 11. Purpose

Assemble the final structured retrieval result from the ranked, evidence-qualified memory records.

The objective is to provide downstream components with relevant information in a consistent and traceable format.

The Memory Engine returns structured retrieval results. The Agent Orchestrator remains responsible for integrating memory results with other engine outputs and assembling the final user-facing response.

## 11.1 Responsibilities

- Assemble retrieved memory records.
- Remove duplicate references.
- Preserve ranking.
- Preserve temporal context.
- Preserve confidence and provenance.
- Identify conflicting information.
- Identify incomplete retrieval.
- Validate output structure.
- Enforce ownership and access rules.
- Return structured results.

## 11.2 Output Contract

Conceptual output:

| Attribute | Purpose |
|---|---|
| `retrieval_id` | Unique retrieval operation |
| `query_id` | Original query reference |
| `user_id` | User scope |
| `retrieved_memories` | Retrieved memory records |
| `ranking_metadata` | Ranking information |
| `evidence_references` | Supporting provenance |
| `temporal_context` | Current or historical context |
| `confidence_metadata` | Confidence information |
| `relationship_metadata` | Relevant memory relationships |
| `conflicts` | Identified conflicts |
| `completeness_status` | Retrieval completeness |
| `retrieval_status` | Overall result |
| `processing_version` | Retrieval version |
| `created_at` | Completion timestamp |

## 11.3 Retrieval Status

Conceptual statuses:

- `completed`
- `completed_with_warnings`
- `partial`
- `no_results`
- `needs_clarification`
- `failed`
- `cancelled`

## 11.4 Output Validation

Before returning results:

1. Validate user ownership.
2. Validate memory lifecycle.
3. Check that deleted memories are excluded.
4. Check that provenance references exist.
5. Verify ranking metadata.
6. Preserve historical and current distinctions.
7. Preserve inference labels.
8. Preserve conflict information.
9. Remove unintended duplicate result references.
10. Validate output structure.

## 11.5 Processing Algorithm

1. Receive final filtered and ranked memories.
2. Deduplicate memory references.
3. Assemble relevant memory records.
4. Attach evidence references.
5. Attach confidence metadata.
6. Attach temporal context.
7. Attach relationship information where relevant.
8. Attach conflict information.
9. Determine completeness status.
10. Validate output.
11. Return structured retrieval result.

## 11.6 Pseudocode

```text
FUNCTION assemble_retrieval_output(query, memories):

    results = deduplicate_memory_references(memories)

    results = preserve_ranking(results)

    results = attach_provenance(results)

    results = attach_temporal_context(results)

    results = attach_confidence_metadata(results)

    results = attach_relationship_metadata(results)

    conflicts = identify_unresolved_conflicts(results)

    completeness = evaluate_query_coverage(
        query,
        results
    )

    output = create_retrieval_result(
        query,
        results,
        conflicts,
        completeness
    )

    validate_retrieval_output(output)

    RETURN output
```

## 11.7 Failure Handling

| Failure | Expected behaviour |
|---|---|
| No matching memories | Return `no_results` |
| Missing provenance | Exclude or qualify affected result |
| Invalid memory reference | Reject affected record |
| Ownership violation | Reject retrieval |
| Partial search failure | Preserve valid results and mark partial |
| Ranking failure | Use approved fallback or fail safely |
| Output validation failure | Do not return invalid result |
| Retrieval cancellation | Preserve operation state |

## 11.8 Acceptance Criteria

- AC-01: Results are returned in a structured format.
- AC-02: Ranking is preserved.
- AC-03: Provenance is included.
- AC-04: Temporal context is retained.
- AC-05: Confidence metadata is included.
- AC-06: Conflicting information remains distinguishable.
- AC-07: Deleted memories are excluded.
- AC-08: User ownership is enforced.
- AC-09: Partial retrieval is explicitly represented.
- AC-10: Empty results are distinguishable from failures.
- AC-11: Output is validated before returning.
- AC-12: The Memory Engine does not assume ownership of final cross-engine response assembly.

**Specification status:** COMPLETE.

---

# 12. Cross-Algorithm Data Flow

| Algorithm | Input | Output |
|---|---|---|
| 6.4.1 Query Understanding | User query | Structured retrieval query |
| 6.4.2 Strategy Selection | Structured query | Retrieval plan |
| 6.4.3 Hybrid Search | Retrieval plan | Candidate memories |
| 6.4.4 Context & Temporal Filtering | Candidate memories | Filtered memories |
| 6.4.5 Relationship-Aware Retrieval | Filtered memories | Related memories |
| 6.4.6 Ranking & Scoring | Retrieved memories | Ranked memories |
| 6.4.7 Evidence & Confidence Filtering | Ranked memories | Evidence-qualified results |
| 6.4.8 Dynamic Top-K | Qualified results | Sufficient retrieval set |
| 6.4.9 Retrieval Assembly | Final result set | Structured retrieval output |

---

# 13. Shared Security and Privacy Requirements

1. Enforce user ownership during every retrieval operation.
2. Apply authorization before searching private records.
3. Never expose another user's memories.
4. Exclude deleted memories.
5. Preserve private and shared entity boundaries.
6. Prevent unvalidated candidates from being presented as authoritative memory.
7. Validate provenance references.
8. Avoid exposing unnecessary sensitive content in logs.
9. Respect memory retention and deletion policies.
10. Ensure cached retrieval results cannot bypass authorization or deletion.

---

# 14. Performance and Resource Considerations

Quality takes priority over retrieval speed and cost.

The retrieval architecture should support:

- Hybrid search.
- Metadata pre-filtering.
- Bounded semantic search.
- Efficient candidate ranking.
- Selective relationship expansion.
- Dynamic Top-K.
- Retrieval caching with safe invalidation.
- Controlled concurrency.
- Early stopping.
- Reuse of valid search results.

Caching must not return deleted, unauthorized or stale memory records.

Exact search infrastructure, embedding models, ranking weights, thresholds and performance targets will be selected during subsequent implementation and evaluation phases.

---

# 15. Evaluation Metrics

| Area | Metrics |
|---|---|
| Query understanding | Intent accuracy, entity extraction accuracy |
| Strategy selection | Retrieval strategy accuracy |
| Hybrid search | Recall@K, Precision@K |
| Context filtering | Contextual precision |
| Temporal retrieval | Temporal correctness |
| Relationship retrieval | Relevant relationship retrieval rate |
| Ranking | NDCG, Mean Reciprocal Rank |
| Evidence filtering | Evidence coverage, unsupported retrieval rate |
| Dynamic retrieval | Retrieval completeness, unnecessary expansion rate |
| Output assembly | Provenance completeness, output validation success |
| Reliability | Failure rate, recovery success |
| Privacy | Unauthorized retrieval incidents |

False retrieval of deleted or unauthorized memories must be treated as a critical failure.

Numerical targets will be established during Phase 12 using representative evaluation datasets.

---

# 16. Phase 6.4 Completion Criteria

Phase 6.4 is architecturally specified when:

- All nine algorithms have defined inputs and outputs.
- Query understanding and retrieval strategy selection are documented.
- Hybrid retrieval is defined.
- Context and temporal filtering are specified.
- Relationship-aware retrieval is defined.
- Ranking dimensions remain independent.
- Evidence and confidence filtering are documented.
- Dynamic retrieval depth is specified.
- Retrieval assembly and validation are documented.
- Security and privacy boundaries are defined.
- Failure and recovery behaviour is documented.
- Evaluation metrics are identified.

| Algorithm | Specification status |
|---|---|
| 6.4.1 — Query Understanding & Normalization | COMPLETE |
| 6.4.2 — Retrieval Strategy Selection | COMPLETE |
| 6.4.3 — Hybrid Memory Search | COMPLETE |
| 6.4.4 — Context & Temporal Filtering | COMPLETE |
| 6.4.5 — Relationship-Aware Retrieval | COMPLETE |
| 6.4.6 — Memory Ranking & Scoring | COMPLETE |
| 6.4.7 — Evidence & Confidence Filtering | COMPLETE |
| 6.4.8 — Dynamic Top-K & Retrieval Expansion | COMPLETE |
| 6.4.9 — Retrieval Assembly & Output Validation | COMPLETE |

**Important:** COMPLETE means algorithm specifications are documented. It does not mean retrieval infrastructure, vector indexes, ranking systems or evaluation tests have been implemented.

---

# 17. Dependencies

Phase 6.4 depends on:

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
- Phase 6.3 — Memory Resolution.

---

# 18. Next Phase

**Phase 6.5 — Memory Consolidation & Maintenance**

The next phase will define how Raven maintains the quality of stored memories over time.

It will cover:

- Memory decay.
- Importance-based retention.
- Freshness management.
- Memory consolidation.
- Episodic grouping.
- Semantic memory generation.
- Derived profile maintenance.
- Memory lifecycle maintenance.
- Scheduled and event-driven maintenance.
- Stale memory detection.
- Safe forgetting.
- Deletion propagation.
- Consolidation integrity.

Phase 6.5 will ensure that Raven does not simply accumulate memories indefinitely but continuously maintains their relevance, consistency and usefulness.

---

**Project:** Raven  
**Engine:** Memory Engine  
**Phase:** 6.4 — Memory Retrieval  
**Document:** `03-memory-retrieval.md`  
**Status:** ALL NINE ALGORITHM SPECIFICATIONS COMPLETE
