---
name: sme-growth-advisory
description: "Use when growing an SME/family business's sales pipeline."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [sme, family-business, lead-generation, tenders, gem, competitor-analysis, hvac, india]
---

# SME / Family-Business Growth Advisory

For requests like *"iss sector me kaam kaise laayen"*, *"live tenders list karo"*,
*"competitors ka kya position hai, unse kya seekhein"* — i.e. the user (or a client)
owns a small trade/service business and wants more work. Distinct from
`client-prospecting` (which finds clients for Sanad's AI services).

Live case file: **HMW Engineering Solutions / HMW Air Controls** (Hyderabad HVAC/R) —
see `references/hmw-air-controls-profile.md`. India-first is the standing priority.

## Non-negotiable delivery rules (this user = non-technical owner/beginner)

1. **Hinglish, short sentences, ZERO unexplained jargon.** User has said verbatim:
   *"easy and concise way me explain karo no jargons"*. Every unavoidable term
   (EMD, turnover, CAMC, OEM authorisation) gets a **one-line plain meaning**.
   Better: put the terms in a glossary sheet of the workbook and keep chat clean.
2. **Numbers over adjectives.** Competitor claims must carry a number + source + year.
   Never invent or "round up" market figures, tender values, or deadlines. When a local tool
   answers the money question, keep it on the 7b model and quote the row's tag — a swap to the
   "fast" 3b model once reported a **₹2.56 lakh/month** floor as **₹92 lakh**, so a speed-model
   shortcut is a fabrication risk, not an optimisation.
3. **Always end with 1–3 concrete questions** (which segment first? which 3 clients can
   give a certificate?). Short numeric replies (e.g. a bare "1") are answers to the
   last question asked — interpret them, don't re-ask.
4. **Deliver a file, not just chat.** A workbook the owner can fill in is the artifact;
   chat is only the summary. Spec + generator below.
5. **Start from what they already own.** Existing clients, GSTIN, 10+ years of work =
   the strongest asset. First move for a beginner is almost always *renew/extract from
   existing clients*, not chasing new logos.
6. **"Expertly review karo" = depth with plain words**, not a longer glossary. Tiers,
   numbers, and an explicit "what we copy / where we win" table.
7. **One-liner instructions get acted on, not questioned.** Short directives (*"Add as
   consultation to hmw engineering"*, *"Show the profit in rupees"*, *"Give this tabulated"*)
   are this owner's normal register — pick the obvious default, state the assumption in one line,
   and deliver the artifact. He answers by moving to the next question, so a pending multiple-choice
   clarify just stalls the thread: do the work first and keep the alternative visible as an offer.

## Workflow

1. **Read the owner's own document first** (`read_file` handles PDF/DOCX/XLSX uploads).
   It usually carries the real client list, GSTIN, contacts, and past projects —
   extract these before any web research.
2. **Buyer map by segment** — name actual local buyers (plant names, hospital names,
   hotels, malls, data centres, banks), each with a one-line pitch. Generic categories
   are useless to a beginner.
3. **Live work channels** — government tender portals + keywords + result/award pages
   so expiring AMCs can be pre-empted. Recipes: `references/india-tender-channels.md`.
4. **Competitor map in tiers** (OEMs → big EPC → local rivals → unorganised labour),
   each tier with strength / weakness / lesson / our counter. Data bank:
   `references/india-hvac-competitors-2026.md`.
5. **Eligibility ladder** — state the smallest winnable bid first (₹5–50 lakh AMC range
   for HVAC) and exactly which documents gate the bigger ones.
6. **Build the workbook**, verify by re-opening it, deliver with `MEDIA:<abs path>`.

## Deliverable spec — the "BD tracker" workbook

`scripts/build_bd_tracker.py` generates the skeleton with correct styling/widths/freeze
panes. Sheets that have worked:

| Sheet | Content |
|---|---|
| `START HERE` | 5-step week-one plan, plain words |
| `1. Purane Clients` | existing clients × (kya bechein / kya maangein) |
| `2. Target Buyers` | local names, category-wise + pitch + how to reach |
| `3. Tender Tracker` | portal links, keyword recipes, blank Last date/Value/Status columns |
| `4. Kaagzaat aur Shabd` | ~20 terms with plain meanings + where to obtain |
| `5. 30 Din Ka Plan` | week-wise targets |
| `6. Competitors` | tier × strength × weakness × lesson × our counter |
| `7. Copy Karo (Plan)` | action / who does it / what we do / by when / proof |

## Bids: from a tender link to a submission-ready bid set

When the user pastes a tender link and asks for a draft (*"expertly draft this tender, official
way"*), deliver **three** artifacts, never one:

1. **Technical bid** — submission-ready, pure English, official tone: DOCX master (to fill,
   print, sign) **+** PDF reading copy.
2. **Insider copy** — internal playbook for the family/team: strategy, pre-bid queries, pricing,
   submission mechanics, rejection self-check, dated action plan. Never sent to the buyer.
3. **Cost-model workbook (XLSX)** — the price is built here (Part A monthly build-up, Part B BOQ,
   manpower, PPM matrix, spares, compliance checklist, action plan, margin calculator).

Extraction recipe (index-slicing the cached notice), the 11-section bid skeleton, the playbook
outline, the 9 workbook sheets, GeM mechanics and the single-source DOCX+PDF build pattern are
in `references/gem-tender-bid-drafting.md`. Worked case: INCOIS HVAC CAMC, sources in
`/home/ubuntu/hmw_bid/` (`c1..c3b.py`, `i1..i2.py`, `mk_docx.py`, `mk_pdf.py`, `mk_xlsx*.py`).

## The money answer (investment / profit) — deliver it twice, tabulated

The owner asks this in two waves: first *"simply batao kitna investment aur kitna profit"*, then
*"isko acche tabulated format in English crystal clear format"*. Answer both from the same numbers:

1. **Chat, 6–10 lines, Hinglish** — one rounded headline pair (*"~₹16 lakh invest, ₹2–7 lakh/year
   profit"*), the refundable-vs-at-risk split, and one line on the biggest risk.
2. **Tabulated, in-chat AND as a 1–2 page English PDF** — four blocks in order: *Investment
   required (with a Refundable? column → TOTAL FUNDS TO ARRANGE → less refundable → NET CASH AT
   RISK)* · *Yearly cost vs revenue in Lean / Base / Weak columns* · *Profit at different winning
   prices (descending, ending below break-even)* · *Decision-rules box (floor price, target band,
   "every ₹1 lakh/month = ₹12 lakh over 36 months", return on at-risk capital, extension upside,
   Part B margin, no-escalation risk)*. Full spec + construction rules:
   `references/tender-site-visit-submission-and-roi-summary.md`.

Formatting rules for this platform and this user:

- **Telegram does not render markdown pipe tables.** Put every table in a fenced code block with
  fixed-width aligned columns (monospace renders correctly), and attach the PDF for anything the
  owner will print, forward, or show to family/banks.
- **Numbers in chat and in the PDF must be identical.** Round in chat, never re-derive there.
- **Never ask the owner for the contract tenure** — read it from the tender/corrigendum and show
  the working (per-year, per-month split) so the figure is auditable.
- **Rupees, not percentages, when the owner says so.** Verbatim ask after the first tabulated
  one-pager: *"Show the profit in terms of rupees not percentage"*. Then lead every profit table
  with **absolute rupee columns — profit per year, profit per month, profit over 36 months** — and
  drop the margin-% column entirely (keep a single "~₹0 at break-even" line if the floor needs it).
  Amounts as `2,63,000` (Indian grouping, no symbol clutter inside tables). Same four blocks as
  above; generator `mk_profit_rupees.py` → `HMW_INCOIS_Profit_in_Rupees.pdf` (2 pages). Never show
  a percentage column and a rupee column for the same figure in one table — pick one and be
  consistent between chat and PDF.
- Both deliverables are **English** (chat framing may be Hinglish; all files pure English).

## Selling the bid stack as a paid consultancy

The owner's next question after a big bid pack is nearly always commercial: *can we sell this
high-level bidding help to other firms, how much do we charge, and how do we find those firms?*
Answer all three, tabulated, plus guardrails — and remember **the pack that was just built is the
product proof** (case study #1). Service tiers, market-rate benchmark, cost/margin, Year-1 ramp,
the seven lead channels, the six-step funnel, the 90-day plan and the ethics/conflict rules are in
`references/bid-consultancy-service-line.md` (generator: `mk_consult_offering.py`).
Headline pricing that survived: Tier 1 alerts ₹15,000/yr · Tier 2 bid pack ₹40–75k/tender ·
Tier 3 complete ₹90k–1.5 L/tender · Tier 4 retainer ₹3 L/yr · optional success fee 0.5–1.5% from
private firms only. Skip the ₹1,500-per-upload GeM commodity market; sell the Go/No-Go + pricing
method. Always state the **one-tender-one-client** conflict rule and "no payment to any official".

## "AI se karwa loonga" — the AI-proof answer, and the pain-point lead roster

Buyer, owner or competitor will say paid AI (Claude/ChatGPT class ~₹2,000/mo in India, or an
India tender-AI SaaS licence) can produce the same documents cheaper. Do **not** defend the
documents — concede the doc layer fast and move the money. Answer in this fixed order:
1) the doc layer is commoditised; 2) capability matrix — AI does the tender PDF/OCR/checklist,
technical-bid text, compliance-matrix draft, BOQ structure, corrigendum summary and "suggested"
(historical-average = fiction) rate, but **cannot** produce the real no-loss price, accountability,
site truth, portal execution (DSC/catalogue/upload), the bank-CA-OEM chain, buyer-side
intelligence, the advice *"bid MAT karo, loss hoga"*, post-L1 negotiation, or ownership of the
deadline; 3) the rupee money logic (docs error = ₹1 cr AMC + ₹20–30 L revenue gone vs a ₹40–50 k
fee = 0.5% insurance; 8%-low quote = ₹8 L lost; rejected ePBG wording = ₹15 L blocked);
4) honest market comparison; 5) **tier table with an AI-proof rating** — T1 doc pack ₹15–25 k = LOW
(lead magnet only), T2 Bid Room ₹60 k–1.5 L = HIGH (real rate + site + portal), T3 AMC lifecycle
retainer ₹3–6 L/yr = HIGHEST ("AI kar hi nahi sakta"), T4 price-intel + Go/No-Go watch
₹15–25 k/month = MED-HIGH; 6) the honest limit — where the client only needs a format/letter we
lose to a ₹2,000 subscription, so target ₹50 lakh–5 crore deals where one mistake costs lakhs.
Sales line that lands: *"AI aapke chiller ki condition dekhne site pe nahi aayega… likhne ka kaam
hum bhi AI se hi karte hain, isliye aapko sasta padta hai"* + **"AI hamara dushman nahi, mera
staff hai"** (using AI internally is why we undercut the ₹1.5 L consultant at ₹60 k).
Best customer = someone who tried AI and got rejected twice.

**The companion deliverable — the pain-point lead roster.** When asked *"which firms need this,
with contacts and LinkedIn"*, ship one English XLSX with 6 sheets (`Leads PAN-India` incl.
**pain point** + evidence link + priority · `Tiers with Pain Points` · `AI vs HMW` ·
`Money Logic (Why They Pay)` · `Method and Honesty` · `First 90 Days`). Priority ladder
A+ (exact trade fit **and** live demand) → A (adjacent trade) → B → C (backup only). Pain points
must be **evidence-derived**, never generic: read the job post / tender result and translate it
("khud *Tender & Estimation Executive – HVAC* hire kar rahe hain = in-house capacity nahi").
Guardrails: carry a per-row `verified` / `check-domain` / `not found` flag and never invent a
website, email or LinkedIn URL; tell the owner to confirm one contact before bulk outreach
(consent/DPDP + brand risk); never guarantee a win (promise *compliant, correctly priced,
submission-ready + honest Go/No-Go*); real certificates/OEM letters only or the client is
debarred. Run the outreach **after** our own live bid closes — that pack is case study #1.
Full tables, script, segmentation, roster spec and harvest recipe:
`references/ai-proof-advisory-positioning.md` + `client-prospecting → references/job-board-capability-gap-leads.md`.

## Pitfalls

- **Site visit is an ELIGIBILITY item, not a courtesy — and the certificate is issued on the spot.**
  Window is usually publication → **2 working days before the bid due date**, working days only,
  1000–1600 hrs, with a **prior e-mail request** to the named officers (max 2 representatives,
  govt photo ID, authorization letter). Miss it and a perfectly priced bid is rejected at
  technical evaluation. Explain the payoff in the owner's language: entry pass + reality check on
  the "indicative" annexures + the takeover **joint as-found inventory supersedes the equipment
  annexure** + pre-existing defects recorded now become a documented price-adjustment query instead
  of silently becoming your cost. Formalities table + submission sequence:
  `references/tender-site-visit-submission-and-roi-summary.md`.
- **Submit at least 2 working days before the deadline.** GeM gets slow on the final day and DSC /
  upload failures cost the whole bid; the deadline and opening time come from the **corrigendum**,
  not the original notice. Pre-award prep that takes days must start early: Class-3 DSC registered
  on GeM, Udyam (MSE) EMD exemption, OEM/ASP letters.
- **"Contract kab se shuru hoga?" — the tender gives no calendar start date; derive it from the
  award clauses.** Answer: *"N (three) years from the date of commencement, extendable by up to 2
  further years"* — the clock starts at award + site takeover, **not** on the bid date. Build the
  timeline from the document's own mobilisation clauses (INCOIS case: order acceptance within **10
  days** of AOC · ePBG within **15 days** of award · joint as-found inspection within **14 days**
  of LoA · full mobilisation and deployment within **30 days** of LoA, ₹2,000/day penalty per
  milestone). Corroborate the reading with the ePBG validity (38 months = 36 + 2 buffer). Realistic
  calendar answer for a September bid: award Oct–Nov, service running Nov–Dec, 36 months to the
  same months three years later, extension to year 5 — and flip it into three prep warnings
  (mobilisation is one month of work, so team/OEM letters/BG facility must be ready *before*
  award; BG duration must cover the extension; the price freeze starts before the clock does).
  Present it as the standard "when each step happens" table (step | when | note). Details:
  `references/tender-site-visit-submission-and-roi-summary.md`.
- **Post-award: ePBG 5% must stay valid for contract period + 60 days** (keep any extension period
  inside the validity), submitted typically within 15 days of award — otherwise EMD forfeiture and
  debarment risk. Plan ~2 months of running cost as working capital (monthly arrears + ~30 days).
- **GeM "Estimated Bid Value" on a multi-year service bid is the TOTAL for the whole contract
  period, NOT per year.** Verify with two cross-checks: the price-bid item quantity (e.g. *Part A
  "Fixed Monthly CAMC Charges", Qty 36.00 Months*) and EMD = 2% of the estimate. A ₹1 crore
  estimate on a 36-month AMC = ₹33.33 lakh/year, ₹2.78 lakh/month. Misreading it as per-year
  inflates the ROI tenfold and produces a bid that loses the tender or bleeds. State the
  per-year and per-month split explicitly in every ROI answer.
- **Get the real tender document from the BUYER's website, not the aggregator.** Even when GeM's
  `showbidDocument` page is JS-walled, the buyer (INCOIS) publishes the full tender + corrigenda
  as PDFs on its own tenders page — find the row, download the PDFs, and check for a corrigendum
  that moves the due date. These PDFs are often **scans**: OCR with `pdftoppm -r 200 -gray` +
  `tesseract` (run pages through `xargs -P4`; 46 pages ≈ 3-4 min, so run it with
  `background=true`). Grep the OCR dump for `period of|contract period|Estimated Bid Value|
  ePBG|manpower|excluded|payment` — that single dump answers tenure, EMD, penalties, exclusions
  and the manpower requirement. Some annexure pages are rotated or mirrored and come back as
  word-salad — **do NOT skip them** (an earlier version of this skill said to; that advice cost a
  full read of the corrigendum). Auto-detect the orientation instead: OCR the same page in 8
  variants (0/90/180/270 × normal/mirrored) and keep the variant with the most English
  dictionary-word hits, then re-run the whole document at that rotation. In the INCOIS case the
  entire 39-page corrigendum was only readable at **270°** — at 0° tesseract returned reversed
  gibberish — and it carried the real inventory, the amended scope and a deleted equipment group.
  Recipe + script: `references/gem-corrigendum-and-ocr.md`.
- **Service-AMC ROI model (use this shape):** investment = EMD (refundable, MSME exempt) + ePBG
  (take a bank guarantee, don't block the cash) + tools/instruments + initial spares & chemical
  stock + working capital (≈2 months of running cost, because payment is monthly in arrears
  +30 days). Profit = bid value − annual running cost, where the big cost lines are manpower
  (≈50-56% of cost), spares, OEM/ASP service, chemicals, insurance/admin. Always publish three
  execution cases (lean / base / heavy) and a **floor price** = base break-even + ~10%. Flag that
  "firm and fixed rates for 36 months with no price-variation clause" means load an 8-10%
  escalation cushion into the quote.
- **Aggregator text ≠ the tender document.** A public notice (tenderdetail / CPPP mirror) is
  enough to *draft*, but always tell the owner to download the real tender after login —
  inventory annexure, price format, BOQ appendix, corrigenda — and state that corrigenda
  override whatever the aggregator shows. GeM `showbidDocument` pages are JS-walled (web_extract
  and a browser `innerText` dump both return <1 KB): don't burn calls there.
- **The CORRIGENDUM is usually the highest-value document in the whole set — read it before
  quoting a rupee.** It is rarely just a date change. In the INCOIS case No. 01 (issued 08-09-2026)
  contained: the buyer's "Reply to Pre-Bid Queries" table (columns *Clause | Raised by | Existing
  text of the tender | Text as amended*), a **revised Annexure VII (inventory with makes, models
  and serial numbers)**, a revised PPM annexure and a **new annexure** (filter schedule) — i.e. the
  real inventory and the amended scope travel *inside the corrigendum file itself*, no portal login
  needed. Harvest these before telling the owner "download the annexures after login":
  1. **Amended dates** + "where the tender document and the GeM portal differ, the portal governs".
  2. **Sign the corrigendum and upload it with the bid** — bidders who forget are non-responsive.
  3. **Deleted / added scope items** (one equipment group was deleted as condemned and replaced by
     a separate capital work, while a "holding obligation" stayed with the contractor).
  4. **New costs pulled INTO the lump sum** (one-off tests, annual overhauls, an extra sampling
     regime, a consumable replacement schedule) — price them or they eat the margin silently.
  5. **Exclusions re-confirmed** — end-of-life replacement of a chiller/cooling tower/AHU/PAC/
     pump/drive, and control-card/VFD end-of-life replacement, sit OUTSIDE the lump sum and belong
     to the item-rate set. Equipment the buyer has already declared end-of-life is a **near-certain
     order** — quote those item rates properly instead of dumping a token rate.
  6. **Relaxations** (e.g. OEM/ASP authorisation letter required for only 2 named machines, an
     undertaking accepted for everything else) — changes how much paperwork gates the bid.
  7. **Zero / blank / "NA" rates = bid NON-RESPONSIVE** where the corrigendum says so. Every
     price-bid line carries a number; never leave a token `0.00` to "fix later".
  8. **Who raised the pre-bid queries** is a free competitor read: national OEM-linked majors in
     the list means the small bidder's cost base is structurally higher — advise *lean-bid or skip*,
     never a price war. Say it plainly when the honest answer is "margin here is 5-15% at best".
  9. If a one-off activity repeats per year (eddy-current test once in 36 months, ultrasonic survey
     twice), **amortise it into the annual cost line** so the yearly profit table stays comparable.
  Full 14-point digest checklist + the ROI-sheet layout that survived review:
  `references/gem-corrigendum-and-ocr.md`.
- **Never invent rates, quantities or deadlines.** DOCX gets `<FILL: …>` markers; XLSX fill-me
  cells get a yellow fill and stay formula-driven. Close the draft with a clearly-marked
  "INTERNAL NOTE — PLACEHOLDERS (DELETE BEFORE SUBMISSION)" section listing every blank.
- **Keep the two copies separate.** The insider copy carries pricing/margin/competitor reasoning
  and must never reach the buyer — name the file "Insider" and say so in the covering message.
- **Assembly numbering drift**: when a long document is authored in separate module files,
  section numbers collide. Renumber with quote-anchored regexes in descending order, then
  `py_compile` and dump all headings to verify before building.
- **Search snippets are stale.** A tender shown "live" in a search result may have
  closed weeks ago. Always say "verify the last date on the portal before bidding" —
  never present a snippet date as the current deadline.
- **Don't push a beginner at big EPC work.** Large orders look impressive but carry
  thin/negative margins (an Indian HVAC EPC major posted a ₹123.95 Cr FY25 EBITDA loss
  with BB- rating). Recurring AMC + spares is the profitable core — say so explicitly.
- **Three gates kill unprepared bids**: EMD, turnover proof, experience certificate
  (plus OEM authorisation and class registration for large works). Warn before the
  owner wastes an EMD.
- **Portal registrations need DSC / Aadhaar / PAN / GST / ITR** — list them up front so
  the owner isn't surprised mid-registration.
- **Renewal pipeline trick**: government award/result (AOC) pages show who holds which
  AMC and for which period; AMCs are typically 1–3 years, so the re-tender shows up
  2–3 months before expiry. Teach this instead of only refreshing "live tender" pages.
- Generating XLSX on a PEP-668 host: `python3 -m pip install --break-system-packages openpyxl`.
  `execute_code` runs Python reliably; if a plain `terminal` call returns exit 126 with
  empty output, pass `workdir=<existing dir>` (stale session cwd) instead of chaining commands.
- **Verify every workbook write** by re-opening with `openpyxl.load_workbook` and
  printing sheet names + row counts before sending it.

## Live artifacts already built for HMW (reuse, don't rebuild)

- **Notion tracker** — DB `3d76012e-e39a-8140-89bc-ec3f6c2ba666` ("HMW Contracts & Buyers"),
  parent page `3d76012e-e39a-8168-a654-d8042662a028`, read-me page + "Growth Blueprint" page
  under it. Built with `~/hmw_notion/` scripts (mkdb.py, build_rows.py, patch1.py,
  mkblueprint.py). Token: `~/.config/notion/token`.
- **Notion API gotchas**: append children with `PATCH /v1/blocks/<id>/children` (POST =
  `invalid_request_url`); create databases/pages with `Notion-Version: 2022-06-28`;
  archive with `PATCH /v1/pages/<id> {"archived":true}`.
- **Daily tender digest** — `~/.hermes/scripts/hmw_tender_digest.py`, cron job
  `ffc6fbe597c0` (08:30 IST, `no_agent=true`, silent when nothing new). Parses aggregator
  listing pages with urllib (no JS), anchors rows on `#<bidref>`, keeps only `Live` +
  closing-date >= today + HVAC/AC keyword rows; state captured from the `GeM <State>` tail.
  Precision over recall — a widened source list floods the digest with non-Telangana and
  crore-scale civil works.
- **Local bid brain (RAG + rate registry) — answer money questions from here, never from memory.**
  `~/hmw_bid/rag/` holds chroma collections `hmw_tenders|clauses|rates|bidkit|leads` (~475 chunks)
  with `hmw_ask.py search|ask`; `~/hmw_bid/rates/hmw_rates.db` (65 rows) with
  `rate_cli.py find/add/fill/stats` holds the rate rows. Every lookup is **hybrid** — vector
  chunks **plus** an FTS5 rate hit labelled `[RATE DB]` — so hard numbers come out sourced
  (EMD **₹2,00,000**, PBG **5%**, CAMC floor **₹2.56 L/month**) instead of vague. Tender rate
  rows carry provenance/confidence tags: `tender` (buyer's own document) / `hmw-model` /
  `hmw-estimate` / `fill-needed` (awaiting a real vendor quote) / `verified`. A row still tagged
  `fill-needed` is a business TODO to close **before** the price bid — a blank or token `0.00`
  line makes the bid non-responsive. New tenders arrive by themselves: the daily digest appends
  to `~/hmw_bid/rag/digest_feed.jsonl` and weekly cron `a511f774db60` ingests only that delta.
  Design/build recipes: `chromadb-rag-ops → references/hybrid-retrieval-and-rate-registry.md`
  + `references/incremental-corpus-feeding.md`.

## References

- `references/hmw-air-controls-profile.md` — the family business: identity, 18 existing
  clients, service lines, what to sell each client type, Hyderabad target-buyer lists.
- `references/india-tender-channels.md` — portals, keyword recipes, eligibility
  glossary, bid-size ladder, renewal monitoring.
- `references/india-hvac-competitors-2026.md` — competitor tiers with sourced numbers
  and the "what to copy / where we win" conclusions.
- `references/gem-tender-bid-drafting.md` — tender link → bid set: notice-extraction recipe,
  11-section technical-bid skeleton, insider playbook outline, 9-sheet cost model, GeM
  mechanics that decide L1, and the single-source DOCX + Chrome-PDF build pattern.
- `references/gem-corrigendum-and-ocr.md` — the corrigendum-first workflow: orientation-detected
  OCR of scanned annexures, the 14-point corrigendum digest (deleted scope, added lump-sum costs,
  exclusions, rate-entry rules, who raised the queries), and the ROI-sheet layout with the
  floor-price method.
- `references/tender-site-visit-submission-and-roi-summary.md` — the last mile: site-visit
  formalities + certificate payoff, submission-day sequence (DSC, Stage-1 docs, corrected dates,
  EMD/MSE exemption, ePBG validity, the four bid-killing mistakes), and the tabulated
  investment/profit one-pager spec with its construction rules.
- `references/bid-consultancy-service-line.md` — packaging the same bid stack as a **paid
  consultancy for other firms**: sellable-service map (with India market prices), the
  feasibility verdict + gaps, four pricing tiers with the researched market benchmark, cost/margin
  table, Year-1 ramp, seven lead channels, six-step funnel, 90-day plan, and the
  ethics/conflict guardrails. Also carries the "start date / mobilisation timeline" table.
- `references/ai-proof-advisory-positioning.md` — **"why us when AI is cheaper"** positioning
  (capability matrix of what AI cannot do, rupee risk→fee insurance tables, market comparison,
  tier table with AI-proof ratings, the sales script and the honest limit) **plus** the
  pain-point lead-roster spec: prospect segmentation, evidence-derived pain points, the 6-sheet
  English XLSX layout, priority ladder and contact-honesty guardrails.
- `scripts/ocr_orient.py` — OCRs a rotated/mirrored scanned PDF: scores 8 orientations, picks the
  readable one, then dumps the whole document. Run this before declaring any scan unreadable.
- `scripts/build_bd_tracker.py` — generator for the tracker workbook skeleton.
