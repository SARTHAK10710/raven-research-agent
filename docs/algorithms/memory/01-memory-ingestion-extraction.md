# Raven — Memory Input Validation & Normalization

**Algorithm ID:** 6.2.1  
**File:** `01-memory-ingestion-extraction.md`  
**Directory:** `docs/algorithms/memory/`  
**Phase:** 6.2 — Memory Ingestion & Extraction  
**Status:** Algorithm Specification

---

# 1. Purpose

This algorithm defines how Raven receives, validates, normalizes and prepares incoming information for memory processing.

It establishes the entry point of the Memory Engine ingestion pipeline.

Raven must support three initial input categories:

1. Text and user messages.
2. Conversation history.
3. Documents: PDF, DOCX and TXT.

The ingestion architecture follows a hybrid processing approach:

- Important inputs receive priority.
- Routine inputs are processed asynchronously.
- Explicit memory instructions receive appropriate priority.
- Explicit forgetting requests bypass normal ingestion and are routed to the deletion workflow.

The objective is to ensure that every accepted input is properly validated, traceable, securely handled and prepared for downstream processing.

---

# 2. Scope and Responsibilities

## 2.1 Responsibilities

This algorithm is responsible for:

- Input type identification.
- Input validation.
- User and ownership verification.
- Source metadata validation.
- Content integrity checks.
- Text normalization.
- Document content extraction at the parsing level.
- Conversation structure preservation.
- Processing priority assignment.
- Synchronous or asynchronous routing.
- Duplicate ingestion protection.
- Input processing status tracking.
- Error handling.

## 2.2 Out of Scope

The following operations belong to subsequent algorithms:

| Operation | Responsible algorithm |
|---|---|
| Relevance evaluation | 6.2.2 — Relevance Gate |
| Atomic fact extraction | 6.2.3 — Atomic Fact Extraction |
| Importance evaluation | 6.2.4 — Memory Evaluation |
| Explicit versus inferred classification | 6.2.5 — Memory Classification |
| Candidate generation | 6.2.6 — Candidate Generation & Validation |
| Duplicate memory detection | 6.3 — Memory Resolution |
| Entity resolution | 6.3 — Memory Resolution |
| Memory retrieval | 6.4 — Memory Retrieval |

Ingestion must not automatically create an active memory.

---

# 3. Supported Input Types

## 3.1 Text and User Messages

Examples:

- Direct user statements.
- Explicit memory instructions.
- Preferences.
- Goals.
- Decisions.
- Important events.
- Knowledge shared by the user.

The system must preserve the original message content.

Text normalization must not rewrite the user's meaning.

## 3.2 Conversation History

Conversation inputs may contain multiple messages.

The ingestion process must preserve:

- Conversation identifier, where available.
- Message identifiers, where available.
- Speaker or role.
- Original message order.
- Message timestamps, where available.
- Original message content.
- Relevant source references.

Conversation messages must not be flattened into one undifferentiated text block.

Speaker identity and message boundaries are important because the same statement can have different meanings depending on who said it.

For example, a statement made by the user must not automatically be treated as a personal fact when it was actually quoted from another person.

## 3.3 Documents

Initially supported formats:

- PDF
- DOCX
- TXT

The document ingestion process must:

1. Validate the file type.
2. Validate file integrity.
3. Extract readable text.
4. Preserve the original document.
5. Capture available document metadata.
6. Record parsing status.
7. Prepare normalized text for downstream processing.

The original document must remain distinguishable from its extracted text.

A parsing failure must not be treated as an empty document.

Scanned PDFs that require OCR must be handled through a separately defined document-processing capability. OCR must not be assumed to exist merely because PDF support is enabled.

---

# 4. Input Data Contract

Every incoming input should be represented through a common conceptual ingestion envelope.

## 4.1 Input Attributes

| Attribute | Purpose |
|---|---|
| `ingestion_id` | Unique identifier for the ingestion operation |
| `user_id` | Identifies the owning user |
| `source_type` | Text, conversation or document |
| `source_id` | Original source identifier, where available |
| `content_reference` | Reference to original stored content |
| `received_at` | Time Raven received the input |
| `source_timestamp` | Original source timestamp, where available |
| `content_metadata` | Source-specific metadata |
| `priority_hint` | Initial priority information |
| `instruction_type` | Normal, explicit remember or explicit forget, where identifiable |
| `schema_version` | Version of the ingestion contract |

These attributes describe the logical contract, not a finalized database schema.

## 4.2 Source Metadata

Source-specific metadata must be preserved.

Examples:

**Text:**
- Message identifier.
- Input timestamp.
- Source channel, where available.

**Conversation:**
- Conversation identifier.
- Message identifier.
- Speaker.
- Message order.
- Timestamp.

**Document:**
- Original filename.
- File format.
- File size.
- Content type.
- Document metadata, where available.

Missing optional metadata must not automatically cause rejection.

---

# 5. Preconditions

Before processing an input, Raven must establish:

1. The input belongs to a supported input category.
2. The requesting user or originating system is authenticated.
3. The user is authorized to submit the input.
4. The input has a valid ownership scope.
5. The input satisfies configured size and format constraints.
6. The original content can be safely accessed.
7. The ingestion operation has a valid identifier or can be assigned one.

If mandatory conditions are not satisfied, processing must stop with an explicit failure reason.

---

# 6. Processing Algorithm

## Step 1 — Receive Input

Receive an input through the authorized ingestion interface.

Capture:

- Original content or file reference.
- Source type.
- User context.
- Available metadata.
- Receipt timestamp.
- Relevant instruction information.

Do not perform memory extraction at this stage.

## Step 2 — Identify Input Type

Determine whether the input is:

- Text.
- Conversation history.
- Document.

For documents, identify the actual file format using content inspection where possible rather than trusting only the filename extension.

Unsupported input types must be rejected with a clear reason.

## Step 3 — Validate User and Ownership

Validate the user identity and authorization.

Confirm that the source is permitted to be associated with the requested user scope.

Never assume that missing ownership metadata makes information public.

Cross-user data access must be rejected unless explicitly authorized by the relevant access policy.

## Step 4 — Validate Input Integrity

Perform the appropriate checks.

**Text:**
- Check for valid content.
- Validate encoding.
- Detect empty or malformed input.

**Conversation:**
- Validate message structure.
- Check speaker and message boundaries.
- Validate available identifiers and timestamps.
- Preserve message ordering.

**Documents:**
- Validate file integrity.
- Check actual file format.
- Enforce configured file-size limits.
- Detect unsupported or corrupted documents.
- Apply appropriate security inspection before parsing.

Potentially malicious or malformed files must not be passed directly into downstream processing.

## Step 5 — Preserve Original Input

The original input must be retained separately from its normalized representation according to the applicable retention policy.

For documents:

- Preserve the original file.
- Store extracted text separately.
- Retain the relationship between the file and extracted content.

For conversations:

- Preserve original message boundaries.
- Retain original message order and speaker information.

For text:

- Preserve the original text independently of normalized text.

The original input is the reference for provenance and future reprocessing.

## Step 6 — Normalize Content

Prepare a normalized representation for downstream processing.

Normalization may include:

- Unicode normalization.
- Line-ending standardization.
- Removal of unnecessary formatting artifacts.
- Consistent whitespace handling.
- Text encoding normalization.
- Document text extraction.
- Preservation of paragraph and section boundaries where possible.

Normalization must not:

- Change the semantic meaning.
- Rewrite user statements.
- Remove meaningful punctuation.
- Remove negations.
- Convert uncertain statements into certain statements.
- Remove important timestamps.
- Merge different speakers into one identity.
- Discard meaningful document structure.

Where practical, maintain a mapping between normalized content and its original source locations.

This supports provenance and error investigation.

## Step 7 — Handle Source-Specific Processing

### Text

Create a normalized text representation while preserving the original message.

### Conversation History

Normalize messages individually.

Preserve:

- Speaker.
- Message order.
- Timestamp.
- Conversation relationship.

Do not combine different speakers' statements into a single user statement.

### Documents

Extract readable content using an appropriate parser.

Preserve:

- Document identity.
- Available page or section references.
- Text boundaries.
- Extraction status.

If parsing is incomplete, record the limitation.

Do not silently present partial extraction as complete extraction.

## Step 8 — Identify Instruction Type

Identify whether the incoming input contains an explicit instruction relevant to memory handling.

Conceptual categories:

- Normal input.
- Explicit remember instruction.
- Explicit forget instruction.

An explicit remember instruction indicates that the user wants the information prioritized for memory processing. It does not bypass validation, ownership, relevance or candidate evaluation.

An explicit forget instruction must be routed to the Memory Engine's forgetting and deletion workflow.

**Important:** Forgetting must not enter the normal extraction pipeline where the information could accidentally be recreated.

## Step 9 — Assign Processing Priority

Assign an initial processing priority using deterministic rules.

Priority may consider:

- Explicit user instruction.
- Explicit remember request.
- User-designated importance.
- Source type.
- Operational urgency.
- Existing processing requirements.

The initial priority is an ingestion scheduling signal.

It is not the same as the final memory importance score.

Memory importance is evaluated later by Algorithm 6.2.4.

## Step 10 — Select Processing Mode

Use the hybrid ingestion model.

**Priority synchronous processing:**

Inputs requiring immediate handling may enter the synchronous processing path.

Examples:

- Explicit memory instructions.
- Important user-designated information.
- Small inputs requiring immediate acknowledgement or processing.

**Asynchronous processing:**

Routine inputs may be queued for background processing.

Examples:

- Routine conversation history.
- Large documents.
- Bulk ingestion.
- Non-urgent source processing.

The system must be able to acknowledge receipt without falsely claiming that memory extraction or persistence has completed.

Exact priority thresholds and scheduling policies will be finalized during implementation and evaluation.

## Step 11 — Prevent Duplicate Ingestion

Before creating a new ingestion operation, check whether the same logical input has already been accepted or processed.

Use available identifiers and source metadata.

Where suitable, a content fingerprint may help identify repeated submissions.

However:

- Identical content does not always mean identical source events.
- Two separate conversations may legitimately contain the same statement.
- Duplicate ingestion detection must not delete or merge original source records.
- Memory-level duplicate detection remains the responsibility of Phase 6.3.

If an operation is already in progress, the system should reconcile with the existing operation rather than create an unintended duplicate.

## Step 12 — Generate Normalized Input Package

After successful validation and normalization, prepare a normalized input package.

It must contain:

- Ingestion identifier.
- User and ownership scope.
- Source type.
- Original content reference.
- Normalized content reference.
- Source metadata.
- Relevant timestamps.
- Instruction classification.
- Processing priority.
- Processing mode.
- Validation result.
- Parsing result, where applicable.

This package becomes the input for Algorithm 6.2.2 — Relevance Gate.

---

# 7. Pseudocode

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

    IF source_type == TEXT:
        normalized = normalize_text(input)

    ELSE IF source_type == CONVERSATION:
        normalized = normalize_conversation(input)

    ELSE IF source_type == DOCUMENT:
        normalized = extract_and_normalize_document(input)

    IF normalized.status == FAILED:
        RETURN PARSING_FAILED

    instruction = classify_memory_instruction(normalized)

    IF instruction == EXPLICIT_FORGET:
        RETURN route_to_forgetting_workflow(input)

    priority = assign_initial_priority(
        normalized,
        instruction
    )

    existing = check_existing_ingestion(input)

    IF existing IS ALREADY_PROCESSING:
        RETURN existing.ingestion_reference

    IF existing IS ALREADY_COMPLETED:
        RETURN reconcile_existing_ingestion(existing)

    package = create_normalized_input_package(
        original_reference,
        normalized,
        metadata,
        priority,
        instruction
    )

    IF priority_requires_immediate_processing:
        RETURN submit_to_synchronous_pipeline(package)

    ELSE:
        RETURN enqueue_for_async_processing(package)
```

This pseudocode defines the logical workflow. Actual interfaces and implementation details will be established later.

---

# 8. Output Contract

The algorithm must return an explicit processing result.

## 8.1 Successful Validation

Expected output:

- Ingestion identifier.
- Source reference.
- Normalized content reference.
- Validation status.
- Parsing status.
- Processing priority.
- Processing mode.
- Next processing stage.

Possible status:

`validated`

## 8.2 Asynchronous Submission

Expected output:

- Ingestion identifier.
- Queue or operation reference.
- Accepted timestamp.
- Processing status.

Possible status:

`queued`

Queued does not mean successfully extracted or stored as memory.

## 8.3 Failed Validation

Possible outcomes:

- `rejected`
- `invalid_input`
- `unsupported_input`
- `access_denied`
- `ownership_validation_failed`
- `parsing_failed`
- `processing_failed`

These are conceptual ingestion outcomes. Exact persisted status enums must remain consistent with the final implementation contract.

## 8.4 Explicit Forgetting

An explicit forgetting instruction is routed to the deletion workflow.

The result must identify the deletion operation or its status.

It must not create a new memory candidate from the information being forgotten.

---

# 9. Failure Handling

| Failure | Expected behaviour |
|---|---|
| Invalid user context | Reject the operation |
| Unauthorized input | Reject without exposing private data |
| Unsupported format | Return explicit unsupported-input status |
| Corrupted document | Mark parsing failure |
| Empty content | Reject or mark empty according to source policy |
| Partial document extraction | Preserve partial status and source references |
| Encoding error | Attempt safe supported normalization or reject |
| Duplicate submission | Reconcile with existing ingestion |
| Queue unavailable | Retry safely or retain recoverable pending state |
| Storage failure | Do not report successful preservation |
| Parser failure | Record failure and permit safe retry where appropriate |
| Cancellation | Stop eligible processing and preserve operation state |

A timeout must not automatically be treated as proof that an operation failed.

Before retrying an operation with an uncertain outcome, Raven must reconcile using the ingestion identifier.

---

# 10. Edge Cases

The following cases must be addressed during implementation.

### 10.1 Repeated User Messages

The same message may be submitted more than once.

Raven must prevent unintended duplicate ingestion while preserving legitimate separate source events.

### 10.2 Multiple Speakers

A conversation may contain statements from the user and other participants.

Statements must retain their original speaker attribution.

Information about another person must not automatically become a personal fact about the user.

### 10.3 Quoted Information

A user may quote another person's statement.

Quoted text must remain distinguishable from the user's own claims.

### 10.4 Contradictory Statements

An input may contradict existing information.

The ingestion algorithm must preserve the new source and allow Phase 6.3 to evaluate the conflict.

It must not overwrite an existing memory.

### 10.5 Empty Documents

A document may be valid but contain no extractable text.

This must be distinguished from a successfully extracted empty document.

### 10.6 Scanned PDFs

A scanned PDF may contain images without an embedded text layer.

It must be marked as requiring OCR or another supported processing method.

### 10.7 Very Large Documents

Large documents must respect configured resource limits.

Where supported, document parsing may be performed in bounded sections while preserving page and section references.

### 10.8 Partial Conversation History

Conversation imports may lack timestamps, identifiers or some messages.

Missing metadata must be explicitly represented rather than invented.

### 10.9 Sensitive Content

Sensitive content must follow applicable privacy and access policies.

Raw content must not be unnecessarily exposed through operational logs.

### 10.10 Explicit Forgetting

A forgetting instruction must bypass ordinary extraction and enter the deletion workflow.

The system must not recreate forgotten information through routine reprocessing.

---

# 11. Security and Privacy Requirements

1. Authenticate the originating user or authorized system.
2. Validate ownership before accepting private data.
3. Apply user isolation throughout ingestion.
4. Treat uploaded documents as untrusted input.
5. Validate file content before parsing.
6. Prevent unsafe file processing.
7. Restrict access to original and normalized content.
8. Avoid logging raw sensitive information unnecessarily.
9. Apply configured retention policies to original content.
10. Ensure deletion requests propagate to relevant stored representations.

The ingestion pipeline must not bypass Shared Infrastructure authorization policies or Memory Engine ownership rules.

---

# 12. Performance and Resource Considerations

Quality takes priority over speed and cost.

However, ingestion must remain resource-aware.

Considerations include:

- Input size.
- Document parsing complexity.
- Conversation length.
- Memory consumption.
- Processing time.
- Queue capacity.
- Concurrent ingestion operations.
- Retry limits.
- Storage requirements.

Large inputs should use bounded processing where appropriate.

Priority scheduling must not allow unlimited resource consumption.

Exact limits will be configurable and evaluated during implementation.

---

# 13. Observability

Every ingestion operation should be traceable.

Record relevant operational metadata:

- Ingestion identifier.
- User scope reference.
- Source type.
- Processing start and completion timestamps.
- Validation outcome.
- Parsing outcome.
- Processing mode.
- Current status.
- Failure reason.
- Retry count, where applicable.
- Relevant processing version.

Operational logs must not expose unnecessary raw content or secrets.

---

# 14. Acceptance Criteria

Algorithm 6.2.1 is considered implementation-ready when the following behaviours are specified and can be tested.

| ID | Acceptance criterion |
|---|---|
| AC-01 | Valid text input is accepted and normalized |
| AC-02 | Valid conversation input preserves speaker and message ordering |
| AC-03 | Supported PDF, DOCX and TXT documents can be validated |
| AC-04 | Unsupported document formats are rejected |
| AC-05 | Original source information remains distinguishable from normalized content |
| AC-06 | Invalid user authorization prevents ingestion |
| AC-07 | Cross-user ownership violations are rejected |
| AC-08 | Explicit remember instructions receive appropriate priority |
| AC-09 | Explicit forget instructions bypass normal extraction |
| AC-10 | Routine inputs can enter asynchronous processing |
| AC-11 | Important inputs can enter the priority processing path |
| AC-12 | Duplicate submissions do not create unintended duplicate operations |
| AC-13 | Partial document extraction is explicitly represented |
| AC-14 | Parsing and storage failures are traceable |
| AC-15 | Normalization preserves the original meaning and source attribution |
| AC-16 | Successful ingestion does not automatically create an active memory |

---

# 15. Dependencies

This algorithm depends on:

- Phase 1 — Overall System Architecture.
- Phase 2 — Memory Engine Architecture.
- Phase 5.1 — Overall Data Architecture.
- Phase 5.2 — Data Ownership & Boundaries.
- Phase 5.3 — Core Entities & Relationships.
- Phase 5.4 — Memory Engine Data Models.
- Phase 5.7 — Shared Infrastructure Data Models.
- Phase 5.10 — Retention, Deletion & Migration.
- Phase 6.1 — Shared Algorithm Framework & Scoring System.

It produces normalized input packages for:

**Algorithm 6.2.2 — Relevance Gate.**

---

# 16. Completion Status

**Algorithm:** 6.2.1 — Input Validation & Normalization

**Specification status:** COMPLETE

This means the logical algorithm, inputs, outputs, processing rules, failure cases and acceptance criteria have been documented.

It does not mean implementation, testing, parser selection or infrastructure configuration has been completed.

---

# 17. Next Algorithm

**Algorithm 6.2.2 — Relevance Gate**

The next algorithm will determine:

- Whether incoming information is worth further memory processing.
- Which features indicate potential memory value.
- How relevance is evaluated.
- How important information is protected from premature filtering.
- When information should be rejected, deferred or passed to extraction.
- How quality and resource costs are balanced.

The Relevance Gate must follow the hybrid and quality-first principles established in Phase 6.1.

---

**Project:** Raven  
**Engine:** Memory Engine  
**Phase:** 6.2 — Memory Ingestion & Extraction  
**Algorithm:** 6.2.1 — Input Validation & Normalization
