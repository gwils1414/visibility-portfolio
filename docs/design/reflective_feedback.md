# Hermes Reflective Feedback Loop — Plan

## Overview

Two distinct loops working together:

```
Loop 1 — Real-time:   capture feedback after every response → store in DB
Loop 2 — Daily batch: agent reviews recent feedback → updates own instructions
```

The agent literally rewrites its own operating instructions based on user feedback. Daily cadence keeps it from over-reacting to single bad responses while still adapting quickly enough to feel responsive.

---

## Data Model

```sql
-- feedback per response
CREATE TABLE agent_feedback (
    id              INTEGER PRIMARY KEY,
    session_id      TEXT,
    turn_id         INTEGER,
    user_input      TEXT,
    response        TEXT,
    feedback_type   TEXT,        -- "good" | "bad" | "correction"
    correction      TEXT,        -- what should have happened (optional)
    tags            TEXT[],      -- ["hallucination", "tool_error", "format"]
    created_at      TIMESTAMP DEFAULT now(),
    reviewed_at     TIMESTAMP    -- null until processed by daily batch
);

-- agent's evolving instructions
CREATE TABLE agent_instructions (
    id              INTEGER PRIMARY KEY,
    version         INTEGER,
    instructions    TEXT,
    system_prompt   TEXT,
    rationale       TEXT,        -- why this version was created
    based_on_ids    INTEGER[],   -- feedback IDs that drove this update
    created_at      TIMESTAMP DEFAULT now(),
    active          BOOLEAN
);
```

---

## Loop 1 — Real-Time Capture

### CLI capture after every response

```python
console.print(Markdown(result.output))

feedback = questionary.select(
    "Feedback?",
    choices=[
        "👍 Good",
        "👎 Bad",
        "✏️  Add correction",
        "⏭  Skip"
    ]
).ask()
```

### Branching logic

```python
if feedback.startswith("👍"):
    log_feedback(turn_id, "good")

elif feedback.startswith("👎"):
    reason = questionary.text("What was wrong?").ask()
    tags  = questionary.checkbox(
        "Tag the issue:",
        choices=["hallucination", "tool_error", "format", "tone", "off_topic"]
    ).ask()
    log_feedback(turn_id, "bad", reason=reason, tags=tags)

elif feedback.startswith("✏️"):
    correction = questionary.text("What should it have done?").ask()
    log_feedback(turn_id, "correction", correction=correction)
```

### Skip is the default
Most turns won't get explicit feedback — make Skip the easiest option and don't penalize empty feedback. Only good/bad/correction are signal.

### Optional — auto-tagging
After a few weeks of feedback you could have a small judge model auto-tag responses without requiring user input:

```python
async def auto_tag(user_input: str, response: str) -> list[str]:
    """Light LLM judge to tag potential issues."""
    # only fires when user doesn't manually provide feedback
```

---

## Loop 2 — Daily Reflection

### What the daily job does

```
1. pull all unreviewed feedback from last 24h
2. cluster by tag (hallucination, format, tone, etc.)
3. for each cluster, identify the pattern
4. generate updated instructions that address the pattern
5. write new version of instructions to DB (mark previous inactive)
6. mark feedback as reviewed
```

### Prefect schedule

```python
from prefect import flow, task
from prefect.schedules import CronSchedule

@flow(schedule=CronSchedule(cron="0 3 * * *"))  # 3am daily
async def daily_reflection():
    feedback = await pull_unreviewed_feedback()
    if len(feedback) < 3:
        return  # not enough signal, skip this cycle
    
    current_instructions = await get_active_instructions()
    
    new_instructions = await reflection_agent.run(
        build_reflection_prompt(feedback, current_instructions)
    )
    
    await save_new_instructions(new_instructions, based_on=feedback)
    await mark_feedback_reviewed(feedback)
```

### The reflection prompt

```python
def build_reflection_prompt(feedback: list, current: str) -> str:
    return f"""
    You are reviewing yesterday's feedback to improve your own instructions.
    
    Current instructions:
    ---
    {current}
    ---
    
    Yesterday's feedback ({len(feedback)} items):
    {format_feedback_for_review(feedback)}
    
    Analyze the patterns. For each recurring issue:
    1. Identify the root cause (was it a missing instruction? unclear guideline? wrong tool?)
    2. Propose a specific instruction update that would prevent it
    3. Be precise — vague instructions don't help
    
    Output the FULL updated instructions, not a diff. Keep what's working,
    add or modify what's needed. Explain your reasoning at the top.
    """
```

### Key constraints on the reflection

- **Don't delete existing instructions unless feedback explicitly contradicts them**
- **Prefer additive changes** — adding a guideline is safer than rewriting
- **Version everything** — every update is a new row, never overwrite
- **Always include rationale** so you can audit later why it changed
- **Cap instruction length** — set a max so it doesn't grow indefinitely

### Drift detection
If two days in a row the agent removes the same instruction it added before, that's a signal something deeper is wrong — alert you rather than keep flipping.

---

## How Instructions Get Loaded

```python
def get_instructions() -> str:
    active = db.query(
        "SELECT instructions FROM agent_instructions WHERE active = true"
    )
    return active.instructions or DEFAULT_INSTRUCTIONS
```

Called every turn since `instructions` is dynamic in pydantic-ai. So the new instructions take effect immediately after the daily job runs.

---

## CLI Commands

```
/feedback show              show last 20 feedback entries
/feedback stats             counts by tag, good vs bad ratio
/instructions show          show currently active instructions
/instructions history       show version history with rationale
/instructions rollback <v>  revert to a previous version
/reflection run             manually trigger reflection now (skip schedule)
```

Rollback is critical — if the daily job produces bad instructions, you need a way out.

---

## Build Order

```
Phase 1 — Capture
  ├── DB schema (agent_feedback, agent_instructions)
  ├── log_feedback() function
  └── CLI prompt after each response

Phase 2 — Storage
  ├── get_active_instructions() loaded into agent
  ├── /feedback show command
  └── /instructions show command

Phase 3 — Reflection
  ├── reflection_agent (separate small agent for this job)
  ├── build_reflection_prompt()
  ├── daily_reflection() flow
  └── Prefect schedule

Phase 4 — Safety
  ├── Versioning + rollback
  ├── Drift detection
  ├── Instruction length caps
  └── /reflection run for manual trigger
```

---

## Open Design Questions

- **Granularity** — one set of instructions for all of Hermes, or per-tool feedback that updates tool-specific instructions?
- **Threshold for action** — how many bad ratings on the same pattern before the agent updates? Avoid over-reacting to one bad day.
- **Feedback decay** — should older feedback matter less? Recent corrections weigh more than month-old ones?
- **Reflection model** — use the same model Hermes runs on, or a stronger model for reflection? A stronger judge gives better analysis but adds another dependency.
- **What if the agent disagrees with feedback?** — should it have the ability to "push back" rather than blindly accept all corrections? E.g. "user marked this bad but the response was correct, they may have misunderstood."

---

## Why This Is Interesting

Most "reflective agents" do real-time self-critique in the response itself ("let me check my work"). This is different — it's **offline reflection on aggregated behavior over time**. The agent literally rewrites its operating manual based on what it learned about you. Combined with a local model and persistent feedback storage, you have a genuinely personalized agent that improves measurably over weeks, not just minutes.