# Corrigenda, scanned annexures and the bid ROI sheet

Companion to `references/gem-tender-bid-drafting.md`. Written from the INCOIS HVAC CAMC case
(GeM `GEM/2026/B/7915716`, doc `INCOIS:PUR:96/2025`, ₹1 crore estimate, 36 months) where the
buyer's corrigendum — not the tender — turned out to hold the real scope, the real inventory and
the amended price basis.

---

## 1. Reading a scanned / rotated tender PDF

Buyer websites (INCOIS publishes `documents/Tenders/*.pdf`) hand you scans, not text PDFs.

Pipeline:

```bash
pdftoppm -r 200 -gray tender.pdf /tmp/pg          # 200 dpi grayscale is enough
ls /tmp/pg-*.p*m | xargs -P4 -I{} sh -c 'tesseract "{}" stdout --psm 6' > ocr.txt
```

- 46 pages ≈ 3–4 min. Run the whole thing with `background=true, notify_on_complete=true`; never
  a foreground call at the edge of the 600 s cap.
- Then **one grep dump answers most of the commercial questions**:
  `grep -inE "contract period|Estimated Bid Value|EMD|ePBG|penalt|excluded|manpower|payment|site visit" ocr.txt`

### Rotated / mirrored pages: detect, don't skip

Degraded scans come out as reversed word-salad (`9202-80-EL` for `18-08-2026`, `SIODNL` for
`INCOIS`) — that is a rotation/mirror problem, not a bad scan. Never conclude "unreadable" and
never skip the annexures: **OCR one page in 8 variants** (0/90/180/270°, each also mirrored) and
keep the variant with the most hits against a common-English-word list, then re-OCR the full
document at that orientation. Mirrored-page text cannot be recovered by reversing the characters —
you must re-render the image.

In this case the whole 39-page corrigendum was readable only at **270°**; at 0° every page was
gibberish. Run `scripts/ocr_orient.py` (does detection + full-document OCR in one go).

Corollary for future skill notes: a previous version of `SKILL.md` said "some annexure pages are
mirrored/rotated; skip them". That was wrong and cost a re-read — corrected there.

---

## 2. Fourteen-point corrigendum digest

Produce this as a sheet in the workbook *and* as a chat list. Every point below was live in one
real corrigendum No. 01.

1. Corrigendum number and date; reference numbers must match the GeM bid id and buyer doc number.
2. **Amended dates** — clarification cut-off, pre-bid date, submission due, opening. State the
   cut-off hour; "22-09-2026 1900 Hrs", not "22 September".
3. **Tender document vs portal conflict rule** — the portal governs. Say it, so nobody trusts a
   stale PDF.
4. **Sign the corrigendum and upload it with the bid** (some tenders make it mandatory → non-
   responsive otherwise). Add "cover letter + signed corrigendum" to the submission checklist.
5. **Which documents were re-issued with the corrigendum.** Revised inventory annexure (makes,
   models, serial numbers), revised PPM/checklist annexure, new annexure (filter schedule). These
   are inside the corrigendum file — you do not need portal login to price the job.
6. **Deleted scope items** (an equipment group deleted as condemned, disposal under a separate
   tender, replacement a separate capital work) — and any *residual obligation* the tender keeps
   with the contractor while the condemned asset is still on site.
7. **Added costs pulled into the lump sum** — one-off tests (eddy-current testing on named
   machines, ultrasonic wall-thickness surveys), annual overhauls (chillers per OEM running hours,
   PACs, AHUs/ERV, freezers, fan motors, pump bearings), consumable replacement schedules,
   extra water sampling. Add a cost line for each, or the margin disappears quietly.
8. **Exclusions re-confirmed** — end-of-life replacement of chiller / tower / AHU / PAC / pump /
   drive, and control-card / VFD end-of-life replacement, sit outside the lump sum. Where the buyer
   replaces an asset mid-contract, note the pro-rata CAMC adjustment clause.
9. **Items already declared end-of-life by the buyer** = near-certain item-rate orders. Quote those
   item rates properly; this is where the real profit is on a thin AMC.
10. **Rate-entry rules** — zero, blank or "NA" rates made non-responsive (a change from the base
    tender, which had allowed `0.00`). Every line carries a price.
11. **Relaxations** — e.g. OEM/ASP authorisation letter required for only two named machines, an
    undertaking accepted for everything else. Recompute the paperwork/eligibility list.
12. **Manpower and resident-staff requirement** — re-check whether any technician/helper/reliever
    count is mandated, and distinguish it from the buyer's separate O&M manpower contract.
13. **Site-visit window** — working days 1000–1600 hrs up to two working days before due date, on
    prior e-mail, certificate issued on the spot. Put the visit and the nameplate-recording task in
    the action plan; it is the only chance to price ambiguous commodity groups.
14. **Who raised the pre-bid queries.** If national OEM-linked majors are querying, the small
    bidder's cost base is structurally higher (OEM rates, bulk refrigerant, own crews). The honest
    advice is *lean-bid or skip*, with the real profit in the item-rate set and the extension.

Also record where the record is ambiguous (quantity differs between the list and a note, tank
capacity differs, pump-end makes known only at site) — explicitly instruct the owner to price per
the revised annexure and verify at joint inspection.

---

## 3. ROI sheet layout that survived review

Sheet name `10 ROI_Investment`, added as a **new sheet** — never rewrite the existing cost sheets.

| Section | Content |
|---|---|
| 1 | Contract facts with a source tag per line (`[T]` = stated in tender/corrigendum, `[E]` = our engineering estimate) |
| 2 | Tenure + extension, in plain words, first line of the sheet |
| 3 | Revenue scenarios — at estimate / likely L1 (−5%) / floor / danger zone, each as ₹/year and ₹/month, shown as `= total/36` formulas |
| 4 | Annual cost build-up, three columns: lean / base / heavy, one line per cost head with a basis note |
| 5 | Profit at each price (per year, all three cases + 36-month total) |
| 6 | Investment required — refundable vs at-risk split, working capital = 2 months of base cost |
| 7 | Return on money at risk over the term (%) |
| 8 | **Live calculator** — yellow input cells (monthly rate, annual cost) with real Excel formulas so the owner can re-price himself |
| 9 | Where the money really is (item-rate works, end-of-life replacements, extension, reference value) |
| 10 | Verdict / floor price / risks / "deal only if" test |

Method notes that matter:

- **Floor price = base break-even for the full term**, then quote above it; target band sits between
  break-even and the buyer's estimate. Publish all three break-evens (lean/base/heavy) so the owner
  sees how narrow the safe band is.
- **Firm-and-fixed rates for the whole term with no price-variation clause** → load an 8–10%
  escalation cushion; there is no renegotiation.
- **Competitive reality check**: on a comprehensive AMC with OEM-linked majors bidding, a small
  bidder's honest margin is single digits to low teens. Say so, and say what to do instead
  (lean execution, item-rate works, treat year 4–5 extension as the profit pool, or skip).
- When your own earlier answer used a wrong assumption (e.g. "₹1 crore is per year"), correct it
  explicitly in the next reply with the source line that fixes it. Don't quietly change numbers.
- Two small workbook-hygiene fixes that recur: search the finished sheets for `MSP` (should be
  `MSE`) and for duplicated header labels in the column-header row; and add the new sheets to the
  cover sheet's contents list so the owner can navigate.
