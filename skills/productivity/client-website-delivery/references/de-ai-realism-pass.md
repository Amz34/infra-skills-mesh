# De-AI Realism Pass — "generic / AI-type / fake-looking" complaint ke liye

Companion to `ux-psychology-design-overhaul.md`. That reference = design-system
overhaul when the page is "generic/boxy/dashboard-like". THIS reference = the
**realism pass** when the user says the site "looks AI-generated / fake /
wordpress-style realistic chahiye, AI-free" — usually phrased as fonts "AI
type small and random", email/contact "looks fake/generic", copy "generic".
Proven 2026-09-02 on estelar-demo v2 (dark-luxury real-estate demo, EN/AR),
after v1 was rejected with: *"Its looking generic make it using wordpress
style and relevant skills realistic ai free and fonts are also ai type small
and random email and ci[t]act looks ge..."*

Run the full list below — each tell independently screams "demo/AI".

## AI-tell checklist → concrete fix

1. **Poetic-vague copy** ("where skylines meet serenity", "knows your name",
   "outlive buildings", rule-of-three abstractions) → **concrete specifics**:
   floor/unit counts, sqm, delivery dates, neighborhood/corniche, status
   ("The Aria is now selling", "38 villas across 1.2M m², immediate
   possession", "40% sold in pre-launch"). Every sentence should carry a
   number, a place, or a date a human could verify.
2. **Number consistency**: figures must reconcile with their own arithmetic —
   estelar had "64 floors × 2 residences/floor" but copy said "212 units"
   (correct: 128). Cross-check every derived count before writing copy; one
   broken figure nukes the whole trust layer.
3. **Fake contact details**: `.example`/`example.com` email TLDs,
   all-zero phone numbers (`+966 55 000 0000`), placeholder CR/TAX numbers →
   real-format fictional: `hello@<brand>.sa` + the client's actual mobile in
   national format (`+966 5X XXX XXXX`, Saudi mobiles = 5x + 8 digits) +
   real-looking address/hours. Same format rules as real listings.
4. **Font pairing tell** — Cormorant Garamond + Manrope (or any
   "AI-luxury default" pairing) → **WordPress-premium classic**:
   Playfair Display (display/serif, 500–700 + italics) + Inter (sans
   300–700). Arabic builds: Noto Sans Arabic (body) + Amiri (headings).
   Google Fonts two-family link, WP-classic look.
5. **Micro-caps disease** ("chhota-random" feel): 9–11px `tracking-[0.2–0.3em]`
   uppercase eyebrow labels + all-caps buttons everywhere → sentence-case
   text, sizes +1–2px, base html `font-size: 17px` (16px reads "small").
   Audit greps: `text-[1[01]px]|tracking-\[0\.[23][0-9]em\]|text-xs` and
   `uppercase` class sweeps.
6. **Trust-layer realism**: licensing/regulatory bodies (Saudi real estate:
   REGA, Aqar), warranty claims ("5-year structural warranty"), grounded
   testimonials ("handover came three weeks early"), delivery milestones —
   the credibility furniture real premium sites carry.
7. **Loud "fictional concept showcase" disclaimers**: if the user asks for
   realistic, remove/soften them — they undercut the realism ask. Meta
   title/description also get humanized ("… | The Aria Now Selling").

## Execution pattern (proven)

1. Read the ENTIRE content file first; diagnose AI-tells; keep key-shape
   contract IDENTICAL (components untouched → build pass = contract check).
2. One single `write_file` rewrite of the content module (not patch-by-patch),
   then index.html (fonts link + title/desc), tailwind.config (fontFamily
   swap), index.css (17px base, sentence-case helpers).
3. `npm run build` → preview redeploy (`--branch preview`) → curl-verify.
4. **Live screenshots in a FRESH Chrome** after any daemon restart (see
   headless-browser-automation skill): EN hero/mid/portfolio/contact +
   AR (toggle + RTL) + mobile — compose 2 review sheets (EN grid, AR grid)
   with PIL (resize ≤760w) for Telegram.
5. Verify computed styles live: h1 fontFamily contains Playfair, body Inter,
   base 17px, `document.documentElement.lang/dir` flips with the toggle.
6. Approval gate → prod deploy only after user review (never before).
