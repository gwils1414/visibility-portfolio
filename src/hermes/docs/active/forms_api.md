# Forms API — MVP brainstorm

*Working name: TBD. Placeholder: **FormBee** (riffing on Signbee's playful naming, and because the product literally pollinates structured data into forms).*

*Status: pre-build. This document is for sharpening the idea, not for committing to it.*

Building off the product designs like resend or tavily.
API as an agent service
---

## The one-line pitch

> The API that turns any form into JSON and any JSON into a filled form. Built for AI agents.

Two endpoints. Stateless. Template-free. Pay per call.

---

## The shape of the product

### Endpoint 1: `POST /inspect`

**Input:** a form file (PDF, image, URL). Optional: a hint about what kind of form it is.

**Output:** a JSON schema describing every field — semantic ID, human-readable label, type, constraints, sensitivity, position on the page, and (if recognized) a template match against a known form.

The agent uses this schema to figure out what data to gather and how to validate it.

### Endpoint 2: `POST /fill`

**Input:** the schema from `/inspect` with field values populated.

**Output:** a filled PDF (URL or base64), plus structured validation results. If something's wrong, the agent gets a typed error it can correct and retry — not a broken PDF.

### What we explicitly do NOT do in V1

- No signing. Hand off to Signbee, DocuSign, or wherever. We are not e-signatures.
- No storage of filled forms beyond a short retention window for debugging. Customers download and store themselves.
- No UI for end users. We are a developer API only.
- No "agent" — we don't run the LLM that figures out what values go in the form. The customer's agent does that. We are the boring plumbing.
- No multi-step workflows, no envelope state, no recipient management. Stateless, idempotent, one call at a time.

The discipline of saying no to all of this is the product. Anvil, PandaDoc, and DocuSign all do too many things. We do one thing.

---

## Why this exists

### The pain it solves

Every team building an agent that has to fill out a form today does one of three things:

1. Hand-roll PDF parsing with PyMuPDF + a vision call to a frontier model, then string-match field labels. Brittle, slow, expensive.
2. Use Apryse / pdfRest, which requires knowing the PDF's internal field names (`f1_06[0]`). Useless when forms aren't tagged.
3. Use Anvil, which requires pre-building a template per form in their dashboard. Defeats the point of an agent that handles arbitrary forms.

The 80% case is "agent gets handed a form it's never seen, has to figure out what to do with it." Nothing on the market handles this cleanly.

### Who hurts most

The buyer profile is concentrated. Five segments where every team is rebuilding this badly in-house right now:

| Segment | Pain | Volume signal |
|---|---|---|
| Tax prep / accounting agents | W-9, W-4, 1099 series, state forms × 50 | Y Combinator has funded ~6 in the last 18 months |
| Healthcare admin agents | Insurance enrollment, intake forms, prior auth | AWS has a reference architecture for this; demand is real |
| Immigration / legal tech | USCIS forms, court filings | High-margin, well-funded buyers |
| HR / onboarding agents | W-4, I-9, state withholding × 50, benefits enrollment | Every HR-tech AI startup hits this |
| Insurance claims | FNOL forms, claim forms by carrier | $1B+ market for claim automation |

---

## Why now

Three changes converged:

1. **Vision models got good enough.** Claude and GPT-5 with vision can identify form fields with bounding boxes reliably enough that schema inference works on messy scans. This was not true 18 months ago.
2. **Agent volume.** The number of AI agents that need to fill out forms went from "demos" to "production workloads" in the last 12 months. Every customer support agent, accounting agent, healthcare agent eventually hits paperwork.
3. **MCP standard.** Every agent framework speaks MCP now. Shipping an MCP server alongside the REST API gets us into Claude / Cursor / Windsurf with one config file.

---

## What's actually defensible

The temptation is to think the API is the product. It isn't. The API is two endpoints any decent engineer could sketch in a weekend.

The moat is the **template cache**.

The first time anyone uploads IRS Form W-9, we burn a vision call and produce the schema. We store the page layout fingerprint and the resulting schema. The second time anyone uploads W-9, it's a layout-hash lookup. Cheap, instant, perfect.

After 6 months and 10K customers, we have schemas for every common US tax form, most state forms, the top 100 insurance company forms, common immigration forms, and so on. **A new entrant has to either re-do all of that work or accept that their unit economics are 50× worse than ours on the long tail.**

The schemas also get *better* with feedback. When a fill operation fails downstream (signature placed wrong, validation rejected by the receiving agency), the customer reports it, we update the schema, every other customer benefits. The corpus compounds.

This is the same shape that made Stripe defensible (the merchant database), Tavily defensible (the agent-tuned web index), and Resend defensible (the deliverability reputation). The product looks like an API; the moat is the data.

---

## V1 scope (90 days, two people)

### Forms to seed the cache (Day 1 corpus)

Pick 30 forms that cover the highest-volume agent use cases. Hand-curate the schemas. These ship "Day 1 quality" from launch.

**Tax (10):**
- IRS Form W-9
- IRS Form W-4
- IRS Form 1099-NEC
- IRS Form 1099-MISC
- IRS Form 1099-K
- IRS Form 1040 (top page only — full filing is a different product)
- IRS Form 8821 (taxpayer information authorization)
- IRS Form 2848 (power of attorney)
- IRS Form W-9 Substitute (common variants)
- IRS Form W-8BEN

**HR / onboarding (8):**
- USCIS Form I-9
- USCIS Form I-94
- California DE-4
- New York IT-2104
- Texas W-4
- Florida (no state withholding — placeholder)
- Massachusetts M-4
- Direct deposit authorization (generic)

**Healthcare (6):**
- HIPAA authorization (generic)
- Common patient intake (one variant)
- Insurance verification (one variant)
- CMS-1500 (insurance claim)
- Medicare enrollment (CMS-40B)
- Prior authorization (generic)

**Immigration (3):**
- USCIS Form N-400 (citizenship)
- USCIS Form I-130 (family petition)
- USCIS Form I-485 (adjustment of status)

**Insurance (3):**
- ACORD 25 (certificate of insurance)
- ACORD 125 (commercial application)
- Auto FNOL (generic)

Why these 30: they're the forms agents will be asked to fill out in the first 6 months. Coverage > breadth. We can add the long tail later via VLM-inferred schemas with lower confidence.

### Technical stack

Keep it boring. No exotic infrastructure.

- **API:** FastAPI on Fly.io or Railway. Postgres for metadata. S3 for form storage and filled PDFs.
- **PDF parsing:** PyMuPDF (fitz) for AcroForm detection. Extracts existing field dictionaries when present.
- **Vision:** Claude Opus 4.7 for the hard cases (untagged PDFs, scans, photos). Cached aggressively — most pages will never hit the model after the first time.
- **Template matching:** layout fingerprint = perceptual hash of rendered page + spatial hash of detected text blocks. Two-stage lookup: exact hash, then nearest-neighbor against the corpus.
- **PDF filling:** PyMuPDF for AcroForm fills, ReportLab for overlaying text on flat PDFs.
- **MCP server:** thin wrapper exposing `inspect_form` and `fill_form` as MCP tools. Ship alongside SDK.
- **SDKs:** Python first, TypeScript second. Auto-generated from OpenAPI spec.
- **Observability:** Logfire from day one. (We already know it; it's purpose-built for agent workloads.)

### What the dev experience looks like

```python
from formbee import FormBee

fb = FormBee(api_key="...")

# Inspect
schema = fb.inspect("https://www.irs.gov/pub/irs-pdf/fw9.pdf")
print(schema.detected_template)  # "IRS Form W-9 (2024-03)"
print([f.id for f in schema.fields])  # ["name", "business_name", "tax_classification", ...]

# Agent does its work, populates values...
for field in schema.fields:
    field.value = agent_decide(field)

# Fill
result = fb.fill(schema)
print(result.pdf_url)  # https://files.formbee.dev/...
```

That's the whole API. Two methods. A junior developer should be able to integrate it in 10 minutes.

### MCP equivalent

```json
{
  "mcpServers": {
    "formbee": {
      "command": "npx",
      "args": ["-y", "@formbee/mcp"],
      "env": { "FORMBEE_API_KEY": "..." }
    }
  }
}
```

Claude / Cursor / any MCP host now has `inspect_form` and `fill_form` tools available. The agent figures out the rest.

### Ship list (90 days)

**Days 1–30:** core engine
- AcroForm inspection working end-to-end
- Vision-based inspection for flat PDFs (single page first)
- Template matching with a corpus of 5 hand-curated forms
- Fill endpoint for AcroForms
- Postgres schema for templates and audit logs
- Basic auth (API keys), basic rate limiting

**Days 31–60:** developer surface
- Python SDK, auto-generated from OpenAPI
- MCP server (Python implementation, distributed via uvx)
- Docs site (Mintlify or Fern)
- `llms.txt` so agents can self-onboard
- Expand corpus to 30 forms
- TypeScript SDK
- Sandbox mode (free, lower quality, no audit retention)

**Days 61–90:** the things that make it real
- Multi-page form support
- Scan/image input handling (rasterize → vision → schema)
- Webhook for async inspection (some scans take 30+ seconds)
- Audit log export to S3 / Datadog / Logfire
- Self-hosted executor (Docker image) for customers who can't send forms to our cloud — this is the hook for the enterprise conversation
- First 10 design-partner customers

---

## Pricing (first pass)

Steal from Tavily and Resend. Flat tiers with generous free, usage-based above.

| Tier | Price | Inspect | Fill | Notes |
|---|---|---|---|---|
| Free | $0 | 100 / month | 100 / month | Sandbox watermark on PDFs |
| Starter | $29 / mo | 2,000 | 2,000 | No watermark, email support |
| Pro | $199 / mo | 25,000 | 25,000 | Slack support, audit retention 90d |
| Enterprise | Custom | Volume | Volume | Self-hosted executor, SSO, SOC 2 |

Overage: $0.05 / inspect, $0.02 / fill above tier limit.

The economics: inspect costs us ~$0.01 (vision call) the first time it sees a form, $0.0001 (DB lookup) every time after. Fill costs us ~$0.0005 (rendering compute). The template cache is what makes the unit economics work. Each tier should be 80%+ margin after the first month of usage.

---

## Go-to-market

### Sequence

1. **Founder-led design partners (Days 0–60).** Find 10 founders building agents in the segments above. Free access in exchange for hands-on feedback. Goal: schema corpus from real workloads, not synthetic.
2. **YC + Product Hunt launch (Day 90).** The "two-endpoint" framing is tweetable. Sharif Shameem's "28 AI tools I wish existed" is the template for the launch tweet: "Here's the API I wish existed for filling out tax forms."
3. **Vertical channel partnerships (Days 90–180).** Tax-prep agent startups can integrate FormBee, then resell their full agent to accountants. We're the boring layer; they're the customer-facing product. Splits.
4. **Direct sales to mid-market (Day 180+).** Once we have logos, sell to HR-tech and healthcare-admin companies directly. This is where the enterprise dollars live.

### Distribution hacks

- **Ship an MCP server before the SDK.** Every Claude / Cursor / Windsurf user has access to it the moment they install. Discoverability via the MCP registry.
- **`llms.txt` from day one.** Agents that search for "how do I fill out a PDF form via API" find our docs first.
- **One-form-a-day Twitter thread.** "Today's form: IRS W-9. Here's the JSON schema we extract." Builds the cache *and* generates SEO content. 30 days of free marketing.
- **Open-source the schema corpus** (not the engine). MIT-licensed JSON files for common forms on GitHub. Drives developer trust and gets us indexed for every form name.

### The Avalara risk

The biggest risk to the API model is that vertical players like Avalara absorb the use case before we get to scale. Their move would be "we file your taxes" — not "we sell you an API to fill out tax forms."

Counter-positioning: **we are the layer underneath vertical players.** When the next Avalara-for-immigration startup launches, they should be building on FormBee, not rebuilding the form-handling primitives. Sell to them, not against them.

---

## Open questions (rank-ordered)

These are the things we don't have answers to yet. In rough priority order:

1. **Schema confidence and the long tail.** The first 30 forms are hand-curated and perfect. Form #31 through #10,000 are VLM-inferred and imperfect. How do we communicate confidence to agents? A `confidence: 0.82` field is necessary but probably not sufficient. Do we ship a "human verification" tier where customers pay extra for human-reviewed schemas?
2. **Liability.** If an agent uses FormBee to fill out a W-9 incorrectly and the IRS rejects it, are we liable? Probably not legally (we're plumbing), but the customer perception matters. Do we need legal review of the ToS in week 1, or week 12?
3. **Government form changes.** The IRS updates forms annually. Some state forms update unpredictably. We need a process — automated detection of form version changes plus a "deprecate old schemas" workflow. Probably starts as manual, becomes automated by month 12.
4. **Multi-form workflows.** A common pattern: "filing taxes for an LLC" might require filling 6 related forms. Do we add a `workflow` endpoint, or stay rigorously one-form-per-call and let the agent orchestrate? Lean toward the second, but the first is a real upsell hook.
5. **Sensitive data handling.** SSNs, medical info, financial data flow through our system. What's the minimum compliance stance for V1? Probably: TLS, encryption at rest, short retention windows (24h max), no logging of field values, self-hosted executor as an enterprise option. SOC 2 Type II by month 9.
6. **Open source the engine?** Vanna 2.0 went open-source-first and it's working. The argument for: faster adoption, developer trust, harder for incumbents to copy. The argument against: gives away the moat (or the appearance of one) and complicates monetization. Lean toward keeping closed for V1, evaluate at month 6.
7. **Build-vs-buy on vision.** Right now we'd use Claude Opus 4.7 for vision. At scale, training our own vision model on the corpus might be cheaper and faster. That's a year-2 question, not a V1 question.

---

## Decision points

Things that need an answer before we start writing code:

- **Cofounder / collaborator?** This is a 2-person, 90-day build. Solo is possible but slower. Areté Intelligence team has the relevant skill mix; question is whether this is a side bet or a real bet.
- **Naming.** FormBee, Bento (forms as bento boxes), Quill, Schema, Render. Need to do trademark/domain checks before committing.
- **Hosted vs. self-hostable from day 1?** Hosted is faster to ship. Self-hostable is what unlocks the enterprise sale. The middle ground: ship hosted, but architect the engine so the executor can be containerized and shipped to customers by month 4 without rework.
- **Should this be an open-source seed (like Resend's open-source React Email) plus a paid hosted service?** Probably yes — the schemas can be open-source, the engine stays closed. Need to think about which artifact is the open-source hook.

---

## What "success" looks like at 6 months

- 50 paying customers, $25K MRR
- 5,000 forms in the template cache, 80% hit rate on inspect calls
- 3 design-partner case studies (one tax, one HR, one healthcare)
- MCP server installed in 1,000+ developer environments
- Hiring conversation: do we hire a third person, or stay tight and bootstrap?

What "failure" looks like at 6 months: less than $5K MRR, fewer than 5 paying customers, and a clear signal that Anvil or the cloud providers have shipped the agent-native version and have better distribution. In that case: open-source the engine, write up the lessons, move on.

---

## Next steps (if we decide to do this)

1. Lock the name and grab the domain. Half a day.
2. Build a static landing page with the API spec. One day. Goal: collect 20 design-partner emails before we write any backend code.
3. Build the inspect endpoint for AcroForm PDFs (the easy case). Two days.
4. Build vision-based inspection. Five days.
5. Build fill. Two days.
6. Hand-curate the 30-form corpus. Five days.
7. Ship to first three design partners. One week.

Three weeks of work to first signal. If at week three we have three teams actively using it and giving feedback, we keep going. If we have crickets, we have an answer.