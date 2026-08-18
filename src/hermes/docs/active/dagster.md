# Dagster Reference

A practical guide covering what Dagster is, how it compares to Prefect and Airflow, and how to apply it to DB-driven dynamic workflows.

---

## What is Dagster?

Dagster is an open-source data orchestrator. Unlike Airflow and Prefect, which model workflows as **tasks to run in order**, Dagster models workflows as **data assets and how they are produced**. This inversion — thinking about data products instead of compute steps — is the entire design philosophy.

A **software-defined asset** is a Python function decorated with `@asset` that declares:
- What data object it produces (a table, a file, a model)
- Which other assets it depends on

Dagster derives the execution graph from those declarations. You describe the data; Dagster figures out the order.

```python
import dagster as dg

@dg.asset
def raw_sales_data():
    return load_from_source()

@dg.asset(deps=[raw_sales_data])
def cleaned_sales_data(raw_sales_data):
    return clean(raw_sales_data)

@dg.asset(deps=[cleaned_sales_data])
def sales_report(cleaned_sales_data):
    return build_report(cleaned_sales_data)
```

Dagster sees the dependency chain and materializes assets in the right order automatically.

---

## Does Dagster Need Airflow?

No. Dagster is fully standalone. The only relationship is optional and goes the other direction — Dagster ships a `dagster-airflow` integration that can run existing Airflow DAGs inside Dagster to enable incremental migration. A greenfield Dagster install has no Airflow dependency.

---

## Is Dagster Open Source?

Yes. The core is fully open source and free to self-host. Dagster+ (the managed cloud product) is paid, and as of May 2026 removed free credits from Solo and Starter plans — every asset materialization is now billed at ~$0.035–$0.040 per credit from zero. If you self-host the OSS version this is irrelevant.

---

## How Dagster Runs

A self-hosted Dagster deployment has three long-running pieces:

| Component | Role |
|---|---|
| `dagster-webserver` | Serves the UI and GraphQL API |
| `dagster-daemon` | Handles schedules, sensors, and run queuing |
| Code location | Your Python package — where ops/assets/jobs are defined |

For local development, `dagster dev` starts all three in one command.

Triggering a run does not require the UI:

```bash
# CLI
dagster job execute -j my_job

# Asset materialization
dagster asset materialize --select my_asset

# Sensor (event-driven, defined in code)
# Schedule (cron-based, defined in code)
# GraphQL API (programmatic)
```

---

## Dagster vs Airflow vs Prefect

| | Airflow | Dagster | Prefect |
|---|---|---|---|
| **Core abstraction** | Task graph (DAG) | Data assets | Python functions |
| **Dynamic workflows** | Hard, footguns at scale | `DynamicOut` for fan-out | First-class, decorator-based |
| **dbt integration** | Operator-level | Native — dbt models become assets with lineage | Task-level |
| **Developer experience** | Steep setup, XML-era feel | Asset model has learning curve | Lowest friction |
| **Testing** | Hard to unit test without infra | Unit test pipelines without mocking infra | Moderate |
| **Best for** | Enterprise, existing ecosystem | Data-centric teams, lineage-heavy work | Fast iteration, agentic + data mixed workloads |
| **Self-host cost** | Free | Free | Free |
| **Hiring signal** | Strongest (still dominant) | Growing | Moderate |

### When to pick each

- **Stay on Airflow** — if you already have 50+ production DAGs and they work. Migration cost rarely justifies a switch without acute pain.
- **Pick Dagster** — greenfield, dbt-heavy, need per-asset lineage and testability, or regulatory-grade reliability.
- **Pick Prefect** — mixed agentic + data workloads, fast iteration, small team, dynamic Python-native workflows.

---

## Dynamic Workflows in Dagster

Dagster's dynamic mechanism is `DynamicOut` / `DynamicOutput`. It gives you dynamic **width** (how many parallel branches) at runtime — not dynamic topology (which ops exist). The graph shape is still fixed at definition time.

```python
@dg.op(out=dg.DynamicOut())
def load_pieces():
    for idx, piece in load_data().chunk():
        yield dg.DynamicOutput(piece, mapping_key=idx)  # count unknown until runtime

@dg.op
def process_piece(piece): ...

@dg.op
def merge(results): ...

@dg.job
def dynamic_job():
    pieces = load_pieces()
    results = pieces.map(process_piece)   # fan out — N copies at runtime
    merge(results.collect())              # fan back in
```

### What Dagster dynamic is NOT

An agent loop (model → tool call → observe → decide next tool) is not a DAG — it's a control-flow loop that can be cyclic. Dagster's `DynamicOut` gives variable width, not variable topology. Trying to model an agent as a Dagster graph fights the framework.

**The right pattern:** run the agent loop *inside* a single op/asset. Dagster sees one node; the agent does whatever it wants internally.

```python
@dg.asset
def agent_findings(context):
    result = run_pydantic_ai_agent(...)   # full loop lives here
    context.add_output_metadata({"tools_called": result.tool_count})
    return result.output
```

---

## DB-Driven Dynamic Workflows

### The pattern

Store step metadata (not Python source) in Postgres. Dagster reads the table and builds the job graph from it.

```sql
CREATE TABLE workflow_steps (
    id            SERIAL PRIMARY KEY,
    workflow_id   INT NOT NULL,
    step_order    INT NOT NULL,
    name          TEXT NOT NULL,
    script_path   TEXT NOT NULL         -- path to a .py file on disk
);
```

```
workflow_id=1, 5 steps          workflow_id=1, 4 steps (next run)
──────────────────────          ──────────────────────────────────
validate                        validate
extract                         extract
build_deck                      build_deck
build_memo                      build_memo
notify                          (removed)
```

### Option A — Read at code location load time (recommended for stable workflows)

The graph is built once when Dagster starts. Changing the DB requires a code location reload.

```python
import dagster as dg
import subprocess

def load_steps(workflow_id: int) -> list[dict]:
    # SELECT step_order, name, script_path
    # FROM workflow_steps
    # WHERE workflow_id = %s ORDER BY step_order
    ...

def make_op(step: dict):
    @dg.op(name=step["name"])
    def _op(context, upstream=None):
        result = subprocess.run(
            ["uv", "run", step["script_path"]],
            env={**os.environ, "ARETEOS_INPUT_FILE": write_input(upstream)},
            capture_output=True, text=True, timeout=180,
        )
        context.log.info(result.stdout)
        if result.returncode != 0:
            raise Exception(result.stderr)
        return result.stdout
    return _op

def build_workflow_job(workflow_id: int):
    steps = load_steps(workflow_id)
    ops = [make_op(s) for s in steps]

    @dg.job(name=f"workflow_{workflow_id}")
    def _job():
        prev = None
        for op in ops:
            prev = op(prev)   # sequential chain: step1 → step2 → ... → stepN

    return _job

# definitions.py
defs = dg.Definitions(
    jobs=[build_workflow_job(workflow_id=1)]
)
```

**Result in the UI:** a proper N-node graph where each DB row is a visible node, with per-step retry, logs, and timing.

### Option B — Read at run time (for volatile workflows)

If the step list changes between runs and each run must reflect the current DB state, collapse everything into one op. You lose per-step nodes in the UI but gain live DB reads on every trigger.

```python
@dg.op
def execute_workflow(context):
    payload = None
    for step in load_steps(workflow_id=1):    # fresh read every run
        result = subprocess.run(
            ["uv", "run", step["script_path"]],
            env={**os.environ, "ARETEOS_INPUT_FILE": write_input(payload)},
            capture_output=True, text=True, timeout=180,
        )
        context.log.info(f"{step['name']}: {result.stdout}")
        if result.returncode != 0:
            raise Exception(result.stderr)
        payload = result.stdout
    return payload

@dg.job
def dynamic_workflow():
    execute_workflow()
```

---

## Storing Steps: File Paths vs Python Source

### Do NOT store Python source in the DB

```sql
-- Avoid this
step_source TEXT   -- "print(result)\ndo_thing()"
```

Running DB-stored source requires `exec()` — arbitrary code execution of database content. If anything upstream can write to the table, this is a security hole. Even for trusted content, it bypasses version control and makes steps untestable.

### DO store file paths

```sql
-- Do this
script_path TEXT   -- "/scripts/validate.py"
```

Then your op body is simply:

```python
subprocess.run(["uv", "run", step["script_path"]], ...)
```

**Why this works:**
- Scripts live in git — versioned, reviewable, testable
- No `exec()` risk
- Each script is independently runnable outside Dagster
- The DB is pure config/metadata, not a code store
- Fully compatible with PEP 723 inline dependencies (`# /// script`)
- Orchestrator-agnostic — the same scripts work with Prefect, Dagster, or a plain cron job

### Dagster does not "pick up" your script files

Dagster imports your **op definitions** from the code location. The scripts on disk are invisible to Dagster — it never parses or imports them. It only knows the op finished (or failed). The subprocess boundary is the full extent of Dagster's involvement with the script content.

---

## AretéOS File-Contract Compatibility

Your existing step scripts (`validate.py`, `build_deck.py`, `build_memo.py`) are already structured correctly for this pattern:

- Self-contained via PEP 723 inline dependencies
- Input/output via `ARETEOS_INPUT_FILE` env var (JSON envelope)
- Output written to `ARETEOS_WORKSPACE_ARTIFACTS`
- Return JSON on stdout for downstream mapping

The Dagster op wrapper is a thin shell around this contract:

```python
@dg.op(name="validate")
def validate_op(context, upstream=None):
    input_path = write_input_file(upstream)    # write upstream output to temp JSON
    result = subprocess.run(
        ["uv", "run", "/scripts/validate.py"],
        env={
            **os.environ,
            "ARETEOS_INPUT_FILE": input_path,
            "ARETEOS_WORKSPACE_ARTIFACTS": artifacts_dir,
        },
        capture_output=True, text=True, timeout=180,
    )
    context.log.info(result.stdout)
    if result.returncode != 0:
        raise Exception(result.stderr)
    return json.loads(result.stdout)           # pass JSON output to next step
```

Nothing in the existing scripts needs to change.

---

## Quick Reference

```bash
# Install
pip install dagster dagster-webserver

# Start local dev server (daemon + UI + code location)
dagster dev

# Execute a job from CLI
dagster job execute -j workflow_1

# Materialize an asset
dagster asset materialize --select validate

# Reload code location (picks up DB changes for Option A)
# Use UI button or restart `dagster dev`
```