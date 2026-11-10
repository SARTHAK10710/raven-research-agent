# Raven — Shared Algorithm Framework & Scoring System

**File:** `README.md`  
**Directory:** `docs/algorithms/`  
**Phase:** 6.1 — Shared Algorithm Framework  
**Status:** Architecture Specification

---

# 1. Purpose

This document establishes the common algorithm design principles, scoring definitions, confidence framework, validation rules and processing contracts for Raven.

Raven consists of three major processing components:

1. Memory Engine
2. Research Engine
3. Agent Orchestrator

Each component performs different operations and requires different decision-making mechanisms.

However, they must follow consistent principles when interpreting scores, handling uncertainty, validating outputs and modifying authoritative information.

This document establishes those shared principles.

**Important:** The shared framework defines common terminology and decision constraints. It does not force every engine to use the same scoring formula.

---

# 2. Processing Architecture

Raven follows a hybrid processing architecture combining deterministic algorithms, conventional NLP, statistical methods and selective non-generative ML models.

## 2.1 Deterministic Processing Layer

Responsible for operations requiring predictable and enforceable behaviour.

Examples:

- Input validation.
- Authorization.
- Ownership verification.
- Data integrity checks.
- State transitions.
- Lifecycle management.
- Deduplication constraints.
- Deletion propagation.
- Retry and recovery rules.
- Final validation before authoritative updates.

Deterministic controls must not be bypassed by model predictions.

## 2.2 Statistical and NLP Processing Layer

Responsible for structured information processing and measurable analytical operations.

Examples:

- Tokenization.
- Text normalization.
- Named entity recognition.
- Feature extraction.
- Statistical classification.
- Rule-assisted information extraction.
- Similarity feature analysis.
- Confidence estimation.

## 2.3 Non-Generative ML Layer

Responsible for selected semantic and predictive capabilities.

Examples:

- Text embeddings.
- Semantic similarity.
- Optional classification models.
- Ranking signals.
- Entity matching signals.
- Semantic clustering.

ML outputs are signals for downstream decisions, not authoritative decisions by themselves.

## 2.4 Processing and Validation Flow

A typical processing operation follows this sequence:

1. Receive input.
2. Validate input structure and permissions.
3. Normalize the input.
4. Extract relevant features.
5. Apply appropriate rules, statistical methods or ML models.
6. Calculate relevant scores.
7. Evaluate uncertainty and constraints.
8. Validate the proposed result.
9. Perform an authorized state transition if permitted.
10. Record the processing outcome.

Not every operation requires every stage.

---

# 3. Shared Scoring Framework

Raven must distinguish between different dimensions of information quality.

A single generic score must not represent relevance, confidence, importance, reliability and freshness simultaneously.

The following dimensions are established across Raven.

## 3.1 Relevance

**Definition:** Relevance measures how closely information relates to a particular task, query or processing objective.

Examples:

- How relevant is a memory to a user question?
- How relevant is a research source to the research objective?
- How relevant is a task result to the final response?

Relevance is context-dependent.

The same memory may be highly relevant to one query and irrelevant to another.

Relevance must not be interpreted as truth, importance or source reliability.

## 3.2 Confidence

**Definition:** Confidence measures how strongly available evidence supports a particular extracted fact, classification, match or conclusion.

Examples:

- Confidence that an extracted memory accurately represents the original input.
- Confidence that two entity mentions refer to the same entity.
- Confidence that a research finding is supported by its evidence.

Confidence must be associated with the specific proposition or decision being evaluated.

Confidence must not automatically increase simply because an operation has been repeated.

## 3.3 Importance

**Definition:** Importance measures the long-term or operational value of retaining or prioritizing information.

Examples:

- A user's long-term preference.
- A significant personal decision.
- A critical research finding.
- A high-priority execution task.

Importance is distinct from confidence.

An important memory can have low confidence and therefore require review rather than immediate promotion.

## 3.4 Reliability

**Definition:** Reliability measures the trustworthiness of a source, process or mechanism used to produce information.

Examples:

- Reliability of an official financial filing.
- Reliability of a research publication.
- Reliability of an extraction mechanism.
- Reliability of an external data provider.

Reliability is specific to the source or process being evaluated.

A reliable source can still publish outdated or incorrect information.

## 3.5 Freshness

**Definition:** Freshness measures how current information is relative to the time at which it is being used.

Freshness depends on:

- Original publication or event time.
- Last verification time.
- Information type.
- Expected rate of change.
- Current task requirements.

A historical event does not become incorrect simply because it is old.

Freshness must be interpreted according to context.

---

# 4. Separation of Scoring Dimensions

The five dimensions must remain logically independent.

| Scenario | Relevant interpretation |
|---|---|
| Important but uncertain memory | High importance, low confidence |
| Relevant but unreliable article | High relevance, low reliability |
| Reliable but outdated information | High reliability, low freshness |
| Accurate but irrelevant memory | High confidence, low relevance |
| Current but unverified claim | High freshness, uncertain confidence |

No dimension should automatically determine another.

For example:

- Importance must not artificially increase confidence.
- Relevance must not establish factual accuracy.
- Freshness must not establish source reliability.
- Source reliability must not prove every individual claim.
- Similarity must not prove entity identity.

---

# 5. Score Representation

## 5.1 Normalized Score Convention

Where a normalized score is useful, Raven may represent it using a numerical range from 0 to 1.

| Score | Interpretation |
|---|---|
| 0.00 | Lowest evaluated degree |
| 0.25 | Low |
| 0.50 | Intermediate |
| 0.75 | High |
| 1.00 | Highest evaluated degree |

These values represent a normalized scale, not universal probability or guaranteed accuracy.

A score of 0.90 must not automatically be interpreted as a 90% probability that a statement is true.

The interpretation depends on the underlying calculation and calibration.

## 5.2 Score Metadata

A score should retain enough information to be interpreted and audited.

Conceptual attributes:

- `score_type`
- `score_value`
- `scoring_method`
- `scoring_version`
- `evaluated_at`
- `input_references`
- `calibration_status`, where applicable

Not every score needs to be stored as an independent database record.

The owning engine decides whether the score belongs in the main record, a revision or a separate evaluation record.

## 5.3 Missing Scores

A missing score must not automatically be interpreted as zero.

Raven must distinguish:

- Not evaluated.
- Evaluation unavailable.
- Evaluation failed.
- Insufficient evidence.
- Score not applicable.

Missing information must not silently become a negative or positive decision.

---

# 6. Confidence Framework

Confidence is particularly important because Raven processes information that may be incomplete, ambiguous or inferred.

## 6.1 Confidence Sources

Confidence may be influenced by:

- Directness of the original evidence.
- Extraction quality.
- Source reliability.
- Independent corroboration.
- Contextual consistency.
- Temporal consistency.
- Entity resolution quality.
- Contradictory evidence.
- Processing method reliability.

Not all factors apply to every operation.

Each engine must define which factors are relevant to its confidence calculation.

## 6.2 Conceptual Confidence Levels

Raven will use the following conceptual confidence levels.

| Level | Meaning | Typical handling |
|---|---|---|
| Very High | Strong supporting evidence with no material unresolved conflict | Eligible for normal acceptance rules |
| High | Good supporting evidence with limited uncertainty | Eligible subject to domain validation |
| Medium | Partial or mixed evidence | Retain uncertainty and apply additional checks |
| Low | Weak or ambiguous evidence | Candidate, review or further verification |
| Insufficient | Evidence unavailable or inadequate | Do not assert as established information |

These labels are not universal numerical thresholds.

Each engine must define its own thresholds and acceptance policies through evaluation.

## 6.3 Confidence Is Not Truth

Raven must never treat confidence as proof.

A high-confidence extraction may still be wrong.

A low-confidence finding may eventually prove correct after further verification.

Confidence represents the strength of available support at a particular time.

## 6.4 Confidence Updates

Confidence may change when:

- New evidence becomes available.
- Existing evidence is corrected.
- A source becomes inaccessible or unreliable.
- A contradiction is discovered.
- An extraction error is identified.
- Entity resolution changes.
- A verification process produces new results.

Material confidence changes must be traceable.

---

# 7. Uncertainty Handling

Raven must preserve uncertainty rather than forcing every operation into a binary decision.

## 7.1 Uncertainty Categories

The system should distinguish:

1. Ambiguous input.
2. Incomplete information.
3. Conflicting evidence.
4. Low-confidence extraction.
5. Unresolved entity identity.
6. Unavailable source.
7. Stale information.
8. Failed evaluation.

## 7.2 Handling Policy

| Condition | Expected behaviour |
|---|---|
| Strong evidence | Proceed under domain acceptance rules |
| Partial evidence | Preserve uncertainty |
| Ambiguous entity | Avoid forced entity merging |
| Conflicting evidence | Preserve competing claims and investigate |
| Missing evidence | Avoid unsupported conclusions |
| Failed evaluation | Preserve failure state |
| Unavailable source | Seek alternatives where appropriate |
| Uncertain operation outcome | Reconcile before retrying |

## 7.3 Abstention

Raven must be able to abstain from making a decision.

Examples:

- Do not merge two entities when identity is uncertain.
- Do not promote a weakly supported memory into an established fact.
- Do not present a research claim as verified when evidence is insufficient.
- Do not execute a sensitive operation when authorization cannot be established.

Abstention is a valid processing outcome, not necessarily a system failure.

---

# 8. Engine-Specific Scoring Ownership

The shared framework establishes terminology. Each engine owns its domain-specific calculations.

## 8.1 Memory Engine

The Memory Engine may use the following scores:

| Score | Purpose |
|---|---|
| Extraction confidence | Measures how accurately information was extracted |
| Memory importance | Measures long-term value of retaining information |
| Memory relevance | Measures usefulness for a particular retrieval request |
| Entity match confidence | Measures support for associating mentions with entities |
| Duplicate similarity | Measures similarity between candidate and existing records |
| Contradiction confidence | Measures support for identifying a conflict |
| Freshness | Measures temporal currency where applicable |

Important constraints:

- Importance and confidence remain independent.
- Similarity alone cannot establish duplication.
- Repeated extraction alone cannot establish truth.
- Inferred memories require supporting evidence and appropriate confidence.
- Low-confidence information must remain appropriately classified.

## 8.2 Research Engine

The Research Engine may use:

| Score | Purpose |
|---|---|
| Source reliability | Evaluates the trustworthiness of a source |
| Fact confidence | Evaluates support for an individual claim |
| Evidence strength | Measures the quality and relevance of supporting evidence |
| Source relevance | Measures relevance to the research objective |
| Corroboration strength | Evaluates independent supporting sources |
| Freshness | Evaluates temporal suitability |
| Extraction confidence | Evaluates extraction quality |

Important constraints:

- Source reliability and fact confidence remain separate.
- Repeated copies do not count as independent corroboration.
- Official sources receive appropriate consideration but are not automatically treated as infallible.
- Historical findings must remain distinguishable from current findings.
- Conflicting evidence must be preserved.

## 8.3 Agent Orchestrator

The Orchestrator may use:

| Score | Purpose |
|---|---|
| Intent confidence | Evaluates confidence in request interpretation |
| Task priority | Determines execution importance |
| Urgency | Measures time sensitivity |
| Expected value | Estimates the contribution of a task |
| Resource cost | Estimates execution resource requirements |
| Routing confidence | Evaluates confidence in the selected destination |
| Dependency readiness | Determines whether a task can execute |

Important constraints:

- Security and authorization cannot be overridden by priority.
- Dependency requirements must be satisfied before execution.
- High-priority tasks do not automatically justify unlimited resource consumption.
- Uncertain routing must use fallback or clarification policies.

---

# 9. Scoring and Decision Thresholds

Raven will use configurable thresholds rather than hardcoding universal values throughout the system.

Each engine must define:

- Minimum acceptance thresholds.
- Review thresholds.
- Rejection conditions.
- Abstention conditions.
- Escalation conditions.
- Threshold calibration methods.

Thresholds must be evaluated using representative datasets.

## 9.1 Threshold Governance

A threshold change must not silently change the meaning of historical scores.

Material scoring changes should retain:

- Previous scoring version.
- New scoring version.
- Effective date.
- Relevant evaluation results.
- Expected behavioural changes.

## 9.2 Threshold Safety

No numerical threshold can override mandatory deterministic constraints.

Examples:

- A high confidence score cannot bypass authorization.
- A high similarity score cannot bypass entity validation.
- A high importance score cannot bypass privacy requirements.
- A high source reliability score cannot eliminate the need to inspect claim-specific evidence.

---

# 10. Shared Processing Contract

Every major algorithm must follow a consistent specification structure.

## 10.1 Required Specification Elements

1. Algorithm name.
2. Purpose.
3. Scope and ownership.
4. Inputs.
5. Preconditions.
6. Processing steps.
7. Decision rules.
8. Scoring dimensions used.
9. Outputs.
10. State transitions.
11. Validation rules.
12. Failure handling.
13. Edge cases.
14. Complexity and resource considerations.
15. Observability requirements.
16. Security and privacy considerations.
17. Acceptance criteria.

## 10.2 Processing Output

An algorithm's conceptual output should identify:

- Operation status.
- Result or result references.
- Relevant scores.
- Confidence or uncertainty.
- Decision outcome.
- Processing metadata.
- Failure or review reason, where applicable.

Exact serialization and API contracts will be defined during implementation design.

---

# 11. Quality-First Optimization

Quality is Raven's primary optimization objective.

The system must prioritize:

1. Correctness.
2. Data integrity.
3. Evidence quality.
4. Privacy and security.
5. Reliability.
6. Retrieval and decision quality.
7. Processing efficiency.
8. Computational cost.

This does not mean performance and cost are unimportant.

It means optimization must not compromise essential correctness guarantees.

Examples:

- Do not skip necessary verification merely to reduce latency.
- Do not merge uncertain memories to reduce storage.
- Do not discard conflicting research evidence to simplify response generation.
- Do not retry indefinitely in pursuit of a successful operation.
- Do not return stale cached information as current.

---

# 12. Evaluation and Measurement

Each algorithm must have measurable quality criteria.

## Memory Engine

- Extraction precision and recall.
- Candidate promotion quality.
- Duplicate detection precision and recall.
- Entity resolution accuracy.
- Contradiction detection quality.
- Retrieval relevance.
- Consolidation quality.
- Deletion completeness.

## Research Engine

- Discovery coverage.
- Extraction accuracy.
- Source evaluation quality.
- Evidence traceability.
- Independent corroboration quality.
- Verification accuracy.
- Freshness detection.
- Comparison correctness.

## Agent Orchestrator

- Intent classification accuracy.
- Routing correctness.
- Planning quality.
- Dependency correctness.
- Scheduling efficiency.
- Recovery success.
- Cancellation correctness.
- Response completeness.

Quantitative targets will be established during Phase 12 using representative evaluation datasets.

---

# 13. Architectural Constraints

The following rules apply to all subsequent Phase 6 specifications.

1. Hybrid processing is mandatory.
2. Deterministic controls govern sensitive and authoritative operations.
3. Conventional NLP and statistical methods should be preferred where appropriate.
4. Non-generative ML models may provide semantic and predictive capabilities.
5. Generative LLM APIs and locally hosted generative LLMs are excluded from core Raven processing.
6. ML predictions are signals, not authoritative decisions.
7. Relevance, confidence, importance, reliability and freshness must remain distinct.
8. Similarity is not proof of identity, duplication or truth.
9. Uncertainty must be preserved.
10. Abstention is a valid outcome.
11. All authoritative updates must respect ownership and authorization.
12. Processing must support idempotency and recovery.
13. Important decisions must be observable and traceable.
14. Quality takes priority over speed and cost.

---

# 14. Phase 6.1 Completion Criteria

Phase 6.1 is complete when:

- The hybrid processing architecture is documented.
- Shared scoring dimensions are defined.
- Confidence terminology is established.
- Uncertainty handling is specified.
- Engine-specific scoring ownership is defined.
- Threshold governance is established.
- The shared algorithm specification contract is established.
- Quality-first optimization principles are documented.

**Phase 6.1 status: ARCHITECTURE SPECIFICATION COMPLETE.**

This does not mean the scoring formulas, numerical thresholds, models or algorithms have been implemented, calibrated or tested.

---

# 15. Next Subphase

**Phase 6.2 — Memory Ingestion & Extraction**

The next specification will define:

- Memory input processing.
- Relevance Gate.
- Text normalization.
- Candidate generation.
- Atomic fact extraction.
- Importance evaluation.
- Extraction confidence.
- Explicit versus inferred information.
- Candidate validation and promotion.
- Failure and edge-case handling.

All Phase 6.2 algorithms must follow the shared framework established in this document.

---

**Project:** Raven  
**Phase:** 6 — Algorithms & Processing Design  
**Subphase:** 6.1 — Shared Algorithm Framework  
**Status:** Architecture Specification Complete
