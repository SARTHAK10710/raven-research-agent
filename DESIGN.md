# Raven — Design

## 1. What is Raven?

Raven is an independent AI research agent built around three core capabilities: persistent memory, external research, and intelligent orchestration.

The goal is to build a system that doesn't simply retrieve information, but can preserve useful context, investigate external information, and coordinate multi-step tasks while maintaining evidence, provenance, and data integrity.

## 2. How It Works

Raven consists of three primary engines supported by shared infrastructure.

- **Memory Engine:** Ingests information, extracts atomic facts, manages entities and relationships, resolves duplicates and contradictions, and retrieves relevant historical context.
- **Research Engine:** Discovers external information, extracts claims and evidence, evaluates sources, verifies findings, and maintains persistent research sessions.
- **Agent Orchestrator:** Understands requests, plans tasks, routes work to the appropriate engines, coordinates execution, manages failures, and assembles evidence-aware responses.

Shared infrastructure provides persistence, messaging, authentication, storage, and observability.

A typical request flows through the Orchestrator, which determines whether it needs memory retrieval, external research, or both. The engines execute their respective responsibilities and return structured results for final response assembly.

## 3. Why I Built It This Way

The central design decision was to separate memory, research, and orchestration instead of building one large agent responsible for everything.

This provides:

- **Clear ownership:** Each engine has a defined responsibility and controls its own data.
- **Independent evolution:** Memory and Research can evolve without redesigning the entire system.
- **Evidence traceability:** Retrieved information retains its source, confidence, and temporal context.
- **Controlled execution:** The Orchestrator coordinates workflows rather than owning every processing capability.
- **Data integrity:** Similarity alone cannot authorize memory merges, updates, or deletion.
- **Recoverability:** Long-running tasks support checkpoints, retries, cancellation, and reconciliation.

The architecture prioritizes correctness, privacy, and reliability over premature optimization.

## 4. What I Considered and Rejected

| Alternative | Why I didn't choose it |
|---|---|
| One monolithic agent handling everything | Blurs ownership and makes memory, research, and execution harder to evolve independently. |
| Microservices from day one | Adds deployment, networking, and operational complexity before independent scaling is justified. |
| Vector search as the only retrieval mechanism | Semantic similarity cannot replace keyword, metadata, temporal, and relationship-based retrieval. |
| Similarity-based automatic memory merging | Similar statements are not necessarily identical facts. |
| Generative LLMs for all core processing | Makes deterministic validation, reproducibility, and controlled processing harder to guarantee. |
| Treating every source as equally reliable | Information requires source evaluation, evidence assessment, and contextual verification. |

The selected approach combines deterministic processing, conventional NLP, statistical methods, embeddings, and selective non-generative machine learning.

## 5. What I Would Do With Another Week

My next priorities would be:

1. Complete the Memory Engine's foundational ingestion and persistence pipeline.
2. Implement atomic fact extraction and candidate evaluation.
3. Build entity resolution and contradiction-handling workflows.
4. Implement hybrid retrieval using PostgreSQL and pgvector.
5. Establish automated tests for correctness, ownership isolation, and deletion propagation.
6. Benchmark retrieval quality using a small, carefully labelled evaluation dataset.

The priority would be to establish one reliable end-to-end memory workflow rather than implement every planned component superficially.

## 6. Current Status

Raven's architecture, data models, algorithm specifications, and technology decisions are documented.

Implementation, integration, benchmarking, and deployment are separate stages of the project. Features should only be described as implemented when supported by actual code and verification evidence.

**Design principle:** Build a system that can explain what it remembers, where information came from, why it trusts a result, and how it handles uncertainty.
