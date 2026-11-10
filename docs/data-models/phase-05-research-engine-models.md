# Phase 5.5 — Research Engine Data Models

**Project:** Raven — AI Research Agent  
**Phase:** 5 — Data Models & Database Design  
**Component:** Research Engine  
**Status:** Architecture Complete  
**Optimization Priority:** Research Engine — 55:45 (as established in Phase 3)

---

# 1. Objective

This document defines the logical data models, relationships, ownership boundaries and lifecycle principles of the Raven Research Engine.

The Research Engine is responsible for discovering, extracting, evaluating, verifying, organizing and retrieving external information.

Its data architecture must support:

- Research session management.
- Research query tracking.
- External source discovery.
- Content extraction and normalization.
- Fact and evidence management.
- Source reliability and verification.
- Historical research preservation.
- Incremental research updates.
- Comparison and conclusion generation.
- Research provenance and traceability.
- Research result retrieval.
- Partial completion and failure recovery.

The Research Engine must preserve the distinction between external information, extracted facts, supporting evidence and conclusions.

This document defines logical data architecture, not production database schemas or technology choices.

---

# 2. Research Engine Data Architecture

The Research Engine owns all business records associated with external research.

The initial logical entity inventory includes:

1. Research Session
2. Research Snapshot
3. Research Source
4. Extracted Content
5. Research Finding
6. Evidence Record
7. Comparison
8. Research Conclusion
9. Research Processing Event
10. Research Source Evaluation Record
11. Research Attribute Record
12. Research Session Relationship

These are conceptual entities. Not every entity necessarily requires an independent database table or collection.

The Research Engine remains the authoritative owner of these records.

---

# 3. Research Session

A Research Session represents a logically identifiable research objective and its associated work.

A session may contain multiple research activities, sources, findings and snapshots.

### 3.1 Session Identity

Every Research Session has a globally unique opaque identifier.

Session identity remains stable across incremental research updates.

### 3.2 Session Responsibilities

A Research Session logically groups:

- Research objective.
- Research queries.
- Discovered sources.
- Extracted content.
- Findings.
- Evidence.
- Comparisons.
- Conclusions.
- Research snapshots.
- Relevant processing history.

### 3.3 Session Lifecycle

Research Sessions support the following lifecycle states:

- `complete`
- `partially_complete`
- `failed`
- `cancelled`

A session may be partially complete when some sources are unavailable or some research tasks fail.

Partial results must remain distinguishable from complete results.

### 3.4 Research Session Ownership

The Research Engine owns Research Sessions.

The Orchestrator may reference sessions and coordinate their execution but does not own their research data.

---

# 4. Research Snapshot

A Research Snapshot represents a preserved state of research knowledge at a particular point in time.

Snapshots support historical comparison and incremental research updates.

### 4.1 Snapshot Responsibilities

A snapshot may preserve:

- Research findings at a particular point.
- Supporting evidence references.
- Source references.
- Relevant source metadata.
- Comparison results.
- Research conclusions.
- Verification status.
- Snapshot timestamp.

### 4.2 Snapshot Principles

1. Snapshots belong to their originating Research Session.
2. Snapshots preserve the state of research at the time they were created.
3. Historical snapshots must not be silently overwritten.
4. New research updates may create additional snapshots.
5. Snapshots preserve source and evidence traceability.
6. Historical research must remain distinguishable from current information.
7. Snapshot retention follows the Research Engine's lifecycle policies.

### 4.3 Incremental Research

When a user asks for an update to existing research:

- Raven retrieves the relevant previous Research Session.
- It identifies findings requiring verification or refresh.
- It discovers additional information where necessary.
- It updates relevant findings and evidence.
- It creates a new snapshot when a meaningful updated research state is established.

Unchanged findings need not be unnecessarily recreated.

---

# 5. Research Source

A Research Source represents an external information source used during research.

Examples include:

- Official websites.
- Government publications.
- Research papers.
- News articles.
- Technical documentation.
- Public datasets.
- Reports and industry publications.

### 5.1 Source Identity

Each Research Source receives a globally unique opaque identifier.

Source identity must remain distinguishable from a particular research session or finding.

### 5.2 Source Metadata

A Research Source may contain:

- Source identity.
- Original URL or source locator.
- Source title.
- Publisher or organization.
- Publication date where available.
- Retrieval timestamp.
- Source type.
- Source metadata.
- Access status.
- Relevant version or revision information.

Exact fields and types will be finalized during detailed schema design.

### 5.3 Source Ownership

The Research Engine owns Research Source records.

Public source information may be classified for shared reuse where permitted, but shared classification does not transfer ownership.

### 5.4 Source Retention

Source metadata and URLs are retained according to research retention requirements.

Full webpage content is temporary by default.

Complete source snapshots may be retained selectively when justified by
