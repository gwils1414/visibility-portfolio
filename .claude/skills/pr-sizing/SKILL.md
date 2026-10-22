---
name: pr-sizing
description: Break work into small, independently reviewable issues and ship narrow PRs a human can actually read. Use this before starting any coding task larger than a one-line fix — features, refactors, migrations, bug fixes with unclear scope, or anything phrased as "build X" or "add support for Y". Also use it mid-task when a change is sprawling past its original shape, and when opening a PR or writing up issues. Documentation-heavy changes get a larger line budget; logic changes do not.
---

# PR Sizing

A reviewer approves what they can hold in their head. Past a few hundred lines of logic, review stops being review and becomes skimming with a rubber stamp — which is exactly when a subtle bug ships with three approvals on it.

The job is not "make PRs small." It's **make each PR one idea**, and the small size follows.

## Plan before you write

For any task bigger than a trivial fix, decompose first and show the plan. Do not start coding a five-part change and reveal the shape of it at the end.

The output is a short numbered list. For each piece: what it does, roughly how big, and what it depends on.

```
1. Add `vendor_aliases` table + migration              ~40 lines   no deps
2. Alias lookup function + tests                        ~80 lines   needs 1
3. Wire lookup into the matching pipeline               ~50 lines   needs 2
4. Backfill script for existing vendors                 ~60 lines   needs 1
5. Docs: matching methodology update                    ~300 lines  needs 3
```

Then stop and let the human confirm the split before writing code. A wrong decomposition caught in five lines of plan costs nothing; caught after four PRs it costs a day.

## What makes a good split

**Each piece stands alone.** It merges, the tests pass, nothing is broken. If piece 2 leaves `main` in a state where the pipeline half-uses the new lookup, that's not a split — it's a cliffhanger. Land new code unused first, then flip the caller over in the next PR. That also gives you a one-line revert if it goes wrong.

**Vertical, not horizontal.** Split by capability, not by layer. "Model + query + endpoint for one entity" is reviewable. "All models," then "all queries," then "all endpoints" means nobody can evaluate anything until the last PR, and the first two are unreviewable in isolation.

**Refactor and behavior change never ride together.** This is the single most common cause of an unreviewable diff. Move the code in one PR with zero logic change — reviewer confirms it's a pure move and moves on. Change the behavior in the next, where the diff is now five lines and every one of them is visible. Mixed together, the real change hides inside 400 lines of noise.

**Mechanical changes get their own PR.** Renames, formatter runs, import reordering, dependency bumps, generated code, lockfiles. These are enormous and reviewed by reading the command that produced them, not the diff. Never bury a logic change inside one — that is where bugs go to hide undetected.

**Split on the seam where you'd want to revert.** If part of this ships badly at 2am, what's the smallest thing you'd want to yank? Cut there.

## Size budgets

Count only hand-written logic — application and pipeline code. These are targets, not gates:

| Kind | Target | Stop and reconsider |
|---|---|---|
| Logic (app, pipeline, transforms) | ≤ 200 lines | > 400 |
| Tests for that logic | no limit, within reason | — |
| Documentation, comments, docstrings | ≤ 1000 lines | > 1500 |
| Generated files, lockfiles, fixtures, snapshots | excluded | — |
| Mechanical (rename, format, bump) | excluded, but must be its own PR | — |

Docs run long because prose is linear — a reviewer reads 800 words of a methodology doc far faster than 200 lines of a diff with branching. So a docs PR can be big, but it's still one topic. "Update the vendor matching methodology" is a PR. "Rewrite all client-facing docs" is four.

Same logic for tests: a 400-line test file next to an 80-line function is fine, because tests are read as a list of cases, not as control flow.

## When a PR outgrows its plan

You'll be halfway through piece 3 and discover it needs a refactor to piece 1. Normal. Don't push through — that's how a 60-line PR becomes 500.

Stop, say what you found, and offer the split:

> Wiring the lookup in needs the matcher to take a resolver argument, which touches 6 call sites. That's a separate mechanical PR before this one. Want me to do that first, or keep going and hand you one bigger diff?

Stack the dependent PR on the first rather than merging everything into one branch, when the tooling supports it.

## When not to split

Splitting has a cost — more branches, more review round trips, more chances to leave `main` half-migrated. Keep it together when:

- The change genuinely doesn't work in pieces (a rename that must be atomic across the codebase, a schema change and the code that reads it)
- Splitting would ship broken intermediate states
- It's mostly generated or mechanical anyway, so the real diff is already tiny
- It's a small enough total that the overhead exceeds the benefit

Say which of these applies rather than silently shipping something big.

## Writing the issues

One issue per piece. Each needs a title stating the outcome, two or three lines of context, and acceptance criteria concrete enough that "done" isn't a judgment call. Note dependencies explicitly. Skip effort estimates and templated headings nobody reads.

## Writing the PR

Follow the template here: .claude/skills/pr-template/SKILL.md