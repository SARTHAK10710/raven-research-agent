# Project Architecture

## Status and Scope

Phase 1 — Overall System Architecture is **formally complete**. Phases 2–4 are **architecture complete**. This repository captures conceptual architecture only; it contains no engine implementation.

Raven combines personal/contextual memory with current external research through four conceptual layers: Entry Layer, Agent Orchestrator, specialized Memory and Research Engines, and Shared Infrastructure. The layers define ownership, not deployment topology.

## Fixed Design Preferences

| Engine | Optimization : Performance | Architectural consequence |
| --- | --- | --- |
| Memory Engine | **70 : 30** | Favor durable, attributable, deduplicated memory and correct forgetting. |
| Research Engine | **55 : 45** | Balance evidence quality with efficient acquisition and reuse. |
| Agent Orchestrator | **45 : 55** | Favor efficient routing, controlled parallelism, and throughput while preserving correctness. |

These ratios are decision preferences, not quotas, service-level objectives, or benchmark results.

## Boundaries and Communication

The Orchestrator plans and coordinates. Memory owns memory lifecycle and data integrity. Research owns external discovery, evidence handling, and research-session lifecycle. Shared Infrastructure supplies common technical capabilities. Memory and Research do not directly orchestrate one another; the Orchestrator mediates cross-engine coordination by default.

Communication is hybrid: synchronous request/response for immediate operations and asynchronous commands/events for long-running work. Conceptual message types are Command, Query, Response, and Event. Contracts require versioning, validation, identity, execution/task/correlation IDs, idempotency, timeouts, standardized errors, provenance, and observability. Concrete schemas and protocols are deferred.

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

## Deferred

Database/storage, API/message schemas, protocols, algorithms, scoring, retry counts, capacity/resource thresholds, retention durations, security mechanisms, observability thresholds, deployment, implementation, benchmarks, and tests are deferred and not implemented or validated.
