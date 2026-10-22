# Repo Bloat in AI-Assisted Development

*Reference doc — causes, evidence, and what actually works. Last updated August 2026.*

---

## What this covers

Why codebases built with AI coding agents accumulate duplicated code, orphaned
files, and abandoned abstractions faster than human-written ones — and which
interventions have evidence behind them.

The short version: **this is a structural problem, not a carelessness problem.**
Agents duplicate because finding existing code is expensive and unreliable while
writing new code is cheap and always succeeds. Any fix that doesn't change that
asymmetry is mostly decorative.

---

## The evidence

GitClear's 2026 *Maintainability Gap* study analyzed 623 million code changes from
2023–2026, tracking eight quality signals as AI authorship scaled. Every signal
moved the wrong way.

### Risk signals (rising)

| Signal | 2023 | 2026 YTD | Change |
|---|---|---|---|
| Block duplication (per M changed lines) | 40.3 | 73.0 | **+81%** |
| Within-commit copy/paste | — | — | **+41%** |
| Error-masking constructs | — | — | **+47%** |
| Two-week code churn | — | — | **+15%** |

### Reuse signals (falling)

| Signal | Baseline | 2026 YTD | Change |
|---|---|---|---|
| Cross-file function connectivity (calls per K changed lines) | 343 (2023) | 223 | **−35%** |
| Refactoring line moves | 21% of changed lines (2022) | 3.8% | **−70%** vs 2022 |
| Long-term legacy maintenance (changes touching code >12mo old) | 1.7% (2023) | 0.46% | **−74%** |

### The three numbers that matter most

**Duplication is at a record high and still climbing.** Block duplication —
five or more consecutive repeated meaningful lines — rose every single year of the
window, hitting 73.0 per million changed lines in 2026. Duplicated blocks carry a
propagation tax: changing one copy obligates a developer to locate and evaluate
every sibling, across files and domains they may not know.

**Refactoring has inverted.** In 2022, the last pre-AI year, developers preferred
refactoring over duplicating by about 2:1. By 2026 the preference had flipped to
roughly 1:5 in favor of duplication — copy/paste climbed from 9.4% to 15.7% of
changed lines while moved code fell from 21% to 3.8%. 2024 was the first year on
record where within-commit copy/paste exceeded moved code.

**New code no longer connects to old code.** Function connectivity fell 35% since
2023. GitClear names this directly: new code is increasingly isolated in
self-contained files, which is the structural signature of duplicative reinvention
beating progressive reuse. This is the metric that most closely tracks "the repo is
spreading outward instead of deepening."

Corroborating: Google's 2024 DORA report found increased AI adoption correlating
with a rising defect rate, and prior research links cloned code blocks to somewhere
between 15% and 50% more defects.

### The framing worth remembering

GitClear's own summary of the mechanism: the default AI workflow is incentivized to
deliver atomic code — a happy path, a passing test, a closed ticket — while quietly
taxing the reuse, consolidation, and error-surfacing that determine what a codebase
costs to own in year three. The throughput is real. So is the debt.

---

## Why agents specifically do this

Seven mechanisms, roughly in order of how much they explain.

### 1. Retrieval is lexical, not semantic

**This is the big one.** Claude Code navigates codebases primarily through glob
(find files) and grep (search contents). Both operate on strings. Neither has any
model of the semantic structure of code — grep can't distinguish a variable name
from a function name, or two same-named functions in different files.

The consequence, per Nik Haldimann's analysis: Claude has **no persistent semantic
model of your codebase.** It has on-the-fly understanding of files it has read this
session, and nothing else.

So "does something like this already exist?" is a genuinely hard question requiring
you to guess the name of the thing you're looking for. Writing it fresh always
works. The economics point one direction on every task.

*Corollary:* whatever isn't findable by name effectively doesn't exist. Anything
buried in a long grab-bag module is invisible to retrieval and will be rewritten.

### 2. A generation bias on top of the retrieval problem

Haldimann quantified duplication in a production codebase and found it accumulating
two ways: poor reuse of existing library code, *and* poor extraction of new library
code. He describes this as largely by design — a built-in preference for producing
new code over reusing and consolidating.

Both halves matter. Even with perfect retrieval, an agent that never extracts
shared code leaves duplication in place.

### 3. Editing is riskier than adding, within a single session

A new file cannot break anything. Modifying a shared module might break callers the
agent hasn't read. Given no instruction otherwise, the locally safe move is always
additive — and it's safe *for that task* while being costly for the repo.

### 4. The objective is the closed ticket

Nothing in a typical agent loop rewards consolidation. Tests pass, the ticket
closes, the session ends. Refactoring is invisible work with deferred payoff, which
is exactly the category that gets skipped under throughput pressure. This is
GitClear's central thesis and it's consistent across every signal they track.

### 5. Iterative fix loops leave debris

A documented Claude Code failure mode: during iterative fixing, multiple attempts at
the same problem get placed in different directories without previous attempts being
removed — in the reported case, causing duplicate filenames and build failures.

Nobody decided to duplicate. Attempt three simply never deleted attempt two. This is
one of the most common ways agent-written repos accumulate garbage.

### 6. Session amnesia and compaction

Context doesn't survive between sessions, and compaction drops detail *within* one.
Session two doesn't know what session one built, so it rebuilds it under a slightly
different name in a slightly different place. This compounds mechanism #1: not only
is existing code hard to find, the agent doesn't even know to look.

### 7. Dependency sprawl

Same instinct, different surface. Agents will pull in a third-party package to solve
a small problem that existing utilities or a few lines of plain code would handle —
saving time up front while adding maintenance burden, upgrade risk, and review
scope later.

---

## Failure patterns to watch for

Concrete signatures, useful for review:

- **Parallel implementations** — `service.py` and `service_v2.py` coexisting; the
  old one still imported somewhere
- **Wrapper-only functions** — a helper whose body is one call into a library,
  adding a name and nothing else
- **Attempt debris** — `handler_fix.py`, `handler_fix2.py`, `handler_final.py`
- **Orphaned abstractions** — a base class or factory with exactly one
  implementation, built for extensibility that never arrived
- **Self-contained new files** — a feature that imports nothing from the existing
  codebase (the connectivity metric, at file scale)
- **Naming drift for one concept** — `get_vendor`, `fetch_vendor`, `load_vendor`,
  three implementations, three files
- **Frozen strata** — whole directories untouched for a year while functionality
  gets rebuilt around them
- **Error-masking** — broad `except:` blocks, null-guards, and defensive idioms
  added to make something pass rather than to handle a real case (up 47%)

---

## What works

Ranked by how much of the root cause each addresses.

### Tier 1 — attacks the retrieval problem

**Semantic code navigation.** Serena (in the official Claude Code plugin
marketplace) provides symbol-level retrieval and editing across 30+ languages,
replacing grep-guessing with actual lookup. LSP-based "code intelligence" plugins
exist too, though as of early 2026 practitioner reports describe them as underbaked
and per-language.

**Deterministic duplication detection.** `jscpd` finds clones across many languages
without asking a model to guess. The DRYwall plugin wraps it as an MCP server plus
skill for Claude Code. A deterministic tool beats a prompt for a deterministic
problem — and it's cheaper in tokens.

**A written index of what exists.** Since retrieval works off names, a maintained
per-feature doc recording the *names and locations* of reusable code is a
hand-built substitute for the semantic index the tooling lacks. This is the
`feature-log` skill's core job.

### Tier 2 — good practice, helps regardless

**Small, focused, well-named files.** Claude decides what to load partly from
filenames, so one class or one closely-related group per file beats a long generic
`utils.py`. Explicitly flagged as a problem for Python, whose convention of long
grab-bag modules is now actively harmful. Descriptive names for anything meant to
be reused.

**Conventional locations.** Put shared code where the agent already knows to look —
`lib/`, `utils/`, `helpers/` — rather than inventing placement per feature.

**Narrow task scope.** One task, one concern. Large multi-concern diffs lose
reviewability, and a "quick fix" that expands into a shared-utility change is how
unplanned architecture happens.

**Budget for refactoring and legacy maintenance explicitly.** GitClear's first
recommendation. If consolidation isn't scheduled, it doesn't happen — it's the work
that's always deferrable.

### Tier 3 — necessary but insufficient

**CLAUDE.md instructions.** Worth writing, and they reduce the from-scratch bias
somewhat. But the practitioner who measured this is blunt that in a large codebase,
checking whether similar logic exists is fundamentally hard and token-expensive —
you cannot prompt your way past a retrieval limitation.

Treat instructions as necessary scaffolding, not a solution. They work best when
they specify a *procedure* (search these vocabularies, check these directories,
report any new file) rather than a *value* (avoid duplication).

**The ordered gate.** The most useful instruction pattern found: make discovery a
gate rather than an optional detour.

```
Search → Reuse → Extend → Refactor if required → Create as a last resort
```

With a stated target of **zero unjustified new files per task** — not zero new
files, zero *unjustified* ones, with the justification said out loud.

---

## What doesn't work

- **Assuming the model will notice.** It won't; the incentives run the other way.
- **"Avoid duplication" as a bare instruction.** Too abstract to act on, and it
  doesn't solve the finding problem that causes the duplication.
- **Reviewing volume instead of structure.** Lines shipped says nothing about
  connectivity, duplication, or whether old code is being maintained. GitClear's
  fifth recommendation is explicitly to measure structure, not just volume.
- **Purely mechanical deduplication.** Worth noting even when using the tooling:
  duplication is often a symptom of missing abstraction or a design weakness.
  Extracting the clone doesn't fix the design. Large refactorings are worth
  reviewing as signals about architecture.

---

## Sources

**Primary research**

- GitClear, *The Maintainability Gap: AI Code Quality in 2026* — 623M changes,
  2023–2026, eight signals.
  https://www.gitclear.com/the_ai_code_quality_maintainability_gap
- GitClear, *AI Copilot Code Quality* (Feb 2025) — 211M changed lines, 2020–2024.
  First year copy/paste exceeded moved code.
  https://www.gitclear.com/ai_assistant_code_quality_2025_research
- GitClear, *AI Coding Tools Attract Top Performers* (Jan 2026) — heavy AI users
  out-produce others 4–10x, but ~25% of that is attributable to AI itself.
  https://www.gitclear.com/developer_ai_productivity_analysis_tools_research_2026
- GitClear, live quarterly signal graphs.
  https://www.gitclear.com/industry_stats/ai_code_quality_signal_graphs

**Practitioner analysis**

- Nik Haldimann, *4 ways to combat Claude's code duplication* — glob/grep as the
  root limitation, generation bias, DRYwall.
  https://ngof.nikhaldimann.com/p/4-ways-to-combat-claudes-code-duplication
- *How to Use Prompts to Reduce Redundant Code Generation in Claude Code* —
  discovery-as-gate, the Search→Reuse→Extend→Create ordering.
  https://www.aiqnahub.com/use-prompts-reduce-redundant-code-generation/
- *How to Use AI Coding Agents Without Breaking Your Codebase* — scope creep and
  dependency sprawl.
  https://programminginsider.com/how-to-use-ai-coding-agents-without-breaking-your-codebase/

**Issue reports**

- Claude Code #1342 — duplicate files from iterative fix attempts.
  https://github.com/anthropics/claude-code/issues/1342

**Tooling**

- Serena (semantic retrieval) — available via `/plugin` in Claude Code
- jscpd — https://jscpd.dev/
- DRYwall — https://github.com/nikhaldi/drywall

---

## Related

- `.claude/skills/minimal-footprint/SKILL.md` — the discovery gate and reuse rules
- `.claude/skills/feature-log/SKILL.md` — cross-session index of what exists
