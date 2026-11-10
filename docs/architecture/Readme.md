# Raven — System Architecture

## Overview

This directory contains the foundational system architecture of **Raven**, an independent AI research agent designed around three core capabilities:

1. Memory Engine
2. Research Engine
3. Agent Orchestrator

The architecture defines how these components interact, their responsibilities, communication patterns, execution lifecycle and system-wide constraints.

The objective is to maintain a modular, reliable, privacy-conscious and extensible architecture before implementation begins.

---

## Architecture Overview

Raven is organized into four conceptual layers:

| Layer | Responsibility |
|---|---|
| User Interface / Entry Layer | Receives user requests and delivers responses |
| Agent Orchestrator | Understands intent, plans tasks and coordinates execution |
| Memory & Research Engines | Perform memory management and external research |
| Shared Infrastructure | Provides common infrastructure and operational capabilities |

Shared Infrastructure is a cross-cutting support layer, not an additional business engine.

### Core Components

**1. Memory Engine**

The Memory Engine contains two separate logical knowledge domains with independent ownership, data models, retrieval workflows and lifecycle rules. They may share infrastructure, but document chunks are never treated as personal memories.

*Personal Memory* — responsible for:

- Memory ingestion and extraction.
- Importance and confidence evaluation.
- Entity and relationship management.
- Duplicate and contradiction resolution.
- Memory storage and indexing.
- Contextual retrieval.
- Memory consolidation.
- Forgetting and deletion.

*Document Intelligence* — responsible for:

- Document registration, validation and versioning.
- Text and structure extraction from uploaded documents.
- Structure-aware chunking and document embeddings.
- Hybrid (vector and keyword) document retrieval.
- Evidence selection, extractive answer assembly and citation provenance.
- Document lifecycle and deletion of derived artifacts.

Document Intelligence was added to the Memory Engine through the Phase 5–7 amendments; see [data-models](../data-models/Readme.md), [algorithms](../algorithms/Readme.md) and [technical-decisions](../technical-decisions/Readme.md).

**2. Research Engine**

Responsible for:

- Query understanding.
- Information discovery.
- Content extraction.
- Fact extraction and normalization.
- Source evaluation and verification.
- Research session and snapshot management.
- Research retrieval and comparison.

**3. Agent Orchestrator**

Responsible for:

- Intent understanding.
- Task planning.
- Engine routing.
- Sequential and parallel execution.
- Context management.
- Execution state and progress tracking.
- Failure recovery and cancellation.
- Response assembly.

**4. Shared Infrastructure**

Provides:

- Database and storage infrastructure.
- Search and indexing infrastructure.
- Identity and access control.
- Shared execution support.
- Logging and monitoring.
- Configuration and secrets management.
- Backup and disaster recovery.

---

## Architecture Documents

The following documents define Raven's system architecture.

| Document | Description | Status |
|---|---|---|
| `phase-01-overall-architecture.md` | Overall architecture, system layers, ownership, communication and lifecycle | Complete |
| `phase-02-memory-engine.md` | Memory Engine components, workflows, retrieval, consolidation and forgetting | Complete |
| `phase-03-research-engine.md` | Research Engine components, discovery, extraction, verification and retrieval | Complete |
| `phase-04-agent-orchestrator.md` | Orchestration, planning, routing, execution, context and recovery | Complete |

*The filenames above are the actual files in this directory.*

---

## Architectural Principles

Raven follows these foundational principles:

1. **Single ownership:** Each business capability has one authoritative owner.
2. **Modularity:** Engines have clearly defined responsibilities and boundaries.
3. **Orchestration over duplication:** The Orchestrator coordinates engines instead of reimplementing their business logic.
4. **Privacy by design:** User-specific information remains isolated and access-controlled.
5. **Evidence and provenance:** Important information retains traceability to its origin.
6. **Reliability:** Failures, retries, cancellation and partial completion must be handled explicitly.
7. **Consistency:** Current information must be distinguishable from historical information.
8. **Extensibility:** Components should evolve without unnecessarily coupling the entire system.

---

## Communication Model

Raven uses a hybrid communication approach:

- Synchronous request-response communication for immediate operations.
- Asynchronous processing for longer-running operations.
- Orchestrator-mediated coordination between engines by default.
- Explicit contracts, correlation identifiers and traceable execution state.

The technologies for these patterns were selected in Phase 7: REST/OpenAPI via FastAPI for synchronous communication, and RabbitMQ with Celery for asynchronous processing (see [technical-decisions](../technical-decisions/Readme.md)). Concrete API and message schemas are defined during implementation.

---

## Project Progress

| Phase | Description | Status |
|---|---|---|
| Phase 1 | Overall System Architecture | Complete |
| Phase 2 | Memory Engine Architecture | Complete |
| Phase 3 | Research Engine Architecture | Complete |
| Phase 4 | Agent Orchestrator Architecture | Complete |

**Architecture status: COMPLETE**

This means the architectural specifications have been documented. It does not indicate that the corresponding software has been implemented or tested.

Later documentation phases build on this architecture:

| Phase | Description | Status |
|---|---|---|
| Phase 5 | Data Models & Database Design ([data-models](../data-models/Readme.md)) | Documented |
| Phase 6 | Algorithms & Processing Design ([algorithms](../algorithms/Readme.md)) | Documented |
| Phase 7 | Technology & Infrastructure Selection ([technical-decisions](../technical-decisions/Readme.md)) | Documented |
| Phase 8 | Memory Engine Implementation ([plans](../implementation-plans/Phase-08-memory-engine/Readme.md)) | Planned; implementation not started |

---

## Next Steps

Phases 5–7 have translated the architecture into data models, algorithms and technology decisions. The next stages are:

- Memory Engine implementation (Phase 8), starting with Phase 8.1 Foundation and Project Setup.
- Research Engine and Agent Orchestrator implementation.
- Engine integration.
- Testing, evaluation and deployment.

Architecture documents are the source of truth for implementation. Implementation decisions must remain consistent with these specifications.

---

**Project:** Raven  
**Repository:** `raven-research-agent`  
**Documentation:** System Architecture
