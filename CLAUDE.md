# CLAUDE.md — Raven Research Agent

Primary instruction and navigation file for Claude Code sessions in this repository. Keep it short: it points to sources, it does not replace them.

## Project

Raven is an independent AI research agent that builds persistent, evidence-grounded knowledge. It has **three primary engines** — Memory Engine, Research Engine, Agent Orchestrator — supported by Shared Infrastructure, deployed initially as a **modular monolith with independent background workers**. The Memory Engine holds two separate logical domains: **Personal Memory** and **Document Intelligence**.

This repository holds the architecture, data-model, algorithm and technology specifications (Phases 1–7), the Phase 8 Memory Engine implementation plans, and — from Phase 8 onward — the implementation itself. **No application code exists yet.**

## Current phase

See [`docs/project-context/PROJECT_STATUS.md`](docs/project-context/PROJECT_STATUS.md). At the time of writing: Phase 8 (Memory Engine implementation), subphase 8.1 (Foundation and Project Setup). The foundation is implemented and verified (Python 3.12, mypy strict, uv workspace, root `tests/`, Pydantic Settings; see [7.1 §22](docs/technical-decisions/01-baseline-technology-stack.md)). Phase 8.2 has not been approved to start.

Run checks from the repository root: `uv sync`, `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`. Never begin or advance a subphase without explicit user approval.

## Context loading (every session)

Read, in order, and stop there unless the task needs more:

1. This file (`.claude/rules/*.md` are loaded automatically with it).
2. [`docs/project-context/PROJECT_STATUS.md`](docs/project-context/PROJECT_STATUS.md)
3. [`docs/project-context/ARCHITECTURE_SUMMARY.md`](docs/project-context/ARCHITECTURE_SUMMARY.md)
4. [`docs/project-context/KNOWN_CONSTRAINTS.md`](docs/project-context/KNOWN_CONSTRAINTS.md)
5. [`docs/project-context/NEXT_STEPS.md`](docs/project-context/NEXT_STEPS.md) (includes the latest session handoff)
6. The implementation plan for the current subphase in [`docs/implementation-plans/Phase-08-memory-engine/`](docs/implementation-plans/Phase-08-memory-engine/Readme.md).

Then load only the source documents the task needs, using the map in [`docs/project-context/README.md`](docs/project-context/README.md#targeted-documentation-map). Do not read every Phase 1–7 document for every task, do not print whole files, and do not search the whole repository without a specific reason.

## Source-of-truth hierarchy

1. **Approved architecture:** [`PROJECT_ARCHITECTURE.md`](PROJECT_ARCHITECTURE.md), [`docs/architecture/`](docs/architecture/Readme.md).
2. **Approved specifications, each authoritative in its area:** data models [`docs/data-models/`](docs/data-models/Readme.md) (Phase 5), algorithms [`docs/algorithms/`](docs/algorithms/Readme.md) (Phase 6), technology [`docs/technical-decisions/`](docs/technical-decisions/Readme.md) (Phase 7). Where a file carries an appended amendment, the amendment extends the original; it does not replace it.
3. **Implementation plans:** [`docs/implementation-plans/`](docs/implementation-plans/Phase-08-memory-engine/Readme.md) — how to implement; they cannot change architecture.
4. **Project context:** [`docs/project-context/`](docs/project-context/README.md) — navigation summaries and verified state. If a summary disagrees with a source document, the source wins and the summary must be corrected.
5. **The repository itself** is the only evidence of what is implemented and tested.

Conflicts between documents are **reported to the user, never silently resolved**. Only the user approves architectural changes. Significant decisions are recorded in the relevant file under `docs/technical-decisions/` (there is no single `docs/technical-decisions.md`).

## Mandatory constraints

Full list: [`KNOWN_CONSTRAINTS.md`](docs/project-context/KNOWN_CONSTRAINTS.md). Never violate:

- No generative LLM APIs and no locally hosted generative LLMs in Raven's processing.
- Correctness, privacy, security and data integrity before performance.
- Personal Memory and Document Intelligence stay separate; document chunks are never personal memories.
- Similarity is a signal, not proof. Provenance and evidence are preserved.
- Deletion propagates to all derived data; forgotten data must not reappear.
- No cross-user access. No secrets in code, Git, images or logs.
- No new infrastructure or dependency without documented justification.

Rules files: [architecture](.claude/rules/architecture.md) · [coding standards](.claude/rules/coding-standards.md) · [security and privacy](.claude/rules/security-and-privacy.md) · [implementation workflow](.claude/rules/implementation-workflow.md).

**Raven engineering conventions.** The rules files contain five practices adopted for this project that are *not* requirements of the source documents. Each is labeled where it appears:

1. Map errors to API error categories at the interface layer, not in the domain (coding standards).
2. Exception class names end in `Error` (coding standards).
3. Log the error code and type by default, not raw exception messages (security and privacy).
4. Never enter real credentials on the user's behalf or echo secret values (security and privacy).
5. Do not tune models on user data automatically; the source requirement covers training only (security and privacy).

If a convention ever conflicts with a source document, the source document wins.

## Implementation workflow (summary)

One approved subphase at a time → inspect before modifying → read only relevant docs → implement incrementally → run the relevant tests and report actual output → update project context → write the session handoff → stop and wait for approval. Details: [implementation workflow](.claude/rules/implementation-workflow.md).

## Testing and verification

- Never claim tests passed without running them; report exact commands and results.
- A task is `VERIFIED` only when its acceptance criteria are met with executed test evidence. Generated code is not verified code.
- Tests validate behavior and correctness, not just imports or HTTP 200s.

## Checkpoint updates (mandatory)

After completing a subphase, or at the end of any session that changed the repository, update in `docs/project-context/`:

- Always: `PROJECT_STATUS.md`, `IMPLEMENTATION_STATE.md`, `NEXT_STEPS.md` (including its Session Handoff section).
- When applicable: `TECHNOLOGY_DECISIONS.md` (approved technology change), `KNOWN_CONSTRAINTS.md` (constraint, limitation or deferral change), `ARCHITECTURE_SUMMARY.md` (approved architecture change only), this file or `.claude/rules/` (persistent instructions change).

Record only verified repository state — never planned or discussed work as done.

## Git

Run `git status` before changing files; never overwrite unrelated changes. Do not commit or push without explicit user approval.
