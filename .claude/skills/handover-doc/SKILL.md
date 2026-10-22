---
name: client-handover-doc
description: "Maintain a living handover doc for the Lumist Labs repo. Update automatically when new decisions, files, env vars, or architecture changes come up. Also triggers on: handover doc, delivery doc, client handover, end of engagement, what have we built, document this."
---

# Client Handover Doc — Lumist Labs

Maintains a living `.docx` handover package for the Lumist Labs engagement. **Update it as work happens** — don't wait until delivery. When something new is decided, built, or changed, add it to the doc in the same conversation.

## When to update (proactively — no explicit ask needed)

- A new file, script, or asset pipeline is introduced
- An env var or config value is defined or changed
- A build decision is made (tool choice, format, naming convention)
- A known issue or limitation is discovered
- Architecture or data flow is described or clarified
- A section of work is completed (e.g., "finished the SVG export pipeline")

If any of the above happens in the conversation and the doc exists — update it. Don't wait for "update the handover doc."

---

## What it produces

Output: `lumist-labs-handover.docx` in `/mnt/user-data/outputs/`

**Document structure:**

```
[Title block — "Lumist Labs — Client Handover Package"]
[Repo / delivery access line]

1. Project Overview
   - What was built, brief scope summary

2. Asset Pipeline & Build System
   - Tools and scripts used (Python, Playwright, Inkscape, etc.)
   - How assets are generated (SVG pipeline, export process)
   - File naming conventions
   - Output formats and counts

3. Deliverable Assets
   - What's included (logos, marks, variants, formats)
   - Asset inventory table (Asset | Format | Count | Notes)

4. Environment & Dependencies
   - Runtime requirements
   - Env vars table (Variable | Description) if applicable
   - Install / run instructions

5. Support Documentation
   - Architecture or process docs
   - Known issues / limitations
   - Documentation Gaps table (Area | Status)
```

Adapt sections to what exists. Skip what doesn't apply. Add sections for anything that doesn't fit the above (e.g., a color system, a font licensing note, a CI/CD workflow).

---

## Incremental update mode (default behavior)

When new information arrives mid-engagement:

1. Check if `lumist-labs-handover.docx` exists in `/mnt/user-data/outputs/`
2. **If found:** unzip → edit `word/document.xml` → rezip (docx skill XML editing pattern). Only touch the relevant section — don't regenerate the whole doc.
3. **If not found:** generate from scratch with everything known so far, even if incomplete. Mark unknowns as `TBD`.
4. Re-verify after every edit (LibreOffice → pdftoppm, read the pages).

---

## Generating / regenerating from scratch

Use the `docx` npm package (`require('docx')` — preinstalled, no install needed).

**docx-js rules:**
- US Letter: `width: 12240, height: 15840` (DXA)
- Table widths: `WidthType.DXA` only — never `PERCENTAGE`
- Table shading: `ShadingType.CLEAR` only
- No `\n` — use separate `Paragraph` elements
- `PageBreak` must be inside a `Paragraph`

**Color palette:**
- Title/header fill: `1F4E79`
- Subhead text: `2E75B6`
- Callout left border: `2E75B6`
- Table header fill: `1F4E79`, text `FFFFFF`
- Alternating rows: `FFFFFF` / `F2F2F2`

**Verify after every build:**

```bash
libreoffice --headless --convert-to pdf --outdir /home/claude /mnt/user-data/outputs/lumist-labs-handover.docx
pdftoppm -jpeg -r 120 /home/claude/lumist-labs-handover.pdf /home/claude/page
# Read each page-N.jpg — check tables, headings, no leftover placeholders
```

Then `present_files(['/mnt/user-data/outputs/lumist-labs-handover.docx'])`.

---

## Env var / config conventions

- Required: plain description
- Optional: prefix `(Optional)`
- Secret: "injected from secrets manager at deploy time"

---

## Documentation gaps

Always include a gaps table. Common ones to check:

- Upgrade / regeneration procedure if source files change
- Font licensing notes
- Color system documentation
- Onboarding instructions for Lumist Labs' own team to run the pipeline

Note each as "Not documented" or "Partial — [what exists]."

---

## Notes

- Client is **Lumist Labs** — avoid Areté internal shorthand in the doc
- SVG-first pipeline with Montserrat converted to outlines — note font dependency in deliverables section
- 115 assets is the baseline count — update if more are added
- The doc is for the client; write as if they're reading it without us in the room
