# Raven — Technology & Infrastructure

## Purpose

This directory contains the technology and infrastructure specifications for Raven.

It translates the architectural principles and algorithm specifications into concrete technology choices.

Technology decisions must preserve Raven's core requirements:

- Quality-first processing.
- Data integrity.
- Privacy and security.
- Modular architecture.
- Independent engine ownership.
- Evidence traceability.
- Maintainability.
- Controlled scalability.
- Cost awareness.

## Phase 7 — Document Index

| Phase | Document | Scope |
|---|---|---|
| 7.1 | 01-baseline-technology-stack.md | Programming language, frameworks and baseline stack |
| 7.2 | 02-database-and-storage-architecture.md | PostgreSQL, relational storage and object storage |
| 7.3 | 03-vector-search-and-embedding-infrastructure.md | Embeddings, pgvector and semantic search |
| 7.4 | 04-background-processing-and-messaging.md | RabbitMQ, Celery and asynchronous execution |
| 7.5 | 05-nlp-and-machine-learning-stack.md | NLP, statistical processing and non-generative ML |
| 7.6 | 06-api-security-and-internal-communication.md | API contracts, authentication and authorization |
| 7.7 | 07-observability-and-testing-infrastructure.md | Logging, tracing, monitoring and testing |
| 7.8 | 08-deployment-and-environment-architecture.md | Docker, environments, deployment and recovery |

## Technology Decision Register

The central technology decision register is maintained at:

`docs/technical-decisions.md`

Detailed technology specifications belong in this directory.

Avoid duplicating complete technical specifications in the decision register. The register should contain decisions, rationale, status and references to detailed documents.

## Technology Selection Principles

1. Prefer mature and maintainable technologies.
2. Prioritize correctness and reliability.
3. Preserve engine ownership boundaries.
4. Avoid unnecessary infrastructure complexity.
5. Use interfaces to reduce vendor lock-in.
6. Introduce distributed infrastructure only when justified.
7. Keep core processing independent of generative LLMs.
8. Evaluate technologies using Raven-specific requirements.
9. Document deferred decisions explicitly.
10. Never claim implementation or deployment before verification.

## Important Architectural Constraint

Raven's core processing will not use generative LLM APIs or locally hosted generative LLMs.

Conventional NLP, statistical methods, embeddings and non-generative machine learning are permitted.

## Phase Status

Phase 7 documents technology selections and infrastructure specifications.

Implementation, integration, benchmarking and deployment belong to subsequent phases.
