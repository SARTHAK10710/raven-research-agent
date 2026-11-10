# Phase 3 — Research Engine

**Status: architecture complete.**  
**Optimization : Performance = 55 : 45.**  
**Scope: architecture policy only; no code, schema, database, detailed algorithm, threshold, or test is implemented.**

## Purpose

The Research Engine discovers, extracts, normalizes, verifies, preserves, retrieves, and compares external information. It balances evidence quality, freshness, context, and provenance with efficient acquisition and reuse. The Orchestrator decides whether research is needed; Research decides how to execute its assigned task.

## Seven Logical Components

1. **Query Understanding** — objectives, entities, attributes, constraints, intent, outputs, material ambiguity, adaptive decomposition.
2. **Information Discovery** — queries, source ranking, primary/alternative sources, deduplication, reuse.
3. **Content Extraction** — content/tables/context, source URL/timestamps, dynamic/restricted/incomplete content detection.
4. **Fact Extraction & Normalisation** — comparable entities, attributes, values, units/currencies, time, conditions, original wording, provenance.
5. **Source Evaluation & Verification** — authority, evidence, freshness, corroboration, context; source reliability remains distinct from fact confidence.
6. **Research Memory Management** — sessions, findings, relationships, snapshots, provenance, retention.
7. **Research Retrieval & Comparison** — historical retrieval, context-compatible comparison, conflict and temporal distinction.

## Agreed Policies

**Adaptive decomposition:** simple requests remain single tasks; complex work is decomposed only when worthwhile.  
**Hybrid retention:** structured findings, source metadata, relevant excerpts, sessions, and relationships persist subject to future policy; full webpage content is temporary by default; fuller snapshots are selective.  
**Session lifecycle:** complete, partially complete, failed, or cancelled. Preserve successful work, identify missing information, avoid endless retries, and never fabricate unavailable evidence.  
**Adaptive verification:** use basic, standard, or deep verification based on impact, uncertainty, freshness, conflict, reliability, and requested confidence; repeated copies are not independent corroboration.  
**Persistent sessions with incremental snapshots:** append changes/new verification to the same objective; create a linked session when the objective materially changes; preserve historical values and provenance.

## Evidence Rules

Preserve original values and context. Do not compare incompatible plans, regions, dates, billing cycles, units, currencies, or conditions. Missing remains missing. Material unresolved conflict is presented with source/date/context; a user choice is recorded as user-selected rather than verified.

## Architecture Coverage

The policy covers simple/complex research, history/targeted update, missing sessions, duplicate/inaccessible/incomplete sources, normalization, conflict/staleness, session linkage, retention, verification failures, and concurrent updates. This is not operational testing.

## Deferred

Schemas/database choice; query/ranking/extraction/normalization/verification algorithms and scoring; cache/retention terms; transactions; retry/resource thresholds; source adapters; benchmarks; security controls; and tests are deferred, unimplemented, and unvalidated.
