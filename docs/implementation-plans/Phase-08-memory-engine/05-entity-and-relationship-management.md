# Phase 8.5 — Entity & Relationship Management Implementation Plan

## 1. Objective

Implement the Memory Engine's entity and relationship management capabilities.

The system must identify entities referenced in memory candidates, maintain their identities and aliases, associate mentions with source evidence, and represent meaningful relationships between entities and memories.

Entities provide contextual structure across individual memories.

For example, if Raven extracts these facts:

- The user is working on Raven.
- Raven uses Python.
- Raven uses PostgreSQL.
- The user is developing Raven's retrieval system.

The entity management system should recognize that these facts refer to related entities and maintain their associations.

### Primary objectives

- Identify entities in memory candidates.
- Create and maintain entity records.
- Support entity types and aliases.
- Track entity mentions.
- Associate entities with memory records.
- Represent entity-to-entity relationships.
- Represent memory-to-memory relationships.
- Preserve provenance.
- Maintain user isolation.
- Provide reliable entity and relationship persistence.

## 2. Architecture references

Claude Code must review:

1. `PROJECT_ARCHITECTURE.md`
2. `docs/architecture/` — Memory Engine architecture.
3. `docs/data-models/` — approved Memory Engine data models.
4. `docs/algorithms/memory/02-memory-resolution.md`
5. `docs/algorithms/memory/01-memory-ingestion-extraction.md`
6. `docs/algorithms/shared/01-shared-algorithm-framework.md`
7. `docs/technology/01-baseline-technology-stack.md`
8. `docs/technology/02-database-and-storage-architecture.md`
9. `docs/implementation-plans/phase-08-memory-engine/02-database-and-persistence.md`
10. `docs/implementation-plans/phase-08-memory-engine/04-extraction-and-evaluation.md`

The approved Phase 5 data models are authoritative.

Do not invent new entity or relationship types without identifying the architectural gap and reporting it first.

## 3. Scope

### Included

- Entity identification.
- Entity type classification.
- Entity record creation.
- Entity aliases.
- Entity mentions.
- Entity-to-memory associations.
- Entity-to-entity relationships.
- Memory-to-memory relationships.
- Provenance tracking.
- Entity and relationship persistence.
- Ownership and access control.
- Unit and component testing.

### Excluded

- Final duplicate entity resolution.
- Contradiction resolution.
- Memory merging.
- Memory supersession.
- Memory retrieval and ranking.
- Vector embedding generation.
- Memory consolidation.
- Derived profile generation.
- Forgetting and deletion execution.
- Document RAG.

Duplicate and contradiction resolution belong to Phase 8.6.

## 4. Entity management architecture

Implement the following logical components.

### 4.1 Entity Identifier

Responsibilities:

- Identify entity mentions in validated memory candidates.
- Extract entity names and available contextual information.
- Identify potential entity types.
- Preserve the originating memory reference.
- Preserve source evidence.
- Produce entity identification results.

Entity identification may use conventional NLP and deterministic rules.

Approved technology candidates include spaCy and other selected Phase 7 NLP components.

Entity identification must not assume that every recognized name represents a unique entity.

For example, two different people can have the same name.

### 4.2 Entity Classifier

Classify entities using the approved entity type model.

Potential categories include:

- Person.
- Organization.
- Project.
- Product.
- Place.
- Concept.
- Event.
- Other approved entity types.

The implementation must use the actual approved entity type definitions from the Phase 5 data model.

Do not create an independent classification taxonomy that conflicts with the existing model.

Where an entity type cannot be confidently determined, preserve uncertainty rather than forcing an incorrect classification.

### 4.3 Entity Registry

Responsibilities:

- Create entity records.
- Maintain entity identifiers.
- Associate entities with their owner.
- Store canonical names.
- Maintain entity metadata.
- Track creation and update timestamps.
- Provide entity lookup interfaces.

Entity identifiers must be stable.

Entity records must be scoped according to the approved ownership model.

Do not expose one user's private entity records to another user.

### 4.4 Alias Management

Aliases allow Raven to recognize different names or references that may refer to the same entity.

Examples:

- Full name and shortened name.
- Project name and project abbreviation.
- Company name and commonly used short name.
- Product name and alternative spelling.

Responsibilities:

- Store approved aliases.
- Associate aliases with entity records.
- Preserve alias provenance where supported.
- Support alias lookup.
- Handle case and whitespace normalization.
- Avoid treating every similar name as an alias.

An alias is not proof of identity.

Ambiguous alias matches must remain unresolved until the resolution process determines the correct association.

### 4.5 Entity Mention Manager

An entity mention represents an occurrence of an entity within a source or memory.

Responsibilities:

- Associate identified mentions with source records.
- Associate mentions with memory candidates.
- Preserve available offsets or evidence locations.
- Preserve source timestamps.
- Track the identification method.
- Support multiple mentions of the same entity.

The system must distinguish an entity record from an occurrence of that entity.

Do not collapse multiple mentions into a single mention record.

### 4.6 Entity Relationship Manager

Represent meaningful relationships between entities.

Examples:

- Person works at Organization.
- User owns Project.
- Project uses Technology.
- Product belongs to Organization.
- Person is associated with Project.

Relationship records should follow the approved Phase 5 model.

Preserve:

- Relationship type.
- Source entity.
- Target entity.
- Evidence references.
- Temporal context.
- Confidence where defined.
- Creation and update metadata.

Do not infer relationships solely because two entities appear in the same sentence or document.

### 4.7 Memory Relationship Manager

Represent meaningful relationships between memory records.

Examples:

- Related memories.
- Supporting memories.
- Corrective relationships.
- Temporal progression.
- Derived relationships.
- Other approved relationship types.

This milestone may create and persist supported relationship records.

However, final decisions about duplicate, contradictory, superseding or merging memories belong to Phase 8.6.

Do not use relationship creation to silently resolve conflicting facts.

## 5. Entity identification workflow

Implement the following logical sequence:

1. Receive a validated memory candidate.
2. Read its fact content and provenance.
3. Identify entity mentions.
4. Normalize mention representations.
5. Classify potential entity types.
6. Search for possible existing entities using approved lookup interfaces.
7. Create new entity records where identity is sufficiently established.
8. Preserve ambiguous matches as unresolved references for Phase 8.6.
9. Register entity mentions.
10. Associate entities with relevant memory candidates.
11. Create supported entity relationships.
12. Create supported memory relationships.
13. Persist records and provenance.
14. Record processing status.

Do not assume that a name match is sufficient to establish entity identity.

## 6. Entity matching boundaries

This phase may perform basic candidate lookup to avoid unnecessary entity creation.

However, it must not independently make complex identity-resolution decisions.

Examples requiring later resolution:

- Two people share the same name.
- A company and product share a name.
- A project changes its name.
- A short name matches multiple entities.
- An alias conflicts with an existing canonical name.
- A person is mentioned without sufficient identifying context.

Use the following distinction:

| Operation | Milestone |
|---|---|
| Recognize a named entity | Phase 8.5 |
| Identify its possible type | Phase 8.5 |
| Search for possible matches | Phase 8.5 |
| Create a clearly identifiable entity | Phase 8.5 |
| Manage approved aliases | Phase 8.5 |
| Resolve ambiguous identities | Phase 8.6 |
| Merge duplicate entities | Phase 8.6, if supported by the approved model |
| Resolve identity conflicts | Phase 8.6 |

The system must not create duplicate entities simply because the lookup mechanism cannot immediately establish identity.

## 7. Relationship modeling

Use the existing relationship models.

### Entity-to-entity relationships

Represent relationships between two entities.

Example:

Person → works_at → Organization

Project → uses → Technology

### Entity-to-memory associations

Represent which entities are referenced by a memory.

Example:

Memory: "Raven uses PostgreSQL."

Associations:

- Raven.
- PostgreSQL.

### Memory-to-memory relationships

Represent relationships between memory records.

Example:

- A memory supports another memory.
- A memory corrects another memory.
- Two memories describe different stages of the same project.

Only create relationships when supported by available evidence.

### Temporal relationships

Where the approved model supports temporal information, preserve:

- Valid-from timestamp.
- Valid-to timestamp.
- Source observation timestamp.
- Relationship creation timestamp.

Do not assume that a current relationship was always true historically.

## 8. Confidence and provenance

Entity identification and relationship creation must preserve evidence.

For every relevant entity mention or relationship, retain the available:

- Source identifier.
- Ingestion identifier.
- Memory identifier.
- Evidence reference.
- Identification method.
- Processing timestamp.
- Confidence information where supported.

Distinguish:

- Explicitly stated relationships.
- Inferred relationships.
- Uncertain relationships.

Do not treat inferred relationships as verified facts.

Do not silently discard evidence when an entity is updated or associated with additional memories.

## 9. Persistence requirements

Use the approved Phase 5 data models and Phase 8.2 persistence implementation.

The implementation must reconcile its operations with the existing model inventory, including:

- Entity.
- Alias.
- Mention.
- Entity Relationship.
- Memory Relationship.
- Atomic Memory associations.
- Provenance records.

Requirements:

- Enforce ownership constraints.
- Maintain stable entity identifiers.
- Enforce valid references.
- Preserve source provenance.
- Support transactional persistence for related database operations.
- Prevent duplicate mention records during retries.
- Support optimistic concurrency where applicable.
- Preserve historical information when relationships change.

Do not introduce a separate graph database in this milestone.

Use PostgreSQL and the approved relational relationship models initially.

## 10. Failure handling

| Scenario | Expected behavior |
|---|---|
| Entity name unavailable | Skip entity identification for that fact |
| Entity type ambiguous | Preserve uncertainty |
| Multiple possible matches | Mark unresolved for later resolution |
| Duplicate entity creation attempt | Apply safe lookup and idempotency rules |
| Conflicting aliases | Preserve conflict for Phase 8.6 |
| Missing source provenance | Reject unsupported relationship persistence |
| Invalid relationship type | Reject with validation details |
| Missing referenced entity | Reject or defer relationship creation |
| Concurrent entity updates | Apply approved concurrency controls |
| NLP model unavailable | Use approved fallback or record processing failure |
| Database failure | Preserve failure state and support safe retry |

Do not automatically merge entities to recover from a failed lookup.

## 11. Testing requirements

### Unit tests

Test:

- Entity mention identification.
- Entity type classification.
- Canonical name normalization.
- Alias normalization.
- Entity lookup.
- Mention construction.
- Relationship construction.
- Provenance validation.
- Ownership validation.

### Component tests

Test:

- Entity registration.
- Alias persistence.
- Mention persistence.
- Entity-to-memory association.
- Entity-to-entity relationship persistence.
- Memory-to-memory relationship persistence.
- Idempotent processing.
- Concurrent entity updates.

### Edge-case tests

Include:

- Same name used by different people.
- Organization and product sharing a name.
- Multiple aliases.
- Misspelled entity names.
- Abbreviations.
- Entity name changes.
- Ambiguous references.
- Missing timestamps.
- Multiple entities in one fact.
- Multiple mentions of the same entity.
- Contradictory relationship observations.

### Security tests

Verify:

- Cross-user entity access is denied.
- Unauthorized relationship creation is rejected.
- Ownership is checked for referenced memories.
- Private metadata is not exposed through logs.

## 12. Observability

Record structured events for:

- Entity identification started.
- Entity mention identified.
- Entity classified.
- Entity registered.
- Alias registered.
- Ambiguous match detected.
- Relationship created.
- Relationship rejected.
- Entity processing failed.

Track:

- Entities identified.
- New entity records created.
- Alias registrations.
- Ambiguous match rate.
- Relationship creation rate.
- Invalid relationship rate.
- Processing latency.
- Duplicate processing rate.

Do not log unnecessary sensitive source content.

## 13. Acceptance criteria

Phase 8.5 is complete only when:

- [ ] Entities can be identified from memory candidates.
- [ ] Entity types follow the approved data model.
- [ ] Entity records can be created and retrieved.
- [ ] Aliases can be registered and looked up.
- [ ] Entity mentions preserve their source references.
- [ ] Entities can be associated with memories.
- [ ] Supported entity-to-entity relationships can be persisted.
- [ ] Supported memory-to-memory relationships can be persisted.
- [ ] Provenance is preserved.
- [ ] User ownership is enforced.
- [ ] Ambiguous identities are not silently merged.
- [ ] Duplicate processing is handled safely.
- [ ] Failure and recovery behavior is tested.
- [ ] Unit and component tests pass.
- [ ] Security and edge-case tests pass.
- [ ] No out-of-scope resolution or retrieval functionality has been introduced.

## 14. Implementation constraints

Claude Code must:

1. Inspect the existing repository before modifying files.
2. Reuse the Phase 8.1–8.4 implementation.
3. Follow approved Phase 5 models.
4. Follow the Phase 6 algorithms.
5. Reuse the approved persistence layer.
6. Keep entity identification separate from identity resolution.
7. Keep entity relationships separate from memory relationships.
8. Preserve evidence and provenance.
9. Avoid introducing a graph database without an approved architectural decision.
10. Avoid generative LLM functionality.
11. Avoid implementing document RAG in this milestone.
12. Place source code inside `memory-engine/`.
13. Place tests inside `tests/`.
14. Do not proceed to Phase 8.6 automatically.

If an existing model cannot represent a required relationship, report the exact gap and recommend a solution before changing the approved schema.

## 15. Completion report

Claude Code must provide:

1. Summary of entity management functionality.
2. Files created or modified.
3. Models and repositories reused.
4. Entity identification approach.
5. Alias management approach.
6. Relationship types implemented.
7. Provenance implementation.
8. Tests executed and exact results.
9. Known limitations.
10. Deviations from architecture.
11. Acceptance criteria status.

## 16. Definition of done

Phase 8.5 is complete when Raven can identify and register entities, manage aliases and mentions, and maintain evidence-backed relationships between entities and memories without silently resolving ambiguous identities.

**The output is a traceable entity and relationship layer that enables Phase 8.6 to perform reliable memory and identity resolution.**
