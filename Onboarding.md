# Onboarding — Visibility / Hermes

This repo is two things wearing one skin:

1. **Hermes** — a personal CLI agent. You launch it (`hermes chat`), pick a model, and chat. Behind the prompt sits a [pydantic-ai](https://ai.pydantic.dev) orchestrator agent that delegates to specialist sub-agents (filesystem, Notion, morning briefing) and pulls personal context from an Obsidian vault for grounding. Every response is judged inline by a small LLM-as-judge and the scores render as colored 0–1 progress bars.
2. **A dlt → Postgres pipeline** — daily ingest of GitHub stats (commits, issues, repos) and Notion tasks into a local Postgres database. The agent then queries that database via tools instead of hitting the source APIs on every turn.

The original goal (per [README.md](README.md)) was a "5 a.m. newspaper in the driveway" — a morning HTML brief covering yesterday's GitHub activity and outstanding Notion tasks. That's still the north star, but the project is partway through a wider arc toward a self-improving agent with short-term memory, evals, and reflective fine-tuning.

It is built for one user (Garett). The patterns are reusable; the data sources are personal.

---

## Setup — top to bottom

You need three things on your machine before any code runs: Python 3.12, uv, and Postgres. The repo also assumes you have an Obsidian vault (for context retrieval) and accounts at GitHub, Notion, Ollama Cloud, and Resend — these are configured by env vars, not by code.

### 1. System prerequisites

```bash
# Python 3.12 — see .python-version
brew install python@3.12

# uv — package + venv manager (this repo uses uv.lock, not requirements.txt)
brew install uv

# Postgres 16 — runs as a background service
brew install postgresql@16
brew services start postgresql@16
```

### 2. Create the Postgres database

```bash
createdb hermes
```

The default Homebrew install creates a Postgres role matching your macOS user (e.g. `garettwilson`) with `trust` auth on localhost — that's enough for `psql`. dlt's destination layer is stricter and requires an explicit username + password, so create one:

```bash
psql -d hermes -c "CREATE ROLE postgres WITH LOGIN SUPERUSER PASSWORD 'postgres';"
```

Verify:

```bash
psql -d hermes -c "select current_database();"
```

### 3. Install dependencies

```bash
cd Arete/visibility
uv sync
```

`uv sync` reads [pyproject.toml](pyproject.toml) + [uv.lock](uv.lock) and materializes a `.venv/` with everything pinned. There is no `requirements.txt`.

### 4. Configure secrets

Secrets are managed via **[Infisical](https://infisical.com)** for this project. You have two options:

**Option A — Infisical (preferred).** Install the CLI (`brew install infisical/get-cli/infisical`), authenticate (`infisical login`), and run commands with secrets injected at runtime:

```bash
infisical init
infisical run -- uv run hermes
infisical run -- uv run python -m hermes.db.pipeline
```

Infisical pulls the variables listed below into the process env without touching a local `.env` file.

**Option B — Local `.env`.** Copy [.env.example](.env.example) to `.env` and fill in each value by hand. Use this if you're not set up with Infisical or want to override a value temporarily.

Either way, the full list of variables with what each is for:

| Variable | What it's for | Where to get it |
|---|---|---|
| `DB_URL` | Postgres connection string. Read by [Settings](src/hermes/models/deps.py#L5) and consumed by both the dlt pipelines and the `psycopg` connection helpers. | `postgresql://postgres:postgres@localhost:5432/hermes` if you followed step 2. |
| `OLLAMA_API_KEY` | Ollama Cloud API key. All agents use it via `OpenAIChatModel` pointed at `https://ollama.com/v1` — see [agents/helpers.py:7](src/hermes/agents/helpers.py#L7). The default model is `gpt-oss:120b-cloud`; the CLI also offers `gemma4:31b-cloud`. | [ollama.com](https://ollama.com) account → API keys. |
| `GITHUB_PAT_TOKEN` | GitHub personal access token. Used by the dlt pipeline in [db/github_stats.py](src/hermes/db/github_stats.py) to pull commits, issues, and repo metadata. | GitHub → Settings → Developer settings → PATs. Needs `repo` scope. |
| `OPENAI_API_KEY` | OpenAI key. Lets the CLI's `/models` picker route to `openai-chat:gpt-4.1` instead of the Ollama Cloud models. Optional if you only use the Ollama models. | [platform.openai.com](https://platform.openai.com) → API keys. |
| `NOTION_API_KEY` | Notion integration token. Used by [db/notion_stats.py](src/hermes/db/notion_stats.py) for the daily task pull and by [mcps/notion_mcp.py](src/hermes/mcps/notion_mcp.py) at agent runtime. | [notion.com/my-integrations](https://www.notion.com/my-integrations) → New internal integration → share the relevant database with it. |
| `NOTION_DATABASE_ID` / `NOTION_DATASOURCE_ID` | The two Notion identifiers the pipeline + MCP need. The pipeline reads `NOTION_DATABASE_ID` from the env directly at [db/notion_stats.py:13](src/hermes/db/notion_stats.py#L13); the MCP reads `NOTION_DATASOURCE_ID` via [Settings](src/hermes/models/deps.py#L12) at [mcps/notion_mcp.py:25](src/hermes/mcps/notion_mcp.py#L25). | Notion → open the database → copy the database ID from the URL; the data source ID is exposed via the Notion API once the integration is connected. |
| `GH_ORG` | GitHub org slug used by the bash agent to resolve `--repo` values against `gh repo list <org>` ([bash.py:78](src/hermes/tools/bash.py#L78)). | The org your work lives in (e.g. `aretecp`). |
| `OBSIDIAN_VAULT_PATH` | Absolute path to the Obsidian vault root. Every `.md` file with a `description:` frontmatter field gets embedded and indexed — see [db/obsidian_embeddings.py:26](src/hermes/db/obsidian_embeddings.py#L26). | Wherever your vault lives, e.g. `/Users/you/Documents/Obsidian/MainVault`. |
| `OBSIDIAN_COMMANDS_PATH` | Absolute path to a folder of slash-command skill definitions. Each subdirectory is a slash command; its `SKILL.md` is read and injected into the prompt — see [cli/commands.py:12](src/hermes/cli/commands.py#L12). | Typically a subdirectory of your vault. |
| `OBSIDIAN_MEMORY_PATH` | Absolute path to a `MEMORY/` folder inside your vault. The obsidian sub-agent reads `MEMORY.md` as an index and writes topic files (preferences, project context, session notes) here — see [tools/obsidian_memory.py:16](src/hermes/tools/obsidian_memory.py#L16). | Create a `MEMORY/` subdirectory of your vault and point at it. |
| `RESEND_API_KEY` / `RESEND_DOMAIN` | Resend (transactional email) for sending the morning briefing as an HTML email. Currently a placeholder tool in [tools/resend.py](src/hermes/tools/resend.py). | [resend.com](https://resend.com) dashboard. |
| `LOGFIRE_WRITE_TOKEN` | Logfire token for pydantic-ai instrumentation traces — see `logfire.instrument_pydantic_ai()` at the top of each agent file. Drops every LLM call, tool call, and token count into [logfire.pydantic.dev](https://logfire.pydantic.dev). | Logfire dashboard. |

### 5. Populate the database

```bash
uv run python -m hermes.db.pipeline
```

This runs three dlt pipelines back-to-back: GitHub repos/commits/commit-details/issues → schema `github`, Notion tasks → schema `notion`, Obsidian embeddings → schema `obsidian_embeddings`. First run takes a few minutes (the GitHub bulk endpoints are paginated and the Qwen3 embedding model downloads on first call — ~600 MB).

Verify a table landed:

```bash
psql -d hermes -c "\dt github.*"
psql -d hermes -c "select count(*) from notion.notion_tasks;"
```

### 6. Launch the CLI

```bash
uv run hermes chat
```

You'll see the figlet banner, get prompted to pick a model, and land at a `You:` prompt. Type a question; Hermes streams the response token-by-token via `run_stream` ([chat.py:147](src/hermes/cli/chat.py#L147)), re-renders the green panel when the stream closes, and prints inline eval bars beneath.

Built-in keywords at the prompt (not slash commands — they're matched before the slash-command resolver runs):

| Keyword | What it does |
|---|---|
| `models` | Re-open the model picker mid-session. |
| `commands` | List the slash commands discovered under `OBSIDIAN_COMMANDS_PATH`. |
| `memory` | Asks Hermes to review the current session via `call_short_term_memory` and update or create memory files in your vault. |
| `feedback` | Prompt a 👍 / 👎 + freeform reason, store it in the `feedback` table via [db/feedback.py:55](src/hermes/db/feedback.py#L55). |
| `workflows` | Reserved for the workflows menu (not wired yet). |
| `q` / `quit` / `exit` | Quit. |

---

## What lives where

| Directory | Purpose | Worth reading first |
|---|---|---|
| [src/hermes/cli/](src/hermes/cli/) | CLI entry point (`chat.py`) and slash-command resolver (`commands.py`) | [chat.py](src/hermes/cli/chat.py) — the entire user-facing loop |
| [src/hermes/agents/](src/hermes/agents/) | pydantic-ai `Agent` definitions and their `@tool_plain` methods | [hermes.py](src/hermes/agents/hermes.py) — orchestrator; `bash_agent.py`, `pce_agent.py`, `obsidian_sub_agent.py`, `notion_sub_agent.py`, `morning_briefing.py` are the specialist sub-agents it delegates to |
| [src/hermes/tools/](src/hermes/tools/) | Implementations the agent tools wrap — DB queries, filesystem, Obsidian similarity + memory CRUD, the `gh` shell validator, the Python sandbox, sub-agent spawning | [obsidian_skills.py](src/hermes/tools/obsidian_skills.py) — semantic similarity over markdown frontmatter; [obsidian_memory.py](src/hermes/tools/obsidian_memory.py) — the memory-tier file CRUD |
| [src/hermes/db/](src/hermes/db/) | dlt pipelines (`pipeline.py`), connection helpers, source-specific data classes, and the short-/long-term memory tables under [db/memory/](src/hermes/db/memory/) | [pipeline.py](src/hermes/db/pipeline.py) — the three pipelines + Prefect flow wrappers |
| [src/hermes/mcps/](src/hermes/mcps/) | FastMCP servers exposed to sub-agents as MCP toolsets | [notion_mcp.py](src/hermes/mcps/notion_mcp.py) — currently the only one wired up |
| [src/hermes/evals/](src/hermes/evals/) | Inline eval judge that runs after every response, plus a stubbed baseline-evals harness | [inline_evals.py](src/hermes/evals/inline_evals.py) |
| [src/hermes/system_prompts/](src/hermes/system_prompts/), [src/hermes/instructions/](src/hermes/instructions/) | The actual text fed to each agent. Two-file split: "system prompt" is identity/role, "instructions" is behavior. Each sub-agent that has its own prompts (hermes, bash, pce, obsidian) gets a pair of files here. | Open whichever agent you're touching — they're plain Python returning long strings |
| [src/hermes/docs/active/](src/hermes/docs/active/) | Working design docs the agent reads as context (Postgres decision, workflow brainstorms, recap layouts) | [postgres_portability.md](src/hermes/docs/active/postgres_portability.md), [posgres_transition.md](src/hermes/docs/archived/posgres_transition.md) |
| [src/hermes/sandbox/](src/hermes/sandbox/) | Mount root for the PCE Docker container — source mounted read-only, `output/` writable. Generated charts/CSVs land here. | — |
| [src/docker/](src/docker/) | Dockerfiles for the `python-sandbox` image (PCE) and the pipeline image. | [src/docker/pce/Dockerfile](src/docker/pce/Dockerfile) |
| [src/config/paths.py](src/config/paths.py) | The lone non-env constant: `PROJ_ROOT`. Used by anything that needs a path relative to the repo root. | One line, but get the layering right |

Files outside `src/` worth knowing about: [pyproject.toml](pyproject.toml) lists all runtime deps; the `hermes` CLI entry point is defined by the `hermes` script in `[project.scripts]`.

---

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

**Agent layer.** [hermes.py](src/hermes/agents/hermes.py) is the only agent the user talks to. It has no domain knowledge of its own — every concrete capability is a tool that either reads from the database, calls a sub-agent (each its own pydantic-ai `Agent` with a narrow toolset), or runs a sync helper. Sub-agents are intentionally single-purpose:

- `bash_agent` touches the filesystem with human-in-the-loop confirmation on writes and wraps the narrow `gh` shell tool (see "Bash agent shell access" below).
- `notion_agent` only talks to Notion via the MCP toolset.
- `obsidian_agent` owns vault access — the brain lookup (cosine similarity over `brain/` notes) plus the memory tier (read/write `MEMORY.md` and topic files in `OBSIDIAN_MEMORY_PATH`). See "Obsidian sub-agent" below.
- `morning_briefing` only pulls historical data from the local DB.
- `pce_agent` writes Python and runs it in the locked-down sandbox. See "Python code execution" below.
- `spin_up_sub_agent` is the escape hatch: an ad-hoc agent created at call time with a free-form instruction string, for fan-out research where the orchestrator wants multiple independent passes on the same question.

This is "artificial narrow intelligence" by convention — each agent is too constrained to misbehave outside its lane.

**Data layer.** Source APIs (GitHub, Notion, the local Obsidian vault) are *not* hit on every chat turn. Instead, [db/pipeline.py](src/hermes/db/pipeline.py) runs three dlt sources daily — each writes into its own schema in the local `hermes` Postgres database. Tools like [query_commit_details](src/hermes/tools/query_github_stats.py#L7) and [query_notion_tasks](src/hermes/tools/query_notion_tasks.py#L6) then `pd.read_sql` from that warehouse. This decouples agent latency from upstream API rate limits and lets historical data accrue. The Obsidian embeddings pipeline is different in flavor — it embeds every markdown file's `description:` frontmatter using Qwen3-Embedding-0.6B locally and stores the vectors as JSONB. Semantic similarity at runtime is sklearn cosine over the unpacked vectors (see [obsidian_skills.py:53](src/hermes/tools/obsidian_skills.py#L53)). There is a TODO at [pipeline.py:131](src/hermes/db/pipeline.py#L131) to migrate to native `pgvector` columns once the extension is enabled.

**Why Postgres and not DuckDB / SQLite.** This was DuckDB until recently. The rationale for moving is in [posgres_transition.md](src/hermes/docs/archived/posgres_transition.md) — short version: DuckDB is OLAP (great for ad-hoc analytics, bad at frequent small writes), SQLite serializes writes, Postgres handles concurrent writers with row-level locking. The moment sub-agents fan out in parallel and each logs to short-term memory, the single-writer model breaks.

---

## Bash agent shell access (`run_subprocess`)

The bash sub-agent has a fifth tool beyond the four filesystem helpers: [run_subprocess](src/hermes/agents/bash_agent.py#L144). It is the only place in the codebase that shells out on the agent's behalf, and it is deliberately narrow.

The agent passes a JSON string of the form `{"command": "gh"|"git", "sub_command": "...", "args": {...}}`. The string is parsed and run through [Bash.validate_commands](src/hermes/tools/bash.py#L91) before anything executes. The allowlist ([bash.py:50](src/hermes/tools/bash.py#L50)):

| Command | Sub-command | Allowed flags / values |
|---|---|---|
| `gh` | `issue create` | `--title`, `--body`, `--assignee`, `--repo` |
| `gh` | `issue list` | `--repo`, `--state`, `--limit`, `--assignee` |
| `gh` | `label list` | `--repo` |
| `gh` | `repo list` | repo owner (e.g. `aretecp`) |
| `gh` | `repo view aretecp/<repo>` | any repo in the live `nameWithOwner` list |
| `gh` | `label` | `list` |
| `git` | `log` | `--oneline`, `-S` |
| `git` | `diff` | `HEAD`, `HEAD~1` |

`--repo` values are matched against the live `nameWithOwner` list returned by `gh repo list $GH_ORG` (lazy-fetched once per process at [bash.py:78](src/hermes/tools/bash.py#L78)). Flag values are also scanned for blocked substrings (`&&`, `;`, `|`, `>`, `<`, `` ` ``, `$(`, `../`, `~/`, `secret`, `webhook`, `deploy`, `--delete`, `--admin`, `--token`) with a 1000-char ceiling. A passing payload is rendered in a yellow Rich panel and gated on a `questionary` Yes/No prompt before `subprocess.run(..., shell=False)` fires from `~/Arete`.

Return values are always strings: a validation error, the literal `"Cancelled"` (user declined), or the command's stdout/stderr. The agent reports them verbatim — Hermes' instructions explicitly forbid retrying on `"Cancelled"` or paraphrasing the result. See [bash_agent_system_prompt.py](src/hermes/system_prompts/bash_agent_system_prompt.py) hard-rule 2b for the full envelope.

The takeaway for anyone extending this: adding a new sub-command means adding it to `allowed_sub_commands` in [bash.py:50](src/hermes/tools/bash.py#L50) *and* updating the bash agent's instructions and system prompt so the agent actually knows it exists. Skipping the prompt update leaves the capability invisible to the model.

---

## Python code execution (`pce_agent`)

Hermes does not run Python directly — it delegates to the **PCE sub-agent** ([pce_agent.py](src/hermes/agents/pce_agent.py)) via [call_pce_agent](src/hermes/agents/hermes.py#L163). The sub-agent owns one tool, [run_python_in_sandbox](src/hermes/agents/pce_agent.py#L38), which wraps [execute_python_in_sandbox](src/hermes/tools/pce.py#L38). It writes the code, runs it, reads the error if it fails, and iterates up to three times before reporting back. Use cases: generating plotly charts, ad-hoc pandas/numpy transforms, anything that needs real execution rather than reasoning.

The container is locked down: `--network none`, `--cap-drop ALL`, `--security-opt no-new-privileges`, non-root, 512MB memory, 1 CPU, 128-pid cap, 30s timeout, sandbox source mounted read-only. Only `pandas`, `numpy`, and `plotly` are pre-installed. A pre-flight check in [PCE_Validation.check_code](src/hermes/tools/pce.py#L22) rejects code containing `subprocess`, `__import__`, `pip install`, `socket`, or `shutil.rmtree` before the container even starts.

Any file the code produces must be written to `output/` (e.g. `fig.write_image("output/foo.png")`). That path maps back to the host at `src/hermes/sandbox/output/`, which is also mounted read-write while everything else is read-only. To view the produced file, Hermes delegates a read to `call_bash_agent`.

The Docker image (`python-sandbox`) is built from [src/docker/pce/Dockerfile](src/docker/pce/Dockerfile). If `docker run` fails with "Unable to find image 'python-sandbox:latest'", build it from that directory first. A second image for containerizing the dlt pipelines themselves is planned — separate concern, separate image — but not yet implemented.

---

## Obsidian sub-agent

The obsidian sub-agent ([obsidian_sub_agent.py](src/hermes/agents/obsidian_sub_agent.py)) is Hermes' interface to the vault. It owns six tools and is the only thing that touches `OBSIDIAN_VAULT_PATH` or `OBSIDIAN_MEMORY_PATH` at runtime:

| Tool | What it does |
|---|---|
| `obsidian_brain_lookup` | Embed the user prompt, cosine-similarity-rank against the `obsidian_embeddings` table, return the best-matching note if score ≥ 0.4 — otherwise `"No relevant files"`. ([obsidian_sub_agent.py:42](src/hermes/agents/obsidian_sub_agent.py#L42)) |
| `read_memory_index` | Read `MEMORY.md` — the master index of memory files under `OBSIDIAN_MEMORY_PATH`. |
| `read_memory_file` | Read a specific `.md` file from the MEMORY dir. Path-escape and non-`.md` files are rejected by the `safe_path` layer in [tools/obsidian_memory.py:27](src/hermes/tools/obsidian_memory.py#L27). |
| `write_memory_file` | Create/overwrite a memory file. HITL Yes/No before writing. |
| `insert_into_memory_file` | Insert a single line at a 0-indexed line number inside an existing file. HITL preview before writing. |
| `append_to_memory_index` | Append a one-line `- [Title](file.md) — hook` pointer to `MEMORY.md`. HITL Yes/No. |

The orchestrator calls this agent twice per turn by convention: once at the start of the turn (with the raw user prompt, to run the brain check) and again later if the user reveals a preference or project decision worth remembering. The `memory` keyword at the CLI prompt asks Hermes to run that second pass explicitly against the current session's short-term memory.

Two tiers, one agent: `brain/` is curated long-form context (embedded once by the obsidian pipeline, similarity-searched at runtime); `MEMORY/` is the agent's own writable scratchpad (read by index, written file-by-file). Don't conflate them — they live in different paths and serve different jobs.

---

## How slash commands work

Slash commands are **not** defined in Python. They live in your Obsidian vault.

[cli/commands.py:12](src/hermes/cli/commands.py#L12) reads `OBSIDIAN_COMMANDS_PATH` from `.env` and treats every subdirectory as a command. When you type `/foo bar` at the prompt, the resolver finds the `foo/` directory, reads its `SKILL.md`, and injects that file's contents into the user prompt as command output. The LLM then sees both your `/foo bar` invocation and the skill instructions, and responds accordingly.

**Nested references.** A `SKILL.md` can link to other files in the commands directory using `[[references/handoff.md]]` syntax. The injected prompt includes an instruction telling the agent to use [read_commands_reference_files](src/hermes/agents/hermes.py#L191) (a Hermes tool wrapping [read_command_references](src/hermes/cli/commands.py#L37)) to fetch each referenced file on demand. The tool resolves the path against `OBSIDIAN_COMMANDS_PATH`, rejects path escapes and symlinks, caps file size at 2MB, and returns the contents as text. CSV/XLSX get pandas-read and returned as JSON records.

The implication: to add a new slash command, create a new folder in your commands directory with a `SKILL.md` inside, plus any `references/*.md` files it wants to link to. No code change.

The built-in keywords (`models`, `commands`, `memory`, `feedback`, `workflows`, `exit`) are matched *before* the slash-command resolver and don't take a `/`. See the "Launch the CLI" table above for what each one does.

---

## Models

Every agent constructs its model the same way — `OpenAIChatModel` pointed at the Ollama Cloud endpoint (`https://ollama.com/v1`) authenticated by `OLLAMA_API_KEY`. The factory is [agents/helpers.py:7](src/hermes/agents/helpers.py#L7).

The CLI picker ([chat.py:45](src/hermes/cli/chat.py#L45)) offers three options:

- `gpt-oss:120b-cloud` — default. Bound at import time to hermes, notion_sub_agent, morning_briefing, obsidian_agent, and pce_agent (the bigger model helps PCE write correct pandas/plotly code).
- `gemma4:31b-cloud` — smaller, faster. Bound at import time to bash_agent (routing-only, doesn't need the big model).
- `openai-chat:gpt-4.1` — routes through OpenAI directly. Requires `OPENAI_API_KEY` and is wired in `request_model` ([chat.py:119](src/hermes/cli/chat.py#L119)).

Hermes' model is rebound at runtime when you pick from the `models` menu — `chat.py` reassigns `hermes_agent.model`. Sub-agents keep whatever model their module set at import time.

The model on the inline eval judge ([evals/inline_evals.py:12](src/hermes/evals/inline_evals.py#L12)) is independent of your CLI selection — it always uses the default from `generate_ollama_model()`.

---

## Inline evals, memory, and feedback

Three things fire around every assistant response, all written to Postgres:

**Inline evals.** After the stream closes, [chat.py:305](src/hermes/cli/chat.py#L305) calls a judge model to score the response on two axes (`hallucination`, `factualness`, both 0–1). The scores render as colored progress bars in a panel under the response — green ≥0.8, yellow 0.5–0.8, red <0.5, thresholds at [chat.py:53](src/hermes/cli/chat.py#L53). Scores are *not* persisted yet; that lands when the reflective fine-tune loop is built ([reflective_feedback.md](src/hermes/docs/active/reflective_feedback.md)).

**Short-term memory.** Each turn writes a row to the `short_term_memory` table — session UUID, user prompt, response, tool-call names, and the full message-history JSON ([chat.py:298](src/hermes/cli/chat.py#L298)). [ShortTermMemory](src/hermes/db/memory/short_term.py#L21) lives in its own schema so concurrent writes don't fight the warehouse tables. The plan in the file's tail comments: a weekly LLM-judge job reads these rows and distills durable preferences into `MEMORY/` files via the obsidian sub-agent — that's what `long_term.py` is the stub for.

**Feedback.** The `feedback` keyword at the prompt opens a 👍/👎 + freeform reason and writes to the `feedback` table via [Feedback.store_feedback](src/hermes/db/feedback.py#L55). Future work: a Prefect job reviews accumulated feedback and proposes instruction edits — design intent at the top of [db/feedback.py](src/hermes/db/feedback.py).

---

## Running the daily pipelines

There are three pipelines and a Prefect-wrapped flow for each. Today they're all triggered manually:

```bash
uv run python -m hermes.db.pipeline      # runs all three in sequence
```

The `if __name__ == "__main__":` block at the bottom of [pipeline.py](src/hermes/db/pipeline.py) calls each pipeline's `.run()` directly without Prefect. The Prefect `@flow` wrappers (`run_pipeline`, `run_notion_pipeline`, `run_obsidian_pipeline`) exist and have `.serve(...)` calls commented out — they're meant for a future Docker deployment with cron triggers, not for local use.

Schema layout after a full run:

| Schema | Tables | Source |
|---|---|---|
| `github` | `repos`, `commits`, `commit_details`, `issues` | [db/github_stats.py](src/hermes/db/github_stats.py) — GraphQL + REST against `gh_stats.get_*_bulk()` |
| `notion` | `notion_tasks` (plus dlt's child tables for nested properties: `notion_tasks__task_details`, `notion_tasks__task_description`) | [db/notion_stats.py](src/hermes/db/notion_stats.py) — REST against `data_sources/{id}/query` |
| `obsidian_embeddings` | `obsidian_embeddings` | [db/obsidian_embeddings.py](src/hermes/db/obsidian_embeddings.py) — Qwen3-Embedding-0.6B over vault `*.md` frontmatter |

---

## State of things — what works, what's stubbed

Worth knowing what to trust:

| Component | State |
|---|---|
| Hermes CLI loop (streaming) | Working — token-streamed via `run_stream` with a live-updating Rich panel |
| Model selection (`models`) | Working — three models in the picker, including OpenAI direct |
| Slash-command resolution from vault | Working, including nested `[[references/*.md]]` injection via `read_commands_reference_files` |
| `call_bash_agent` tool + HITL writes | Working |
| `gh` / `git` shell allowlist on bash agent | Working — validator + HITL approval, allowlist at [bash.py:50](src/hermes/tools/bash.py#L50) |
| `call_notion_agent` tool via Notion MCP | Working |
| `call_obsidian_agent` — brain lookup + memory CRUD | Working (sklearn cosine, blocking — TODO at [obsidian_sub_agent.py:40](src/hermes/agents/obsidian_sub_agent.py#L40) to async-ify on the pgvector migration) |
| `call_pce_agent` — Python in Docker sandbox | Working — pce_agent writes code and calls the sandbox; locked-down `python-sandbox` image built from [src/docker/pce/Dockerfile](src/docker/pce/Dockerfile) |
| `spin_up_sub_agent` ad-hoc agents | Working |
| Inline evals + progress bars | Working — not persisted yet |
| Short-term memory | Working — writes each turn to the `short_term_memory` table ([db/memory/short_term.py](src/hermes/db/memory/short_term.py)); the `memory` keyword distills into `MEMORY/` files via the obsidian agent |
| Long-term memory consolidation job | Not built — design at the top of [db/memory/long_term.py](src/hermes/db/memory/long_term.py) |
| Feedback (`feedback` keyword) | Working — 👍/👎 + reason persisted to the `feedback` table; the Prefect review-and-rewrite loop is the next step |
| GitHub / Notion / Obsidian dlt pipelines | Working against Postgres |
| `morning_briefing` agent | Tool functions work; system prompt + instructions are still empty strings ([morning_briefing.py:26-27](src/hermes/agents/morning_briefing.py#L26)). Runs but won't behave purposefully until written. |
| `notion_sub_agent` prompts | Same issue as `morning_briefing` — empty strings at [notion_sub_agent.py:32-33](src/hermes/agents/notion_sub_agent.py#L32). |
| HTML "newspaper" morning brief | Not built. Layout sketch in [morning_recap_newspaper_detailed.html](src/hermes/docs/active/morning_recap_newspaper_detailed.html). |
| Resend email tool | Placeholder at [tools/resend.py](src/hermes/tools/resend.py) |
| Workflow execution | Empty file at [tools/workflows.py](src/hermes/tools/workflows.py); design in [workflows_plan.md](src/hermes/docs/active/workflows_plan.md) |
| `workflows` keyword in the CLI | Reserved — the keyword exists in the banner but isn't wired to a handler yet |

---

## Common stumbles

**`Missing field 'credentials' / 'password'` from dlt.** dlt's postgres destination won't fall back to OS-user / peer auth like `psql` does — it requires explicit `username:password` in the URL. The `DB_URL` in `.env` must include them: `postgresql://postgres:postgres@localhost:5432/hermes`, not `postgresql://localhost:5432/hermes`.

**`KeyError: ['Due Date'] not in index`** when running the Notion pipeline. Means one of your Notion tasks has no `Due date` property and the rename + subset chain in [notion_stats.py:71](src/hermes/db/notion_stats.py#L71) blew up. Already patched with `.reindex(...)` which inserts NaN for missing columns. If you see it again, check that all expected properties exist on your Notion database schema.

**Inline evals returning a coroutine error.** If you edit [inline_evals.py](src/hermes/evals/inline_evals.py) while `hermes chat` is running, the running process holds the old import — exit and re-launch. Same applies to any agent or tool change.

**`coroutine` warnings or sync-blocks-loop slowness.** All tools are `async def`, but several call sync helpers underneath (psycopg `pd.read_sql`, sync file I/O). For a single-user CLI you won't notice; for fan-out workloads see the TODOs at [obsidian_sub_agent.py:40](src/hermes/agents/obsidian_sub_agent.py#L40), [morning_briefing.py:40](src/hermes/agents/morning_briefing.py#L40), and [bash_agent.py:41](src/hermes/agents/bash_agent.py#L41).

**Obsidian brain returns nothing.** [obsidian_sub_agent.py:49](src/hermes/agents/obsidian_sub_agent.py#L49) gates on cosine similarity ≥ 0.4 before returning a file. If your vault's frontmatter `description:` fields are sparse or generic, you'll fall under the threshold. Either lower the gate, or improve your markdown descriptions.

**`Permission denied` from memory writes.** The obsidian sub-agent's `write_memory_file`, `insert_into_memory_file`, and `append_to_memory_index` tools all fire a `questionary` Yes/No prompt before touching disk. Declining returns the literal string `"Permission denied"` to the agent — that's a normal user choice, not an error. Hermes is instructed to report it verbatim and stop, not retry.

**`OBSIDIAN_MEMORY_PATH not found`.** The memory tier won't auto-create your `MEMORY/` directory; create it yourself once and drop an empty `MEMORY.md` inside so the first `read_memory_index` call doesn't return an error.
