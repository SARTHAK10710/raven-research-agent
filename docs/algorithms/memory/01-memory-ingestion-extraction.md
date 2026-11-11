# Raven — Memory Ingestion & Extraction

**Project:** Raven  
**Engine:** Memory Engine  
**Phase:** 6.2 — Memory Ingestion & Extraction  
**Document:** Memory Ingestion & Extraction Algorithm Specifications  
**Directory:** `docs/algorithms/memory/`  
**File:** `01-memory-ingestion-extraction.md`  
**Status:** Architecture & Algorithm Specification

---

# 1. Overview

This document defines how Raven receives information, determines its relevance, extracts factual information, evaluates potential memories, classifies their origin and generates validated memory candidates.

The Memory Ingestion & Extraction pipeline is responsible for transforming raw information into structured, evidence-backed memory candidates.

It must preserve the original meaning, context, ownership and provenance of information throughout processing.

The pipeline consists of six algorithms:

| Algorithm | Name | Primary responsibility |
|---|---|---|
| 6.2.1 | Input Validation & Normalization | Validate and prepare incoming information |
| 6.2.2 | Relevance Gate | Determine whether information deserves further processing |
| 6.2.3 | Atomic Fact Extraction | Extract independently meaningful factual propositions |
| 6.2.4 | Memory Evaluation | Evaluate importance, confidence, freshness and utility |
| 6.2.5 | Explicit & Inferred Memory Classification | Determine how information was obtained |
| 6.2.6 | Candidate Generation & Validation | Generate and validate structured memory candidates |

## 1.1 Processing Architecture

Raven follows a hybrid processing approach:

- Deterministic rules handle validation, ownership, structural integrity and state transitions.
- Conventional NLP and statistical methods support extraction and classification.
- Non-generative ML supports semantic analysis, similarity and ranking.
- Deterministic validation controls whether outputs can proceed to authoritative memory operations.

Generative LLM APIs and locally hosted generative LLMs are not dependencies of the core Raven processing pipeline.

## 1.2 Core Processing Flow

```text
Incoming Information
        |
        v
6.2.1 Input Validation & Normalization
        |
        v
6.2.2 Relevance Gate
        |
        +------ Reject / Defer
        |
        v
6.2.3 Atomic Fact Extraction
        |
        v
6.2.4 Memory Evaluation
        |
        v
6.2.5 Explicit & Inferred Classification
        |
        v
6.2.6 Candidate Generation & Validation
        |
        +------ Reject / Needs Review
        |
        v
Validated Memory Candidate
        |
        v
Phase 6.3 — Memory Resolution
        |
        v
Memory Storage & Lifecycle Management
```

**Important distinction:** A validated memory candidate is not automatically an active memory. Duplicate detection, entity resolution, contradiction handling and final memory updates belong to subsequent processing stages.

---

# 2. Shared Processing Principles

All six algorithms must follow these principles.

## 2.1 Quality First

The primary optimization objective is correctness and reliability.

Priority order:

1. Correctness.
2. Data integrity.
3. Evidence and provenance.
4. Privacy and security.
5. Reliability.
6. Memory quality.
7. Processing efficiency.
8. Infrastructure cost.

Speed and cost must not override correctness or data integrity.

## 2.2 Preserve Original Information

Original input must remain distinguishable from:

- Normalized content.
- Extracted propositions.
- Evaluated facts.
- Classified memories.
- Generated candidates.

Derived representations must retain links to their original evidence.

## 2.3 Separate Evaluation Dimensions

The following dimensions must remain independent:

| Dimension | Meaning |
|---|---|
| Relevance | How useful the information is for further processing |
| Importance | How valuable the information may be over time |
| Extraction confidence | How confidently the system extracted the proposition |
| Fact confidence | How strongly the available evidence supports the proposition |
| Source reliability | How trustworthy the originating source is |
| Freshness | How current the information is |
| Utility | How useful the information is for future retrieval or decisions |

These dimensions must not be collapsed into one universal score.

A highly important fact can have low confidence. A highly reliable source can contain information that is irrelevant to long-term memory.

## 2.4 Hybrid Processing

Use a combination of:

- Deterministic rules.
- Conventional NLP.
- Statistical methods.
- Non-generative machine learning.
- Explicit validation.

ML outputs are signals, not authority.

## 2.5 Uncertainty and Abstention

When evidence is incomplete or ambiguous:

- Preserve uncertainty.
- Mark the relevant fields.
- Lower confidence where justified.
- Request review where appropriate.
- Avoid unsupported assumptions.
- Do not promote uncertain information as confirmed fact.

Abstention is a valid outcome.

## 2.6 Idempotency and Traceability

Every operation must be traceable through stable identifiers and provenance references.

Retries must not create unintended duplicate operations or duplicate memory candidates.

---

# Algorithm 6.2.1 — Input Validation & Normalization

**Algorithm ID:** 6.2.1  
**Status:** Specification

## 3. Purpose

This algorithm defines how Raven receives, validates, normalizes and prepares incoming information for memory processing.

It establishes the entry point of the Memory Engine ingestion pipeline.

Initial supported input categories:

1. Text and user messages.
2. Conversation history.
3. Documents: PDF, DOCX and TXT.

The ingestion architecture follows a hybrid approach:

- Important inputs receive priority.
- Routine inputs are processed asynchronously.
- Explicit memory instructions receive appropriate priority.
- Explicit forgetting requests bypass ordinary extraction and enter the deletion workflow.

The objective is to ensure that accepted input is validated, traceable, securely handled and prepared for downstream processing.

## 3.1 Responsibilities

- Input type identification.
- Authentication and authorization checks.
- Ownership verification.
- Source metadata validation.
- Content integrity checks.
- Original content preservation.
- Text normalization.
- Document text extraction.
- Conversation structure preservation.
- Processing priority assignment.
- Synchronous or asynchronous routing.
- Duplicate ingestion protection.
- Input status tracking.
- Failure handling.

## 3.2 Supported Input Types

### Text and User Messages

Examples:

- Direct user statements.
- Explicit memory instructions.
- Preferences.
- Goals.
- Decisions.
- Important events.
- Knowledge shared by the user.

Original message content must be preserved.

Normalization must not rewrite the user's meaning.

### Conversation History

Conversation inputs may contain multiple messages.

Preserve:

- Conversation identifier.
- Message identifiers.
- Speaker or role.
- Original message order.
- Message timestamps.
- Original message content.
- Relevant source references.

Messages must not be flattened into one undifferentiated text block.

A statement made by another participant must not automatically become a personal fact about the user.

### Documents

Initially supported formats:

- PDF.
- DOCX.
- TXT.

The document ingestion process must:

1. Validate file type.
2. Validate file integrity.
3. Extract readable text.
4. Preserve the original document.
5. Capture available metadata.
6. Record parsing status.
7. Prepare normalized content.

Original documents must remain distinguishable from extracted text.

Scanned PDFs requiring OCR must be handled through a separately defined capability. OCR must not be assumed to exist simply because PDF support is enabled.

## 3.3 Input Contract

| Attribute | Purpose |
|---|---|
| `ingestion_id` | Unique ingestion operation identifier |
| `user_id` | Owning user |
| `source_type` | Text, conversation or document |
| `source_id` | Original source identifier |
| `content_reference` | Reference to original content |
| `received_at` | Time Raven received the input |
| `source_timestamp` | Original source timestamp |
| `content_metadata` | Source-specific metadata |
| `priority_hint` | Initial priority information |
| `instruction_type` | Normal, explicit remember or explicit forget |
| `schema_version` | Contract version |

These fields describe a logical contract, not a finalized database schema.

## 3.4 Preconditions

Before processing:

1. Input belongs to a supported category.
2. Originating user or system is authenticated.
3. User is authorized to submit the input.
4. Ownership scope is valid.
5. Input satisfies configured size and format constraints.
6. Original content can be safely accessed.
7. An ingestion identifier exists or can be assigned.

If mandatory conditions fail, processing must stop with an explicit reason.

## 3.5 Processing Algorithm

**Step 1 — Receive Input**

Capture original content or file reference, source type, user context, metadata and receipt timestamp.

Do not extract memories at this stage.

**Step 2 — Identify Input Type**

Determine whether the input is text, conversation history or a document.

For documents, inspect the actual file format where possible instead of trusting only the extension.

**Step 3 — Validate User and Ownership**

Validate identity, authorization and source ownership.

Missing ownership metadata must never be interpreted as public access.

**Step 4 — Validate Input Integrity**

For text:
- Check valid content and encoding.
- Detect empty or malformed input.

For conversations:
- Validate message structure.
- Preserve speakers and message boundaries.
- Validate available timestamps and identifiers.

For documents:
- Validate file integrity and actual format.
- Enforce configured file-size limits.
- Detect corrupted or unsupported files.
- Apply appropriate security inspection.

**Step 5 — Preserve Original Input**

Retain the original input separately from normalized content according to retention policy.

**Step 6 — Normalize Content**

Normalization may include:

- Unicode normalization.
- Line-ending standardization.
- Whitespace handling.
- Encoding normalization.
- Removal of unnecessary formatting artifacts.
- Document text extraction.
- Preservation of paragraph and section boundaries.

Normalization must not:

- Change semantic meaning.
- Remove negations.
- Remove meaningful punctuation.
- Convert uncertain statements into certain statements.
- Merge different speakers.
- Invent timestamps.
- Discard meaningful document structure.

**Step 7 — Handle Source-Specific Processing**

Normalize conversation messages individually.

Preserve document page and section references where available.

Keep original text distinguishable from normalized text.

**Step 8 — Identify Instruction Type**

Identify:

- Normal input.
- Explicit remember instruction.
- Explicit forget instruction.

Explicit remember prioritizes processing but does not bypass validation and evaluation.

Explicit forget must bypass ordinary extraction and enter the forgetting workflow.

**Step 9 — Assign Initial Priority**

Consider:

- Explicit user instruction.
- User-designated importance.
- Source type.
- Operational urgency.
- Existing processing requirements.

Initial priority is a scheduling signal, not the final memory importance score.

**Step 10 — Select Processing Mode**

Priority synchronous processing may be used for explicit memory instructions and important inputs.

Asynchronous processing may be used for routine conversations, large documents and bulk ingestion.

Acknowledging receipt must not be confused with confirming successful memory persistence.

**Step 11 — Prevent Duplicate Ingestion**

Use source identifiers and metadata. Content fingerprints may help identify repeated submissions.

Identical content does not always represent the same source event.

Memory-level duplicate detection remains the responsibility of Phase 6.3.

**Step 12 — Generate Normalized Input Package**

Produce a package containing:

- Ingestion identifier.
- User and ownership scope.
- Source type.
- Original content reference.
- Normalized content reference.
- Source metadata.
- Timestamps.
- Instruction classification.
- Processing priority.
- Processing mode.
- Validation result.
- Parsing result.

This package becomes the input to Algorithm 6.2.2.

## 3.6 Pseudocode

```text
FUNCTION ingest_input(input, user_context):

    ingestion = initialize_ingestion(input)

    IF NOT authenticate(user_context):
        RETURN AUTHENTICATION_FAILED

    IF NOT authorize_input(user_context, input):
        RETURN ACCESS_DENIED

    source_type = identify_source_type(input)

    IF source_type NOT IN [TEXT, CONVERSATION, DOCUMENT]:
        RETURN UNSUPPORTED_INPUT

    IF NOT validate_input_integrity(input):
        RETURN INVALID_INPUT

    IF NOT validate_ownership(input, user_context):
        RETURN OWNERSHIP_VALIDATION_FAILED

    preserve_original_input(input)

    normalized = normalize_by_source_type(input)

    IF normalized.status == FAILED:
        RETURN PARSING_FAILED

    instruction = identify_memory_instruction(normalized)

    IF instruction == EXPLICIT_FORGET:
        RETURN route_to_forgetting_workflow(input)

    existing = check_existing_ingestion(input)

    IF existing IS ALREADY_PROCESSING:
        RETURN existing.ingestion_reference

    IF existing IS ALREADY_COMPLETED:
        RETURN reconcile_existing_ingestion(existing)

    priority = assign_initial_priority(normalized, instruction)

    package = create_normalized_input_package(
        input,
        normalized,
        priority,
        instruction
    )

    IF priority_requires_immediate_processing:
        RETURN submit_to_synchronous_pipeline(package)

    RETURN enqueue_for_async_processing(package)
```

## 3.7 Output and Statuses

Possible outcomes:

- `validated`
- `queued`
- `rejected`
- `invalid_input`
- `unsupported_input`
- `access_denied`
- `ownership_validation_failed`
- `parsing_failed`
- `processing_failed`

A queued operation does not mean memory extraction or persistence has completed.

## 3.8 Failure Handling

| Failure | Expected behaviour |
|---|---|
| Invalid user context | Reject |
| Unauthorized input | Reject |
| Unsupported format | Return explicit status |
| Corrupted document | Mark parsing failure |
| Empty content | Reject or mark empty according to policy |
| Partial extraction | Preserve partial status |
| Encoding error | Safe normalization or rejection |
| Duplicate submission | Reconcile existing operation |
| Queue unavailable | Retry safely or retain pending state |
| Storage failure | Do not report successful preservation |
| Cancellation | Stop eligible processing and preserve state |

A timeout is not proof that an operation failed. Reconcile using the ingestion identifier before retrying.

## 3.9 Security and Privacy

- Authenticate the originating user or system.
- Validate ownership before accepting private data.
- Apply user isolation.
- Treat uploaded documents as untrusted.
- Inspect files before parsing.
- Restrict access to original and normalized content.
- Avoid logging raw sensitive information unnecessarily.
- Apply retention and deletion policies.

## 3.10 Acceptance Criteria

- AC-01: Valid text is accepted and normalized.
- AC-02: Conversation speaker and message ordering are preserved.
- AC-03: PDF, DOCX and TXT are validated.
- AC-04: Unsupported formats are rejected.
- AC-05: Original content remains distinguishable from normalized content.
- AC-06: Invalid authorization prevents ingestion.
- AC-07: Cross-user ownership violations are rejected.
- AC-08: Explicit remember receives appropriate priority.
- AC-09: Explicit forget bypasses normal extraction.
- AC-10: Routine inputs can enter asynchronous processing.
- AC-11: Important inputs can enter priority processing.
- AC-12: Duplicate submissions do not create unintended duplicate operations.
- AC-13: Partial document extraction is represented.
- AC-14: Parsing and storage failures are traceable.
- AC-15: Normalization preserves original meaning.
- AC-16: Successful ingestion does not automatically create active memory.

**Specification status:** COMPLETE.

---

# Algorithm 6.2.2 — Relevance Gate

**Algorithm ID:** 6.2.2  
**Status:** Specification

## 4. Purpose

The Relevance Gate determines whether incoming information deserves further memory extraction and evaluation.

Its objective is to reduce unnecessary processing without prematurely discarding information that may be important.

This is an initial filtering stage, not the final memory importance evaluator.

## 4.1 Responsibilities

- Evaluate potential memory relevance.
- Identify information with possible long-term value.
- Identify contextually significant information.
- Detect explicit user intent.
- Apply protection rules for important inputs.
- Route information to processing, deferral or rejection.
- Record the reason for the decision.

## 4.2 Input Contract

| Attribute | Purpose |
|---|---|
| `ingestion_id` | Original ingestion reference |
| `user_id` | User scope |
| `source_type` | Input category |
| `normalized_content` | Normalized content |
| `source_metadata` | Source information |
| `instruction_type` | Normal, remember or forget |
| `received_at` | Receipt timestamp |
| `processing_priority` | Initial priority |
| `validation_status` | Input validation result |

## 4.3 Relevance Dimensions

### Personal Relevance

Does the information relate to the user's life, preferences, activities, responsibilities or interests?

### Long-Term Utility

Could the information help with future conversations, decisions or tasks?

### Temporal Significance

Does the information relate to an important event, deadline, milestone or time-sensitive situation?

### Contextual Significance

Does the information provide meaningful context for understanding other information?

### Explicit User Intent

Has the user directly requested that information be remembered?

### Information Density

Does the input contain meaningful information rather than mostly noise or repetitive content?

These dimensions are independent indicators, not a universal truth score.

## 4.4 Processing Approach

Use a hybrid evaluation model.

**Deterministic rules:**
- Explicit remember instructions.
- Explicit forget instructions.
- Supported source validation.
- Known priority conditions.
- Structural checks.

**NLP and statistical methods:**
- Statement classification.
- Feature identification.
- Information density.
- Contextual signals.

**Non-generative ML:**
- Semantic relevance signals.
- Classification signals.
- Context similarity.

## 4.5 Relevance Score

A conceptual relevance score may be represented as:

\[
R = w_pP + w_lL + w_tT + w_cC + w_dD
\]

Where:

- \(P\): Personal relevance.
- \(L\): Long-term utility.
- \(T\): Temporal significance.
- \(C\): Contextual significance.
- \(D\): Information density.
- \(w\): Configurable weights.

The weights and thresholds are not finalized. They must be calibrated using evaluation data.

A normalized score is not automatically a probability that information is true or important.

Missing feature values must not automatically be treated as zero.

## 4.6 Processing Outcomes

| Outcome | Meaning |
|---|---|
| `PROCESS` | Send to detailed extraction |
| `DEFER` | Retain for controlled later processing |
| `REJECT` | Do not continue ordinary memory extraction |

A rejection must have an explicit reason.

## 4.7 Protection Rules

The following must receive appropriate protection against premature filtering:

- Explicit remember instructions.
- Important user-designated information.
- Significant personal events.
- Contextual corrections.
- Information needed to understand an ongoing commitment.
- Ambiguous inputs where premature rejection could lose important meaning.

Explicit forget instructions bypass this algorithm and enter the deletion workflow.

Explicit remember does not guarantee promotion to active memory. It guarantees priority consideration and subsequent evaluation.

## 4.8 Processing Algorithm

**Step 1 — Receive Input**

Receive the validated normalized package from 6.2.1.

**Step 2 — Check Instruction Type**

If explicit forget, route to deletion.

If explicit remember, prioritize further processing.

**Step 3 — Identify Relevance Features**

Identify personal, temporal, contextual and informational signals.

**Step 4 — Evaluate Features**

Use deterministic, NLP, statistical and non-generative ML methods as appropriate.

**Step 5 — Calculate Relevance**

Calculate a configurable relevance score where sufficient features exist.

**Step 6 — Apply Protection Rules**

Check explicit intent and other protected conditions.

**Step 7 — Determine Outcome**

Select PROCESS, DEFER or REJECT.

**Step 8 — Record Decision**

Store the decision, reason, score metadata and processing version.

**Step 9 — Route Input**

Send PROCESS outcomes to 6.2.3.

## 4.9 Pseudocode

```text
FUNCTION evaluate_relevance(input):

    IF input.instruction_type == EXPLICIT_FORGET:
        RETURN route_to_forgetting_workflow(input)

    IF input.instruction_type == EXPLICIT_REMEMBER:
        RETURN PROCESS_WITH_PRIORITY

    features = extract_relevance_features(input)

    relevance = calculate_relevance(features)

    protections = evaluate_protection_rules(input, features)

    IF protections.require_processing:
        RETURN PROCESS_WITH_PRIORITY

    IF protections.require_review:
        RETURN DEFER

    IF relevance.meets_processing_policy:
        RETURN PROCESS

    IF relevance.requires_more_context:
        RETURN DEFER

    RETURN REJECT_WITH_REASON
```

## 4.10 Failure Handling

| Failure | Expected behaviour |
|---|---|
| Missing context | Defer or evaluate using available evidence |
| Uncertain relevance | Avoid automatic rejection |
| Scoring failure | Use approved deterministic fallback or defer |
| Explicit remember | Prioritize processing |
| Explicit forget | Route to deletion |
| Duplicate information | Preserve source and defer memory-level resolution |
| NLP failure | Use safe fallback or defer |

## 4.11 Acceptance Criteria

- AC-01: Relevant information proceeds to extraction.
- AC-02: Clearly irrelevant information can be rejected with a reason.
- AC-03: Ambiguous information can be deferred.
- AC-04: Explicit remember receives priority.
- AC-05: Explicit forget bypasses ordinary extraction.
- AC-06: Relevance and importance remain separate.
- AC-07: Missing features are not automatically treated as zero.
- AC-08: Scoring decisions are traceable.
- AC-09: ML signals do not independently authorize memory creation.
- AC-10: Uncertain inputs are not prematurely discarded.

**Specification status:** COMPLETE.

---

# Algorithm 6.2.3 — Atomic Fact Extraction

**Algorithm ID:** 6.2.3  
**Status:** Specification

## 5. Purpose

Atomic Fact Extraction converts relevant input into independently meaningful, evidence-linked fact proposals.

It transforms natural-language information into structured propositions while preserving original meaning, context, speaker attribution and temporal details.

The algorithm must not create active memories.

## 5.1 Responsibilities

- Identify candidate factual statements.
- Segment content into meaningful units.
- Extract atomic fact proposals.
- Identify subjects, predicates and objects.
- Extract values and attributes.
- Preserve context.
- Identify temporal references.
- Preserve negation and modality.
- Resolve references using available local context.
- Maintain source attribution.
- Estimate extraction confidence.
- Identify ambiguous proposals.
- Generate structured output.

## 5.2 Definition of an Atomic Fact

An atomic fact is one independently meaningful proposition that can be evaluated, updated, retrieved or linked to other facts independently.

Example:

"I am a software engineering student, currently learning Kotlin, and I want to become an Android developer."

Possible fact proposals:

1. The user is a software engineering student.
2. The user is currently learning Kotlin.
3. The user wants to become an Android developer.

However, tightly connected attributes must remain together.

Example:

"I started my internship at Company X on 11 June 2025 for two months."

The internship, organization, start date and duration must remain connected.

**Granularity principle:** Split independently meaningful propositions, but do not fragment information in a way that destroys its meaning.

## 5.3 Input Contract

| Attribute | Purpose |
|---|---|
| `ingestion_id` | Original ingestion reference |
| `user_id` | User scope |
| `source_type` | Text, conversation or document |
| `source_reference` | Original source |
| `normalized_content` | Content to process |
| `source_metadata` | Original metadata |
| `processing_context` | Available context |
| `relevance_result` | Result from 6.2.2 |
| `schema_version` | Contract version |

## 5.4 Hybrid Extraction Approach

**Deterministic processing:**
- Source boundaries.
- Speaker attribution.
- Sentence segmentation.
- Negation preservation.
- Timestamp preservation.
- Explicit patterns.
- Numeric normalization where unambiguous.
- Provenance attachment.
- Output validation.

**Conventional NLP:**
- Tokenization.
- Part-of-speech identification.
- Named entity recognition.
- Dependency parsing.
- Relation extraction.
- Temporal expression detection.
- Coreference candidate identification.

**Non-generative ML:**
- Entity recognition signals.
- Statement classification.
- Relation extraction signals.
- Semantic feature identification.
- Coreference scoring.
- Extraction confidence estimation.

ML predictions must not independently authorize changes to authoritative memory.

## 5.5 Statement Classification

| Statement type | Example | Treatment |
|---|---|---|
| Factual assertion | "I work at Company X." | Extract proposition |
| Preference | "I prefer dark mode." | Extract preference proposal |
| Goal | "I want to become an engineer." | Preserve intended goal |
| Decision | "I decided to use PostgreSQL." | Preserve decision proposal |
| Question | "Should I learn Kotlin?" | Do not turn into a fact |
| Hypothetical | "If I move abroad..." | Preserve hypothetical context |
| Opinion | "Company X is the best." | Attribute as opinion |
| Quoted statement | "My friend said he is moving." | Preserve attribution |
| Conditional | "If selected, I will relocate." | Preserve condition |
| Negated | "I do not work there." | Preserve negation |
| Uncertain | "I might move next year." | Preserve uncertainty |

Final explicit-versus-inferred classification is handled by 6.2.5.

## 5.6 Fact Representation

Raven uses a hybrid natural-language and structured representation.

| Attribute | Purpose |
|---|---|
| `fact_proposal_id` | Unique proposal identifier |
| `ingestion_id` | Original ingestion reference |
| `user_id` | User scope |
| `original_text` | Exact supporting source text |
| `normalized_proposition` | Normalized factual statement |
| `subject` | Subject or entity |
| `predicate` | Relationship or property |
| `object` | Related entity, value or object |
| `context` | Interpretation context |
| `temporal_information` | Dates and periods |
| `modality` | Factual, intended, possible, conditional |
| `negation` | Whether proposition is negated |
| `conditions` | Conditions attached to proposition |
| `speaker_reference` | Original speaker |
| `source_reference` | Original source |
| `source_location` | Message, paragraph, page or text span |
| `extraction_method` | Method used |
| `extraction_confidence` | Confidence in extraction |
| `extraction_status` | Processing outcome |

This is a conceptual contract, not a finalized database schema.

## 5.7 Processing Algorithm

1. Receive relevant normalized content.
2. Validate relevance outcome.
3. Segment content into meaningful units.
4. Preserve message, speaker and document boundaries.
5. Classify preliminary statement types.
6. Identify candidate factual propositions.
7. Extract subjects, predicates, objects and attributes.
8. Apply atomicity rules.
9. Extract contextual information.
10. Extract temporal information.
11. Preserve negation and modality.
12. Resolve local references where evidence supports it.
13. Attach original source evidence.
14. Estimate extraction confidence.
15. Validate proposals.
16. Produce structured fact proposals.

## 5.8 Important Extraction Rules

### Preserve Temporal Meaning

"I started learning Python three months ago."

Preserve the relative temporal expression and reference timestamp.

Do not invent an absolute date when the reference timestamp is missing.

### Preserve Conditions

"I will relocate if I get selected."

Do not convert this into a confirmed relocation.

### Preserve Negation

"I do not work at Company X."

Do not extract the positive statement that the user works there.

### Preserve Speaker Attribution

"My friend is learning Java."

The subject is the friend, not the user.

### Preserve Corrections

"I said June earlier, but it was actually July."

Preserve the correction and its relationship to the earlier statement. Resolution belongs to Phase 6.3.

### Preserve Quantities and Units

"I run 5 kilometres every morning."

Preserve activity, quantity, unit and frequency.

## 5.9 Extraction Confidence

Extraction confidence measures confidence in the extraction process, not objective truth.

Consider:

- Clarity of source statement.
- Subject identification.
- Predicate identification.
- Relation extraction.
- Temporal interpretation.
- Reference resolution.
- Source completeness.

Repetition alone must not increase extraction confidence.

## 5.10 Output Contract

The output contains:

- `ingestion_id`
- `extraction_id`
- `user_id`
- `fact_proposals`
- `extraction_status`
- `extraction_method`
- `processing_version`
- `source_coverage`
- `warnings`
- `created_at`

Conceptual proposal statuses:

- `extracted`
- `needs_review`
- `partially_extracted`
- `rejected`
- `failed`

A successful extraction may return zero fact proposals. This must be distinguished from a processing failure.

## 5.11 Pseudocode

```text
FUNCTION extract_atomic_facts(package):

    IF package.relevance_result != PROCESS:
        RETURN NOT_ELIGIBLE_FOR_EXTRACTION

    segments = segment_content(package.normalized_content)

    proposals = []

    FOR EACH segment IN segments:

        statements = classify_statement_types(segment)

        FOR EACH statement IN statements:

            IF statement_is_unsupported(statement):
                CONTINUE

            candidate = identify_candidate_fact(statement)

            IF candidate IS NOT SUPPORTED:
                CONTINUE

            components = extract_fact_components(candidate)

            components = preserve_context(components)

            components = extract_temporal_information(components)

            components = preserve_negation_and_modality(components)

            components = resolve_local_references(components)

            atomic_proposals = apply_atomicity_rules(components)

            FOR EACH proposal IN atomic_proposals:

                attach_source_evidence(proposal, package)

                estimate_extraction_confidence(proposal)

                validation = validate_fact_proposal(proposal)

                IF validation == VALID:
                    proposal.status = EXTRACTED
                    proposals.append(proposal)

                ELSE IF validation == AMBIGUOUS:
                    proposal.status = NEEDS_REVIEW
                    proposals.append(proposal)

                ELSE:
                    record_rejection_reason(proposal)

    RETURN create_extraction_result(proposals)
```

## 5.12 Failure Handling

| Failure | Expected behaviour |
|---|---|
| Segmentation failure | Record affected segment |
| Ambiguous subject | Mark for review |
| Ambiguous pronoun | Preserve unresolved reference |
| Incorrect speaker attribution | Reject affected proposal |
| Missing source location | Preserve available provenance |
| Temporal ambiguity | Retain original expression |
| Negation detection failure | Avoid accepting potentially altered proposition |
| Incomplete document | Mark partial extraction |
| NLP failure | Retry safely or use approved fallback |
| Low extraction confidence | Mark for review |
| Validation failure | Reject affected proposal |

A failure affecting one proposal should not automatically discard all successful proposals.

## 5.13 Acceptance Criteria

- AC-01: Relevant normalized content produces fact proposals.
- AC-02: Independent facts can be separated.
- AC-03: Tightly connected attributes retain shared meaning.
- AC-04: Subject, predicate and object are extracted where applicable.
- AC-05: Original supporting text is preserved.
- AC-06: Speaker attribution is maintained.
- AC-07: Questions are not converted into assertions.
- AC-08: Hypothetical statements remain conditional.
- AC-09: Negation is preserved.
- AC-10: Modality and uncertainty are preserved.
- AC-11: Temporal information is not fabricated.
- AC-12: Quantities and units are preserved.
- AC-13: Ambiguous references are not guessed.
- AC-14: Quoted information retains attribution.
- AC-15: Every proposal has traceable evidence.
- AC-16: Extraction confidence is separate from fact confidence.
- AC-17: Low-confidence proposals can require review.
- AC-18: Partial failures preserve valid proposals.
- AC-19: Empty results are distinguishable from failures.
- AC-20: Extraction does not create active memories.

**Specification status:** COMPLETE.

---

# Algorithm 6.2.4 — Memory Evaluation

**Algorithm ID:** 6.2.4  
**Status:** Specification

## 6. Purpose

Memory Evaluation determines the potential value, reliability and usefulness of extracted fact proposals.

Its purpose is to evaluate which information deserves consideration for long-term memory and how confidently the underlying information is supported.

This algorithm evaluates extracted facts. It does not decide whether information is explicit or inferred, and it does not directly create memory candidates.

## 6.1 Responsibilities

- Evaluate memory importance.
- Evaluate fact confidence.
- Evaluate freshness.
- Estimate long-term utility.
- Consider contextual significance.
- Identify uncertainty.
- Identify incomplete or weakly supported information.
- Produce evaluation metadata.
- Recommend whether a proposal should proceed, require review or be rejected.

## 6.2 Input Contract

| Attribute | Purpose |
|---|---|
| `extraction_id` | Extraction operation |
| `fact_proposal_id` | Extracted fact identifier |
| `user_id` | User scope |
| `normalized_proposition` | Extracted proposition |
| `context` | Relevant context |
| `temporal_information` | Temporal attributes |
| `extraction_confidence` | Extraction confidence |
| `source_reference` | Evidence source |
| `source_metadata` | Source metadata |
| `speaker_reference` | Original speaker |
| `evaluation_version` | Evaluation method version |

## 6.3 Evaluation Dimensions

### A. Importance

Importance estimates the potential value of retaining the information over time.

Possible indicators:

- Personal significance.
- Long-term relevance.
- Relationship significance.
- Goal or commitment relevance.
- Decision significance.
- Recurrence or ongoing relevance.
- User-designated importance.

Examples:

| Information | Potential importance |
|---|---|
| Long-term career goal | High |
| Persistent communication preference | High |
| Major personal decision | High |
| Important relationship context | High |
| Temporary restaurant preference | Context-dependent |
| One-time irrelevant observation | Low |

Importance is contextual and must not be based only on repetition.

### B. Fact Confidence

Fact confidence estimates how strongly the available evidence supports the extracted proposition.

Consider:

- Directness of the statement.
- Source attribution.
- Evidence completeness.
- Contextual consistency.
- Uncertainty in the original statement.
- Whether the statement is quoted or second-hand.
- Whether the statement is conditional or hypothetical.

A direct assertion and a tentative possibility must not receive equivalent treatment.

### C. Freshness

Freshness estimates how current the information is relative to its intended use.

Consider:

- Original timestamp.
- Time sensitivity.
- Whether the information describes a changing state.
- Whether newer evidence exists.
- Whether the fact is historical or current.

Different memory types require different freshness behaviour.

For example:

- A person's birth date does not become stale in the same way as their current job.
- A temporary project deadline becomes less useful after the deadline passes.
- A preference may remain valid until corrected or superseded.

### D. Long-Term Utility

Long-term utility estimates whether retaining the information may improve future retrieval or decisions.

Consider:

- Likelihood of future relevance.
- Reusability across conversations.
- Relationship to ongoing projects.
- Value for future personalization.
- Value for contextual continuity.

### E. Contextual Significance

Contextual significance estimates whether the information helps interpret other facts or ongoing situations.

Examples:

- A project deadline related to an existing project.
- A decision connected to a career goal.
- A preference that affects multiple future recommendations.
- An event related to an ongoing commitment.

## 6.4 Evaluation Score Framework

Each dimension must be evaluated independently.

Conceptually:

```text
importance_score
fact_confidence_score
freshness_score
long_term_utility_score
contextual_significance_score
```

Scores may use normalized values between 0 and 1 where appropriate.

However:

- A score of 0.90 is not automatically a 90% probability that a fact is true.
- Missing information must not automatically become zero.
- Different scoring dimensions must not be combined without an explicit evaluation policy.
- Thresholds must be configurable.
- Scoring methods and versions must be recorded.
- Numerical thresholds require calibration during evaluation.

## 6.5 Evidence-Aware Evaluation

The algorithm must distinguish different evidence situations.

| Evidence situation | Evaluation behaviour |
|---|---|
| Direct user assertion | Evaluate as direct evidence |
| Explicitly uncertain assertion | Preserve uncertainty |
| Quoted statement | Preserve original attribution |
| Third-party information | Do not attribute automatically to user |
| Hypothetical | Do not evaluate as completed fact |
| Conditional plan | Preserve condition |
| Repeated statement | Record additional evidence without assuming independence |
| Missing source timestamp | Avoid invented freshness |
| Contradictory evidence | Mark conflict for Phase 6.3 |

## 6.6 Processing Algorithm

**Step 1 — Receive Fact Proposals**

Receive extracted proposals from 6.2.3.

**Step 2 — Validate Extraction Output**

Check source references, proposition structure and extraction status.

**Step 3 — Evaluate Importance**

Estimate potential long-term value using deterministic rules and supported statistical signals.

**Step 4 — Evaluate Fact Confidence**

Assess how strongly the source supports the proposition.

**Step 5 — Evaluate Freshness**

Consider temporal context and the nature of the information.

**Step 6 — Estimate Long-Term Utility**

Evaluate potential usefulness in future interactions.

**Step 7 — Evaluate Contextual Significance**

Identify connections to ongoing goals, projects, commitments and other context.

**Step 8 — Identify Uncertainty**

Mark missing evidence, weak attribution, ambiguity and conditional information.

**Step 9 — Produce Evaluation Result**

Generate independent evaluation dimensions and a processing recommendation.

**Step 10 — Pass to Classification**

Send eligible fact proposals and their evaluation metadata to 6.2.5.

## 6.7 Evaluation Outcomes

| Outcome | Meaning |
|---|---|
| `PROCEED` | Suitable for memory classification |
| `NEEDS_REVIEW` | Requires additional context or review |
| `REJECT` | Does not satisfy memory processing policy |
| `DEFER` | Re-evaluation may be useful later |

These outcomes are processing decisions, not final memory lifecycle states.

## 6.8 Pseudocode

```text
FUNCTION evaluate_memory(fact_proposal):

    validate_extraction_output(fact_proposal)

    IF fact_proposal.status == FAILED:
        RETURN REJECT

    importance = evaluate_importance(fact_proposal)

    fact_confidence = evaluate_fact_confidence(
        fact_proposal.source_evidence,
        fact_proposal.context,
        fact_proposal.modality
    )

    freshness = evaluate_freshness(
        fact_proposal.temporal_information,
        fact_proposal.source_timestamp
    )

    utility = evaluate_long_term_utility(fact_proposal)

    context_significance = evaluate_contextual_significance(
        fact_proposal
    )

    uncertainty = identify_uncertainty(fact_proposal)

    result = create_evaluation_result(
        importance,
        fact_confidence,
        freshness,
        utility,
        context_significance,
        uncertainty
    )

    IF result.contains_critical_ambiguity:
        RETURN NEEDS_REVIEW

    IF result.violates_memory_policy:
        RETURN REJECT

    IF result.requires_future_context:
        RETURN DEFER

    RETURN PROCEED_WITH_EVALUATION(result)
```

## 6.9 Failure Handling

| Failure | Expected behaviour |
|---|---|
| Missing extraction confidence | Flag incomplete evaluation |
| Missing timestamp | Do not invent freshness |
| Incomplete source evidence | Lower confidence or request review |
| Scoring failure | Use approved fallback or defer |
| Contradictory evidence | Preserve conflict for Phase 6.3 |
| Uncertain statement | Preserve uncertainty |
| Missing context | Avoid unsupported conclusions |
| Evaluation timeout | Retry safely using operation identity |

## 6.10 Acceptance Criteria

- AC-01: Every eligible fact proposal receives an evaluation result.
- AC-02: Importance is evaluated independently.
- AC-03: Fact confidence is evaluated independently.
- AC-04: Freshness is evaluated separately.
- AC-05: Long-term utility is considered.
- AC-06: Contextual significance is considered.
- AC-07: Uncertainty is explicitly represented.
- AC-08: Quoted information retains attribution.
- AC-09: Repetition is not treated as independent proof.
- AC-10: Missing timestamps are not invented.
- AC-11: Contradictions are preserved for resolution.
- AC-12: Evaluation decisions are traceable.
- AC-13: Uncertain facts can require review.
- AC-14: Evaluation does not directly create active memories.

**Specification status:** COMPLETE.

---

# Algorithm 6.2.5 — Explicit & Inferred Memory Classification

**Algorithm ID:** 6.2.5  
**Status:** Specification

## 7. Purpose

This algorithm determines whether an evaluated fact proposal originates from an explicit statement or an inference derived from available information.

Its objective is to preserve the distinction between what the user directly communicated and what Raven derived from contextual evidence.

This distinction is essential for memory reliability, user trust and future retrieval.

## 7.1 Responsibilities

- Identify explicit information.
- Identify inferred information.
- Preserve supporting evidence.
- Evaluate inference confidence.
- Identify unsupported conclusions.
- Classify the origin of each fact proposal.
- Assign appropriate review requirements.
- Prevent weak inferences from becoming authoritative memories.

## 7.2 Classification Categories

### Explicit Memory

Information directly communicated by the user or explicitly provided through an authorized source.

Examples:

- "I am learning Kotlin."
- "I prefer dark mode."
- "Remember that I am preparing for placements."
- "I have decided to use PostgreSQL."

An explicit statement does not automatically mean the information is objectively verified.

It means the origin of the information is direct.

### Inferred Memory

Information derived from one or more pieces of evidence without being directly stated in the same form.

Examples:

- Repeated direct statements may support a possible ongoing preference.
- Multiple project discussions may suggest an ongoing project.
- Repeated scheduling information may suggest a recurring routine.

Inferences must retain the evidence from which they were derived.

### Unknown or Unresolved Origin

Some information may have insufficient evidence to determine whether it was explicitly stated or inferred.

Such information must not be forced into either category.

It should remain unresolved or require review.

## 7.3 Input Contract

| Attribute | Purpose |
|---|---|
| `fact_proposal_id` | Fact proposal identifier |
| `user_id` | User scope |
| `normalized_proposition` | Extracted proposition |
| `speaker_reference` | Original speaker |
| `source_reference` | Original source |
| `source_evidence` | Supporting source spans |
| `extraction_confidence` | Extraction confidence |
| `fact_confidence` | Evaluation confidence |
| `evaluation_result` | Result from 6.2.4 |
| `context` | Available supporting context |
| `processing_version` | Classification version |

## 7.4 Classification Rules

### Rule 1 — Direct User Statement

If the user directly states a proposition, classify it as explicit.

Example:

"I prefer working in the morning."

Classification: Explicit.

### Rule 2 — Explicit Memory Instruction

If the user directly requests that something be remembered, classify the stated information as explicit and prioritize its processing.

However, explicit remember does not bypass validation, authorization or candidate validation.

### Rule 3 — Contextual Inference

If the proposition is derived from contextual evidence rather than directly stated, classify it as inferred.

The inference must retain its evidence references.

### Rule 4 — Third-Party Information

If the user describes another person's information, preserve the correct subject and attribution.

Do not automatically classify it as a personal fact about the user.

### Rule 5 — Quoted Information

Quoted statements must retain their original speaker attribution.

A quoted statement does not become an explicit personal assertion by the user.

### Rule 6 — Weak Inference

If the evidence is insufficient, classify the proposition as unresolved or require review.

Do not promote it merely because similar statements appear repeatedly.

### Rule 7 — Hypothetical and Conditional Information

Hypothetical and conditional statements must preserve their modality.

They must not become confirmed facts.

## 7.5 Inference Confidence

Inference confidence measures the strength of evidence supporting the derived interpretation.

Consider:

- Number and quality of supporting evidence sources.
- Independence of evidence.
- Contextual consistency.
- Temporal consistency.
- Subject attribution.
- Alternative explanations.
- Ambiguity.

Repeated copies of the same original information must not be treated as independent evidence.

Inference confidence is separate from importance and source reliability.

## 7.6 Inference Lifecycle

Inferred information must have a controlled lifecycle.

Conceptual states:

- `candidate`
- `active`
- `needs_review`
- `rejected`

A weak inference must remain a candidate or require review.

An inference must not become active simply because it appears repeatedly.

Promotion requires sufficient evidence and the applicable validation rules.

## 7.7 Processing Algorithm

**Step 1 — Receive Evaluated Fact**

Receive the evaluated fact proposal from 6.2.4.

**Step 2 — Inspect Original Source**

Determine whether the proposition appears directly in the source.

**Step 3 — Validate Attribution**

Identify the original speaker and subject.

**Step 4 — Determine Origin**

Classify as explicit, inferred or unresolved.

**Step 5 — Evaluate Inference Evidence**

For inferred information, inspect supporting evidence and alternative explanations.

**Step 6 — Estimate Inference Confidence**

Estimate confidence without treating repetition as independent proof.

**Step 7 — Apply Classification Rules**

Determine whether the information can proceed, requires review or should be rejected.

**Step 8 — Preserve Provenance**

Attach supporting source references and classification rationale.

**Step 9 — Generate Classification Result**

Pass the classified proposal to Algorithm 6.2.6.

## 7.8 Pseudocode

```text
FUNCTION classify_memory_origin(fact_proposal):

    validate_evaluation_result(fact_proposal)

    attribution = validate_speaker_and_subject(fact_proposal)

    IF attribution.is_invalid:
        RETURN NEEDS_REVIEW

    IF proposition_is_directly_supported_by_user_source(
        fact_proposal
    ):
        origin = EXPLICIT

    ELSE IF proposition_is_supported_by_derived_evidence(
        fact_proposal
    ):
        origin = INFERRED

    ELSE:
        origin = UNRESOLVED

    IF origin == INFERRED:

        evidence = collect_supporting_evidence(fact_proposal)

        confidence = evaluate_inference_confidence(evidence)

        IF confidence.is_insufficient:
            RETURN NEEDS_REVIEW

        IF evidence.has_unsupported_assumptions:
            RETURN REJECT

    result = create_classification_result(
        origin,
        attribution,
        evidence,
        confidence
    )

    RETURN result
```

## 7.9 Output Contract

The classification result should contain:

- `fact_proposal_id`
- `origin_type`
- `classification_confidence`
- `supporting_evidence`
- `speaker_reference`
- `subject_reference`
- `classification_reason`
- `review_status`
- `classification_version`

Possible origin values:

- `explicit`
- `inferred`
- `unresolved`

## 7.10 Failure Handling

| Failure | Expected behaviour |
|---|---|
| Missing speaker attribution | Require review |
| Ambiguous subject | Require review |
| Weak inference | Do not promote |
| Missing supporting evidence | Reject or mark unresolved |
| Contradictory evidence | Preserve conflict for Phase 6.3 |
| Quoted third-party statement | Preserve original attribution |
| Repeated copied evidence | Avoid treating it as independent corroboration |
| Classification failure | Preserve original proposal and report failure |

## 7.11 Acceptance Criteria

- AC-01: Directly supported statements are classified as explicit.
- AC-02: Derived propositions are classified as inferred.
- AC-03: Unresolved origin remains identifiable.
- AC-04: Speaker attribution is preserved.
- AC-05: Third-party information is not automatically assigned to the user.
- AC-06: Quoted information retains attribution.
- AC-07: Inferences retain supporting evidence.
- AC-08: Weak inferences do not become active memories.
- AC-09: Repetition alone does not promote inferred information.
- AC-10: Hypothetical and conditional statements retain their meaning.
- AC-11: Classification decisions are traceable.
- AC-12: Classification does not directly create active memories.

**Specification status:** COMPLETE.

---

# Algorithm 6.2.6 — Candidate Generation & Validation

**Algorithm ID:** 6.2.6  
**Status:** Specification

## 8. Purpose

This algorithm converts evaluated and classified fact proposals into structured Memory Candidates.

It is the final algorithm in the Memory Ingestion & Extraction pipeline.

Its objective is to ensure that information entering the Memory Resolution stage has:

- A valid structure.
- Correct ownership.
- Supporting evidence.
- Appropriate classification.
- Evaluation metadata.
- Valid lifecycle information.
- Sufficient confidence for further processing.

A Memory Candidate is not an active memory.

It is a validated proposal that can be evaluated by subsequent memory resolution and storage processes.

## 8.1 Responsibilities

- Generate structured memory candidates.
- Map fact proposals to the Memory Engine data model.
- Preserve explicit or inferred origin.
- Attach importance and confidence metadata.
- Attach provenance.
- Preserve temporal and contextual information.
- Validate candidate completeness.
- Validate ownership and access boundaries.
- Identify invalid or incomplete candidates.
- Prevent unsupported candidate promotion.
- Prepare candidates for Phase 6.3.

## 8.2 Input Contract

| Attribute | Purpose |
|---|---|
| `fact_proposal_id` | Extracted fact reference |
| `user_id` | Memory ownership scope |
| `normalized_proposition` | Fact representation |
| `context` | Relevant context |
| `temporal_information` | Temporal information |
| `importance_score` | Importance evaluation |
| `fact_confidence_score` | Fact confidence |
| `extraction_confidence` | Extraction confidence |
| `origin_type` | Explicit, inferred or unresolved |
| `supporting_evidence` | Evidence references |
| `source_reference` | Original source |
| `evaluation_result` | Evaluation outcome |
| `classification_result` | Classification outcome |
| `processing_version` | Pipeline version |

## 8.3 Memory Candidate Structure

The candidate must follow the Memory Engine data model established in Phase 5.4.

Conceptual attributes:

| Attribute | Purpose |
|---|---|
| `candidate_id` | Unique candidate identifier |
| `user_id` | Owning user |
| `proposition` | Candidate memory statement |
| `category` | One or more memory categories |
| `importance` | Importance evaluation |
| `confidence` | Fact confidence |
| `origin_type` | Explicit or inferred |
| `context` | Supporting context |
| `temporal_information` | Valid-time information |
| `source_references` | Original evidence |
| `provenance` | Extraction and evaluation history |
| `extraction_metadata` | Extraction method and version |
| `evaluation_metadata` | Evaluation dimensions |
| `classification_metadata` | Origin classification |
| `status` | Candidate lifecycle state |
| `created_at` | Candidate creation timestamp |
| `updated_at` | Last update timestamp |
| `version` | Candidate version |

These attributes are a logical representation, not a finalized database schema.

## 8.4 Category Assignment

Memory candidates may have multiple categories.

Initial supported categories:

1. Personal Preferences.
2. Goals.
3. Decisions.
4. Important Events.
5. Relationships.
6. Knowledge.
7. Projects.
8. Commitments.

Examples:

| Fact | Possible category |
|---|---|
| "I prefer dark mode." | Personal Preferences |
| "I want to become an AI engineer." | Goals |
| "I decided to use PostgreSQL." | Decisions |
| "I graduated in 2025." | Important Events |
| "My friend works at Company X." | Relationships |
| "I am learning distributed systems." | Knowledge |
| "I am building Raven." | Projects |
| "I have a meeting on Friday." | Commitments |

Multiple categories may apply when justified.

Category assignment must not be based on unsupported assumptions.

## 8.5 Candidate Generation Rules

### Rule 1 — Valid Evaluation Required

A fact proposal must have a valid evaluation result before candidate generation.

### Rule 2 — Valid Classification Required

Origin must be classified as explicit or inferred, or the candidate must remain unresolved and require review.

### Rule 3 — Evidence Required

Every candidate must retain source references or supporting evidence appropriate to its origin.

### Rule 4 — Preserve Original Meaning

Candidate generation may normalize representation but must not alter the proposition.

### Rule 5 — Preserve Context

Relevant context must remain attached.

### Rule 6 — Preserve Temporal Meaning

Past, current, future, recurring and conditional information must remain distinguishable.

### Rule 7 — Preserve Independent Scores

Importance, fact confidence, extraction confidence and inference confidence must not be merged into one value.

### Rule 8 — Do Not Resolve Duplicates Here

Candidate generation must not independently merge candidates or overwrite existing memories.

Duplicate and contradiction resolution belongs to Phase 6.3.

### Rule 9 — Do Not Automatically Activate Candidates

Candidates must remain in the candidate lifecycle until subsequent resolution and promotion policies authorize changes.

## 8.6 Candidate Lifecycle

Conceptual lifecycle:

```text
Fact Proposal
     |
     v
Evaluation
     |
     v
Classification
     |
     v
Candidate Generation
     |
     v
Validation
     |
     +------ Invalid / Rejected
     |
     +------ Needs Review
     |
     v
Validated Candidate
     |
     v
Phase 6.3 — Memory Resolution
     |
     v
Promotion / Update / Merge / Review
```

Candidate states:

- `candidate`
- `validated`
- `needs_review`
- `rejected`
- `superseded`

These are candidate lifecycle states, not the final Atomic Memory lifecycle states.

## 8.7 Validation Rules

### Structural Validation

Check:

- Candidate identifier.
- Proposition.
- Ownership scope.
- Category assignments.
- Origin classification.
- Evaluation metadata.
- Source references.
- Lifecycle status.

### Evidence Validation

Check:

- Evidence references are accessible.
- Source attribution is preserved.
- Supporting text is available where required.
- Inferred candidates have supporting evidence.
- The proposition is supported by the evidence.

### Semantic Validation

Check:

- Proposition preserves original meaning.
- Negation remains correct.
- Modality remains correct.
- Context is not lost.
- Temporal information is consistent.
- Subject attribution is correct.

### Ownership Validation

Check:

- Candidate belongs to the correct user scope.
- No cross-user data is referenced without authorization.
- Private memory is not exposed through shared entities.
- Shared canonical entities do not contain private user memory.

### Evaluation Validation

Check:

- Importance exists where evaluation was completed.
- Fact confidence remains separate.
- Extraction confidence is retained.
- Missing evaluation dimensions are explicitly represented.
- Low-confidence information follows review policy.

## 8.8 Processing Algorithm

**Step 1 — Receive Classified Fact Proposal**

Receive the output of Algorithm 6.2.5.

**Step 2 — Validate Evaluation**

Confirm that the fact has an acceptable evaluation result.

**Step 3 — Validate Classification**

Confirm that origin classification and attribution are valid.

**Step 4 — Map to Memory Candidate**

Convert the proposition into the candidate structure defined by Phase 5.4.

**Step 5 — Assign Categories**

Assign one or more supported categories based on evidence.

**Step 6 — Attach Evaluation Metadata**

Attach importance, confidence, freshness and utility information separately.

**Step 7 — Attach Provenance**

Attach source references, extraction history, classification and evaluation metadata.

**Step 8 — Validate Candidate Structure**

Run structural, semantic, evidence and ownership validation.

**Step 9 — Determine Candidate Status**

Select validated, needs_review or rejected.

**Step 10 — Produce Candidate Output**

Send validated candidates to Phase 6.3.

## 8.9 Pseudocode

```text
FUNCTION generate_memory_candidate(classified_fact):

    validate_evaluation_result(classified_fact)

    validate_classification_result(classified_fact)

    IF classified_fact.evaluation_result == REJECT:
        RETURN REJECTED

    IF classified_fact.origin_type == UNRESOLVED:
        RETURN NEEDS_REVIEW

    candidate = initialize_memory_candidate()

    candidate.proposition = map_proposition(classified_fact)

    candidate.category = assign_memory_categories(classified_fact)

    candidate.importance = classified_fact.importance_score

    candidate.confidence = classified_fact.fact_confidence_score

    candidate.origin_type = classified_fact.origin_type

    candidate.context = preserve_context(classified_fact)

    candidate.temporal_information = preserve_temporal_information(
        classified_fact
    )

    candidate.provenance = attach_provenance(classified_fact)

    candidate.evaluation_metadata = attach_evaluation_metadata(
        classified_fact
    )

    validation = validate_candidate(candidate)

    IF validation == INVALID:
        candidate.status = REJECTED

    ELSE IF validation == AMBIGUOUS:
        candidate.status = NEEDS_REVIEW

    ELSE:
        candidate.status = VALIDATED

    RETURN candidate
```

## 8.10 Failure Handling

| Failure | Expected behaviour |
|---|---|
| Missing proposition | Reject candidate |
| Missing ownership | Reject candidate |
| Missing source evidence | Require review or reject according to policy |
| Invalid category | Re-evaluate category or require review |
| Invalid classification | Require review |
| Low fact confidence | Require review or reject according to policy |
| Invalid provenance | Do not validate candidate |
| Temporal inconsistency | Require review |
| Cross-user ownership violation | Reject |
| Duplicate candidate submission | Reconcile using operation identity |
| Candidate storage failure | Do not report successful persistence |
| Validation timeout | Retry safely or preserve pending state |

## 8.11 Output Contract

The algorithm produces:

- Candidate identifier.
- User ownership scope.
- Proposition.
- Category assignments.
- Importance metadata.
- Fact confidence metadata.
- Origin classification.
- Context.
- Temporal information.
- Source references.
- Provenance.
- Candidate status.
- Processing version.
- Creation timestamp.

Possible overall outcomes:

- `candidate_generated`
- `validated`
- `needs_review`
- `rejected`
- `processing_failed`

## 8.12 Acceptance Criteria

- AC-01: Valid evaluated facts can generate memory candidates.
- AC-02: Origin classification is retained.
- AC-03: Candidate structure follows Phase 5.4.
- AC-04: Multiple categories are supported.
- AC-05: Importance and confidence remain separate.
- AC-06: Extraction confidence is preserved.
- AC-07: Inference evidence is retained.
- AC-08: Source provenance is preserved.
- AC-09: Context and temporal information are preserved.
- AC-10: Negation and modality remain correct.
- AC-11: Ownership validation is enforced.
- AC-12: Invalid candidates are rejected.
- AC-13: Ambiguous candidates can require review.
- AC-14: Duplicate resolution remains outside this algorithm.
- AC-15: Candidate generation does not automatically activate memory.
- AC-16: Validated candidates can be passed to Phase 6.3.

**Specification status:** COMPLETE.

---

# 9. Cross-Algorithm Data Flow

The six algorithms must operate as a connected pipeline.

| Stage | Input | Output | Next stage |
|---|---|---|---|
| 6.2.1 | Raw input | Validated normalized package | 6.2.2 |
| 6.2.2 | Normalized package | Relevance decision | 6.2.3 |
| 6.2.3 | Relevant content | Atomic fact proposals | 6.2.4 |
| 6.2.4 | Fact proposals | Evaluation metadata | 6.2.5 |
| 6.2.5 | Evaluated facts | Origin classification | 6.2.6 |
| 6.2.6 | Classified facts | Validated memory candidates | Phase 6.3 |

## 9.1 Ownership Boundaries

| Responsibility | Owner |
|---|---|
| Raw input validation | Memory Engine |
| Relevance filtering | Memory Engine |
| Fact extraction | Memory Engine |
| Memory evaluation | Memory Engine |
| Origin classification | Memory Engine |
| Candidate generation | Memory Engine |
| Duplicate resolution | Memory Engine — Phase 6.3 |
| Entity resolution | Memory Engine — Phase 6.3 |
| Memory retrieval | Memory Engine — Phase 6.4 |
| Execution coordination | Agent Orchestrator |

The Agent Orchestrator coordinates execution but does not own the Memory Engine's extraction or evaluation logic.

## 9.2 Cross-Algorithm Invariants

1. Original source information remains preserved according to retention policy.
2. Every derived fact retains provenance.
3. Ownership boundaries are enforced.
4. Explicit forgetting bypasses ordinary extraction.
5. Uncertain information remains distinguishable.
6. Inferred information retains supporting evidence.
7. Importance and confidence remain independent.
8. Extraction does not directly create active memories.
9. Candidate generation does not resolve duplicates.
10. Every processing stage produces traceable outcomes.
11. Failed processing must not be reported as successful.
12. Deletion must propagate to derived representations according to Phase 5.10.

---

# 10. Shared Failure and Recovery Requirements

The pipeline must support:

- Bounded retries.
- Idempotent processing.
- Explicit failure states.
- Partial processing results.
- Operation-level traceability.
- Safe cancellation.
- Recovery from temporary infrastructure failures.
- Preservation of successfully completed stages.
- Reconciliation of uncertain operation outcomes.

A downstream failure must not automatically cause completed upstream processing to be repeated unnecessarily.

For example, if candidate generation fails after extraction and evaluation succeed, Raven should be able to resume from the appropriate checkpoint.

Timeouts must not be interpreted as proof that an operation failed.

---

# 11. Security and Privacy Requirements

All six algorithms must follow the security requirements established in the overall architecture.

1. User ownership must be validated.
2. User data must remain isolated.
3. Source content must be treated as untrusted.
4. Uploaded documents must be safely processed.
5. Derived data must retain ownership references.
6. Private content must not be exposed through shared entities.
7. Operational logs must avoid unnecessary raw content.
8. Inferred information must not bypass validation.
9. Forgetting operations must prevent information from being recreated through routine reprocessing.
10. Deletion must propagate to associated candidates, facts, embeddings, indexes and other derived representations.

---

# 12. Performance and Resource Management

Quality remains the primary optimization objective.

The pipeline should nevertheless support:

- Priority processing for important information.
- Asynchronous processing for routine inputs.
- Bounded document processing.
- Controlled concurrency.
- Resource-aware extraction.
- Reuse of valid processing results.
- Safe retry and recovery.
- Avoidance of unnecessary repeated work.

Exact numerical performance targets, score thresholds and resource limits will be established during implementation and Phase 12 evaluation.

---

# 13. Observability and Evaluation

Each algorithm must record sufficient operational information to investigate failures and measure quality.

Common metadata:

- Operation identifier.
- User scope reference.
- Source reference.
- Processing stage.
- Processing version.
- Start and completion timestamps.
- Processing status.
- Failure reason.
- Retry count.
- Relevant evaluation metadata.

## 13.1 Pipeline Evaluation Metrics

| Area | Metrics |
|---|---|
| Ingestion | Validation success, parsing success, duplicate operation rate |
| Relevance | Precision, recall, false rejection rate |
| Extraction | Fact extraction precision, recall, atomicity quality |
| Evaluation | Importance consistency, confidence calibration |
| Classification | Explicit/inferred classification accuracy |
| Candidate generation | Candidate validation success, invalid candidate rate |
| Reliability | Retry success, failure rate, recovery rate |
| Provenance | Evidence coverage, attribution correctness |
| Privacy | Ownership violations, deletion propagation correctness |

Numerical acceptance targets must be defined using representative evaluation datasets during Phase 12.

---

# 14. Phase 6.2 Completion Criteria

Phase 6.2 is considered architecturally specified when all six algorithms have:

- Defined purpose and responsibilities.
- Defined inputs and outputs.
- Documented processing steps.
- Clear ownership boundaries.
- Failure handling.
- Edge-case handling.
- Security and privacy requirements.
- Acceptance criteria.
- Dependencies and downstream relationships.

## 14.1 Algorithm Status

| Algorithm | Specification status |
|---|---|
| 6.2.1 — Input Validation & Normalization | COMPLETE |
| 6.2.2 — Relevance Gate | COMPLETE |
| 6.2.3 — Atomic Fact Extraction | COMPLETE |
| 6.2.4 — Memory Evaluation | COMPLETE |
| 6.2.5 — Explicit & Inferred Classification | COMPLETE |
| 6.2.6 — Candidate Generation & Validation | COMPLETE |

<ins>Important:</ins> COMPLETE here means the algorithm specifications are documented. It does not mean code has been implemented, tests have passed, scoring thresholds have been calibrated or production infrastructure has been configured.

---

# 15. Dependencies

Phase 6.2 depends on:

- Phase 1 — Overall System Architecture.
- Phase 2 — Memory Engine Architecture.
- Phase 5.1 — Overall Data Architecture.
- Phase 5.2 — Data Ownership & Boundaries.
- Phase 5.3 — Core Entities & Relationships.
- Phase 5.4 — Memory Engine Data Models.
- Phase 5.7 — Shared Infrastructure Data Models.
- Phase 5.10 — Retention, Deletion & Migration.
- Phase 6.1 — Shared Algorithm Framework & Scoring System.

---

# 16. Next Phase

**Phase 6.3 — Memory Resolution**

The next phase will define how Raven handles:

- Duplicate memory detection.
- Semantic similarity.
- Entity resolution.
- Alias management.
- Contradiction detection.
- Memory updates and corrections.
- Supersession and historical versions.
- Relationship management.
- Resolution confidence.
- Safe promotion of validated candidates into authoritative memory.

Phase 6.3 must consume the validated candidates produced by Algorithm 6.2.6.

It must not assume that every candidate is new information or that every candidate should become a separate active memory.

---

**Project:** Raven  
**Engine:** Memory Engine  
**Phase:** 6.2 — Memory Ingestion & Extraction  
**Document:** `01-memory-ingestion-extraction.md`  
**Status:** ALL SIX ALGORITHM SPECIFICATIONS COMPLETE

---

<!-- Amendment approved by the project owner on 2026-11-11 (Decision 13 of the Phase 8.2 architecture decision review). Appended; earlier text unchanged. -->

# Amendment — Document parsing ownership (Decision 13)

**Approved 2026-11-11.** Recorded in [7.1 §24.2](../../technical-decisions/01-baseline-technology-stack.md).

Algorithm 6.2.1 §3.2 ("Documents") lists seven steps for document inputs. They are split between two owners, so each uploaded document has one parser and one extracted representation per version:

| 6.2.1 §3.2 step | Owner |
|---|---|
| 1. Validate file type (actual format, not the extension or claimed MIME type) | Ingestion (plan 8.3 §6.1) |
| 2. Validate file integrity (size limits, checksum, approved pre-parse security checks) | Ingestion (plan 8.3 §6.1) |
| 4. Preserve the original document | Ingestion (plan 8.3 §6.2), in object storage (7.1 §24.1) |
| 5. Capture available metadata | Ingestion: upload metadata; the document pipeline: metadata found in the content |
| 3. Extract readable text | **Document pipeline** (Document Intelligence, plan 8.12) |
| 6. Record parsing status | **Document pipeline**: `doc_extracted_representation` and version processing status |
| 7. Prepare normalized content | **Document pipeline** |

Consequences:
- Memory ingestion parses text messages and conversations only. It never parses PDF, DOCX or TXT files, and a document upload creates Document Intelligence records, not a Memory Source.
- Personal Memory reaches document text only through the authorized document-to-memory extraction path. Its authorization model is Decision 6, which is not yet decided, so that path stays disabled until it is approved. Uploading a document never creates memories (Phase 8 Readme §4.2).
- The `document` Memory Source type is used only by that authorized path.
- 6.2.1's text and conversation handling, the `parsing_failed` source status for content that cannot be normalized, and 6.2.1 §3.9 (inspect files before parsing) are unchanged. The pre-parse inspection is done by ingestion, the parsing by the document pipeline.
