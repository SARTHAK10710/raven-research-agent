# Raven Research Agent

An independent AI Research Agent architecture centered on persistent memory, evidence-based research, and adaptive orchestration.

> **Status:** documentation complete through Phase 7 (architecture, data models, algorithms, and technology decisions). Phase 8 (Memory Engine implementation) has started: **only the Phase 8.1 foundation is implemented** (configuration, error hierarchy, structured logging, 71 unit tests; merged in PR #3). No memory, document, research, or orchestration functionality exists, and nothing has been deployed. Current state: [docs/project-context/PROJECT_STATUS.md](docs/project-context/PROJECT_STATUS.md).

## Architecture Summary

Raven is built around **three primary engines** supported by shared infrastructure:

1. **Memory Engine** — persistent knowledge in two separate logical domains:
   - **Personal Memory** — facts, preferences, decisions, entities, and relationships about the user.
   - **Document Intelligence** — uploaded document processing, chunking, embeddings, hybrid retrieval, evidence selection, and citations.
2. **Research Engine** — external discovery, extraction, verification, and research-session lifecycle.
3. **Agent Orchestrator** — intent understanding, planning, routing, coordination, execution state, recovery, and response assembly.

These sit within four conceptual layers: the **User Interface / Entry Layer** (request intake, authentication context, validation, and response delivery), the **Agent Orchestrator**, the **Specialized Engines** (Memory and Research), and **Shared Infrastructure** (storage, indexing, identity, messaging, execution, and observability).

Personal Memory and Document Intelligence have separate ownership, data models, retrieval workflows, and lifecycle rules. They may share infrastructure, but document chunks are never treated as personal memories.

These are ownership boundaries, not a decision to deploy separate microservices. Phase 7 selected a modular monolith with independently executable background workers.

| Component | Optimization : Performance |
| --- | --- |
| Memory Engine | **70 : 30** |
| Research Engine | **55 : 45** |
| Agent Orchestrator | **45 : 55** |

The ratios are architecture preferences, not measured runtime allocations or benchmarks.

## Technology Baseline

Phase 7 selected Python (3.12), FastAPI, Pydantic (with Pydantic Settings for configuration), PostgreSQL with SQLAlchemy and Alembic, pgvector, S3-compatible object storage, RabbitMQ with Celery, spaCy, scikit-learn, the sentence-transformers ecosystem, OpenTelemetry, Prometheus, Grafana, pytest, Ruff, mypy (strict mode), uv (as a workspace), and Docker. Core processing does not use generative LLM APIs or locally hosted generative LLMs. See [docs/technical-decisions](docs/technical-decisions/Readme.md) for the full decisions and their status.

## Phase Status

Documentation completion and implementation completion are tracked separately.

| Phase | Documentation | Implementation |
| --- | --- | --- |
| Phase 1 — Overall Architecture | **Formally complete** | — |
| Phase 2 — Memory Engine Architecture | **Architecture complete** | — |
| Phase 3 — Research Engine Architecture | **Architecture complete** | — |
| Phase 4 — Agent Orchestrator Architecture | **Architecture complete** | — |
| Phase 5 — Data Models & Database Design | **Documented** | — |
| Phase 6 — Algorithms & Processing Design | **Documented** | — |
| Phase 7 — Technology & Infrastructure Selection | **Documented** | — |
| Phase 8 — Memory Engine Implementation | **Plans documented** | **In progress:** 8.1 foundation verified and merged; 8.2–8.12 not started |

## Documentation

| Area | Location |
| --- | --- |
| Claude Code instructions and project context | [CLAUDE.md](CLAUDE.md), [docs/project-context](docs/project-context/README.md) (status, implementation state, constraints, next steps) |
| Architecture baseline | [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md), [docs/architecture](docs/architecture/Readme.md) |
| Design overview | [DESIGN.md](DESIGN.md) |
| Data models (Phase 5) | [docs/data-models](docs/data-models/Readme.md) |
| Algorithms (Phase 6) | [docs/algorithms](docs/algorithms/Readme.md) |
| Technology decisions (Phase 7) | [docs/technical-decisions](docs/technical-decisions/Readme.md) |
| Memory Engine implementation plans (Phase 8) | [docs/implementation-plans/Phase-08-memory-engine](docs/implementation-plans/Phase-08-memory-engine/Readme.md) |

## Claude Code Workflow

1. Treat the approved architecture documents as the source of truth.
2. Create an implementation-ready specification before coding a component.
3. Use Claude Code to implement only the approved specification.
4. Propose and approve architecture changes before implementation.
5. Validate implementation against architecture, acceptance criteria, evidence/provenance rules, and tests.
6. Record schema, database, algorithm, threshold, and operational decisions before relying on them.

Claude Code must not independently alter agreed architectural decisions.

## Deferred Work

Database and core technology choices are no longer deferred; they were made in Phase 7. The following remain deferred until implementation evidence or an explicit decision is available:

- Exact embedding model and dimensions, reranking model, chunk size and overlap.
- Document parser adoption (pypdf and python-docx are proposed but require evaluation), OCR, and advanced layout or table extraction.
- Authentication and secrets-management providers, cloud provider, production hosting, and production orchestration.
- Dedicated vector database or search engine (only if measured workload justifies them).
- Concrete API and message schemas, queue topology, retry counts, resource budgets, and operational thresholds.
- Retention periods, backup frequency and retention, and RPO/RTO targets.
- CI provider, coverage thresholds, and benchmark datasets.

Nothing has been implemented, benchmarked, or validated by tests yet.
