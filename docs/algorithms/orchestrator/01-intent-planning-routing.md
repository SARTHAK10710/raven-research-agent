# Phase 6.11 — Agent Orchestrator: Intent, Planning & Routing Algorithms

**Project:** Raven Research Agent  
**Phase:** 6 — Algorithms & Processing Design  
**Subphase:** 6.11 — Intent, Planning & Routing  
**Status:** Architecture and algorithm specification  
**Optimization Priority:** Quality first  
**Processing Approach:** Hybrid — deterministic rules, conventional NLP/statistical methods, and selective non-generative ML

---

## 1. Purpose

The Agent Orchestrator is the coordination layer responsible for managing user requests across Raven.

It determines:

- What the user wants.
- Which engines are required.
- What tasks need to be performed.
- Which tasks depend on other tasks.
- Which tasks can execute in parallel.
- What context should be provided to each engine.
- How execution should be monitored.
- How results should be validated and assembled.

The Orchestrator does not perform the Memory Engine's memory extraction or the Research Engine's source discovery and verification.

It coordinates these capabilities through defined interfaces.

### Core principles

1. The Orchestrator owns execution coordination, not engine business logic.
2. Every request must have a traceable execution identity.
3. Routing decisions must be explainable.
4. Memory and Research Engine ownership boundaries must remain intact.
5. Dependencies must be resolved before execution.
6. Independent tasks should be parallelized where safe.
7. Quality and correctness take priority over unnecessary concurrency.
8. Completed work should be preserved when another task fails.
9. Context passed to engines must be relevant and authorized.
10. Final responses must preserve evidence, uncertainty, and completeness status.

---

# 2. Algorithm Inventory

This document defines ten algorithms.

| ID | Algorithm | Primary responsibility |
|---|---|---|
| 6.11.1 | Request Validation & Intent Understanding | Understand and validate user requests |
| 6.11.2 | Contextual Intent Resolution | Resolve references using authorized context |
| 6.11.3 | Task Decomposition | Break requests into manageable tasks |
| 6.11.4 | Execution Plan Generation | Define task order and dependencies |
| 6.11.5 | Engine Routing & Capability Selection | Route tasks to the correct engine |
| 6.11.6 | Dependency Resolution & Scheduling | Determine task readiness and execution order |
| 6.11.7 | Adaptive Parallelism & Resource Allocation | Allocate execution capacity |
| 6.11.8 | Execution Context Assembly | Prepare context for engine operations |
| 6.11.9 | Execution State & Progress Management | Track execution lifecycle |
| 6.11.10 | Failure Recovery & Cancellation Coordination | Recover or cancel execution safely |

---

# 3. 6.11.1 — Request Validation & Intent Understanding

## Purpose

Understand the user's request and convert it into a structured representation for orchestration.

A request may require:

- Memory retrieval.
- Memory updates.
- External research.
- Historical research retrieval.
- Comparisons.
- Multiple engine operations.
- Direct response without either engine.

The Orchestrator must identify the intended outcome before planning execution.

## Intent categories

| Intent | Description |
|---|---|
| `MEMORY_RETRIEVAL` | Retrieve stored user or project context |
| `MEMORY_UPDATE` | Store or update information in Memory Engine |
| `MEMORY_DELETION` | Request forgetting or deletion |
| `EXTERNAL_RESEARCH` | Discover and verify external information |
| `HISTORICAL_RESEARCH` | Retrieve previous research |
| `RESEARCH_UPDATE` | Refresh previous research |
| `COMPARISON` | Compare entities or information |
| `MULTI_ENGINE_REQUEST` | Requires Memory and Research |
| `DIRECT_RESPONSE` | Can be handled without engine execution |
| `CLARIFICATION_REQUIRED` | Essential ambiguity prevents safe execution |

Multiple intents may exist within one request.

## Validation dimensions

- Input presence.
- Supported request structure.
- User identity.
- Execution context.
- Request scope.
- Explicit instructions.
- Relevant constraints.
- Temporal requirements.

## Algorithm

**Input:**

- User request.
- User identity.
- Request metadata.
- Conversation context reference.

**Output:**

- Validated request.
- Primary intent.
- Secondary intents.
- Intent confidence.
- Ambiguity indicators.

### Processing steps

1. Receive the request.
2. Validate input structure.
3. Preserve the original request.
4. Normalize the text without changing meaning.
5. Extract entities and requested actions.
6. Identify explicit constraints.
7. Classify primary and secondary intents.
8. Evaluate ambiguity.
9. Produce a structured request representation.
10. Return validation results.

### Pseudocode

```text
FUNCTION understand_request(request):

    validate_request_structure(request)

    preserve_original_request(request)

    normalized = normalize_request(request)

    features = extract_request_features(normalized)

    intents = classify_intents(features)

    ambiguity = evaluate_intent_ambiguity(intents)

    RETURN {
        original_request,
        normalized_request,
        primary_intent,
        secondary_intents,
        ambiguity,
        validation_status
    }
```

## Safeguards

- Do not discard explicit user instructions during normalization.
- Do not force multiple intents into one category.
- Do not infer authorization from request wording.
- Do not execute ambiguous destructive operations.
- Preserve the original request for traceability.

---

# 4. 6.11.2 — Contextual Intent Resolution

## Purpose

Resolve ambiguous references using authorized context.

Examples:

- "Find its latest pricing."
- "Compare it with the previous company."
- "Update the research we did earlier."
- "Remember this for my project."

The Orchestrator should use relevant context rather than unnecessarily asking the user to repeat information.

## Context sources

- Current conversation context.
- User identity and authorization metadata.
- Memory Engine retrieval results.
- Research Engine session references.
- Previous execution results.
- Explicitly supplied project context.

The Orchestrator must access private memory and research information only through authorized interfaces.

## Algorithm

**Input:**

- Structured request.
- Authorized context references.
- Previous execution references.
- Entity mentions.

**Output:**

- Resolved references.
- Contextual constraints.
- Remaining ambiguity.
- Context provenance.

### Processing steps

1. Identify unresolved references.
2. Retrieve only context relevant to those references.
3. Resolve entity and project references.
4. Resolve previous research references.
5. Validate ownership and access.
6. Check for conflicting contextual interpretations.
7. Preserve the source of each resolved reference.
8. Mark unresolved ambiguity.
9. Return enriched intent.

### Pseudocode

```text
FUNCTION resolve_request_context(request, context):

    references = identify_unresolved_references(request)

    relevant_context = retrieve_authorized_context(
        references,
        context
    )

    resolved = resolve_references(
        references,
        relevant_context
    )

    validate_context_ownership(resolved)

    ambiguity = identify_remaining_ambiguity(resolved)

    RETURN {
        resolved_context,
        provenance,
        ambiguity
    }
```

## Safeguards

- Use only authorized context.
- Do not expose unrelated personal memories to Research Engine.
- Do not assume similarly named projects are identical.
- Preserve historical and current context separately.
- Request clarification when competing interpretations materially affect execution.

---

# 5. 6.11.3 — Task Decomposition

## Purpose

Break a user request into independent or dependent execution tasks.

A single request may require several operations across both engines.

Example:

"Based on what you know about my project, research three competing products and compare their pricing."

Possible tasks:

1. Retrieve relevant project context from Memory Engine.
2. Identify the research entities.
3. Discover the competitors.
4. Retrieve their current pricing.
5. Normalize pricing attributes.
6. Verify sources.
7. Compare compatible values.
8. Assemble the final response.

## Decomposition principles

- Preserve the original objective.
- Create only useful tasks.
- Avoid duplicate work.
- Identify engine ownership.
- Identify dependencies.
- Define expected outputs.
- Identify validation requirements.
- Support adaptive replanning.

## Task categories

- `CONTEXT_RETRIEVAL`
- `MEMORY_OPERATION`
- `RESEARCH_OPERATION`
- `COMPARISON_OPERATION`
- `VALIDATION_OPERATION`
- `RESPONSE_ASSEMBLY`
- `DIRECT_OPERATION`

## Algorithm

**Input:**

- Structured user request.
- Resolved context.
- Intent classification.
- Available engine capabilities.

**Output:**

- Task list.
- Task descriptions.
- Dependencies.
- Expected outputs.
- Completion criteria.

### Processing steps

1. Identify the final user objective.
2. Identify required information.
3. Determine required engine capabilities.
4. Generate candidate tasks.
5. Remove redundant tasks.
6. Identify task dependencies.
7. Assign task ownership.
8. Define expected outputs.
9. Define validation requirements.
10. Validate task coverage against the original request.

### Pseudocode

```text
FUNCTION decompose_request(request):

    objective = identify_final_objective(request)

    requirements = extract_information_requirements(
        objective
    )

    candidate_tasks = generate_tasks(requirements)

    tasks = remove_redundant_tasks(candidate_tasks)

    FOR EACH task IN tasks:
        task.owner = determine_task_owner(task)
        task.output_contract = define_expected_output(task)

    dependencies = identify_dependencies(tasks)

    validate_task_coverage(tasks, objective)

    RETURN {
        tasks,
        dependencies
    }
```

## Safeguards

- Do not assign Memory Engine responsibilities to Research Engine.
- Do not assign Research Engine responsibilities to Memory Engine.
- Do not create parallel tasks when one requires another's output.
- Do not omit user constraints.
- Do not create tasks without a defined purpose or output.

---

# 6. 6.11.4 — Execution Plan Generation

## Purpose

Convert the task list into an executable plan.

Task decomposition identifies what needs to happen.

Execution planning determines the order, dependencies, priorities, and recovery boundaries.

## Planning dimensions

- Task dependencies.
- Engine ownership.
- Expected execution cost.
- Importance.
- Urgency.
- Resource requirements.
- Validation requirements.
- Failure impact.
- Cancellation requirements.

## Execution patterns

### Sequential

Use when a task depends on another task's output.

Example:

Memory retrieval → context enrichment → targeted research.

### Parallel

Use when tasks are independent.

Example:

Researching two unrelated companies using independent sources.

### Hybrid

Use a combination of sequential and parallel execution.

This is the default strategy for complex requests.

## Algorithm

**Input:**

- Task list.
- Dependency graph.
- Task priorities.
- Resource constraints.

**Output:**

- Execution plan.
- Task ordering.
- Dependency graph.
- Execution groups.
- Checkpoint boundaries.

### Processing steps

1. Validate all tasks.
2. Validate task ownership.
3. Construct dependency graph.
4. Detect circular dependencies.
5. Identify independent task groups.
6. Determine sequential and parallel execution opportunities.
7. Assign priorities.
8. Define checkpoints.
9. Define expected failure handling.
10. Validate the execution plan.

### Pseudocode

```text
FUNCTION generate_execution_plan(tasks):

    validate_tasks(tasks)

    graph = build_dependency_graph(tasks)

    IF graph.contains_cycle:
        RETURN INVALID_DEPENDENCY_GRAPH

    groups = identify_execution_groups(graph)

    priorities = assign_task_priorities(tasks)

    checkpoints = define_checkpoint_boundaries(groups)

    plan = create_execution_plan(
        groups,
        priorities,
        checkpoints
    )

    validate_plan(plan)

    RETURN plan
```

## Planning safeguards

- Circular dependencies must be rejected.
- Dependencies cannot be silently ignored.
- Critical validation tasks must not be skipped.
- Parallel execution must respect resource limits.
- Plan changes must be recorded.

---

# 7. 6.11.5 — Engine Routing & Capability Selection

## Purpose

Determine which Raven component should execute each task.

Routing is based on capability ownership, not merely keyword matching.

## Routing rules

| Task requirement | Owner |
|---|---|
| Retrieve personal memories | Memory Engine |
| Extract and evaluate personal memories | Memory Engine |
| Resolve memory contradictions | Memory Engine |
| Consolidate personal memory | Memory Engine |
| Forget or delete personal memories | Memory Engine |
| Discover external information | Research Engine |
| Extract external source content | Research Engine |
| Verify research claims | Research Engine |
| Compare research findings | Research Engine |
| Maintain research sessions | Research Engine |
| Coordinate tasks | Agent Orchestrator |
| Manage execution state | Agent Orchestrator |
| Assemble cross-engine results | Agent Orchestrator |
| Validate final combined response | Agent Orchestrator |

## Routing outcomes

- `MEMORY_ENGINE`
- `RESEARCH_ENGINE`
- `ORCHESTRATOR`
- `DIRECT_RESPONSE`
- `MULTI_ENGINE`
- `CLARIFICATION_REQUIRED`

## Hybrid routing logic

### Memory-first

When historical or personal context is needed before external research.

### Research-first

When the task requires external research without personal context.

### Parallel engine routing

When Memory and Research operations are independent and can safely execute simultaneously.

### Direct response

When neither engine is needed and the Orchestrator is permitted to handle the request directly.

## Algorithm

**Input:**

- Task.
- Intent classification.
- Capability registry.
- Context requirements.
- Engine availability.

**Output:**

- Selected engine.
- Routing rationale.
- Required input contract.
- Routing status.

### Processing steps

1. Identify the task capability.
2. Identify its authoritative owner.
3. Validate that the owner supports the operation.
4. Check required input references.
5. Determine whether another task must execute first.
6. Check engine availability.
7. Assign the destination.
8. Record the routing decision.

### Pseudocode

```text
FUNCTION route_task(task):

    capability = identify_required_capability(task)

    owner = resolve_capability_owner(capability)

    IF owner == NONE:
        RETURN UNSUPPORTED_CAPABILITY

    validate_engine_contract(owner, task)

    IF NOT engine_available(owner):
        RETURN ROUTING_BLOCKED

    RETURN {
        destination: owner,
        input_contract,
        routing_rationale
    }
```

## Safeguards

- One authoritative owner per business capability.
- The Orchestrator must not duplicate engine business logic.
- An engine must not modify another engine's records directly.
- Routing must preserve user and execution scope.
- Unsupported capabilities must be reported explicitly.

---

# 8. 6.11.6 — Dependency Resolution & Scheduling

## Purpose

Determine when a task is ready to execute.

A task may be queued but still blocked by incomplete dependencies.

The Orchestrator must distinguish between task existence and task readiness.

## Task readiness conditions

A task may execute when:

- Its required dependencies are complete.
- Its input references are available.
- Its execution context is valid.
- Its engine destination is available.
- Required authorization checks pass.
- Resource capacity is available.

## Scheduling priorities

Evaluate:

- Dependency readiness.
- Importance.
- Urgency.
- Expected value.
- Resource cost.
- User-requested priority.
- Correctness criticality.

Correctness and safety requirements take precedence over efficiency.

## Algorithm

**Input:**

- Execution plan.
- Task states.
- Dependency graph.
- Resource availability.

**Output:**

- Ready task queue.
- Blocked task list.
- Scheduling priority.

### Processing steps

1. Load the execution plan.
2. Retrieve current task states.
3. Evaluate dependency completion.
4. Validate input availability.
5. Check authorization.
6. Check resource availability.
7. Identify ready tasks.
8. Calculate scheduling priority.
9. Add eligible tasks to the queue.
10. Preserve blocked-task reasons.

### Pseudocode

```text
FUNCTION resolve_task_dependencies(execution):

    tasks = load_execution_tasks(execution)

    ready = []
    blocked = []

    FOR EACH task IN tasks:

        IF task.status == COMPLETED:
            continue

        dependencies = load_task_dependencies(task)

        IF NOT all_dependencies_completed(dependencies):
            blocked.append(task)
            continue

        IF NOT required_inputs_available(task):
            blocked.append(task)
            continue

        IF NOT authorization_valid(task):
            blocked.append(task)
            continue

        IF NOT resource_capacity_available(task):
            blocked.append(task)
            continue

        ready.append(task)

    ready = prioritize_tasks(ready)

    RETURN {
        ready_tasks,
        blocked_tasks
    }
```

## Safeguards

- A blocked task must not be dispatched.
- Failed dependencies must not be treated as completed.
- Skipped dependencies require explicit policy handling.
- Dependency changes must be traceable.
- Circular dependencies must never enter the execution queue.

---

# 9. 6.11.7 — Adaptive Parallelism & Resource Allocation

## Purpose

Allocate execution capacity across independent tasks while protecting system reliability.

Parallelism can improve throughput but can also increase:

- Resource contention.
- External service load.
- Database concurrency.
- Failure complexity.
- Duplicate work.
- Cost.

Raven should use selective parallelism rather than maximizing concurrent execution.

## Allocation dimensions

- Task priority.
- Dependency readiness.
- Estimated resource cost.
- Engine capacity.
- External service limits.
- Execution deadlines.
- Current system load.
- Retry state.
- Reserved critical capacity.

## Allocation strategy

Use bounded concurrency with adaptive capacity.

The system must not use a fixed assumption that every task should run simultaneously.

### Example

A request requiring research on three independent companies may allow parallel research tasks.

However, if all three tasks require the same rate-limited source, their retrieval operations may need controlled scheduling.

## Algorithm

**Input:**

- Ready tasks.
- Resource budgets.
- Engine capacity.
- Current system load.
- External service limits.

**Output:**

- Dispatch group.
- Resource allocation.
- Deferred task list.

### Processing steps

1. Retrieve ready tasks.
2. Evaluate task dependencies.
3. Estimate resource requirements.
4. Inspect engine capacity.
5. Inspect external service limits.
6. Reserve capacity for critical tasks.
7. Select a safe dispatch group.
8. Apply concurrency limits.
9. Defer tasks that exceed capacity.
10. Monitor execution load.
11. Recalculate allocation when conditions change.

### Pseudocode

```text
FUNCTION allocate_execution_resources(tasks, capacity):

    validate_capacity_configuration(capacity)

    prioritized = prioritize_tasks(tasks)

    dispatch = []
    deferred = []

    FOR EACH task IN prioritized:

        requirement = estimate_resource_cost(task)

        IF capacity.supports(task, requirement):
            dispatch.append(task)
            reserve_capacity(task, requirement)
        ELSE:
            deferred.append(task)

    RETURN {
        dispatch,
        deferred,
        remaining_capacity
    }
```

## Safeguards

- Concurrency must remain bounded.
- Engine-specific capacity must be respected.
- External rate limits must be respected.
- Critical tasks must not be starved by low-priority tasks.
- Parallel execution must not violate data ownership or consistency.
- Capacity exhaustion must not silently discard tasks.

---

# 10. 6.11.8 — Execution Context Assembly

## Purpose

Prepare the information an engine needs to execute a task.

The Orchestrator must not pass the entire conversation or all available memory to every engine.

Context must be relevant, authorized, and bounded.

## Context categories

- User identity and authorization scope.
- Execution identity.
- Task identity.
- Original request.
- Task-specific instructions.
- Relevant memory references.
- Relevant research references.
- Entity references.
- Temporal constraints.
- Previous task results.
- Required output contract.
- Processing metadata.

## Context assembly principles

1. Minimum necessary context.
2. Reference-based sharing where possible.
3. Explicit ownership and access validation.
4. Preserve provenance.
5. Preserve temporal information.
6. Avoid duplicate context.
7. Support additional context requests through authorized interfaces.

## Algorithm

**Input:**

- Execution.
- Task.
- Required context fields.
- Authorized context references.
- Dependency results.

**Output:**

- Task-specific context package.
- Context provenance.
- Validation status.

### Processing steps

1. Identify required context for the task.
2. Retrieve relevant execution metadata.
3. Collect required dependency outputs.
4. Retrieve authorized memory or research references.
5. Remove irrelevant context.
6. Deduplicate references.
7. Validate access boundaries.
8. Preserve provenance and timestamps.
9. Validate the output contract.
10. Dispatch the context package.

### Pseudocode

```text
FUNCTION assemble_task_context(task, execution):

    requirements = identify_context_requirements(task)

    context = initialize_context_package(task)

    context.add(execution.metadata)

    context.add(
        retrieve_dependency_results(task)
    )

    context.add(
        retrieve_authorized_references(requirements)
    )

    context = remove_irrelevant_context(context)

    context = deduplicate_context(context)

    validate_context_access(context)

    validate_context_contract(context)

    RETURN context
```

## Safeguards

- Do not expose unrelated private memories.
- Do not pass unauthorized research sessions.
- Preserve source references and timestamps.
- Do not convert uncertain information into confirmed context.
- Context snapshots must be scoped to their execution and retention policy.

---

# 11. 6.11.9 — Execution State & Progress Management

## Purpose

Track the lifecycle of the complete user request and every individual task.

The execution state must be centrally managed by the Orchestrator.

Engine-level operation status may be returned through interfaces, but the Orchestrator owns the overall execution state.

## Execution states

- `CREATED`
- `VALIDATED`
- `PLANNING`
- `READY`
- `RUNNING`
- `PARTIALLY_COMPLETED`
- `BLOCKED`
- `RECOVERING`
- `CANCELLATION_REQUESTED`
- `CANCELLED`
- `COMPLETED`
- `FAILED`

## Task states

- `CREATED`
- `VALIDATED`
- `BLOCKED`
- `QUEUED`
- `DISPATCHED`
- `RUNNING`
- `COMPLETED`
- `RETRYING`
- `FAILED`
- `SKIPPED`
- `CANCELLATION_REQUESTED`
- `CANCELLED`

## State transition principles

- Every transition must be valid.
- State changes must be recorded.
- Completed tasks must not be unnecessarily repeated.
- Failed tasks must remain distinguishable from blocked tasks.
- Partial completion must be represented.
- Cancellation must be explicit.
- Execution completion requires evaluation of required tasks.

## Algorithm

**Input:**

- Execution record.
- Task records.
- Engine operation results.
- State transition events.

**Output:**

- Updated execution state.
- Updated task states.
- Progress metadata.
- State history.

### Processing steps

1. Receive execution event.
2. Identify execution and task.
3. Validate event ownership.
4. Validate the requested state transition.
5. Update task state.
6. Recalculate dependent task readiness.
7. Recalculate overall execution status.
8. Persist state transition.
9. Update progress metadata.
10. Trigger the next orchestration action.

### Pseudocode

```text
FUNCTION update_execution_state(execution, event):

    validate_execution_event(event)

    task = resolve_task(event.task_id)

    validate_state_transition(task.status, event.new_status)

    persist_task_state(task, event.new_status)

    tasks = load_execution_tasks(execution)

    execution_status = calculate_execution_status(tasks)

    persist_execution_state(
        execution,
        execution_status
    )

    RETURN {
        execution_status,
        task_status,
        progress
    }
```

## Completion rules

An execution may be marked complete only when:

- All required tasks have completed.
- Required outputs have passed validation.
- No mandatory dependency remains unresolved.
- Final response assembly is complete.

Optional tasks may be skipped under an explicit policy, but their status must remain visible.

---

# 12. 6.11.10 — Failure Recovery & Cancellation Coordination

## Purpose

Coordinate recovery and cancellation across the entire execution.

A failure in one engine must not automatically invalidate successful work performed by another engine.

Similarly, cancellation must prevent unnecessary new work while allowing already completed work to remain available according to retention policy.

## Failure categories

- `VALIDATION_FAILURE`
- `ROUTING_FAILURE`
- `ENGINE_UNAVAILABLE`
- `TIMEOUT`
- `DEPENDENCY_FAILURE`
- `RESOURCE_EXHAUSTION`
- `PERSISTENCE_FAILURE`
- `OUTPUT_VALIDATION_FAILURE`
- `CONCURRENCY_CONFLICT`
- `CANCELLATION_FAILURE`

## Recovery strategies

### Retry

Use for transient and retryable failures.

### Partial recovery

Preserve completed tasks and retry only failed operations.

### Replanning

Modify the execution plan when a dependency or engine becomes unavailable.

### Graceful degradation

Return useful partial results when optional work cannot be completed.

### Escalation

Request clarification or report that a critical requirement cannot be satisfied.

## Cancellation principles

1. Record the cancellation request.
2. Prevent new tasks from being dispatched.
3. Signal running tasks to cancel cooperatively.
4. Preserve completed results according to retention policy.
5. Clean temporary resources.
6. Confirm cancellation state.
7. Do not claim cancellation before it is confirmed.

## Algorithm

**Input:**

- Execution.
- Failure or cancellation event.
- Task states.
- Retry policies.
- Completed results.

**Output:**

- Recovery or cancellation plan.
- Updated execution status.
- Preserved results.
- Failure information.

### Processing steps

1. Receive failure or cancellation event.
2. Validate execution ownership.
3. Identify affected tasks.
4. Preserve completed task outputs.
5. Evaluate whether the failure is retryable.
6. Check retry and resource budgets.
7. Retry, replan, degrade, or escalate.
8. If cancellation is requested, prevent new dispatches.
9. Signal active tasks.
10. Reconcile engine operation states.
11. Update execution state.
12. Record recovery or cancellation outcome.

### Pseudocode

```text
FUNCTION coordinate_failure_or_cancellation(execution, event):

    validate_event(event)

    affected = identify_affected_tasks(execution, event)

    preserve_completed_results(execution)

    IF event.type == CANCELLATION:

        mark_execution_cancellation_requested(execution)

        stop_new_dispatches(execution)

        signal_running_tasks_to_cancel(affected)

        reconcile_task_states(affected)

        RETURN cancellation_status

    strategy = classify_failure_and_select_recovery(
        event,
        affected
    )

    execute_recovery_strategy(strategy)

    recalculate_execution_state(execution)

    RETURN recovery_status
```

## Recovery safeguards

- Retry only retryable operations.
- Use bounded retry policies.
- Do not rerun completed tasks unnecessarily.
- Preserve idempotency.
- Do not treat timeouts as proof that an engine operation failed.
- Reconcile uncertain operation states before retrying.
- Do not hide partial failures.
- Do not report success when required tasks remain incomplete.

---

# 13. Orchestration Execution Lifecycle

The algorithms above form the following logical lifecycle:

```text
User Request
     |
     v
Validation & Intent Understanding
     |
     v
Contextual Resolution
     |
     v
Task Decomposition
     |
     v
Execution Plan Generation
     |
     v
Engine Routing
     |
     v
Dependency Resolution
     |
     v
Resource Allocation
     |
     v
Context Assembly
     |
     v
Task Dispatch
     |
     v
Execution State Management
     |
     +------ Failure / Cancellation
     |                |
     |                v
     |        Recovery Coordination
     |                |
     +----------------+
     |
     v
Result Collection
     |
     v
Cross-Engine Response Assembly
     |
     v
Final Validation
     |
     v
Response Delivery
```

This is a logical execution model. Exact implementation protocols and infrastructure are deferred to later phases.

---

# 14. Orchestrator Execution Data Contract

The following is a conceptual contract.

```text
OrchestrationExecution:
    execution_id
    user_id
    original_request
    primary_intent
    secondary_intents
    execution_plan_reference
    context_reference
    task_references
    execution_status
    progress_metadata
    cancellation_status
    failure_metadata
    created_at
    updated_at
    completed_at

OrchestrationTask:
    task_id
    execution_id
    task_type
    owner_engine
    input_contract
    output_contract
    dependency_references
    priority
    resource_requirements
    task_status
    retry_count
    checkpoint_reference
    result_reference
    created_at
    updated_at
```

These are logical contracts, not finalized database schemas.

The Orchestrator owns execution and task records. Engine-owned business records remain with their respective engines.

---

# 15. Security & Privacy Requirements

1. Every execution must be scoped to an authorized user.
2. Engine routing must preserve ownership boundaries.
3. Context assembly must enforce least privilege.
4. Cross-engine references must be validated.
5. Execution IDs and task IDs must be traceable.
6. Sensitive context must not be unnecessarily copied.
7. Engine results must be validated before use.
8. External content must remain untrusted.
9. Cancellation and deletion operations must be authorized.
10. Logs must not expose secrets or unnecessary private information.
11. Cross-user task execution must be prevented.
12. Recovery must preserve data integrity and deletion state.

---

# 16. Evaluation Metrics

These metrics will be evaluated during Phase 12.

| Area | Metric |
|---|---|
| Intent understanding | Intent classification accuracy |
| Context resolution | Reference resolution accuracy |
| Decomposition | Task coverage |
| Planning | Dependency graph correctness |
| Routing | Engine routing accuracy |
| Scheduling | Task readiness accuracy |
| Parallelism | Safe concurrency utilization |
| Context | Context relevance and isolation |
| State management | State transition correctness |
| Recovery | Recovery success rate |
| Cancellation | Cancellation completion accuracy |
| Reliability | Duplicate execution rate |
| Reliability | Completed-work preservation |
| Quality | Incorrect completion rate |

Numerical targets will be established during Phase 12.

---

# 17. Dependencies

This phase depends on:

- Phase 1 — Overall System Architecture.
- Phase 4 — Agent Orchestrator Architecture.
- Phase 5.3 — Core Entities & Relationships.
- Phase 5.6 — Orchestrator Data Models.
- Phase 5.7 — Shared Infrastructure Data Models.
- Phase 6.1 — Shared Algorithm Framework.
- Phase 6.2–6.5 — Memory Engine Algorithms.
- Phase 6.6–6.10 — Research Engine Algorithms.

---

# 18. Phase 6.11 Completion Criteria

The specification is complete when:

- User requests can be validated and interpreted.
- Contextual references can be resolved safely.
- Requests can be decomposed into tasks.
- Execution plans can represent dependencies.
- Tasks can be routed to the correct engine.
- Ready and blocked tasks can be distinguished.
- Parallelism can be bounded and adaptive.
- Context can be assembled with least privilege.
- Execution and task states can be managed consistently.
- Failures can be recovered without unnecessary repetition.
- Cancellation can be coordinated safely.
- Security and ownership boundaries are preserved.

**Completion status:** Specification complete when documented and reviewed. Implementation, routing calibration, concurrency tuning, and testing remain future work.

---

# 19. Next Algorithm Group

**Phase 6.12 — Agent Orchestrator: Result Validation & Response Assembly**

The next document will define:

1. Engine result normalization.
2. Cross-engine result reconciliation.
3. Memory and Research result merging.
4. Duplicate information detection.
5. Conflict preservation.
6. Evidence-aware response assembly.
7. Uncertainty and completeness evaluation.
8. Response formatting.
9. Final response validation.
10. Delivery-state management.

Phase 6.11 defines how Raven coordinates execution. Phase 6.12 defines how it turns engine outputs into a reliable final result.

**Important:** This document specifies intended behavior. It does not claim that orchestration, routing, scheduling, parallel execution, state management, recovery, or cancellation have been implemented.
