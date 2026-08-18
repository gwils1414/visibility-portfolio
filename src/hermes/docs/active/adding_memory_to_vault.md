# Hermes Memory System

## Overview

Hermes uses a two-tier memory architecture backed by an Obsidian vault. The agent reads from both tiers but only writes to the `memory/` tier. The `brain/` tier is curated manually and feeds the existing cosine similarity search.

```
vault/
  memory/                  # agent writes here — dynamic, iterative
    MEMORY.md              # master index — always loaded, describes all other files
    preferences.md         # how the user likes to do things — always loaded
    projects.md            # active projects, context, decisions
    session_log.md         # running log of observations per session
  brain/                   # agent reads only — static, curated examples
    coding_style.md
    patterns.md
    workflows.md
```

All memory files use frontmatter:

```markdown
---
name: preferences
description: How Garett likes to do things — coding patterns, tool choices, formatting conventions
last_updated: 2026-05-29
---
```

---

## Tier Definitions

### `memory/` — Dynamic Memory
- Agent reads and writes
- Updated iteratively as the agent observes patterns and decisions
- Starts with 4 files, grows organically as topics emerge — no fixed limit
- `MEMORY.md` is the master index, always loaded first
- `preferences.md` is always loaded — small and always relevant
- All other files loaded selectively based on session context
- Future: agent may propose promotions to `brain/` for user approval

### `brain/` — Curated Examples
- Agent reads only — never writes
- Fed into cosine similarity search
- Manually maintained by the user
- Represents confirmed, stable preferences and patterns

---

## Memory Files

### `MEMORY.md` — Master Index
Always loaded at session start. Describes what is in every other memory file so the agent can decide what to pull without reading everything. Keep under 200 lines.

```markdown
---
name: memory-index
description: Master index of all Hermes memory files
last_updated: 2026-05-29
---

# Memory Index

## preferences.md
How Garett likes to do things — coding patterns, tool choices, pydantic over dataclasses,
uv for package management, learning from first principles, concise explanations.

## projects.md
Active projects — Accupac analytics platform, Hermes CLI agent. Stack decisions,
current state, key architectural choices.

## session_log.md
Append-only session log. Most recent entries cover gh CLI Bash class debugging,
subprocess cwd issues, ANSI color code fix from gh in Jupyter.
```

As new topic files are created (e.g. `hermes.md`, `accupac.md`, `debugging.md`), add a summary entry here. The index is what makes selective loading possible — without it the agent would have to read every file.

### `preferences.md`
Stores how the user likes to do things — coding patterns, tool choices, formatting conventions, communication style.

```markdown
# Preferences

## Coding
- Prefers pydantic for validation over dataclasses
- Uses uv for Python package management
- Keeps _private attributes with lazy loading pattern
- Type hints on all function signatures

## Tools
- DuckDB for local analytics
- Infisical for secret management
- Logfire for observability
- Marimo for notebooks

## Style
- Prefers learning from first principles before seeing finished code
- Likes concise explanations without excessive bullet points
```

### `projects.md`
Stores active project context — what each project is, its current state, key decisions made, and tech stack.

```markdown
# Projects

## Accupac Analytics Platform
- Status: Active
- Stack: Marimo, pydantic-ai, DuckDB, dbt, Logfire, Infisical
- Key agent: profitability_agent querying fct_sku_profitability
- Message history: plain mutable dict (not mo.state — closure staleness issue)
- Logfire: logfire-us.pydantic.dev/gwilson/accupac

## Hermes
- Status: Active
- Purpose: Personal CLI agentic system
- Tools: gh CLI (Bash class), Obsidian brain, memory system
- Bash allowlist: aretecp org repos only
```

### `session_log.md`
A running append-only log of observations, decisions, and context from each session. Newest entries at the top.

```markdown
# Session Log

## 2026-05-29
- Debugged Bash._fetch_repos — ANSI color codes from gh breaking json.loads in Jupyter
- Fixed by lowercasing nameWithOwner at source in _fetch_repos
- gh repo list must be called with org name explicitly (defaults to personal repos otherwise)
- subprocess cwd should use Path.home() for gh commands to avoid git context issues
```

---

## Agent Instructions

### Reading Memory
At the start of every session:
1. Always load `MEMORY.md` — scan the index to understand what files exist
2. Always load `preferences.md` — small, always relevant
3. Based on the session context and user query, select 1-2 additional files from the index
4. Run cosine similarity against `brain/` for relevant curated examples

Keep injected memory to 10-15% of the context budget — relevant context beats more context.

### Writing to `preferences.md`
Write to `preferences.md` when you observe a clear preference or pattern:
- The user corrects you and explains how they prefer something done
- The user explicitly states a preference ("I always use X for Y")
- You observe a consistent pattern across multiple interactions

Append new entries under the relevant section. Do not overwrite existing entries — add to them.

### Writing to `projects.md`
Write to `projects.md` when:
- A new project is introduced
- A key architectural decision is made
- A significant bug or issue is resolved that future sessions should know about
- The status or stack of a project changes

Keep entries concise — one or two lines per fact. This is a reference, not a journal.

### Writing to `session_log.md`
Append to `session_log.md` at the end of every session with a dated entry summarising:
- What was worked on
- Key decisions or fixes
- Anything that would save time if rediscovered in a future session

Always prepend new entries at the top of the file under a new `## YYYY-MM-DD` heading.

### What NOT to Write
- Do not write routine Q&A or one-off lookups
- Do not write sensitive information (tokens, passwords, keys)
- Do not write speculative observations — only confirmed patterns
- Do not modify `brain/` files under any circumstances

### Creating New Memory Files
When a topic grows large enough to warrant its own file (e.g. `hermes.md`, `accupac.md`, `debugging.md`):
1. Create the new file with frontmatter
2. Move the relevant content out of `projects.md` or `session_log.md`
3. Add a summary entry to `MEMORY.md` immediately

### Updating `MEMORY.md`
Update the index entry for a file whenever its content changes significantly enough that the summary no longer reflects what's inside. Keep summaries to 2-3 lines — just enough for the agent to decide whether to load the file.
Write memory entries in plain, factual language. These are notes for a future instance of the agent, not prose for the user to read. Be specific — "uses pydantic over dataclasses" is more useful than "prefers certain validation libraries".

---

## Example Agent Workflow

```
Session starts
  → Load MEMORY.md (index — always)
  → Load preferences.md (always)
  → Select 1-2 additional files based on query context
  → Run cosine similarity against brain/ for relevant examples

During session
  → User corrects agent on a preference → append to preferences.md
  → Key decision made on Accupac → append to projects.md
  → New topic gets large → create new file, update MEMORY.md index

Session ends
  → Append dated summary to session_log.md
  → Update MEMORY.md index summaries if content changed significantly
```

---

## Implementation Plan

### v1 — Foundation
- [ ] Create `vault/memory/` directory
- [ ] Create `MEMORY.md` with index entries for the 3 starter files
- [ ] Create `preferences.md` with frontmatter and initial content
- [ ] Create `projects.md` with frontmatter and initial content
- [ ] Create `session_log.md` with frontmatter
- [ ] Update Hermes brain tool to always load `MEMORY.md` and `preferences.md` at session start
- [ ] Update brain tool to return top-N results (not just top-1) for selective loading of additional files

### v2 — Selective Loading
- [ ] Agent reads `MEMORY.md` index at session start
- [ ] Agent selects relevant additional files based on query context
- [ ] Brain tool supports returning top-3 from `brain/` instead of top-1
- [ ] Agent updates `last_updated` frontmatter field on write

### v3 — Topic Files
- [ ] Agent can create new topic files when content warrants it
- [ ] Agent updates `MEMORY.md` index when new files are created
- [ ] Session log entries that repeat 3+ times get promoted to a topic file automatically

### v4 — Brain Promotion (Future)
- [ ] Agent tracks pattern frequency in `preferences.md`
- [ ] Agent proposes promotion to `brain/` via CLI (`hermes memory promote --approve`)
- [ ] Approved entries move to `brain/` and are removed from `memory/`

---

## Future: Promotion to `brain/`

In a future iteration, the agent will be able to propose promoting a pattern from `memory/preferences.md` to `brain/` when it has been observed consistently. The user approves or rejects via a CLI command. This is not implemented in v1.