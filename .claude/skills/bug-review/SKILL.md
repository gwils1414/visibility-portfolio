---
name: bug-reviewer
description: Trace the blast radius of a code change — find bugs the change could cause *elsewhere* in the codebase, not defects in the diff itself. Use this whenever a diff, PR, branch, or patch is being reviewed, whenever someone asks "will this break anything", "what else touches this", "is this safe to merge", "what's the blast radius", or when a change touches a function signature, return shape, schema, config value, shared model, or anything with callers. Run it alongside a normal line-level code review, not instead of one.
---

# Bug Reviewer

A normal code review reads the diff. This one reads *everything the diff can reach*.

The job: given a change, find the places that will break because of it, and say how to confirm each one. Callers, consumers, downstream models, cached artifacts, tests that pass for the wrong reason.

Do not re-review the diff itself. Style, naming, and local logic errors belong to the line-level reviewer. If a finding lives inside the changed lines, it's out of scope here — unless it's the *reason* something outside breaks.

## Workflow

### 1. Get the change set

```bash
git diff main...HEAD        # or the branch/base the user names
git diff --stat main...HEAD
```

If no diff is available, ask which commits, branch, or files to compare. Don't guess.

### 2. Classify what each hunk actually changed

Blast radius comes from contract changes, not line count. For each hunk, name the contract:

| Contract | Looks like | Reaches |
|---|---|---|
| Signature | param added/removed/reordered, default changed, arg renamed | every caller, including kwargs callers |
| Return shape | new/renamed/removed key, list→dict, scalar→list, now nullable | every unpack, index, `.get()`, model validation |
| Type / schema | column type, model field, dataclass, Pydantic model, table DDL | serializers, downstream models, stored data |
| Semantics | same signature, different meaning — units, timezone, inclusive vs exclusive bound, sort order | callers that look untouched (worst class) |
| Side effects | writes, deletes, network calls, mutation of an argument, ordering of effects | anything relying on the old effect or its absence |
| Errors | raises a new exception, stops raising, changes exception type, swallows | every `except` clause upstream, retry logic |
| Config / constants | env var, default, feature flag, threshold, path | other environments, deploy scripts, other services |
| Shared state | module-level object, singleton, cache, connection pool | concurrent callers, import-order-sensitive code |

A change that alters no contract has near-zero blast radius. Say so and stop — a short honest report beats a padded one.

### 3. Trace outward

For each contract identified, find who depends on it. Two hops: direct callers, then the callers of anything whose own contract shifts as a result.

```bash
rg -n --stats 'symbol_name'                 # direct references
rg -n 'from .*module import|import module'  # importers
rg -n 'symbol_name' --glob '!tests/'        # prod vs test split
git log -S 'symbol_name' --oneline -20      # who touched it and why
```

Beyond grep, check the places static search misses, since these are where the real production surprises live:

- **Dynamic dispatch** — `getattr`, string-keyed registries, `**kwargs` pass-through, plugin/entry-point loading, Django/Celery task names, DI containers.
- **Serialized boundaries** — anything persisted or sent as JSON: API responses, queue messages, cached values, feature flags payloads. Old-format data written before this change will still arrive after it.
- **Data pipelines** — a changed column, type, or grain propagates to every downstream model, mart, dashboard, and export. Look for `ref()`/`source()` graphs, materialized views, incremental models that won't rebuild history, and schema-on-read consumers.
- **Config surfaces** — same key referenced in CI, Docker, Terraform, systemd units, `.env.example`, docs.
- **Contract copies** — the same shape declared in two places (a TS interface mirroring a Python model, an OpenAPI spec, a fixture file) that won't error when they drift.

### 4. Judge each candidate site

For every place found, answer three things before it earns a spot in the report:

1. **Does it actually break?** Read the call site. Many references are unaffected. Skip them silently.
2. **Does it break loudly or quietly?** Loud = exception at import or first call, caught in CI. Quiet = wrong number, missing row, stale cache, silently truncated column. Quiet ranks higher regardless of frequency — a loud break is a delayed deploy, a quiet one is a wrong answer in a client deliverable.
3. **Would existing tests catch it?** Check for a test that exercises that path with real values. A test that mocks the changed function proves nothing and is itself a finding.

Rank: quiet + untested > quiet + tested > loud + untested > loud + tested.

### 5. Report

```markdown
## Blast radius: <change description>

**Contracts changed:** <one line per contract, or "none — local change only">

### Findings

**[HIGH] `path/to/file.py:142` — <one-line symptom>**
<Two sentences: what this site assumes, and what it now receives.>
Check: `<command or specific thing to run/read>`

**[MED] ...**

### Checked and clear
- `path/other.py:88` — passes the arg positionally, unaffected
- 6 test files reference the symbol, all updated in this diff

### Blind spots
<Where static analysis couldn't reach: dynamic dispatch, external consumers, stored data written under the old format. Name them even without proof — the user knows their system.>
```

Severity is about consequence, not effort: HIGH = wrong data or silent failure in production, MED = loud failure or degraded behavior, LOW = only reachable in an edge case or dev-only path.

## Rules that keep this useful

**Cite file:line for every claim.** A finding without a location is a guess. If it can't be located, it goes in Blind spots.

**Report "clear" honestly.** Listing what was checked and found safe is what makes the HIGH findings believable. A reviewer that always finds something gets ignored.

**Never say "consider reviewing X for potential issues."** Either it breaks and there's a reason, or it doesn't. Vague gestures at whole modules are noise.

**Prefer reading to grepping.** Grep finds candidates; only reading the call site decides. Reporting every grep hit is the main failure mode of this kind of review.

**Migration and backfill are findings too.** If the change is correct going forward but leaves rows, cached values, or queued messages written under the old contract, that's a HIGH — it will surface as a data bug long after the PR is forgotten.

## Examples

**Function now returns `None` on miss instead of raising `KeyError`**
Grep the callers. Any wrapped in `try/except KeyError` now fall through to the happy path with `None`, and the resulting `AttributeError` surfaces several frames away from the cause. Quiet, untested → HIGH.

**dbt model gains a column and changes a join to LEFT**
Row count can only grow. Every downstream model with an aggregate, and every incremental model with `on_schema_change` not set to handle it, is affected. Existing rows won't rebuild → backfill finding.

**Default changed from `timeout=30` to `timeout=5`**
Zero call sites change textually. Every caller that relied on the old default and talks to a slow dependency now raises. Grep the callers that *don't* pass `timeout` — those are the affected ones, which is the inverse of the usual search.

**Pydantic field made `Optional`**
Producers are fine; consumers are not. Find every `.field` access and every place the model is dumped into something with a stricter schema — a database column, an API contract, a downstream parser.
