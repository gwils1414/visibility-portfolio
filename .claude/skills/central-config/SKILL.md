---
name: central-config
description: Use before creating, editing, or deleting anything under .claude/ — a skill, a hook, settings.json, or BASE_INSTRUCTIONS.md. These files are synced from gwils1414/claude-config and local edits are overwritten. Names where the change actually belongs and the two exceptions that stay local.
---

# Where .claude changes belong

`.claude/` in this repo is a **copy**. A scheduled workflow rsyncs
`gwils1414/claude-config` over it and opens a PR with the diff. A skill you edit
here looks fine until the next sync silently reverts it.

So: change it in `claude-config`, not in the working repo.

## Two exceptions — these stay local

| File | Why |
|---|---|
| `.claude/agent_instructions/PROJECT_INSTRUCTIONS.md` | Per-repo by definition. Excluded from the sync. |
| `.claude/settings.local.json` | Machine-local. Excluded from the sync. |

Everything else under `.claude/` — `skills/`, `hooks/`, `settings.json`,
`agent_instructions/BASE_INSTRUCTIONS.md`, the `*-reference/` directories — is
central.

The vendored doc dumps (`duckdb-docs`, `dbt-docs`, `motherduck-docs`) are in
neither: local, untracked, and not synced. Leave them alone.

## Making the change

Work in a clone of `claude-config`, commit, push. Then either wait for the daily
sync or dispatch it (`gh workflow run sync-claude-config.yml`) and merge the PR
it opens.

If the repo isn't cloned locally:

```bash
git clone git@github.com-personal:gwils1414/claude-config.git
```

The `github.com-personal` host alias is required — plain `git@github.com` picks
the wrong key.

## When a skill is genuinely repo-specific

Rare, and worth pushing back on before accepting it. A skill that names this
repo's tables, services, or file paths still goes in `claude-config` — the
description line is what decides whether it fires, so an irrelevant skill in
another repo costs nothing. A skill that only works here, left here, is
invisible to every other repo and drifts out of date.

If it truly cannot be central, say so explicitly in chat and get agreement
before writing it locally.
