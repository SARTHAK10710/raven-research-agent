# Raven Research Agent

An independent AI Research Agent architecture centered on persistent memory, evidence-based research, and adaptive orchestration.

> **Status:** architecture only. No engine code, schemas, database choices, detailed algorithms, operational thresholds, implementation, or production tests are included.

## Architecture Summary

Raven has four conceptual layers:

1. **User Interface / Entry Layer** — request intake, authentication context, validation, and response delivery.
2. **Agent Orchestrator** — intent understanding, planning, routing, coordination, execution state, recovery, and response assembly.
3. **Specialized Engines** — Memory Engine for persistent memory and Research Engine for external evidence.
4. **Shared Infrastructure** — future storage, indexing, identity, communication, execution, and observability capabilities.

These are ownership boundaries, not a decision to deploy separate microservices.

| Component | Optimization : Performance |
| --- | --- |
| Memory Engine | **70 : 30** |
| Research Engine | **55 : 45** |
| Agent Orchestrator | **45 : 55** |

The ratios are architecture preferences, not measured runtime allocations or benchmarks.

## Phase Status

| Phase | Status |
| --- | --- |
| Phase 1 — Overall Architecture | **Formally complete** |
| Phase 2 — Memory Engine | **Architecture complete** |
| Phase 3 — Research Engine | **Architecture complete** |
| Phase 4 — Agent Orchestrator | **Architecture complete** |

Read [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) and the documents in [docs/architecture](docs/architecture).

## Claude Code Workflow

1. Treat the approved architecture documents as the source of truth.
2. Create an implementation-ready specification before coding a component.
3. Use Claude Code to implement only the approved specification.
4. Propose and approve architecture changes before implementation.
5. Validate implementation against architecture, acceptance criteria, evidence/provenance rules, and tests.
6. Record schema, database, algorithm, threshold, and operational decisions before relying on them.

Claude Code must not independently alter agreed architectural decisions.

## Deferred Work

Database choices, schemas, API contracts, algorithms, retention periods, retry limits, resource budgets, concurrency mechanisms, operational thresholds, benchmarks, deployment, security implementation, and tests are intentionally deferred and not yet implemented or validated.
