# Rule: Coding Standards

Phase 8.1 created the foundation code (`memory-engine/src/memory_engine/`: `config`, `domain`, `exceptions`, `observability`); follow its patterns. These standards come from the approved Phase 7 specifications ([7.1](../../docs/technical-decisions/01-baseline-technology-stack.md), [7.7](../../docs/technical-decisions/07-observability-and-testing-infrastructure.md), [7.8](../../docs/technical-decisions/08-deployment-and-environment-architecture.md)) and the [Phase 8.1 plan](../../docs/implementation-plans/Phase-08-memory-engine/01-foundation-and-project-setup.md). Items marked **pending** are not decided; do not act on them until the user approves them, then update this file. Once code exists, follow its established conventions and record them here.

## Python

- Python 3.12 (**approved**, [7.1 §22](../../docs/technical-decisions/01-baseline-technology-stack.md)). `requires-python` begins at 3.12; develop and test on 3.12.
- Type-annotate all code. mypy in **strict mode** is the only type checker (**approved**); do not add Pyright.
- Ruff for linting and formatting with rules `E, W, F, I, B, UP, SIM, S, N, RUF`, line length 100 (`S101` allowed in tests). Configured in the root `pyproject.toml`; run `uv run ruff check .` and `uv run ruff format --check .` from the repository root.
- Use absolute imports (`from memory_engine.x import y`); the domain boundary test rejects relative imports.
- Keep business logic free of framework and infrastructure imports (see Structure).

## Project structure

- Memory Engine code lives only in `memory-engine/`. Do not modify other engines' directories unless the approved task says so.
- uv workspace (**approved**): the root `pyproject.toml` owns the workspace configuration and contains no application code; `memory-engine/` is a member; one root `uv.lock`. Never create per-member lockfiles. The workspace is not a microservice split.
- Tests live in the repository-root `tests/` (**approved**), organized by engine and test type, for example `tests/memory_engine/unit/`. Never in `memory-engine/tests/`.
- Never place source code in `docs/`.
- Layers: **domain** (concepts, invariants, value objects, domain errors; no FastAPI, database drivers, RabbitMQ, Celery or storage SDKs), **application** (use cases; depends on interfaces), **infrastructure** (database, repositories, storage, messaging, observability adapters), **interfaces** (contracts other components use).
- Create a module only when it has real content. No empty placeholder packages. No abstraction unless it protects ownership, enables testing or isolates replaceable infrastructure.
- Package layout (**approved**, [7.1 §23.1](../../docs/technical-decisions/01-baseline-technology-stack.md)): `memory_engine.personal` and `memory_engine.documents`, each with `domain/` and `application/` and a public `api.py`; shared kernel `memory_engine.domain`; adapters in `memory_engine.infrastructure`; Orchestrator contracts in `memory_engine.interfaces`. Create packages only when they have content.
- Import rules (enforced by tests): domain packages import only the standard library, the shared kernel and `exceptions`; application never imports `infrastructure`; `documents` never imports `personal`; `personal.application` may use `documents.api` only, for authorized document-to-memory extraction; `interfaces` imports only public facades and the shared kernel.
- Persistence (**approved**, 7.1 §23.2–23.4): psycopg 3 with synchronous SQLAlchemy 2.0; one `Session` per unit of work; every repository method takes an `OwnerScope`; every owned table has `owner_id`; tables in the `memory` schema prefixed `pm_`, `doc_` or `me_`; no implicit `ON DELETE CASCADE` on user data; no vector columns, tables or indexes before Phase 8.7 (embedding metadata only until the model is selected, 7.1 §23.5); no outbox table before Phase 8.3 (7.1 §23.6).
- Vocabularies and lifecycle states come only from the Phase 8.2 amendment of [5.4](../../docs/data-models/phase-05-memory-engine-models.md); do not invent new relationship types or states. They live in `memory_engine.domain.vocabulary`.
- Established in 8.2 step 1 (follow these patterns):
  - Domain records are `@dataclass(frozen=True, slots=True, kw_only=True)` with invariants in `__post_init__`; JSON fields are copied into read-only mappings.
  - Repositories return domain records, never ORM rows, and wrap database calls in `translate_database_errors("<fixed operation name>")`. Another owner's record behaves like a missing one (`None` or `RecordNotFoundError`).
  - Child tables reference parents through composite `(id, owner_id)` foreign keys. Append-only tables get the `pm_reject_update` trigger.
  - Migrations freeze vocabularies as literals (a unit test checks them against the enums) and name constraints with `op.f(...)`; otherwise Alembic applies the naming convention twice.
  - Integration tests are marked `integration`, use the `connection`/`uow_factory`/`doc_uow_factory` fixtures (rolled back per test) and synthetic data only.
- Established in 8.2 step 2:
  - Status-only updates use the `me_guard_columns(<mutable columns>)` trigger; with no arguments a table is append-only. List new mutable columns in the migration's `GUARDED_TABLES`; a unit test checks that they exist.
  - In check constraints, compare possibly-NULL columns with `IS NOT DISTINCT FROM`, never `=`: PostgreSQL treats a NULL check result as passing. The reverse also bites: `a IS DISTINCT FROM b` is *false* when both are NULL, so guard "must differ" rules with `a IS NULL OR …` (step 3). Test both the NULL/NULL and the NULL/value cases.
  - Status changes go through a conditional `UPDATE … WHERE status = <expected>` (`conditional_update` in `database.py`), which distinguishes "not found" from a concurrency conflict.
  - History that must keep insertion order within one transaction needs its own sequence (`seq`, an identity column): `now()` is the same for every row in a transaction (step 3).
  - Writers of derived document content call `require_writable_version` first, so nothing is recreated once deletion is requested.
  - Mutually referencing rows (a profile and its current revision) use a deferrable foreign key. `SET CONSTRAINTS … IMMEDIATE` lasts for the rest of the transaction, so every such write runs `SET CONSTRAINTS ALL DEFERRED` first and `SET CONSTRAINTS ALL IMMEDIATE` at its end, to fail inside the operation rather than at commit (step 4).
  - To store SQL `NULL` in a JSON/JSONB column, write `sqlalchemy.null()`: Python `None` is stored as the JSON value `null`, which passes `IS NOT NULL` (step 5).
  - Two foreign keys whose first column is the same (for example two revision keys starting with `memory_id`) need explicit names; the naming convention uses only the first column and would give both the same name (step 5).
  - A repository method that replaces content (not just a status) is conditional on a version or revision number, never on the status alone; otherwise two writers that read the same state both succeed (acceptance review A1).
  - Conflict tests on the shared rolled-back connection are sequential. To test a real race, use separate connections from `engine` and remove the committed rows afterwards (`test_concurrency_and_failures.py`).
  - Only `pm_document_evidence_ref` may reference `doc_` tables; `documents/` and its infrastructure never import Personal Memory code (tested).
- Established in 8.3 step 1 (object storage):
  - Application code uses the `ObjectStorage` port from `memory_engine.domain.object_storage`; only `memory_engine.infrastructure.object_storage` imports boto3. Unit tests use `InMemoryObjectStorage`.
  - Object keys are opaque and owner-partitioned (`<area>/<owner_id>/…`, never a filename). Every port call takes the `OwnerScope` and refuses a key of another owner before any I/O.
  - Compute the SHA-256 and size before storing and pass them to `put`; the adapter verifies both and deletes a mismatched object. Never report content as stored when `put` raised.
- Established in 8.3 step 2 (ingestion):
  - Order of work: validate, check the idempotency key, upload to object storage, then write the database record. If the record fails, delete the uploads (best effort) and look the key up again, since a concurrent request may have won.
  - An idempotency key always comes with a fingerprint of the request (excluding receipt time). The same key with a different fingerprint raises `IdempotencyKeyReusedError`; never overwrite.
  - Rejections raise `IngestionRejectedError` with `details["outcome"]` and an UPPER_SNAKE_CASE `details["reason"]`; error messages never contain the input.
- Established in 8.3 step 3 (document ingestion):
  - The content decides a file's format; extensions and declared types are only cross-checked. Never parse, unzip or render a document during ingestion. DOCX is checked from its ZIP listing only.
  - Filenames are display names only (`safe_filename`); never build a key or path from them.
- Established in 8.3 step 4 (reliable handoff):
  - A handoff is an `OutboxMessage` added through the unit of work's `outbox`, in the same transaction as the record it hands off. Never publish to the broker from an application service.
  - Envelopes carry identifiers and object keys only, never content; the contract is `memory_engine.domain.handoff` (schema version "1"). Consumers validate with `HandoffEnvelope.from_dict` and deduplicate on the message id: delivery is at least once.
  - A record moves to `queued` only in the relay's transaction after the broker confirmed. Forget instructions never get a handoff to extraction.
  - Only `memory_engine.infrastructure.messaging` imports celery, kombu or amqp (tested). Celery never retries a publish; the outbox does.
- Established in 8.4 step 1 (extraction worker):
  - A worker validates the envelope with `HandoffEnvelope.from_dict` and refuses invalid messages without side effects. It decides from the subject's state (`queued`), never from the message, so duplicates are harmless.
  - Pipeline outcomes are written atomically with their candidates, in one unit of work, conditional on the expected source state. Transient infrastructure errors (`TRANSIENT_ERRORS`) propagate for the Celery retry; every other failure becomes a final state with an error code.
  - Transitions into `deferred` or `rejected` carry a `reason_code`; only failures carry an `error_code`.
  - Quality datasets are versioned JSON Lines under `tests/memory_engine/quality/data/` and are never edited once a result depends on them: add a new version instead.
- Established in 8.4 step 2 (relevance gate):
  - NLP goes through the `SentenceAnalyzer` port (`personal/application/analysis.py`); only `memory_engine.infrastructure.nlp` imports spaCy (tested). Analyzer output is a signal for deterministic rules, never a decision.
  - Scores combine only the signals that were evaluated, renormalizing the weights; a missing signal is never zero (6.2.2 AC-07). Weights and thresholds live in settings and are marked uncalibrated until step 6.
  - Stored decisions keep positions, outcomes, codes and scores, never the text.
  - Quality datasets are labelled by intent, not by the current output; quality tests assert exact matches for rule-decided cases and an accuracy floor overall.
- Established in 8.4 step 3 (fact extraction):
  - Pipeline stages hand each other in-memory records through ports (`ExtractionStage`, `ProposalStage`); only the final outcome is persisted, atomically. Fact proposals are never stored on their own.
  - Rewrite only first-person references ("the user"); keep third-person pronouns as written and send the proposal to review. Never resolve a relative date to an absolute one.
  - A failure on one sentence is recorded and never discards the others; an empty result is a valid outcome, distinct from a failure.
  - If a dataset's labels were written after looking at the output, say so: it is a regression set, not a quality measure.
- Established in 8.3 step 5 (observability):
  - Record metrics only through the `Metrics` port (`memory_engine.observability.metrics`), injected with a no-op default; tests use `InMemoryMetrics`. Labels are limited to `input`, `outcome`, `reason` and `kind`, with word or code values: identifiers belong in logs, never in labels.
  - Log events set `event_type` (`<area>.<outcome>`) and carry ids, codes and durations, plus `user_scope` (the opaque owner id); never content, filenames or caller-supplied keys.
  - Telemetry must never change an operation's outcome (`observe_ingestion` reports a telemetry failure and keeps the original result or error).

## Naming

- Follow PEP 8: `snake_case` modules, functions and variables; `PascalCase` classes; `UPPER_SNAKE_CASE` constants.
- Use the domain vocabulary from the Phase 5 data models (for example memory source, memory candidate, atomic memory, document version, document chunk). Do not invent synonyms for defined concepts.
- Exception class names end in `Error`. *(Raven engineering convention, not a source-document requirement.)*

## Error handling

- Meaningful exception types, with domain errors separate from infrastructure errors.
- Preserve the original cause (`raise ... from err`). Never swallow exceptions.
- Never return stack traces or internal details to callers or users.
- Never report an operation as successful before its required persistence is confirmed. Distinguish accepted asynchronous work from completed work.
- API error categories follow [7.6 §13](../../docs/technical-decisions/06-api-security-and-internal-communication.md): `INVALID_REQUEST`, `UNAUTHENTICATED`, `FORBIDDEN`, `RESOURCE_NOT_FOUND`, `RATE_LIMITED`, `CONFLICT`, `REQUEST_TIMEOUT`, `SERVICE_UNAVAILABLE`, `INTERNAL_ERROR`.
- Mapping errors to these API categories belongs at the interface layer, not in the domain. *(Raven engineering convention, not a source-document requirement.)*

## Logging

- Python standard `logging` with structured output (7.7 §3). Do not add a logging framework without approval.
- Conceptual fields (7.7 §6.1): timestamp, level, service/component, environment, event type, message, request/execution/task/trace IDs, non-sensitive user scope, duration, error code.
- Never log secrets, tokens, credentials, full request bodies, raw personal-memory content or document text. See [security and privacy](security-and-privacy.md).

## Configuration

- Pydantic Settings (`pydantic-settings`, **approved**) for validated, environment-based configuration; fail at startup on missing or invalid mandatory configuration.
- Environment-specific values stay out of code. Environments: development, testing, staging, production.
- Secrets are separate from ordinary configuration. `.env` is git-ignored; `.env.example` holds placeholders only.

## Dependencies

- uv manages environments; `pyproject.toml` is the central configuration; dependencies are pinned and locked reproducibly; runtime and development dependencies are separated.
- Add a dependency only in the subphase that needs it, with a stated reason and a check for an existing solution. Review licence and maintenance status.
- Approved timing ([7.1 §22.1](../../docs/technical-decisions/01-baseline-technology-stack.md)): 8.1 adds `pydantic`, `pydantic-settings` and, for development, `pytest`, `pytest-cov`, `ruff`, `mypy`. SQLAlchemy, Alembic and the PostgreSQL driver wait for 8.2. HTTPX and OpenTelemetry are added only when required.
- Never add generative LLM libraries. Proposed parsers (pypdf, python-docx) need evaluation and approval first. See [`TECHNOLOGY_DECISIONS.md`](../../docs/project-context/TECHNOLOGY_DECISIONS.md).

## Testing

- pytest; pytest-cov for coverage reporting (no threshold until one is approved); HTTPX only where HTTP/API testing is required.
- Layers (7.7 §10): unit, component, integration, end-to-end, quality/evaluation, reliability/security.
- Tests are repeatable, use synthetic data, never touch production data, and make no network calls in unit tests. Integration tests use isolated real infrastructure; do not mock away every meaningful integration.
- Test behavior and invariants (duplicates, contradictions, isolation, deletion propagation, provenance), not just imports or successful responses.
- Coverage alone never proves correctness.

## Documentation and quality

- Each package's README covers its responsibilities, boundaries, setup and test commands, and links to the architecture docs instead of duplicating them.
- Quality gates before acceptance: format/lint, type check, unit tests, relevant component and integration tests, plus migration validation when the schema changes.
- Keep docstrings and comments for intent and invariants, not restatements of code.
