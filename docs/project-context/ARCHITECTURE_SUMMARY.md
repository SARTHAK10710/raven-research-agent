# Architecture Summary

An orientation map, not a specification. For anything you will build against, read the linked source. Permanent rules are in [`.claude/rules/architecture.md`](../../.claude/rules/architecture.md).

## Overall system

Four conceptual layers ([phase-01](../architecture/phase-01-overall-architecture.md)):

1. **Entry Layer** — request intake, authentication context, validation, cancellation intake, response delivery.
2. **Agent Orchestrator** — coordination.
3. **Specialized Engines** — Memory and Research.
4. **Shared Infrastructure** — common technical capabilities.

Together these are the **three primary engines** (Memory, Research, Orchestrator) plus Shared Infrastructure. The layers are ownership boundaries. Deployment is a **modular monolith with independently executable Celery workers** ([7.1 §2](../technical-decisions/01-baseline-technology-stack.md), [7.8 §3](../technical-decisions/08-deployment-and-environment-architecture.md)).

Design preferences (optimization : performance): Memory **70:30**, Research **55:45**, Orchestrator **45:55**. These are preferences, not SLOs.

## Memory Engine

[phase-02](../architecture/phase-02-memory-engine.md) · data [5.4](../data-models/phase-05-memory-engine-models.md) · algorithms [memory/](../algorithms/Readme.md) · plans [Phase 8](../implementation-plans/Phase-08-memory-engine/Readme.md)

Owns two **separate logical domains** that share infrastructure but not records, models, retrieval workflows or lifecycle.

### Personal Memory

Lifecycle: Ingestion → Extraction → Evaluation → Resolution → Storage → Retrieval → Consolidation (+ Forgetting).

- Key records: memory sources, memory candidates, atomic memories (mutable current value plus immutable revisions), entities and aliases, relationships, episodes, derived profiles, provenance, and embedding metadata.
- Only validated, resolved candidates become authoritative memories. Profiles are derived views.
- Duplicates, progressions and contradictions are classified. History is never silently overwritten.

### Document Intelligence

Pipeline: Registration → Parsing → Structure Extraction → Chunking → Embedding → Indexing → Retrieval → Evidence Selection → Answer Assembly ([memory/05](../algorithms/memory/05-document-processing-and-rag.md), [plan 8.12](../implementation-plans/Phase-08-memory-engine/12-document-rag-pipeline.md)).

- Key records: document, document version, extracted representation, chunk, chunk location/provenance, document embedding metadata, and processing operation (5.4 amendment).
- Formats: PDF, DOCX and TXT. No OCR.
- Answers are extractive and deterministic, with citations to document, version, chunk and page/section.
- Chunks are never personal memories. Document facts reach personal memory only through the authorized candidate → resolution workflow.

## Research Engine

[phase-03](../architecture/phase-03-research-engine.md) · data [5.5](../data-models/phase-05-research-engine-models.md) · algorithms `research/`

- **External research:** query understanding, discovery, content extraction, fact normalization, source evaluation and adaptive verification, research sessions with incremental snapshots, retrieval and comparison.
- Source reliability is distinct from fact confidence. Repeated copies are not corroboration. Missing evidence stays missing.
- Not part of Phase 8.

## Agent Orchestrator

[phase-04](../architecture/phase-04-agent-orchestrator.md) · data [5.6](../data-models/phase-05-orchestrator-models.md) · algorithms `orchestrator/`

- Intent → planning → routing → execution coordination → state and recovery → evidence-aware response assembly.
- Routing: historical → Memory; current external → Research; both → Memory first, then targeted Research. It decides when to use personal memory, documents or both.
- Owns execution and task state (pending, running, completed, failed, retrying, skipped, cancellation_requested, cancelled). Cancellation is cooperative and idempotent.
- Not part of Phase 8.

## Shared Infrastructure

Data [5.7](../data-models/phase-05-shared-infrastructure-models.md) · tech [7.2](../technical-decisions/02-database-and-storage-architecture.md), [7.4](../technical-decisions/04-background-processing-and-messaging.md), [7.7](../technical-decisions/07-observability-and-testing-infrastructure.md), [7.8](../technical-decisions/08-deployment-and-environment-architecture.md)

- Provides: PostgreSQL (one deployment, schemas `memory`, `research`, `orchestrator`, `shared`), pgvector, S3-compatible object storage, RabbitMQ and Celery, identity and authorization, logging, metrics, tracing, configuration and secrets, backup and recovery.
- Owns identity, authorization policy, shared configuration and infrastructure audit records. Never engine business data or logic.

## Engine communication

- Hybrid: synchronous REST/OpenAPI (FastAPI, `/api/v1/`) for immediate work; asynchronous versioned message envelopes over RabbitMQ/Celery for long-running work.
- At-least-once delivery with application-level idempotency, plus a transactional outbox for database-to-broker publishing ([7.4](../technical-decisions/04-background-processing-and-messaging.md)).
- Correlation identifiers: `request_id`, `execution_id`, `task_id`, `message_id`, `correlation_id`, `causation_id`, `trace_id`, `span_id` ([7.7 §5](../technical-decisions/07-observability-and-testing-infrastructure.md)).
- Cross-engine access uses typed references and authorized interfaces. Memory and Research never orchestrate each other.

## Ownership boundaries

| Data | Owner |
|---|---|
| Personal memory records and their embeddings | Memory Engine |
| Document Intelligence records, chunks and embeddings | Memory Engine |
| Research sessions, findings, evidence, snapshots | Research Engine |
| Executions, tasks, dependencies, checkpoints | Agent Orchestrator |
| Identity, authorization, shared config, infrastructure audit | Shared Infrastructure |

The owner is the only writer. Derived data belongs to the component that generates it.
