# Requirements: Pydantic Graph Workflow Implementation

## Overview

Transition the workflow system from a conceptual state-driven DAG to a concrete implementation using Pydantic AI / Pydantic Graph. The system will execute a series of predefined steps, utilizing a global state dictionary persisted in Postgres.

## Core Objectives

- **Type-Safe State:** Replace "string-ly typed" state transitions with Pydantic-validated state objects.
- **Dynamic Routing:** Use a router-based approach to determine the next step in the graph based on the current state and step output.
- **Durable Persistence:** Store the workflow context as a JSONB blob in Postgres to allow for checkpointing and recovery.
- **Predefined Step Library:** Implement a registry of reusable "steps" (nodes) that can be composed into various graphs.

## Technical Requirements

### 1. State Management

- **Global Context:** A `WorkflowContext` Pydantic model that tracks all variables, outputs, and metadata across the execution.
- **Persistence:**
  - Table: `workflow_instances` (or similar).
  - Column: `state` (JSONB).
  - Every node completion must trigger a state snapshot to Postgres to ensure recovery from failure.

### 2. Graph Architecture

- **Node Definition:** Each predefined step must be implemented as a Pydantic AI agent or a structured function that accepts the current state and returns a state update + a transition signal.
- **Routing Logic:**
  - Implement a Router mechanism that evaluates the output of a node to determine the next node ID.
  - Support for conditional branching (e.g., if `step_result == 'error'`, route to `error_handler_node`).
- **Execution Loop:** A `GraphRunner` that handles the loop of: Fetch State → Execute Node → Update State → Route to Next.

### 3. Step Registry

- A centralized registry where predefined steps are mapped to their implementation.
- Steps should be decoupled from the graph structure, allowing the same step to be reused in different workflows.

## Technical Deep Dive

### 1. The State Persistence Loop (Hydration/Dehydration)

To ensure zero-loss checkpointing, the `GraphRunner` will implement the following lifecycle for every node execution:

1. **Fetch:** Retrieve the state JSONB blob from `workflow_instances` using the `workflow_id`.
2. **Hydrate:** Parse the JSONB into the `WorkflowContext` Pydantic model. This ensures that any schema migrations or missing keys are handled at the start of the step.
3. **Execute:** Pass the hydrated context to the node function. The node performs its logic and returns a `NodeResult` (containing the updated state delta and the next node ID).
4. **Merge & Dehydrate:** Merge the state delta into the global context and serialize the updated `WorkflowContext` back to a JSONB blob.
5. **Commit:** Update the Postgres record and the `current_node_id` in a single transaction.

### 2. The Routing Contract

To avoid "string-ly typed" routing, we will use a structured Transition object.

- **Node Output:** Each node must return a `NodeOutput` model:

```python
class NodeOutput(BaseModel):
    state_update: Dict[str, Any]
    next_step: str  # The ID of the next predefined step
    status: Literal["success", "failure", "awaiting_input"]
```

- **Router Logic:** The `GraphRunner` reads the `next_step` ID. If the status is `awaiting_input`, the runner halts execution and marks the workflow as `PAUSED`, waiting for an external trigger (User/API) to resume.

### 3. The Step Registry Pattern

To keep the graph decoupled from the implementation, we will use a Registry pattern:

- **Registry:** A singleton `StepRegistry` that maps `step_id` (string) → `Callable` (the actual function/agent).
- **Registration:** Use a decorator `@workflow_step("step_id")` to register functions at boot time.
- **Resolution:** The `GraphRunner` looks up the function in the registry using the `next_step` ID. This allows us to swap out the implementation of a "step" without changing the graph definition.

## Frontend & Orchestration: Phoenix LiveView

### Overview

To provide real-time visibility and Human-In-The-Loop (HITL) interaction, a Phoenix LiveView layer will be implemented as the "Control Plane" for the workflow system.

### Architecture: The Polyglot Bridge

Since the core execution is in Python and the UI is in Elixir, the system will use Postgres as the asynchronous bridge:

1. **State Updates:** The Python `GraphRunner` updates the `workflow_instances` JSONB state in Postgres.
2. **Real-time Notification:** The system will utilize Postgres `NOTIFY`/`LISTEN` or a dedicated event table. When a state change is committed by Python, Phoenix is notified.
3. **WebSocket Push:** Phoenix LiveView pushes the updated state to the browser via WebSockets, updating the UI instantly without a page refresh.

### Key LiveView Components

- **Workflow Dashboard:** A real-time list of active, paused, and completed workflow instances.
- **Graph Visualizer:** A visual representation of the predefined steps (using LiveView Hooks + JS library) where the currently executing node is highlighted.
- **HITL Interaction Portal:** A dedicated interface for nodes with a status of `awaiting_input`. This allows users to provide the necessary data to "unblock" the `GraphRunner` and trigger the next transition.

### Integration Roadmap

- **Phase 1 (Read-Only):** Implement a LiveView page that polls/listens to the `workflow_instances` table to show current progress.
- **Phase 2 (Visualization):** Integrate a graph rendering library to map the `StepRegistry` into a visual DAG.
- **Phase 3 (Bi-directional):** Implement the "Resume" trigger, allowing LiveView to send a signal (via API/Queue) to the Python `GraphRunner` to continue execution.

## Success Criteria

- [ ] A workflow can be started, paused (checkpointed), and resumed from a specific node using the Postgres JSONB state.
- [ ] State transitions between nodes are validated by Pydantic models, preventing runtime type errors.
- [ ] The system can successfully route through a non-linear path based on data returned by a predefined step.

## Out of Scope

- Dynamic graph generation (the graph structure itself is predefined).
- Complex UI for graph visualization (handled in separate feature request).
- Network-level distributed execution (single-process async loop is sufficient).