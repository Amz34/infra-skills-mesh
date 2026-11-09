# Competitor / Reference Site Analysis

Use when the client says "competitor jaisi site banao" or hands over a
competitor URL to analyze. Goal: extract structure, content strategy, tech
stack, and gaps — WITHOUT copying content/design verbatim (identical copy =
DMCA + Google duplicate penalty; legal pitch in SKILL.md "Client Scoping
Q&A").

## Fetch (WAF fallback ladder)

1. `curl -sL -A "<desktop UA>" <url>` — many Arabic-region sites (e.g.
   abadnet.com.sa) return HTTP 403 behind a WAF/bot-check; curl then only
   gives a ~6KB challenge shell.
2. 403 → render with the browser (browser_exec): `new_tab(url)`,
   `wait_for_load()`, then read `document.body.innerText` + extract meta via
   `js()`. Strip fbclid/tracking query params from the URL first — pure noise.
3. **Reverse case (proven rafal.com.sa 2026-09)**: some WAFs bot-block
   HEADLESS BROWSERS ("URL blocked" interstitial page) while plain curl with
   a desktop Chrome UA returns HTTP 200 + full HTML. If the browser hits a
   block page, fall back to `curl -sL -A "<desktop UA>"` and parse the saved
   HTML (read_file/grep for h1-h3, `wp-content/themes` fingerprints, RTL
   `dir`). Run the ladder BOTH ways — neither direction is guaranteed.

## Extraction (one js() call)

- title, meta description/keywords, og:title/description/image, canonical,
  robots, viewport, lang/dir (ar + rtl), generator meta (WordPress fingerprint)
- h1/h2/h3 lists, img count + alt coverage, price/CTA buttons
- JSON-LD blocks — schema types present (Organization/WebSite/Product/FAQPage)
- analytics/tracking: gtag, GTM, Clarity, Hotjar, fbq, TikTok pixel
  (aggressive tracking = sales-funnel signal)
- perf signals: script count, stylesheet count, lazy-image ratio, preloads,
  jQuery; `performance.getEntriesByType('resource')` transfer sizes
- `<body>` classes (`wp-theme-astra`, `woocommerce`) → theme + platform

## Interpretation (worked example: Abadnet — Saudi training institute, 2026-08)

- WordPress 7.0.4 + Astra theme + WooCommerce course store, RTL Arabic
- Product page: title/meta/OG all copy the H1 (thin, non-unique), no keywords
  meta; 86 scripts + 42 stylesheets + 0 preloads + 0 lazy images = heavy page
- Pixels: fb + TikTok + Clarity + Hotjar + GTM = aggressive funnel tracking
- JSON-LD only Organization/WebSite — no Product/FAQPage on product pages
- Lessons for OUR builds: lean static pages, unique meta per page, richer
  structured data — that is how a reference competitor is BEATEN, not copied.

## Output

Structure findings as: strengths to reference → weaknesses to beat →
concrete recommendations for the new build. Never reproduce their text,
images, or layout pixel-for-pixel.

## Real-developer site anatomy (benchmark for "make ours the best")

When the client says "expertly analyze this link and make our site the best"
(Rafal rafal.com.sa 2026-09), the actionable output is their SECTION IA, not
their words. Extract and replicate the structure with ORIGINAL copy:

1. **Our Story / Legacy** — founder narrative + milestone grid (founded year,
   first landmark, N-th home delivered, current flagship). Gives "real
   company" weight.
2. **Awards / Recognition strip** (optional depth)
3. **Services as pillars** — Buy / Rent / Invest / Partner (or the business's
   real model): icon cards + concrete one-liners, each CTA → contact. Never
   a generic "services" blob.
4. **Communities / Projects with status chips** — per-project phase state
   ("Now Selling", "Coming Soon", "Under Construction", "Handover Qx 20xx")
   — makes the pipeline feel alive.
5. **News / Press / Updates** — dated milestone cards (X% sold, handover,
   construction start). Brand = live company, not demo.
6. Deep footer with nav columns, contact, legal.

Replicate the depth that signals "developer", keep your own brand's dark
luxury / art direction, and stop at ~3 added sections — more bloats nav
(content.js nav auto-derives from section keys). Rafal-class pages are often
WordPress + RTL — check `wp-content/themes` + `dir="rtl"` fingerprints, but
the copy must stay 100% original (never mirror their text).
