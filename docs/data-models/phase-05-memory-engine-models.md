# Phase 5.4 — Memory Engine Data Models

> **Document history:** This file contains the original Phase 5.4 Memory Engine (personal memory) data model, restored from commit `94e25b5`, followed by the Phase 5 Document Intelligence Data Models amendment from commit `3fd622b`, appended at the end of this file. A second amendment, the Phase 8.2 Amendment on relationship vocabularies and Atomic Memory lifecycle states (approved 2026-11-11), follows it. The amendments extend the original decisions; they do not replace them.

**Project:** Raven — AI Research Agent  
**Phase:** 5 — Data Models & Database Design  
**Component:** Memory Engine  
**Status:** Architecture Complete  
**Optimization Priority:** Memory Engine — 70:30 (as established in Phase 2)

---

# 1. Objective

This document defines the logical data models, relationships, ownership boundaries and lifecycle principles of the Raven Memory Engine.

The Memory Engine is responsible for capturing, extracting, evaluating, organizing, storing, retrieving, consolidating and maintaining persistent user memories.

Its data architecture must support:

- Reliable memory ingestion.
- Candidate extraction and evaluation.
- Atomic memory representation.
- Entity identification and relationship management.
- Memory episodes and contextual grouping.
- Derived user profiles.
- Provenance and evidence tracking.
- Semantic embeddings and indexing.
- Memory correction and forgetting.
- Historical information and version management.
- User isolation and data integrity.

This document defines logical architecture and data-model decisions. It does not establish production database schemas or select specific database technologies.

---

# 2. Memory Engine Data Architecture

The Memory Engine uses independently identifiable entities with clearly defined ownership and relationships.

Its principal data models are:

1. Memory Source
2. Memory Candidate
3. Atomic Memory
4. Entity
5. Entity Relationship
6. Memory Relationship
7. Episode
8. Episode Membership
9. Derived Profile
10. Profile–Memory Association
11. Provenance Record
12. Entity Mention
13. Entity Resolution Record
14. Embedding Metadata Record
15. Memory Deletion Operation
16. Memory Correction Request
17. Candidate Evaluation Record
18. Source Processing Event
19. Profile Refresh History
20. Memory Category Assignment
21. Memory Consolidation Result
22. Episode Timeline Event

These represent conceptual entities and supporting records. Not every entity must become a separate database table or collection.

---

# 3. Memory Source

## Decision 5.4.1 — Source content storage: Option B

Raven will store Memory Source metadata in structured database storage and original content in a dedicated content-storage layer.

### Finalized Rules

1. Every original input is represented by a Memory Source record.
2. Source metadata is maintained independently of the original content.
3. The Memory Source maintains a stable reference to its stored content.
4. Multiple Memory Candidates may reference the same Memory Source.
5. Original content remains traceable for provenance, correction and permitted reprocessing.
6. Source content follows the same user-isolation, access-control, retention and deletion requirements as its source record.
7. Original content must not be retained indefinitely without an applicable retention policy.
8. Deletion removes both source metadata and associated content.

The specific content-storage technology is deferred to Phase 7.

---

# 4. Memory Candidates

## Decision 5.4.2 — Independent Memory Candidate records: Option A

Every extracted candidate is represented as an independent record.

### Finalized Rules

1. Each candidate has a globally unique identity.
2. Every candidate references its originating Memory Source.
3. One source may produce zero, one or multiple candidates.
4. Each candidate independently maintains its evaluation state.
5. Candidates support independent matching, review, promotion and rejection.
6. Updating a candidate does not overwrite original source content.
7. Failure of one candidate does not invalidate other candidates from the same source.
8. A candidate remains distinct from a validated Atomic Memory.

---

## Decision 5.4.3 — Candidate promotion: Option A

Candidate promotion follows a controlled process.

### Finalized Rules

1. A candidate becomes eligible for promotion only after appropriate evaluation and resolution.
2. Promotion creates or contributes to an Atomic Memory.
3. Promotion does not change the candidate's identity or record type.
4. Candidate and source lineage must be preserved.
5. Multiple candidates may contribute to one Atomic Memory.
6. Duplicate candidates must not automatically create duplicate memories.
7. Candidates may support, update or correct existing memories through controlled resolution.
8. Candidate history is retained according to the applicable lifecycle policy.
9. Evaluation and promotion remain separate operations.

---

# 5. Atomic Memory

## Decision 5.4.4 — Hybrid Atomic Memory representation: Option C

Atomic Memories use a combination of human-readable natural-language content and structured representation.

### Finalized Rules

1. Human-readable content preserves the meaning of the memory.
2. Structured representation supports querying, matching and reasoning.
3. The model is not restricted to simple subject-predicate-object triples.
4. Richer attributes and contextual information are permitted.
5. Both representations must express consistent information.
6. Structured fields must not introduce unsupported facts.
7. Source and candidate lineage must be preserved.
8. Historical information must remain distinguishable.

---

## Decision 5.4.5 — Independent importance and confidence: Option A

Importance and confidence are separate dimensions.

### Importance

Represents the significance and potential future relevance of a memory.

### Confidence

Represents the strength of evidence supporting the memory.

### Finalized Rules

1. Importance and confidence are maintained independently.
2. Neither is combined into a single score by default.
3. Each dimension can be independently evaluated and updated.
4. A memory may have high importance but low confidence.
5. Evaluation changes follow record versioning and applicable audit-history policies.
6. No separate evaluation-history entity is mandatory for every change.
7. Exact scoring scales and evaluation algorithms are deferred to Phase 6.

---

## Decision 5.4.6 — Hybrid context representation: Option C

Atomic Memories support both natural-language context and structured context.

### Finalized Rules

Context may include:

- Time.
- Location.
- Conditions.
- Scope.
- Circumstances.
- Qualifiers.
- Relevant constraints.

Context must preserve the original meaning and qualifiers.

Missing contextual information must not be fabricated.

Natural-language and structured context must remain consistent.

Context supports matching, retrieval, contradiction resolution and consolidation.

Exact context schemas are deferred to detailed schema design.

---

## Decision 5.4.7 — Mutable current memory with immutable revision history: Option A

Atomic Memories maintain a current record and immutable revision history.

### Finalized Rules

1. The current record represents the latest accepted understanding.
2. Every accepted change creates a new immutable revision.
3. Previous revisions must not be overwritten.
4. Source provenance must remain traceable across revisions.
5. Relevant temporal information must be preserved.
6. Bitemporal representation applies where appropriate.
7. Historical revisions are not considered active by default.
8. Deletion applies to dependent revisions and derived representations according to deletion policy.

---

# 6. Entity Representation and Resolution

## Decision 5.4.8 — Canonical entity references: Option A

Atomic Memories use canonical Entity references when identifiable.

### Finalized Rules

- Identifiable entities are represented through globally unique Entity IDs.
- Ordinary attributes remain literal values.
- Aliases are managed through Entity Management.
- Unresolved entities may temporarily retain their original extracted wording.
- Distinct entities must not be silently merged.
- Source context and provenance must be preserved.
- Entity references follow user and shared-data isolation boundaries.

---

## Decision 5.4.9 — Multi-label Memory Classification

Atomic Memories support multiple categories.

The initial category taxonomy includes:

1. Personal Preferences
2. Goals
3. Decisions
4. Important Events
5. Relationships
6. Knowledge
7. Projects
8. Commitments

### Finalized Rules

- One Atomic Memory may have multiple categories.
- Categories are independently assigned and updated.
- Categories do not replace the underlying memory content.
- Classification changes preserve identity and relevant history.
- The taxonomy may be extended as Raven evolves.

---

## Decision 5.4.10 — Explicit and inferred origin tracking: Option A

Every Atomic Memory records whether its origin is explicit or inferred.

### Explicit Memories

Directly supported by statements or information supplied by the user.

### Inferred Memories

Derived through interpretation of available evidence.

### Finalized Rules

1. Every Atomic Memory records its origin type.
2. Inferred memories preserve evidence and inference provenance.
3. Confidence remains independent of importance.
4. Weak inferences remain candidates and cannot automatically become validated memories.
5. Validation does not convert an inferred memory into an explicit statement.
6. Corrections preserve relevant inference history.
7. Both types follow the same ownership, revision and deletion policies.

---

## Decision 5.4.11 — Hybrid Memory Granularity: Option C

Raven uses a hybrid approach to memory granularity.

### Finalized Rules

1. Independently meaningful facts should generally be separated.
2. Tightly coupled information remains together when separation would lose meaning.
3. Each Atomic Memory maintains independent importance, confidence, provenance and lifecycle.
4. Related facts may share source references.
5. Related memories can be connected through Memory Relationships and Episodes.
6. Semantic meaning takes priority over maximizing record count.
7. The same principles apply to extraction, correction and consolidation.

---

## Decision 5.4.12 — Three-stage Entity Resolution: Option C

Entity resolution follows three conceptual stages.

### Stage 1 — Entity Mention

Preserve the original extracted entity mention and its source context.

### Stage 2 — Resolution

Compare the mention against existing canonical entities using:

- Identity evidence.
- Aliases.
- Context.
- Relevant attributes.

### Stage 3 — Canonical Association

Link the mention to an existing canonical Entity when sufficiently supported, or create a new Entity when justified.

### Finalized Rules

- Uncertain mentions remain unresolved.
- Similarity alone is insufficient proof of identity.
- Incorrect merges must be correctable without losing original mentions or provenance.
- Resolution respects user and shared-data boundaries.

---

## Decision 5.4.13 — Private and shared Entity scopes: Option C

Raven supports two Entity scopes.

### Private User-Scoped Entities

Examples include:

- Personal contacts.
- Private organizations.
- Contextual identities.
- User-specific relationships.

### Shared Canonical Public Entities

Examples include:

- Public companies.
- Products.
- Locations.
- Public organizations.

### Finalized Rules

1. Private relationships remain private even when referencing shared entities.
2. Shared entities must not contain private user context.
3. Moving private information into shared data requires explicit classification and validation.
4. Private deletion must not remove independently owned shared entities.

---

## Decision 5.4.14 — Independent Alias Management: Option A

Canonical Entities maintain independently managed aliases.

### Finalized Rules

- Canonical Entity IDs remain stable.
- Multiple aliases may resolve to the same Entity.
- Original source wording is preserved in Entity Mentions.
- Ambiguous aliases require contextual evaluation.
- Alias matching alone does not prove identity.
- Name changes are distinguished from identity changes.
- Mergers, acquisitions and organizational splits are represented as explicit relationships or identity events, not simple aliases.
- Alias management respects Entity scope.

---

## Decision 5.4.15 — Independent Entity Relationship records: Option A

Entity Relationships are represented as independent typed directed records.

### Finalized Rules

1. Every relationship identifies a source Entity and target Entity.
2. Relationships have an explicit type.
3. Contextual attributes, confidence and provenance may be included.
4. Relationships are directed by default.
5. Symmetric relationship semantics must be explicitly defined.
6. Temporal validity and transaction history are preserved where relevant.
7. The Memory Engine controls relationship creation and updates.
8. Similarity alone cannot establish a relationship.
9. Private and shared Entity boundaries must be respected.
10. Historical relationship changes must not be silently overwritten.

---

# 7. Episodes

## Decision 5.4.16 — Independent Episode entities: Option A

Episodes are independent entities that organize related Atomic Memories.

### Finalized Rules

1. Each Episode has its own globally unique identity.
2. Episodes reference constituent Atomic Memories.
3. Atomic Memories remain authoritative.
4. Episodes may contain titles, summaries, temporal boundaries, context and participant references where supported.
5. Episode membership preserves provenance and source traceability.
6. A memory may participate in multiple Episodes.
7. Episode summaries are derived representations and must not introduce unsupported facts.
8. Changes to constituent memories may trigger Episode review or refresh.
9. Episode updates preserve chronology and historical context.
10. Deleting an Episode does not automatically delete its constituent Atomic Memories.

---

# 8. Derived Profiles

## Decision 5.4.17 — Hybrid persisted and dynamically refreshed profiles: Option C

Commonly useful Derived Profiles are persisted, while uncommon or stale profiles may be generated or refreshed dynamically.

### Finalized Rules

- Commonly useful profiles may be persisted.
- Profiles are incrementally updated when relevant memories change.
- Stale, incomplete or contradicted profiles can be dynamically refreshed.
- Every profile preserves references to supporting memories.
- Profile versions and freshness must be trackable.
- Profiles are derived representations, not authoritative facts.
- Unsupported conclusions must not be introduced.
- On-demand profiles need not always be persisted.

---

# 9. Provenance Records

## Decision 5.4.18 — Hybrid provenance storage: Option C

Essential provenance references are maintained on relevant records, while detailed evidence relationships use independent Provenance Records where necessary.

### Finalized Rules

1. Atomic Memories and Candidates retain essential provenance references.
2. Independent Provenance Records capture detailed evidence and source relationships where required.
3. One memory may be supported by multiple sources.
4. Provenance distinguishes explicit, inferred and system-generated information.
5. Inferred memories preserve their inference lineage.
6. Corrections preserve historical traceability.
7. Embedded references and independent records must remain consistent.
8. Provenance records follow Memory Engine ownership and lifecycle policies.

---

# 10. Embeddings and Indexing

## Decision 5.4.19 — Separate embedding metadata and vector storage: Option C

Embedding metadata is stored separately from vector payloads.

### Finalized Rules

1. Each embedding has an independent metadata record.
2. Metadata references the relevant Atomic Memory and revision.
3. Metadata identifies the embedding model and version.
4. Vector payloads reside in a dedicated vector-indexing layer.
5. Multiple embeddings may exist for different models or revisions where justified.
6. Embeddings are derived data.
7. Updates trigger regeneration or re-indexing as appropriate.
8. Deletion propagates to metadata and vector payloads.
9. Indexing status and failures are trackable.

The vector database and embedding model are deferred to Phase 7.

---

## Decision 5.4.20 — Hybrid embedding lifecycle tracking: Option C

The current lifecycle state is stored in Embedding Metadata Records.

Independent job records are created when detailed processing history or recovery information is necessary.

### Finalized Rules

- Embedding metadata maintains current lifecycle state.
- Lifecycle states cover pending, generating, generated, indexing, indexed, failed, superseded and deletion processing.
- Detailed job records may capture retry, recovery and processing history.
- The Memory Engine owns embedding data and its current state.
- The Orchestrator owns general execution and task coordination.
- Stale or failed embeddings must not silently be treated as current.
- Updates and deletions propagate to associated records.

---

## Decision 5.4.21 — Hybrid embedding granularity: Option C

Each eligible Atomic Memory receives one primary embedding, with additional embeddings only when distinct semantic aspects provide meaningful retrieval value.

### Finalized Rules

1. Every eligible Atomic Memory receives a primary embedding.
2. Additional embeddings may represent distinct semantic aspects.
3. All embeddings reference the same Atomic Memory and its revision.
4. Embedding metadata identifies the purpose of each representation.
5. Multiple fields alone do not justify multiple embeddings.
6. Retrieval deduplicates results to their authoritative Atomic Memory.
7. Atomic Memories remain authoritative.
8. Additional embedding-generation criteria are deferred to Phase 6.

---

# 11. Memory Categories

## Decision 5.4.22 — Hybrid Memory Category representation: Option C

Current category assignments are stored in a structured form associated with Atomic Memories.

Independent assignment records are used when detailed history, confidence, provenance or review tracking is necessary.

### Finalized Rules

- An Atomic Memory may have multiple categories.
- A standard category taxonomy defines available categories.
- Current assignments remain efficiently accessible.
- Independent records may capture detailed classification metadata.
- Inferred or ambiguous classifications can preserve confidence and evidence.
- Classification changes preserve relevant history.
- Category assignments do not replace memory content.

---

# 12. Memory Consolidation

## Decision 5.4.23 — Hybrid consolidation-result representation: Option C

Existing entities are reused for established consolidation outputs.

Independent typed derived records are created only when a meaningful result does not fit an existing model.

### Finalized Rules

- Established outputs use existing entities such as Episodes and Derived Profiles.
- Independent derived records may represent new meaningful output types.
- Persisted results preserve contributing Atomic Memory references.
- Relevant records preserve consolidation method, version, timestamp and provenance.
- Derived results never replace authoritative memories.
- Temporary intermediate outputs are not automatically persisted.

---

# 13. Memory Deletion

## Decision 5.4.24 — Hybrid deletion tracking: Option C

Coordinated deletion uses independent Memory Deletion Operation records, while affected records maintain their own deletion lifecycle state.

### Finalized Rules

1. Coordinated deletion requests create independent operation records.
2. Affected records maintain their individual deletion state.
3. Simple deletions may use a lightweight path.
4. Operations track affected dependencies and propagation progress.
5. Failed propagation can resume safely and idempotently.
6. Information undergoing deletion becomes inaccessible when required by policy.
7. Deletion records must not unnecessarily preserve forgotten content.
8. The Memory Engine owns memory deletion operations.
9. The Orchestrator may coordinate execution without taking ownership.
10. Completion requires satisfaction of all applicable deletion obligations.

---

# 14. Candidate Evaluation

## Decision 5.4.25 — Hybrid Candidate Evaluation History: Option C

The latest evaluation state is stored inside the Memory Candidate.

Independent Candidate Evaluation records are created for material evaluation changes.

### Finalized Rules

- Candidate records maintain their latest evaluation state.
- Material changes create independent evaluation records.
- Evaluation history preserves relevant evidence, provenance, timestamps and outcomes.
- Routine processing details remain operational telemetry.
- Meaningful evaluation history must not be overwritten.
- Exact evaluation algorithms and thresholds are deferred to Phase 6.

---

# 15. Memory Correction

## Decision 5.4.26 — Hybrid Memory Correction tracking: Option C

Straightforward corrections use the Atomic Memory revision mechanism.

Complex corrections use independent Memory Correction Request records.

### Finalized Rules

1. Simple corrections update the relevant Atomic Memory through a new revision.
2. Complex corrections create independent correction records.
3. Correction records preserve affected memory references, proposed changes, supporting evidence and resolution.
4. Accepted corrections use the normal revision mechanism.
5. Historical facts remain available where still valid and relevant.
6. Dependent profiles, relationships, Episodes and Embeddings are reviewed or refreshed.
7. Rejected or unresolved corrections must not silently modify authoritative memories.
8. The Memory Engine owns correction workflows.
9. Criteria for classifying complex corrections are deferred to Phase 6.

---

# 16. Memory Relationships

## Decision 5.4.27 — Independent Memory Relationship records: Option A

Meaningful relationships between Atomic Memories are represented through independent Memory Relationship records.

### Finalized Rules

1. Every relationship has its own globally unique ID.
2. Every relationship identifies source and target Atomic Memories.
3. Relationships have explicit types.
4. Examples include:
   - `supports`
   - `contradicts`
   - `updates`
   - `supersedes`
   - `related_to`
   - `part_of`
   - `derived_from`
5. Relationships may contain confidence, provenance and contextual metadata.
6. Relationships can be updated independently.
7. Historical changes are preserved where relevant.
8. User ownership and access boundaries apply.
9. Similarity alone cannot establish factual relationships.
10. Deletion triggers referential-integrity handling.

Memory Relationships are distinct from Entity Relationships.

---

# 17. Memory Source Processing History

## Decision 5.4.28 — Hybrid Memory Source processing history: Option C

Memory Source records maintain current processing status.

Independent Source Processing Event records capture meaningful processing transitions, failures, retries and recovery.

### Finalized Rules

- Source records maintain their current processing state.
- Meaningful transitions are independently traceable.
- Failures, retries and recovery events are preserved where significant.
- Routine telemetry does not automatically become permanent business data.
- Candidates retain references to originating sources.
- The Memory Engine owns source processing state and domain-specific events.
- The Orchestrator owns general task coordination.
- Processing records follow source retention and deletion policies.

---

# 18. Episode Membership

## Decision 5.4.29 — Independent Episode Membership records: Option B

Every Episode–Atomic Memory association is represented by an independent Episode Membership record.

### Finalized Rules

1. Every membership has its own unique ID.
2. It references one Episode and one Atomic Memory.
3. Membership can capture sequence or ordering.
4. It may identify the memory's role within the Episode.
5. Relevant temporal context, provenance and confidence may be included.
6. Membership can be managed independently.
7. Historical membership changes are preserved where relevant.
8. One Atomic Memory may belong to multiple Episodes.
9. Episode deletion does not automatically delete Atomic Memories.
10. Referential integrity and deletion policies apply.

---

# 19. Episode Timeline

## Decision 5.4.30 — Hybrid Episode timeline representation: Option C

Episode records maintain overall temporal boundaries.

Episode Membership records preserve ordering.

Independent timeline events represent meaningful milestones when necessary.

### Finalized Rules

- Episodes maintain known start and end boundaries.
- Membership records maintain memory ordering.
- Independent timeline events may represent important milestones.
- Timeline events reference their Episode and relevant memories.
- Temporal precision and uncertainty are preserved.
- Unknown dates must not be fabricated.
- Historical timeline corrections preserve previous understanding.
- Valid time and transaction time remain distinguishable.

---

# 20. Derived Profile–Memory Relationships

## Decision 5.4.31 — Independent Profile–Memory Association records: Option B

Relationships between Derived Profiles and supporting Atomic Memories use independent association records.

### Finalized Rules

1. Each association has its own unique ID.
2. Each association references one Derived Profile and one Atomic Memory.
3. Associations may capture contribution or relevance.
4. Supporting evidence and provenance references are preserved where applicable.
5. Associations can be updated independently.
6. Historical changes are preserved where relevant.
7. A memory may support multiple profiles.
8. A profile may be supported by multiple memories.
9. Removing an association does not automatically delete either endpoint.
10. Access and deletion policies follow record ownership.

---

# 21. Derived Profile Refresh History

## Decision 5.4.32 — Hybrid Derived Profile refresh tracking: Option C

Derived Profiles maintain current freshness and refresh status.

Independent Profile Refresh History records capture meaningful changes, failures, recovery and material version updates.

### Finalized Rules

- Profiles maintain current freshness and refresh status.
- Meaningful refresh events create independent history records.
- Refresh records preserve triggers, supporting-memory references, outcomes and timestamps.
- Significant failures and recovery attempts are traceable.
- Routine details remain operational telemetry.
- Immutable profile revisions preserve previous content.
- Refresh history does not duplicate Orchestrator execution records.
- The Memory Engine owns profiles, revisions and refresh history.

---

# 22. Entity Mentions

## Decision 5.4.33 — Independent Entity Mention records: Option A

Extracted Entity Mentions are represented as independent records.

### Finalized Rules

1. Each independently tracked mention has its own unique ID.
2. Original extracted wording is preserved.
3. The mention references its originating Memory Source and relevant context.
4. Mention type and resolution status are recorded.
5. A canonical Entity reference is attached when resolution is sufficiently supported.
6. Unresolved and ambiguous mentions remain independent.
7. Confidence and provenance are preserved where applicable.
8. Incorrect resolutions can be corrected without losing the original mention.
9. Canonical Entity aliases remain a separate concern.
10. Mention records follow Memory Engine ownership, isolation, retention and deletion policies.

An Entity Mention represents what Raven observed; a canonical Entity represents the identity Raven resolved it to.

---

# 23. Entity Resolution History

## Decision 5.4.34 — Hybrid Entity Resolution tracking: Option C

The current resolution state is stored in the Entity Mention.

Independent Entity Resolution records are created for meaningful decisions, corrections, reassignments and entity merges.

### Finalized Rules

1. Entity Mention records maintain current resolution status.
2. The current canonical Entity reference is stored when resolution is sufficiently supported.
3. Independent resolution records preserve material resolution decisions.
4. Resolution records may capture:
   - Candidate canonical entities.
   - Supporting identity evidence.
   - Resolution outcome.
   - Relevant rationale.
   - Timestamp and provenance.
5. Routine matching attempts remain operational logs.
6. Historical resolution decisions remain traceable.
7. Similarity alone is never sufficient proof of identity.
8. Incorrect resolution decisions must be correctable without losing original mentions.
9. Resolution must respect private and shared Entity boundaries.
10. The Memory Engine owns its entity-resolution records.

---

# 24. Memory Engine Ownership Summary

| Data Model | Authoritative Owner |
|---|---|
| Memory Source | Memory Engine |
| Memory Candidate | Memory Engine |
| Atomic Memory | Memory Engine |
| Entity | Memory Engine |
| Entity Relationship | Memory Engine |
| Memory Relationship | Memory Engine |
| Episode | Memory Engine |
| Episode Membership | Memory Engine |
| Derived Profile | Memory Engine |
| Profile–Memory Association | Memory Engine |
| Provenance Record | Memory Engine |
| Entity Mention | Memory Engine |
| Entity Resolution Record | Memory Engine |
| Embedding Metadata | Memory Engine |
| Memory Deletion Operation | Memory Engine |
| Memory Correction Request | Memory Engine |
| Candidate Evaluation Record | Memory Engine |
| Source Processing Event | Memory Engine |
| Profile Refresh History | Memory Engine |
| Memory Category Assignment | Memory Engine |
| Memory Consolidation Result | Memory Engine |
| Episode Timeline Event | Memory Engine |

The vector-indexing infrastructure may be shared or separately deployed, but the Memory Engine retains ownership of its embedding metadata and domain-specific indexing state.

---

# 25. Cross-Cutting Memory Integrity Rules

The following rules apply to every Memory Engine model:

1. Every record has a unique identity.
2. Every record belongs to a clearly defined ownership scope.
3. User-specific data remains isolated.
4. Original sources remain traceable.
5. Derived records retain source references.
6. Current and historical memory states remain distinguishable.
7. Importance and confidence remain separate.
8. Explicit and inferred memories remain distinguishable.
9. Similarity alone cannot establish identity or factual relationships.
10. Deletion propagates through all applicable dependencies.
11. Embeddings and profiles never become authoritative over original memories.
12. Historical corrections must preserve valid historical information.
13. Failed background operations must remain traceable.
14. No derived representation may introduce unsupported facts.

---

# 26. Deferred Implementation Decisions

The following topics are intentionally outside the scope of this document.

## Phase 6 — Algorithms & Processing Design

- Relevance Gate.
- Memory extraction.
- Candidate evaluation and promotion.
- Duplicate detection.
- Contradiction resolution.
- Entity resolution.
- Memory relationship discovery.
- Episode construction.
- Profile generation and refresh.
- Memory consolidation.
- Embedding generation.
- Retrieval ranking.
- Memory decay and forgetting.
- Deletion propagation and recovery.

## Phase 7 — Technology & Infrastructure Selection

- Database technology.
- Vector database.
- Content/object storage.
- Embedding model.
- Search/indexing infrastructure.
- Queue and messaging technology.
- Deployment and scaling architecture.

## Implementation Phases

- Production database schemas.
- Field names and types.
- Index definitions.
- Migrations.
- Repository and service implementation.
- Automated testing.
- Performance benchmarking.

---

# 27. Completion Status

**Phase 5.4 — Memory Engine Data Models: Architecturally Complete.**

All 34 decisions have been finalized and documented.

The Memory Engine data model establishes the foundation for subsequent algorithm design and implementation.

**Next:** Phase 5.5 — Research Engine Data Models.

---

<!-- Amendment reapplied from commit 3fd622b. Its text is unchanged except for corrected documentation paths. -->

# Phase 5 Amendment — Document Intelligence Data Models

## 1. Purpose

This amendment extends the Memory Engine data model to support document intelligence and Retrieval-Augmented Generation (RAG).

The existing personal memory model remains authoritative for user-related memories.

Document intelligence introduces a separate logical data domain for:

- Uploaded documents.
- Document versions.
- Extracted content.
- Document chunks.
- Chunk provenance.
- Document embeddings.
- Document processing operations.
- Document lifecycle and deletion dependencies.

The amendment must preserve the existing Memory Engine architecture and approved technology decisions.

It does not introduce a new engine or require a separate database deployment.

## 2. Data ownership

The Memory Engine owns both:

1. Personal memory records.
2. Document intelligence records.

However, the two domains must maintain separate logical models and processing lifecycles.

### Personal memory

Represents information about the user, including preferences, goals, decisions, events, relationships, knowledge, projects, and commitments.

### Document intelligence

Represents the content and structure of documents uploaded or authorized by the user.

Document content is not automatically personal memory.

Document chunks must never be treated as atomic memory records.

## 3. Document intelligence entities

The following are proposed logical entities. Their exact names, fields, and relationships must be reconciled with existing Phase 5 conventions before database implementation.

### 3.1 Document

Represents the identity of an uploaded document.

**Responsibilities:**

- Identify a document independently of its filename.
- Associate it with its owner.
- Maintain document-level metadata.
- Reference its current version where applicable.
- Track its lifecycle.
- Support document-level deletion.

**Logical attributes:**

| Attribute | Description |
|---|---|
| Document ID | Stable document identifier |
| User ID | Document owner |
| Title | Human-readable document title |
| Original filename | Uploaded filename |
| Detected media type | Validated file format |
| Created at | Registration timestamp |
| Updated at | Last metadata update |
| Current version ID | Reference to the applicable current version |
| Lifecycle status | Current document lifecycle state |

The document identifier must not depend on the original filename.

### 3.2 Document Version

Represents a specific content version of a document.

**Responsibilities:**

- Preserve historical document versions.
- Identify the exact source used during retrieval.
- Track version-specific extraction and indexing.
- Prevent updated documents from silently replacing historical content.

**Logical attributes:**

| Attribute | Description |
|---|---|
| Document Version ID | Unique version identifier |
| Document ID | Parent document |
| Version number | Version sequence |
| Object reference | Original file storage reference |
| Content checksum | Content integrity identifier |
| File size | Original file size |
| Detected media type | Validated format |
| Uploaded at | Upload timestamp |
| Processing status | Version processing state |
| Created at | Record creation timestamp |

A new upload that represents an update must create a distinct version according to the approved document-version policy.

The system must retain enough information to distinguish historical and current versions.

### 3.3 Extracted Document Representation

Represents content derived from a specific document version.

**Responsibilities:**

- Preserve extracted textual content.
- Preserve structural information.
- Associate extraction output with its source.
- Support downstream chunking.
- Track extraction metadata and failures.

**Logical attributes:**

| Attribute | Description |
|---|---|
| Extraction ID | Unique extraction identifier |
| Document Version ID | Source version |
| Extracted content reference | Text or durable content reference |
| Extraction method | Parser or extraction method |
| Extraction version | Parser or processing version |
| Structure metadata | Available headings, sections, tables, and layout |
| Extraction status | Processing status |
| Extracted at | Extraction timestamp |

Extracted content is derived data. The original uploaded document remains the authoritative source artifact.

The model must not require all extracted content to be stored directly in PostgreSQL if the approved storage architecture calls for object storage.

### 3.4 Document Chunk

Represents a retrieval unit derived from extracted document content.

**Responsibilities:**

- Divide extracted content into retrievable units.
- Preserve source ordering.
- Support vector and keyword retrieval.
- Maintain document-version provenance.
- Support citation generation.

**Logical attributes:**

| Attribute | Description |
|---|---|
| Chunk ID | Unique chunk identifier |
| Document Version ID | Source document version |
| Extraction ID | Source extraction |
| Chunk sequence | Position within the document |
| Content | Chunk text or content reference |
| Content checksum | Chunk integrity identifier |
| Chunking strategy | Strategy identifier |
| Chunking version | Chunking algorithm version |
| Created at | Chunk creation timestamp |

Chunking must preserve the relationship between each chunk and its original document version.

### 3.5 Chunk Location and Provenance

Represents the source location and evidence relationship of a document chunk.

**Responsibilities:**

- Identify where a chunk originated.
- Support page-level citations.
- Support section-level citations.
- Preserve structural location.
- Enable evidence verification.

**Logical attributes:**

| Attribute | Description |
|---|---|
| Location ID | Location record identifier |
| Chunk ID | Associated chunk |
| Document Version ID | Source version |
| Page number | Page reference, when available |
| Section or heading | Structural location |
| Start position | Starting content position, where available |
| End position | Ending content position, where available |
| Structural path | Hierarchical source location, where available |

Not every document format supports page numbers or the same location metadata.

Missing location metadata must remain explicitly unavailable rather than being fabricated.

### 3.6 Document Embedding Metadata

Represents the embedding information associated with a document chunk.

**Responsibilities:**

- Track embedding generation.
- Associate embeddings with the correct chunk and version.
- Support vector indexing.
- Track model and preprocessing versions.
- Support embedding regeneration and deletion.

**Logical attributes:**

| Attribute | Description |
|---|---|
| Embedding ID | Embedding record identifier |
| Chunk ID | Associated document chunk |
| Model identifier | Embedding model |
| Model version | Model version |
| Vector dimensions | Expected vector dimensions |
| Preprocessing version | Text preprocessing configuration |
| Created at | Embedding timestamp |
| Indexing status | Vector indexing state |

Embedding vectors must use the approved pgvector infrastructure initially.

Document embeddings and personal memory embeddings must remain logically distinct.

### 3.7 Document Processing Operation

Represents a processing operation performed on a document or document version.

**Responsibilities:**

- Track processing progress.
- Support retries.
- Record failures.
- Prevent duplicate work.
- Enable recovery.
- Support deletion coordination.

**Logical attributes:**

| Attribute | Description |
|---|---|
| Operation ID | Unique operation identifier |
| Document ID | Associated document |
| Document Version ID | Applicable version |
| Operation type | Parsing, chunking, embedding, indexing, deletion, etc. |
| Operation status | Current processing status |
| Idempotency reference | Retry and duplicate protection |
| Created at | Operation creation time |
| Updated at | Last status update |
| Error metadata | Structured failure information |

Exact operation types and statuses must follow the approved workflow contracts.

## 4. Personal memory model remains separate

The existing personal memory entities remain unchanged unless a separate approved amendment is required.

The document model must not replace or duplicate:

- Memory Source.
- Memory Candidate.
- Atomic Memory.
- Memory Revision.
- Entity.
- Entity Alias.
- Entity Mention.
- Entity Relationship.
- Memory Relationship.
- Episode.
- Episode Membership.
- Derived Profile.
- Profile-Memory Association.
- Memory Provenance.
- Memory Embedding Metadata.
- Category Assignment.
- Deletion Operation.
- Processing History.

The exact existing model names and relationships remain governed by the original Phase 5 specification.

## 5. Document-to-memory provenance

Document content may contribute evidence to a personal memory when the user explicitly authorizes extraction.

The relationship must be traceable.

A document-derived memory candidate must retain references to the relevant:

- Document.
- Document version.
- Extraction.
- Chunk.
- Source location, where available.
- Extraction method.

The exact provenance relationship must be reconciled with the existing Memory Provenance model.

Do not create a separate independent memory lifecycle for document-derived facts.

Document-derived facts must follow the normal workflow:

`Document Evidence → Memory Candidate → Evaluation → Resolution → Authoritative Memory`

Uploading or indexing a document must not automatically create personal memories.

## 6. Embedding domain separation

The system must support two logically separate embedding domains.

### Personal memory embeddings

Represent authoritative personal memory content.

### Document embeddings

Represent document chunks and support document retrieval.

Both domains may share PostgreSQL and pgvector infrastructure.

They must retain independent:

- Source associations.
- Ownership checks.
- Model metadata.
- Indexing status.
- Retrieval rules.
- Deletion dependencies.

Similarity across these domains must not be treated as proof that a document chunk is a personal memory.

## 7. Document lifecycle

A document version may pass through the following logical lifecycle:

`Registered → Validated → Stored → Parsing → Extracted → Chunked → Embedded → Indexed`

It may also enter:

- Failed.
- Retry pending.
- Deletion requested.
- Deleting.
- Deleted.

These states are conceptual and must be reconciled with the existing operation and lifecycle model.

A document must not be marked fully processed if required extraction or indexing operations remain incomplete.

## 8. Relationships

The proposed logical relationships are:

- One Document may have multiple Document Versions.
- One Document Version belongs to one Document.
- One Document Version may have multiple extraction operations or representations, according to the versioning policy.
- One Extracted Representation belongs to a Document Version.
- One Extracted Representation may produce multiple Document Chunks.
- One Document Chunk belongs to one Document Version.
- One Document Chunk may have one or more location references where required.
- One Document Chunk may have associated embedding representations.
- One Document may have multiple processing operations.
- A document-derived Memory Candidate may reference one or more supporting document chunks.
- An authoritative Memory may preserve provenance from its originating candidate and supporting sources.

Relationship cardinality must be confirmed against the existing data model and actual requirements.

Do not create unnecessary many-to-many relationships.

## 9. Deletion dependencies

Document deletion must cover the applicable dependency chain:

`Document → Versions → Original Objects → Extracted Representations → Chunks → Embeddings → Indexes → Caches → Pending Operations`

The system must also identify document-derived memory provenance.

Deleting a document must not automatically delete unrelated personal memories.

Where a memory depends exclusively on deleted evidence, the approved deletion and provenance policy must determine the appropriate action.

Deletion must be recoverable and idempotent.

## 10. Security and ownership

Every document and derived document representation must remain scoped to its authorized owner.

Ownership must propagate through:

- Document.
- Document Version.
- Extracted Representation.
- Document Chunk.
- Chunk Embedding.
- Processing Operation.
- Retrieval Result.

Do not rely only on client-provided identifiers for authorization.

Validate access through the approved ownership model.

Document content must be treated as untrusted input.

## 11. Storage strategy

Follow the approved Phase 7 storage architecture.

- PostgreSQL stores authoritative metadata and relational records.
- S3-compatible object storage stores original documents and large content artifacts where appropriate.
- pgvector stores approved vector representations.
- PostgreSQL full-text search supports keyword retrieval.

Do not introduce a separate document database or vector database as part of this amendment.

## 12. Schema implementation rules

Before implementing these logical entities:

1. Inspect existing Phase 5 data-model documents.
2. Identify any existing models that already support the proposed responsibilities.
3. Reuse existing models where appropriate.
4. Avoid duplicate entities.
5. Confirm relationship cardinality.
6. Confirm ownership enforcement.
7. Confirm lifecycle and deletion dependencies.
8. Update the approved data-model documentation.
9. Only then implement database migrations.

This amendment does not claim that these entities already exist in the database.

## 13. Acceptance criteria

The document intelligence data model is ready for implementation when:

1. Document identity is independent of filenames.
2. Document versions preserve historical content references.
3. Extracted content retains source-version provenance.
4. Document chunks retain source and location references.
5. Document embedding metadata is version-aware.
6. Processing operations support idempotency and recovery.
7. Document and personal memory models remain separate.
8. Document-derived memory provenance is traceable.
9. Deletion dependencies are discoverable.
10. User ownership is enforced throughout the model.
11. The model is consistent with the approved PostgreSQL and pgvector architecture.
12. All schema decisions are reconciled with the existing Phase 5 specification.

**Final principle:** Documents represent source material. Personal memories represent validated information about the user. Raven must preserve this distinction throughout the data lifecycle.

## 14. Persisted vocabularies and schema (Phase 8.2 step 2)

**Approved 2026-11-11.** Sections 7 above and 5.10 §6.1–6.3 describe these states as conceptual. The persisted values are:

| Vocabulary | Values | Source |
|---|---|---|
| Document lifecycle (availability) | `registered`, `available`, `deletion_requested`, `deleting`, `deleted` | 5.10 §6.1 |
| Version processing status | `registered`, `validated`, `stored`, `parsing`, `extracted`, `chunked`, `embedded`, `indexed`, `validation_failed`, `extraction_failed`, `processing_failed`, `retry_pending`, `deletion_requested`, `deleting`, `deleted` | §7 above + 5.10 §6.2 |
| Extraction status | `extracted`, `partially_extracted`, `extraction_failed` | new |
| Embedding status | `pending`, `generating`, `generated`, `indexing`, `indexed`, `failed`, `superseded`, `deletion_pending` | Decision 5.4.20 |
| Operation status | `created`, `queued`, `running`, `completed`, `failed`, `retry_pending`, `cancellation_requested`, `cancelled` | 5.10 §6.3 |
| Operation type | `validation`, `storage`, `extraction`, `structure_extraction`, `normalization`, `chunking`, `embedding`, `indexing`, `deletion` | memory/05 §3 stages |
| Media type | `application/pdf`, DOCX (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`), `text/plain` | security rules (PDF, DOCX, TXT only) |
| Personal-memory evidence status | `active`, `source_deleted` | 7.1 §23.3 |

Deliberately not persisted: a version `superseded` state (derived from the document's current-version reference, never stored twice); `interrupted` (recorded as `retry_pending`); `indexing_incomplete` (the version stays `embedded`).

**Schema decisions made during implementation** (7.1 §23.3 holds the placement decision):
- **Records → tables:** §3.1 `doc_document`, §3.2 `doc_document_version`, §3.3 `doc_extracted_representation`, §3.4 `doc_chunk`, §3.5 `doc_chunk_location`, §3.6 `doc_embedding`, §3.7 `doc_processing_operation`. Document-derived evidence (§5) is `pm_document_evidence_ref`, owned by Personal Memory and attached to a Memory Candidate; `pm_provenance` cites it through `document_evidence_id`.
- **No version mixing:** a chunk references its representation through `(representation_id, version_id)`, so a chunk can never combine two versions (memory/05 §8.7).
- **Locations:** one-to-many per chunk with an explicit `ordinal`; unknown fields stay NULL, and at least one field must be known.
- **Immutability:** representations, chunks and locations are append-only. Versions, embeddings, operations and documents may change only their status columns (database trigger `me_guard_columns`).
- **Evidence and deletion:** an evidence row keeps two sets of identifiers. Linked columns (`document_id`, `version_id`, `chunk_id`) have `RESTRICT` foreign keys, so active evidence blocks deletion of the passage it cites. Opaque copies (`document_ref`, `version_ref`, `chunk_ref`) have no foreign key and are never cleared. Marking evidence `source_deleted` clears the linked columns (enforced by a check constraint), which lets the document be deleted while provenance stays traceable. Memories are never deleted by this step; the deletion policy (8.10) decides.
- **Keyword search:** `doc_chunk.tsv` is a stored `tsvector` using the language-neutral `simple` text-search configuration, with a GIN index. The language requirement (gap G6) is still open; changing the configuration later is one migration that rebuilds the column.
- **Embedding vectors:** none yet. Metadata only, unique per chunk, model, revision and preprocessing version; vector storage arrives in 8.7 (7.1 §23.5).

## 15. Document ingestion rules (Phase 8.3 step 3)

**Approved 2026-11-11.** Ingestion accepts and registers uploads; the document pipeline parses them (Decision 13).

**Format and filename:**
- **Format comes from the content:**
  - PDF: header and `%%EOF` trailer;
  - DOCX: a ZIP containing `word/document.xml`, checked from the file listing only; macro parts, encrypted entries and archives that expand excessively are refused;
  - TXT: UTF-8 with no NUL bytes.
- The filename extension and any declared media type must agree with the content.
- Uploads are limited to 25 MiB by default (configurable; 7.6 §18 still defers the final value).
- **Filenames** are kept only as display names (last path component, no control characters) and never appear in object keys.

**Re-uploads:**
- An upload without a document ID always creates a new document, even when its content matches another one (checksums never merge identities, plan 8.3 §8).
- An upload naming a document creates its next version. It is refused if it is identical to the current version or if the media type changes.

**On success:**
- The original is stored first, then the document is `registered` and the version `stored`.
- An `extraction` processing operation is created (`created`) for the pipeline. Nothing is marked processed.
- The request's idempotency key is the operation's key (prefixed `upload:`). A retry returns the same registration, and a reused key with different content is refused.

**Not done:** no malware scan, because no tool is approved. This deferral was accepted by the owner and is recorded in `KNOWN_CONSTRAINTS.md`.

---

<!-- Phase 8.2 amendment, approved by the project owner on 2026-11-11 (Decision 4 of the Phase 8.2 architecture decision review). Appended; earlier text unchanged. -->

# Phase 8.2 Amendment — Relationship Vocabularies and Atomic Memory Lifecycle

## 1. Purpose

Reconcile the relationship and state vocabularies that differ across Decision 5.4.27, Phase 6 algorithms 6.3.7 and 6.3.8, retrieval 6.4.5 and plan 8.5 §7. It also defines the Atomic Memory lifecycle states, which no earlier document specified (Phase 6.2 §8.6 notes that candidate states "are not the final Atomic Memory lifecycle states"; Decision 5.3.6 delegates state definitions to each engine).

This amendment extends Decisions 5.4.7, 5.4.15, 5.4.26 and 5.4.27. It does not remove any of their rules. Analysis and alternatives: [Phase 8.2 architecture decision review](../project-context/PHASE-8-2-ARCHITECTURE-DECISION-REVIEW.md) §5.4.

## 2. Naming conventions

- Vocabulary values are lowercase `snake_case` strings, enforced by database check constraints.
- A relationship reads **"source ‹type› target"** in active voice. Passive inverses (for example "superseded by") are never stored; they are derived at query time.
- Symmetric types are flagged explicitly and stored once, with a canonical ordering (lower identifier as source), per Decision 5.4.15 rule 5.
- Temporal meaning is carried by attributes (section 7), not by relationship names.

## 3. Entity relationships (Entity → Entity)

Typed, directed records per Decision 5.4.15. Each carries valid time, transaction time, confidence, provenance and scope. Rows are closed with `valid_to` and replaced, never overwritten.

| Type | Meaning (source → target) | Symmetric |
|---|---|---|
| `works_at` | person → organization | No |
| `member_of` | person or organization → group or organization | No |
| `reports_to` | person → person | No |
| `knows` | person ↔ person | Yes |
| `part_of` | entity → containing entity | No |
| `located_in` | entity → location | No |
| `uses` | project, person or organization → technology or product | No |
| `acquired_by` | organization → organization (identity event, Decision 5.4.14) | No |
| `merged_into` | organization → organization (identity event) | No |
| `renamed_to` | entity → successor identity, when identity changes rather than an alias (Decision 5.4.14) | No |
| `related_to` | weak, unspecified association (last resort) | Yes |

The catalogue is extended only by approval. Private relationships may reference shared entities, never the reverse (Decision 5.4.13).

## 4. Memory relationships (Atomic Memory → Atomic Memory)

Independent records per Decision 5.4.27. Both endpoints are Atomic Memories.

| Type | Meaning (source → target) | Effect on target | Symmetric |
|---|---|---|---|
| `supports` | source is independent evidence for target | none | No |
| `contradicts` | both cannot hold in the same context and time | both kept; may trigger `needs_review` | Yes |
| `supersedes` | source replaces target as the current representation | target becomes `historical`; `valid_to` set | No |
| `updates` | source refines target, which remains current | none | No |
| `part_of` | source is a component of target | none | No |
| `derived_from` | source (an inferred memory) was derived from target (its evidence) | none | No |
| `depends_on` | source's validity is conditional on target (added from 6.3.8) | re-evaluate source when target changes | No |
| `related_to` | weak association (last resort) | none | Yes |

A `supersedes` relationship records a `reason`: `temporal_change` (a progression, such as moving city), `replacement`, or `correction` (when the erroneous fact was a separate memory).

**Reconciliation with Phase 6 and plan 8.5:**
- `ABOUT_ENTITY` (6.3.8, 6.4.5) is not a memory relationship. It is represented as a **Memory–Entity association** (section 5).
- "Corrects" (plan 8.5 §7) is not a relationship. Correcting the same fact creates a new revision with change type `corrected` (Decision 5.4.26). A correction by a different memory is `supersedes` with reason `correction`.

## 5. Memory–Entity associations

Record which entities an Atomic Memory concerns (plan 8.5 §7, "entity-to-memory associations"), with a `role` of `subject`, `object`, `mentioned` or `context`. These are distinct from Entity Relationships (section 3) and Memory Relationships (section 4).

## 6. Revision change types

Each immutable Atomic Memory revision (Decision 5.4.7) records one change type. The 6.3.7 supersession types map as shown.

| Value | Replaces 6.3.7 | Meaning |
|---|---|---|
| `created` | — | first revision |
| `updated` | `UPDATED_BY` | attribute or context change (6.3.6) |
| `corrected` | `CORRECTED_BY` | the prior content was wrong (Decision 5.4.26) |
| `evidence_added` | — | duplicate or merge evidence attached (outcomes `merge` / `no_change`) |
| `superseded` | `SUPERSEDED_BY` | the memory stopped being current because another memory `supersedes` it |
| `expired` | `EXPIRED` | time-limited validity ended |
| `retracted` | `RETRACTED` | the user withdrew the assertion |
| `reclassified` | — | category or origin change (Decision 5.4.9) |

## 7. Atomic Memory lifecycle status

| Status | Meaning | Retrievable by default |
|---|---|---|
| `active` | the current accepted understanding | Yes |
| `historical` | superseded or expired, retained for history | Only for historical or temporal queries |
| `needs_review` | unresolved contradiction or insufficient evidence | No; flagged when requested |
| `retracted` | withdrawn by the user | No |
| `deletion_pending` | tombstoned; deletion propagation in progress | **Never** |
| `deleted` | deletion complete; only a minimal tombstone remains | **Never** |

This status is separate from candidate states (6.2 §8.6), retention classifications (6.5.3), deletion operation states (6.5.8) and embedding lifecycle states (Decision 5.4.20).

## 8. Temporal attributes

Per the bitemporal model (Decision 5.3.4; 6.3.7 §9.3), memories and relationships carry:
- `valid_from` / `valid_to`: when the information was true in the world
- `recorded_at` / `superseded_at`: when Raven recorded or replaced it
- `observed_at`: when the source stated it

A "progression" is `supersedes` with reason `temporal_change` plus continuous valid time.

## 9. Evidence and derived knowledge

- **Evidence** is recorded in Provenance Records (Decision 5.4.18) linking a memory to its source, candidate or document evidence, with a `role` of `origin`, `supporting`, `contradicting` or `correcting`. This is distinct from the memory-to-memory `supports` relationship.
- **Derived knowledge** (episodes, semantic consolidation results, profiles) links to its source Atomic Memories through its own association records (Episode Membership, Profile–Memory Association, Consolidation Result sources). Derived records never become Atomic Memories.

## 10. Resolution outcomes

The resolution outcomes of Phase 6.3 remain unchanged: `create_new`, `merge`, `update_existing`, `link_existing`, `supersede`, `needs_review`, `reject`, `no_change`. They are processing decisions recorded in resolution audit, not stored relationships.

## 11. Memory Source processing states

**Approved 2026-11-11** (Phase 8.2 implementation). Decision 5.4.28 requires a Memory Source to maintain its current processing status but no document enumerated the values. They are derived from the ingestion outcomes (6.2.1 §3.7) and extraction outcomes (6.2.2) that describe a *stored* source, plus one in-progress state implied by the 6.2.1 pseudocode (`ALREADY_PROCESSING`).

| Status | Meaning |
|---|---|
| `validated` | input accepted and preserved |
| `queued` | waiting for asynchronous processing |
| `processing` | extraction in progress |
| `extracted` | extraction finished |
| `partially_extracted` | some content extracted (6.2.2) |
| `rejected` | rejected by validation or policy |
| `parsing_failed` | content could not be normalized |
| `processing_failed` | pipeline failed; retryable |

`invalid_input`, `unsupported_input`, `access_denied` and `ownership_validation_failed` are request outcomes, not source states: no Memory Source is stored for them. Transitions and their events (Source Processing Event, Decision 5.4.28) are defined with the ingestion pipeline (plan 8.3).

## 12. Entity vocabularies and persistence rules (Phase 8.2 step 3)

**Approved 2026-11-11.** Decisions 5.4.13, 5.4.33 and 5.4.34 require these states but did not enumerate them.

| Vocabulary | Values | Source |
|---|---|---|
| Entity scope | `private`, `shared` — **only `private` permitted** (Decision 11; 7.1 §23.7) | 5.4.13 |
| Entity and mention type | `person`, `organization`, `project`, `product`, `place`, `institution`, `technology`, `event`, `other`, `unknown` | 6.3.4 §6.1, plus `unknown` so uncertainty is kept rather than forced (plan 8.5) |
| Entity status | `active`, `merged`, `deletion_pending`, `deleted` | new |
| Mention resolution status | `unresolved`, `resolved`, `ambiguous`, `needs_review` | 5.4.33–5.4.34 |
| Resolution outcome (history) | `matched_existing`, `created_new`, `left_unresolved`, `sent_to_review`, `corrected`, `reassigned`, `merged` | 6.3.4 §6.2 outcomes; 5.4.34 corrections, reassignments, merges |

`other` means identifiable but not one of the listed types; `unknown` means the type could not be determined.

**Persistence rules:**
- **Mentions** keep their original wording permanently; only the resolution (status, entity, confidence) may change. A mention is `resolved` exactly when it names an entity.
- **Resolution records** are append-only history:
  - mention outcomes name the mention;
  - `merged` names no mention, and records the merged entity (`previous_entity_id`) and the survivor (`entity_id`);
  - `corrected` and `reassigned` record the entity they replace, and the database refuses them unless the mention still points at that entity.
  - History is ordered by `(recorded_at, seq)`, where `seq` is an insertion counter, because `created_at` is identical within one transaction.
- **Merges** never delete. The merged entity keeps its row with `status = 'merged'` and `merged_into_id`, and existing mentions keep pointing at it, so a merge can be corrected. Merged entities take no new references and drop out of candidate lookup; `canonical()` follows merges to the survivor.
- **Aliases** are unique per entity after normalization (trimmed, case-folded, whitespace collapsed). The same alias may belong to several entities: alias lookup returns candidates only and never establishes identity (5.4.14).
- **Relationships** (section 3 for entities, section 4 for memories) are stored once in canonical order when symmetric. At most one *current* row exists per endpoint pair and type (a partial unique index on `superseded_at IS NULL`), and closing sets `valid_to`/`superseded_at` only. Persisting `supersedes` does not itself change the target memory; resolution (8.6) applies the effect in the same unit of work.
- **Memory–Entity associations** (section 5) are append-only and unique per memory, entity and role.

## 13. Episodes, profiles, categories and memory embeddings (Phase 8.2 step 4)

**Approved 2026-11-11.** Decisions 5.4.16–5.4.23 and 5.4.29–5.4.32 define these records, but their states were either undefined or given only as examples (6.5.6 "Profile categories — Examples").

| Vocabulary | Values | Source |
|---|---|---|
| Episode status | `active`, `needs_refresh`, `needs_review`, `deletion_pending`, `deleted` | 5.4.16 rule 8 ("may trigger review or refresh") |
| Temporal precision | `exact`, `day`, `month`, `year`, `approximate`, `unknown` | 5.4.30 ("precision and uncertainty are preserved") |
| Profile type | `user`, `preference`, `project`, `skill_knowledge`, `relationship_context`, `work_context` | 6.5.6 examples |
| Profile status | `current`, `stale`, `refreshing`, `refresh_failed`, `needs_review`, `deletion_pending`, `deleted` | 5.4.32 |
| Refresh trigger | `event`, `scheduled`, `on_demand` | 6.5.1 trigger categories |
| Refresh outcome | `refreshed`, `no_change`, `partially_refreshed`, `failed`, `needs_review` | 5.4.32; 6.5.6 |
| Memory category | `personal_preference`, `goal`, `decision`, `important_event`, `relationship`, `knowledge`, `project`, `commitment` | 5.4.9 taxonomy |
| Embedding purpose | `primary`, `aspect` | 5.4.21 |
| Embedding status | the 5.4.20 values (as in Document Intelligence §14) | 5.4.20 |

The embedding status vocabulary is now defined once, in the shared kernel, and used by both memory and document embeddings; the two kinds stay in separate tables.

**Persistence rules:**
- **Unknown dates:** a time whose precision is `unknown` has no value, and a known precision requires one. This applies to episode start and end and to timeline events (5.4.30).
- **Episodes:**
  - membership has no role column, because 5.4.29 says membership "may" carry a role and no roles are defined;
  - removing a member closes the row (`removed_at`), and at most one current membership exists per episode and memory;
  - timeline corrections close the old event and add a new one, so the earlier understanding stays (5.4.30);
  - an episode carries a `version` that every update must name and increment, so concurrent edits are detected rather than overwritten (added by migration `0006` after the 8.2 acceptance review; 7.2 §7).
- **Profiles:**
  - content lives in append-only revisions, and the profile points at its current revision (5.4.32);
  - each revision lists its supporting memories together with the memory *revision* used (5.4.31). The foreign key guarantees that version exists, which makes a profile reproducible (6.5.6).
- **Refresh history** is append-only and ordered by `(recorded_at, seq)`:
  - `refreshed` and `partially_refreshed` create the next revision, and the other outcomes create none;
  - `failed` carries a safe error code;
  - a partial or failed refresh never leaves a profile `current`, and only `refreshed` and `no_change` update `refreshed_at` (6.5.6).
- **One live profile per kind:** at most one profile that isn't `deleted` per owner and type, or per owner, type and subject entity.
- **Category assignments** record origin (explicit or inferred) and confidence. A change closes the old row (5.4.22), and at most one assignment per memory and category is current.
- **Memory embeddings** are metadata only (vectors come in 8.7). Each belongs to one memory revision (5.4.19 rule 2), with at most one `primary` per memory revision, model, model revision and preprocessing version. An `aspect` embedding carries a label.
- **No consolidation-result table.** 5.4.23 says established consolidation outputs reuse Episodes and Derived Profiles, and that independent records are created only for result types that don't fit. None is defined yet, so a record type is added when Phase 8.9 defines one (no placeholder tables).

## 14. Processing, evaluation, correction and deletion records (Phase 8.2 step 5)

**Approved 2026-11-11.** Decisions 5.4.24–5.4.26 and 5.4.28 require these records; 6.2.3 §6.7 and 6.5.8–6.5.9 give some of their values, and the rest were not enumerated.

| Vocabulary | Values | Source |
|---|---|---|
| Processing event type | `transition`, `failure`, `retry`, `recovery` | 5.4.28 ("transitions, failures, retries and recovery") |
| Evaluation outcome | `proceed`, `needs_review`, `reject`, `defer` | 6.2.3 §6.7 |
| Correction status | `open`, `accepted`, `rejected`, `withdrawn`, `deleted` | 5.4.26 rules 3 and 7; `deleted` for 5.4.24 rule 7 |
| Deletion request kind | `user_request`, `account`, `administrative`, `system` | 6.5.8 B and C |
| Deletion operation status | `requested`, `validating`, `approved`, `in_progress`, `propagating`, `verifying`, `completed`, `partially_completed`, `failed`, `requires_reconciliation` | 6.5.8 |
| Deletion target kind | one value per `pm_` table without the prefix, except the deletion tables | 6.5.9 dependency inventory |
| Deletion action | `delete`, `invalidate`, `refresh` | 6.5.9 required handling |
| Deletion target state | `pending`, `propagated`, `verified`, `failed` | 6.5.9 propagation and verification |

**Persistence rules:**
- **Processing events** (5.4.28) are append-only and ordered by `(occurred_at, seq)`. Each event changes the source status, and the source status and the event are written together, conditional on the expected status. Only `failure` events carry an error code.
- **Candidate evaluations** (5.4.25) are append-only. Recording one updates the candidate's latest state (its status, plus any scores the evaluation carries) in the same write. An outcome limits the resulting status: `proceed` → `candidate` or `validated`, `needs_review` → `needs_review`, `reject` → `rejected`, `defer` → `candidate`. Evaluations hold scores and a reason code, never the proposition. The source and candidate tables now allow updates only to their state columns.
- **Correction requests** (5.4.26) are for complex corrections only; simple ones remain a new Atomic Memory revision. Each request lists the affected memories with the revision it was based on. Acceptance names, for every affected memory, the later revision that applied it; rejection and withdrawal name none, so they never change a memory. `deleted` drops the proposed change, the evidence references and the note.
- **Deletion operations** (5.4.24; 6.5.8):
  - one operation per owner and idempotency key;
  - finished (`completed`, `partially_completed`, `failed`) exactly when `finished_at` is set; `failed` carries an error code, and `completed` has none;
  - `completed` is refused unless every ledger row is `verified` (6.5.9).
- **The deletion ledger** has one row per affected record: its kind, its identifier, whether the request named it directly, the action, the state and the attempt count. Rows move `pending` → `propagated` → `verified`; `failed` can return to `pending`. There is no foreign key to the record, so the row outlives a purged record and can be replayed after a restore (6.5.9 backup handling). Nothing in the ledger holds content (5.4.24 rule 7).
- **Policy-driven forgetting** (6.5.8 A) and simple deletions (5.4.24 rule 3) create no operation.
- **Error and reason codes** are UPPER_SNAKE_CASE codes, never free text, so they cannot carry user content.

## 15. Ingestion fields on the Memory Source (Phase 8.3 step 2)

**Approved 2026-11-11.** Plan 8.3 §5–8 and algorithm 6.2.1 need instruction, priority and retry-safety data for each accepted input. The owner chose to extend the Memory Source rather than add an ingestion-operation table. Rejected inputs create no Memory Source (§11), so there is nothing else to track.

| Vocabulary | Values | Source |
|---|---|---|
| Instruction type | `normal`, `remember`, `forget` | 6.2.1 step 8 |
| Ingestion priority | `normal`, `high` | 6.2.1 step 9 (a scheduling signal, not importance) |

**Fields added to `pm_memory_source` (migration `0007`):**
- `instruction_type`, `priority`;
- `idempotency_key`, unique per owner, with `request_sha256`, a fingerprint of the request that excludes the receipt time;
- `source_ref` (external source identifier), `source_timestamp`;
- `normalized_ref` (object key of the normalized representation, kept apart from the original, 6.2.1 AC-05).

**Rules:**
- A key always comes with its fingerprint. Reusing a key for a different request is refused; repeating the same request returns the existing source.
- Explicit `remember` and `forget` instructions are always `high` priority.
- These fields are immutable once written (the 0005 column guard).
- A `forget` instruction is stored and never handed to extraction. Plan 8.10 resolves what it targets.
- Original and normalized content live in object storage under `memory-sources/{owner}/{source}/original` and `/normalized`.

## 16. Deferred sources and reason codes (Phase 8.4 step 1)

**Approved 2026-11-12.** Section 11 listed no state for "held for later processing", although 6.2.2 has a `DEFER` outcome and the English-first decision (G6) defers non-English sources. Also, only `failure` events could carry a code, so a rejection or deferral could not say why. Migration `0009`.

- **New Memory Source state `deferred`:** held for controlled later processing, never discarded. A deferred source may later return to `queued` when its blocker is lifted (for example, when multilingual support is approved).
- **`reason_code` on Source Processing Events:** an UPPER_SNAKE_CASE code, required exactly for transitions into `deferred` or `rejected` (for example `UNSUPPORTED_LANGUAGE`). `error_code` stays for `failure` events only.
- **Extraction transitions (8.4):** `queued` → `processing` → outcome, written in one transaction with the candidates, where the outcome is `extracted`, `partially_extracted`, `rejected`, `deferred`, `parsing_failed` or `processing_failed`. When the worker's retries run out, `queued` → `processing_failed`. The explicit reprocess goes `processing_failed` → `validated` as a `retry` event, and the handoff is re-armed.

## 17. Relevance assessments (Phase 8.4 step 2)

**Approved 2026-11-12.** 6.2.2 step 8 requires storing each relevance decision with its reason, score metadata and processing version. No record held it. Migration `0010`.

- **Relevance Assessment** (`pm_relevance_assessment`): one row per extraction run of a Memory Source. It holds:
  - the outcome (`process`, `defer` or `reject`) and a reason code, required exactly for `defer` and `reject`;
  - the method and method version;
  - per-sentence results as JSON: segment and sentence position, outcome, reason or protection code, score, and the signals that were evaluated.
  - It never holds the text.
- It is append-only, owner-scoped, and written in the same transaction as the source's outcome.
- **Deletion:** `relevance_assessment` is a deletion target kind, so plan 8.10 removes the records with their source.
- **Vocabulary:** relevance outcome `process`, `defer`, `reject` (6.2.2 §4.6).
