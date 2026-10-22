# Handover Doc

Maintains a living handover doc for this repo — what a new developer or client would need to pick it up cold. **Update it as work happens** — don't wait until delivery. When something new is decided, built, or changed, add it to the doc in the same conversation.

## When to update (proactively — no explicit ask needed)

- A new pipeline stage, script, or model is introduced
- An env var or config value is defined or changed
- A build or architecture decision is made (tool choice, incremental strategy, naming convention)
- A known issue or limitation is discovered
- Data flow or architecture is described or clarified in conversation
- A section of work is completed

If any of the above happens and the doc exists — update it. Don't wait for "update the handover doc."

---

## What it produces

Primary output: `HANDOVER.md` at the project root — the source of truth, kept in git.

Secondary output: `HANDOVER.docx`, generated from the markdown when a client or non-technical recipient needs a document rather than a repo file. Regenerate it from `HANDOVER.md` any time the markdown changes and a docx is needed; don't hand-maintain the two separately.

**Document structure** — adapt sections to what actually exists in the repo; skip what doesn't apply, add sections for anything that doesn't fit:

```
[Title — "<Repo/Project Name> — Handover Doc"]

1. What this repo is
   - Scope, and any unrelated sub-tracks living in the same repo

2. Running it
   - Entry-point commands, where the "real" build tool lives if not the repo root
   - What's untested / stubbed / a known placeholder

3. Architecture
   - Data/pipeline flow, one section per stage
   - Anything two components silently depend on (ordering, connection handling,
     locking) that would break if "cleaned up" without knowing why it's there

4. Deployment
   - Where it runs, how it gets there, what's regenerated vs. hand-edited
   - Constraints imposed by the deploy mechanism itself (mirroring, secrets handling)

5. Observability / Operations
   - What's actually wired up vs. what looks wired up but isn't
   - Where logs/metrics/run history actually land

6. Things that look like tech debt but aren't
   - Deliberate stubs, intentional rollback paths, load-bearing pins or overrides
   - Each with a one-line reason and a pointer to fuller rationale if one exists

7. Where to look for more
   - Design docs, decision logs, vendored reference material

8. Documentation gaps
   - Table: Area | Status ("Not documented" / "Partial — what exists")
```

---

## Incremental update mode (default behavior)

When new information arrives mid-engagement:

1. Check if `HANDOVER.md` exists at the project root.
2. **If found:** edit the relevant section in place per this project's global preference — append/supplement rather than replace unless the existing content is now factually wrong.
3. **If not found:** generate it from scratch with everything known so far; mark unknowns as `TBD` rather than guessing.
4. If `HANDOVER.docx` exists and is meant to stay in sync, regenerate it from the updated markdown (see below). If it isn't currently needed by anyone, it's fine to let it lag until it's asked for — the markdown is the source of truth.

---

## Generating the docx

There's no `docx` npm package or system `pandoc` assumed to be preinstalled — check first (`which pandoc`, `node -e "require('docx')"`). Use whichever is actually available, in this order of preference:

1. **`pandoc HANDOVER.md -o HANDOVER.docx`** — if installed, this is the simplest correct path and needs no styling code. Prefer it.
2. **Python, via a throwaway `uv` run** (no dependency added to `pyproject.toml`, since docx export is tooling, not application code): `uv run --with python-docx python3 <script>` reading `HANDOVER.md` and writing headings/paragraphs/tables with `python-docx`.
3. **Node, via `docx`**, only if the environment already has it available — same idea, `require('docx')`.

Whichever path is used, keep the styling minimal (default template, no custom color scheme) unless the client engagement specifically calls for branded output — this skill produces internal/technical handover material, not a marketing deliverable.

**Verify after generating:** convert back to text/PDF and skim it if a converter is available (e.g. `libreoffice --headless --convert-to pdf`), otherwise at minimum open the file and confirm headings/tables rendered before considering the doc done.

---

## Notes

- Voice: written for the recipient to read without the person who built it in the room. Plain, direct, no internal shorthand that only makes sense to the people who were in the room for the decision.
- Cite code with line-anchored relative links (`path/file.py#L42`) so a reader can jump straight to source, matching this repo's existing docs convention.
- This is a living doc — resist the urge to write it once at the end of an engagement. The whole point is that it stays current with zero extra ceremony.
