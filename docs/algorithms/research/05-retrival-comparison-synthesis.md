# Phase 6.10 — Research Retrieval, Comparison & Synthesis Algorithms

**Project:** Raven Research Agent  
**Phase:** 6 — Algorithms & Processing Design  
**Subphase:** 6.10 — Research Retrieval, Comparison & Synthesis  
**Status:** Architecture and algorithm specification  
**Optimization Priority:** Quality first  
**Processing Approach:** Hybrid — deterministic rules, conventional NLP/statistical methods, and selective non-generative ML

---

## 1. Purpose

The Research Engine stores findings, evidence, sources, and historical snapshots across research sessions.

However, stored information becomes useful only when Raven can retrieve the right information, compare it correctly, and organize it into a coherent answer.

Research retrieval is different from ordinary semantic search.

A relevant result must satisfy the user's research objective, context, temporal requirements, and evidence requirements.

For example, when comparing two companies, Raven must ensure that:

- Both companies are correctly identified.
- Comparable attributes are retrieved.
- Financial metrics use compatible definitions.
- Reporting periods are aligned.
- Sources are sufficiently reliable.
- Conflicting information remains visible.
- Historical and current values are not mixed incorrectly.

This phase defines the algorithms responsible for:

1. Research query retrieval.
2. Session and snapshot selection.
3. Finding retrieval.
4. Evidence-aware ranking.
5. Cross-source comparison.
6. Attribute normalization and comparison.
7. Timeline and trend analysis.
8. Research synthesis.
9. Final research output validation.

### Core principles

1. Retrieve information based on research intent, not similarity alone.
2. Preserve source and evidence references.
3. Distinguish historical from current findings.
4. Compare only contextually compatible information.
5. Preserve disagreements and missing information.
6. Do not invent missing attributes.
7. Keep facts, estimates, opinions, and conclusions distinguishable.
8. Ensure every material conclusion can be traced to evidence.
9. Adapt output structure to the research request.
10. Quality and factual integrity take priority over response speed.

---

# 2. Algorithm Inventory

This document defines nine algorithms.

| ID | Algorithm | Primary responsibility |
|---|---|---|
| 6.10.1 | Research Query Retrieval & Interpretation | Understand what stored research is needed |
| 6.10.2 | Session & Snapshot Selection | Select relevant research sessions and versions |
| 6.10.3 | Research Finding Retrieval | Retrieve relevant findings and evidence |
| 6.10.4 | Evidence-Aware Ranking | Rank findings based on relevance and evidence quality |
| 6.10.5 | Cross-Source Comparison | Compare findings across sources |
| 6.10.6 | Attribute & Entity Comparison | Perform structured comparisons |
| 6.10.7 | Timeline & Trend Analysis | Identify changes and patterns over time |
| 6.10.8 | Research Synthesis | Assemble evidence-backed research outputs |
| 6.10.9 | Final Research Output Validation | Validate completeness, accuracy, and provenance |

---

# 3. 6.10.1 — Research Query Retrieval & Interpretation

## Purpose

Understand which stored research information is required to answer a new research request.

A query may request:

- A specific previous finding.
- A complete research session.
- A comparison across entities.
- The latest information.
- Historical information.
- Changes since the previous research snapshot.
- A summary of several investigations.

The retrieval algorithm must identify the appropriate research scope before retrieving records.

## Query dimensions

Evaluate:

- Research objective.
- Entity references.
- Requested attributes.
- Research session references.
- Temporal requirements.
- Geographic constraints.
- Comparison requirements.
- Output requirements.
- Historical versus current intent.

## Retrieval intent categories

- `SINGLE_FINDING`
- `SESSION_RETRIEVAL`
- `SNAPSHOT_RETRIEVAL`
- `ENTITY_RESEARCH`
- `COMPARATIVE_RETRIEVAL`
- `HISTORICAL_RETRIEVAL`
- `LATEST_FINDINGS`
- `CHANGE_ANALYSIS`
- `MULTI_SESSION_RETRIEVAL`

## Algorithm

**Input:**

- Research query.
- Authorized context.
- Entity references.
- Existing research session references.

**Output:**

- Retrieval intent.
- Retrieval scope.
- Required attributes.
- Temporal constraints.
- Retrieval requirements.

### Processing steps

1. Validate the query and access context.
2. Normalize the research request.
3. Identify referenced entities.
4. Identify requested attributes.
5. Detect historical or current information requirements.
6. Identify explicit session or snapshot references.
7. Determine the retrieval intent.
8. Define the required research scope.
9. Return the structured retrieval request.

### Pseudocode

```text
FUNCTION interpret_research_retrieval_query(query):

    validate_query(query)

    entities = identify_entities(query)

    attributes = identify_requested_attributes(query)

    temporal = identify_temporal_requirements(query)

    intent = classify_retrieval_intent(query)

    scope = determine_retrieval_scope(
        intent,
        entities,
        attributes,
        temporal
    )

    RETURN {
        intent,
        scope,
        entities,
        attributes,
        temporal
    }
```

## Safeguards

- Do not assume a request for latest information means the latest stored information is current.
- Distinguish requests for historical snapshots from requests for current findings.
- Preserve explicit user constraints.
- Do not retrieve unrelated sessions merely because their topics are similar.

---

# 4. 6.10.2 — Session & Snapshot Selection

## Purpose

Identify the correct research sessions and snapshots for the retrieval request.

A research session may contain multiple snapshots representing different points in time.

The algorithm must select the appropriate version based on the requested objective and temporal context.

## Selection dimensions

- User ownership.
- Session objective.
- Entity identity.
- Attribute coverage.
- Research scope.
- Snapshot completeness.
- Verification state.
- Snapshot timestamp.
- Temporal compatibility.
- Session lifecycle status.

## Selection outcomes

- `EXACT_SESSION_MATCH`
- `RELATED_SESSION_MATCH`
- `LATEST_VALID_SNAPSHOT`
- `HISTORICAL_SNAPSHOT`
- `MULTIPLE_SESSIONS_REQUIRED`
- `NO_SUITABLE_SESSION`
- `NEEDS_REVIEW`

## Algorithm

**Input:**

- Structured retrieval request.
- Existing research sessions.
- Snapshot metadata.
- Ownership context.

**Output:**

- Selected session references.
- Selected snapshot references.
- Selection rationale.

### Processing steps

1. Validate user ownership.
2. Search eligible research sessions.
3. Compare session objectives.
4. Match entities and attributes.
5. Evaluate scope compatibility.
6. Retrieve available snapshots.
7. Check snapshot completeness and validity.
8. Select the appropriate snapshot or snapshot set.
9. Preserve historical snapshots when requested.
10. Return selected references.

### Pseudocode

```text
FUNCTION select_research_snapshots(request):

    sessions = find_authorized_sessions(request.user_id)

    candidates = match_sessions(
        sessions,
        request
    )

    selected = []

    FOR EACH session IN candidates:

        snapshots = retrieve_session_snapshots(session)

        valid = filter_valid_snapshots(snapshots)

        match = select_snapshot_for_request(
            valid,
            request
        )

        IF match.exists:
            selected.append(match)

    RETURN selected
```

## Safeguards

- Never access another user's private research session.
- Do not select an incomplete snapshot as complete.
- Preserve the difference between latest stored and latest verified information.
- Do not silently replace a requested historical snapshot with the latest snapshot.
- Multiple sessions may be selected when the request explicitly requires cross-session research.

---

# 5. 6.10.3 — Research Finding Retrieval

## Purpose

Retrieve findings, evidence, sources, and contextual metadata from selected research sessions.

Retrieval should be selective.

The Research Engine should retrieve only the information required to satisfy the current research objective.

## Retrieval dimensions

- Finding text and structured attributes.
- Entity references.
- Evidence references.
- Source references.
- Confidence classifications.
- Verification outcomes.
- Temporal context.
- Geographic context.
- Measurement context.
- Historical revision references.
- Contradiction records.

## Retrieval methods

### A. Structured retrieval

Suitable for:

- Entity-specific attributes.
- Financial metrics.
- Dates and numerical values.
- Known finding IDs.
- Specific session or snapshot references.

### B. Keyword retrieval

Suitable for:

- Exact terminology.
- Names.
- Product identifiers.
- Specific technical terms.

### C. Semantic retrieval

Suitable for:

- Conceptual questions.
- Related research topics.
- Similar findings expressed using different wording.

### D. Relationship-aware retrieval

Suitable for:

- Related findings.
- Connected entities.
- Linked research sessions.
- Evidence dependencies.
- Historical versions.

### E. Temporal retrieval

Suitable for:

- Latest findings.
- Historical snapshots.
- Changes over time.
- Time-bounded comparisons.

## Algorithm

**Input:**

- Selected sessions and snapshots.
- Retrieval scope.
- Requested attributes.
- Retrieval constraints.

**Output:**

- Retrieved findings.
- Evidence and source references.
- Contextual metadata.
- Retrieval completeness status.

### Processing steps

1. Load selected snapshots.
2. Identify eligible findings.
3. Apply entity and attribute filters.
4. Apply temporal constraints.
5. Apply verification and lifecycle filters.
6. Retrieve associated evidence and sources.
7. Retrieve relevant contradictions and revisions.
8. Deduplicate equivalent retrieval results.
9. Validate ownership and provenance.
10. Return the structured retrieval result.

### Pseudocode

```text
FUNCTION retrieve_research_findings(request, snapshots):

    findings = []

    FOR EACH snapshot IN snapshots:

        records = retrieve_snapshot_findings(snapshot)

        records = filter_by_entity(records, request.entities)

        records = filter_by_attribute(
            records,
            request.attributes
        )

        records = filter_by_temporal_scope(
            records,
            request.temporal
        )

        findings.extend(records)

    findings = deduplicate_retrieved_findings(findings)

    evidence = retrieve_linked_evidence(findings)

    sources = retrieve_linked_sources(findings)

    validate_provenance(findings, evidence, sources)

    RETURN {
        findings,
        evidence,
        sources,
        completeness_status
    }
```

## Safeguards

- Deleted or unauthorized records must not be returned.
- Historical findings must remain identifiable as historical.
- Unverified findings must retain their qualification.
- Retrieval must not remove contradictory evidence.
- Missing source records must be reported.
- Incomplete retrieval must not be presented as exhaustive.

---

# 6. 6.10.4 — Evidence-Aware Ranking

## Purpose

Rank retrieved findings according to their usefulness and evidence quality for the current research objective.

A finding can be semantically relevant but poorly supported.

A highly reliable finding can also be irrelevant to the current query.

Ranking must consider both relevance and evidence quality.

## Ranking dimensions

1. Query relevance.
2. Entity match.
3. Attribute match.
4. Context compatibility.
5. Temporal relevance.
6. Verification status.
7. Evidence quality.
8. Source reliability.
9. Independent corroboration.
10. Finding completeness.

These dimensions must remain independently inspectable.

## Illustrative ranking model

A configurable model may be used:

\[
R = w_qQ + w_eE + w_aA + w_cC + w_tT + w_vV + w_pP
\]

Where:

- \(Q\) = query relevance.
- \(E\) = entity match.
- \(A\) = attribute match.
- \(C\) = context compatibility.
- \(T\) = temporal relevance.
- \(V\) = verification quality.
- \(P\) = provenance and evidence quality.
- \(w\) = configurable weights.

This is an illustrative ranking model. Numerical weights must be calibrated during evaluation.

## Algorithm

**Input:**

- Retrieved findings.
- Research query.
- Evidence metadata.
- Verification metadata.
- Ranking configuration.

**Output:**

- Ranked findings.
- Dimension-level scores.
- Ranking rationale.

### Processing steps

1. Validate retrieved findings.
2. Evaluate query relevance.
3. Evaluate entity and attribute matches.
4. Evaluate temporal and contextual compatibility.
5. Inspect verification status.
6. Evaluate evidence quality.
7. Evaluate source reliability and corroboration.
8. Calculate ranking signals.
9. Apply ranking policy.
10. Preserve qualification and uncertainty.
11. Return ranked findings.

### Pseudocode

```text
FUNCTION rank_research_findings(findings, query):

    ranked = []

    FOR EACH finding IN findings:

        relevance = evaluate_query_relevance(finding, query)

        entity_match = evaluate_entity_match(finding, query)

        attribute_match = evaluate_attribute_match(
            finding,
            query
        )

        context = evaluate_context_compatibility(
            finding,
            query
        )

        temporal = evaluate_temporal_relevance(
            finding,
            query
        )

        evidence = evaluate_evidence_quality(finding)

        verification = evaluate_verification_quality(finding)

        score = calculate_ranking_score(
            relevance,
            entity_match,
            attribute_match,
            context,
            temporal,
            evidence,
            verification
        )

        ranked.append({
            finding,
            score,
            ranking_metadata
        })

    RETURN sort_by_ranking(ranked)
```

## Ranking safeguards

- Ranking must not upgrade verification status.
- High semantic similarity cannot compensate for incompatible context.
- Conflicting findings must remain available.
- Unverified information must not be presented as verified because it ranks highly.
- Missing evaluation dimensions must remain distinguishable from low scores.
- A ranking score is not a probability of truth.

---

# 7. 6.10.5 — Cross-Source Comparison

## Purpose

Compare findings from different sources to identify agreement, differences, and conflicts.

Cross-source comparison is especially important when multiple sources report information about the same entity or event.

## Comparison dimensions

- Entity identity.
- Attribute identity.
- Claim meaning.
- Numerical values.
- Measurement units.
- Reporting period.
- Geographic scope.
- Source publication date.
- Evidence quality.
- Verification status.

## Comparison outcomes

- `AGREEMENT`
- `PARTIAL_AGREEMENT`
- `DIFFERENCE`
- `CONTRADICTION`
- `INCOMPARABLE`
- `INSUFFICIENT_INFORMATION`

## Algorithm

**Input:**

- Findings from multiple sources.
- Entity references.
- Attribute metadata.
- Temporal and measurement context.
- Evidence references.

**Output:**

- Comparison records.
- Agreement and disagreement classification.
- Conflict references.
- Comparison rationale.

### Processing steps

1. Group findings by entity and attribute.
2. Confirm entity identity.
3. Normalize attribute definitions.
4. Validate measurement compatibility.
5. Validate reporting-period compatibility.
6. Compare values and claims.
7. Identify agreement and disagreement.
8. Determine whether differences are explainable by context.
9. Preserve source-specific values.
10. Generate comparison records.

### Pseudocode

```text
FUNCTION compare_cross_source_findings(findings):

    groups = group_by_entity_and_attribute(findings)

    comparisons = []

    FOR EACH group IN groups:

        pairs = generate_comparable_pairs(group)

        FOR EACH pair IN pairs:

            IF NOT same_entity(pair):
                classification = INCOMPARABLE

            ELSE IF NOT compatible_context(pair):
                classification = INCOMPARABLE

            ELSE:
                classification = compare_claims(pair)

            comparisons.append(
                create_comparison_record(
                    pair,
                    classification
                )
            )

    RETURN comparisons
```

## Safeguards

- Never compare incompatible units or metric definitions.
- Preserve each source's original reported value.
- Do not average conflicting figures without a justified methodology.
- Do not interpret disagreement as proof that one source is false.
- Preserve uncertainty when differences cannot be explained.

---

# 8. 6.10.6 — Attribute & Entity Comparison

## Purpose

Perform structured comparisons between entities using compatible attributes.

For example, comparing two software products may involve:

- Pricing.
- Supported platforms.
- Features.
- Integrations.
- Performance.
- Licensing.
- Security capabilities.

Comparing companies may involve:

- Revenue.
- Funding.
- Employees.
- Products.
- Headquarters.
- Market presence.

The relevant comparison dimensions depend on the user's request.

## Comparison requirements

Each comparison attribute must define:

- Canonical attribute.
- Entity reference.
- Reported value.
- Original value.
- Unit.
- Currency where relevant.
- Time period.
- Geographic scope.
- Source reference.
- Evidence reference.
- Verification status.

## Missing information handling

An entity may lack a value for a requested attribute.

Possible statuses:

- `AVAILABLE`
- `NOT_FOUND`
- `NOT_DISCLOSED`
- `NOT_APPLICABLE`
- `UNVERIFIED`
- `INCOMPARABLE`
- `CONFLICTING`

These statuses must not be collapsed into a single null value.

## Algorithm

**Input:**

- Entity list.
- Requested comparison attributes.
- Research findings.
- Evidence and verification metadata.

**Output:**

- Structured comparison matrix.
- Attribute-level comparison results.
- Missing information indicators.

### Processing steps

1. Validate the entity list.
2. Resolve entity identity.
3. Identify requested comparison attributes.
4. Retrieve findings for each entity.
5. Normalize attribute definitions.
6. Validate temporal and measurement compatibility.
7. Identify missing or undisclosed information.
8. Preserve conflicting values.
9. Generate the comparison matrix.
10. Validate evidence coverage.

### Pseudocode

```text
FUNCTION compare_entities(entities, attributes):

    matrix = initialize_comparison_matrix(
        entities,
        attributes
    )

    FOR EACH entity IN entities:

        FOR EACH attribute IN attributes:

            findings = retrieve_entity_attribute_findings(
                entity,
                attribute
            )

            IF findings.is_empty:
                set_attribute_status(
                    matrix,
                    entity,
                    attribute,
                    NOT_FOUND
                )
                continue

            normalized = normalize_comparable_values(findings)

            validate_comparison_context(normalized)

            result = evaluate_attribute_comparison(normalized)

            add_comparison_result(matrix, result)

    validate_comparison_matrix(matrix)

    RETURN matrix
```

## Comparison safeguards

- Do not invent missing values.
- Do not infer that an undisclosed value is zero.
- Preserve incompatible values separately.
- Make reporting dates visible.
- Identify estimated versus actual figures.
- Preserve evidence references for every displayed value.

---

# 9. 6.10.7 — Timeline & Trend Analysis

## Purpose

Identify changes and patterns in research findings across different points in time.

Timeline analysis reconstructs events and observations.

Trend analysis identifies patterns across multiple observations.

These are related but different operations.

### Timeline analysis

Focuses on:

- What happened?
- When did it happen?
- What was known at that time?
- What changed afterward?

### Trend analysis

Focuses on:

- How did a value change?
- Is there a recurring pattern?
- Is the direction increasing or decreasing?
- Are observations sufficiently comparable?

## Temporal data requirements

- Event date.
- Observation date.
- Publication date.
- Reporting period.
- Valid time.
- Source reference.
- Measurement definition.

## Algorithm

**Input:**

- Historical findings.
- Temporal metadata.
- Entity and attribute references.
- Measurement context.

**Output:**

- Ordered timeline.
- Trend observations.
- Change records.
- Temporal completeness status.

### Processing steps

1. Retrieve historical findings.
2. Group findings by entity and attribute.
3. Normalize temporal fields.
4. Validate measurement compatibility.
5. Sort observations chronologically.
6. Identify material changes.
7. Calculate trends where the data supports them.
8. Identify missing time periods.
9. Identify conflicting or anomalous observations.
10. Return the timeline and trend analysis.

### Pseudocode

```text
FUNCTION analyze_research_timeline(findings):

    groups = group_by_entity_and_attribute(findings)

    results = []

    FOR EACH group IN groups:

        observations = normalize_temporal_observations(group)

        observations = filter_comparable_observations(
            observations
        )

        ordered = sort_chronologically(observations)

        changes = detect_material_changes(ordered)

        trends = calculate_supported_trends(ordered)

        results.append({
            timeline: ordered,
            changes,
            trends
        })

    RETURN results
```

## Safeguards

- Do not calculate trends from incomparable metrics.
- Do not assume missing observations represent zero.
- Do not infer causation from correlation or temporal sequence alone.
- Preserve changes in measurement methodology.
- Distinguish actual observations from forecasts.
- Mark insufficient time-series data as insufficient.

---

# 10. 6.10.8 — Research Synthesis

## Purpose

Combine retrieved and evaluated findings into a coherent research response.

Synthesis must preserve the distinctions between:

- Verified findings.
- Supported but incompletely verified claims.
- Historical findings.
- Estimates.
- Opinions.
- Conflicting evidence.
- Missing information.
- Analytical conclusions.

The synthesis algorithm organizes evidence. It must not invent information to make the output appear complete.

## Synthesis structure

Depending on the request, a research response may contain:

1. Executive summary.
2. Research scope.
3. Key findings.
4. Detailed analysis.
5. Comparisons.
6. Timeline or trends.
7. Conflicting information.
8. Evidence limitations.
9. Sources and citations.
10. Conclusion.

Not every request requires every section.

## Synthesis inputs

- Original research query.
- Retrieval intent.
- Ranked findings.
- Verification records.
- Evidence records.
- Source reliability evaluations.
- Comparison results.
- Timeline and trend results.
- Output requirements.

## Algorithm

**Input:**

- Qualified research findings.
- Evidence and source references.
- Comparison outputs.
- Requested response structure.

**Output:**

- Structured research response.
- Evidence references.
- Limitations.
- Completeness status.

### Processing steps

1. Load the original research objective.
2. Retrieve relevant qualified findings.
3. Group findings by topic and subquestion.
4. Identify key evidence-backed observations.
5. Incorporate comparison and timeline results where relevant.
6. Separate verified findings from uncertain claims.
7. Preserve unresolved contradictions.
8. Identify unanswered research requirements.
9. Organize the response according to the requested format.
10. Attach evidence references to material claims.
11. Generate a structured synthesis.
12. Return the result for validation.

### Pseudocode

```text
FUNCTION synthesize_research(request, research_results):

    validate_research_scope(request)

    groups = group_findings_by_topic(
        research_results.findings
    )

    sections = []

    FOR EACH group IN groups:

        qualified = filter_by_qualification(group)

        summary = summarize_evidence_backed_findings(
            qualified
        )

        conflicts = retrieve_group_conflicts(group)

        limitations = identify_group_limitations(group)

        sections.append(
            create_research_section(
                summary,
                conflicts,
                limitations
            )
        )

    response = assemble_response(
        request.output_requirements,
        sections
    )

    RETURN response
```

## Synthesis safeguards

- Every material factual statement must have supporting evidence.
- Do not convert estimates into exact figures.
- Do not present opinions as established facts.
- Preserve historical qualifications.
- Do not suppress contradictory findings.
- Do not invent missing comparison values.
- Clearly distinguish findings from analytical interpretation.
- Do not claim that a research question is fully answered if important requirements remain incomplete.

## Generative model constraint

The core Raven processing architecture does not use generative LLM APIs or locally hosted generative LLMs.

Therefore, synthesis must be designed around structured evidence, deterministic templates, rule-based organization, and conventional NLP/statistical techniques.

Any future architectural change introducing generative components would require a separate explicit architecture revision, including security, provenance, and validation requirements.

---

# 11. 6.10.9 — Final Research Output Validation

## Purpose

Validate the final research response before it is returned to the Agent Orchestrator.

This is the final Research Engine quality gate.

The Orchestrator remains responsible for combining outputs across engines and delivering the final user-facing response.

## Validation dimensions

### A. Coverage

- Does the response address the original question?
- Are all required subtasks represented?
- Are requested entities included?
- Are requested attributes covered?

### B. Factual integrity

- Are factual claims supported?
- Are numerical values accurate relative to their source records?
- Are qualifiers preserved?
- Are estimates and forecasts correctly identified?

### C. Evidence integrity

- Do citations resolve?
- Does the evidence support the associated claim?
- Are sources represented accurately?
- Are conflicting sources retained?

### D. Context integrity

- Are dates correct?
- Are reporting periods visible?
- Are units and currencies preserved?
- Are historical and current values distinguished?

### E. Completeness

- Are missing fields identified?
- Are limitations disclosed?
- Is partial research marked appropriately?
- Is uncertainty represented?

## Validation outcomes

- `VALID`
- `VALID_WITH_WARNINGS`
- `INCOMPLETE`
- `NEEDS_REVIEW`
- `REJECTED`

## Algorithm

**Input:**

- Structured research response.
- Original query.
- Qualified findings.
- Evidence and source references.
- Research completeness metadata.

**Output:**

- Validated research response.
- Validation status.
- Warnings.
- Missing information indicators.

### Processing steps

1. Load the research response.
2. Validate response structure.
3. Compare coverage against the original query.
4. Validate factual claims against findings.
5. Validate evidence references.
6. Validate numerical and temporal context.
7. Check for unsupported conclusions.
8. Check whether contradictions were preserved.
9. Check completeness status.
10. Assign validation outcome.
11. Return the validated response.

### Pseudocode

```text
FUNCTION validate_research_output(response, request):

    structure = validate_response_structure(response)

    coverage = validate_query_coverage(response, request)

    facts = validate_factual_claims(response)

    evidence = validate_evidence_references(response)

    context = validate_temporal_and_measurement_context(
        response
    )

    uncertainty = validate_uncertainty_representation(response)

    IF NOT structure.valid:
        RETURN REJECTED

    IF facts.has_unsupported_material_claims:
        RETURN NEEDS_REVIEW

    IF NOT evidence.valid:
        RETURN NEEDS_REVIEW

    IF coverage.is_incomplete:
        RETURN INCOMPLETE

    IF has_non_critical_warnings(response):
        RETURN VALID_WITH_WARNINGS

    RETURN VALID
```

## Final output safeguards

- No unsupported material claims.
- No fabricated citations.
- No missing evidence represented as verified.
- No false completeness claims.
- No silent removal of material conflicts.
- No unauthorized information.
- No loss of temporal context.

---

# 12. Research Retrieval & Synthesis Output Contract

The following is a conceptual contract.

```text
ResearchSynthesisResult:
    synthesis_id
    research_session_references
    snapshot_references
    original_query
    retrieval_intent
    retrieved_finding_references
    ranked_findings
    comparison_results
    timeline_results
    evidence_references
    source_references
    verification_qualifications
    synthesis_sections
    identified_conflicts
    missing_information
    limitations
    completeness_status
    validation_status
    processing_version
    created_at
```

This is a logical contract, not a finalized database schema.

The Research Engine returns a structured, evidence-aware result to the Agent Orchestrator.

The Orchestrator owns final cross-engine response assembly.

---

# 13. Failure Handling

| Failure | Expected handling |
|---|---|
| No matching research session | Report no stored research and request new discovery |
| Snapshot unavailable | Identify the missing snapshot |
| Findings incomplete | Return partial retrieval status |
| Evidence reference missing | Mark finding evidence incomplete |
| Conflicting findings | Preserve and qualify the conflict |
| Incompatible metrics | Mark comparison as incomparable |
| Historical data unavailable | Report the historical coverage limitation |
| Trend data insufficient | Do not infer a trend |
| Synthesis failure | Preserve retrieved results for recovery |
| Validation failure | Do not return as a fully validated result |
| Resource budget exhausted | Return partial synthesis with limitations |

Partial results are valid when their limitations are accurately represented.

---

# 14. Security & Privacy Requirements

1. Research retrieval must enforce user ownership.
2. Historical snapshots must follow current authorization rules.
3. Deleted records must not reappear through historical retrieval.
4. Evidence and source references must retain access controls.
5. Cross-engine private context must be accessed only through authorized interfaces.
6. Research results must preserve provenance.
7. Logs must not unnecessarily duplicate sensitive information.
8. External content must remain untrusted.
9. Synthesis must not disclose information outside the authorized research scope.
10. Validation must include authorization and data-boundary checks.

---

# 15. Evaluation Metrics

These metrics will be evaluated during Phase 12.

| Area | Metric |
|---|---|
| Retrieval | Retrieval relevance precision |
| Retrieval | Relevant finding recall |
| Session selection | Correct snapshot selection rate |
| Ranking | Evidence-aware ranking quality |
| Comparison | Attribute comparison accuracy |
| Comparison | Incompatible comparison detection |
| Timeline | Temporal ordering accuracy |
| Trend analysis | Trend detection accuracy |
| Synthesis | Research coverage |
| Synthesis | Evidence attribution completeness |
| Validation | Unsupported claim detection rate |
| Validation | Citation correctness |
| Reliability | False completeness rate |
| Reliability | Contradiction preservation rate |

Numerical targets will be established during Phase 12.

---

# 16. Dependencies

This phase depends on:

- Phase 3 — Research Engine Architecture.
- Phase 5.3 — Core Entities & Relationships.
- Phase 5.5 — Research Engine Data Models.
- Phase 6.1 — Shared Algorithm Framework.
- Phase 6.6 — Query Understanding & Information Discovery.
- Phase 6.7 — Content Extraction & Fact Normalization.
- Phase 6.8 — Source Evaluation & Verification.
- Phase 6.9 — Research Memory Management & Session Lifecycle.

---

# 17. Phase 6.10 Completion Criteria

The specification is complete when:

- Research retrieval intent can be identified.
- Correct sessions and snapshots can be selected.
- Findings and evidence can be retrieved selectively.
- Results can be ranked using relevance and evidence quality.
- Cross-source findings can be compared.
- Entity and attribute comparisons preserve context.
- Historical timelines and supported trends can be generated.
- Research findings can be synthesized without inventing information.
- Final output can be validated for evidence and completeness.
- Research results preserve provenance and authorization boundaries.

**Completion status:** Specification complete when documented and reviewed. Retrieval implementation, ranking calibration, comparison implementation, synthesis implementation, and testing remain future work.

---

# 18. Research Engine Algorithm Design — Overall Status

The Research Engine algorithm design is organized into five major groups.

| Phase | Algorithm group | File |
|---|---|---|
| 6.6 | Query Understanding & Information Discovery | `01-query-understanding-discovery.md` |
| 6.7 | Content Extraction & Fact Normalization | `02-content-extraction-normalization.md` |
| 6.8 | Source Evaluation & Verification | `03-source-evaluation-verification.md` |
| 6.9 | Research Memory Management & Session Lifecycle | `04-research-memory-session-lifecycle.md` |
| 6.10 | Retrieval, Comparison & Synthesis | `05-retrieval-comparison-synthesis.md` |

The Research Engine algorithm specification is architecturally covered once these five groups have been documented and reviewed.

---

# 19. Next Algorithm Group

**Phase 6.11 — Agent Orchestrator Algorithms**

The next group will define:

1. Intent understanding.
2. Task decomposition.
3. Execution planning.
4. Memory and Research Engine routing.
5. Dependency resolution.
6. Parallel and sequential execution.
7. Context assembly.
8. State and progress management.
9. Failure recovery and cancellation.
10. Final response coordination.

The Research Engine produces structured evidence-backed research results. The Agent Orchestrator coordinates those results with Memory Engine outputs and manages the complete user request.

**Important:** This document specifies intended algorithms. It does not claim that research retrieval, comparison, ranking, synthesis, or output validation has been implemented.
