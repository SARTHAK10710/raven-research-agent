# Phase 4 — Agent Orchestrator

**Status: architecture complete.**  
**Optimization : Performance = 45 : 55.**  
**Scope: architecture policy only; no code, schema, database, detailed algorithm, threshold, or test is implemented.**

## Purpose and Boundary

The Orchestrator determines what should happen, in what order, and how outputs should be combined. It does not independently extract memory, discover sources, or verify facts. It mediates cross-engine work by default and preserves engine ownership.

## Eight Logical Responsibilities

1. **Intent Understanding** — lightweight objective/constraint/output interpretation.
2. **Task Planning** — rule-based predictable plans, dynamic complex plans, controlled replanning.
3. **Engine Routing** — hybrid adaptive routing.
4. **Execution Coordination** — dependency sequencing, controlled parallel work, reuse.
5. **Context Management** — selective provenance-preserving context and controlled additional retrieval.
6. **State & Progress Management** — execution IDs, task state/dependencies/checkpoints/results/errors/cancellation.
7. **Failure & Recovery Management** — bounded retry, partial recovery, fallback, degradation, escalation, cancellation.
8. **Response Assembly** — evidence-aware composition without invention or silent conclusion changes.

## Routing

- Historical information → Memory Engine.
- Current external information → Research Engine.
- Historical plus current information → Memory first, then targeted Research.
- Material ambiguity → inspect context or ask for clarification.
- Neither engine needed → answer directly where permitted.

Do not call both engines by default or lose the difference between historical and newly researched information.

## Execution, Recovery, and Cancellation

Use sequential work for dependencies and controlled parallelism for independent tasks. Priority considers dependencies, importance, urgency, resource cost, and expected value; correctness and critical paths outweigh small performance gains.

Task state is centralized and architecture-level states include pending, running, completed, failed, retrying, skipped, cancellation_requested, and cancelled. Tasks and parent executions have separate outcomes. Context isolation and future optimistic conflict detection are required for shared updates.

Use bounded retry, preservation of completed work, selective retry, permitted fallback, honest partial results, and escalation when safe continuation needs user input. Cancellation is cooperative and idempotent: stop pending work, signal running work, prevent downstream dispatch, reconcile non-interruptible work, preserve committed data per future policy, clean temporary resources, and report cancellation distinctly.

## Response Assembly

Combine Memory and Research outputs; remove duplicates without removing history; preserve timestamps, source, confidence, and conflicts; distinguish verified facts, assumptions, and incomplete evidence; adapt to the user request; and never fabricate findings.

## Deferred

State schemas/storage, scheduler and planning algorithms, priority scoring, checkpoint implementation, protocols, transactions, cancellation guarantees, retry/queue/backpressure/resource thresholds, metrics, security, benchmarks, deployment, and tests are deferred, unimplemented, and unvalidated.
