# Deterministic replication QA — sentiment parity + rendered-card verification

Recipe from 2026-09-19: replicate a viral "I am starting a new position / here is my exact hiring screen"
post (`raj-vaibhaav` ugcPost-7497…, seed link `lnkd.in/p/dQmJH24f`) into Aamir's own announcement.
Working tree to reuse as the template: `~/ops/linkedin/newposition/` (drafts/, copy/, assets/, out/).

Why it matters: "replicate this viral post" is only defensible if you can **measure** that your copy carries
the same emotional signature and your cards actually render. Eyeballing after a render is not QA.

## The QA chain (one command, reproducible)

`./run_qa.sh` in that dir runs the whole deterministic chain, every artifact into `out/`:

1. `sentiment_audit.py <post.txt> --json out/audit_X.json --label X` — VADER (rule-based, reproducible)
   per-document dims: chars / words / lines / bullets / avg bullet length / hook line-1 and line-2 chars /
   you-vs-first-person ratio / questions / emoji / hashtags / links / Flesch / mean bullet compound.
2. `parity.py` — source vs each draft, per-dimension tolerance bands → `out/parity_report.md`, whose verdict
   line reads `N dimension(s) outside tolerance; M/N matched`.
3. `li_reach.py score <draft> [--json]` — the reach gate (0-100 + raw `x/104` + `fails[]`).
4. `claim_integrity.py` (mandatory before shipping) → `out/claim_integrity.txt`.
5. `build_cards.py` — cards at 1080×1350 (+ `carousel.pdf` for the document-post variant).
6. `verify_cards.py` — geometry / font / contrast / pixel / OCR per card → `out/cards_qa.txt`.
7. `summary.py` — one-glance `out/final_status.txt` (parity dims, gate scores, card verdict, manifest).

Env: keep this in an isolated venv (`python3 -m venv ~/.venvs/sentiment && ~/.venvs/sentiment/bin/pip
install vaderSentiment`) — PEP 668 blocks system-python installs.

## Technique: measure rendered HTML with no browser-automation stack

1. Render: `google-chrome-stable --headless=new --screenshot=out.png --window-size=1080,1350 file.html`.
2. Measure: inject JS that writes a JSON blob into `document.title`, then
   `google-chrome-stable --headless=new --dump-dom file.html` and pull the blob out of the `<title>`.
   Nothing else reads computed styles headlessly.
3. The JS should return, per card: every element's rect, **overflow detection** (any child rect outside the
   card box), `document.fonts.check('800 96px Inter')`, and a **WCAG contrast ratio per text node**
   (walk up ancestors for the first non-transparent `background-color`; fall back to the card background).
4. Thresholds: ≥ 4.5 normal text, ≥ 3.0 large text (≥ 24px, or ≥ 18.66px at weight ≥ 700). Report the
   passing count as evidence of legibility; a gradient/glow overlay is only approximated, so say so.

## OCR pitfalls — a whole-card read lies

- One `--psm 6` read of a display-type card mis-segments badly: it rendered line 2 (`not the`, 96px) as `e`
  and missed the `SWIPE` pill entirely. Both were real pixels. Before calling anything a render bug,
  confirm with **per-row ink coverage** (PIL) plus a **crop OCR** — line 2 carried 9.35% ink and read
  cleanly as `not the` under psm 7.
- Pass criterion: OCR each card under **psm 4, 6 and 11** and accept if ANY mode contains every required
  phrase after normalisation (uppercase → strip non-alnum → map `|`→`I`). Inter's uppercase `I` OCRs as a
  pipe, so `I DO NOT CARE ABOUT` comes back as `| DO NOT CARE ABOUT`; space-insensitive matching also
  absorbs letter-spaced kickers and line breaks.
- **Reversed text is invisible to whole-card OCR**: dark text on an accent pill (`SWIPE`) never appears.
  Mark those elements `data-ocr="1"` in the HTML, have the measurement JS return their rects, then crop the
  PNG around each rect (3× upscale, `--psm 7`) and match the element's own text. That is what finally
  verified the pill; crop-OCR also proved the pill text was rendered, not missing.

## VADER gotchas

- The lexicon is **US English**: `favourite` scores 0.0, `favorite` 0.459. A "warmth" dimension tuned with
  British spellings silently does nothing — push candidate phrases through the analyzer BEFORE rewriting
  copy, then apply the ones that score.
- Warmth drift is the classic replication failure. The source's positivity lives in short human parenthetical
  asides ("life happens, I get it", "welcome to 2026", "my favorite question to ask"), not in the claims.
  Copying only the skeleton landed at mean bullet compound **0.095 vs the source's 0.169** (open DRIFT).
  Fix by restoring honest asides on 2-3 bullets → re-measure (0.194 PASS), never by softening the threshold.
- Keep `parity.py`'s guardrail text in the report: do not claim a scoring advantage that the measurement
  does not show.

## Honest-deviations rule (do not soften a report to defend earlier copy)

The first pass claimed post_a and post_c "tie at 96/104, only the Tue-Thu slot unclaimed". Re-measuring
showed a `signoff` deduction on post_b, a `good_slot` deduction on all three, and a warmth DRIFT the report
had to record. Correct action: fix the copy (additive asides) and re-run, not reword the finding. State the
residual deductions in the handoff.

## Delivery shape that worked

- All files in English; the final post pasted inline in chat as a paste-ready block (the user posts by hand).
- Attach every visual: one PNG per card **plus** the carousel PDF (document-post = highest dwell).
- List the fill-in slots explicitly: role title, city/on-site mode, and the apply route **in the first
  comment** (links in the body cost reach); posting window Tue-Thu 13:00-20:00 KSA; reply to every comment
  in the first hour (that is what drove the source post's spread).
- Make geometry/contrast/OCR the primary evidence, with a vision pass as secondary confirmation.
