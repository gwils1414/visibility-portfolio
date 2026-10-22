---
name: essential-changes-only
description: Use when asked to "clean up", "fix", "tidy", or "refactor" code that already exists and mostly works. Also use when a diff is growing past the specific defect that prompted it, when replacing a construct the existing code uses at every call site, or when tempted to drop a dependency, delete an uncalled function, add a helper, or change a return shape nobody asked about. Symptoms: "while I'm in here", "the docs show a cleaner way", "this works but it's awkward".
---

# Essential Changes Only

"Clean this up" is a bug-fix request. It is not a rewrite license.

The failure mode: asked to clean up a 100-line file with four broken statements
in it, an agent returns a rewritten file. The four bugs are fixed — and so are
six things that were never broken. The user now has to review a rewrite to find
out whether their working code survived. They will discard the whole thing, and
they are right to.

## Classify before you edit

Every candidate change lands in one of two buckets:

1. **Broken** — you can name the failure. The exception it raises. The wrong
   value it returns. The statement the database rejects.
2. **Not to your taste** — it runs. You would have written it differently.

Bucket 1 is the diff. Bucket 2 is one line of prose in your response, at the end,
and nothing more.

**The test for bucket 1 is whether you can write the failure down concretely.**
"`con` returns `None` on the second access, so the next call raises
`AttributeError: 'NoneType' has no attribute 'execute'`" is bucket 1. "This
should really return a flat dict" is bucket 2. If you cannot name the failure,
it is bucket 2 — no matter how confident you feel.

| Tempting change | Bucket | Why |
|---|---|---|
| pandas `DataFrame` used for a one-row result | 2 | Works. Costs nothing you were asked about. |
| A method with no callers | 2 | Mention it. Deleting it is a separate decision. |
| Return shape that's awkward for the caller | 2 | Awkward is not broken. |
| A helper that centralizes fragile escaping | 2 | New surface area during a fix. Propose it. |
| Dropping a now-unused import | 2 | You orphaned it with an out-of-scope change. Revert that instead. |
| Moving idempotent setup into the constructor | 2 | That's an architecture change wearing a cleanup costume. |
| A statement the engine rejects outright | 1 | Fix it. |
| A `return` inside the wrong block | 1 | Fix it. |

## The existing pattern is a constraint

When the code uses the same construct at **every** call site, that construct is a
requirement until the user says otherwise. Fix how it is used. Do not route
around it.

Documentation that appears to offer a simpler path is often describing a
different thing. The user's pattern encodes their actual deployment; the docs
describe the general case. If the simpler path really is better, say so in one
sentence and let them decide.

## Worked example: the quack wrapper

Three methods each wrapped their SQL in `FROM home_db.query("...")`, and all
three statements were malformed. The quack docs show that an attached remote's
tables can be referenced directly — `home_db.main.my_table` — so the rewrite
dropped `query()` from all three.

That was wrong. `catalog.query()` is `quack_query_by_name`, which runs the
statement **in the server's session** — the only place the mart is actually
visible. `home_db.main.my_table` resolves through the *client's* catalog view,
which is a different namespace. The wrapper was load-bearing for a reason not
visible in the file.

The essential diff was four things, all of which would raise:

- `return self._con` sat inside the `if self._con is None:` block, so every
  access after the first returned `None`.
- The inner SQL was double-quoted. In DuckDB `"..."` is an *identifier*, so the
  server received a column reference instead of a statement. `'...'` for all three.
- The DDL's `"` landed after `varchar` instead of the column list's closing paren
  — no `)` for `create table (` and no close for `query(`.
- `VALUES ({a}), ({b}))` was two single-column rows against a two-column table,
  one paren too many, values unquoted so they read as identifiers.

Everything else — pandas, `to_dict()`, the uncalled `create_schema`, the `as dcm`
alias, the comments — stayed exactly as written.

## Flag changes you had to make

Sometimes a fix requires touching something adjacent. `insert or replace` needs a
key to replace on, so making that statement legal meant adding `primary key` to
the DDL. That is bucket 1 by necessity, but it changes the schema — so it gets
called out explicitly in the response, framed as rejectable, not buried in the
diff.

## Red flags — stop and re-classify

- "While I'm in here..."
- "The docs show a cleaner way"
- "This works, but it's awkward / not idiomatic / a bit odd"
- Deleting an import, or a function with no callers
- Replacing a construct that appears at every call site
- Adding a helper, wrapper, or method during a cleanup task
- A changed line you cannot tie to a named failure

## Rationalizations

| Excuse | Reality |
|---|---|
| "They said clean up, which is broader than fix" | "Clean up" means make the broken parts work. Everything else is a proposal, not an action. |
| "The docs show a simpler path" | The docs describe the general case. Their pattern encodes their setup. One sentence in chat, then move on. |
| "Nothing calls this function" | Then nothing breaks by leaving it. Say so in chat. |
| "I'm just removing the import I orphaned" | You orphaned it with an out-of-scope change. The orphaning was the mistake. |
| "This centralizes a real correctness risk" | Correct, and still additive. Propose it and let them say yes. |
| "It's strictly better this way" | Probably true and entirely beside the point. A rewrite they have to audit is worse than four lines they can read. |
| "I'll just modernize this one idiom" | Every changed line is a line they have to verify. Spend that budget on the bugs. |

## Reporting

Lead with the count: "four edits, all of them things that would raise at
runtime." Then one bullet per fix naming the failure it prevents. Out-of-scope
observations go last, one line each, as observations — not as work you did.
