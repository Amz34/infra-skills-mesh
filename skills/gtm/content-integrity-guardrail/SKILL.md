---
name: content-integrity-guardrail
description: Use when shipping content claims — enforce proof tags.
version: 1.0.0
author: Aamir Zameer — Hermes
license: MIT
metadata:
  hermes:
    tags: [content, claims, integrity, governance, gate, linkedin, email, proposals]
    related_skills: [linkedin-content-engine, b2b-outreach-email, content-remix-engine, job-application-packs, client-website-delivery]
---

# Content-integrity guardrail (libaas-e-zoor)

## The rule

Nothing we generate may claim what we were **not given**. Basis: Sahih Muslim 2129 (Book 37,
Hadith 191) — *"The one who makes a false statement of that which he has not been given is like
one who wears a garment of falsehood."* Permanent ops rule: `~/brains/ops/rules/content-integrity.md`.

This binds fabricated **metrics, credentials, social proof, testimonials, brand credit, tenure,
size, and approvals**. True-but-unproven claims are allowed — they must be **tagged**, so silence
is never the default.

## When to Use

Any time content is generated that makes a claim — before it ships.

Before ship, on **every** generated artifact:

- LinkedIn/X post, carousel, comment, DM → mode `post`
- cold email / follow-up / proposal / tender answer → mode `proposal`
- CV, profile, bid document → mode `cv`
- client-site or landing copy, case study, one-pager → mode `site`
- report, deck, audit deliverable → mode `text`

## Workflow

1. Write the draft as a file (or pipe it) — never judge claims from memory.
2. Gate it:
   ```bash
   python3 ~/ops/verify/claim_integrity.py post  ~/ops/drafts/linkedin-post.md      # one file
   python3 ~/ops/verify/claim_integrity.py site  ~/clients/avvs-triatek/site         # whole dir
   python3 ~/ops/verify/claim_integrity.py text  -  < draft.md                        # stdin
   ```
   Read every `[HIGH FAIL]` line with its `fix:` hint. `--json` for machine output, `--summary`
   for counts, `--quiet` for exit-code-only, `--rules` for the catalogue.
3. Resolve each HIGH by exactly one of:
   - **evidence** — `[src: <path|url|thread|artifact>]` on a line in the same paragraph;
   - **recorded waiver** — `[claim-ok: <reason>]` (deliberate and reviewable, e.g. a figure
     pending the client's final report);
   - **delete or rewrite** — the honest fallback: drop the number, attribute the party
     ("built with the vendor's team"), or describe qualitatively ("since 2019").
4. Re-run until exit 0. MED findings (`--strict` fails them) are advisory: fix or tag them too.
5. Ship. Exit 2 = could not read the input — that is **not** a pass; fix the path.

## Tag shapes

```markdown
We reduced the client's manual entry from 40 orders/day to 6. [src: ~/clients/sanad/ops-log.csv]
Trusted by 120+ clients. [src: ~/clients/portfolio.md#records]
"Fastest turnaround we've had." — A. Rahman, Ops Manager [src: email thread 2026-08-30]
Our team of 4 ships weekly. [claim-ok: internal headcount, 2026-09]
```
A tag anywhere in the paragraph clears it. `<!-- claim-policy: verified -->` at the top of a
document with a real evidence base downgrades MED/LOW to notes.

## Pitfalls

- **Tag laundering**: a tag must point at a real artifact. Citing a file that does not contain the
  number is worse than no tag — it *is* the garment of falsehood.
- **Borrowed credit with a citation is still borrowed**: `[src: vendor case study]` does not make
  their build ours. Attribute the party in the sentence.
- **Round numbers invented for rhythm** ("300% growth") are the classic catch — replace with the
  real measured figure or a qualitative line.
- **Client names**: only brands on the client record (`knowledge/clients/portfolio.md`). Otherwise
  "an SME in Jeddah".
- **Placeholders** (lorem, TBD, [insert]) must never reach a client deliverable.
- Do not disable the gate or pass `--fail-on none` to ship; that is the exact act the hadith names.

## Verification

```bash
python3 ~/ops/verify/tests/test_claim_integrity.py      # must be 24/24, exit 0
python3 ~/ops/verify/claim_integrity.py <mode> <target> # your artifact: exit 0 required
```

### Calibration lessons (measured 2026-09-15, first live audit)

The gate was first run over our own live properties and produced 185 HIGH findings — mostly
phantom. Fixed before adoption, and the fix is the lesson:

- A **bare adjective is not a claim**: "certified", "testimonial", bare currency. CI-01 needs a
  self-reference or a *named* authority (ISO 9001, cloud partner); CI-03 needs attribution verbs;
  CI-04 needs a percentage/multiple attached to an outcome.
- **Numbers that are not claims**: prices, offer caps ("first 5 clients"), targets/benchmarks,
  templates, and projections. These live in `HYPOTHETICAL_RE` / `OFFER_RE` and are suppressed at
  paragraph level for CI-02/CI-04 only.
- **Strip non-copy before scanning** — HTML tag attributes, inline code, rule tables and numbered
  headings gave hundreds of false positives. `strip_noise()` handles it; keep that in mind before
  blaming the rules on a `.html` target.
- Client sites are mostly **client-supplied copy**: use `--exclude "products*.html"` for imported
  catalogues, and treat a live client-certification badge as a *request for the certificate
  number*, not as noise.
- After calibration: 16 real HIGH findings across 5 properties, all actionable. If a run reports
  dozens of findings on ordinary copy, that is a calibration bug — fix the rule, do not tag around
  it.
The gate also runs daily via `~/ops/verify/checks-selfqa.json` (5 checks) → `daily_selfqa.sh`,
and rows land in `~/ops/observability/verify-ledger.jsonl` under `tool: claim_integrity.py`.

Background: `~/brains/ops/knowledge/governance/content-integrity-gate.md`,
`~/brains/ops/ingestion/2026-09-15-libaas-e-zoor.md`.
