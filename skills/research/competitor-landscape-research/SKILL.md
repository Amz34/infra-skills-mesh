---
name: competitor-landscape-research
description: Use when mapping a category's competitors and prices.
version: 1.0.0
author: hermes-curator
license: CC-BY-4.0
metadata:
  hermes:
    tags: [research, competitors, pricing, market, positioning, grounded-citations]
    category: research
    related_skills: [grounded-citations, client-prospecting, sme-growth-advisory, tech-adoption-analysis, competitor-news-monitor, competitor-seo-analysis]
---

# Competitor Landscape Research

One-shot map of a product category: who sells it, in what shape, at what public
price, under which standard — turned into a positioned, sourced deliverable the
user can act on (pitch, price, or kill the idea). Worked example: camera/video
fire & smoke detection for Fire & Smoke Watch, Sep 2026 (the fire/smoke case is
written up as the fire-smoke-market-landscape reference inside the
`camera-vision-alert-consoles` skill).

## When to Use

- "Iske competitors kaun hain, links ke saath nikaalo" / "who else does this"
- Before pricing a build, or before pitching a client a category that already has
  vendors (pairs with the tool-eval honesty rule: value, free alternative, cost).
- Before naming a product (brand-collision check is part of this research).
- **"Competitors ka sentiment analysis kare the na?"** — a landscape pass does NOT
  cover this. Vendors, prices and standards are not sentiment; the honest answer is
  "landscape done, sentiment not done" and then run the sentiment layer (below). Do
  not dress a price table up as customer sentiment — the user will notice.

Not this skill:
- Watching named companies over time → `competitor-news-monitor`
- SEO/keyword gap vs a competitor site → `competitor-seo-analysis`
- Finding buyers/leads → `client-prospecting`, `event-lead-generation`

## Method (4 phases)

**1. Scope + segment before searching.** Decide the product class and split it into
5–6 buckets. The buckets that actually decide the answer, and are easy to miss:
- certified/enterprise vendors (the "real" competitors)
- OEM/hardware makers whose recognition is embedded in the hardware
- software-only layers that plug into cameras the client already owns (closest analogue to a software build)
- hardware + human monitored service (reveals the true upper price)
- sensor/adjacent modality (thermal, gas, ground sensors) — competes for the same budget
- **free/open-source floor** — what a motivated buyer gets for $0 (datasets, public
  model repos, NVR platforms). Mandatory: it caps what you can charge.

**2. Breadth: batch searches, 6–8 queries per round, 2–3 rounds.** Mix: product
category + "commercial product", named leaders, "market key players report",
open-source/GitHub, price/cost, and the regional angle (e.g. KSA/Gulf) separately —
regional players rarely surface in English category searches.

**3. Depth: extract the official pages, not the listicles.** 5 URLs per `web_extract`
call, in parallel batches. Prioritise: vendor product pages, standards bodies (NFPA /
SFPE / EN / BIS), procurement records, and one build-vs-buy engineering article.

**4. Synthesise with citations.** Register every URL in the `grounded-citations`
ledger **before** drafting, cite per sentence, mark your own judgement `[unverified]`,
then `sources.py verify <draft>` before delivering.

## Sentiment layer — what buyers praise and punish (separate pass)

A landscape answers *who sells, at what price, under which standard*. It does not
answer *how the category feels*: what makes buyers pick a vendor, what makes them
churn, what they complain about after the demo. When the user asks "sentiment
kya hai, aur humein kya change karna hoga", run this as its own pass.

**Query shapes that actually surface sentiment** (6–10, mixed, dedupe by URL):
`"<category> reviews complaints"` · `site:reddit.com <category> false alarm /
worth it / experience` · `site:g2.com <vendor> reviews` · `"<vendor>" review
complaints` · `"<category>" operator alert fatigue / trust` · `<metric> false
alarm rate study` · `<vendor> lock-in / pricing complaint`.

**Where sentiment actually lives, in priority order** (full ladder + worked
numbers in `references/customer-sentiment-sourcing.md`):
1. Review aggregators that synthesise G2 / Capterra / Trustpilot / app-store /
   forums *with per-source quotes and review counts* — highest sentiment density
   per fetch, and they state n so you can weight it.
2. Vendor/consultancy engineering blogs for the **operator economics** (alert
   fatigue thresholds, false-alarms-per-camera-per-day cliffs, cost models).
3. Product pages on G2/Capterra for split ratings (ease-of-use vs cost vs support)
   — the grievance is usually in one sub-score, not the average.
4. Forum threads. **When a forum host is walled from the datacenter IP** (login
   interstitial instead of content), treat it as snippet-only: quote the search
   snippet for exactly what it says, label it *snippet-level*, and take the
   load-bearing numbers from 1–3. Never present a snippet as a read page.

**Rating distortion is a finding, not noise.** Record n and the invitation
channel: 5.0★ from 12 vendor-invited reviewers is marketing; 2.0★ from 263
independent reviewers is a buyer-experience signal. Report both numbers together —
a single star rating with no n is not evidence.

**Deliverable shape — sentiment that produces requirements, not adjectives:**
- Praise themes (ranked, with what it implies for us) and **punish themes in
  damage order** — the thing that loses deals first, not the loudest complaint.
- A "required system changes" table, one row per gap: `gap | change | effort |
  status`, where status is `HAVE / PARTIAL / BUILD` judged against the actual
  code and docs (grep the repo before marking anything HAVE — half the items are
  usually already half-built, and claiming otherwise wastes a build cycle).
- A **claim-boundary block**: which marketing lines are now off-limits
  (certification, compliance, "replaces X"), routed through
  `content-integrity-guardrail` if the copy ships.
- Open questions with an owner-facing "which one do I build first?" at the end.
- File it in the same `~/ops/kb/<topic>/` as the landscape, cross-referenced; chat
  reply = headline themes + the changes table in short form + `MEDIA:` attachment.

## Where the facts that matter actually live

- **Prices are quote-only in this space — look for the public exception.** The best
  public price evidence is government procurement: municipal staff reports, city
  council legistar items, tender awards, transparency portals. A $100k/3-year
  contract line tells you more than any vendor page.
- **Standards pages tell you what claim you may legally make.** Read the standards
  body / certification regime directly (worked example: NFPA 72 recognises video
  detection only under performance-based design; no UL listing exists) instead of
  repeating a vendor's marketing paraphrase.
- **Independent engineering numbers beat vendor accuracy claims** — false-alarm
  rates per camera per day, precision after temporal validation. These are the
  numbers buyers who have already run a demo will ask for.
- **Naming:** check whether the brand you want is taken, and whether the phrase is a
  generic regulated service term. Both were landmines in the worked example.

## Deliverable shape

- File: English, markdown, at `~/ops/kb/<topic>/<slug>-YYYY-MM.md` (kb = source of
  truth; `~/brains/ops` only gets a decision line if a decision follows).
- Sections: segments → vendor table with links → price anchors → standards reality
  → free/open-source floor → naming risk → where-we-fit (gaps + what NOT to claim)
  → gaps in the research → Sources. Template: `templates/landscape-outline.md`.
- Chat reply: Hinglish, short, **with the actual links inline** (the user asked for
  links, not a teaser), headline numbers, 2–4 "what this means for us" bullets, and
  the file attached via `MEDIA:`.
- Always include: the free/cheap alternative, the honest gap ("no regional vendor
  found in this round"), and a next-step offer — never a link dump.

## Pitfalls

- **A source URL with parentheses breaks the rendered Sources block.** Markdown
  inline links end at the first unescaped `)`, so the rendered URL truncates and
  `verify` reports a Sources block that disagrees with the ledger. Seen Sep 2026 with
  a Legistar report: `...ViewReport.ashx?...Title=Staff+Report+Details+(With+Text)`.
  Fix: find a paren-free canonical form of the SAME document
  (`.../LegislationDetail.aspx?ID=…&GUID=…`), confirm it (`curl -sI` → 200 and a
  string you know is in the file), register it as a new id, swap the id in prose,
  re-render with `--replace-in`. The superseded id then appears in the "uncited
  registered source" warning — expected, don't chase it.
- **Citing a page whose extracted text you never actually saw.** When
  `web_extract` / `web_search` come back summarised (a byte count, no body), the
  fetched page is still on disk at `$HERMES_HOME/cache/web/<domain>-<hash>.md`.
  Grep those files for the exact figures and policy wording you plan to cite, and
  draft from that text. If the cache file is gone, re-extract — never write the
  claim from the snippet or from memory.
- **Treating a search description as a read page.** A snippet supports only what it
  literally says; anything load-bearing needs the extracted body.
- **Quoting market size from one report.** Market-size reports disagree wildly
  (worked example: $3.5B→$5.71B vs $1.98B→$4.59B for the same category, same year).
  Cite two with their CAGRs and say which you weight.
- **Scope drift into the user's own product.** The deliverable is evidence, not a
  pitch: keep the "where we fit" section explicitly marked as judgement
  (`[unverified]`), sized against the anchors above.
- **Findings that live only in the chat.** Write the file; chat is the summary.
- Never put real credentials, alert inboxes, or client/vendor personal contact
  details in the report — mask or omit.
- The `grounded-citations` skill is bundled (not editable): if its render/verify
  flow needs a fix, record the workaround here instead of patching that skill.
