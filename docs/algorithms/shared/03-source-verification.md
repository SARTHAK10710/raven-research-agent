# Phase 6.8 — Research Source Evaluation & Verification Algorithms

**Project:** Raven Research Agent  
**Phase:** 6 — Algorithms & Processing Design  
**Subphase:** 6.8 — Research Source Evaluation & Verification  
**Status:** Architecture and algorithm specification  
**Optimization Priority:** Quality first  
**Processing Approach:** Hybrid — deterministic rules, conventional NLP/statistical methods, and selective non-generative ML

---

## 1. Purpose

Finding information and extracting claims does not establish that those claims are correct.

A source may be:

- Authoritative but outdated.
- Relevant but unreliable.
- Accurate about one subject but irrelevant to another.
- Repeating information from another publication.
- Reporting an estimate rather than a confirmed value.
- Contradicting another source.
- Making a claim without providing supporting evidence.

Raven must evaluate both the source and the evidence supporting each individual finding.

This phase defines the algorithms responsible for:

1. Evaluating source reliability.
2. Assessing evidence quality.
3. Identifying independent corroboration.
4. Verifying extracted claims.
5. Detecting contradictions.
6. Checking temporal consistency.
7. Estimating fact confidence.
8. Selecting verification depth.
9. Qualifying findings for downstream research use.

### Core principles

1. Source reliability and fact confidence are separate dimensions.
2. A reliable source can contain an incorrect or outdated claim.
3. A less authoritative source can provide useful supporting evidence.
4. Multiple publications do not necessarily represent independent corroboration.
5. Evidence must support the specific claim being evaluated.
6. Conflicting evidence must remain visible.
7. Historical truth and current applicability must be distinguished.
8. Uncertainty must not be hidden.
9. Verification depth must adapt to the research objective.
10. The system must be allowed to abstain when evidence is insufficient.

---

# 2. Algorithm Inventory

This document defines nine algorithms.

| ID | Algorithm | Primary responsibility |
|---|---|---|
| 6.8.1 | Source Reliability Evaluation | Assess source trustworthiness |
| 6.8.2 | Evidence Quality Assessment | Evaluate evidence supporting a finding |
| 6.8.3 | Source Independence & Corroboration | Determine whether supporting sources are independent |
| 6.8.4 | Claim Verification | Evaluate whether evidence supports a claim |
| 6.8.5 | Contradiction Detection | Identify conflicting findings |
| 6.8.6 | Temporal Consistency Evaluation | Check time-sensitive claims |
| 6.8.7 | Fact Confidence Assessment | Estimate confidence in individual findings |
| 6.8.8 | Adaptive Verification Depth | Determine how much verification is required |
| 6.8.9 | Research Finding Qualification | Assign a final evidence-based qualification |

---

# 3. 6.8.1 — Source Reliability Evaluation

## Purpose

Evaluate the trustworthiness of a source for a particular research context.

Source reliability should not be treated as one universal property.

A source may be reliable for one type of information and unsuitable for another.

For example:

- Official product documentation may be highly relevant for product specifications.
- A government publication may be highly relevant for official statistics.
- A company's announcement may be reliable evidence of what the company announced, but not independent proof of every claim in that announcement.
- A technical blog may be useful for practical implementation experience but less suitable for establishing regulatory requirements.

## Evaluation dimensions

### A. Authority

Evaluate:

- Publisher identity.
- Institutional credibility.
- Subject-matter expertise.
- Official status.
- Relevant domain expertise.

### B. Evidence transparency

Evaluate:

- Presence of supporting evidence.
- References and citations.
- Methodology disclosure.
- Data origin.
- Ability to trace claims.

### C. Freshness

Evaluate:

- Publication date.
- Last updated date.
- Relevance of the date to the research question.
- Whether the subject changes frequently.

### D. Editorial and methodological quality

Evaluate:

- Editorial standards.
- Research methodology.
- Disclosure of limitations.
- Conflict-of-interest information.
- Correction practices.

### E. Context suitability

Evaluate:

- Whether the source addresses the correct entity.
- Whether the source covers the requested geography.
- Whether the source uses the required metric.
- Whether its reporting period matches the research question.

## Algorithm

**Input:**

- Source record.
- Source metadata.
- Research task.
- Source content.
- Available publisher information.

**Output:**

- Source reliability evaluation.
- Dimension-level scores.
- Evaluation rationale.
- Missing information indicators.

### Processing steps

1. Identify the source and publisher.
2. Determine the source category.
3. Evaluate authority for the relevant subject.
4. Inspect evidence transparency.
5. Evaluate freshness.
6. Inspect editorial or methodological information.
7. Check context suitability.
8. Identify missing reliability information.
9. Generate a reliability assessment.
10. Record the evaluation method and version.

### Pseudocode

```text
FUNCTION evaluate_source_reliability(source, task):

    authority = evaluate_authority(source, task)

    transparency = evaluate_evidence_transparency(source)

    freshness = evaluate_source_freshness(source, task)

    methodology = evaluate_methodological_quality(source)

    context = evaluate_context_suitability(source, task)

    missing = identify_missing_reliability_information(
        source
    )

    RETURN {
        authority,
        transparency,
        freshness,
        methodology,
        context,
        missing,
        reliability_assessment
    }
```

## Safeguards

- Official status must not automatically establish factual correctness.
- Publisher reputation must not replace claim-level verification.
- Unknown source information must remain unknown.
- Source reliability must be evaluated relative to the subject.
- Source reliability must not be confused with extraction confidence.

---

# 4. 6.8.2 — Evidence Quality Assessment

## Purpose

Evaluate how strongly the available evidence supports an individual research finding.

A source can be reliable while providing weak evidence for a specific claim.

For example, an official company website may be reliable for its product features, but a general homepage may not directly support a specific revenue figure.

## Evidence quality dimensions

1. **Directness:** Does the evidence directly address the claim?
2. **Specificity:** Does it provide the required detail?
3. **Traceability:** Can the original supporting material be located?
4. **Methodological strength:** Is the evidence based on a sound method?
5. **Context match:** Does it refer to the correct entity, time period, and metric?
6. **Completeness:** Are important qualifiers or limitations missing?
7. **Source reliability:** How trustworthy is the originating source?

These dimensions must remain independently inspectable.

## Evidence categories

- `DIRECT_EVIDENCE`
- `INDIRECT_EVIDENCE`
- `SUPPORTING_CONTEXT`
- `CONTRADICTORY_EVIDENCE`
- `INSUFFICIENT_EVIDENCE`
- `UNAVAILABLE_EVIDENCE`

## Algorithm

**Input:**

- Research finding.
- Evidence records.
- Source reliability evaluations.
- Research context.

**Output:**

- Evidence quality assessment.
- Supporting evidence classification.
- Missing evidence indicators.

### Processing steps

1. Load the finding and linked evidence.
2. Confirm that evidence references resolve.
3. Compare evidence content with the claim.
4. Evaluate directness.
5. Evaluate specificity.
6. Check contextual compatibility.
7. Inspect methodological information.
8. Identify missing qualifiers.
9. Assign evidence quality dimensions.
10. Return the assessment.

### Pseudocode

```text
FUNCTION assess_evidence_quality(finding):

    evidence_records = load_evidence(finding)

    FOR EACH evidence IN evidence_records:

        traceability = validate_evidence_reference(evidence)

        directness = evaluate_direct_support(
            finding,
            evidence
        )

        specificity = evaluate_specificity(
            finding,
            evidence
        )

        context = evaluate_evidence_context(
            finding,
            evidence
        )

        methodology = evaluate_evidence_methodology(evidence)

        classify_evidence(
            evidence,
            traceability,
            directness,
            specificity,
            context,
            methodology
        )

    RETURN evidence_quality_assessment
```

## Safeguards

- A matching keyword is not sufficient evidence.
- A search snippet is not equivalent to inspected source content.
- An indirect reference must not be represented as direct proof.
- Missing evidence must not be replaced by inference.
- Evidence must retain its original attribution and qualifications.

---

# 5. 6.8.3 — Source Independence & Corroboration

## Purpose

Determine whether multiple sources independently support the same claim.

Multiple sources do not automatically mean multiple independent confirmations.

For example, five websites repeating one original press release may represent only one underlying information source.

## Independence signals

Evaluate:

- Original publication identity.
- Shared citations.
- Identical wording.
- Syndication relationships.
- Shared data providers.
- Common underlying research.
- Independent reporting or measurement.
- Separate primary evidence.

## Corroboration categories

| Category | Meaning |
|---|---|
| `INDEPENDENT_CORROBORATION` | Evidence originates from independent sources |
| `DEPENDENT_REPETITION` | Sources repeat or derive from the same origin |
| `PARTIAL_CORROBORATION` | Sources support only part of a finding |
| `MIXED_EVIDENCE` | Sources provide both support and conflict |
| `NO_CORROBORATION` | No independent supporting source identified |

## Algorithm

**Input:**

- Research finding.
- Supporting source records.
- Evidence records.
- Publication relationships.
- Citation relationships.

**Output:**

- Source dependency groups.
- Corroboration classification.
- Independent evidence count or representation.
- Corroboration rationale.

### Processing steps

1. Collect sources supporting the finding.
2. Identify original publishers.
3. Compare publication dates and references.
4. Identify shared citations and source origins.
5. Detect syndicated or duplicated content.
6. Group sources by likely underlying origin.
7. Identify genuinely independent evidence.
8. Evaluate whether sources support the same specific claim.
9. Assign corroboration status.
10. Preserve source relationships.

### Pseudocode

```text
FUNCTION evaluate_source_independence(finding):

    sources = get_supporting_sources(finding)

    relationships = identify_source_relationships(sources)

    groups = group_by_underlying_origin(
        sources,
        relationships
    )

    independent_sources = identify_independent_origins(groups)

    corroboration = evaluate_claim_support(
        finding,
        independent_sources
    )

    RETURN {
        source_groups,
        independent_sources,
        corroboration
    }
```

## Important safeguards

- Different URLs do not prove independent sources.
- Different publishers do not necessarily prove independent reporting.
- Repetition must not inflate confidence.
- A primary source and a secondary source quoting it must not automatically count as two independent confirmations.
- Uncertain source dependencies should be marked as uncertain.

---

# 6. 6.8.4 — Claim Verification

## Purpose

Determine whether available evidence supports, partially supports, contradicts, or fails to establish an extracted claim.

This algorithm operates at the individual finding level.

A research document may contain several findings with different verification outcomes.

## Verification outcomes

- `SUPPORTED`
- `PARTIALLY_SUPPORTED`
- `CONTRADICTED`
- `UNVERIFIED`
- `INSUFFICIENT_EVIDENCE`
- `NOT_APPLICABLE`

## Verification approach

Use:

- Deterministic comparisons.
- Entity and attribute matching.
- Temporal compatibility checks.
- Numerical validation.
- Evidence alignment.
- Conventional NLP.
- Statistical and non-generative classification signals.

The algorithm must not treat semantic similarity alone as proof.

## Algorithm

**Input:**

- Candidate finding.
- Supporting evidence.
- Source reliability evaluations.
- Context metadata.
- Verification policy.

**Output:**

- Verification result.
- Supporting and contradictory evidence references.
- Verification rationale.

### Processing steps

1. Load the candidate finding.
2. Retrieve all relevant evidence.
3. Normalize claim and evidence attributes.
4. Validate entity identity.
5. Compare predicates and values.
6. Compare temporal and geographic context.
7. Check qualifiers and measurement definitions.
8. Identify direct supporting evidence.
9. Identify contradictory evidence.
10. Apply the verification policy.
11. Assign a verification result.
12. Preserve the supporting evidence references.

### Pseudocode

```text
FUNCTION verify_claim(finding):

    evidence = retrieve_relevant_evidence(finding)

    normalized_claim = normalize_claim(finding)

    supporting = []
    contradictory = []
    incomplete = []

    FOR EACH record IN evidence:

        alignment = compare_claim_with_evidence(
            normalized_claim,
            record
        )

        IF alignment.supports:
            supporting.append(record)

        ELSE IF alignment.contradicts:
            contradictory.append(record)

        ELSE IF alignment.is_incomplete:
            incomplete.append(record)

    result = determine_verification_outcome(
        supporting,
        contradictory,
        incomplete
    )

    RETURN {
        result,
        supporting,
        contradictory,
        verification_rationale
    }
```

## Verification safeguards

- Do not verify a claim using evidence about a different entity.
- Do not compare different reporting periods as though they were equivalent.
- Preserve approximate values and qualifiers.
- Distinguish an absence of evidence from evidence of absence.
- A claim may be partially supported.
- A claim may be true historically but no longer current.

---

# 7. 6.8.5 — Contradiction Detection

## Purpose

Identify conflicting research findings and determine the nature of the conflict.

Not all apparent contradictions represent genuine factual disagreement.

For example:

- One source reports annual revenue while another reports quarterly revenue.
- Two sources report different values for different dates.
- One source reports a forecast and another reports actual results.
- Two sources describe different product versions.

These differences must be classified before conclusions are drawn.

## Contradiction categories

| Category | Description |
|---|---|
| `DIRECT_CONTRADICTION` | Incompatible statements about the same context |
| `NUMERICAL_CONFLICT` | Different values for comparable measurements |
| `TEMPORAL_CONFLICT` | Different claims for different time periods |
| `ATTRIBUTE_CONFLICT` | Different values for the same attribute |
| `ENTITY_MISMATCH` | Findings refer to different entities |
| `DEFINITION_MISMATCH` | Metrics or terms have different definitions |
| `SOURCE_CONFLICT` | Sources explicitly disagree |
| `APPARENT_CONTRADICTION` | Difference may be explained by context |

## Algorithm

**Input:**

- Research findings.
- Entity references.
- Attribute records.
- Temporal context.
- Evidence references.

**Output:**

- Conflict records.
- Conflict category.
- Supporting evidence references.
- Resolution recommendation.

### Processing steps

1. Group findings by entity and attribute.
2. Identify potentially conflicting values.
3. Compare temporal context.
4. Compare measurement definitions and units.
5. Compare geographic scope.
6. Compare actual, estimated, and forecast classifications.
7. Determine whether the difference is genuine.
8. Classify the conflict.
9. Preserve all original findings.
10. Trigger further verification when required.

### Pseudocode

```text
FUNCTION detect_research_contradictions(findings):

    groups = group_by_entity_and_attribute(findings)

    conflicts = []

    FOR EACH group IN groups:

        pairs = generate_comparable_finding_pairs(group)

        FOR EACH pair IN pairs:

            compatibility = compare_context(pair)

            IF compatibility.is_incompatible:
                classify_context_mismatch(pair)
                continue

            conflict = compare_claim_values(pair)

            IF conflict.exists:
                category = classify_conflict(pair)

                conflicts.append(
                    create_conflict_record(
                        pair,
                        category
                    )
                )

    RETURN conflicts
```

## Conflict handling rules

- Do not silently select the most recent value.
- Do not automatically prefer the highest-rated source.
- Do not merge incompatible measurements.
- Preserve conflicting findings and their provenance.
- Use temporal context to distinguish valid changes from contradictions.
- Escalate unresolved material conflicts for deeper verification.

---

# 8. 6.8.6 — Temporal Consistency Evaluation

## Purpose

Determine whether a claim is valid for the time period relevant to the research request.

Research findings often change over time.

Examples:

- Product pricing.
- Company leadership.
- Employee counts.
- Funding information.
- Market share.
- Software versions.
- Regulatory requirements.

A source may accurately describe an earlier state without representing the current state.

## Temporal dimensions

- Publication time.
- Retrieval time.
- Event time.
- Effective time.
- Reporting period.
- Valid-from time.
- Valid-until time.
- Time of observation.

## Algorithm

**Input:**

- Research finding.
- Source publication metadata.
- Temporal context.
- Research target period.

**Output:**

- Temporal compatibility status.
- Currentness classification.
- Historical applicability.
- Revalidation recommendation.

### Processing steps

1. Identify the target time period.
2. Retrieve finding temporal metadata.
3. Retrieve source publication time.
4. Identify event or reporting period.
5. Compare the finding's valid time with the target period.
6. Identify newer observations.
7. Detect whether the finding is historical or current.
8. Determine whether a refresh is required.
9. Return temporal compatibility.

### Pseudocode

```text
FUNCTION evaluate_temporal_consistency(finding, target_period):

    publication_time = finding.publication_time

    event_time = finding.event_time

    valid_period = finding.valid_period

    target = normalize_target_period(target_period)

    IF valid_period.is_known:
        compatibility = compare_periods(
            valid_period,
            target
        )

    ELSE:
        compatibility = evaluate_available_temporal_evidence(
            publication_time,
            event_time,
            target
        )

    IF compatibility.is_historical:
        status = HISTORICAL

    ELSE IF compatibility.is_current:
        status = CURRENT

    ELSE:
        status = TEMPORALLY_UNCERTAIN

    RETURN {
        status,
        compatibility,
        revalidation_recommendation
    }
```

## Safeguards

- Publication date is not automatically the date a claim became true.
- A current webpage may contain old information.
- Historical facts must remain historically valid.
- A newer publication does not automatically invalidate older information.
- Time-sensitive claims require an appropriate freshness assessment.

---

# 9. 6.8.7 — Fact Confidence Assessment

## Purpose

Estimate how strongly the available evidence supports a research finding.

Fact confidence is different from source reliability, extraction confidence, and evidence quality.

These dimensions contribute to an overall assessment but must remain separately accessible.

## Confidence inputs

- Source reliability.
- Evidence quality.
- Directness of evidence.
- Independent corroboration.
- Verification result.
- Context compatibility.
- Temporal consistency.
- Contradiction severity.
- Missing evidence.

## Confidence classifications

- `VERY_HIGH`
- `HIGH`
- `MEDIUM`
- `LOW`
- `INSUFFICIENT`

These are qualitative classifications.

They are not universal probabilities and do not imply fixed numerical thresholds.

## Algorithm

**Input:**

- Research finding.
- Source reliability evaluations.
- Evidence quality assessments.
- Corroboration records.
- Verification results.
- Contradiction records.
- Temporal evaluation.

**Output:**

- Fact confidence classification.
- Dimension-level confidence information.
- Confidence rationale.
- Uncertainty indicators.

### Processing steps

1. Retrieve all relevant evaluation records.
2. Validate that evidence supports the same specific claim.
3. Evaluate directness and quality.
4. Evaluate source reliability.
5. Evaluate source independence.
6. Consider verification outcome.
7. Consider temporal compatibility.
8. Evaluate contradictions.
9. Identify missing information.
10. Assign a confidence classification.
11. Record the reasoning and processing version.

### Pseudocode

```text
FUNCTION assess_fact_confidence(finding):

    source_quality = retrieve_source_evaluations(finding)

    evidence_quality = retrieve_evidence_evaluations(finding)

    corroboration = retrieve_corroboration(finding)

    verification = retrieve_verification(finding)

    contradictions = retrieve_conflicts(finding)

    temporal = retrieve_temporal_evaluation(finding)

    confidence = calculate_confidence_classification(
        source_quality,
        evidence_quality,
        corroboration,
        verification,
        contradictions,
        temporal
    )

    RETURN {
        confidence,
        contributing_dimensions,
        rationale
    }
```

## Confidence safeguards

- Repeated copies must not artificially increase confidence.
- Strong source reputation cannot compensate automatically for irrelevant evidence.
- Unresolved material contradictions must lower confidence or require abstention.
- Missing evidence must remain visible.
- A finding with insufficient evidence must not be presented as established fact.
- Confidence must be recalculated when material evidence changes.

---

# 10. 6.8.8 — Adaptive Verification Depth

## Purpose

Determine how much verification a research finding or task requires.

Not every question requires the same verification effort.

A simple factual lookup may require less investigation than a high-impact financial, legal, medical, or safety-related claim.

## Verification levels

### A. Basic

Suitable for straightforward, low-consequence questions.

Includes:

- Initial source assessment.
- Evidence alignment.
- Basic context validation.
- Identification of missing information.

### B. Standard

Suitable for ordinary research and comparisons.

Includes:

- Multiple relevant sources where appropriate.
- Source reliability evaluation.
- Evidence quality assessment.
- Corroboration analysis.
- Temporal validation.
- Contradiction detection.

### C. Deep

Suitable for consequential, disputed, complex, or explicitly comprehensive research.

Includes:

- Strong preference for primary evidence where available.
- Independent corroboration.
- Detailed source-dependency analysis.
- Deeper contradiction investigation.
- Methodology inspection.
- More extensive temporal validation.
- Explicit unresolved uncertainty reporting.

These levels describe the intended process. They do not guarantee that independent sources or sufficient evidence will be available.

## Selection factors

- Consequence of an incorrect answer.
- User-requested depth.
- Claim importance.
- Source reliability.
- Evidence quality.
- Contradiction presence.
- Temporal sensitivity.
- Research complexity.
- Availability of primary evidence.

## Algorithm

**Input:**

- Research task.
- Claim or finding.
- Initial evidence assessment.
- Risk and consequence metadata.
- User-requested research depth.

**Output:**

- Verification level.
- Required checks.
- Verification budget.
- Escalation conditions.

### Processing steps

1. Identify the research objective.
2. Evaluate the consequence of error.
3. Check explicit depth requirements.
4. Inspect source reliability.
5. Inspect evidence quality.
6. Check for conflicting claims.
7. Evaluate freshness requirements.
8. Select verification depth.
9. Define the required checks.
10. Reassess depth when new conflicts or risks appear.

### Pseudocode

```text
FUNCTION select_verification_depth(task, finding):

    consequence = evaluate_error_consequence(task)

    requested_depth = task.requested_depth

    source_quality = inspect_source_quality(finding)

    evidence_quality = inspect_evidence_quality(finding)

    conflicts = inspect_conflicts(finding)

    freshness = inspect_temporal_sensitivity(finding)

    level = determine_required_depth(
        consequence,
        requested_depth,
        source_quality,
        evidence_quality,
        conflicts,
        freshness
    )

    RETURN {
        level,
        required_checks,
        escalation_conditions
    }
```

## Escalation rules

Escalate verification when:

- A material contradiction appears.
- Evidence is indirect.
- The primary source is unavailable.
- The claim is highly consequential.
- The information is time-sensitive.
- The original evidence cannot be traced.
- A source's methodology is unclear.

If the required verification cannot be completed, the result must reflect that limitation.

---

# 11. 6.8.9 — Research Finding Qualification

## Purpose

Assign an evidence-aware qualification to each research finding before it is used in final research synthesis.

The qualification summarizes the current verification state.

It must not replace the underlying source and evidence records.

## Qualification categories

| Category | Meaning |
|---|---|
| `VERIFIED` | Evidence sufficiently supports the claim under the applied verification policy |
| `SUPPORTED` | Available evidence supports the claim, but verification may be incomplete |
| `PARTIALLY_SUPPORTED` | Only part of the claim is supported |
| `CONTESTED` | Material conflicting evidence exists |
| `UNVERIFIED` | The claim has not been sufficiently verified |
| `INSUFFICIENT_EVIDENCE` | Available evidence is inadequate |
| `HISTORICAL_ONLY` | Evidence supports the claim for a historical period |
| `REJECTED` | The extracted finding is invalid or materially unsupported |

## Qualification algorithm

**Input:**

- Research finding.
- Verification result.
- Fact confidence.
- Source reliability.
- Evidence quality.
- Contradiction records.
- Temporal consistency.
- Applied verification policy.

**Output:**

- Finding qualification.
- Qualification rationale.
- Supporting evidence references.
- Limitations and warnings.

### Processing steps

1. Retrieve the finding and its evidence.
2. Retrieve source reliability assessments.
3. Retrieve evidence quality assessments.
4. Retrieve corroboration and verification results.
5. Check contradiction status.
6. Check temporal applicability.
7. Check required verification depth.
8. Determine whether the applied checks are complete.
9. Assign the qualification.
10. Preserve the rationale and evidence references.
11. Return the qualified finding.

### Pseudocode

```text
FUNCTION qualify_research_finding(finding):

    validation = validate_extraction(finding)

    IF validation == REJECTED:
        RETURN REJECTED

    verification = get_verification_result(finding)

    confidence = get_fact_confidence(finding)

    conflicts = get_material_conflicts(finding)

    temporal = get_temporal_status(finding)

    IF conflicts.unresolved:
        qualification = CONTESTED

    ELSE IF temporal == HISTORICAL:
        qualification = HISTORICAL_ONLY

    ELSE IF verification == INSUFFICIENT_EVIDENCE:
        qualification = INSUFFICIENT_EVIDENCE

    ELSE IF verification == CONTRADICTED:
        qualification = CONTESTED

    ELSE IF verification == PARTIALLY_SUPPORTED:
        qualification = PARTIALLY_SUPPORTED

    ELSE IF verification == SUPPORTED
        AND required_checks_completed(finding)
        AND confidence_sufficient(confidence):
        qualification = VERIFIED

    ELSE:
        qualification = UNVERIFIED

    RETURN {
        qualification,
        confidence,
        evidence_references,
        rationale
    }
```

## Qualification safeguards

- `VERIFIED` is always relative to the applied verification policy and available evidence.
- It does not mean absolute certainty.
- Historical claims must not be presented as current facts.
- Contested claims must retain both supporting and contradictory evidence.
- Insufficient evidence must not be upgraded simply because the user expects an answer.
- Unverified claims may still be reported when clearly labeled and relevant.

---

# 12. Research Verification Data Contract

The following is a conceptual contract.

```text
ResearchVerification:
    verification_id
    research_session_id
    finding_id
    source_evaluations
    evidence_evaluations
    corroboration_records
    verification_result
    contradiction_references
    temporal_consistency
    fact_confidence
    verification_depth
    finding_qualification
    rationale
    processing_version
    evaluated_at
```

This is a logical contract, not a finalized database schema.

Individual source evaluations, evidence records, and contradiction records remain independently identifiable.

---

# 13. Failure Handling

| Failure | Expected handling |
|---|---|
| Source reliability information missing | Preserve unknown dimensions |
| Evidence reference unavailable | Mark evidence incomplete |
| Source dependency unclear | Avoid assuming independence |
| Conflicting sources | Preserve conflict and investigate |
| Primary source unavailable | Use alternatives with qualification |
| Temporal information missing | Mark currentness uncertain |
| Metric definitions differ | Do not compare as equivalent |
| Verification budget exhausted | Return incomplete verification |
| Evidence insufficient | Abstain from strong factual claims |
| Verification process fails | Preserve previous verified snapshot and report failure |
| New evidence invalidates prior assessment | Re-evaluate affected findings |

---

# 14. Security & Privacy Requirements

1. Every evaluation must preserve user and research-session boundaries.
2. Source content must remain untrusted.
3. Evidence records must preserve source provenance.
4. External source instructions must never control verification policies.
5. Verification records must not expose unrelated private context.
6. Source evaluation must not bypass retrieval access policies.
7. Sensitive research findings must follow their applicable access controls.
8. Evaluation logs must not unnecessarily duplicate source content.
9. Changes to verification results must be traceable.
10. Conflicting evidence must not be silently removed.

---

# 15. Evaluation Metrics

These metrics will be evaluated during Phase 12.

| Area | Metric |
|---|---|
| Source evaluation | Source reliability assessment accuracy |
| Evidence | Evidence relevance precision |
| Evidence | Evidence traceability completeness |
| Corroboration | Independent-source detection accuracy |
| Verification | Claim verification precision and recall |
| Contradictions | Contradiction detection precision and recall |
| Temporal evaluation | Temporal consistency accuracy |
| Confidence | Confidence calibration |
| Verification depth | Appropriate verification-level selection |
| Qualification | Finding qualification accuracy |
| Reliability | False verification rate |
| Reliability | Unsupported claim rate |

Numerical targets will be established during Phase 12.

---

# 16. Dependencies

This phase depends on:

- Phase 3 — Research Engine Architecture.
- Phase 5.3 — Core Entities & Relationships.
- Phase 5.5 — Research Engine Data Models.
- Phase 6.1 — Shared Algorithm Framework.
- Phase 6.6 — Query Understanding & Information Discovery.
- Phase 6.7 — Research Content Extraction & Fact Normalization.

---

# 17. Phase 6.8 Completion Criteria

The specification is complete when:

- Sources can be evaluated independently of individual claims.
- Evidence quality can be assessed.
- Independent corroboration can be distinguished from repeated reporting.
- Individual claims can be verified.
- Contradictions can be detected and classified.
- Temporal consistency can be evaluated.
- Fact confidence can be estimated.
- Verification depth can adapt to research risk and complexity.
- Findings receive explicit evidence-based qualifications.
- Uncertainty and insufficient evidence remain visible.
- Security and provenance requirements are preserved.

**Completion status:** Specification complete when documented and reviewed. Reliability calibration, verification implementation, and evaluation testing remain future work.

---

# 18. Next Algorithm Group

**Phase 6.9 — Research Memory Management & Session Lifecycle**

The next document will define:

1. Research session creation and identity.
2. Research snapshot management.
3. Incremental research updates.
4. Finding persistence.
5. Source and evidence persistence.
6. Historical version management.
7. Research expiration and retention.
8. Session linking and deduplication.
9. Research integrity and recovery.

Phase 6.8 determines how findings should be qualified. Phase 6.9 defines how those findings and their research history should be stored, updated, and maintained.

**Important:** This document defines intended algorithmic behavior. It does not claim that source evaluation, verification, corroboration, or confidence-calibration systems have been implemented.
