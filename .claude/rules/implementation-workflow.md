# Rule: Implementation Workflow

How every Raven implementation session runs. Source: [Phase 8 Readme §6–10](../../docs/implementation-plans/Phase-08-memory-engine/Readme.md).

## Rules

1. **One approved subphase at a time.** Work only on the subphase named as current in [`PROJECT_STATUS.md`](../../docs/project-context/PROJECT_STATUS.md), and only after the user approves it.
2. **Inspect before modifying.** Run `git status`, identify uncommitted user changes and never overwrite them. Read the files you will change and verify paths exist; never assume a file exists because a document mentions it.
3. **Read only relevant documentation.** Load context in the order given in [`CLAUDE.md`](../../CLAUDE.md), then use the [targeted documentation map](../../docs/project-context/README.md#targeted-documentation-map). Do not reread all Phase 1–7 documents.
4. **Reuse existing infrastructure and code** where it is compatible with the architecture.
5. **Avoid unnecessary abstractions and dependencies.** Each new dependency or structural element needs a stated reason.
6. **Never silently change architecture.** Report conflicts, gaps and ambiguities, and propose the smallest safe resolution. Do not invent missing designs.
7. **Implement incrementally** in small, reviewable steps that match the subphase plan's order.
8. **Run the relevant tests,** plus linting and type checking where configured.
9. **Report actual results:** exact commands, pass/fail counts and failures. Never claim an unexecuted check passed.
10. **Update project context** after completed work (see Checkpoint protocol).
11. **Maintain the handoff checkpoint** in `NEXT_STEPS.md`.
12. **Never proceed to the next subphase automatically.** Stop and wait for approval.

Do not commit or push without explicit user approval.

## Subphase report

At the end of each subphase, report: files created and modified; dependencies added or changed; migrations created; tests executed with exact commands and results; acceptance criteria met and unmet; known limitations; architectural deviations and unresolved decisions; security, privacy or data-integrity concerns.

## Status values

Use these in [`IMPLEMENTATION_STATE.md`](../../docs/project-context/IMPLEMENTATION_STATE.md): `NOT_STARTED`, `INSPECTION`, `IN_PROGRESS`, `IMPLEMENTED`, `TESTING`, `VERIFIED`, `BLOCKED`.

- `IMPLEMENTED` means code exists but is not yet fully tested.
- `VERIFIED` requires every acceptance criterion to be met, with executed test evidence recorded. Generated code is never `VERIFIED` by itself.
- `BLOCKED` names the blocker and what would unblock it.

## Checkpoint protocol

After completing a subphase, or at the end of a session that changed the repository:

| File | Update when |
|---|---|
| `PROJECT_STATUS.md` | Always |
| `IMPLEMENTATION_STATE.md` | Always |
| `NEXT_STEPS.md` (with Session Handoff) | Always |
| `TECHNOLOGY_DECISIONS.md` | An approved technology decision changes |
| `KNOWN_CONSTRAINTS.md` | A constraint, limitation or deferred decision changes |
| `ARCHITECTURE_SUMMARY.md` | Only after an approved architectural change |
| `CLAUDE.md`, `.claude/rules/` | Persistent project instructions change |

- Record only verified repository state, with commit references where available. Do not record planned or discussed work as done.
- Keep entries concise: decisions, changes and verified outcomes. Do not paste long documentation into checkpoint files.
- Do not create a new checkpoint file per task. Use the project-level state files unless a separate detailed record is genuinely needed.

## Session handoff contents

Overwrite the Session Handoff section of `NEXT_STEPS.md` with: current objective; work completed; files changed; implementation status; tests and actual results; decisions made; unresolved issues; next action; the exact documents the next session must read. The next session must be able to resume from it without the conversation history.

## Context economy

Do not print entire files, repeat established architecture explanations, load unrelated implementation plans, or duplicate long documentation into reports or checkpoints. Keep reports focused on decisions, changes and verified results.
