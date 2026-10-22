# CLAUDE.md — example for a consuming repo

Copy this to `CLAUDE.md` at the root of a repo that receives this config, and
rewrite the parenthetical describing `PROJECT_INSTRUCTIONS.md` to match what
that repo actually is.

`CLAUDE.md` stays a pointer. Everything it `@`-references is read in full on
every session, so the split is what keeps the synced half and the per-repo half
from fighting: the fan-out overwrites `BASE_INSTRUCTIONS.md` on every push and
never touches `PROJECT_INSTRUCTIONS.md`.

---

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository. It is a pointer — the rules live in two files, both
read in full on every session.

**Repo-agnostic working rules** (code footprint, docstrings, work logs, commits,
TDD, PRs). Synced from `gwils1414/claude-config`; edit it there, not here:

@.claude/agent_instructions/BASE_INSTRUCTIONS.md

**Rules specific to this repo** (what it is, commands, architecture, deployment,
the things not to tidy up). Edit this one freely:

@.claude/agent_instructions/PROJECT_INSTRUCTIONS.md
```
