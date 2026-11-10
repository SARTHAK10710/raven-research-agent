# Phase 6.6 — Research Engine: Query Understanding & Information Discovery

**Project:** Raven Research Agent  
**Phase:** 6 — Algorithms & Processing Design  
**Subphase:** 6.6 — Query Understanding & Information Discovery  
**Status:** Architecture and algorithm specification  
**Optimization Priority:** Quality first  
**Processing Approach:** Hybrid — deterministic rules, conventional NLP/statistical methods, and selective non-generative ML

---

## 1. Purpose

The Research Engine receives research requests from the Agent Orchestrator and determines how to obtain the information required to answer them.

A research request may be:

- A simple factual question.
- A request to find information about a company or product.
- A comparison between multiple entities.
- A request for current information.
- A multi-part research question.
- An investigation requiring multiple independent sources.
- A request to update previously completed research.
- A question requiring historical and current information together.

The Research Engine must understand the information requirement before attempting discovery.

Its objective is not to collect as many documents as possible. It is to discover the most relevant and reliable information needed to satisfy the research objective.

### Core principles

1. Understand the research objective before discovering sources.
2. Reuse relevant historical research where appropriate.
3. Decompose complex requests into manageable research tasks.
4. Avoid unnecessary duplicate discovery.
5. Prefer authoritative and relevant sources.
6. Preserve the original research question and its context.
7. Distinguish current information from historical information.
8. Identify missing information and uncertainty early.
9. Adapt discovery depth to the research objective.
10. Never treat search-result similarity as proof of factual correctness.

---

# 2. Algorithm Inventory

This document defines eight algorithms.

| ID | Algorithm | Primary responsibility |
|---|---|---|
| 6.6.1 | Research Query Validation & Normalization | Validate and normalize incoming research requests |
| 6.6.2 | Research Intent Classification | Identify the type of research required |
| 6.6.3 | Query Context Enrichment | Add relevant context and constraints |
| 6.6.4 | Research Decomposition | Break complex requests into smaller questions |
| 6.6.5 | Research Plan Generation | Determine the research strategy |
| 6.6.6 | Historical Research Reuse | Reuse relevant existing research |
| 6.6.7 | Information Discovery Strategy | Select appropriate discovery methods |
| 6.6.8 | Source Discovery & Candidate Ranking | Find and prioritize candidate sources |

---

# 3. 6.6.1 — Research Query Validation & Normalization

## Purpose

Validate incoming research requests and convert them into a structured representation that downstream algorithms can process.

The algorithm must preserve the user's original meaning.

Normalization must not silently change the research objective.

## Input types

- Natural-language questions.
- Structured research requests.
- Comparison requests.
- Follow-up research requests.
- Requests referencing previous research.
- Requests containing explicit constraints.

## Validation dimensions

### A. Structural validation

Check:

- Query is present.
- Query is readable.
- Query length is within configured limits.
- Required metadata is present.
- Input encoding is valid.
- Request structure is supported.

### B. Semantic validation

Identify:

- Main subject.
- Requested information.
- Expected outcome.
- Explicit constraints.
- Time references.
- Geographic scope.
- Comparison entities.
- Requested research depth.

### C. Context validation

Check whether the request references:

- A previous research session.
- A previous result.
- A known entity.
- A specific date or time period.
- A follow-up question.

## Normalization operations

Possible operations:

- Whitespace normalization.
- Unicode normalization.
- Punctuation normalization where safe.
- Query segmentation.
- Entity mention extraction.
- Date and time expression normalization.
- Identification of explicit constraints.

The original query must remain preserved.

## Algorithm

**Input:**

- Raw research query.
- User context reference.
- Research session reference, if available.
- Request metadata.

**Output:**

- Validated query.
- Normalized query.
- Extracted constraints.
- Validation status.

### Processing steps

1. Receive the research request.
2. Preserve the original query.
3. Validate input structure.
4. Validate supported input format.
5. Normalize text without changing meaning.
6. Identify explicit constraints.
7. Extract potential entities and temporal expressions.
8. Identify whether the request references existing research.
9. Produce a normalized query representation.
10. Return validation results.

### Pseudocode

```text
FUNCTION validate_and_normalize_query(request):

    validate_request_structure(request)

    preserve_original_query(request)

    IF query_is_empty(request):
        RETURN INVALID_QUERY

    normalized_query = normalize_text(
        request.query
    )

    constraints = extract_explicit_constraints(
        normalized_query
    )

    entities = extract_entity_mentions(
        normalized_query
    )

    temporal_context = extract_temporal_context(
        normalized_query
    )

    RETURN {
        original_query,
        normalized_query,
        constraints,
        entities,
        temporal_context,
        validation_status
    }
```

## Acceptance criteria

- Original query is preserved.
- Normalization does not alter user intent.
- Invalid inputs are rejected safely.
- Explicit constraints are retained.
- Temporal expressions are not discarded.
- Follow-up references are preserved for later resolution.

---

# 4. 6.6.2 — Research Intent Classification

## Purpose

Determine what type of research the user is requesting.

Different research intents require different discovery and verification strategies.

For example, finding a company's founding date is different from comparing two companies or investigating a developing event.

## Research intent categories

| Intent | Description | Example |
|---|---|---|
| `FACT_LOOKUP` | Find a specific fact | When was a company founded? |
| `ENTITY_RESEARCH` | Research an entity comprehensively | Research a particular company |
| `COMPARISON` | Compare two or more subjects | Compare two database systems |
| `CURRENT_STATUS` | Find current information | What is the company's current pricing? |
| `HISTORICAL_RESEARCH` | Investigate historical information | How did the product evolve? |
| `TREND_ANALYSIS` | Identify patterns over time | How is the industry changing? |
| `EXPLANATORY_RESEARCH` | Explain a concept using evidence | How does a particular technology work? |
| `MULTI_PART_RESEARCH` | Answer several connected questions | Research a company's product, pricing, and competitors |
| `FOLLOW_UP_RESEARCH` | Continue an existing investigation | Find newer information about the same company |
| `VERIFICATION` | Validate an existing claim | Verify whether a reported statistic is accurate |

Multiple intents may coexist.

For example, a request to compare two products may require entity research, current-status discovery, and verification.

## Classification approach

Use a hybrid classification system:

1. Deterministic rules for explicit request patterns.
2. Conventional NLP for linguistic features.
3. Non-generative classifiers for intent signals.
4. Confidence evaluation.
5. Rule-based validation of the final classification.

ML predictions are signals, not final authority.

## Algorithm

**Input:**

- Normalized query.
- Extracted entities.
- Explicit constraints.
- Conversation context reference.

**Output:**

- Primary research intent.
- Secondary intents.
- Classification confidence.
- Ambiguity indicators.

### Processing steps

1. Analyze query structure.
2. Identify action words and requested outcomes.
3. Identify whether the request asks for current or historical information.
4. Detect comparison or verification requirements.
5. Identify multiple independent information requirements.
6. Generate intent candidates.
7. Score candidates using available features.
8. Select the primary intent.
9. Preserve secondary intents.
10. Mark ambiguous classifications for further interpretation.

### Pseudocode

```text
FUNCTION classify_research_intent(query):

    features = extract_query_features(query)

    candidates = generate_intent_candidates(features)

    scored_intents = score_intent_candidates(
        candidates,
        features
    )

    primary_intent = select_primary_intent(
        scored_intents
    )

    secondary_intents = identify_secondary_intents(
        scored_intents
    )

    IF classification_is_ambiguous(scored_intents):
        mark_for_contextual_resolution()

    RETURN {
        primary_intent,
        secondary_intents,
        confidence,
        ambiguity_status
    }
```

## Important rule

The system must not force every request into one intent category.

A request may legitimately contain multiple research objectives.

---

# 5. 6.6.3 — Query Context Enrichment

## Purpose

Add relevant contextual information to the research query without changing its original objective.

A query often requires additional context to be interpreted correctly.

For example:

"Compare their pricing."

This request cannot be interpreted reliably without knowing which entities "their" refers to.

## Context sources

- Current conversation context supplied by the Orchestrator.
- Existing research session references.
- Relevant historical research.
- Resolved entity references.
- Explicit user constraints.
- Temporal context.
- Geographic context.
- Previously established research scope.

The Research Engine must not independently access private Memory Engine records. Historical personal context must be provided through authorized interfaces.

## Context enrichment dimensions

| Dimension | Description |
|---|---|
| Entity context | Which entities are being discussed? |
| Temporal context | Which time period matters? |
| Geographic context | Which country or region applies? |
| Attribute context | Which properties are relevant? |
| Comparison context | Which entities or dimensions must be compared? |
| Historical context | What previous research is relevant? |
| Scope context | What should be included or excluded? |

## Algorithm

**Input:**

- Validated query.
- Intent classification.
- Authorized context references.
- Existing research session.

**Output:**

- Enriched query representation.
- Resolved contextual references.
- Missing-context indicators.
- Context provenance.

### Processing steps

1. Retrieve authorized contextual references.
2. Identify unresolved pronouns and entity references.
3. Resolve references using available context.
4. Identify relevant temporal and geographic constraints.
5. Retrieve existing research context when referenced.
6. Check whether the added context is compatible with the original query.
7. Preserve the original query.
8. Record the origin of each contextual addition.
9. Identify unresolved ambiguity.
10. Return the enriched representation.

### Pseudocode

```text
FUNCTION enrich_research_context(query, context):

    validate_context_access(context)

    references = identify_contextual_references(query)

    resolved = resolve_references(
        references,
        context
    )

    temporal = resolve_temporal_context(query, context)

    geographic = resolve_geographic_context(query, context)

    enriched_query = construct_enriched_query(
        query,
        resolved,
        temporal,
        geographic
    )

    validate_semantic_preservation(
        query,
        enriched_query
    )

    RETURN enriched_query
```

## Ambiguity handling

If multiple interpretations are plausible and materially change the research outcome:

- Preserve the ambiguity.
- Avoid arbitrary entity selection.
- Request clarification through the Orchestrator when necessary.

Do not ask the user unnecessary questions when context resolves the reference reliably.

---

# 6. 6.6.4 — Research Decomposition

## Purpose

Break complex research requests into smaller, independently manageable research questions.

A complex research request may require information from different sources and different discovery strategies.

Decomposition improves coverage, parallel execution, verification, and result organization.

## Example

Original request:

"Research Company X, its products, pricing, competitors, and recent funding."

Possible subtasks:

1. Identify Company X and its business.
2. Discover its products.
3. Find current pricing information.
4. Identify major competitors.
5. Find recent funding information.
6. Verify important claims.
7. Assemble the findings into a coherent report.

## Decomposition principles

- Preserve the original research objective.
- Create subtasks only when they contribute to the requested outcome.
- Identify dependencies.
- Avoid unnecessary fragmentation.
- Identify shared discovery opportunities.
- Allow independent tasks to run in parallel.
- Keep the original question connected to every subtask.

## Algorithm

**Input:**

- Enriched query.
- Primary and secondary intents.
- Research constraints.
- Existing research references.

**Output:**

- Research task list.
- Task dependencies.
- Coverage requirements.
- Completion criteria.

### Processing steps

1. Identify distinct information requirements.
2. Identify entities and attributes involved.
3. Determine which questions can be answered independently.
4. Identify dependencies between questions.
5. Identify common sources or discovery requirements.
6. Create the minimum useful set of subtasks.
7. Define expected outputs for each task.
8. Define evidence requirements.
9. Validate coverage against the original query.
10. Return the decomposition plan.

### Pseudocode

```text
FUNCTION decompose_research_query(query):

    requirements = extract_information_requirements(query)

    subtasks = generate_candidate_subtasks(
        requirements
    )

    subtasks = remove_redundant_subtasks(subtasks)

    dependencies = identify_task_dependencies(
        subtasks
    )

    coverage = map_subtasks_to_requirements(
        subtasks,
        requirements
    )

    IF coverage.is_incomplete:
        add_missing_subtasks()

    validate_decomposition(subtasks, dependencies)

    RETURN {
        subtasks,
        dependencies,
        coverage
    }
```

## Decomposition safeguards

- Do not split a simple factual query unnecessarily.
- Do not create tasks that have no connection to the original request.
- Do not omit important constraints during decomposition.
- Do not assume that every subtask requires independent source discovery.
- Shared source discovery should be reused where appropriate.

---

# 7. 6.6.5 — Research Plan Generation

## Purpose

Convert the decomposed research questions into an actionable research plan.

Decomposition identifies what needs to be answered.

Research planning determines how to answer it.

## Planning dimensions

- Research intent.
- Information requirements.
- Source types.
- Required freshness.
- Verification depth.
- Expected evidence.
- Dependencies.
- Available historical research.
- Resource and execution budgets.
- Completion criteria.

## Research depth levels

### Basic

For simple questions requiring a small amount of evidence.

### Standard

For ordinary multi-source research and comparisons.

### Deep

For complex, consequential, disputed, or explicitly comprehensive research.

These levels describe research effort, not fixed source counts or guaranteed accuracy.

## Algorithm

**Input:**

- Research subtasks.
- Intent classification.
- Context.
- Research constraints.
- Existing research references.
- Execution budgets.

**Output:**

- Research plan.
- Source discovery strategy.
- Verification requirements.
- Task priorities.
- Completion criteria.

### Processing steps

1. Review all research subtasks.
2. Determine the evidence required for each subtask.
3. Select appropriate source categories.
4. Determine freshness requirements.
5. Select verification depth.
6. Identify opportunities for shared discovery.
7. Determine task dependencies.
8. Assign task priorities.
9. Define resource and time budgets.
10. Define completion criteria.
11. Return the plan to the Orchestrator.

### Pseudocode

```text
FUNCTION generate_research_plan(decomposition):

    plan = initialize_research_plan()

    FOR EACH subtask IN decomposition.subtasks:

        requirements = identify_evidence_requirements(
            subtask
        )

        source_strategy = select_source_strategy(
            subtask,
            requirements
        )

        verification_depth = determine_verification_depth(
            subtask
        )

        task_plan = create_task_plan(
            subtask,
            source_strategy,
            verification_depth
        )

        add_to_plan(plan, task_plan)

    optimize_shared_discovery(plan)

    validate_plan_coverage(plan)

    RETURN plan
```

## Quality-first planning rule

The system must not reduce verification requirements simply because a query is expensive or time-consuming.

If resource limits prevent the required research depth, the plan must explicitly represent the limitation.

---

# 8. 6.6.6 — Historical Research Reuse

## Purpose

Determine whether previous research can be reused to satisfy all or part of a new request.

Raven should avoid repeating research unnecessarily.

However, historical findings may be outdated, incomplete, or based on different research objectives.

## Reuse categories

| Category | Meaning |
|---|---|
| `FULL_REUSE` | Existing research sufficiently answers the request |
| `PARTIAL_REUSE` | Some findings can be reused |
| `REUSE_WITH_REFRESH` | Existing research is useful but requires updates |
| `NEW_RESEARCH` | Existing research is insufficient or irrelevant |
| `NEEDS_REVIEW` | Existing research has unresolved quality or consistency issues |

## Matching dimensions

Evaluate:

- Entity identity.
- Research objective.
- Attribute coverage.
- Temporal compatibility.
- Geographic compatibility.
- Source quality.
- Verification status.
- Research completeness.
- Existing session relationships.

A similar query does not automatically mean the same research objective.

## Algorithm

**Input:**

- Current enriched query.
- Research intent.
- Existing research session references.
- Previous snapshots and findings.
- Freshness requirements.

**Output:**

- Reuse classification.
- Reusable finding references.
- Refresh requirements.
- Missing information.

### Processing steps

1. Identify relevant previous research sessions.
2. Compare research objectives.
3. Resolve entity identity.
4. Compare requested attributes.
5. Evaluate temporal compatibility.
6. Evaluate source reliability and verification status.
7. Identify missing information.
8. Determine which findings remain reusable.
9. Decide whether refresh is necessary.
10. Return a reuse decision with provenance.

### Pseudocode

```text
FUNCTION evaluate_historical_research(query):

    sessions = find_related_research_sessions(query)

    IF sessions.is_empty:
        RETURN NEW_RESEARCH

    evaluations = []

    FOR EACH session IN sessions:

        objective_match = compare_research_objectives(
            query,
            session
        )

        coverage = evaluate_attribute_coverage(
            query,
            session
        )

        freshness = evaluate_research_freshness(session)

        reliability = evaluate_existing_evidence(session)

        evaluations.append(
            evaluate_reuse_suitability(
                objective_match,
                coverage,
                freshness,
                reliability
            )
        )

    RETURN select_reuse_strategy(evaluations)
```

## Important rules

- Preserve the original research snapshot.
- Do not silently replace historical findings with current findings.
- Reuse only findings whose context matches the current request.
- Refresh information that is time-sensitive.
- Retain source references and verification metadata.
- Create a linked new research session when the objective materially changes.

---

# 9. 6.6.7 — Information Discovery Strategy

## Purpose

Select the appropriate discovery method for each research task.

Different information requirements need different discovery strategies.

For example:

- Company information may require official websites and filings.
- Technical research may require documentation and technical publications.
- Current pricing may require official pricing pages.
- Historical research may require archived sources and older publications.
- Scientific claims may require primary research and independent corroboration.

## Discovery methods

### A. Search-based discovery

Use search systems to identify candidate sources.

Suitable for:

- Broad research.
- Discovering unfamiliar entities.
- Finding recent information.
- Finding relevant publications.

### B. Direct-source discovery

Retrieve information from known authoritative sources.

Suitable for:

- Official documentation.
- Company websites.
- Government databases.
- Product pricing pages.
- Regulatory filings.

### C. Historical-source discovery

Search for historical publications, archived material, and earlier research snapshots.

Suitable for:

- Historical timelines.
- Product evolution.
- Earlier announcements.
- Changes over time.

### D. Structured-data discovery

Use structured datasets and records where available.

Suitable for:

- Financial information.
- Statistical datasets.
- Public records.
- Structured entity information.

### E. Existing-research discovery

Reuse information from previous research sessions.

Suitable for:

- Follow-up questions.
- Research updates.
- Comparisons involving previously researched entities.

## Strategy selection factors

- Research intent.
- Entity type.
- Attribute requirements.
- Required freshness.
- Expected source authority.
- Existing research coverage.
- Verification depth.
- Discovery cost.
- Source accessibility.

## Algorithm

**Input:**

- Research task.
- Research plan.
- Entity and attribute requirements.
- Historical research references.

**Output:**

- Selected discovery methods.
- Source categories.
- Discovery constraints.
- Expected evidence requirements.

### Processing steps

1. Identify the information type.
2. Identify the likely authoritative source categories.
3. Check available historical research.
4. Determine whether search-based discovery is necessary.
5. Determine whether direct-source discovery is preferable.
6. Identify structured data sources where applicable.
7. Determine source freshness requirements.
8. Define discovery boundaries.
9. Return the discovery strategy.

### Pseudocode

```text
FUNCTION select_discovery_strategy(task):

    information_type = classify_information_type(task)

    source_categories = identify_relevant_source_categories(
        information_type
    )

    historical_coverage = evaluate_existing_research(task)

    methods = []

    IF historical_coverage.is_reusable:
        methods.append(HISTORICAL_REUSE)

    IF task.requires_broad_discovery:
        methods.append(SEARCH_BASED_DISCOVERY)

    IF authoritative_sources_are_known:
        methods.append(DIRECT_SOURCE_DISCOVERY)

    IF structured_data_is_relevant:
        methods.append(STRUCTURED_DATA_DISCOVERY)

    validate_discovery_coverage(methods, task)

    RETURN {
        methods,
        source_categories,
        discovery_constraints
    }
```

## Adaptive discovery

The Research Engine may change discovery methods when:

- Initial results are insufficient.
- Sources are inaccessible.
- Conflicting evidence appears.
- Important attributes remain missing.
- A more authoritative source is identified.

Discovery should stop when the task's evidence and completion requirements are satisfied or the configured budget is exhausted.

---

# 10. 6.6.8 — Source Discovery & Candidate Ranking

## Purpose

Discover candidate sources and rank them according to their relevance to the research objective.

This algorithm selects sources for further extraction and evaluation.

It does not establish that their claims are correct.

Source verification is defined in a later Research Engine algorithm group.

## Source discovery inputs

- Search queries.
- Direct source targets.
- Source categories.
- Entity names and aliases.
- Research attributes.
- Temporal constraints.
- Geographic constraints.
- Existing source references.

## Candidate source metadata

Each candidate source should capture:

- Source reference.
- URL or identifier.
- Title.
- Domain or publisher.
- Publication timestamp, if available.
- Retrieval timestamp.
- Source type.
- Matched entities.
- Matched attributes.
- Discovery method.
- Preliminary relevance score.
- Accessibility status.

## Ranking dimensions

Evaluate:

1. Query relevance.
2. Entity match.
3. Attribute coverage.
4. Temporal relevance.
5. Geographic relevance.
6. Source category compatibility.
7. Preliminary authority indicators.
8. Discovery completeness.

These dimensions must remain independently inspectable.

A high relevance score does not establish source reliability.

## Candidate source ranking

A configurable scoring model may be used:

\[
S = w_rR + w_eE + w_aA + w_tT + w_gG
\]

Where:

- \(R\) = query relevance.
- \(E\) = entity match.
- \(A\) = attribute coverage.
- \(T\) = temporal relevance.
- \(G\) = geographic relevance.
- \(w\) = configurable weights.

This is an illustrative ranking model. The weights and calibration are deferred to evaluation.

Missing attributes must not automatically be treated as zero without considering whether they are applicable.

## Algorithm

**Input:**

- Discovery strategy.
- Search results.
- Direct-source results.
- Research requirements.
- Source metadata.

**Output:**

- Candidate source records.
- Ranked source list.
- Relevance metadata.
- Discovery coverage information.

### Processing steps

1. Execute the selected discovery methods.
2. Collect candidate source references.
3. Normalize source metadata.
4. Identify duplicate URLs and equivalent source records.
5. Resolve publisher and domain information where possible.
6. Match candidates to research entities.
7. Evaluate attribute coverage.
8. Evaluate temporal and geographic compatibility.
9. Calculate preliminary relevance.
10. Rank candidate sources.
11. Preserve source discovery provenance.
12. Return candidates for content extraction and evaluation.

### Pseudocode

```text
FUNCTION discover_and_rank_sources(task, strategy):

    results = execute_discovery_methods(strategy)

    candidates = normalize_source_results(results)

    candidates = deduplicate_source_candidates(candidates)

    FOR EACH source IN candidates:

        entity_match = evaluate_entity_match(source, task)

        attribute_coverage = evaluate_attribute_coverage(
            source,
            task
        )

        temporal_match = evaluate_temporal_compatibility(
            source,
            task
        )

        relevance = calculate_source_relevance(
            entity_match,
            attribute_coverage,
            temporal_match
        )

        attach_discovery_metadata(
            source,
            relevance
        )

    ranked_sources = rank_candidates(candidates)

    RETURN {
        ranked_sources,
        discovery_coverage,
        discovery_status
    }
```

## Duplicate source handling

The system must distinguish:

- Same URL discovered multiple times.
- Different URLs representing the same publication.
- Syndicated copies of the same article.
- Independent sources discussing the same claim.

Duplicate removal must not accidentally remove independent corroborating evidence.

## Source ranking safeguards

- Search-result position is not proof of authority.
- Domain reputation is only a preliminary signal.
- A source can be relevant but unreliable.
- A source can be authoritative but irrelevant to the specific question.
- Publication date must be distinguished from retrieval date.
- Inaccessible sources must not be treated as successfully inspected.
- Search snippets must not be represented as full-source evidence.

---

# 11. Research Query & Discovery Output Contract

The output of this algorithm group should follow a consistent conceptual structure.

```text
ResearchDiscoveryRequest:
    request_id
    user_id
    original_query
    normalized_query
    research_intents
    enriched_context
    entity_references
    temporal_constraints
    geographic_constraints
    research_subtasks
    task_dependencies
    research_plan
    historical_reuse_decision
    discovery_strategy
    candidate_sources
    source_relevance_metadata
    discovery_status
    processing_version
    created_at
```

This is a logical contract, not a finalized database schema.

The Research Engine should preserve references to the underlying sources and research records rather than copying unnecessary content between components.

---

# 12. Failure Handling

| Failure | Expected handling |
|---|---|
| Invalid query | Reject with validation status |
| Ambiguous entity | Resolve from context or request clarification |
| Intent classification uncertainty | Preserve multiple candidate intents |
| Incomplete decomposition | Re-evaluate task coverage |
| Historical research unavailable | Continue with new discovery |
| Search service unavailable | Retry within limits or use alternative discovery method |
| Duplicate results | Deduplicate without losing source identity |
| Source inaccessible | Record inaccessible status and discover alternatives |
| Insufficient sources | Expand discovery within configured budget |
| Discovery budget exhausted | Return partial discovery status |
| Context access denied | Do not access restricted information |
| Stale historical research | Reuse only with explicit freshness qualification or refresh |

Partial discovery is a valid result.

The system must not claim that research is complete merely because candidate sources were found.

---

# 13. Security & Privacy Requirements

1. Every request must retain its user and execution scope.
2. Context enrichment must use authorized context only.
3. Research sessions must remain isolated by user unless explicitly shared.
4. External source content must be treated as untrusted input.
5. Retrieved instructions must never override Raven's system policies.
6. Search and discovery operations must not expose private Memory Engine content.
7. Source metadata and URLs must retain provenance.
8. Sensitive query information must not be unnecessarily exposed to external services.
9. Discovery logs must avoid storing unnecessary sensitive content.
10. Cross-engine context must be passed through authorized interfaces.

---

# 14. Evaluation Metrics

These metrics will be evaluated during Phase 12.

| Area | Metric |
|---|---|
| Query validation | Valid query acceptance rate |
| Normalization | Semantic preservation accuracy |
| Intent classification | Classification precision and recall |
| Context enrichment | Entity reference resolution accuracy |
| Decomposition | Research requirement coverage |
| Decomposition | Unnecessary subtask rate |
| Planning | Plan completeness |
| Historical reuse | Reuse decision accuracy |
| Historical reuse | Unnecessary rediscovery rate |
| Discovery strategy | Appropriate method selection |
| Source discovery | Relevant source recall |
| Source ranking | Ranking quality |
| Duplicate handling | Duplicate detection accuracy |
| Discovery | Missing-information detection rate |
| Reliability | Partial discovery reporting accuracy |

Numerical targets will be established during Phase 12.

---

# 15. Dependencies

This algorithm group depends on:

- Phase 3 — Research Engine Architecture.
- Phase 5.3 — Core Entities & Relationships.
- Phase 5.5 — Research Engine Data Models.
- Phase 6.1 — Shared Algorithm Framework.
- Phase 6.4 — Memory Retrieval, for shared conceptual retrieval principles.
- Phase 4 — Agent Orchestrator Architecture, for execution context and authorized context passing.

---

# 16. Phase 6.6 Completion Criteria

The specification is complete when:

- Research requests can be validated and normalized.
- Research intent can be classified.
- Authorized context can enrich queries.
- Complex research can be decomposed.
- Research plans can be generated.
- Historical research can be evaluated for reuse.
- Discovery methods can be selected adaptively.
- Candidate sources can be discovered and ranked.
- Duplicate sources can be handled without losing independent evidence.
- Ambiguity, missing information, and partial discovery are represented explicitly.
- Security and privacy constraints are preserved.

**Completion status:** Specification complete when documented and reviewed. Implementation, classifier training, ranking calibration, and test verification remain future work.

---

# 17. Next Algorithm Group

The next group is:

**Phase 6.7 — Research Content Extraction & Fact Normalization**

It will define:

1. Source accessibility and retrieval.
2. Content extraction.
3. Document and webpage parsing.
4. Content normalization.
5. Fact and claim extraction.
6. Attribute and entity normalization.
7. Temporal and contextual normalization.
8. Evidence linking.
9. Extraction quality validation.

The output of Phase 6.6 is a structured discovery plan and ranked candidate sources. Phase 6.7 will process those sources into structured research content and candidate facts.

**Important:** This document defines the intended algorithms. It does not claim that discovery integrations, search services, classifiers, research sessions, or source-ranking systems have been implemented.
