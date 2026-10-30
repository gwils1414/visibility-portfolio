# Workflow System: Critical Audit & Robust Architecture

## 1. The "Happy Path" Critique (What's Wrong with the Current Plan)
- **Linearity Trap**: The current "Option A" assumes a perfect sequence. In real-world agentic workflows, Step 3 often needs to loop back to Step 1 based on a condition. A linear loop cannot handle this without "hacky" jump-to-step logic.
- **Brittle State Resolution**: Using `$step_n.output` is a "string-ly typed" nightmare. If a step is inserted at the beginning, all subsequent indices shift, breaking the entire workflow.
- **The 'Black Box' Tool Problem**: The plan treats tools as simple functions. It doesn't account for tools that take 10 minutes to run, tools that fail intermittently, or tools that return massive payloads that crash the context.
- **Lack of Versioning**: The DB schema stores the *current* workflow. There is no concept of "Workflow v1" vs "Workflow v2," making it impossible to regression test changes.

## 2. The "Frontier" Architecture Proposal: State-Driven Directed Acyclic Graph (DAG) with Cycles
Instead of a loop, we move to a **State-Machine** architecture.

### A. The State Object (The Single Source of Truth)
- Move away from `$step_n`. Use a **Global State Dictionary** (e.g., `workflow_context`).
- Steps do not reference other steps; they read from and write to the `workflow_context`.
- **Example**: Step 2 reads `context['user_query']` and writes `context['search_results']`. Step 3 reads `context['search_results']`.

### B. The Execution Engine: Event-Driven Graph
- **Nodes**: Each tool is a node.
- **Edges**: Edges are not just "next step," but "conditional transitions."
- **The Router**: Implement a `Router` node (or let `ask_hermes` be the router) that decides the next node based on the current state.

### C. Robust Error Recovery (The "Human-in-the-Loop" Pattern)
- **Checkpointing**: Every step writes its output to a `workflow_runs` table in DuckDB. If the system crashes at Step 5, it resumes from Step 5, not Step 1.
- **Intervention Points**: Define "Critical" steps that require a `/confirm` from Garett before proceeding.
- **Self-Healing**: If a tool returns an error, the graph routes to an `error_handler` node which uses `ask_hermes` to decide whether to retry, skip, or abort.

## 3. Revised Technical Roadmap
1. **Phase 1: The State Store**: Implement the `workflow_context` and the `workflow_runs` table for persistence.
2. **Phase 2: The Registry**: Map tools to a standard `ToolInterface` (input validation $\rightarrow$ execution $\rightarrow$ output normalization).
3. **Phase 3: The Graph Runner**: Implement a basic `GraphRunner` that supports linear paths but allows for conditional "jumps."
4. **Phase 4: The CLI**: Implement `/run-workflow` with a "live trace" view (showing which node is currently active).
5. **Phase 5: The Designer**: Create `/create-workflow` using a DSL (Domain Specific Language) or a JSON schema that defines the graph.

## 4. Conceptual Code: The State-Driven Runner
```python
class WorkflowState:
    def __init__(self, run_id):
        self.run_id = run_id
        self.context = {} # Global key-value store
        self.history = [] # Audit trail of steps executed

1. **Phase 1: Schema Definition**: Define the Pydantic State models and the DuckDB persistence schema.
2. **Phase 2: Tool Wrapper**: Implement a standard wrapper that converts Pydantic AI agent outputs into state updates.
3. **Phase 3: Orchestrator Implementation**: Build the Pydantic AI controller that manages the transition logic between agents.
4. **Phase 4: CLI & Traceability**: Implement `/run-workflow` with a focus on visualizing the state transitions.
5. **Phase 5: Dynamic Designer**: Create a way to define these Pydantic AI agent chains via the CLI.
class GraphRunner:
    async def execute(self, workflow_id):
        state = self.load_state(workflow_id)
        current_node = state.start_node
        
        while current_node:
            # 1. Execute tool
            result = await tool_registry[current_node].run(state.context)
            
            # 2. Update State
            state.context.update(result)
            state.history.append(current_node)
            
            # 3. Determine Next Node (The Router logic)
            current_node = self.determine_next_node(current_node, state.context)
```