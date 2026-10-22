# Model Routing Spec

Rules the harness uses to pick a model, or spawn a sub-agent, for a given task.
Optimizing for: right-sized cost/latency, quality where it matters, no Opus tax on trivial work.

## Decision axes

Every task is scored on three axes before routing:

- **Difficulty** — `mechanical` | `standard` | `novel` | `deep`
  How much reasoning is needed. Reformatting = mechanical. Implementing from a clear spec = standard. Ambiguous spec, tradeoffs, or unfamiliar domain = novel. Multi-step reasoning under uncertainty = deep.
- **Materiality** — `throwaway` | `internal` | `human-facing` | `irreversible`
  What happens if it's wrong. Scratch computation = throwaway. Intermediate agent step = internal. Text a human reads = human-facing. Sends email, writes to prod, spends money = irreversible.
- **Latency budget** — `interactive` (<5s) | `normal` | `batch`

## Model roster

Organized by tier. Top-down = more capable, more expensive, slower.

| Tier   | Current    | Legacy (still on API)          | Strengths                                                                 |
|--------|------------|--------------------------------|---------------------------------------------------------------------------|
| Fable  | Fable 5    | —                              | Top capability. Reserved for hardest, highest-stakes work.                |
| Opus   | Opus 5     | Opus 4.8, Opus 4.7, Opus 4.6   | Deep reasoning, planning, agentic coding, gnarly debugging.               |
| Sonnet | Sonnet 5   | Sonnet 4.6                     | Balanced workhorse. Code writing, tool use, standard implementation.      |
| Haiku  | Haiku 4.5  | —                              | Fast, cheap. Routing, classification, formatting, short summaries.        |

### Cross-vendor review — Codex CLI

Some work is better judged by a model that did not write it. The Codex CLI is
installed locally and authenticated; a second Anthropic model agreeing with the
first is not a second opinion.

**Model:** whatever `codex doctor` reports as configured (currently
`gpt-5.6-luna`). The local default is `model_reasoning_effort = "low"`, which is
wrong for review — override per call rather than editing the user's config:

```sh
codex exec --sandbox read-only --skip-git-repo-check \
  -c model_reasoning_effort="high" "<prompt>"
```

`codex review --base develop` scopes a review to a diff instead of a prompt. It
takes no `--sandbox` flag — it inherits the sandbox from config and project
trust (this repo is marked `trusted` in `~/.codex/config.toml`, which is not
read-only). When the read-only guarantee matters, use `codex exec` with the
flag instead.

**When it fires.** Two triggers, both tied to axes this document already uses:

| Trigger | What to ask for |
|---|---|
| A change whose **rendered result** differs — a screen, component, layout, interaction, visual system, or a mockup of one | Which option to ship and why; the failure modes; what is missing. Name the audience — this product is for non-engineers, and that changes the answer. |
| Output at `human-facing` materiality — UI copy, PR bodies, user-facing docs, onboarding text, error messages | Whether it says what it means, to that reader. Not a grammar pass. |

**When it does not.** The trigger is user-visible change, not file type. Skip the
call when a change has no semantic, visual or interaction difference for a user
and adds no new human-facing text: test-only edits, internal refactors, CSS that
renders identically, formatting passes, internal engineering docs written for us
(`ARCHITECTURE.md`, `docs/features/` work logs, `research/`), and content already
reviewed and not materially edited since. Substantive edits after a review mean
another review — the point is the shipped thing being seen, not the ritual.

Code, comments, logs and commit messages are **not** human-facing for this rule,
whatever the materiality axis says elsewhere. They are reviewed by the code
review loop. A PR body is, despite being written from the same commits — it is
read by someone who did not make the change.

**It is advisory, and it is additional.** Codex does not approve or block, and it
never stands in for a review another rule requires. Inside an ultracode workflow
`CLAUDE.md` still puts all review on Opus — the Codex pass sits alongside that,
it does not move review off Opus. The stop-hook's `/code-review` and
`/bug-reviewer` loop is likewise untouched: that covers code, this covers what a
person sees. Where Codex disagrees with a decision already made, report the
disagreement to the user rather than silently switching. If it is unavailable or
errors, say so and proceed, unless it was the only review the work was getting
(see `Draft → cross-review`).

Getting a useful answer out of it:

- **Point it at real files.** Name paths and tell it to read them first; a
  description of the code gets a review of the description.
- **Ask it to disagree**, explicitly. Without that it ratifies.
- **Give it what it cannot see** — who the users are, what shipped last week,
  what was already rejected and why.
- **Numbered questions and a word budget.** Open prompts return essays.
- **`--sandbox read-only` by default.** `workspace-write` lets it edit files;
  that is a real grant the user may decline, so take the opinion and make the
  edits yourself unless told otherwise.
- `timeout` is not a macOS builtin — do not wrap the call in it.

### When to pin a legacy version
- **Determinism**: workflow validated on a specific version, don't want silent behavior drift.
- **Fable 5 fallback path**: Opus 4.8 is the auto-fallback target when Fable 5's safety classifier trips (bio/cyber flags). If you route to Fable, expect some traffic to land on 4.8 — keep it in the harness's known set.
- **Cost/behavior fit**: legacy Opus versions price similarly to Opus 5. Pin only if *your* eval favors a specific one; otherwise default to current.
- **Sonnet 4.6**: only if you have an existing prompt/tool-use scaffold tuned to it. Sonnet 5 is the default.

## Task → tier

Pick the tier from this table, then use the current model in that tier unless you have a pinning reason above.

| Task class                          | Tier       | Notes                                                              |
|-------------------------------------|------------|--------------------------------------------------------------------|
| Route / classify / pick a skill     | Haiku      | Force structured output; fail closed to Sonnet on low confidence.  |
| Extract fields from text            | Haiku      | Sonnet only if schema is ambiguous.                                |
| Format / rewrite for a human        | Sonnet     | Haiku if source is clean and ask is short.                         |
| Summarize for a human               | Sonnet     | Haiku for one-liners; Sonnet when nuance matters.                  |
| Write code from a clear spec        | Sonnet     | Default. This is the workhorse path.                               |
| Debug a failing test / trace        | Sonnet     | Escalate to Opus after 2 failed attempts (see below).              |
| Plan a new feature / refactor       | Opus       | Cache the plan; don't re-plan on every turn.                       |
| Architecture / design tradeoffs     | Opus       | Emit written rationale, not just a decision.                       |
| Review an irreversible output       | Opus       | Required gate before any `irreversible` action fires.              |
| Long-horizon agentic coding         | Opus       | Opus 5 is priced for this workload; don't reach for Fable by reflex. |
| Highest-stakes reasoning            | Fable      | Only when Opus has already failed on the task. Expect bio/cyber → Opus 4.8 fallback. |
| Fan-out parallel simple work        | Haiku × N  | Independent, mechanical subtasks only.                             |
| UI / UX design or change            | Opus + Codex | Opus decides, Codex reviews. Mockups count.                        |
| Human-facing copy                   | Sonnet + Codex | Sonnet drafts, Codex reviews. No Opus unless a finding is a design call, or Codex is unavailable. |

## Sub-agent patterns

The harness spawns sub-agents when a task splits cleanly into phases with different needs.

### Plan → execute → format
Default for `novel` + `standard` mix. Opus writes the plan, Sonnet does the work, Haiku or Sonnet shapes the final output.
```
Opus (plan)  →  Sonnet (execute, step-by-step)  →  Haiku (format for human)
```

### Draft → review
For anything `irreversible` at stakes, and the fallback for `human-facing` output
when cross-review is unavailable — human-facing copy is never shipped with no
review pass at all.
```
Sonnet (draft)  →  Opus (review, block or approve)
```

### Draft → cross-review
For UI/UX and for `human-facing` output. The reviewer is a different vendor on
purpose. The builder decides what to take — this adds no Opus call of its own,
and escalates only when a finding is an architecture or design judgement. Codex
being advisory does not make the review optional: if it cannot run, the
`human-facing` draft falls back to the Opus review above.
```
Opus or Sonnet (build)  →  Codex (review, advisory)  →  builder applies
```

### Fan-out
For N independent mechanical subtasks. Parent stays Sonnet; children are Haiku.
```
Sonnet (split)  →  Haiku × N (each subtask)  →  Sonnet (merge)
```

### Debug loop
```
Sonnet (attempt fix) ── fails ──→ Sonnet (retry with more context) ── fails ──→ Opus (root cause)
```

## Escalation rules

Ladder: **Haiku → Sonnet → Opus → Fable**. The harness moves up when signals show the current tier is out of its depth.

- **Retry ceiling**: 2 failed attempts at the same subtask → escalate one tier.
- **Ambiguity signal**: model asks a clarifying question mid-task, or emits low-confidence markers → re-plan at Opus.
- **Materiality gate**: any `irreversible` action requires an Opus review pass, regardless of who drafted it.
- **Novelty flag**: task references a domain or API not seen in the last N turns → start at Sonnet minimum, even if the ask looks mechanical.
- **Fable gate**: never auto-escalate to Fable. Requires either an explicit caller flag or a documented Opus failure on the same task. Fable is a deliberate choice, not a fallback.

Down-shifting also matters: if a task landed at Opus but turned out to be `mechanical` on inspection (e.g. plan was cached), the harness runs execution at Sonnet or Haiku instead of re-invoking Opus.

## Guardrails

- Never route interactive (<5s) turns to Opus or Fable. If either is required, warn the caller and run async.
- **Fable 5 fallback awareness**: if the harness routes to Fable, log the actual responding model — Fable's safety classifier can silently swap to Opus 4.8 for flagged content. Downstream code that assumes Fable-tier output should treat this as a soft failure.
- Cache Opus and Fable outputs (plans, reviews) keyed by input hash. Re-planning is the biggest wasted spend.
- Sub-agents inherit the parent's cost budget and materiality flag. A child can escalate up but never lowers the materiality of its output.
- Codex calls are advisory and never gate an action on their own. Its verdict is
  reported to the user with the disagreement intact, not laundered into agreement.
- Never send Codex anything that must not leave this machine's vendor boundary —
  it is a different provider. Source in this repo is fine; secrets, credentials
  and customer data are not, the same rule as any other tool.
- Structured outputs (JSON, tool calls) → prefer Haiku or Sonnet. Opus or Fable for pure structured output is almost always overkill.

## Defaults

If the harness can't score a task:
- Assume `standard` / `internal` / `normal` → **Sonnet 5**.
- Bail to **Opus 5** only when materiality is confirmed high or difficulty is confirmed novel/deep.
- **Fable 5** is never a default. Requires explicit caller intent.
