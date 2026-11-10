# Phase 7.7 — Observability & Testing Infrastructure

## 1. Purpose

This document defines Raven's observability, monitoring, logging, alerting, and testing architecture.

It establishes how Raven will:

- Understand internal system behavior.
- Trace requests across components.
- Monitor engine and worker health.
- Detect processing failures.
- Measure retrieval and processing quality.
- Validate data integrity.
- Test asynchronous workflows.
- Detect performance regressions.
- Evaluate reliability and security.

The objective is to make Raven observable, testable, and maintainable as its engines and infrastructure become more complex.

---

## 2. Architectural Principles

Raven follows these principles:

1. Every important operation must be traceable.
2. Logs, metrics, and traces serve different purposes.
3. Observability must cover all three engines and shared infrastructure.
4. Errors must not disappear silently.
5. Monitoring must distinguish infrastructure health from business correctness.
6. Testing must validate behavior, not merely code execution.
7. Data integrity and privacy must be included in testing.
8. Performance optimization must be driven by measured evidence.
9. Evaluation datasets must be versioned and reproducible.
10. Production observability must avoid exposing sensitive user information.
11. Critical workflows must support failure injection and recovery testing.
12. Correctness and reliability take priority over raw throughput.

---

## 3. Observability Technology Stack

The initial recommended stack is:

| Responsibility | Technology |
|---|---|
| Instrumentation | OpenTelemetry |
| Metrics collection | Prometheus |
| Metrics visualization | Grafana |
| Structured logging | Python logging with structured output |
| Distributed tracing | OpenTelemetry tracing |
| Testing framework | pytest |
| API testing | HTTPX |
| Coverage | pytest-cov |
| Code formatting and linting | Ruff |
| Static type checking | mypy, strict mode ([7.1 §22](01-baseline-technology-stack.md)) |
| Dependency management | uv |

These technologies provide the initial baseline. Exact deployment and storage configurations will be finalized during implementation.

### 3.1 OpenTelemetry

OpenTelemetry provides standardized instrumentation for:

- Request tracing.
- Internal operation tracing.
- Database operations.
- Background task execution.
- External service calls.
- Distributed context propagation.

### 3.2 Prometheus

Prometheus collects operational metrics such as:

- Request rates.
- Error rates.
- Latency.
- Queue depth.
- Worker utilization.
- Database connection usage.
- Processing throughput.

### 3.3 Grafana

Grafana provides dashboards for:

- Overall system health.
- Engine-specific health.
- Queue and worker health.
- API performance.
- Retrieval quality.
- Error and recovery trends.

### 3.4 pytest

pytest is the primary testing framework for:

- Unit tests.
- Integration tests.
- API tests.
- Workflow tests.
- Regression tests.
- Data integrity tests.

---

## 4. Three Pillars of Observability

Raven uses three complementary observability mechanisms.

### 4.1 Logs

Logs describe individual events and processing outcomes.

Examples:

- Request received.
- Task dispatched.
- Memory extraction completed.
- Research source failed to load.
- Embedding generation failed.
- Deletion propagation completed.
- Database transaction rolled back.

Logs help explain what happened.

### 4.2 Metrics

Metrics represent numerical measurements over time.

Examples:

- Average API latency.
- Research completion rate.
- Memory extraction failure rate.
- Queue waiting time.
- Embedding generation duration.
- Retrieval precision.
- Worker utilization.

Metrics help identify patterns and operational problems.

### 4.3 Traces

Traces follow a request or operation across multiple components.

For example:

```text
User Request
    |
    v
FastAPI
    |
    v
Agent Orchestrator
    |
    +------> Memory Engine
    |             |
    |             v
    |         PostgreSQL
    |
    +------> Research Engine
                  |
                  v
              RabbitMQ
                  |
                  v
               Worker
                  |
                  v
              PostgreSQL
```

A distributed trace should allow Raven to identify:

- Where processing started.
- Which components participated.
- How long each operation took.
- Where a failure occurred.
- Which execution and task caused the operation.

Logs, metrics, and traces should use consistent identifiers wherever possible.

---

## 5. Correlation and Traceability

Every important operation should carry traceable identifiers.

| Identifier | Purpose |
|---|---|
| `request_id` | Identifies an incoming API request |
| `execution_id` | Identifies an Orchestrator execution |
| `task_id` | Identifies a logical task |
| `message_id` | Identifies an internal message |
| `correlation_id` | Connects related operations |
| `causation_id` | Identifies the event that caused another event |
| `trace_id` | Identifies a distributed trace |
| `span_id` | Identifies an individual trace operation |

### 5.1 Trace propagation

Trace context should propagate across:

- FastAPI.
- Agent Orchestrator.
- Memory Engine.
- Research Engine.
- RabbitMQ messages.
- Celery workers.
- Database operations.
- External service calls.

### 5.2 Trace boundaries

A long-running research execution may span multiple worker processes and extended periods.

Raven should preserve logical execution and correlation identifiers even when individual distributed traces cannot remain open for the entire workflow.

Do not keep an active tracing span open indefinitely for a long-running workflow.

Instead, use linked traces and persistent execution records.

---

## 6. Logging Architecture

Raven should use structured application logging.

### 6.1 Log structure

Conceptual fields:

| Field | Purpose |
|---|---|
| `timestamp` | Event timestamp |
| `level` | Severity |
| `service` | Service or component |
| `environment` | Execution environment |
| `event_type` | Event category |
| `message` | Human-readable summary |
| `request_id` | Request reference |
| `execution_id` | Execution reference |
| `task_id` | Task reference |
| `trace_id` | Trace reference |
| `user_scope` | Non-sensitive ownership reference where appropriate |
| `duration_ms` | Processing duration where relevant |
| `error_code` | Structured error category |

This is a conceptual logging contract, not a finalized schema.

### 6.2 Log levels

- `DEBUG`: Detailed development diagnostics.
- `INFO`: Normal processing events.
- `WARNING`: Recoverable problems or unusual conditions.
- `ERROR`: Failed operations requiring attention.
- `CRITICAL`: Severe failures affecting system integrity or availability.

### 6.3 Logging rules

- Use structured logs rather than relying only on free-form messages.
- Include correlation identifiers.
- Record significant state transitions.
- Avoid duplicate noisy logs.
- Avoid logging entire request bodies by default.
- Never log passwords, access tokens, API keys, or secrets.
- Avoid unnecessary personal memory content.
- Redact sensitive values where logging is necessary.
- Apply retention and access controls.

### 6.4 Business and infrastructure events

Engine-specific business events remain owned by their respective engines.

Infrastructure logs and security events remain owned by Shared Infrastructure.

Operational logs must not replace authoritative business records or audit history.

---

## 7. Metrics Architecture

Metrics must cover infrastructure health, application behavior, and engine-specific quality.

### 7.1 API metrics

- Request count.
- Request rate.
- Response latency.
- Error rate.
- Status code distribution.
- Authentication failure rate.
- Rate-limit events.

### 7.2 Orchestrator metrics

- Execution count.
- Execution completion rate.
- Execution failure rate.
- Average execution duration.
- Task count per execution.
- Retry rate.
- Cancellation rate.
- Partial completion rate.
- Dependency waiting time.
- Resource allocation.

### 7.3 Memory Engine metrics

- Ingestion volume.
- Relevance gate outcomes.
- Extraction success rate.
- Candidate generation rate.
- Candidate promotion rate.
- Entity resolution accuracy.
- Duplicate detection performance.
- Retrieval latency.
- Retrieval precision and recall.
- Consolidation success rate.
- Deletion propagation success rate.

### 7.4 Research Engine metrics

- Research requests.
- Discovery success rate.
- Source accessibility rate.
- Extraction success rate.
- Verification outcomes.
- Source corroboration coverage.
- Research completion rate.
- Research refresh success rate.
- Retrieval latency.
- Finding relevance.
- Incomplete research rate.

### 7.5 Background processing metrics

- Queue depth.
- Queue waiting time.
- Message redelivery rate.
- Task execution duration.
- Worker availability.
- Retry count.
- Dead-letter volume.
- Outbox backlog.

### 7.6 Database and infrastructure metrics

- Database connection usage.
- Query latency.
- Transaction failures.
- Storage utilization.
- Vector index size.
- Object storage failures.
- CPU and memory usage.
- Disk usage.

### 7.7 Metric cardinality

Avoid high-cardinality metric labels such as:

- Raw user IDs.
- Full URLs containing unique parameters.
- Arbitrary memory content.
- Request payloads.
- Unbounded task identifiers.

Use traces and logs for detailed individual-operation investigation.

---

## 8. Dashboards

Raven should maintain logically separated dashboards.

### 8.1 System Overview

Displays:

- API availability.
- Overall error rate.
- Request latency.
- Active executions.
- Queue health.
- Worker health.
- Database health.
- Resource utilization.

### 8.2 Memory Engine Dashboard

Displays:

- Ingestion throughput.
- Extraction outcomes.
- Candidate evaluation.
- Resolution outcomes.
- Retrieval performance.
- Consolidation health.
- Deletion propagation status.

### 8.3 Research Engine Dashboard

Displays:

- Research request volume.
- Source discovery success.
- Extraction failures.
- Verification outcomes.
- Research duration.
- Refresh status.
- Retrieval quality.

### 8.4 Orchestrator Dashboard

Displays:

- Active executions.
- Task status distribution.
- Execution duration.
- Retry and recovery rates.
- Cancellation status.
- Partial completion.
- Dependency bottlenecks.

### 8.5 Infrastructure Dashboard

Displays:

- PostgreSQL health.
- RabbitMQ health.
- Celery worker health.
- Vector storage health.
- Object storage health.
- CPU, memory, and disk utilization.

---

## 9. Alerting Architecture

Monitoring without actionable alerts is insufficient.

Raven should define alerts for conditions that require investigation or intervention.

### 9.1 Availability alerts

Examples:

- API unavailable.
- Database unavailable.
- RabbitMQ unavailable.
- Critical worker pool unavailable.
- Storage unavailable.

### 9.2 Reliability alerts

Examples:

- Sustained task failure increase.
- Growing dead-letter queue.
- Stuck executions.
- Outbox backlog growth.
- Repeated worker crashes.
- Failed deletion propagation.
- Reconciliation failures.

### 9.3 Performance alerts

Examples:

- Sustained API latency increase.
- Excessive queue waiting time.
- Database connection exhaustion.
- High resource utilization.
- Retrieval latency regression.

### 9.4 Data integrity alerts

Examples:

- Orphaned embeddings.
- Deleted memories still searchable.
- Invalid cross-engine references.
- Inconsistent task states.
- Failed migration validation.
- Unauthorized access attempts.

### 9.5 Alert design

Each alert should define:

- Alert name.
- Trigger condition.
- Severity.
- Responsible component.
- Investigation guidance.
- Recovery or escalation procedure.

Thresholds must be established from measured baselines and operational requirements, not arbitrary assumptions.

---

## 10. Testing Architecture

Raven uses a layered testing strategy.

### Layer 1 — Unit Testing

Tests individual functions and modules.

Examples:

- Input normalization.
- Relevance scoring.
- Entity matching.
- Confidence calculation.
- Ranking functions.
- Task state transitions.
- Temporal parsing.

### Layer 2 — Component Testing

Tests individual engine components with controlled dependencies.

Examples:

- Memory extraction pipeline.
- Memory resolution.
- Research extraction.
- Research verification.
- Orchestrator planning.

### Layer 3 — Integration Testing

Tests communication between real application components and infrastructure dependencies.

Examples:

- FastAPI and PostgreSQL.
- SQLAlchemy persistence.
- RabbitMQ and Celery.
- Memory Engine and vector storage.
- Research Engine and object storage.

### Layer 4 — End-to-End Testing

Tests complete workflows from user request to final response.

Examples:

- Store and retrieve a memory.
- Correct an existing memory.
- Research a current topic.
- Refresh historical research.
- Perform a multi-engine request.
- Cancel a running execution.

### Layer 5 — Quality and Evaluation Testing

Measures semantic and factual performance.

Examples:

- Memory retrieval relevance.
- Extraction correctness.
- Entity resolution accuracy.
- Research evidence quality.
- Source verification.
- Conflict preservation.

### Layer 6 — Reliability and Security Testing

Tests behavior under failures and adversarial conditions.

Examples:

- Worker crashes.
- Database failure.
- Duplicate message delivery.
- Unauthorized access.
- Cross-user data isolation.
- Deletion recovery.
- Invalid external content.

---

## 11. Testing Technology Stack

The initial testing stack is:

| Technology | Responsibility |
|---|---|
| pytest | Primary test framework |
| HTTPX | API testing |
| pytest-cov | Code coverage |
| Ruff | Linting and formatting |
| mypy (strict mode) | Static type checking ([7.1 §22](01-baseline-technology-stack.md)) |
| Docker Compose | Local integration dependencies |
| PostgreSQL test database | Database integration tests |
| RabbitMQ test instance | Messaging integration tests |

The exact CI provider and deployment pipeline are deferred to implementation.

---

## 12. Test Data and Fixtures

Raven must use controlled test data.

### 12.1 Test data categories

Memory Engine:

- Explicit facts.
- Inferred statements.
- Contradictory facts.
- Corrections.
- Duplicate memories.
- Ambiguous entities.
- Historical facts.
- Deletion scenarios.

Research Engine:

- Reliable sources.
- Low-quality sources.
- Conflicting sources.
- Historical information.
- Current information.
- Duplicate and syndicated content.
- Missing evidence.
- Inaccessible sources.

Orchestrator:

- Simple requests.
- Multi-intent requests.
- Ambiguous requests.
- Sequential workflows.
- Parallel workflows.
- Partial failures.
- Cancellation scenarios.

### 12.2 Test data governance

- Prefer synthetic data for general testing.
- Do not use real personal data unnecessarily.
- Keep evaluation datasets versioned.
- Document annotation rules.
- Ensure repeatable test execution.
- Separate test data from production data.

---

## 13. Quality Evaluation and Benchmarking

Passing unit tests does not prove that Raven retrieves or interprets information correctly.

Raven therefore needs separate quality evaluation.

### 13.1 Memory quality

Evaluate:

- Atomic fact extraction precision and recall.
- Explicit versus inferred classification.
- Entity resolution precision.
- False merge rate.
- Duplicate detection quality.
- Contradiction detection quality.
- Retrieval precision@K and recall@K.
- Historical retrieval correctness.
- Deletion propagation correctness.

### 13.2 Research quality

Evaluate:

- Query understanding accuracy.
- Source discovery relevance.
- Extraction accuracy.
- Evidence traceability.
- Source reliability assessment.
- Claim verification accuracy.
- Contradiction preservation.
- Research retrieval quality.
- Context compatibility in comparisons.

### 13.3 Orchestrator quality

Evaluate:

- Intent classification accuracy.
- Routing accuracy.
- Task decomposition quality.
- Dependency correctness.
- Execution completion.
- Failure recovery.
- Cancellation correctness.
- Response evidence preservation.

### 13.4 Benchmark governance

Each benchmark should specify:

- Dataset version.
- Evaluation objective.
- Expected outputs.
- Scoring methodology.
- Model or algorithm version.
- Evaluation timestamp.
- Known limitations.

Numerical quality targets will be established in Phase 12.

---

## 14. Reliability and Failure Injection Testing

Raven must test how the system behaves when components fail.

### 14.1 Infrastructure failures

- PostgreSQL unavailable.
- RabbitMQ unavailable.
- Object storage unavailable.
- Vector search unavailable.
- Worker process terminated.
- Network interruption.

### 14.2 Application failures

- Invalid task payload.
- Extraction exception.
- Model inference failure.
- Database transaction rollback.
- Partial research completion.
- Invalid engine response.

### 14.3 Consistency failures

- Duplicate message delivery.
- Timeout after successful persistence.
- Outbox publication failure.
- Stale embedding.
- Orphaned derived record.
- Partial deletion propagation.

### 14.4 Recovery expectations

Tests must verify that Raven:

- Preserves completed work.
- Does not report false success.
- Avoids duplicate authoritative effects.
- Reconciles uncertain outcomes.
- Maintains user isolation.
- Recovers through controlled retries.
- Records unresolved failures.

---

## 15. Security and Privacy Testing

Security tests must cover:

- Authentication validation.
- Authorization boundaries.
- Cross-user isolation.
- Privileged operations.
- File upload validation.
- Sensitive log exposure.
- Secret handling.
- Unauthorized task replay.
- External content handling.
- Deletion propagation.
- Backup restoration behavior.

Privacy testing must include derived data such as embeddings, caches, indexes, and temporary processing copies.

A deletion test is incomplete if the authoritative record is deleted but an accessible derived copy remains.

---

## 16. Performance and Load Testing

Performance testing should measure:

- API throughput.
- API latency.
- Memory ingestion throughput.
- Research processing duration.
- Embedding generation throughput.
- Vector retrieval latency.
- Queue processing throughput.
- Database query latency.
- Concurrent execution behavior.
- Resource consumption.

### 16.1 Workload categories

Evaluate:

- Lightweight requests.
- Large document ingestion.
- Complex research workflows.
- High-volume memory retrieval.
- Concurrent user workloads.
- Background maintenance.
- Bulk embedding migration.

### 16.2 Performance policy

- Establish realistic workloads.
- Measure before optimizing.
- Identify bottlenecks.
- Preserve quality during optimization.
- Compare results across versions.
- Avoid optimizing isolated components at the expense of end-to-end performance.

---

## 17. Continuous Integration Quality Gates

Every implementation change should pass appropriate automated checks before being accepted.

Recommended quality gates:

1. Formatting and linting.
2. Static type checking.
3. Unit tests.
4. Relevant component tests.
5. Integration tests.
6. Security checks.
7. Regression tests.
8. Quality evaluation for affected algorithms.
9. Migration validation where database changes occur.

### 17.1 Change impact

Testing scope should depend on the change.

For example:

- A Memory Engine extraction change requires memory extraction regression tests.
- An embedding model change requires retrieval evaluation and migration checks.
- An API contract change requires contract and compatibility tests.
- A deletion workflow change requires full deletion propagation tests.

### 17.2 Quality gates

Critical correctness, privacy, and security failures must block release.

Code coverage alone must never be treated as proof of correctness.

---

## 18. Observability and Privacy

Observability data can itself contain sensitive information.

Requirements:

- Do not log raw personal memory content by default.
- Avoid sensitive text in metric labels.
- Restrict trace access.
- Redact secrets and tokens.
- Apply retention policies to logs and traces.
- Protect dashboards and monitoring endpoints.
- Separate operational metadata from business content.
- Ensure debugging access follows authorization policies.

Operational visibility must not become an alternative route to accessing private user data.

---

## 19. Finalized Decisions

The following architectural decisions are established:

1. OpenTelemetry is the instrumentation baseline.
2. Prometheus is the initial metrics collection technology.
3. Grafana is the initial dashboard and visualization technology.
4. Structured application logging is required.
5. Distributed tracing must cover cross-component execution.
6. pytest is the primary testing framework.
7. HTTPX supports API testing.
8. pytest-cov supports coverage measurement.
9. Ruff provides linting and formatting.
10. mypy in strict mode provides static type checking (selected in [7.1 §22](01-baseline-technology-stack.md)).
11. Testing uses unit, component, integration, end-to-end, quality, and reliability layers.
12. Raven requires separate algorithm and retrieval quality evaluation.
13. Failure injection is required for critical workflows.
14. Security and privacy testing must include derived data.
15. CI quality gates must block critical correctness, security, and integrity failures.
16. Observability data must follow privacy and retention requirements.

---

## 20. Deferred Decisions

The following decisions require implementation and operational evaluation:

- Metrics retention and storage configuration.
- Log aggregation backend.
- Trace storage backend.
- Dashboard organization and access policy.
- Alert delivery mechanism.
- Production alert thresholds.
- Test environment topology.
- CI provider.
- Coverage thresholds.
- Benchmark dataset sizes.
- Quality acceptance thresholds.
- Load-testing tooling.
- Security scanning tooling.
- Production monitoring deployment.

These decisions must remain consistent with Raven's quality-first and privacy-first principles.

---

## 21. Completion Criteria

Phase 7.7 is architecturally specified when:

- Logs, metrics, and traces are defined.
- Correlation and trace propagation are established.
- Engine-specific monitoring is documented.
- Dashboards and alert categories are specified.
- Testing layers and tools are selected.
- Evaluation datasets and quality metrics are defined.
- Failure injection and recovery testing are covered.
- Security and privacy testing are documented.
- CI quality gates are established.

**Status:** Architecture specification complete.

**Important:** This document does not claim that monitoring dashboards, alert rules, test suites, CI pipelines, or benchmark datasets have been implemented or deployed.

---

## 22. Next Phase

**Phase 7.8 — Deployment & Environment Architecture**

This will define development, testing, staging, and production environments; Docker deployment; configuration management; secrets; migrations; release strategy; backup and recovery; and deployment safety.
