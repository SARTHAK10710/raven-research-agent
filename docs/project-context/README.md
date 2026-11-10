# Raven Project Context

## Purpose

This directory gives every Claude Code session a compact, verified picture of Raven: what it is, what has been decided, what is actually implemented, and what to do next. Sessions use it instead of re-reading the whole repository. Persistent project knowledge lives here and in the repository, not in any single conversation.

These files are **navigation summaries and state records**. They do not replace the source specifications. If a summary disagrees with a source document, the source document is authoritative and the summary must be corrected.

## Files

| File | Contains | Changes when |
|---|---|---|
| [`PROJECT_STATUS.md`](PROJECT_STATUS.md) | Current phase and subphase; documentation vs implementation completion; active task; last verified update | Every completed subphase or repository-changing session |
| [`ARCHITECTURE_SUMMARY.md`](ARCHITECTURE_SUMMARY.md) | Orientation to engines, domains, communication and ownership, with links | Only after an approved architectural change |
| [`TECHNOLOGY_DECISIONS.md`](TECHNOLOGY_DECISIONS.md) | Approved, proposed, pending, deferred and prohibited technologies; what is actually installed | An approved technology decision changes, or a dependency is installed |
| [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md) | Per-subphase status, files, dependencies, tests, issues and commits | Every completed subphase or repository-changing session |
| [`KNOWN_CONSTRAINTS.md`](KNOWN_CONSTRAINTS.md) | Permanent constraints, deferred decisions, known limitations, open documentation issues | A constraint, limitation or deferral changes |
| [`NEXT_STEPS.md`](NEXT_STEPS.md) | Immediate priorities, prerequisites, open decisions, next approved action, and the latest **Session Handoff** | Every session that changes the repository |

Permanent rules live in [`.claude/rules/`](../../.claude/rules/) (architecture, coding standards, security and privacy, implementation workflow). Claude Code loads them automatically with [`CLAUDE.md`](../../CLAUDE.md).

## How to load context

At the start of every session:

1. [`CLAUDE.md`](../../CLAUDE.md) (with `.claude/rules/`)
2. [`PROJECT_STATUS.md`](PROJECT_STATUS.md)
3. [`ARCHITECTURE_SUMMARY.md`](ARCHITECTURE_SUMMARY.md)
4. [`KNOWN_CONSTRAINTS.md`](KNOWN_CONSTRAINTS.md)
5. [`NEXT_STEPS.md`](NEXT_STEPS.md)
6. The implementation plan for the current subphase

Read `TECHNOLOGY_DECISIONS.md` and `IMPLEMENTATION_STATE.md` when the task involves dependencies or prior implementation detail. Then load only the source documents listed for the task below. Use section-level reads of long files (many are 400–2,400 lines) rather than reading them whole.

## Targeted documentation map

Paths are relative to the repository root. "Plan" means `docs/implementation-plans/Phase-08-memory-engine/`. Phase 5 and 7 files marked "+amendment" contain the original specification followed by a Document Intelligence amendment at the end; read the part you need.

| Task | Read |
|---|---|
| 8.1 Foundation and setup | Plan `01-…`; [7.1 baseline](../technical-decisions/01-baseline-technology-stack.md); [7.7](../technical-decisions/07-observability-and-testing-infrastructure.md) §3, §6, §10–12, §17; [7.8](../technical-decisions/08-deployment-and-environment-architecture.md) §4, §6–7 |
| 8.2 Database and persistence | Plan `02-…`; [5 overview](../data-models/phase-05-data-models-overview.md); [5.4 memory models +amendment](../data-models/phase-05-memory-engine-models.md); [5.8–5.10 +amendment](../data-models/phase-05-relationships-and-lifecycle.md); [7.2 +amendment](../technical-decisions/02-database-and-storage-architecture.md); [7.3](../technical-decisions/03-vector-search-and-embedding-infrastructure.md) §9 |
| 8.3 Ingestion | Plan `03-…`; [memory/01 algorithm](../algorithms/memory/01-memory-ingestion-extraction.md); 5.4 memory sources; [7.4 messaging](../technical-decisions/04-background-processing-and-messaging.md); [7.6](../technical-decisions/06-api-security-and-internal-communication.md) §12 |
| 8.4 Extraction and evaluation | Plan `04-…`; memory/01 algorithm; [shared/01 framework](../algorithms/shared/01-shared-algorithm-framework.md); [7.5 NLP](../technical-decisions/05-NLP-and-machine-learning-stack.md) (original part) |
| 8.5 Entities and relationships | Plan `05-…`; [memory/02 algorithm](../algorithms/memory/02-memory-resolution.md); 5.4 §6 (entities) |
| 8.6 Memory resolution | Plan `06-…`; memory/02 algorithm; 5.4; 7.3 (original part) |
| 8.7 Storage and indexing | Plan `07-…`; 5.4 §10; 5.8–5.10; 7.2; 7.3 |
| 8.8 Memory retrieval | Plan `08-…`; [memory/03 algorithm](../algorithms/memory/03-memory-retrieval.md); 5.4 memory models; 7.3 §11 |
| 8.9 Consolidation and maintenance | Plan `09-…`; [memory/04 algorithm](../algorithms/memory/04-memory-consolidation-maintenance.md); 7.4 |
| 8.10 Forgetting and deletion | Plan `10-…`; memory/04 algorithm; 5.8–5.10 (Decisions 5.10.5–5.10.7); 7.2 §12–13 |
| 8.11 Integration and testing | Plan `11-…`; 7.7 |
| 8.12 Document RAG | Plan `12-…`; [memory/05 algorithm](../algorithms/memory/05-document-processing-and-rag.md); amendments in 5.4, 5.8–5.10, 7.2, 7.3 and 7.5; 7.6 §12 |
| Any API or contract work | 7.6; [PROJECT_ARCHITECTURE.md](../../PROJECT_ARCHITECTURE.md) |
| Any deployment or configuration work | 7.8 |

If a mapped section is not where the map says, find it by heading search, then fix this table.

## Maintenance

- Follow the checkpoint protocol in [implementation-workflow](../../.claude/rules/implementation-workflow.md).
- Record only verified repository state: what exists in the repository and what tests actually showed. Planned or discussed work is not progress.
- Keep files short. Link to sources instead of copying them. Replace stale entries rather than appending history; Git keeps the history.
- Record significant decisions in the relevant `docs/technical-decisions/` file first, then reflect them here.
