# Phase 8 — Memory Engine Implementation

## 1. Purpose

This directory contains the implementation plans for Raven's Memory Engine.

The purpose of Phase 8 is to translate the approved Memory Engine architecture, data models, algorithms, and technology decisions into a working, testable implementation.

All source code will be written inside the existing:

`memory-engine/`

This directory contains implementation instructions only. It must not contain application source code.

## 2. Implementation Objectives

The Memory Engine must support:

- Information ingestion and validation.
- Memory relevance evaluation.
- Atomic fact extraction.
- Explicit and inferred memory classification.
- Candidate generation and evaluation.
- Entity and relationship management.
- Duplicate and contradiction detection.
- Memory updates and version management.
- Authoritative memory persistence.
- Hybrid memory retrieval.
- Episodic and semantic consolidation.
- Derived profile generation.
- Memory maintenance.
- Forgetting and deletion propagation.
- Reliability, observability, and recovery.

## 3. Implementation Plan Index

| Step | Document | Responsibility |
|---|---|---|
| 8.1 | [Foundation and Project Setup](01-foundation-and-project-setup.md) | Establish the Memory Engine foundation |
| 8.2 | [Database and Persistence](02-database-and-persistence.md) | Implement database models and persistence |
| 8.3 | [Ingestion Pipeline](03-ingestion-pipeline.md) | Validate and ingest supported inputs |
| 8.4 | [Extraction and Evaluation](04-extraction-and-evaluation.md) | Extract and evaluate memory candidates |
| 8.5 | [Entity and Relationship Management](05-entity-and-relationship-management.md) | Manage entities, aliases and relationships |
| 8.6 | [Memory Resolution](06-memory-resolution.md) | Resolve duplicates, contradictions and updates |
| 8.7 | [Memory Storage and Indexing](07-memory-storage-and-indexing.md) | Persist authoritative memories and indexes |
| 8.8 | [Memory Retrieval](08-memory-retrieval.md) | Implement hybrid memory retrieval |
| 8.9 | [Consolidation and Maintenance](09-consolidation-and-maintenance.md) | Implement episodes, profiles and maintenance |
| 8.10 | [Forgetting and Deletion](10-forgetting-and-deletion.md) | Implement controlled forgetting and deletion |
| 8.11 | [Integration and Testing](11-memory-engine-integration-and-testing.md) | Verify complete Memory Engine workflows |

## 4. Architecture References

Implementation must follow the approved documents.

### Architecture

`docs/architecture/`

### Data Models

`docs/data-models/`

### Algorithms

`docs/algorithms/memory/`

### Technology Decisions

`docs/technical-decisions.md`

### Technology Specifications

`docs/technology/`

These documents collectively define the approved design and implementation constraints.

## 5. Implementation Principles

1. Architecture documents are the source of truth.
2. Implement one milestone at a time.
3. Respect the established Memory Engine ownership boundary.
4. Keep authoritative memories separate from candidates and derived data.
5. Preserve source provenance and temporal context.
6. Preserve explicit versus inferred classification.
7. Never treat similarity as proof of identity.
8. Do not automatically destroy ambiguous or conflicting memories.
9. Enforce user-level data isolation.
10. Make processing operations idempotent where required.
11. Implement deletion as a coordinated lifecycle operation.
12. Use deterministic validation for authoritative state transitions.
13. Keep generative LLM APIs and locally hosted generative LLMs out of core processing.
14. Do not introduce unnecessary infrastructure or dependencies.
15. Do not claim a milestone is complete without implementation and test evidence.

## 6. Implementation Workflow

Every milestone follows this workflow:

1. Read the corresponding implementation plan.
2. Read its architecture, data model, and algorithm references.
3. Inspect the existing repository before modifying files.
4. Identify dependencies and existing implementation.
5. Implement only the approved scope.
6. Add relevant automated tests.
7. Run the tests and inspect the results.
8. Review data integrity, security, and ownership boundaries.
9. Document actual implementation status.
10. Move to the next milestone only after acceptance criteria are satisfied.

## 7. Definition of Done

A milestone is complete only when:

- Required functionality is implemented.
- Expected source files exist.
- Architecture and data model requirements are respected.
- Relevant automated tests pass.
- Failure cases are handled.
- Security and ownership requirements are verified.
- No known critical integrity issues remain.
- Implementation evidence is documented.

Documentation completion alone does not constitute implementation completion.

## 8. Phase Completion

Phase 8 is complete when the Memory Engine's required capabilities have been implemented, integrated, tested, and verified against the approved specifications.

**Current status:** Implementation planning.

**Next milestone:** Phase 8.1 — Foundation and Project Setup.
