# Rule: Raven Architecture

Permanent architectural rules. Sources: [`PROJECT_ARCHITECTURE.md`](../../PROJECT_ARCHITECTURE.md), [`docs/architecture/`](../../docs/architecture/Readme.md), [7.1 baseline](../../docs/technical-decisions/01-baseline-technology-stack.md). Changing any rule here requires explicit user approval and an update to the source documents first.

## Engines and ownership

| Component | Owns | Must not |
|---|---|---|
| Memory Engine | Personal Memory and Document Intelligence: ingestion, extraction, entities, resolution, storage, retrieval, consolidation, documents, deletion | Orchestrate other engines or perform external research |
| Research Engine | External discovery, extraction, normalization, source verification, research sessions and snapshots | Own personal memory or uploaded-document records |
| Agent Orchestrator | Intent, planning, routing, execution state, cross-engine coordination, recovery, response assembly | Extract memories, discover sources or verify facts itself |
| Shared Infrastructure | Database, object storage, messaging, identity, logging, monitoring, deployment | Contain engine-specific business logic or own engine business data |

- Each engine owns its business logic and authoritative data, and is the only writer of its own data.
- A shared PostgreSQL deployment does not mean shared ownership. Logical schemas: `memory`, `research`, `orchestrator`, `shared` ([7.2](../../docs/technical-decisions/02-database-and-storage-architecture.md)).
- Derived records belong to the component that generates them.
- Initial deployment is a modular monolith with independent background workers. No microservice split without a documented, approved decision.

## Communication

- Memory and Research do not orchestrate each other; the Orchestrator mediates cross-engine work by default.
- Hybrid communication: synchronous request/response for short operations (REST/OpenAPI via FastAPI); asynchronous commands and events for long-running work (RabbitMQ + Celery).
- Contracts are structured, versioned and validated, and carry identity, user scope, execution/task/correlation IDs, idempotency keys, timeouts, standardized errors and provenance.
- Cross-engine access uses authorized interfaces and typed references, never direct writes to another engine's records.
- Message delivery is at-least-once; business operations must be idempotent. A timeout is not proof of failure.

## Personal Memory vs Document Intelligence

- Two separate logical domains in the Memory Engine with separate ownership, data models, retrieval workflows and lifecycle policies. They may share PostgreSQL, pgvector, object storage and workers.
- Document chunks are not atomic personal memories. Uploading a document never creates personal memories automatically.
- Document-derived facts enter personal memory only through an explicit, authorized extraction workflow, using the normal candidate → evaluation → resolution process.
- Personal-memory retrieval does not return document chunks by default. Document retrieval never silently changes personal memory.
- Memory embeddings and document embeddings are logically separate.

## Document retrieval vs external research

- Document retrieval (Memory Engine) searches the user's uploaded content. External research (Research Engine) discovers information outside Raven.
- The Orchestrator decides whether a request needs personal memory, documents, research or a combination. Historical plus current needs: memory first, then targeted research. Do not call every engine by default.
- Keep historical/stored information distinguishable from newly researched information in every response.

## Data integrity and provenance

- Authoritative records are the source of truth. Embeddings, indexes, profiles and caches are derived and must never override them.
- Every material finding keeps its provenance and temporal context. Document evidence keeps document, version, chunk and page/section location where available.
- Current observations never silently overwrite history; revisions are preserved.
- Similarity identifies candidates; it is never sufficient proof for a merge or an answer.
- Distinguish verified, inferred, low-confidence, conflicting and missing information. Never fabricate evidence.
- Failures and incomplete work stay visible; they are never reported as success.
- Explicit forgetting overrides expiry and archival, and propagates to derived data.
- Recovery belongs to the owning component; the Orchestrator coordinates.
- Performance never weakens correctness, deletion, identity or evidence obligations.
