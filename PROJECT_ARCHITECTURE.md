# Project Architecture

## Status and Scope

Phase 1 — Overall System Architecture is **formally complete**. Phases 2–4 are **architecture complete**. Phases 5–7 (data models, algorithms, and technology decisions) are **documented**, and Phase 8 (Memory Engine implementation) is planned. The repository contains no engine implementation yet.

Raven has **three primary engines** (Memory Engine, Research Engine, and Agent Orchestrator) supported by Shared Infrastructure. It combines personal/contextual memory and uploaded-document knowledge with current external research through four conceptual layers: Entry Layer, Agent Orchestrator, specialized Memory and Research Engines, and Shared Infrastructure. The layers define ownership, not deployment topology; Phase 7 selected a modular monolith with independently executable background workers.

## Memory Engine Knowledge Domains

The Memory Engine owns two separate logical knowledge domains:

- **Personal Memory** — persistent user facts, preferences, decisions, entities, and relationships.
- **Document Intelligence** — uploaded document registration, extraction, chunking, embeddings, hybrid retrieval, evidence selection, and citation management.

The domains keep separate ownership, data models, retrieval workflows, and lifecycle policies even when they reuse infrastructure. Document chunks are not personal memories, uploads do not automatically create personal memories, and document-derived facts enter personal memory only through the authorized extraction and resolution workflow. Document retrieval (uploaded content) is also distinct from external research, which the Research Engine owns.

## Fixed Design Preferences

| Engine | Optimization : Performance | Architectural consequence |
| --- | --- | --- |
| Memory Engine | **70 : 30** | Favor durable, attributable, deduplicated memory and correct forgetting. |
| Research Engine | **55 : 45** | Balance evidence quality with efficient acquisition and reuse. |
| Agent Orchestrator | **45 : 55** | Favor efficient routing, controlled parallelism, and throughput while preserving correctness. |

These ratios are decision preferences, not quotas, service-level objectives, or benchmark results.

## Boundaries and Communication

The Orchestrator plans and coordinates. Memory owns memory lifecycle and data integrity. Research owns external discovery, evidence handling, and research-session lifecycle. Shared Infrastructure supplies common technical capabilities. Memory and Research do not directly orchestrate one another; the Orchestrator mediates cross-engine coordination by default.

Communication is hybrid: synchronous request/response for immediate operations and asynchronous commands/events for long-running work. Conceptual message types are Command, Query, Response, and Event. Contracts require versioning, validation, identity, execution/task/correlation IDs, idempotency, timeouts, standardized errors, provenance, and observability. Phase 7 selected REST/OpenAPI via FastAPI for synchronous communication and RabbitMQ with Celery for asynchronous work; concrete schemas are defined during implementation.

## Invariants

1. External dependencies are untrusted.
2. Every accepted request is traceable through an execution identity.
3. Every task is traceable and independently stateful.
4. Ownership, permissions, and user/context isolation are preserved.
5. Material findings retain provenance and temporal context.
6. Current observations never silently overwrite history.
7. Similarity identifies candidate matches; it is not proof for a merge.
8. Repeated operations require idempotent reconciliation.
9. Failures and incomplete work remain visible.
10. Explicit forgetting overrides expiry and archival.
11. Recovery stays with the owning component; the Orchestrator coordinates.
12. Performance never silently weakens correctness, deletion, identity, or evidence obligations.

## Claude Code Workflow

1. Use these documents as the architecture baseline.
2. Define implementation scope, data models, algorithms, and acceptance criteria before coding.
3. Implement with Claude Code only after relevant design decisions are approved.
4. Keep architecture changes separate from implementation changes.
5. Review implementation against this document and its phase specification.
6. Add deterministic and operational testing before claiming behavior is proven.

## Decided in Later Phases

Data models (Phase 5, [docs/data-models](docs/data-models/Readme.md)), algorithms (Phase 6, [docs/algorithms](docs/algorithms/Readme.md)), and the database, storage, messaging, NLP, API, observability, and deployment technologies (Phase 7, [docs/technical-decisions](docs/technical-decisions/Readme.md)) have been documented. Those documents are authoritative for their areas.

## Deferred

Concrete API/message schemas, exact embedding and reranking models, scoring and decision thresholds, retry counts, capacity/resource thresholds, retention durations, identity and secrets providers, hosting and deployment targets, observability thresholds, benchmarks, implementation, and tests remain deferred and are not implemented or validated.
