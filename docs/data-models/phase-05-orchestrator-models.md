# Phase 5.6 — Agent Orchestrator Data Models

**Project:** Raven — AI Research Agent  
**Phase:** 5 — Data Models & Database Design  
**Component:** Agent Orchestrator  
**Status:** Architecture Complete  
**Optimization Priority:** Agent Orchestrator — 45:55 (as established in Phase 4)

---

# 1. Objective

This document defines the logical data models, relationships, ownership boundaries and lifecycle principles of the Raven Agent Orchestrator.

The Agent Orchestrator coordinates requests and manages execution across the Memory Engine, Research Engine and other system components.

Its data architecture must support:

- Request execution tracking.
- Task creation and management.
- Task dependencies.
- Execution planning and scheduling.
- Sequential and parallel execution.
- Context management.
- Execution progress tracking.
- Retry and recovery.
- Cancellation management.
- Checkpointing.
- Result validation.
- Partial completion.
- Execution history and traceability.

The Orchestrator owns execution-related records but does not own the business data maintained by the Memory Engine or Research Engine.

This document defines logical architecture, not production database schemas or technology choices.

---

# 2. Orchestrator Data Architecture

The Orchestrator maintains seven primary conceptual entities:

1. Execution
2. Task
3. Task Dependency
4. Execution Context
5. Checkpoint
6. Execution Event
7. Execution Result

Additional internal metadata may be introduced when required by implementation.

Not every conceptual entity must become a separate database table or collection.

The Orchestrator remains the authoritative owner of execution and task coordination records.

---

# 3. Execution

An Execution represents one identifiable instance of processing a user request.

It provides the top-level coordination context for all tasks associated with that request.

## 3.1 Execution Identity

Every Execution receives a globally unique opaque identifier.

The Execution ID provides a stable reference for:

- Task association.
- Progress tracking.
- Context management.
- Checkpointing.
- Retry and recovery.
- Cancellation.
- Result consolidation.
- Execution history.

An Execution ID must not encode private user information.

## 3.2 Execution Responsibilities

An Execution logically groups:

- Original request reference.
- User identity and authorization context.
- Interpreted intent.
- Execution plan.
- Associated tasks.
- Task dependencies.
- Resource and priority information.
- Execution progress.
- Context references.
- Checkpoints.
- Execution events.
- Task results.
- Final execution outcome.

The Orchestrator owns these execution records.

## 3.3 Execution Lifecycle

Execution lifecycle represents the overall state of a request.

The exact execution state taxonomy will be finalized during algorithm and schema design.

The lifecycle must distinguish:

- Execution creation.
- Validation.
- Planning.
- Active execution.
- Partial completion.
- Successful completion.
- Failure.
- Cancellation.
- Recovery where applicable.

Execution state must remain consistent with its associated task states.

## 3.4 Execution Ownership

The Orchestrator is the sole authoritative owner of Execution records.

Memory Engine and Research Engine may receive execution references but cannot directly modify Orchestrator-owned execution state.

---

# 4. Task

A Task represents an independently identifiable unit of work within an Execution.

Tasks allow the Orchestrator to coordinate sequential, parallel and dependent operations.

## 4.1 Task Identity

Every Task receives a globally unique opaque identifier.

Every Task references its parent Execution.

## 4.2 Task Responsibilities

A Task may represent:

- Memory retrieval.
- Research discovery.
- Research extraction.
- Memory processing requests.
- Evidence verification.
- Data consolidation.
- Other delegated operations.

The task represents the requested work and its execution state.

Engine-specific business operations remain owned by the respective engines.

## 4.3 Task Metadata

A Task may logically contain:

- Task identity.
- Parent Execution reference.
- Task type.
- Assigned component or engine.
- Task input references.
- Task status.
- Priority.
- Dependency information.
- Retry information.
- Execution timestamps.
- Result references.
- Error information where applicable.

Exact fields and types are deferred to schema design.

## 4.4 Task Lifecycle

The following task states were established in Phase 1:

- `created`
- `validated`
- `blocked`
- `queued`
- `dispatched`
- `running`
- `completed`
- `retrying`
- `failed`
- `skipped`
- `cancellation_requested`
- `cancelled`

Task state transitions are controlled by the Orchestrator.

Invalid transitions must be rejected.

## 4.5 Task Ownership

The Orchestrator owns Task records and task coordination state.

An assigned engine executes the delegated business operation but does not become the owner of the Orchestrator's Task record.

---

# 5. Task Dependency

A Task Dependency represents an explicit execution dependency between two tasks.

## 5.1 Dependency Responsibilities

Task dependencies define whether one task must wait for another task to complete or reach an acceptable outcome.

Examples:

- Memory retrieval must finish before targeted research begins.
- Research discovery must finish before source extraction.
- Independent research queries may execute concurrently.
- Result consolidation may wait for multiple tasks.

## 5.2 Dependency Representation

Task Dependencies are represented as independent logical records.

Each dependency identifies:

- The dependent task.
- The prerequisite task.
- The dependency relationship.
- Relevant dependency metadata.

## 5.3 Dependency Rules

1. A task must not execute before its required dependencies are satisfied.
2. Independent tasks may execute concurrently.
3. Dependencies must be traceable.
4. Dependency cycles must be detected and rejected.
5. Failed prerequisite tasks must be handled according to recovery policy.
6. Skipped or cancelled prerequisites must not silently satisfy dependencies.
7. Dependency changes must preserve execution consistency.

## 5.4 Ownership

The Orchestrator owns Task Dependency records.

Engines may report task outcomes but cannot independently redefine the overall execution dependency graph.

---

# 6. Execution Context

Execution Context represents the bounded information required by the Orchestrator and its delegated tasks.

It may contain references to information retrieved from the Memory Engine, Research Engine and other authorized components.

## 6.1 Context Responsibilities

Execution Context supports:

- Relevant historical memories.
- Research findings.
- Source references.
- Confidence and verification information.
- Temporal information.
- User constraints.
- Task-specific inputs.
- Intermediate execution information.

## 6.2 Context Ownership

The Orchestrator owns execution-specific context snapshots.

Original information remains owned by its originating engine.

A context snapshot does not transfer ownership of referenced data.

## 6.3 Context Integrity

1. Context must be limited to information relevant to the task.
2. Original source references must be preserved.
3. Provenance and timestamps must remain available where applicable.
4. User-level isolation must be enforced.
5. Historical and current information must remain distinguishable.
6. Stale context must not silently be treated as current.
7. Deletion and access-control changes must propagate to applicable snapshots.
8. Temporary context follows execution and task retention policies.

## 6.4 Temporary Context Snapshots

The Orchestrator may create temporary context snapshots for individual executions or tasks.

These snapshots are operational representations, not authoritative engine records.

The originating engine retains ownership of the original data.

---

# 7. Checkpoint

A Checkpoint represents a recoverable execution state captured during an Execution.

Checkpoints help the Orchestrator resume work without unnecessarily repeating completed operations.

## 7.1 Checkpoint Responsibilities

A checkpoint may preserve:

- Execution reference.
- Relevant task states.
- Completed task references.
- Dependency progress.
- Recovery position.
- Required context references.
- Relevant execution metadata.

## 7.2 Checkpoint Rules

1. Checkpoints belong to the Orchestrator.
2. Checkpoints must identify the Execution they belong to.
3. Checkpoints must preserve enough information for supported recovery.
4. Checkpoints must not become authoritative copies of engine-owned business data.
5. Recovery must validate the freshness of referenced information.
6. Checkpoint updates must not silently overwrite authoritative task history.
7. Checkpoint retention follows execution retention policies.

## 7.3 Recovery Principles

When an Execution fails:

- Previously completed tasks remain completed.
- Only eligible failed or incomplete tasks are retried.
- Dependencies are reevaluated.
- Existing results are reused when valid.
- Stale or inconsistent state is reconciled before recovery.

---

# 8. Execution Events

Execution Events represent meaningful events in the lifecycle of an Execution or Task.

Examples include:

- Execution created.
- Task created.
- Task dispatched.
- Task started.
- Task completed.
- Task failed.
- Retry initiated.
- Cancellation requested.
- Cancellation completed.
- Checkpoint created.
- Recovery initiated.

## 8.1 Event Responsibilities

Execution Events provide traceability for orchestration operations.

They may capture:

- Event identity.
- Execution reference.
- Task reference where applicable.
- Event type.
- Timestamp.
- Relevant state transition.
- Correlation information.
- Safe metadata.

## 8.2 Event Ownership

The Orchestrator owns Execution Events.

Events must not duplicate engine-specific business audit records.

For example:

- The Orchestrator records that a Research task completed.
- The Research Engine records the source verification and findings produced by that task.

## 8.3 Event Integrity

- Events must be traceable.
- Events must preserve execution correlation.
- Sensitive content and secrets must not be unnecessarily stored.
- Event history follows applicable retention and access policies.
- Duplicate event processing must be handled safely.

---

# 9. Execution Results

An Execution Result represents the outcome produced by a Task or Execution.

## 9.1 Result Responsibilities

Results may include:

- Result identity
