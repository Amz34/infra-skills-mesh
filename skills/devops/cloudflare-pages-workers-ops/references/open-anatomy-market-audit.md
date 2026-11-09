# Open Anatomy — product/market audit + roadmap (2026-09-07)

Condensed deliverable for Aamir's digital-health strategist ask (full end-to-end
audit + benchmark + positioning + top-10 ranked changes + roadmap). Data from
live measurements + web benchmark (Kenhub, Complete Anatomy/3D4Medical,
BioDigital, Zygote). Reuse for client deck/positioning — don't redo research.

## Live technical state (measured)

- Perf ELITE: TTFB 36ms, load ~196ms, ~2.4KB initial HTML.
- Content: 199 bones / 7 regions / 1,460-structure catalog / 213 bilingual
  EN+AR facts. Full RTL Arabic (rare among free anatomy tools).
- GAPS found: no robots.txt/sitemap/manifest/OG tags/JSON-LD/semantic content
  → search-engine invisible; no social preview card (raw link on LinkedIn/WA);
  no in-app search across 1,460 structures; facts passive (no quiz/recall);
  no PWA/offline; a11y partial (ARIA + lang/dir OK; focus trap, reduced-motion
  missing); no deep links per structure.

## Competitive benchmark (≈2026 prices)

| Player | Price | Notes |
|---|---|---|
| Kenhub | $39/mo, $29/mo×3, $290 lifetime | 485+ quizzes, spaced repetition, 6M+ students; moat = active recall |
| Complete Anatomy (Elsevier) | $39.99/yr student 1st yr, $99.99/yr pro, institutional | cut/dissect/annotate, female model, patient-ed bookmarks |
| BioDigital Human | free tier ~10 views/mo, ~$19.99/yr personal | 700+ models, 8 languages, embed |
| ZygoteBody | free web | basic visualizer |
| Anatomy.app | free+ | encyclopedia-style SEO → 1.2M users |

## Market data (search-backed)

- 3D anatomy market ~$265M (2025) → ~$462M (2032, ~8.25% CAGR); education
  ~58% of spend; MEA budget-constrained → free tools win; ME/Africa small
  share → low competition for Arabic-first.

## Positioning verdict

Sector: medical + allied-health students (nursing/physio/pre-med) + educators,
MENA + English markets. Wedge: "free bilingual (EN+AR) open-data explorer —
no login, no paywall, works on any phone" vs paid incumbents. Differentiators:
Arabic-first, open source, zero friction. DON'T promise muscles/skin layers
(not in catalog) or a paid tier (free = growth moat; monetize later via embed
licensing / institutional B2B).

## Top-10 changes (impact × feasibility, 5=highest)

1. Arabic-first SEO content: per-region/bone pages or prerendered JSON-LD
   (MedicalWebPage + FAQ schema) for 199 bones/7 regions — organic traffic moat. 5/5
2. Search box over 1,460 structures (data exists; ~30-line filter). 5/5
3. OG/social share card + robots.txt/sitemap/manifest. 5/5
4. Quiz/self-test mode from 213 facts (Kenhub-style recall + score). 4/5
5. Deep links (`?bone=ulna`) — shareable per structure. 4/5
6. PWA + offline cache (CF Pages SW; mind cache-bust versions). 4/5
7. Pinned multi-select compare (2–3 bones). 3/5
8. Explode slider 0–100% (Human Atlas parity; currently on/off toggle). 3/5
9. Progress tracking "explored X of 1,460" (localStorage). 3/5
10. Embeddable iframe widget (LMS/school embed → B2B door opener). 3/5

## Roadmap (90 days)

- Phase 1 (wk 1–2): items 2, 3, 5 — search, share meta, deep links.
  (Items 2+3 offered as immediate ~20-min work on 2026-09-07 — PENDING user reply.)
- Phase 2 (wk 3–5): item 1 — static prerender of 7 regions + 199 bone pages,
  JSON-LD, sitemap.
- Phase 3 (wk 6–8): items 4, 9 — quiz mode + progress (return visits).
- Phase 4 (wk 9–12): items 6, 7, 8, 10 — PWA, compare, explode, embed widget.
