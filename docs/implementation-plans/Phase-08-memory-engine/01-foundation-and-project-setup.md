# Phase 8.1 — Foundation & Project Setup

## 1. Objective

Establish the foundational project structure and development environment for Raven's Memory Engine.

This milestone prepares the Memory Engine for subsequent implementation of ingestion, extraction, entity management, memory resolution, storage, retrieval, consolidation, and deletion.

The objective is not to implement memory functionality yet.

The objective is to create a clean, modular, testable, and maintainable foundation that follows Raven's approved architecture.

**Implementation location:**

`memory-engine/`

**Implementation plan location:**

`docs/implementation-plans/Phase-08-memory-engine/01-foundation-and-project-setup.md`

---

## 2. Architecture References

Claude Code must read and follow the relevant approved documents before implementation.

### Architecture

- `docs/architecture/`
- Memory Engine architecture specifications.

### Data Models

- `docs/data-models/`
- Memory Engine entity and relationship specifications.
- Data ownership and lifecycle specifications.

### Algorithms

- `docs/algorithms/shared/01-shared-algorithm-framework.md`
- `docs/algorithms/memory/`

### Technology

- `docs/technical-decisions/01-baseline-technology-stack.md`
- `docs/technical-decisions/02-database-and-storage-architecture.md`
- `docs/technical-decisions/03-vector-search-and-embedding-infrastructure.md`
- `docs/technical-decisions/04-background-processing-and-messaging.md`
- `docs/technical-decisions/05-NLP-and-machine-learning-stack.md`
- `docs/technical-decisions/06-api-security-and-internal-communication.md`
- `docs/technical-decisions/07-observability-and-testing-infrastructure.md`
- `docs/technical-decisions/08-deployment-and-environment-architecture.md`
- `docs/technical-decisions/Readme.md`

If a referenced document is missing, report it instead of inventing its contents.

---

## 3. Initial Repository Inspection

Before creating or modifying files, inspect the existing repository.

Inspect:

- Root directory structure.
- Existing `memory-engine/` contents.
- Existing Python files.
- Existing configuration files.
- Dependency management files.
- Existing test structure.
- Existing database configuration.
- Existing shared infrastructure modules.
- Existing Git configuration.
- Existing documentation and architecture references.

### Required actions

1. Identify whether `memory-engine/` already contains implementation code.
2. Identify whether a Python project has already been initialized.
3. Identify existing dependencies and their versions.
4. Identify existing package conventions.
5. Identify any existing reusable shared infrastructure.
6. Identify conflicts between the current repository and this implementation plan.
7. Prepare a short inspection summary before modifying files.

### Important

Do not delete, overwrite, rename, or restructure existing files merely to match a proposed structure.

Reuse existing components where they are compatible with the approved architecture.

If an existing implementation conflicts with an architectural specification, report the conflict and explain the proposed resolution before making a major architectural change.

---

## 4. Project Structure

Establish a modular Python package inside `memory-engine/`, as a member of a uv workspace rooted at the repository root.

The following is the proposed logical structure:

```text
raven-research-agent/              # repository root
│
├── pyproject.toml                 # uv workspace configuration only; no application code
├── uv.lock                        # single lockfile for the whole workspace
├── .python-version                # 3.12
├── .gitignore                     # includes .env files
│
├── memory-engine/                 # workspace member
│   ├── pyproject.toml             # member package metadata and dependencies
│   ├── .env.example               # placeholder values only
│   ├── README.md
│   └── src/
│       └── memory_engine/
│           ├── __init__.py
│           │
│           ├── config/
│           ├── domain/
│           ├── ingestion/
│           ├── extraction/
│           ├── entities/
│           ├── resolution/
│           ├── storage/
│           ├── retrieval/
│           ├── consolidation/
│           ├── deletion/
│           │
│           ├── interfaces/
│           ├── services/
│           ├── infrastructure/
│           ├── exceptions/
│           └── observability/
│
└── tests/                         # existing repository-root test directory
    └── memory_engine/
        ├── unit/
        ├── integration/
        └── fixtures/
```

This is the initial proposed structure, not an instruction to create every module immediately. Tests are not placed in `memory-engine/tests/`.

> **Superseded for later phases (approved 2026-11-11):** from Phase 8.2 onward, the package uses the domain-first layout in [`01-baseline-technology-stack.md`](../../technical-decisions/01-baseline-technology-stack.md) §23.1. The feature modules listed below become modules inside `memory_engine.personal.application`; Document Intelligence lives in `memory_engine.documents`. The Phase 8.1 foundation modules (`config`, `domain`, `exceptions`, `observability`) are unchanged.

Only establish directories and modules necessary for the foundation.

Empty placeholder modules must not be created merely to make the folder tree look complete.

### Module responsibilities

| Module | Responsibility |
|---|---|
| `config/` | Validated application configuration |
| `domain/` | Core domain concepts and business invariants |
| `ingestion/` | Input ingestion |
| `extraction/` | Fact extraction and evaluation |
| `entities/` | Entity and relationship management |
| `resolution/` | Duplicate and contradiction resolution |
| `storage/` | Persistence interfaces and implementations |
| `retrieval/` | Memory retrieval |
| `consolidation/` | Episodic and semantic consolidation |
| `deletion/` | Forgetting and deletion workflows |
| `interfaces/` | Contracts exposed to other components |
| `services/` | Application-level coordination |
| `infrastructure/` | Technical integrations |
| `exceptions/` | Structured domain and application errors |
| `observability/` | Logging and instrumentation |

Engine ownership must remain clear.

The Memory Engine must not absorb Orchestrator or Research Engine business responsibilities.

---

## 5. Python Project Configuration

Initialize or update the Python project using the approved technology baseline.

### Approved decisions

These were approved on 2026-11-11 and are recorded in [`docs/technical-decisions/01-baseline-technology-stack.md`](../../technical-decisions/01-baseline-technology-stack.md) §22.

| Decision | Approved choice |
|---|---|
| Python version | Python 3.12 |
| Type checker | mypy, strict mode |
| Project layout | uv workspace |
| Test location | Repository-root `tests/` |
| Configuration | Pydantic Settings (`pydantic-settings`) |

### Requirements

- Python 3.12 as the implementation runtime. Declare `requires-python` as a range beginning at 3.12 (`>=3.12`), and pin the development interpreter to 3.12.
- A uv workspace: the root `pyproject.toml` owns the workspace configuration and contains no application code; `memory-engine/` is a workspace member with its own `pyproject.toml`.
- One root `uv.lock` for the whole workspace. Do not create a separate lockfile for `memory-engine/`.
- `uv` as the selected dependency management tool.
- Reproducible dependency locking.
- Clear separation of runtime and development dependencies.
- A consistent import and package structure.

The uv workspace does not change the modular-monolith architecture and does not imply independent deployment.

### Dependency categories

**Phase 8.1 runtime dependencies:**

- Pydantic — data validation.
- pydantic-settings — validated, environment-based configuration.

**Phase 8.1 development dependencies:**

- pytest.
- pytest-cov.
- Ruff.
- mypy (strict mode).

**Deferred to Phase 8.2 (database persistence):**

- SQLAlchemy — database access.
- Alembic — database migrations.
- PostgreSQL driver — database connectivity. The driver and sync vs async access are decided in 8.2.

**Added only when required:**

- HTTPX — when API or HTTP testing is required.
- OpenTelemetry API/SDK — when instrumentation is implemented.

Additional NLP, embedding, messaging, and storage dependencies should be introduced in the milestones that actually require them.

Do not install every technology selected in Phase 7 during this initial milestone.

### Dependency policy

- Avoid unnecessary packages.
- Pin and lock dependencies appropriately.
- Avoid duplicate libraries performing the same responsibility without justification.
- Review licensing and maintenance status for new dependencies.
- Do not introduce generative LLM libraries as core processing dependencies.

---

## 6. Configuration Management

Create a centralized configuration mechanism.

Use Pydantic Settings (`pydantic-settings`) for validated, environment-based configuration.

Configuration must support environment-specific values.

Database connection settings may be defined and validated as configuration in 8.1, but no database driver or connection code is added until Phase 8.2.

### Initial configuration categories

- Application environment.
- Application name.
- Logging level.
- Database connection settings.
- Database schema configuration where required.
- Object storage configuration placeholders.
- Observability settings.
- Feature flags where justified.

### Requirements

1. Validate mandatory configuration at startup.
2. Reject invalid configuration.
3. Keep secrets outside source code.
4. Provide `.env.example` with placeholder values only.
5. Add actual `.env` files to `.gitignore`.
6. Never commit credentials.
7. Avoid hardcoding environment-specific values.
8. Keep configuration independent of business logic.

Do not connect to production infrastructure during local foundation setup.

---

## 7. Application and Module Boundaries

Establish clear boundaries between domain logic and infrastructure.

### Domain layer

Contains:

- Domain concepts.
- Business invariants.
- Domain-level value objects.
- Domain-specific exceptions.

It must not depend directly on:

- FastAPI.
- PostgreSQL drivers.
- RabbitMQ.
- Celery.
- External storage providers.

### Application layer

Coordinates use cases and domain operations.

It should depend on interfaces rather than concrete infrastructure implementations wherever practical.

### Infrastructure layer

Contains technical implementations such as:

- Database connections.
- Repository implementations.
- External storage adapters.
- Messaging integrations.
- Observability integrations.

### Interface layer

Defines the contracts through which other components interact with the Memory Engine.

The Orchestrator must interact with the Memory Engine through defined interfaces rather than directly manipulating its internal records.

### Important

Do not introduce excessive abstractions.

Create interfaces where they protect ownership, enable testing, or isolate replaceable infrastructure.

---

## 8. Error Handling Foundation

Establish a consistent exception structure.

Potential categories:

- Configuration errors.
- Validation errors.
- Authorization errors.
- Ownership errors.
- Persistence errors.
- Ingestion errors.
- Extraction errors.
- Resolution errors.
- Retrieval errors.
- Deletion errors.
- Infrastructure errors.

### Requirements

- Use meaningful exception types.
- Preserve the original cause of technical failures.
- Avoid swallowing exceptions.
- Avoid returning raw stack traces to users.
- Keep domain errors separate from infrastructure errors.
- Ensure failures can be logged and traced.
- Do not report an operation as successful before its required persistence is confirmed.

Detailed recovery and retry behavior will be implemented in the relevant later milestones.

---

## 9. Logging and Observability Foundation

Establish the initial structured logging mechanism.

### Logging requirements

- Consistent log format.
- Timestamp.
- Log level.
- Component name.
- Operation name.
- Correlation identifiers where available.
- Safe error information.

### Privacy requirements

Never log:

- Passwords.
- API keys.
- Access tokens.
- Database credentials.
- Unnecessary raw personal memory content.

### Observability

Prepare the codebase for OpenTelemetry instrumentation, for example by carrying correlation identifiers in structured logs. Do not add OpenTelemetry packages in this milestone; they are added when instrumentation is implemented.

Do not build a complete monitoring deployment in this milestone.

Full metrics, traces, dashboards, and alerting are covered by the relevant infrastructure and testing plans.

---

## 10. Testing Foundation

Establish pytest and a consistent testing structure.

Tests live in the repository-root `tests/` directory, organized by engine and test type (Memory Engine tests under `tests/memory_engine/`). Create test directories only when they contain tests.

### Test categories

**Unit tests**

Test individual functions, validators, domain objects, and configuration behavior.

**Integration tests**

Test interactions with actual infrastructure dependencies, using isolated test resources.

**Fixtures**

Provide reusable test fixtures and controlled synthetic data.

### Initial tests

Implement tests for:

1. Project imports.
2. Configuration validation.
3. Missing mandatory configuration.
4. Invalid configuration values.
5. Exception behavior.
6. Basic domain-layer independence from infrastructure.
7. Logging initialization.

### Testing rules

- Tests must be repeatable.
- Tests must not depend on production data.
- External infrastructure tests must use isolated test resources.
- Do not make network calls in ordinary unit tests.
- Test failures must be investigated rather than ignored.
- Do not use mocks to replace every meaningful integration test.

---

## 11. Development Environment

Establish a reproducible local development workflow.

Document commands for:

- Installing dependencies.
- Activating the development environment.
- Running tests.
- Running linting.
- Running type checking (mypy, strict mode).
- Checking package imports.

Commands run through uv from the repository root against the workspace.

Use Docker Compose only where required for local infrastructure dependencies.

Do not deploy PostgreSQL, RabbitMQ, or object storage as part of this milestone unless an existing repository setup already requires it.

Database infrastructure setup is handled in Phase 8.2.

---

## 12. README Documentation

Create or update:

`memory-engine/README.md`

It should explain:

- What the Memory Engine does.
- Its responsibilities.
- Its boundaries.
- Its relationship with the Orchestrator.
- Its relationship with Shared Infrastructure.
- How to set up the development environment.
- How to run tests.
- Where detailed architecture documentation lives.

Do not duplicate the complete architecture specification.

---

## 13. Implementation Order

Claude Code should execute this milestone in the following order:

### Step 1 — Repository inspection

Inspect existing code and configuration.

### Step 2 — Foundation proposal

Report the existing structure and proposed changes.

### Step 3 — Package setup

Establish the Python package and minimal directory structure.

### Step 4 — Dependency management

Configure the root workspace `pyproject.toml`, the `memory-engine/pyproject.toml` member, and the single root `uv.lock`.

### Step 5 — Configuration

Implement validated environment-specific configuration.

### Step 6 — Module boundaries

Establish the minimum required domain, application, infrastructure, and interface boundaries.

### Step 7 — Error handling

Implement foundational exception types.

### Step 8 — Logging

Implement structured logging initialization.

### Step 9 — Testing

Establish pytest and foundational tests.

### Step 10 — Documentation

Create or update `memory-engine/README.md`.

### Step 11 — Verification

Run all required checks and report actual results.

---

## 14. Expected Deliverables

At the end of this milestone, the repository should contain:

- A valid Python project inside `memory-engine/`.
- A reproducible dependency configuration.
- A validated application configuration mechanism.
- A minimal modular package structure.
- Foundational error handling.
- Structured logging initialization.
- A working pytest setup.
- Initial automated tests.
- A Memory Engine README.
- A documented implementation summary.

The exact files depend on the existing repository inspection.

Do not create unnecessary files just to match a prescribed example.

---

## 15. Acceptance Criteria

Phase 8.1 is complete only when:

### Project foundation

- [ ] Python package initializes successfully on Python 3.12.
- [ ] uv workspace is configured at the repository root with `memory-engine/` as a member.
- [ ] Dependency installation works.
- [ ] A single root `uv.lock` is generated and reproducible.
- [ ] Only the approved Phase 8.1 dependencies are present.
- [ ] Package imports work.

### Configuration

- [ ] Configuration uses Pydantic Settings.
- [ ] Valid configuration loads.
- [ ] Missing mandatory configuration fails clearly.
- [ ] Invalid values are rejected.
- [ ] Secrets are not committed.

### Architecture

- [ ] Domain and infrastructure boundaries are established.
- [ ] Memory Engine ownership is preserved.
- [ ] No Orchestrator or Research business logic is introduced.
- [ ] No unnecessary infrastructure is added.

### Quality

- [ ] Logging initializes correctly.
- [ ] Error handling is consistent.
- [ ] pytest executes successfully from the repository root.
- [ ] Foundational tests in `tests/memory_engine/` pass.
- [ ] Ruff checks pass.
- [ ] mypy in strict mode passes for the configured scope.

### Documentation

- [ ] Memory Engine README exists and is accurate.
- [ ] Setup and testing commands are documented.
- [ ] Existing repository documentation is preserved.

---

## 16. Out of Scope

Do not implement the following in Phase 8.1:

- Database tables and migrations.
- Memory ingestion logic.
- Fact extraction.
- Memory candidate generation.
- Entity resolution.
- Duplicate detection.
- Contradiction detection.
- Memory retrieval.
- Embedding generation.
- Vector indexing.
- Episodic consolidation.
- Profile generation.
- Forgetting and deletion workflows.
- RabbitMQ integration.
- Celery worker implementation.
- Production deployment.

These belong to subsequent implementation milestones.

---

## 17. Claude Code Execution Instructions

Claude Code must follow these rules:

1. Inspect the existing repository before making changes.
2. Read the referenced architecture and technology documents.
3. Do not redesign approved architecture.
4. Do not overwrite existing working code without justification.
5. Do not invent missing architecture decisions.
6. Do not install unnecessary dependencies.
7. Do not introduce generative LLM APIs or locally hosted generative LLMs.
8. Keep implementation inside the existing `memory-engine/` directory.
9. Keep implementation plans inside `docs/implementation-plans/`.
10. Run tests and report actual outputs.
11. Report incomplete acceptance criteria honestly.
12. Do not proceed to Phase 8.2 automatically.

If a significant architectural conflict or security concern is discovered, stop the affected work and report it.

---

## 18. Completion Report

Claude Code must provide a final implementation report containing:

- Files created.
- Files modified.
- Dependencies added.
- Configuration implemented.
- Tests added.
- Commands executed.
- Test results.
- Linting results.
- Type-checking results.
- Known limitations.
- Unresolved issues.
- Acceptance criteria status.

A planned or partially implemented feature must not be described as complete.

**Status:** Planned.

**Next milestone:** Phase 8.2 — Database and Persistence.
