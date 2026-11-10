# Raven — Design

## What is Raven?

Raven is an independent AI research agent designed to build persistent, structured and evidence-grounded intelligence from two sources:

1. **Personal Memory:** Information, preferences, decisions, relationships and knowledge accumulated about a user over time.
2. **Document Intelligence:** Information extracted from uploaded documents, organized into searchable knowledge and made accessible through retrieval and evidence-based processing.

Raven brings these capabilities together through an intelligent orchestration layer that understands requests, coordinates processing and delivers relevant results.

The central idea is simple: an intelligent system should not repeatedly start from zero. It should be able to retrieve what it already knows, discover what it does not know and preserve the evidence behind its conclusions.

## How it works

Raven is built around three primary engines supported by shared infrastructure.

### 1. Memory Engine

The Memory Engine manages persistent knowledge through two distinct but integrated capabilities.

**Personal Memory**
- Ingests information from user interactions and other authorized sources.
- Extracts and evaluates atomic facts.
- Identifies entities, relationships, duplicates and contradictions.
- Maintains memory revisions, confidence and provenance.
- Retrieves relevant information using hybrid search.
- Consolidates, updates and deletes memories when required.

**Document Intelligence**
- Processes uploaded PDF, DOCX and TXT documents.
- Extracts text and document structure.
- Organizes content into meaningful chunks.
- Generates embeddings for semantic retrieval.
- Combines vector search with keyword search.
- Retrieves relevant evidence and preserves document citations.
- Supports document comparison and structured, evidence-based answers.
- Maintains document versions, provenance and deletion dependencies.

These are separate logical knowledge domains with independent ownership and lifecycle rules. They can share infrastructure without treating document chunks as personal memories.

### 2. Research Engine

The Research Engine handles information that must be discovered externally.

It decomposes research queries, discovers sources, extracts information, evaluates source reliability, verifies facts and maintains research sessions.

It distinguishes new discoveries from previously collected information and preserves source references for future retrieval.

### 3. Agent Orchestrator

The Orchestrator coordinates Raven's capabilities.

It understands user intent, determines which engine is required, creates execution plans, manages dependencies, coordinates parallel and sequential tasks, handles failures and assembles final responses.

It can retrieve personal memories, search uploaded documents, conduct external research or combine these capabilities when a request requires them.

### 4. Shared Infrastructure

The engines use shared infrastructure for persistence, storage, vector search, messaging, identity, monitoring and deployment.

The initial technology direction uses Python, FastAPI, PostgreSQL, pgvector, RabbitMQ, Celery and S3-compatible object storage.

## Why this architecture?

The architecture follows a few important principles:

**Clear ownership:** Each engine owns its business responsibilities and authoritative data. The Orchestrator coordinates rather than duplicating engine logic.

**Persistent knowledge:** Personal memories and document knowledge should remain available beyond individual requests.

**Evidence over assumptions:** Similarity scores and statistical predictions are signals, not proof. Information should retain provenance, confidence and verification status.

**Separation without unnecessary infrastructure:** Personal memory and document intelligence have separate logical workflows but can reuse the same underlying database and vector infrastructure.

**Correctness before speed:** Retrieval, resolution, verification and deletion must preserve data integrity, even when this requires additional processing.

**No generative LLM dependency:** Raven's core processing does not depend on generative LLM APIs or locally hosted generative LLMs. It relies on deterministic algorithms, conventional NLP, statistical methods, embeddings, structured extraction and evidence-based answer assembly.

## Alternatives considered and rejected

| Alternative | Reason for rejection |
|---|---|
| One large monolithic engine | Blurs responsibilities and makes individual capabilities harder to maintain and evaluate |
| Separate microservices for every component | Adds operational and communication complexity before workload justifies it |
| One unified memory store for everything | Risks mixing personal facts, document content and research findings |
| Dedicated vector database from day one | Adds infrastructure before measured scale requires it |
| Generative LLM-dependent processing | Conflicts with Raven's non-generative processing constraint |
| Similarity-only retrieval | Similarity does not establish factual correctness or evidence sufficiency |

The selected architecture uses modular ownership, shared infrastructure and independent logical processing workflows.

## What would another week improve?

With another week, the highest-value improvements would be:

1. **Retrieval evaluation:** Build representative datasets to measure personal memory and document retrieval quality independently.
2. **Document processing evaluation:** Test PDF and DOCX parsers against complex layouts, tables and different document structures.
3. **Evidence validation:** Strengthen citation correctness, conflicting evidence handling and unsupported-answer detection.
4. **Memory quality:** Evaluate duplicate detection, contradiction resolution and temporal correctness.
5. **Integration testing:** Validate complete workflows across Memory, Research and Orchestrator.
6. **Performance profiling:** Measure embedding generation, retrieval latency, database queries and background processing costs.

The priority would be to validate the quality and reliability of the architecture rather than prematurely introducing more infrastructure.

---

**Raven's design philosophy:**

Build an agent that does not merely retrieve information, but understands where that information came from, how reliable it is, how it relates to existing knowledge and when it should no longer be trusted.
