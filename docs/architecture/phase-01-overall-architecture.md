# Phase 1 — Overall System Architecture

**Status: formally complete.**  
**Scope: conceptual architecture; not an implementation specification.**

## Architecture

The four conceptual layers are:

1. **Entry Layer** — request reception/validation, authentication context, cancellation intake, and response delivery.
2. **Agent Orchestrator** — intent, planning, routing, state, recovery, and response assembly.
3. **Specialized Engines** — Memory lifecycle and external research/evidence.
4. **Shared Infrastructure** — future storage, indexing, identity, messaging, execution, and observability.

The layers are responsibility boundaries, not mandatory microservices.

## Ownership

| Component | Owns |
| --- | --- |
| Entry Layer | Input validation, identity context, and delivery |
| Orchestrator | Planning, routing, coordination, execution state, response assembly |
| Memory Engine | Memory ingestion, retrieval, storage, maintenance, deletion |
| Research Engine | Discovery, extraction, verification, research sessions |
| Shared Infrastructure | Common technical capabilities |

The Orchestrator does not take over engine-internal business logic. Engines do not directly orchestrate each other.

## Communication

Use hybrid communication: synchronous request/response when an immediate result is required, and asynchronous commands/events for long-running or independent work. Conceptual message categories are Command, Query, Response, and Event. Contracts require versioning, validation, identity, correlation, idempotency, timeouts, standard errors, provenance, and observability.

## Adaptive Request Lifecycle

1. Request reception.
2. Validation, authentication, and execution-ID creation.
3. Intent understanding.
4. Conditional context acquisition.
5. Task planning and dependency management.
6. Engine routing and coordination.
7. Task execution and progress management.
8. Result validation and consolidation.
9. Evidence-aware response assembly.
10. Response delivery and execution finalization.

The lifecycle is adaptive, not rigid: routing, replanning, partial results, cancellation, and delivery retries are supported.

## Failure and Safety Policies

Components own local failures; the Orchestrator coordinates cross-engine recovery; Shared Infrastructure owns infrastructure failures; Entry owns request/authentication/delivery failures. Permitted recovery includes bounded retry, fallback, partial recovery, graceful degradation, escalation, and safe cancellation. Failures and incomplete work cannot be presented as success.

External services are untrusted. The architecture requires identity isolation, ownership-aware reuse, provenance, historical preservation, conflict visibility, idempotency, and correct explicit forgetting.

## Deferred

Formal schemas, database choices, protocols, scheduling/routing algorithms, backpressure, retry/resource/timeout thresholds, retention periods, security mechanisms, deployment, operations, and tests are deferred and not implemented or validated.
