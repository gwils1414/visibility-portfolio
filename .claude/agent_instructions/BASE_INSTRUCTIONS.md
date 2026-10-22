# Base instructions

Repo-agnostic working rules. Synced from `gwils1414/claude-config` — edit it
there, not here. Project-specific rules live in `PROJECT_INSTRUCTIONS.md`.

## How we work (best practices)

First and Foremost , always follow the Clanker Constitution. Reference it here.

@/.claude/clanker-constitution/clanker-constitution.md

## Talking to me

Whenever responding to me conversationally, reference the
`reply-like-a-colleague` skill.

Reference '.claude/skills/reply-like-a-colleague/SKILL.md'

## Code footprint

**Before writing or changing any code, follow the `minimal-footprint` skill.**

The short version:
- Surgical edits over rebuilds. Check stdlib → existing deps → existing internal
  code before implementing anything. No wrappers around single library calls.
- Edit existing files. New files need an architectural reason, not convenience.
  Delete what you replace.
- Conform to the established structure. Architecture changes are proposals, not
  side effects of a feature ticket.
- Comments are one or two plain-English lines explaining *why*, not specs.
- Read `docs/` for prior plans and decisions before implementing.

**When the code already exists and mostly works — "clean this up", "fix this",
"tidy this" — follow the `essential-changes-only` skill.** Only changes that fix a
failure you can name go in the diff. Everything else is a one-line observation in
chat, not an edit. Existing patterns used at every call site are constraints, not
suggestions.

Reference '.claude/skills/caveman-code/SKILL.md'
Reference '.claude/skills/essential-changes-only/SKILL.md'

## Managing Complexity:
Reference '.claude/skills/complexity/SKILL.md'

## Design before code

**Before building anything whose shape isn't obvious — a feature, module,
pipeline or service — follow the `strategic-design` skill.**

Spend the extra 20% on design up front. A degraded codebase collects at least
that much on the back end anyway, so the only thing I'm choosing is when to pay
it. Tactical programming is the default rather than a style — it's the path you
take when nobody decides otherwise, and patching around a design problem instead
of fixing it is the move that gets us there.

Three skills, one job each. `grill-me` gets us on the same page; don't propose
architectures until it has. `strategic-design` gets us on the same design: three
candidates, a sub-agent each, every one optimizing a constraint that pulls
against the others. The comparison goes in a file at `docs/design/`, all three
written to the same shape and length so the design is the only thing that
differs, and the pick comes to me through AskUserQuestion with each layout as a
preview. You recommend, you don't decide.
`superpowers:writing-plans` turns what I picked into the spec, carrying the
rejected designs and why they lost.

Skip all of it for a one-line fix or a bug with a named cause. The test is
whether the decision constrains code that doesn't exist yet.

Reference '.claude/skills/strategic-design/SKILL.md'
Reference '.claude/skills/grill-me/SKILL.md'

## Docstrings

**When writing or reworking a function docstring, follow the
`python-function-docstrings` skill.** It hands the actual writing to a Sonnet
subagent, which produces noticeably more natural prose for this than the
planning models do.

- Google style: one-line imperative summary, then `Args:` covering every
  parameter, then `Returns:` unless the annotation is `-> None`.
- Say what a value **means**; never restate its type — the signature is one line
  up. `deps: Run deps; provides the workspace path.` not
  `deps (AreteDeps): The dependencies object.`
- Name the empty case. A function returning `None`/`""` when there is nothing to
  show must say so in `Returns:` — that is the line readers actually need.
- Fragments beat sentences. If it wouldn't sound normal read aloud in standup,
  cut it.
- This **overrides** `minimal-footprint`'s "skip the Args/Returns block" line.
  Here every function gets one.
- A docstring is not the place for long-form rationale. Keep the one-line *why*
  plus its issue number inline and move the essay to `docs/architecture/` —
  `agent-runtime-design-notes.md` is the pattern.


## Work logs

**For any non-trivial or multi-session task, follow the `feature-log` skill.**

- Check `docs/features/` for an existing log and read it before writing code.
- One living doc per feature: `docs/features/<feature-slug>.md`. Update in place,
  never create a v2.
- Keep "Where I left off" current — it's what the next session reads first.
- Record decisions and dead ends. Skip narration and progress summaries.

### Conventional commits
Use [Conventional Commits](https://www.conventionalcommits.org):
`type(scope): summary` where type ∈ `feat|fix|refactor|docs|test|chore|perf|build|ci`.
Use `!` for breaking changes. Body explains the **why**, not the what. Small,
logically-scoped commits; commit after each coherent unit of work. Verify it
builds/tests before committing. Do **not** push unless asked. End commit messages

### Red-green TDD
Write the failing test first (RED), make it pass with the minimal change (GREEN),
then refactor — tests stay green throughout.
- **Security-critical behavior must have a regression test** that would fail on
  the old/buggy behavior (e.g. a dropped tenant filter, a four-eyes bypass, a
  concurrent double-resume). Several real bugs in this repo were found exactly
  this way.
- Offline unit tests use fakes (`FunctionModel`/`TestModel`, fake embedders) — no
  network, no DB. DB-backed behavior goes in `tests/integration/` (marker
  `integration`) and **auto-skips** when the DB/key is absent, so keyless CI stays
  green. Live LLM/embedding tests skip without API keys.
- Never weaken or delete a test to make a change pass; fix the cause.


### Pull Requests

Follow this template @.claude/skills/pr-template/SKILL.md

### No AI attribution
in commits, PR bodies, or issues — no `Co-Authored-By:` trailer, no "Generated
with Claude Code" footer. See the global `commits` skill.
