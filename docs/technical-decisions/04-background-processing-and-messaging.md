# Phase 7.4 — Background Processing & Messaging Infrastructure

## 1. Purpose

This document defines Raven's asynchronous processing and internal messaging architecture.

It establishes how Raven executes long-running tasks, coordinates background workers, communicates between components, handles retries and failures, and maintains reliable execution across the Memory Engine, Research Engine, and Agent Orchestrator.

The objective is to support reliable asynchronous execution without sacrificing correctness, traceability, data integrity, or user isolation.

This document defines the architectural direction. Exact queue topology, worker counts, concurrency settings, and production delivery guarantees will be finalized during implementation and evaluation.

---

## 2. Architectural Principles

Raven's background processing infrastructure follows these principles:

1. Long-running work should not block request-handling operations.
2. The Orchestrator owns workflow coordination and execution state.
3. Each engine owns its business processing and domain-specific job results.
4. Workers execute tasks; they do not independently redefine business workflows.
5. Every task must have a traceable identity.
6. Task execution must be safe under retries and duplicate delivery.
7. Acknowledgement must reflect actual processing and persistence outcomes.
8. Failure must not be silently reported as success.
9. Cancellation must be cooperative and state-aware.
10. Queue processing must respect user isolation and authorization.
11. Completed work must be preserved when unrelated tasks fail.
12. Correctness and reliability take priority over throughput optimization.

---

## 3. Technology Selection

The initial background processing stack is:

| Responsibility | Selected technology |
|---|---|
| Message broker | RabbitMQ |
| Background task framework | Celery |
| Primary database | PostgreSQL |
| Database ORM | SQLAlchemy |
| Database migrations | Alembic |
| Application language | Python |
| API framework | FastAPI |

### 3.1 RabbitMQ

RabbitMQ provides message transport between application components and background workers.

It is responsible for:

- Message routing.
- Queue management.
- Message delivery.
- Acknowledgements.
- Retry and dead-letter routing support.
- Durable queue and message configuration where required.

RabbitMQ does not own Raven's business execution state.

### 3.2 Celery

Celery provides the background task execution framework.

It is responsible for:

- Executing background jobs.
- Worker management.
- Task scheduling.
- Retry mechanics.
- Task routing.
- Task execution lifecycle hooks.
- Worker concurrency configuration.

Celery does not replace the Orchestrator's execution and task state management.

### 3.3 PostgreSQL

PostgreSQL remains the authoritative store for Raven's execution records and engine-owned business records.

RabbitMQ and Celery must not become the only source of truth for task completion or business outcomes.

---

## 4. Logical Architecture

Raven uses a hybrid synchronous and asynchronous execution architecture.

```text
                  User Request
                       |
                       v
                 FastAPI Layer
                       |
                       v
                Agent Orchestrator
                       |
             Execution & Task Records
                       |
                       v
                Message Publisher
                       |
                       v
                   RabbitMQ
                       |
          +------------+------------+
          |            |            |
          v            v            v
      Memory       Research     Maintenance
      Workers      Workers       Workers
          |            |            |
          v            v            v
      Memory       Research     Shared/Owned
      Engine       Engine       Operations
          |            |            |
          +------------+------------+
                       |
                       v
                   PostgreSQL
                       |
                       v
              Result / Event Records
                       |
                       v
                Agent Orchestrator
                       |
                       v
                 Final Response
```

This is a logical architecture. It does not require every worker category to run as a separate deployed service from the beginning.

---

## 5. Synchronous vs Asynchronous Processing

Raven must use both execution modes.

### 5.1 Synchronous processing

Use synchronous processing when an operation is:

- Short-running.
- Required to complete before the immediate response.
- Lightweight enough to execute within the request lifecycle.
- Better handled through direct request-response communication.

Examples:

- Request validation.
- Authorization checks.
- Lightweight intent classification.
- Simple metadata retrieval.
- Small database reads.
- Immediate status queries.

### 5.2 Asynchronous processing

Use asynchronous processing when an operation is:

- Long-running.
- Resource-intensive.
- Independently retryable.
- Suitable for background execution.
- Not required to block the initial request.

Examples:

- Research discovery and extraction.
- Large document processing.
- Routine memory extraction.
- Embedding generation.
- Memory consolidation.
- Bulk re-indexing.
- Research refresh.
- Maintenance and reconciliation.

### 5.3 Hybrid execution

A workflow may combine both modes.

For example:

1. Receive and validate a user request synchronously.
2. Create an execution record.
3. Generate a task plan.
4. Publish background tasks.
5. Return an execution identifier or initial status.
6. Execute work asynchronously.
7. Record progress and results.
8. Notify or respond when the workflow reaches an appropriate state.

The Orchestrator determines which execution mode is appropriate.

---

## 6. Queue Architecture

Raven will use logical queues organized around workload ownership and processing characteristics.

Potential queue categories include:

| Queue category | Responsibility |
|---|---|
| Memory processing | Memory ingestion, extraction, and resolution jobs |
| Memory maintenance | Consolidation, profile refresh, and maintenance |
| Research processing | Discovery, extraction, verification, and synthesis jobs |
| Research maintenance | Research refresh, reconciliation, and retention |
| Embedding processing | Embedding generation and re-indexing |
| Orchestration events | Task completion, progress, and execution events |
| Recovery processing | Reconciliation and recoverable failed work |

These are logical categories, not a requirement to create every queue immediately.

### 6.1 Queue ownership

- Memory jobs are published under Memory Engine ownership.
- Research jobs are published under Research Engine ownership.
- Orchestration jobs are coordinated by the Orchestrator.
- Shared infrastructure jobs are owned by the relevant infrastructure component.

The Orchestrator may publish commands, but it must not take ownership of engine-specific business processing.

### 6.2 Queue isolation

Queues and routing rules must prevent:

- Unauthorized cross-user processing.
- Accidental execution by the wrong worker category.
- Mixing incompatible task types.
- Uncontrolled consumption of critical resources.

Worker authorization must be enforced independently of queue naming.

---

## 7. Standard Task Envelope

Every background task must carry a structured task envelope.

Conceptual fields:

| Field | Purpose |
|---|---|
| `message_id` | Unique message identifier |
| `execution_id` | Parent execution identifier |
| `task_id` | Logical task identifier |
| `user_id` | User ownership context, where applicable |
| `source_component` | Publishing component |
| `destination_component` | Intended processing component |
| `message_type` | Command, event, query, or response |
| `operation` | Requested operation |
| `created_at` | Message creation timestamp |
| `correlation_id` | End-to-end correlation identifier |
| `causation_id` | Identifier of the message or event that caused this message |
| `schema_version` | Envelope schema version |
| `payload_reference` | Reference to the task payload |
| `priority` | Scheduling priority |
| `idempotency_key` | Duplicate-processing protection |
| `trace_context` | Distributed tracing information |

The payload must contain only the information necessary for the operation.

Large documents, source content, and other large objects should be referenced through authorized storage locations rather than copied into broker messages.

### 7.1 Envelope validation

Before processing, workers must validate:

- Required fields.
- Schema version.
- Task identity.
- Operation compatibility.
- Ownership context.
- Payload reference.
- Idempotency information.
- Authorization requirements.

Invalid messages must not be processed as valid business tasks.

---

## 8. Task Execution Lifecycle

A background task follows a controlled lifecycle.

```text
Created
   |
   v
Validated
   |
   v
Queued
   |
   v
Dispatched
   |
   v
Running
   |
   +-------> Completed
   |
   +-------> Retrying
   |            |
   |            v
   |          Running
   |
   +-------> Failed
   |
   +-------> Cancellation Requested
                |
                v
             Cancelled
```

The exact lifecycle must remain consistent with the Orchestrator's established task states.

### 8.1 Important distinction

Celery's internal task state is not the authoritative Raven workflow state.

The Orchestrator's execution and task records remain authoritative for:

- Logical task identity.
- Dependencies.
- Overall execution progress.
- Retry history.
- Cancellation state.
- Completion and failure decisions.

Celery state may be used as operational information, but it must not independently determine the overall workflow outcome.

---

## 9. Task Publishing and Database Consistency

Publishing a message and updating PostgreSQL are separate operations.

A failure between these operations can produce inconsistent states.

For example:

- A task record is created but no message reaches RabbitMQ.
- A message reaches RabbitMQ but the publishing operation times out.
- A worker receives a task before the publishing component confirms the result.

Raven must handle these cases explicitly.

### 9.1 Recommended approach: Transactional Outbox

Use the transactional outbox pattern where reliable database-to-broker publication is required.

Conceptual flow:

1. Create or update the task record in PostgreSQL.
2. Insert an outbox event in the same database transaction.
3. Commit the transaction.
4. An outbox publisher reads pending events.
5. The publisher sends the event to RabbitMQ.
6. The publisher records successful publication.
7. Unpublished events remain eligible for retry.

This ensures that task state and the intent to publish are committed together.

### 9.2 Duplicate publication

A publisher may send a message successfully but fail before recording that publication was completed.

The same event may therefore be published again.

Workers must be designed to handle duplicate delivery safely.

### 9.3 Scope

The outbox pattern is an architectural recommendation for reliable publication.

Exact outbox tables, polling strategy, publisher concurrency, and cleanup policies will be finalized during implementation.

---

## 10. Worker Architecture

Workers execute tasks independently of request handling.

### 10.1 Worker responsibilities

Workers must:

- Consume authorized task messages.
- Validate task envelopes.
- Resolve the relevant task payload.
- Check execution and cancellation state.
- Execute the assigned operation.
- Record processing outcomes.
- Publish completion or failure events.
- Release temporary resources.
- Acknowledge or reject messages according to processing outcome.

### 10.2 Worker boundaries

Workers must not:

- Change another engine's authoritative records directly.
- Bypass engine-owned validation.
- Independently alter the Orchestrator's workflow plan.
- Treat message delivery as proof of task completion.
- Ignore user ownership boundaries.
- Report success before required persistence is confirmed.

### 10.3 Worker categories

Logical worker categories:

- Memory ingestion and extraction workers.
- Memory resolution workers.
- Memory maintenance workers.
- Research discovery workers.
- Research extraction and verification workers.
- Embedding workers.
- Reconciliation workers.

The initial deployment may combine several categories into a smaller number of worker processes.

Separation can increase as workload measurements justify it.

---

## 11. Delivery Guarantees and Idempotency

Raven must assume that messages can be delivered more than once.

The initial architecture should use at-least-once delivery where appropriate, combined with application-level idempotency.

Exactly-once execution must not be assumed.

### 11.1 Idempotency requirements

Each logical operation must have a stable idempotency identity.

Repeated execution with the same idempotency key must not create duplicate authoritative effects.

Examples:

- Duplicate memory ingestion must not create duplicate source records.
- Repeated embedding requests must not create uncontrolled active vectors.
- Repeated research persistence must not duplicate the same finding without reconciliation.
- Repeated completion events must not complete a task multiple times.
- Repeated deletion requests must not damage unrelated records.

### 11.2 Idempotency implementation principles

- Use stable task and operation identifiers.
- Persist operation outcomes.
- Validate current record versions.
- Use database constraints where appropriate.
- Make state transitions conditional.
- Record duplicate execution attempts.
- Keep external side effects separately traceable.

### 11.3 Acknowledgement policy

A worker must not acknowledge a message as successfully processed before the required business outcome is safely recorded.

If processing fails before a safe outcome is committed, the message must follow the configured retry or failure path.

Acknowledgement timing must be designed carefully to avoid both message loss and uncontrolled duplicate work.

---

## 12. Retry and Failure Handling

Retries are required for transient failures, but they must be bounded.

### 12.1 Retryable failures

Examples:

- Temporary database connection failures.
- Temporary broker or network issues.
- Rate limiting from external sources.
- Temporary storage unavailability.
- Temporary model inference failures.

### 12.2 Non-retryable failures

Examples:

- Invalid task schema.
- Unauthorized operation.
- Invalid ownership context.
- Unsupported operation.
- Permanently invalid input.
- Business rule rejection.

Non-retryable failures should be recorded and routed to an appropriate failure outcome rather than repeatedly executed.

### 12.3 Retry policy

Use:

- Bounded retries.
- Exponential backoff where appropriate.
- Jitter to reduce synchronized retry spikes.
- Error classification.
- Maximum retry limits.
- Explicit terminal failure states.

Retry count and timing must be configurable by task category.

No universal retry count or delay is finalized here.

### 12.4 Retry safety

Before retrying, workers must determine whether the previous attempt may already have committed its business result.

A timeout does not prove that the operation failed.

The worker or Orchestrator must reconcile the task using its stable task and operation identifiers before repeating potentially non-idempotent work.

---

## 13. Dead-Letter Queues

Messages that cannot be processed successfully after their permitted recovery attempts should be routed to an appropriate dead-letter path.

### 13.1 Dead-letter responsibilities

Dead-letter handling must preserve:

- Original message identity.
- Task and execution references.
- Failure category.
- Attempt count.
- Last error information, with sensitive data excluded.
- Original creation timestamp.
- Correlation and trace identifiers.

### 13.2 Recovery process

Dead-letter messages must be:

1. Identified.
2. Classified.
3. Investigated.
4. Corrected or declared unrecoverable.
5. Replayed only through a controlled process when appropriate.

Blindly replaying all dead-letter messages is not acceptable.

Replay must respect idempotency, current ownership, deletion state, and task validity.

---

## 14. Scheduling and Priority Management

The Orchestrator owns workflow scheduling and task priority.

Celery and RabbitMQ provide execution and transport mechanisms.

### 14.1 Priority factors

Scheduling may consider:

- Task importance.
- User-requested urgency.
- Dependency readiness.
- Expected value.
- Resource cost.
- Current worker capacity.
- Execution deadlines.
- Correctness criticality.

### 14.2 Resource allocation

The system should support:

- Configurable worker concurrency.
- Separate handling for resource-intensive tasks.
- Capacity limits.
- Protection for critical operations.
- Fairness between workloads.
- Backpressure when queues grow.
- Controlled processing of large backfills.

### 14.3 Priority safeguards

- Low-priority work must not permanently starve.
- High-priority work must not bypass authorization or validation.
- Maintenance jobs must not consume all capacity.
- Resource limits must not cause silent task abandonment.

Exact priority values and worker limits will be determined through evaluation.

---

## 15. Cancellation and Timeout Management

Cancellation is a workflow-level operation coordinated by the Orchestrator.

### 15.1 Cancellation flow

1. Receive cancellation request.
2. Validate authorization.
3. Update the execution state.
4. Mark pending tasks as no longer eligible to start.
5. Signal running tasks to stop where possible.
6. Allow cooperative cleanup.
7. Preserve already completed work according to retention policy.
8. Record final cancellation status.

### 15.2 Cooperative cancellation

Workers should periodically check cancellation state during long-running operations where practical.

Cancellation must not be treated as an ordinary failure.

### 15.3 Timeouts

Different operations may have different timeout policies.

A timeout means the expected completion window was exceeded; it does not necessarily mean the underlying operation failed.

When a timeout occurs:

- Check task and execution state.
- Reconcile possible completion.
- Determine whether the worker is still active.
- Avoid duplicate side effects.
- Apply recovery policy.
- Record the timeout and resulting decision.

### 15.4 Worker termination

If a worker terminates unexpectedly:

- Unacknowledged messages may be redelivered according to broker configuration.
- The task must be reconciled with its authoritative state.
- Partial work must be handled according to checkpoint and idempotency rules.
- Completed business results must not be discarded or duplicated.

---

## 16. Progress and Event Reporting

Workers must provide structured progress information for long-running tasks where useful.

Progress events may include:

- Task started.
- Processing stage changed.
- Progress checkpoint recorded.
- Partial result persisted.
- Retry scheduled.
- Task completed.
- Task failed.
- Cancellation acknowledged.

### 16.1 Progress rules

- Progress must reflect actual processing.
- Percentages must not be invented when progress cannot be measured.
- Events must include execution and task references.
- Repeated events must be safe to process.
- Progress reporting must not become a source of authoritative business data.
- Sensitive content must not be exposed in progress messages.

The Orchestrator aggregates progress into the user-visible execution state.

---

## 17. Concurrency and Resource Isolation

Background execution must be controlled to prevent one workload from affecting the reliability of others.

### 17.1 Concurrency controls

Raven should support:

- Worker concurrency limits.
- Queue-specific capacity.
- Per-operation resource budgets.
- Database connection limits.
- External request rate limits.
- Backpressure.
- Controlled batch sizes.

### 17.2 Isolation requirements

- User data must remain isolated.
- Task context must be scoped to the correct execution.
- Worker credentials must follow least privilege.
- Large jobs must not exhaust shared resources.
- Sensitive operations must use stricter concurrency and integrity controls where required.

### 17.3 Database transaction policy

Workers should use short-lived database transactions.

Long-running research, extraction, and embedding operations must not hold database transactions open while waiting for external operations or expensive computation.

---

## 18. Security

Background messages and workers are part of Raven's trusted execution infrastructure, but message content and referenced external data must still be treated as untrusted input.

Requirements:

- Authenticate internal publishing and consuming components.
- Authorize operations independently of message routing.
- Validate user and ownership context.
- Restrict worker database permissions.
- Protect broker credentials.
- Use secure transport and protected connections.
- Avoid storing secrets in task payloads.
- Avoid sensitive content in logs and error messages.
- Validate payload references before retrieving content.
- Prevent unauthorized task replay.
- Apply retention policies to queued and dead-letter messages.

A message arriving from RabbitMQ is not automatically authorized to modify a user's data.

---

## 19. Monitoring and Observability

The background processing infrastructure must expose operational health and execution visibility.

### 19.1 Broker metrics

- Queue depth.
- Message delivery rate.
- Unacknowledged messages.
- Consumer availability.
- Message redelivery rate.
- Dead-letter volume.
- Broker resource utilization.

### 19.2 Worker metrics

- Active workers.
- Task execution duration.
- Task success rate.
- Task failure rate.
- Retry rate.
- Worker availability.
- Resource utilization.
- Task processing throughput.

### 19.3 Workflow metrics

- Execution completion time.
- Execution failure rate.
- Queue waiting time.
- Cancellation success.
- Dependency waiting time.
- Partial completion rate.
- Recovery success rate.

### 19.4 Traceability

Every task should be traceable through:

- Execution ID.
- Task ID.
- Message ID.
- Correlation ID.
- Causation ID.
- Worker identity.
- Processing attempt.
- Relevant timestamps.

Use the shared OpenTelemetry architecture for distributed tracing where applicable.

---

## 20. Testing Requirements

The infrastructure must eventually be tested for:

### Message delivery

- Duplicate message delivery.
- Delayed message delivery.
- Invalid messages.
- Message acknowledgement failures.
- Broker restart and recovery.

### Worker behavior

- Worker crash during processing.
- Worker restart.
- Database unavailability.
- Storage unavailability.
- Model inference failure.
- Long-running task timeout.

### Reliability

- Retry correctness.
- Idempotent execution.
- Dead-letter routing.
- Controlled replay.
- Outbox recovery.
- Partial task completion.
- Cancellation during execution.

### Security

- Unauthorized task publication.
- Invalid user ownership.
- Unauthorized payload access.
- Cross-user isolation.
- Credential exposure prevention.

### Performance

- Queue throughput.
- Queue latency.
- Worker concurrency.
- Resource contention.
- Large document processing.
- Backfill behavior.

Numerical acceptance targets will be established during Phase 12 — Testing & Evaluation.

---

## 21. Finalized Decisions

The following architectural decisions are established:

1. RabbitMQ is the initial message broker.
2. Celery is the initial background task framework.
3. PostgreSQL remains the authoritative workflow and business-state store.
4. The Orchestrator owns workflow coordination and execution state.
5. Engines own their domain-specific background processing.
6. Raven uses hybrid synchronous and asynchronous processing.
7. Background tasks use structured, versioned message envelopes.
8. At-least-once delivery with application-level idempotency is the initial reliability model where appropriate.
9. Exactly-once execution is not assumed.
10. Transactional outbox is the recommended approach for reliable database-to-broker publication.
11. Retries are bounded and classified.
12. Dead-letter handling is controlled and auditable.
13. Cancellation is cooperative and coordinated by the Orchestrator.
14. Workers must not bypass engine ownership boundaries.
15. Queue and worker behavior must be observable and traceable.
16. Quality, data integrity, and security take priority over throughput.

---

## 22. Deferred Decisions

The following decisions require implementation evidence or workload evaluation:

- Exact queue names and routing keys.
- Queue count and physical topology.
- Celery worker deployment structure.
- Worker concurrency values.
- Queue priority configuration.
- Retry counts and delays.
- Dead-letter retention.
- Outbox polling and cleanup strategy.
- Broker durability and replication configuration.
- Task payload size limits.
- Scheduling and rate-limiting configuration.
- Production resource budgets.
- Broker and worker deployment topology.

All deferred decisions must remain consistent with the ownership, idempotency, security, and reliability principles in this document.

---

## 23. Completion Criteria

Phase 7.4 is architecturally specified when:

- RabbitMQ and Celery responsibilities are defined.
- Synchronous and asynchronous execution boundaries are documented.
- Queue ownership is established.
- Message envelopes and task lifecycle are specified.
- Publishing consistency is addressed.
- Worker boundaries are documented.
- Delivery and idempotency policies are defined.
- Retry and dead-letter behavior is specified.
- Cancellation and timeout behavior are defined.
- Scheduling and resource isolation requirements are documented.
- Security and observability requirements are covered.

**Status:** Architecture specification complete.

**Important:** This document does not claim that RabbitMQ, Celery, queues, workers, outbox tables, or background processing tests have been implemented or deployed.

---

## 24. Next Phase

**Phase 7.5 — NLP & Machine Learning Stack**

This will define Raven's conventional NLP and non-generative ML architecture, including spaCy, scikit-learn, sentence-transformers, feature extraction, classification, entity recognition, model evaluation, and inference boundaries.
