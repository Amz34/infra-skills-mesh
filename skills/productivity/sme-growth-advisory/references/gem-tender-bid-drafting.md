# Tender link → submission-ready bid set (India / GeM, SME size)

Trigger: user pastes a tender link (tenderdetail.com, bidplus.gem.gov.in, CPPP) and asks
for a bid draft, "tender banao", "official way me draft karo", or an insider copy for the team.
Worked case: INCOIS (Hyderabad) HVAC CAMC, GeM `GEM/2026/B/7915716`, 2026-09.

## Step 1 — Extract the notice

- `tenderdetail.com/Indian-Tenders/TenderNotice/...` extracts fine with **web_extract**
  (cached at `~/.hermes/cache/web/<host>-<hash>.md` — re-read the cache instead of re-fetching).
- Slice the important regions by **string index**, not line patterns: find `'Part B'` and
  `'B.1'` and print `t[idx-1200 : idx+3000]`. A regex like `^B\.\d+` against the markdown
  returns **zero** matches (formatting differs) — index slicing always works.
- Keyword-filter the detail tables for: `EMD|Bid End|Opening|Pre-Bid|Annexure|Eligibility|Turnover|Similar work|Period`.
- `bidplus.gem.gov.in/showbidDocument/<id>` is JS-walled: web_extract returns ~1 KB and a
  browser `innerText` dump ~0.6 KB. Do not burn calls there — the aggregator text is enough
  for a draft. **Say explicitly in the answer** that final terms must be downloaded from GeM
  after login (Annexure VII inventory, Annexure IX price format, BOQ appendix, corrigenda).

## Step 2 — Always deliver THREE artifacts

1. **Technical bid** — submission-ready, English, official tone: DOCX (master to fill/print/sign) + PDF (reading copy).
2. **Insider copy / playbook** — internal, for the family/team; never sent to the buyer.
3. **Cost model + BOQ workbook** (XLSX) — the price is built here, not in chat.

## Technical bid skeleton (11 sections — reuse verbatim next time)

| # | Section | What it must carry |
|---|---|---|
| 1 | Bid submission letter | bid no., buyer + designation, subject line, "examined Section 4/5/6/7 + Annexure VII/IX + corrigenda", EMD/PG position, 90-day validity, declaration of compliance |
| 2 | Bidder profile | trade name, GSTIN, Udyam, address, contacts, authorised signatory, service lines, client list, turnover + similar-work tables (blank to fill) |
| 3 | Understanding of scope | tender's own system-wise groups (chillers, CTs, pumps, tanks/valves, AHU/CSU/FCU/VAV, split/tower/cassette, PAC, panels & VFDs, water coolers/RO/fridges/ULT, resident supervisor, OEM service, refrigerant, chemicals) + the Part B table (B.1–B.14) |
| 4 | PPM schedule | frequency matrix (daily → annual) per equipment class |
| 5 | Method statement, response & controls | operating SOP, PPM execution, water treatment programme, refrigerant/F-gas log, breakdown response + SLA matrix, spares/consumables min stock, tools & calibration |
| 6 | Manpower & site organisation | resident supervisor (qualification, shift), technician roster, EPF/ESI, police verification, uniform/ID, 3-tier escalation matrix with response times |
| 7 | QA, reporting & KPIs | MIS/log sheets, OEM service report, RCA, statutory test reports, uptime %, TAT, first-time-fix |
| 8 | Statutory compliance, safety & discipline | CLRA/EPF/ESI/minimum wage, PTW, LOTO, working-at-height, refrigerant handling, campus rules, confidentiality undertaking |
| 9 | Contract management | tenure, payment terms, PG/EMD, LD/penalty acceptance, price validity |
| 10 | Deviations & pre-bid clarifications | **NIL deviation** statement + queries raised |
| 11 | Declaration & signature | signatory block with place/date/seal |
| + | Annexures list | A-1…A-n table (Udyam, GST, PAN, ITR, turnover CA cert, experience certs, OEM/ASP letters, staff list, tools list, undertakings, site-visit report, DSC) |

Finish with **"INTERNAL NOTE — PLACEHOLDERS (DELETE BEFORE SUBMISSION)"** listing every
`<FILL: …>` blank, so the owner can complete the draft and then delete that page.

## Insider playbook skeleton

Bid-at-a-glance → our position/strengths → must-do list → **pre-bid queries to submit** →
pricing strategy → submission mechanics (DSC, EMD exemption) → **why GeM bids get rejected**
(own self-check) → day-by-day action plan to the deadline with owners → first 30 days after
award → do / do-not list → list of blanks still to fill.

## Cost-model workbook sheets (9)

`1 Cover` · `2 PartA_Monthly_CAMC_Cost` (system group × manpower/OEM-spares-consumables/
refrigerant/chemicals/tools-insurance-overheads, auto-totals, margin %, annual & 3-year) ·
`3 PartB_ItemRate_BOQ` (B.1–B.14 + sub-items, qty × rate) · `4 Manpower_Plan` (wage + EPF/ESI) ·
`5 PPM_Schedule` · `6 Spares_Consumables_Tracker` (min stock, vendor, quote) ·
`7 Compliance_Checklist` (doc × owner × due) · `8 Action_Plan` · `9 Margin_Calculator` (+ sensitivity).

## GeM mechanics that decide the outcome

- **Part A = fixed monthly CAMC lump sum → decides L1.** Part B item-rate work is paid only on
  actual order, so never inflate Part B to compensate for a thin Part A.
- **EMD exemption via Udyam/MSME** registration + tender-fee exemption; performance security
  typically 5% of contract value; DSC mandatory for submitting.
- Typical gates that disqualify: OEM / authorised-service-partner letter for chillers & PAC,
  turnover + similar-work certificates, resident supervisor payroll + EPF/ESI challans, and —
  at national institutes — staff address/police verification for site access.
- Public-notice numbers are advisory: the buyer's published corrigenda override them.

## Build pattern (single content source → DOCX + PDF)

- Content as Python modules of blocks: `("H1"|"H2"|"H3"|"P"|"B"|"N"|"T"|"PB", value)`,
  split across several files (`c1..c3b` for the bid, `i1..i2` for the insider copy).
- `mk_docx.py` — python-docx: A4, header letterhead line, footer PAGE field via `fldSimple`,
  `Table Grid` + navy header shading, `**bold**` parsed into runs.
- `mk_pdf.py` — same blocks → one HTML with print CSS → Chrome headless print-to-pdf
  (technique + flags: `chrome-print-pdf-production` skill).
- **Numbering drift is the #1 assembly bug**: modules written separately collide (two sections
  numbered 8). Fix with quote-anchored regex replacements (`'"7.' → '"3.'`), applied in
  **descending** order so a remap never re-hits its own output; then `py_compile` every module
  and dump all `("H1"|"H2"|"H3"` headings + `Section \d+` cross-references to eyeball them.
- `py_compile` after every generated `.py` write: a truncated write surfaces as SyntaxError
  (keep each content module ≲6 KB, or write via a heredoc python script instead of one big file).
- **Never invent rates, quantities, or deadlines.** Use blanks + formulas in XLSX (mark
  fill-me cells with a yellow fill) and `<FILL: …>` markers in DOCX.
- Verify before sending: DOCX paragraph/table counts via python-docx; PDF `pdfinfo` page count
  + `pdftotext | head`; workbook re-opened with `openpyxl.load_workbook` (sheet names, formula
  rows). Deliver with one `MEDIA:<abs path>` line per file.

Artifacts from the worked case: `/home/ubuntu/hmw_bid/` (`c1..c3b.py`, `i1..i2.py`, `mk_docx.py`,
`mk_pdf.py`, `mk_xlsx{,2,3}.py`, DOCX/PDF/XLSX outputs).
