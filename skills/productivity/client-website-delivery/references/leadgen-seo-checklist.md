# Lead-Gen SEO Checklist (client sites)

When Aamir says "site ko SEO banana hai leads ke liye" — audit first, then the
4-layer plan in cost order. Layers 1–2 are free and high-impact; run them
before selling the client a domain.

## 1. Quick audit (5 min, read-only) — show results as "already strong"

```bash
# Title lengths (50-60 chars ideal; 29-59 is acceptable)
for f in *.html ar/*.html; do t=$(grep -o '<title>[^<]*</title>' $f | sed 's/<[^>]*>//g'); echo "$f: ${#t} chars"; done
# Meta description coverage
for f in *.html ar/*.html; do c=$(grep -c 'meta name="description"' $f); [ "$c" -eq 0 ] && echo "$f: MISSING desc"; done
# hreflang coverage (404.html exempt)
for f in *.html ar/*.html; do c=$(grep -c 'hreflang' $f); [ "$c" -eq 0 ] && echo "$f: MISSING hreflang"; done
# Schema types present
grep -o '"@type": *"[^"]*"' index.html | sort -u
```

Good baseline = titles in range, every page has a description, EN/AR hreflang
pair, Organization + WebSite + FAQPage schema (FAQ = rich-result eligibility).

## 2. The 4 layers

### Layer 1 — Keyword & content strategy ($0, ~2–4K tokens/page)
- Target BUYING keywords, not head terms: `venturi valve supplier`,
  `isolation room controller FMS-1650`, `hospital HVAC pressure monitoring`,
  `Triatek certified maintenance`, `[product] supplier/maintenance`
- Weave into titles, H1s, body copy; expand FAQ blocks per page
- One keyword focus per product/service page (avoid cannibalization)
- **FAQ rich-results injection (PROVEN — done on AVVS products/services/
  industries, EN+AR, 28 Qs):** add a visible `.faq-list` section (h3 question +
  p answer per `.faq-item`, same markup as index.html) AND a matching
  `FAQPage` JSON-LD block in `<head>` — Google renders these as expandable
  rich results. Insert the section before `<section class="section cta-band">`;
  inject schema before `</head>`. Write questions as buying-keyword queries
  ("What is the FMS-1650 isolation room controller?"). For Arabic use
  `json.dumps(..., ensure_ascii=False)` so JSON stays readable RTL. ~4–5
  questions/page; verify with `grep -c 'faq-item'` + `grep -c 'FAQPage'`.

### Layer 2 — Search Console + analytics ($0, ~30 min)
- Google Search Console: **HTML-tag verification split** — agent CANNOT do the
  Google login; user adds URL-prefix property (`https://<site>.pages.dev`),
  chooses "HTML tag", pastes the tag to the agent, agent injects + deploys,
  user clicks Verify; then submit sitemap.xml. Tell the user exactly this
  split so they don't stall waiting for you.
- **Cloudflare Web Analytics is the zero-code option for Pages sites** — user
  logs into dash.cloudflare.com → Analytics → Web Analytics → Add a site →
  Enable; Cloudflare's proxy auto-injects, no snippet needed. Do NOT try the
  RUM API with the wrangler OAuth token (verified: 401 — OAuth token only
  serves wrangler endpoints; RUM needs a real API token). Plausible/GA4 are
  fallbacks when the user has no CF dashboard access.
- **NO dashboard login available at all ("khud karlo")?** Build the
  self-hosted KV analytics (no cookie, no login, live JSON stats endpoint):
  full recipe + ready code `references/self-hosted-analytics-kv.md`. PITFALL:
  first deploy 404s on `/api/*` ("Uploaded 0 files") — redeploy once more and
  it prints "✨ Uploading Functions bundle", then endpoints work.
- **After user pastes the verification tag:** inject into ALL pages EN+AR via
  `scripts/add_gsc_verify.py <content-token>` (site-local copy works too),
  deploy, curl-verify the tag is live on both `/` and `/ar/`, then tell user
  to click Verify. Sitemap submit direct link (skips UI hunting):
  `https://search.google.com/search-console/sitemaps?resource_id=https://<site>.pages.dev/`
  — user pastes `sitemap.xml` there.
- **Speed up indexing:** after Verify + sitemap submit, have the user open
  URL Inspection (top search bar), paste the homepage URL, click **Request
  Indexing** — drops time-to-index from ~3–7 days to ~24–48h. Expectations to
  set: main pages 3–7 days, all pages + rich results 1–2 weeks. New sites NOT
  showing in Google in the first days is normal — don't treat as an error.
- **Canonical/sitemap consistency check (do before submitting):** sitemap
  URLs, `<link rel="canonical">`, and hreflang alternates must all reference
  the SAME URL form (e.g. `products.html`). Extension-less URLs (like
  `/products`) that resolve 200 should canonical to the `.html` version — a
  mismatch sends Google duplicate-signal noise. Verify with a script: list
  sitemap `<loc>`s, grep canonical+hreflang from live pages, diff. 404.html
  intentionally absent from sitemap = correct.
- Do after OG/domain fixes so nothing in the sitemap 404s

### Layer 3 — Custom domain (~$10–15/yr + attach time)
- `.pages.dev` CAN rank but custom domain = trust + brand authority
- Attach to Cloudflare Pages, then flip OG/canonical tags BACK to the real
  domain (see og-preview-debugging.md note — tags are per-deploy)

### Layer 4 — Local & authority (free, ongoing)
- Google Business Profile (hospitals/contractors "near me" searches) —
  usually needs the client's phone for verification
- Industry directories, citations, LinkedIn posts (draft in EN, hooky CTA)

## 3. Presentation to user
- Audit table first (what's already strong — builds trust)
- Offer layers 1+2 as immediate free work; layer 3 "when traffic proves it";
  layer 4 ongoing. Ask which to start — don't build everything unprompted.
