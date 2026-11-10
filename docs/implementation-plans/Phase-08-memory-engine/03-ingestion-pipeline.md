# 8.3 — Ingestion Pipeline

## 1. Objective

Implement the Memory Engine ingestion pipeline to accept, validate, normalize, and register incoming information.

The pipeline must support two distinct ingestion paths:

1. **Personal memory ingestion:** messages, text, conversation history, and other supported information that may become personal memory.
2. **Document ingestion:** uploaded files that must be registered, validated, preserved, and handed off for document processing.

Both paths share appropriate validation, ownership, security, and operation-management infrastructure. They must not share the same business processing lifecycle.

The ingestion pipeline must preserve source information and establish reliable downstream processing without prematurely extracting memories or processing document chunks.

## 2. Architecture references

Read the following before implementation:

- `PROJECT_ARCHITECTURE.md`
- `docs/architecture/`
- `docs/data-models/`
- `docs/algorithms/`
- `docs/technical-decisions/`
- `docs/technical-decisions/Readme.md`
- `docs/implementation-plans/Phase-08-memory-engine/02-database-and-persistence.md`
- `docs/implementation-plans/Phase-08-memory-engine/04-extraction-and-evaluation.md`
- `docs/implementation-plans/Phase-08-memory-engine/12-document-rag-pipeline.md`

Follow the approved data models and technology decisions. Do not introduce new entities, dependencies, or processing stages without reconciling them with the existing specifications.

## 3. Ingestion architecture

Implement ingestion as a controlled pipeline:

1. Receive the input.
2. Validate the request.
3. Authenticate and verify ownership.
4. Identify the input type.
5. Validate the content and metadata.
6. Preserve the original source or content reference.
7. Register the ingestion operation.
8. Route to the correct downstream workflow.
9. Record the handoff and processing status.
10. Return an accurate acknowledgement.

The pipeline must not report successful downstream processing merely because an input was accepted.

## 4. Supported input types

The ingestion layer must accommodate the following categories, subject to the approved implementation scope.

### 4.1 Personal memory inputs

- Plain text.
- User messages.
- Conversation history.
- Structured text input.
- Explicit remember instructions.
- Explicit forget instructions.

### 4.2 Document inputs

Initial document formats:

- PDF.
- DOCX.
- TXT.

The ingestion layer must validate actual file content and detected format rather than trusting the file extension alone.

Scanned PDFs and image-based documents may require OCR. OCR support must follow an explicit technology decision and must not be assumed to exist in the initial ingestion implementation.

Unsupported formats must receive a clear status and error.

## 5. Personal memory ingestion

### 5.1 Validation

Validate:

- User identity.
- Source type.
- Content presence.
- Content size.
- Required metadata.
- Input encoding.
- Request schema.
- Idempotency key where required.
- Authorization.

Reject malformed or unauthorized requests before processing.

### 5.2 Normalization

Normalize input without changing its original meaning.

Examples:

- Normalize supported text encoding.
- Standardize metadata representation.
- Preserve timestamps and time zones.
- Preserve speaker identity where available.
- Preserve conversation ordering.
- Remove invalid control characters where safe.

Do not discard the original source when normalization creates a modified representation.

### 5.3 Source preservation

Preserve:

- Original content or durable source reference.
- Source type.
- Source identifier.
- User ownership.
- Received timestamp.
- Original source timestamp where available.
- Relevant metadata.
- Normalization metadata.

All downstream memory candidates must be traceable to their originating source.

### 5.4 Explicit instructions

Explicit remember instructions must be prioritized appropriately for downstream extraction.

Explicit forget instructions must bypass normal memory extraction and enter the approved forgetting and deletion workflow.

The ingestion layer must not treat a forget instruction as ordinary content to be stored as a new personal memory without evaluating the instruction.

## 6. Document ingestion

### 6.1 Document registration

When a user uploads a supported document:

1. Authenticate the user.
2. Validate the upload request.
3. Verify the file's actual format.
4. Enforce file-size and upload limits.
5. Validate the detected media type.
6. Calculate a content checksum.
7. Apply the approved security checks.
8. Preserve the original file in approved object storage.
9. Register the document and its version.
10. Create or register the document-processing operation.
11. Hand off processing to the Document Intelligence pipeline.

Document identity and versioning must follow the Phase 5 data models and plan 8.2.

Do not use filenames as document identifiers.

### 6.2 Original document preservation

The original file must remain available as the authoritative source artifact, subject to retention and deletion policies.

Persist its approved metadata and secure object-storage reference.

Do not store extracted text as a replacement for the original file.

Do not expose internal object-storage credentials or unrestricted storage locations.

### 6.3 Document handoff

After successful registration, create a reliable handoff to the Document Intelligence pipeline defined in plan 8.12.

The handoff must include the approved references needed to identify:

- User ownership.
- Document identity.
- Document version.
- Original object reference.
- Processing operation.
- Relevant metadata.
- Schema or contract version.

Use the approved background-processing architecture.

The handoff must be recoverable if message publication or worker execution fails.

### 6.4 Scope boundary

This plan is responsible for document acceptance and registration.

The following operations belong to plan 8.12:

- PDF/DOCX/TXT content parsing.
- OCR, if approved.
- Layout and structural extraction.
- Document chunking.
- Chunk metadata generation.
- Document embedding generation.
- Document indexing.
- Document retrieval.
- Evidence selection.
- Document answer assembly.
- Citation generation and validation.

Do not duplicate these operations in the ingestion pipeline.

## 7. Input contract

Use the approved request and message contracts.

A logical ingestion request may contain:

| Field | Purpose |
|---|---|
| `ingestion_id` | Unique ingestion operation identifier |
| `user_id` | Owner identity |
| `source_type` | Input source category |
| `source_id` | External or originating source identifier, when available |
| `content_reference` | Content or object-storage reference |
| `received_at` | Time Raven received the input |
| `source_timestamp` | Original source timestamp, when available |
| `content_metadata` | Relevant input metadata |
| `priority_hint` | Processing priority where authorized |
| `instruction_type` | Normal, remember, forget, or other approved instruction |
| `schema_version` | Contract version |

This is a logical contract reference, not authorization to introduce an incompatible schema. Reconcile exact field names and required values with existing contracts.

Document-specific metadata must preserve document and version references rather than overloading personal memory fields.

## 8. Idempotency and duplicate handling

The ingestion pipeline must support safe retries.

Requirements:

- Repeated requests with the same idempotency key must not create duplicate operations.
- Content checksums may help detect identical file content.
- A matching checksum must not automatically merge distinct document identities.
- Re-uploading a document must follow the approved document-version policy.
- Failed handoffs must be recoverable.
- Worker retries must not create duplicate document registrations or memory sources.

Idempotency must be scoped to the appropriate user and operation.

Do not treat content similarity as proof that two documents are identical.

## 9. Processing states and error handling

Use the approved lifecycle model where defined.

The ingestion workflow must distinguish at least:

- Received.
- Validating.
- Validated.
- Registered.
- Queued.
- Handed off.
- Rejected.
- Invalid input.
- Unsupported input.
- Access denied.
- Ownership validation failed.
- Storage failed.
- Processing failed.

These are conceptual states. Reconcile exact persisted values with the approved models before implementation.

The system must not label a document as fully processed when only registration and handoff have succeeded.

Failures must preserve enough operation information to support safe retry and diagnosis.

## 10. Security requirements

Implement:

- Authentication.
- User ownership validation.
- File-size limits.
- File-type validation.
- Safe filename handling.
- Storage access control.
- Input validation.
- Protection against path traversal.
- Protection against malicious or malformed files.
- Safe error responses.
- Sensitive-data protection in logs.

Treat document contents as untrusted input.

Do not execute document contents, embedded scripts, or macros.

Any malware scanning or advanced file inspection dependency must follow the approved technology and security decisions.

## 11. Observability

Record relevant events and metrics:

- Ingestion requests.
- Accepted and rejected requests.
- Validation failures.
- Storage failures.
- Duplicate operations.
- Document registration.
- Processing handoff.
- Handoff failures.
- Processing latency.
- Retry counts.

Correlate operations using the approved request, execution, task, message, and trace identifiers.

Do not log full document contents or unnecessary personal information.

## 12. Testing requirements

### 12.1 Personal memory ingestion tests

- Valid text input.
- Invalid request.
- Empty content.
- Invalid encoding.
- Missing metadata.
- Unauthorized request.
- Ownership mismatch.
- Explicit remember instruction.
- Explicit forget instruction.
- Duplicate request.
- Retry after failure.

### 12.2 Document ingestion tests

- Valid PDF.
- Valid DOCX.
- Valid TXT.
- Invalid file content.
- Extension and actual-format mismatch.
- Oversized upload.
- Empty file.
- Malformed document.
- Duplicate upload request.
- Identical file uploaded as a separate document.
- Storage failure.
- Database registration failure.
- Handoff failure.
- Retry after partial completion.
- Cross-user access attempt.

### 12.3 Integration tests

- Successful document registration and handoff.
- Processing operation remains traceable.
- Original file reference remains valid.
- Failed handoff can be recovered.
- No duplicate registration on retry.
- Document processing is not falsely marked complete.
- Personal memory and document ingestion remain separate.

## 13. Acceptance criteria

This plan is complete when:

1. Personal memory inputs are validated and normalized.
2. Original source information is preserved.
3. Explicit remember and forget instructions are routed correctly.
4. Supported document formats are validated.
5. Original documents are securely stored.
6. Document and version records are registered correctly.
7. Processing operations are traceable.
8. Document processing is handed off reliably.
9. Idempotency and retry behavior are tested.
10. Ownership and security checks pass.
11. Failure states are accurately reported.
12. Required tests pass.

## 14. Out of scope

This plan does not implement:

- Detailed memory extraction.
- Memory candidate evaluation.
- Entity resolution.
- Memory duplicate or contradiction resolution.
- Document parsing.
- OCR.
- Document structure extraction.
- Document chunking.
- Embedding generation.
- Vector indexing.
- Hybrid document retrieval.
- Evidence-grounded answer assembly.
- Full deletion orchestration.

These responsibilities belong to their dedicated plans.

## 15. Claude Code execution instructions

Before implementation:

1. Inspect the existing ingestion implementation and repository conventions.
2. Read the referenced architecture and data-model specifications.
3. Identify existing storage, validation, and background-processing infrastructure.
4. Reconcile the document registration and handoff contracts.
5. Report any unresolved schema or security decisions.
6. Propose the minimum required implementation changes.

Do not silently invent new contracts or dependencies.

After implementation, report:

- Files created or modified.
- Input types supported.
- Document registration behavior.
- Storage and handoff implementation.
- Dependencies added.
- Tests executed and results.
- Acceptance criteria satisfied.
- Known limitations.

Do not automatically proceed to plan 8.4.
