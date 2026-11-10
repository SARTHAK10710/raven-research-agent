# Raven — Data Models & Database Design

## Overview

This directory contains the logical data architecture and data-model specifications for **Raven**.

It defines how information is represented, owned, related, stored, updated, retrieved, retained and deleted across the system.

The objective is to establish clear data ownership, preserve information integrity, support reliable cross-engine communication and maintain user privacy.

These specifications build on the system architecture defined in Phase 1–4.

---

## Data Architecture Overview

Raven follows a domain-oriented data ownership model.

Each major component owns its authoritative business records.

| Component | Data Ownership |
|---|---|
| Memory Engine | Personal memory: memory sources, candidates, atomic memories, entities, relationships, episodes, profiles and memory embeddings. Document Intelligence (a separate logical domain): documents, document versions, extracted representations, chunks, chunk locations, document embedding metadata and document processing operations |
| Research Engine | Research sessions, snapshots, sources, extracted content, findings, evidence and comparisons |
| Agent Orchestrator | Executions, tasks, dependencies, context snapshots, checkpoints and execution results |
| Shared Infrastructure | User identity, authorization policies, shared infrastructure configuration and infrastructure audit records |

The Orchestrator coordinates operations but does not own Memory Engine or Research Engine business data.

Shared Infrastructure provides common capabilities without taking ownership of engine-specific records.

---

## Data Architecture Principles

Raven follows these foundational data principles:

1. **Single authoritative owner:** Every authoritative business record has one owning component.
2. **Domain separation:** Each engine maintains its own data models and business rules.
3. **Reference-based access:** Cross-engine communication uses typed references rather than unrestricted direct access.
4. **User isolation:** Private user data remains isolated and access-controlled.
5. **Explicit shared data:** Data is shared only when explicitly classified and authorized.
6. **Provenance:** Important records preserve their origins and source references.
7. **Temporal integrity:** Historical information remains distinguishable from current information.
8. **Versioning:** Important changes preserve the necessary revision history.
9. **Deletion propagation:** Deletion and forgetting extend to dependent derived data and indexes.
10. **Recoverability:** Data changes, migrations and operational failures must be traceable and recoverable.

---

## Data Model Documents

Phase 5 is documented across the following files.

| Document | Description | Status |
|---|---|---|
| `phase-05-data-models-overview.md` | 5.1–5.3: Overall data architecture, data classification, access model, ownership boundaries, core entities, identifiers, relationships and provenance | Complete |
| `phase-05-memory-engine-models.md` | 5.4: Memory Engine personal memory data models, followed by the Document Intelligence data model amendment | Complete |
| `phase-05-research-engine-models.md` | 5.5: Research Engine data models | Complete |
| `phase-05-orchestrator-models.md` | 5.6: Agent Orchestrator data models | Complete |
| `phase-05-shared-infrastructure-models.md` | 5.7: Shared Infrastructure data models | Complete |
| `phase-05-relationships-and-lifecycle.md` | 5.8–5.10: Relationships, indexing, consistency, retention, deletion and migration, followed by the Document Intelligence relationships and lifecycle amendment | Complete |

*The filenames above are the actual files in this directory. Subphases 5.1–5.3 are documented together in `phase-05-data-models-overview.md`.*

*Two files carry amendments for Document Intelligence and RAG. Each keeps its original specification first and appends the amendment at the end; the amendment extends the original decisions and does not replace them.*

---

## Data Lifecycle Classification

Raven uses four conceptual data lifecycle classes.

| Classification | Meaning |
|---|---|
| Authoritative | The source of truth for a record |
| Derived | Information generated from authoritative records |
| Temporary | Information retained for a limited operational purpose |
| Cached | Reusable copies maintained for performance |

Derived and cached records must not override their authoritative sources.

Changes to authoritative information must trigger the appropriate refresh, invalidation or deletion processes.

---

## Relationship and Consistency Model

Raven uses a hybrid relationship model:

- Direct references for simple ownership and containment.
- Independent relationship records for meaningful relationships with their own attributes or history.
- Typed cross-engine references to preserve domain ownership.

The consistency model combines:

- Owner-controlled authoritative writes.
- Owner-scoped transaction boundaries.
- Optimistic concurrency by default.
- Versioned records where historical traceability matters.
- Eventual consistency for appropriate derived and cached data.
- Idempotent operations and coordinated recovery.

---

## Privacy, Retention and Deletion

Data management must respect:

- User ownership and authorization.
- Private versus explicitly shared data.
- Data sensitivity and retention policies.
- Explicit user forgetting and deletion requests.
- Derived data, embeddings, indexes and cache dependencies.
- Backup restoration and deletion reconciliation.

Deletion must not accidentally remove unrelated information or allow forgotten information to reappear.

Exact retention periods and physical storage mechanisms are implementation and policy decisions.

---

## Project Progress

| Subphase | Description | Status |
|---|---|---|
| 5.1 | Overall Data Architecture | Complete |
| 5.2 | Data Ownership & Boundaries | Complete |
| 5.3 | Core Entities & Relationships | Complete |
| 5.4 | Memory Engine Data Models | Complete |
| 5.5 | Research Engine Data Models | Complete |
| 5.6 | Orchestrator Data Models | Complete |
| 5.7 | Shared Infrastructure Data Models | Complete |
| 5.8 | Database Relationships & Indexing | Complete |
| 5.9 | Consistency, Transactions & Versioning | Complete |
| 5.10 | Retention, Deletion & Migration | Complete |

**Phase 5 status: ARCHITECTURALLY COMPLETE**

This completion refers to logical architecture and documentation. Physical database schemas, database selection, indexes, migrations and application code have not been claimed as implemented.

---

## Upcoming Phases

| Phase | Description |
|---|---|
| Phase 6 | Algorithms & Processing Design |
| Phase 7 | Technology & Infrastructure Selection |
| Phase 8–10 | Individual Engine Implementation |
| Phase 11 | Engine Integration |
| Phase 12 | Testing & Evaluation |
| Phase 13 | Performance Optimization |
| Phase 14 | Deployment & Infrastructure |
| Phase 15 | Continuous Evaluation & Improvement |

The data-model specifications are authoritative references for subsequent algorithm design and implementation.

Any future change to these models must preserve the established ownership, privacy, consistency and lifecycle rules.

---

**Project:** Raven  
**Repository:** `raven-research-agent`  
**Documentation:** Data Models & Database Design
