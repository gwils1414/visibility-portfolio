# Hermes Workflow System — Implementation Plan

## Overview

A two-phase system: the agent helps users **design** workflows, the CLI **executes** them on demand. The agent is also available as a node within any workflow.

```
Phase 1 — Design:   user + hermes → workflow stored in DuckDB
Phase 2 — Execute:  /run-workflow <name> → steps run in order → done
```

---

## Core Concepts

### Workflow
A named, repeatable sequence of steps stored in DuckDB.

### Step
A single tool call with a name, arguments, and order. Arguments can reference previous step outputs via `$step_n.output`.

### Tool Registry
A dict mapping tool names to Python functions. The only tools available to workflows are what's in the registry.

---

## Data Model

```sql
-- workflows
CREATE TABLE workflows (
    id          INTEGER PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at  TIMESTAMP DEFAULT now()
);

-- steps
CREATE TABLE workflow_steps (
    id          INTEGER PRIMARY KEY,
    workflow_id INTEGER REFERENCES workflows(id),
    step_order  INTEGER NOT NULL,
    tool_name   TEXT NOT NULL,
    args        JSON NOT NULL,
    description TEXT,          -- human readable, shown during execution
    status      TEXT DEFAULT 'pending'
);
```

### Example stored workflow
```
workflow: "research_and_report"

step 1 | search_web   | {"query": "AI trends 2026"}
step 2 | ask_hermes   | {"prompt": "summarize this into key points: $step_1.output"}
step 3 | generate_pdf | {"title": "AI Report", "content": "$step_2.output"}
step 4 | send_email   | {"to": "garett@arete.com", "attachment": "$step_3.output"}
```

---

## Tool Registry

```python
TOOL_REGISTRY = {
    # file operations (already built)
    "read_file":    read_file,
    "write_file":   write_file,
    "append_file":  append_file,

    # agent as a node
    "ask_hermes":   ask_hermes,     # passes prompt, returns string

    # to be built
    "search_web":   search_web,
    "generate_pdf": generate_pdf,
    "send_email":   send_email,
    "notion_task":  create_notion_task,
}
```

`ask_hermes` is just a thin wrapper:
```python
async def ask_hermes(prompt: str) -> str:
    result = await hermes_agent.run(prompt)
    return result.data
```

---

## Execution Runtime

### Option A — Simple async loop (recommended to start)

```python
async def run_workflow(name: str):
    steps = load_steps(name)          # from DuckDB, ordered
    results = {}

    for step in steps:
        console.print(f"[dim]Running step {step.order}: {step.tool_name}[/dim]")
        args = resolve_args(step.args, results)
        result = await execute_tool(step.tool_name, args)
        results[step.id] = result
        console.print(f"[green]✓[/green] {step.description or step.tool_name}")

    console.print("[bold green]Workflow complete.[/bold green]")
```

Pros: simple, easy to debug, easy to add status updates
Cons: no branching, no parallel steps, no retry logic

### Option B — Pydantic Graph

Build nodes dynamically from DB steps:

```python
from pydantic_ai.graph import Graph, Node

def build_node(step: WorkflowStep) -> type[Node]:
    class DynamicNode(Node[WorkflowState]):
        async def run(self, state: WorkflowState) -> WorkflowState:
            args = resolve_args(step.args, state.results)
            result = await execute_tool(step.tool_name, args)
            state.results[step.id] = result
            return state
    DynamicNode.__name__ = f"Step_{step.order}_{step.tool_name}"
    return DynamicNode

async def run_workflow(name: str):
    steps = load_steps(name)
    nodes = [build_node(s) for s in steps]
    graph = Graph(nodes=nodes)
    state = WorkflowState(workflow_id=steps[0].workflow_id)
    await graph.run(state)
```

Pros: supports branching, parallel steps, typed state, built-in retry
Cons: more complex, overkill until you need those features

### Recommendation
**Start with Option A.** The loop is transparent and debuggable. Migrate to Option B when you need branching or parallelism.

---

## Arg Resolution

```python
def resolve_args(args: dict, results: dict) -> dict:
    resolved = {}
    for key, value in args.items():
        if isinstance(value, str) and value.startswith("$step_"):
            # $step_1.output → results[1]
            step_id = int(value.split(".")[0].replace("$step_", ""))
            resolved[key] = results[step_id]
        else:
            resolved[key] = value
    return resolved
```

---

## CLI Commands

```
/create-workflow <name>    agent helps user define steps interactively
/list-workflows            show all stored workflows
/show-workflow <name>      show steps for a specific workflow
/run-workflow <name>       execute workflow
/delete-workflow <name>    remove workflow
```

---

## Workflow Creation Flow

Two options for how the agent helps build workflows:

### Option A — Conversational (agent generates steps)
```
user: /create-workflow research_report
hermes: "What should this workflow do?"
user: "Search the web, summarize with AI, generate a PDF, email it to me"
hermes: generates step definitions → confirms with user → stores in DuckDB
```

### Option B — Structured (user defines steps explicitly)
```
user: /create-workflow research_report
cli: prompts for each step interactively via questionary
     → tool name (select from registry)
     → args (key/value pairs)
     → repeat until done
```

### Recommendation
**Option A for discovery, Option B for precision.** Let the agent draft the workflow, then let the user review and edit steps before saving.

---

## Build Order

```
Phase 1 — Foundation
  ├── DuckDB schema (workflows + workflow_steps tables)
  ├── CRUD helpers (save_workflow, load_steps, list_workflows)
  └── Tool registry dict

Phase 2 — Runtime
  ├── resolve_args()
  ├── execute_tool()
  └── run_workflow() loop

Phase 3 — CLI Commands
  ├── /list-workflows
  ├── /show-workflow
  ├── /run-workflow
  └── /delete-workflow

Phase 4 — Creation
  ├── /create-workflow (agent-assisted)
  └── Step confirmation + storage

Phase 5 — Expand Registry
  ├── search_web
  ├── generate_pdf
  ├── send_email
  └── notion_task
```

---

## Open Questions

- **Error handling** — if step 2 fails, should the workflow stop or skip to step 3?
- **Dry run** — show what would execute without running it?
- **Step outputs** — store them in DB for audit/replay, or in-memory only?
- **Scheduling** — on demand only for now, but worth leaving a hook for later