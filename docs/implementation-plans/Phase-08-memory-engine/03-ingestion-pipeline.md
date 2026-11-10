# Phase 8.3 — Ingestion Pipeline Implementation Plan

## 1. Objective

Implement the Memory Engine's ingestion pipeline, responsible for accepting incoming information, validating it, normalizing its structure, preserving its source information and preparing it for downstream processing.

The ingestion pipeline is the entry point into the Memory Engine.

It must ensure that incoming information is valid, traceable, correctly associated with its owner and safely registered before extraction begins.

### Primary objectives

- Accept supported input types.
- Validate incoming data and metadata.
- Normalize content into a consistent internal representation.
- Preserve original source information.
- Enforce user ownership and access boundaries.
- Support idempotent ingestion.
- Handle explicit memory instructions appropriately.
- Register accepted inputs for downstream processing.
- Provide reliable processing status and error information.

## 2. Architecture references

Before implementation, Claude Code must review:

1. `PROJECT_ARCHITECTURE.md`
2. `docs/architecture/` — relevant Memory Engine architecture documents.
3. `docs/data-models/` — approved Memory Engine data models.
4. `docs/algorithms/memory/01-memory-ingestion-extraction.md`
5. `docs/technology/01-baseline-technology-stack.md`
6. `docs/technology/02-database-and-storage-architecture.md`
7. `docs/technology/04-background-processing-and-messaging.md`
8. `docs/implementation-plans/phase-08-memory-engine/01-foundation-and-project-setup.md`
9. `docs/implementation-plans/phase-08-memory-engine/02-database-and-persistence.md`

The existing architecture, data models and algorithm specifications are authoritative.

Do not independently introduce new memory entities or redefine existing data models.

## 3. Scope of implementation

### Included

- Ingestion service.
- Input validation.
- Source type validation.
- Content normalization.
- Metadata validation.
- Ownership and authorization checks.
- Original content preservation.
- Ingestion identifiers and idempotency.
- Ingestion status management.
- Error handling.
- Downstream processing handoff.
- Unit and component tests.

### Excluded

The following capabilities belong to subsequent implementation milestones:

- Detailed relevance evaluation.
- Atomic fact extraction.
- Memory importance and confidence scoring.
- Explicit versus inferred memory classification beyond instruction routing.
- Memory candidate generation.
- Entity resolution.
- Duplicate and contradiction resolution.
- Memory embeddings.
- Vector indexing.
- Memory retrieval.
- Consolidation and maintenance.
- Full forgetting and deletion execution.
- Document RAG and semantic document retrieval.

These capabilities must not be prematurely implemented in this milestone.

## 4. Supported input types

The ingestion pipeline should support the input categories defined by the approved architecture.

| Input type | Expected handling |
|---|---|
| Text | Validate and normalize text content |
| User messages | Preserve message content and source metadata |
| Conversation history | Preserve message order, speaker and available timestamps |
| PDF | Validate format and register the source for supported content processing |
| DOCX | Validate format and register the source for supported content processing |
| TXT | Validate format and register the source for supported content processing |

Important:

- Validate actual file content rather than trusting file extensions.
- Reject malformed or unsupported files.
- Preserve original uploaded files.
- Do not assume OCR support for scanned PDFs.
- Do not claim successful text extraction when no supported parser has performed it.
- Detailed document chunking, embeddings and RAG are deferred to the final Phase 8 architecture review.

## 5. Ingestion architecture

Implement the ingestion pipeline using clearly separated responsibilities.

### 5.1 Ingestion Interface

Responsibilities:

- Receive ingestion requests.
- Accept content and metadata.
- Validate basic request structure.
- Pass requests to the ingestion application service.
- Return structured processing information.

The interface must not contain memory extraction or business logic.

### 5.2 Input Validation

Responsibilities:

- Validate required fields.
- Validate supported source types.
- Validate content presence.
- Validate metadata structure.
- Validate schema version.
- Validate file format and integrity.
- Enforce configurable size limits.
- Reject malformed inputs.

Validation must fail safely.

### 5.3 Source Normalization

Responsibilities:

- Normalize text encoding.
- Standardize line endings.
- Remove invalid control characters where appropriate.
- Normalize supported metadata representations.
- Preserve meaningful formatting.
- Preserve original source content separately.

Normalization must not silently change the meaning of the source.

### 5.4 Ownership and Authorization

Responsibilities:

- Verify the authenticated user.
- Validate the ownership of the ingestion request.
- Prevent cross-user access.
- Verify access to referenced content.
- Prevent one user's source from being attached to another user's memory context.

Never trust a user ID supplied only through an untrusted request payload.

### 5.5 Source Persistence

Responsibilities:

- Preserve original source content.
- Register source metadata.
- Associate the source with the correct user.
- Persist content references.
- Record ingestion timestamps.
- Maintain source provenance.

Follow the approved storage architecture:

- PostgreSQL stores structured metadata and references.
- Object storage stores large original content where appropriate.
- Avoid duplicating large files unnecessarily.
- Use checksums where appropriate for integrity verification.

Do not assume PostgreSQL and object storage support a shared atomic transaction.

Use operation tracking and reconciliation where necessary to handle partial failures.

### 5.6 Ingestion Orchestration

Responsibilities:

- Coordinate validation, normalization and persistence.
- Maintain ingestion status.
- Handle idempotency.
- Register accepted inputs for downstream processing.
- Return a consistent result.

This component must not perform detailed extraction or memory resolution.

## 6. Input contract

Use the existing ingestion input model from the algorithm specification.

The logical contract includes:

| Field | Purpose |
|---|---|
| `ingestion_id` | Unique ingestion identifier |
| `user_id` | Owner identity |
| `source_type` | Type of incoming source |
| `source_id` | Original source identifier, when available |
| `content_reference` | Reference to the stored content |
| `received_at` | Time Raven received the input |
| `source_timestamp` | Original source timestamp, when available |
| `content_metadata` | Additional source metadata |
| `priority_hint` | Priority information, where applicable |
| `instruction_type` | Identifies an explicit instruction, when applicable |
| `schema_version` | Input contract version |

Claude Code must reconcile this contract with the approved Pydantic models and Phase 5 data models before implementation.

Do not create duplicate models if an equivalent approved model already exists.

## 7. Ingestion processing workflow

Implement the following logical sequence:

1. Receive the ingestion request.
2. Validate request structure.
3. Authenticate and verify ownership.
4. Identify the source type.
5. Validate the actual content and format.
6. Normalize the content and metadata.
7. Calculate or validate the content checksum where appropriate.
8. Check idempotency.
9. Persist original content or register its existing reference.
10. Persist ingestion metadata.
11. Register the accepted input for downstream processing.
12. Return the ingestion result.

If a step fails, the pipeline must record the appropriate failure state and avoid reporting successful ingestion.

### 7.1 Explicit instructions

Raven must distinguish ordinary information from explicit memory instructions.

**Explicit remember:**

- Preserve the instruction.
- Assign the appropriate priority hint.
- Continue through normal validation.
- Prepare the input for downstream extraction.

**Explicit forget:**

- Recognize the instruction.
- Do not send it through ordinary memory extraction.
- Route it toward the dedicated forgetting workflow.
- Do not execute the full deletion operation in this milestone.

Explicit forgetting must not be blocked by ordinary relevance filtering.

## 8. Idempotency

Repeated ingestion requests must not create unintended duplicate source records.

Implement idempotency using a stable ingestion identifier or an approved idempotency key.

Requirements:

- Repeated requests with the same idempotency identity should resolve to the existing ingestion result where appropriate.
- Do not assume two files are identical solely because their filenames match.
- Use content checksums as an additional integrity or duplicate-detection signal.
- Distinguish a legitimate new source from a retried request.
- Handle concurrent duplicate requests safely.
- Do not silently overwrite previously stored content.

The exact uniqueness constraints must follow the approved data model.

## 9. Ingestion status management

Use the existing approved status definitions wherever available.

The logical status outcomes include:

- `validated`
- `queued`
- `rejected`
- `invalid_input`
- `unsupported_input`
- `access_denied`
- `ownership_validation_failed`
- `parsing_failed`
- `processing_failed`

Do not introduce conflicting status names if the existing data model already defines equivalent states.

Status transitions must be explicit and auditable.

A successfully validated input is not necessarily an extracted or stored memory.

The ingestion result must clearly distinguish source acceptance from downstream memory processing.

## 10. Error handling and recovery

Handle the following scenarios:

| Scenario | Expected behavior |
|---|---|
| Empty input | Reject with validation error |
| Missing required metadata | Reject with validation error |
| Unsupported file type | Reject safely |
| Incorrect file extension | Validate actual content and reject mismatch |
| Corrupted file | Record parsing failure |
| File exceeds configured limit | Reject with clear error |
| Unauthorized user | Deny access |
| Ownership mismatch | Reject without exposing another user's data |
| Duplicate request | Resolve through idempotency |
| Object storage failure | Record failure and reconcile incomplete operations |
| Database failure | Avoid reporting successful persistence |
| Downstream queue unavailable | Preserve accepted state safely and support controlled retry |
| Malformed metadata | Reject with structured validation error |

Retries must be bounded.

Do not create duplicate source records when recovering from partial failures.

## 11. Downstream integration

The ingestion pipeline must prepare accepted inputs for the next milestone.

Its output should include:

- Ingestion identifier.
- Owner reference.
- Source type.
- Content reference.
- Normalized metadata.
- Source timestamp, if available.
- Processing status.
- Schema version.
- Provenance information.

The next processing milestone, Phase 8.4 — Extraction and Evaluation, will consume accepted inputs.

Use a clearly defined internal interface so extraction can be implemented independently.

Where asynchronous processing is required, use the approved messaging architecture and idempotent task handling.

Do not tightly couple ingestion to extraction implementation.

## 12. Logging and observability

Record structured events for:

- Ingestion request received.
- Validation completed.
- Ownership verification completed.
- Source normalization completed.
- Content persistence completed.
- Idempotency match detected.
- Downstream processing registered.
- Ingestion rejected.
- Ingestion failed.

Include relevant identifiers:

- `ingestion_id`
- `user_id` or a safe internal reference
- `source_id`
- `correlation_id`
- `trace_id`

Never log:

- Full private document contents.
- Sensitive personal information unnecessarily.
- Authentication tokens.
- Credentials.
- Secret storage URLs.

## 13. Testing requirements

### Unit tests

Test:

- Input schema validation.
- Supported source type validation.
- Metadata normalization.
- Text normalization.
- Content checksum generation.
- Idempotency key handling.
- Instruction type recognition.
- Status transition validation.

### Component tests

Test:

- Ingestion service.
- Ownership validation.
- Source persistence.
- Storage failure handling.
- Ingestion status management.
- Downstream handoff.

### Security tests

Test:

- Cross-user source access.
- Forged user identifiers.
- Unauthorized content references.
- Invalid file uploads.
- Malformed metadata.
- Sensitive information leakage through logs.

### Reliability tests

Test:

- Repeated ingestion requests.
- Concurrent duplicate requests.
- Database interruption.
- Object storage interruption.
- Partial persistence failure.
- Queue unavailability.
- Recovery and reconciliation behavior.

### Input coverage

Test supported text, messages, conversation history, PDF, DOCX and TXT inputs.

Include malformed files, extension mismatches and unsupported scanned PDFs where OCR is unavailable.

Verify that original content and source metadata remain traceable.

## 14. Acceptance criteria

Phase 8.3 is complete only when:

- [ ] Supported input types are accepted.
- [ ] Invalid inputs are rejected safely.
- [ ] Actual file formats are validated.
- [ ] Content normalization works correctly.
- [ ] Original source content is preserved.
- [ ] Metadata and provenance are persisted.
- [ ] User ownership is enforced.
- [ ] Idempotent ingestion works.
- [ ] Explicit remember instructions are prioritized appropriately.
- [ ] Explicit forget instructions bypass ordinary extraction.
- [ ] Downstream handoff is defined and tested.
- [ ] Failures are handled without false success reporting.
- [ ] Structured logging and observability are implemented.
- [ ] Unit and component tests pass.
- [ ] Security and reliability tests pass.
- [ ] No out-of-scope extraction or retrieval functionality has been introduced.

## 15. Implementation constraints

Claude Code must follow these constraints:

1. Inspect the existing repository before making changes.
2. Reuse the foundation and persistence layers created in earlier milestones.
3. Follow the approved architecture and data models.
4. Do not introduce unnecessary dependencies.
5. Do not duplicate existing functionality.
6. Do not implement generative LLM functionality.
7. Do not implement document RAG in this milestone.
8. Do not create source code inside `docs/implementation-plans/`.
9. Put implementation code inside the existing `memory-engine/` directory.
10. Keep tests inside the existing `tests/` structure.
11. Do not proceed to Phase 8.4 automatically.

If a conflict exists between an implementation instruction and an approved architecture document, report it before making architectural changes.

## 16. Completion report

After implementation, Claude Code must provide:

1. Summary of completed functionality.
2. Files created or modified.
3. Dependencies added or changed.
4. Database or migration changes, if any.
5. Ingestion interfaces and contracts implemented.
6. Tests executed.
7. Exact test results.
8. Known limitations.
9. Deviations from the approved architecture.
10. Acceptance criteria checklist.

Clearly distinguish implemented functionality from deferred functionality.

## 17. Definition of done

The ingestion pipeline is considered complete when Raven can reliably accept, validate, normalize, register and preserve supported incoming sources while maintaining ownership, provenance, idempotency and failure safety.

It must provide a stable handoff to the extraction pipeline without taking responsibility for downstream memory intelligence.

**Phase 8.3 delivers reliable ingestion, not completed memory formation.**
