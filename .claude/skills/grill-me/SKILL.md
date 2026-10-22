---
name: grilling
description: Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.
---

Interview the user until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round. Then wait for the user's answers before the next round.

Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.

## Ask through AskUserQuestion, not prose

Put every round through the **AskUserQuestion** tool so the user clicks instead of types. One call per round.

- **Four questions maximum per call.** If the frontier is wider than four, ask the four that unblock the most downstream branches and hold the rest for the next round — do not split one round across two back-to-back calls.
- **Two to four options each.** "Other" is added automatically; never write your own.
- **Your recommendation goes first**, with `(Recommended)` appended to its label. The old prose format put the recommendation under the question; now it leads the option list.
- **`header` is 12 characters max.** It's a chip, not a sentence: "Schema shape", "Rename scope", "Load contract".
- **Every option needs a real `description`.** State the consequence, not a restatement of the label. The tradeoff belongs here — this is where the user actually decides.
- **`preview` for shapes worth seeing side by side**: schema sketches, competing signatures, directory layouts, config snippets. Single-select only. Skip it for preference questions where labels and descriptions already carry the weight.

### multiSelect is a trap — use it deliberately

`multiSelect: true` reads cleanly for "which of these do you want," but it makes *non-selection ambiguous*: you cannot tell "no" from "didn't notice." If you ask "which of these five should we drop" and get one back, you don't know the fate of the other four and you've burned a round finding out.

Use it only when every option is independently additive and an unchecked box unambiguously means "not that one." When the options are really one decision with several parts — especially anything shaped like "which of these do we keep / drop / delete" — make it single-select and write the combinations as options:

- ✅ `Keep A, drop the rest (Recommended)` / `Keep everything` / `Keep A and B`
- ❌ multiSelect over `Drop A`, `Drop B`, `Drop C`, `Drop D`

### Word them like a colleague would

The `reply-like-a-colleague` skill governs question and option text too, not just
chat prose. Question bodies, option labels and descriptions are you talking at
the next desk — plain, direct, no headers, no bolded phrases, no explaining the
user's own codebase back to them. Evidence belongs in the body (below); padding
does not.

### Questions carry their evidence

A question is only as good as what the user knows when they answer it. Put the facts you dug up *in the question body* — row counts, null percentages, distinct values, the file and line where the conflicting thing lives. "Contacts link to accounts only by free-text Company Name (133 distinct values, 30 null / 11%), against 164 accounts" is a question someone can answer. "How should we match contacts to accounts?" is not.

State the tension plainly when there is one, including when it cuts against what the user asked for. If their stated approach fights the codebase, say so in the question body and still offer it as an option — it's their call, and they may know something you don't.

### Between rounds

Answers come back keyed by question text. Read them literally:

- An answer that asks a question back, or picks an option and qualifies it, is not a settled decision. Fold the qualification in and re-ask if it changed the shape.
- A multiSelect answer with fewer selections than you expected is ambiguous. Confirm it as a single-select next round rather than assuming.
- When the user picks something you argued against, that's settled. Note the cost once, in one sentence, and build what they chose.

Between calls, say nothing but what the next round needs. No recaps of what was just decided — the user was there.

## Fallback

If AskUserQuestion isn't available, fall back to numbered prose and wait for a typed reply:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

The four-question cap doesn't apply here — ask the whole frontier.
