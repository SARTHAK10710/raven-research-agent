# Phase 2 — Memory Engine

**Status: architecture complete.**  
**Optimization : Performance = 70 : 30.**  
**Scope: architecture policy only; no code, schema, database, detailed algorithm, threshold, or test is implemented.**

## Purpose

The Memory Engine manages persistent user and contextual memory. The 70:30 preference favors memory quality, provenance, deduplication, historical continuity, and deletion correctness over raw throughput.

## Nine Logical Components

1. **Memory Ingestion** — preserves sources, identity, timestamps, and routes remember/forget requests.
2. **Extraction & Evaluation** — relevance gate, atomic facts/entities/relationships, independent importance/confidence, explicit versus inferred candidates.
3. **Entity & Relationship Management** — canonical identities, aliases, typed relationships, derived profiles.
4. **Matching & Resolution** — duplicate, related, progression, and contradiction classification.
5. **Storage & Indexing** — conceptual raw-source, candidate/observation, and validated-memory layers; vector, keyword, metadata, and relationship indexes.
6. **Retrieval** — hybrid search, filtering, ranking, bounded expansion, progressive retrieval, early stopping.
7. **Consolidation & Maintenance** — event/schedule/query-triggered consolidation, freshness, lifecycle, historical/current views.
8. **Forgetting & Deletion Management** — target/dependency analysis, removal/redaction, derived-store/index/cache updates, propagation tracking.
9. **Reliability & Observability** — consistency, recovery, duplicate protection, update-conflict protection, future resource enforcement.

They are logical responsibilities, not a mandatory pipeline or separate services.

## Core Rules

- One message is one source record even if it creates several candidates.
- Extraction does not itself approve validated storage.
- Atomic memories are authoritative; profiles are derived views.
- Similarity is a candidate signal, never sufficient proof to merge.
- Preserve meaningful progression and historical context.
- Do not answer from an unreliable similarity match.
- Consolidation must be idempotent.
- Explicit forgetting overrides archival and expiry; affected information cannot be returned while propagation recovery is pending.
- Performance cannot weaken accuracy, provenance, isolation, or deletion correctness.

## Architecture Coverage

The policy covers creation/retrieval, duplicate/related information, progression, contradictions/corrections, forgetting, preferences, tentative plans, third-party isolation, processing failures, concurrent updates, and stale/incomplete retrieval. This is architecture-level coverage, not executed testing.

## Deferred

Schemas, database/storage choice, embeddings and ranking/matching/consolidation/deletion algorithms, scoring, retention and resource thresholds, transactions/concurrency, retry limits, observability metrics, security controls, and tests are deferred, unimplemented, and unvalidated.
