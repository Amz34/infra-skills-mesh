# Site visit → submission → investment/profit summary (India govt tender, GeM)

Companion to `gem-tender-bid-drafting.md`. Worked case: INCOIS HVAC CAMC `GEM/2026/B/7915716`,
due 22-09-2026 (extended from 03-09 by Corrigendum No. 01), 3-year tenure, 2026-09.

## 1. Site visit — formalities (quote these only after reading the tender's own clause)

Typical public-institute clause (Section 2.1 + corrigendum): **site visit is MANDATORY and the
certificate is an eligibility list item** — no certificate = reject at Stage-1 (technical), the
price bid never opens. So the certificate → trip is the highest-leverage hour of the whole bid.

Formalities that repeat across these tenders:

| Item | Typical requirement |
|---|---|
| Window | from publication date until **2 working days before the bid due date**; working days only |
| Hours | 1000–1600 hrs |
| Prior request | **e-mail to the named officers first** (HOD/grievance address too); visiting inside the window cannot be refused |
| People | max **2 representatives**, company authorization letter on letterhead |
| Carry | valid **Government photo ID**, visiting card, notebook, camera/phone (nameplate photos), safety shoes + torch (plant rooms) |
| Certificate | issued **on the spot** in the tender's own Annexure format (Annexure I), signed + sealed by the authorised officer, with name/designation/date — original goes with the bid |
| Queries | pre-bid meeting is usually already done; later queries go **only on the GeM portal**, with its own cut-off |

What the certificate actually buys (explain this to the owner — it is the "why bother" answer):

1. Entry pass — mandatory eligibility item; a cheap quote without it still dies.
2. Reality check on "indicative" annexures — buyers label the equipment inventory (Annexure VII)
   and price format (Annexure IX) **indicative**, i.e. not warranty-grade.
3. **Takeover signs a joint as-found inventory that SUPERSEDES the annexure list** — the visit is
   the last chance to record what is really there (make/model/serial/qty/condition/filter sizes).
4. Pricing basis + pre-existing-defect evidence: defects recorded now become a documented query
   ("this unit was already dead/leaking — exclude or adjust"), instead of becoming your cost.
5. Officer name/designation/contact for later mobilisation and access approvals.

## 2. Submission — when and how

- Submit **at least 2 working days before the deadline** (portal slowness / DSC-upload failures on
  the last day are the classic way to lose a bid). Deadline and opening time come from the
  **corrigendum**, not the original notice.
- Sequence: GeM seller login + **Class-3 DSC registered on GeM** (allow 1–2 days to sort) → search
  bid no. → Participate/Show Interest → Stage-1 document upload → Stage-2 price bid → Submit →
  download the acknowledgement PDF.
- Stage-1 must always include: the **signed + stamped corrigendum** (skipping it is the #1
  non-responsive kill), the site-visit certificate, OEM/ASP letters for the equipment the tender
  names them for (undertakings for the rest), the price schedule with **every line priced —
  zero / blank / NA = reject**, plus the compliance-checklist documents.
- EMD: pay online/BG, **or claim the MSE (Udyam) exemption** — and still upload the Udyam proof.
- Award: winner submits **ePBG 5%** (typically within 15 days) valid for **contract period + 60
  days** — keep the extension period in the validity or you forfeit EMD / risk debarment.
- Money timing: monthly invoice in arrears + ~30 days ⇒ keep **~2 months of running cost** as
  working capital.

## 3. Investment + profit one-pager (the format the owner asks for)

Owner (non-technical, family business) wants the money answer twice: a 6-line chat version, then
**"isko acche tabulated format in English, crystal clear"**. Deliver BOTH — the chat tables and a
1–2 page English PDF. Standard four blocks, in this order:

1. **Investment required** — every line item with a *Right column `Refundable?`*: EMD +
   performance security are refundable (or ₹0 under MSE exemption / use a Bank Guarantee instead
   of blocking cash), tools & ISO are one-time, spares stock is revolving, working capital is
   recovered. Then the three-row total block: TOTAL FUNDS TO ARRANGE → less refundable →
   **NET CASH AT RISK**. That last number is the one the owner cares about.
2. **Yearly cost vs revenue** — three execution columns (Lean / Base / Weak), rows: running cost,
   revenue at the tender estimate, profit/(loss) per year, margin %, profit over 36 months.
   Show the Weak column as a negative — the owner must see the loss case.
3. **Profit at different winning prices** — one row per candidate bid value: bid (36 months),
   effective monthly price, profit/year at base cost, margin, 36-month profit at base and at lean.
   Descending prices, ending below break-even so the floor is obvious.
4. **Decision rules box** — floor monthly price and the bid value it maps to; target band; the
   leverage line ("every ₹1 lakh/month = ₹12 lakh on a 36-month bottom line"); return on at-risk
   capital; extension-year upside with no new investment; item-rate (Part B) margin range; and the
   biggest risk (rates firm & fixed for the whole tenure, no escalation → bake a cushion now).
   Close by ranking item-rate works where the field data already shows end-of-life units.

Rules of construction:

- **Self-analyse the tenure** from the tender (never ask the owner). Read multi-year tender values
  for the **whole contract period**, not per year.
- Keep one rounded headline in chat ("~₹16 lakh invest, ₹2–7 lakh/year profit") and let the tables
  carry precision; the in-chat totals must match the PDF exactly.
- Generator: HTML + print CSS → Chrome headless print-to-pdf (`chrome-print-pdf-production`
  skill), e.g. `/home/ubuntu/hmw_bid/mk_roi_onepager.py`. Four tables at ~8.5pt A4 legitimately
  spilling to 2 pages is fine — do not shrink below ~8pt chasing a single page.
- Verify with `pdfinfo` (page count) + `pdftotext` before sending; deliver with one
  `MEDIA:<abs path>` line.

## 3a. Rupees-only variant (when the owner says *"show the profit in rupees, not percentage"*)

Same page, same four blocks, but every profit figure becomes an absolute rupee columns and the
margin-% column is deleted: *profit per year · profit per month · profit over 36 months* for each
of Lean / Base / Weak, and for each candidate bid price *profit/year (base) · profit/month (base) ·
36-month profit (base) · 36-month profit (lean)*. Keep one "≈₹0 at break-even" line so the floor
price is still obvious. Indian digit grouping (`2,63,000`), no `₹` inside table cells when the
header already says rupees. Generator: `/home/ubuntu/hmw_bid/mk_profit_rupees.py` →
`HMW_INCOIS_Profit_in_Rupees.pdf` (2 pages). Compute the figures in the script and print them —
never hand-round in the message, so chat and PDF cannot drift.

## 3b. "Contract kab se shuru hoga?" — the start-date answer

The tender carries **no fixed calendar start**. What it says is *"the AMC is for N (three) years
from the date of commencement, extendable by up to 2 further years on the same terms"* — the clock
starts at **award + site takeover**, not on the bid date. Reconstruct the calendar from the
document's own mobilisation clauses rather than guessing:

| Step | When (from the clause) |
|---|---|
| Bid due / opening | as per the corrigendum (19:00 / 19:30 in the INCOIS case) |
| Evaluation → L1 → award (LoA/AOC) | GeM cycle, realistically 3–6 weeks after opening |
| Acceptance of order | within **10 days** of AOC |
| ePBG 5% submitted | within **15 days** of award — validity **38 months** (= 36 + 2 buffer) |
| Joint as-found inspection + takeover | within **14 days** of LoA (supersedes Annexure VII) |
| Full mobilisation + deployment | within **30 days** of LoA, ₹2,000/day penalty per milestone |
| Service running / ends / extension | award month + ~1 month → 36 months → up to 2 more years |

For a September bid, say plainly: **service starts Nov–Dec, runs to the same months three years
later, extension possible to year five.** Then convert it into prep warnings: mobilisation is one
month of work so team shortlist, EPFO/ESIC + police verification, OEM/ASP letters and the BG
facility must be ready *before* award; the 38-month BG must cover the extension; the price is firm
for the whole tenure and is locked *before* the clock starts, so the escalation cushion goes in now.
Deliver as the standard three-column `Step | When | Note` table plus a short "be ready before
award" table.
