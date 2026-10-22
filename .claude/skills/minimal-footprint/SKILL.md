---
name: minimal-footprint
description: Prevents repo bloat by gating new code behind a mandatory discovery step, enforcing reuse over reinvention, adherence to the established architecture, and plain-English comments. Use this skill before writing or modifying ANY code in this repo — especially when adding a feature, creating a new file or module, reaching for a new dependency, writing a helper or utility or wrapper, or refactoring. Also use it when asked to "add", "implement", "build", "set up", "fix", or "clean up" anything, even if the request seems small and self-contained.
---

# Minimal Footprint

The default failure mode of an AI coding agent is *addition*: a new file, a new
wrapper, a new abstraction — each locally reasonable, collectively a repo nobody
can navigate.

This happens for a structural reason, not a carelessness reason. Finding existing
code requires grep and glob, which match strings and have no model of what the
code means. Writing new code always succeeds and costs less. Left alone, the
economics point one direction every time — and the industry data shows it:
duplicated blocks are up 81% since 2023 while refactoring has collapsed to a
fifth of its pre-AI rate, and new code increasingly sits isolated instead of
calling into what already exists.

**This skill exists to make discovery mandatory rather than optional.**

---

## 1. The gate

For any non-trivial change, walk these rungs in order. Stop at the first one that
works. Each step down requires justification.

```
1. SEARCH   — does this already exist?
2. REUSE    — call it
3. EXTEND   — add a parameter, branch, or method to the existing owner
4. REFACTOR — reshape the existing code to absorb the new case
5. CREATE   — new file or new abstraction. Last resort.
```

**Operating target: zero unjustified new files per task.** Not zero new files —
zero *unjustified* ones. If you reach rung 5, say so and say why in your response
before writing it. Silence is how bloat gets in.

Skip the gate only for genuinely trivial edits: a typo, a constant, a one-line
fix in a file you're already in.

---

## 2. Searching properly

Discovery is the step most likely to be skipped or done badly, and a weak search
produces a confident "this doesn't exist yet" that is simply wrong. Grep is a
string matcher — it will not find the thing you want unless you guess its name.

So search for the **concept**, not your guess at the name:

- Search 3–4 different vocabularies for the same idea. Looking for retry logic?
  Try `retry`, `backoff`, `attempt`, `tenacity`, `max_tries`.
- Search for the *library* the code would have used, not the function that wraps
  it: `import httpx`, `from tenacity`, `duckdb.connect`.
- Search call sites, not definitions: if three modules do this, one of them
  probably already has the helper.
- Read the directory listing of `lib/`, `utils/`, `helpers/`, `common/` — actually
  read the filenames rather than grepping blind.
- Read `pyproject.toml` before writing any utility. The dependency that solves
  this is often already installed.

If a semantic code-navigation tool is available in this session (Serena, an LSP
plugin (pyright), a code-index MCP), use it instead of grep — symbol-level lookup is what
this step actually wants. Grep is the fallback, not the goal.

Cap this at a few minutes of searching. The point is a real attempt, not an
exhaustive one.

---

## 3. Don't rebuild the wheel

Check in this order before writing an implementation:

1. **Python standard library** — `pathlib`, `itertools`, `functools`, `dataclasses`,
   `collections`, `contextlib`, `datetime`, `json`, `csv`, `subprocess`, `logging`.
2. **Dependencies already in `pyproject.toml`** — if `pydantic`, `httpx`, `polars`,
   `duckdb`, `tenacity` are already there, use them directly.
3. **Existing internal code** — per the search step above.

### No wrapper for the sake of a wrapper

Never write a function or class whose body is one call into a library. A wrapper
earns its place only if it:

- encodes project-specific defaults used in 3+ call sites, or
- adapts an incompatible interface to one the codebase already uses, or
- isolates a genuinely likely-to-change vendor boundary

```python
# NO — this is a rename, not an abstraction
def read_json_file(path):
    return json.loads(Path(path).read_text())

# YES — encodes a real project convention reused everywhere
def load_config(env: str) -> Config:
    raw = json.loads((CONFIG_DIR / f"{env}.json").read_text())
    return Config.model_validate(raw)
```

### Adding a dependency

A new entry in `pyproject.toml` requires stating, in one sentence, what it does
that the stdlib and current deps can't. If you can't write that sentence, don't
add it. Pulling in a package to solve a ten-line problem trades a small win now
for upgrade risk and review surface later.

---

## 4. Edit existing files

**The default action is editing. Creating is the exception.**

Before creating a file, ask:
- Does a module already own this concern? → put it there
- Is this a variation of existing logic? → parameter or branch, not a parallel file
- Am I creating this because the existing file is "getting long"? → not a reason

Legitimate reasons for a new file:
- The architecture prescribes it (a new domain gets its own
  `schemas.py` / `models.py` / `service.py` / `router.py` set)
- It's a genuinely separate normalized entity or bounded concern
- The existing module is a grab-bag of unrelated responsibilities and splitting
  it is *the point of the task*

Never produce:
- `utils2.py`, `helpers_new.py`, `service_v2.py`
- `enhanced_*`, `improved_*`, `*_final`, `*_fixed`
- A file that imports one thing and re-exports it
- A parallel implementation left beside the old one "for safety"

### Clean up your own attempts

When a fix takes several tries, delete the failed attempts. Do not leave
`handler_fix.py` beside `handler_fix2.py` beside the original. This is one of the
most common ways agent-written repos accumulate garbage: nobody decided to
duplicate, attempt three just never removed attempt two.

**Migrations, not accumulation.** When behavior changes, change the code in place
and delete what it replaced. Dead code left behind is bloat with an alibi.

---

## 5. Make new code findable

If you do add reusable code, name and place it so the *next* session can find it.
Retrieval works off filenames and identifiers, so:

- Descriptive, specific names. `geocode_address` beats `process`. `RetryPolicy`
  beats `Helper`.
- Small, focused, well-named modules over one long grab-bag file. A fat
  `utils.py` is effectively invisible to search — anything buried in it will get
  rewritten from scratch later.
- Put shared code where the repo already puts shared code. Don't open a new
  convention.

This is the one case where a *new* file is the anti-bloat move: splitting a
grab-bag module makes its contents discoverable and stops future reinvention.

---

## 6. Follow the established architecture

Read the surrounding structure first, then conform to it.

If the backend is organized as `schemas → models → service → router` with
supporting files, a new feature is:

| Need | Goes in |
|---|---|
| Request/response shape | `schemas.py` |
| Persistence shape | `models.py` |
| Business logic | `service.py` |
| HTTP surface | `router.py` |

Not a new `manager.py`, not a `handlers/` package, not a `core/` layer, not a
`BaseFeatureFactory`. If the logic can be expressed within the existing layers, it
must be.

**Changing the architecture is a proposal, not an action.** If the structure
genuinely can't support what's being asked, say so and explain why before writing
anything. Don't refactor the architecture as a side effect of a feature ticket.

Same for the data stack: dbt models follow the existing staging/intermediate/marts
layering; pipelines follow the existing dlt → dbt → sync shape. Don't invent a
second orchestration pattern next to the one that's there.

---

## 7. Comments in plain English

Comments explain **why**, in the language you'd use talking to a colleague. They
are not specifications.

```python
# NO
# This function implements a retry mechanism utilizing exponential backoff
# with a configurable base delay parameter. The algorithm computes the delay
# as base_delay * (2 ** attempt), applying jitter to mitigate the thundering
# herd problem in distributed systems...

# YES
# The API rate-limits hard, so back off and spread out retries.
```

Rules:
- One or two lines. Needing a paragraph means the code should be restructured or
  the explanation belongs in `docs/`.
- Explain the non-obvious reason. The code already shows *what*.
- Don't narrate: no `# loop over the items`, no `# return the result`.
- No process breadcrumbs: no `# Updated per user request`, no `# Changed from the
  previous approach`, no unverified `# TODO: check this`.
- Prefer a better name over a comment explaining a bad one.

Docstrings: one line, and only for public functions whose name isn't
self-evident. Skip the Args/Returns/Raises block unless the function is genuinely
complex or externally consumed.

---

## 8. Read the docs before starting

`docs/` holds prior plans, brainstorms, and architecture decisions. Check them
before implementing anything non-trivial.

- An existing plan or decision record may already settle this, with reasoning you'd
  otherwise contradict.
- Prior brainstorms record approaches already tried and rejected. Don't re-propose
  them.
- If your work changes a decision recorded there, update that document in place.
  Don't add `plan-v2.md`.

Consistency with a prior decision beats a locally cleverer approach.

---

## 9. Write for the human who reads it next

Code, and the words around a change, are read far more often than written — almost
always by a human in a hurry. Optimize for their comprehension, not for cleverness
or completeness. (§7 covers comments; this is the code itself and the commit/PR
prose.)

### Code: the obvious version wins

Prefer the straightforward implementation a colleague follows on the first read
over the dense or clever one that saves a few lines.

```python
# NO — clever, one-pass, unreadable
users = {u.id: u for u in (User(**r) for r in rows if r.get("active"))}

# YES — boring, obvious, skimmable
users = {}
for row in rows:
    if not row.get("active"):
        continue
    user = User(**row)
    users[user.id] = user
```

- Name the intermediate step instead of nesting three calls in one expression.
- Return early to keep functions flat; an arrow-shaped pyramid of `if`s is harder
  to hold in your head than a series of guards.
- Don't build for callers that don't exist — an unused parameter or a hook "for
  later" is verbosity dressed as flexibility (§1).
- If a reader can't tell what a function does in ten seconds, the code is too
  clever, not the reader too slow.

### Commits and PRs: plain language, outcome first

The reader wants *what changed and why*, fast. Lead with the outcome in words a
non-author understands. No robospeak, no wall of text, no blow-by-blow of the
approaches you discarded getting there.

- **Commits** follow Conventional Commits (`type(scope): summary`); the body
  explains the *why*, not a restatement of the diff.
- **PRs** describe the change as it stands now and open with the outcome and the
  reason. A reviewer should get the point from the first two sentences.

```
# NO
refactor: comprehensively enhance the recipe-deletion subsystem with a
robust, extensible step-removal mechanism leveraging the existing service...

# YES
feat(workflows): let authors delete a step from the Recipe view

The Recipe view had no way to remove a step once added — authors had to
rebuild the recipe. Wires a delete control to the existing step service.
```

---

## Pre-flight

Before writing code:

- [ ] Read the relevant `docs/` entries for prior decisions
- [ ] Ran the search step with several vocabularies, not one guess
- [ ] Checked stdlib and `pyproject.toml`
- [ ] Landed as high on the gate as possible (reuse > extend > refactor > create)
- [ ] Any new file is prescribed by the architecture, not by convenience
- [ ] No new abstraction layer, wrapper, or pattern introduced

Before finishing:

- [ ] Failed attempts and superseded code deleted, not left beside the new code
- [ ] Nothing added that duplicates a block already in the repo — if a duplication
      checker (`jscpd`) is available, run it on what you touched
- [ ] Comments are short, plain, and explain *why*
- [ ] Code reads plainly for a human; the commit/PR message leads with the
      outcome in plain language, not robospeak
- [ ] Stated explicitly in the response: any new file, new dependency, or new
      pattern introduced, and why the rung above it didn't work

If a checklist item can't be satisfied, say so rather than quietly taking the
expansive path.
