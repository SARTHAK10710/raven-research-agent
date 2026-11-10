# Phase 5 — Data Models & Database Design

**Project:** Raven — AI Research Agent  
**Phase:** 5  
**Status:** Architecture Complete  
**Scope:** Overall Data Architecture, Data Ownership, Data Boundaries and Core Data Principles

---

## 1. Objective

The objective of Phase 5 is to define how Raven represents, organizes, owns, relates, stores and manages data across its major components.

This phase establishes the logical data architecture before database technology selection and implementation.

The design must support:

- Persistent personal memory.
- External research and knowledge retrieval.
- Multi-step agent execution.
- Cross-engine communication.
- Data provenance and traceability.
- Historical information and versioning.
- Reliable updates, corrections and deletion.
- User-level privacy and isolation.
- Future scalability and extensibility.

The decisions in this phase establish architectural policies, not production database schemas.

---

## 2. Overall Data Architecture

Raven follows a logically separated data architecture with shared infrastructure.

The system has four major data ownership domains:

1. Memory Engine
2. Research Engine
3. Agent Orchestrator
4. Shared Infrastructure

Each component maintains authority over its own business records.

Physical database separation is not mandatory. Multiple components may use shared database infrastructure while maintaining strict logical ownership and access boundaries.

### 2.1 Memory Engine Data Domain

The Memory Engine owns information related to persistent user memory.

Its data includes:

- Memory Sources
- Memory Candidates
- Atomic Memories
- Entities
- Entity Relationships
- Memory Relationships
- Episodes
- Derived Profiles
- Provenance Records
- Entity Mentions
- Embedding Metadata
- Memory Evaluation and Maintenance Records
- Memory Deletion and Correction Records

The Memory Engine is the authoritative owner of personal memory records and their derived representations.

### 2.2 Research Engine Data Domain

The Research Engine owns information related to external research and research knowledge.

Its data includes:

- Research Sessions
- Research Snapshots
- Research Sources
- Extracted Content
- Research Findings
- Evidence Records
- Comparisons
- Research Conclusions

Research records remain under Research Engine ownership, including reusable public research information.

### 2.3 Agent Orchestrator Data Domain

The Agent Orchestrator owns information related to request execution and coordination.

Its data includes:

- Executions
- Tasks
- Task Dependencies
- Execution Contexts
- Checkpoints
- Execution Events
- Execution Results

The Orchestrator manages execution state and coordination but does not own Memory Engine or Research Engine business records.

### 2.4 Shared Infrastructure Data Domain

Shared Infrastructure provides common technical capabilities.

Its data includes:

- User Identity Records
- Authorization Policies
- Shared Reference Records
- Configuration Records
- Infrastructure Audit Events
- Infrastructure Metadata

Shared Infrastructure does not own engine-specific business logic or business records.

---

## 3. Logical Separation and Shared Infrastructure

### Decision 5.1.1 — Logical separation with shared infrastructure

Finalized principles:

- Each engine owns its data domain.
- Shared database infrastructure is permitted.
- Each engine remains authoritative over its own records.
- Cross-engine access follows defined interfaces.
- The Orchestrator coordinates operations without taking ownership of engine data.
- Physical separation may be introduced later when justified by scale, security or operational requirements.
- No database technology is selected in this phase.

Logical ownership must remain independent of physical storage topology.

---

## 4. Cross-Engine Data Access

### Decision 5.1.2 — Reference-based access with temporary context snapshots

Cross-engine data access follows a reference-based model.

Finalized principles:

- Engines access external data through defined interfaces.
- References identify original records without transferring ownership.
- The Orchestrator may create bounded, temporary context snapshots for executions and tasks.
- Snapshots preserve source references, timestamps, provenance and confidence or verification information where applicable.
- Temporary snapshots are not authoritative records.
- Updates and deletion follow the original record owner.
- Snapshots cannot bypass access-control or deletion policies.

Full record copying is not the default cross-engine communication mechanism.

---

## 5. User-Scoped and Shared Data

### Decision 5.1.3 — Strict user-scoped data with a separate shared-data domain

Raven distinguishes private user information from explicitly shared information.

### 5.1 Private Data

Private data includes:

- Personal memories.
- User-specific research.
- Private preferences and decisions.
- Personal history.
- Execution records containing private context.
- Derived profiles and personal relationships.

Private records must preserve user ownership and access boundaries.

### 5.2 Shared Data

Shared data may include:

- Public research.
- Reusable reference information.
- Common non-personal datasets.
- Public source metadata.
- Public content where retention and reuse are permitted.

Shared information must be explicitly classified and authorized.

### 5.3 Isolation Rules

- Private data must never become shared automatically.
- Absence of a user identifier does not imply public visibility.
- Shared data must not contain private user context.
- Private-data deletion must not remove independently owned shared information.
- Shared references can be used by private records without transferring ownership.

---

## 6. Data Lifecycle Classification

### Decision 5.1.4 — Four-class data lifecycle model

Every data object must be understood according to its lifecycle and authority.

### 6.1 Authoritative Data

Authoritative data represents the source of truth.

Examples:

- Atomic Memories.
- Research Findings.
- Research Sources.
- Execution and Task records.

Authoritative records are controlled by their designated owners.

### 6.2 Derived Data

Derived data is generated from authoritative records.

Examples:

- Derived Profiles.
- Summaries.
- Embeddings.
- Consolidated knowledge.
- Search representations.

Derived records must retain references to their contributing source records.

### 6.3 Temporary Data

Temporary data supports intermediate processing.

Examples:

- Execution Context Snapshots.
- Intermediate Research Results.
- Temporary Extraction Results.
- Processing Context.

Temporary data follows its associated execution or task retention requirements.

### 6.4 Cached Data

Cached data contains reusable copies of previously retrieved information.

Examples:

- Search Results.
- Retrieval Context.
- Reusable Query Results.

Cached data is never authoritative.

Updates must trigger appropriate refresh or invalidation. Stale cached information must not silently be presented as current.

### 6.5 Lifecycle Rules

- Authoritative records remain the source of truth.
- Derived records preserve source references.
- Temporary data follows defined retention policies.
- Cached data can be refreshed or invalidated.
- Updates propagate to dependent representations.
- Deletion propagates across applicable derived, temporary and cached records.
- Failed refreshes must not silently present stale data as current.

---

## 7. Data Ownership and Boundaries

### Decision 5.2.1 — Engine-specific authoritative ownership

Each engine owns its domain-specific business records.

| Component | Authoritative data ownership |
|---|---|
| Memory Engine | Memory sources, candidates, memories, entities, relationships, episodes, profiles and memory-derived records |
| Research Engine | Research sessions, snapshots, sources, extracted content, findings, evidence and comparisons |
| Agent Orchestrator | Executions, tasks, dependencies, scheduling, retries and cancellation state |
| Shared Infrastructure | Identity, authorization, shared configuration and infrastructure metadata |

Every business record must have one authoritative owner.

### Decision 5.2.2 — Originating engine retains ownership of shared information

Shared classification does not transfer ownership.

- Public research remains Research Engine-owned.
- Memory records remain Memory Engine-owned.
- Infrastructure-managed reference data remains owned by its designated maintaining component.
- Private information never becomes shared automatically.
- Provenance and source attribution must be preserved.

No separate Shared Data Engine is introduced at this stage.

### Decision 5.2.3 — Owner-controlled access

- Each engine exclusively controls writes to its authoritative records.
- Cross-engine reads use defined interfaces.
- Access is authorized and limited to the requested information.
- Direct cross-engine modifications are not permitted.
- The Orchestrator may request changes or deletion on behalf of a user.
- The owning engine validates and executes those operations.
- Deletion is routed to the authoritative owner.

### Decision 5.2.4 — Responsibility-based audit and log ownership

| Component | Audit ownership |
|---|---|
| Memory Engine | Extraction, retrieval, matching and maintenance audit records |
| Research Engine | Discovery, extraction and verification audit records |
| Agent Orchestrator | Execution, task, retry and cancellation records |
| Shared Infrastructure | Authentication, authorization and infrastructure audit records |

Centralized telemetry does not transfer business-record ownership.

Logs must respect access, retention and deletion policies and must avoid unnecessary sensitive content or secrets.

### Decision 5.2.5 — Generating component owns derived records

- The component generating or maintaining a derived record owns it.
- Original source records remain owned by their originating engines.
- Derived records preserve references to contributing sources.
- Derived records cannot override authoritative source records.
- Memory Engine owns Derived Profiles.
- Research Engine owns research summaries and conclusions.
- Orchestrator owns execution-specific summaries and context snapshots.
- Joint ownership is not introduced.

---

## 8. Common Data Metadata Principles

### Decision 5.3.1 — Common metadata contract with domain-specific schemas

Raven uses a common identity and metadata convention across authoritative records.

Proposed conceptual metadata includes:

- Record identity.
- Ownership scope.
- User association where applicable.
- Creation timestamp.
- Update timestamp.
- Version information.
- Lifecycle status.
- Provenance information where applicable.

Each engine defines its own domain-specific data fields.

A universal table or universal record schema is not required.

Exact field names, types, mandatory fields and serialization formats are deferred to detailed schema design.

---

## 9. Entity Relationships and References

### Decision 5.3.2 — Hybrid relationship model

Raven uses two relationship representation approaches.

**Direct references:**

Used for straightforward ownership, containment and simple associations.

**Independent relationship records:**

Used for meaningful relationships that require independent metadata, history, provenance, confidence or lifecycle management.

Many-to-many relationships use explicit association records where necessary.

Examples:

- User to Memory: ownership reference.
- Memory to Source: provenance reference.
- Entity to Entity: independent Entity Relationship.
- Memory to Episode: Episode Membership.
- Finding to Evidence: association record.
- Task to Task: explicit Task Dependency.
- Derived Profile to Memory: Profile–Memory Association.

---

## 10. Record Identity

### Decision 5.3.3 — Globally unique opaque identifiers

Every record receives a globally unique opaque identifier.

Illustrative prefixes may include:

- `mem_`
- `res_`
- `exe_`
- `tsk_`

Prefixes are organizational conventions and are not relied upon for uniqueness.

Finalized rules:

- IDs must not encode personal information.
- Ownership and identity remain separate.
- IDs remain stable throughout the record lifecycle.
- Global uniqueness does not imply global access.
- The exact ID-generation algorithm and format are deferred.

---

## 11. Temporal Data Representation

### Decision 5.3.4 — Bitemporal model

Raven distinguishes two temporal dimensions.

**Valid Time:** When information was true in the real world.

**Transaction Time:** When Raven learned, recorded or updated the information.

This distinction is important for:

- Historical preferences.
- Employment history.
- Entity relationships.
- Research findings.
- Corrections.
- Late-arriving information.

Historical values must not be silently overwritten.

The model applies where temporal history is meaningful, rather than requiring every operational record to maintain two timelines.

Exact timestamp fields and interval representation are deferred.

---

## 12. Provenance Principles

### Decision 5.3.5 — Hybrid provenance model

Every authoritative record carries essential provenance metadata.

Detailed provenance may be maintained through independent records.

Finalized principles:

- Multiple sources can support a single memory or finding.
- Derived records retain contributing source references.
- Explicit, inferred, external and system-generated information are distinguishable.
- Provenance changes and corrections preserve relevant history.
- Cross-engine references maintain traceability.
- Provenance records follow the access, retention and deletion policies of their authoritative owner.

Provenance must not imply stronger evidence than the underlying source supports.

---

## 13. Lifecycle and State Management

### Decision 5.3.6 — Domain-specific lifecycle states

Each engine defines valid lifecycle states for its own entities.

Finalized rules:

- There is no universal lifecycle state machine.
- Each owner controls its own state transitions.
- Invalid transitions must be rejected.
- Lifecycle history is preserved where auditability, recovery or historical understanding requires it.
- Lifecycle status is separate from confidence, authority and verification.

---

## 14. Referential Integrity and Deletion

### Decision 5.3.7 — Referential integrity with deletion propagation

Raven must preserve referential integrity across its data domains.

Finalized rules:

- Relationships reference valid records or an explicitly handled deletion state.
- Deletion triggers dependency analysis.
- Dependent derived records, embeddings, indexes and caches are updated or removed.
- Historical references follow the applicable deletion policy.
- Information pending deletion must not remain accessible when deletion policy requires immediate inaccessibility.
- Unrelated records must remain intact.
- Temporary soft deletion may be used during propagation.
- Deletion operations must be traceable and recoverable without restoring access to explicitly forgotten information.

---

## 15. Cross-Engine Reference Contract

### Decision 5.3.8 — Typed cross-engine references

Cross-engine references conceptually identify:

- Original record identity.
- Owning domain.
- Record type.
- User scope.
- Version where consistency requires it.

Finalized rules:

- References identify the original owner and record.
- A reference is not an authorization credential.
- Receiving components independently validate access.
- References do not transfer ownership or write permissions.
- Full copies are not the default.
- Temporary context snapshots remain distinguishable from authoritative records.

The exact serialized reference contract is deferred to implementation design.

---

## 16. Initial Core Entity Inventory

### Decision 5.3.9 — Initial core entity inventory

The following inventory establishes the initial data-model scope.

### Memory Engine

- Memory Source
- Memory Candidate
- Atomic Memory
- Entity
- Entity Relationship
- Episode
- Derived Profile
- Provenance Record

Additional supporting models are defined in the dedicated Memory Engine document.

### Research Engine

- Research Session
- Research Snapshot
- Research Source
- Extracted Content
- Research Finding
- Evidence Record
- Comparison

### Agent Orchestrator

- Execution
- Task
- Task Dependency
- Execution Context
- Checkpoint
- Execution Event
- Execution Result

### Shared Infrastructure

- User Identity
- Authorization Policy
- Shared Reference Record
- Configuration Record
- Infrastructure Audit Event

Not every conceptual entity must become a separate database table or collection.

Every persisted entity must have a clearly defined owner, lifecycle and purpose.

---

## 17. Cross-Cutting Data Integrity Principles

The following principles apply across Raven:

1. Every business record has one authoritative owner.
2. User data remains isolated and access-controlled.
3. Derived records retain their source references.
4. Historical and current information remain distinguishable.
5. Unverified information must not be presented as verified.
6. Failed operations must never be silently treated as successful.
7. State-changing operations must be traceable and recoverable.
8. Deletion must propagate through dependent data.
9. Temporary and cached data must not become authoritative.
10. Cross-engine access follows defined contracts.
11. Similarity is not proof of identity or factual relationships.
12. Optimization must not compromise correctness, privacy or data integrity.

---

## 18. Decisions Deferred to Later Phases

Phase 5 establishes logical data architecture, not physical implementation.

The following decisions remain deferred:

### Phase 6 — Algorithms & Processing Design

- Memory extraction algorithms.
- Candidate evaluation and promotion.
- Entity resolution algorithms.
- Matching and contradiction resolution.
- Memory consolidation.
- Embedding generation and retrieval policies.
- Research processing algorithms.
- Orchestration algorithms.
- Deletion propagation and recovery procedures.

### Phase 7 — Technology & Infrastructure Selection

- Relational database selection.
- Vector database selection.
- Object/content storage.
- Search and indexing technology.
- Embedding model selection.
- Message broker and communication infrastructure.
- Deployment architecture.
- Database partitioning and scaling strategy.

### Implementation Phases

- Actual database schemas.
- Migrations.
- Index definitions.
- API contracts.
- Repository and service implementation.
- Automated tests.
- Performance benchmarks.

---

## 19. Completion Criteria

Phase 5 is considered architecturally complete when:

- Each engine has defined data ownership.
- Core entities and their relationships are identified.
- Authoritative and derived data are distinguished.
- User and shared-data boundaries are defined.
- Provenance and temporal principles are established.
- Referential integrity and deletion policies are established.
- Cross-engine references follow defined rules.
- Domain-specific lifecycle ownership is clear.
- Detailed data models are documented for each engine.

**Status: Phase 5 — Architecture Complete.**

**Next Phase: Phase 6 — Algorithms & Processing Design.**
