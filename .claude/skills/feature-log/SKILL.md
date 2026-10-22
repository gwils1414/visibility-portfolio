---
name: feature-log
description: Maintains one living markdown doc per feature under docs/features/ so work, decisions, and knowledge of what already exists survive across sessions and context compaction. Use this skill at the START of any multi-step or non-trivial coding task (check for an existing log before writing code), whenever resuming work, whenever the user says "continue", "where were we", "pick this back up", or references earlier work, before and after context compaction, and at the END of a work session. Also use it when a decision, tradeoff, dead end, or search-that-came-up-empty is worth remembering. Treat any task spanning more than a couple of files or more than one session as requiring a log.
---

# Feature Log

Context does not survive. Not between sessions, and not always within one —
compaction drops detail mid-task. The next session starts cold, in a repo too
large to re-read, with no memory of what was built, what was tried, or what was
already searched for and not found.

That amnesia is not just an inconvenience, it is a **direct cause of repo bloat.**
Code navigation runs on string matching, so an agent that doesn't remember what
exists will rebuild it — under a slightly different name, in a slightly different
place. This is the mechanism behind duplicated blocks rising 81% since 2023 while
new code increasingly sits isolated from the code around it.

A feature log is the persistent memory the tooling doesn't provide. It is
half journal, half **index of what already exists** — and the index half is what
prevents reinvention.

**One feature, one file, updated in place, forever.** Not a file per session.
Not a dated journal. One document that always reflects current reality.

---

## Before writing any code

1. `ls docs/features/` and look for a log matching this work.
2. If one exists, **read it fully before anything else.** It contains decisions
   you're expected to honor, dead ends you shouldn't repeat, and pointers to code
   you should reuse rather than rebuild.
3. If none exists and the task is non-trivial, create one *before* starting.
   Scaffolding the checklist first is how you get a plan.
4. Skip the log for a one-line fix or a single obvious edit. Not everything needs
   one.

If a log exists and you're about to contradict a decision recorded in it, stop and
raise it with the user rather than silently overriding it.

This step pairs with the search gate in `minimal-footprint`: the log tells you
what exists, then you search for what the log doesn't cover.

---

## Location and naming

```
docs/features/<feature-slug>.md
```

- Lowercase, hyphenated, matching how the team actually refers to the feature:
  `vendor-matching-geocode.md`, `embedding-drift-detection.md`
- One file per *feature or workstream* — not per session, not per PR, not per file
  you touched.
- Never `-v2`, `-new`, `-final`, or a date suffix. If the feature evolved, the
  document evolves with it.
- Genuinely separate sub-projects get their own log plus a link from the parent.
  The next step in the same work goes in the existing log.

---

## Template

Required sections: **Goal**, **Where I left off**, **Checklist**. Include the rest
only when there's something to put in them — drop empty headers rather than
writing "N/A".

```markdown
# <Feature Name>

**Status:** Not started | In progress | Blocked | Done
**Last touched:** YYYY-MM-DD

## Goal
One or two sentences. What this does and why it exists, written so someone with
zero context understands the point.

## Where I left off
The most important section. Current state, the next thing that was about to
happen, and anything half-finished or knowingly broken. Rewrite this every
session — it is a snapshot, not a history.

## Checklist
- [x] Thing that is done
- [ ] Thing that is not
- [ ] ~~Thing that turned out to be unnecessary~~ — why

## Where things live
The index. Every file this feature touches, and — critically — the *name* of any
reusable function, class, model, or config it added, plus where it lives.
Future sessions find code by name; this is what makes that possible.

- `services/geocode.py` — `resolve_address()`, the one entry point. Everything
  geocoding goes through here.
- `schemas/vendor.py` — `VendorMatch`, shared with the matching pipeline.

## Decisions
- **Chose X over Y** — because Z. Revisit if <condition changes>.
- **Not doing W** — conflicts with <existing constraint>.

## Dead ends & search misses
- Tried A, failed because B.
- Looked for existing retry logic under `retry`, `backoff`, `tenacity` — nothing
  in this repo. Wrote our own in `services/http.py`.

## Deferred
Cleanup, consolidation, or migration knowingly postponed — with enough detail
that it can actually be picked up rather than quietly calcifying.

## Open questions
- Things needing a human answer, marked blocking or not.
```

---

## The index sections earn their keep

Three sections do the anti-bloat work. They are the ones most likely to be skipped
and the ones worth the most later.

**Where things live.** Record the *names*. "Added geocoding" is useless next
session; "`resolve_address()` in `services/geocode.py` is the single entry point"
is what stops a second geocoding helper from appearing. Whenever you create
something reusable, register it here in the same turn.

**Search misses.** If you searched several vocabularies and found nothing, write
that down. It's expensive information and it's completely invisible otherwise —
without it the next session repeats the same search, or worse, doesn't search and
duplicates what you built.

**Deferred.** Old code that nobody returns to is how repos calcify; industry-wide,
changes touching year-old code have fallen 74%. A deferred item with a reason and
a location is retrievable. An undocumented one is permanent.

---

## Update discipline

**Update the log in the same turn as the work.** A log written from memory at the
end of a long session is already wrong.

Update it when you:
- complete or abandon a checklist item
- make a decision with a tradeoff
- hit a dead end or an empty search (high value — record it even when it's dull)
- create something reusable, so it lands in the index
- discover a constraint that changes the plan
- stop working, for any reason

**Write before compaction, not after.** If context is getting long or a large
operation is coming, flush current state to the log first. After compaction, the
log is what you re-read to recover — treat it as the checkpoint, not the summary.

Checkbox discipline:
- `[ ]` → `[x]` when done *and verified*, not when the code is written
- Strike through and annotate items that turned out unnecessary — deleting them
  loses the fact that they were considered
- Add items as they surface; the checklist is allowed to grow

**"Where I left off" gets rewritten, not appended.** It's the one section that must
stay short and current. Anything historical belongs in Decisions or Dead ends.

---

## What to write

Write for a future reader with zero context — which is you, next session.

**Do write:**
- Why, not what. The diff shows what changed.
- Names and locations of anything reusable
- Reasoning behind choices, especially ones that look arbitrary
- Constraints discovered the hard way ("the API silently truncates at 100")
- Anything that took more than ten minutes to figure out

**Don't write:**
- A transcript of the session or narration of your process
- Restatements of the code, or pasted implementations
- Praise for the work, progress percentages, or summaries of how much got done
- Anything obvious from reading the file it describes

Plain English throughout, same as code comments. Short sentences. A section
running past a screen is probably narration.

---

## When the feature is done

Set `**Status:** Done` and leave the file. Don't delete it — Decisions, Dead ends,
and Where things live stay useful long after the code ships.

If `docs/features/` gets cluttered with finished logs, move them to
`docs/features/archive/` in one pass. Don't archive continuously.

---

## Staying out of the way

This skill creates documentation, which is exactly the kind of thing that becomes
bloat. Guardrails:

- **One file per feature. Full stop.** A second file for the same work means you're
  doing it wrong.
- No sidecar files — no `<feature>-notes.md`, no `<feature>-plan.md`. It all goes
  in the one log.
- No log for trivial changes.
- Edit a section rather than appending a new one.
- If the log is longer than the code it describes, cut it.

This is the other half of `minimal-footprint`: that skill says search before you
build — this one makes sure there's something worth finding.
