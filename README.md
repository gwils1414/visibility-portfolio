# Hermes

A personal command-line agent that pulls your work signals — GitHub activity, Notion tasks, Obsidian notes — into a local warehouse and turns them into a morning briefing. You launch it with `hermes chat`, pick a model, and talk to it; behind the prompt a [pydantic-ai](https://ai.pydantic.dev) orchestrator delegates to a set of deliberately narrow sub-agents and queries a Postgres database that a nightly [dlt](https://dlthub.com) pipeline keeps fresh.

The north star is a "5 a.m. newspaper in the driveway": open the terminal and get a single brief covering what happened yesterday, what's still outstanding, and where to start today — assembled from your own activity rather than a feed someone else curated. That brief exists; the wider arc toward a self-improving agent (persistent memory, inline evals, reflective fine-tuning) is in progress.

This is a personal project built for one user. The data sources are personal; the patterns — narrow multi-agent orchestration, a local analytics warehouse decoupled from source APIs, sandboxed code execution, an allowlisted shell — are the reusable part, and the reason it's public.

## Contents

- [What it does](#what-it-does)
- [Architecture](#architecture)
- [Stack](#stack)
- [Repo layout](#repo-layout)
- [Setup](#setup)
- [Status & roadmap](#status--roadmap)

## What it does

- **Talks to one orchestrator, fans out to many specialists.** [hermes.py](src/hermes/agents/hermes.py) has no domain knowledge of its own. Every capability is a tool that reads the database, runs a sync helper, or calls a single-purpose sub-agent — filesystem, Notion, Obsidian, morning briefing, sandboxed Python. Each sub-agent is too constrained to act outside its lane.
- **Keeps a local warehouse instead of hammering APIs.** [db/pipeline.py](src/hermes/db/pipeline.py) runs three dlt sources daily — GitHub stats, Notion tasks, Obsidian embeddings — each into its own Postgres schema. Chat turns query that warehouse, so agent latency is decoupled from upstream rate limits and history accrues over time.
- **Grounds answers in your own notes.** Every Obsidian markdown file with a `description:` frontmatter field is embedded locally with Qwen3-Embedding-0.6B; retrieval at runtime is cosine similarity over the stored vectors.
- **Scores itself as it goes.** Every response is judged inline by a small LLM-as-judge, and the scores render as colored 0–1 progress bars beneath the answer.
- **Runs generated code in a locked-down sandbox.** The `pce_agent` writes Python and executes it inside a minimal Docker image ([src/docker/pce/Dockerfile](src/docker/pce/Dockerfile)) with source mounted read-only — this is how HTML briefings and charts get built.
- **Shells out only through an allowlist.** The bash agent's one shell tool accepts a narrow set of `gh`/`git` sub-commands, scans every flag for blocked substrings, and gates each call on a human Yes/No prompt before anything runs.

## Architecture

```
                          ┌─────────────────────────────┐
   User CLI prompt ─────► │  Hermes (orchestrator)      │
                          │  hermes_agent in hermes.py  │
                          └──────────────┬──────────────┘
                                         │ delegates via @tool_plain
   ┌──────────┬──────────┬───────────────┼───────────────┬──────────┬──────────┐
   │          │          │               │               │          │          │
┌──▼─────┐ ┌──▼─────┐ ┌──▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐ ┌─▼────────┐ │
│ bash   │ │ notion │ │ obsidian│ │ morning     │ │ pce         │ │ spin_up_ │ │
│ _agent │ │ _agent │ │ _agent  │ │ _briefing   │ │ _agent      │ │ sub_     │ │
│ FS R/W │ │ MCP →  │ │ brain + │ │ GH + notion │ │ Python in   │ │ agent    │ │
│ + gh   │ │ Notion │ │ memory  │ │ historical  │ │ docker      │ │ ad-hoc   │ │
│ shell  │ │        │ │ CRUD    │ │ pulls       │ │ sandbox     │ │ research │ │
└────────┘ └────────┘ └────┬────┘ └──────┬──────┘ └─────────────┘ └──────────┘ │
                           │             │                                      │
                           ▼             ▼                                      │
                ┌──────────────────────────────────┐                            │
                │  Postgres (db: hermes)            │ ◄──── call_short_term_   ─┘
                │  schemas: github, notion,         │       memory + feedback
                │  obsidian_embeddings,             │
                │  short_term_memory, feedback      │
                └──────────────▲────────────────────┘
                               │ daily ingest
                    ┌──────────┴──────────┐
                    │   dlt pipelines     │
                    │   db/pipeline.py    │
                    └─────────────────────┘
```

The two halves are decoupled on purpose. The **pipeline** is a scheduled writer; the **agent** is a reader. Postgres sits between them because sub-agents fan out in parallel and each logs to short-term memory — a single-writer store (SQLite, DuckDB) serializes or breaks under that, whereas Postgres handles concurrent writers with row-level locking. The full reasoning, including the DuckDB→Postgres migration, is in [Onboarding.md](Onboarding.md#architecture).

## Stack

| Layer | Choice |
|---|---|
| Agent framework | pydantic-ai (orchestrator + typed sub-agents) |
| Models | Ollama Cloud (`gpt-oss:120b`) by default; OpenAI optional via the model picker |
| Ingestion | dlt sources → Postgres, run daily |
| Warehouse | Postgres 16 (schemas per source) |
| Embeddings | sentence-transformers, Qwen3-Embedding-0.6B, local |
| Sandbox | Docker (`python-sandbox`), source mounted read-only |
| CLI | Typer + Rich + prompt-toolkit |
| Integrations | Notion (MCP), GitHub API, Resend, EDGAR |
| Observability | Logfire (pydantic-ai instrumentation) |

## Repo layout

| Path | What's there |
|---|---|
| [src/hermes/agents/](src/hermes/agents/) | The orchestrator and each single-purpose sub-agent |
| [src/hermes/db/](src/hermes/db/) | dlt pipelines, warehouse connections, memory + feedback stores |
| [src/hermes/tools/](src/hermes/tools/) | Tools the agents call — warehouse queries, the allowlisted shell, etc. |
| [src/hermes/cli/](src/hermes/cli/) | The `hermes chat` loop, model picker, slash-command resolver |
| [src/hermes/evals/](src/hermes/evals/) | Inline LLM-as-judge and baseline evals |
| [src/docker/](src/docker/) | The sandbox image for code execution |
| [src/hermes/docs/](src/hermes/docs/) | Design notes and plans for in-flight work |

## Setup

This is the happy path. The full walkthrough — the complete environment-variable table, the Infisical secrets option, and troubleshooting — is in **[Onboarding.md](Onboarding.md)**.

**Prerequisites:** Python 3.12, [uv](https://docs.astral.sh/uv/), Postgres 16, and Docker (only needed for the code-execution sandbox). Accounts: GitHub (PAT with `repo` scope), Notion (internal integration), and [Ollama Cloud](https://ollama.com) for the default model. OpenAI, Resend, and Logfire are optional.

```bash
# 1. System prerequisites (macOS / Homebrew)
brew install python@3.12 uv postgresql@16
brew services start postgresql@16

# 2. Create the warehouse. dlt's destination needs an explicit role,
#    so create a `postgres` superuser alongside the database.
createdb hermes
psql -d hermes -c "CREATE ROLE postgres WITH LOGIN SUPERUSER PASSWORD 'postgres';"

# 3. Install dependencies (reads uv.lock — there is no requirements.txt)
uv sync

# 4. Configure secrets. Copy the template and fill in each value.
cp .env.example .env
#    DB_URL defaults to postgresql://postgres:postgres@localhost:5432/hermes
#    GITHUB_PAT_TOKEN, NOTION_API_KEY (+ NOTION_DATABASE_ID / NOTION_DATASOURCE_ID),
#    OLLAMA_API_KEY, and the OBSIDIAN_*_PATH vars are the ones that matter.
#    See the full table in Onboarding.md.

# 5. Populate the warehouse (runs the three dlt pipelines back-to-back).
#    First run is slow: GitHub endpoints paginate and the embedding model
#    (~600 MB) downloads on first call.
uv run python -m hermes.db.pipeline

# 6. Launch
uv run hermes chat
```

Verify a table landed before launching if you want a sanity check:

```bash
psql -d hermes -c "\dt github.*"
psql -d hermes -c "select count(*) from notion.notion_tasks;"
```

## Status & roadmap

Working today: the CLI agent and its sub-agents, the daily dlt pipeline, Obsidian embedding retrieval, inline evals, the sandboxed code executor, and short-term memory. It runs locally against a personal Postgres instance.

Where it's headed:

- **Self-improving loop** — long-term memory that updates itself, and a feedback pipeline that feeds reflective fine-tuning rather than just storing scores.
- **Workflows from the CLI** — schedule recurring briefs and research jobs (13-week cash flow, PE/industry research) as first-class workflows.
- **A Phoenix LiveView UI** — a dashboard over agents, workflows, analytics, and audit trails, so complex state has visual feedback the terminal can't give.
- **Local guardrail models** — self-hosted PII and safety guardrails instead of relying on hosted checks.
