---
name: competitor-seo-analysis
description: "Use when client needs SEO gap analysis vs competitors."
version: 1.0.0
author: Hermes + Aamir
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [seo, sitemap, competitor-analysis, client-reports]
---

# Competitor SEO Analysis (Sitemap Gap Report)

Steal competitor SEO strategy via public sitemaps. Proven technique (Deno Hawari method) — every site's sitemap.xml lists all pages = their whole topic strategy.

## Trigger
- Client "mujhe SEO improve karna hai" / competitor research
- New client onboarding (Sanad WordPress audit service)
- Self-audit for AVVS/Luxewave sites

## Workflow (5 min per site)

### 1. Fetch sitemaps — script: scripts/sitemap_probe.py
```bash
python3 scripts/sitemap_probe.py client.com competitor1.com competitor2.com
```
Tries: /sitemap.xml, /sitemap_index.xml, robots.txt → Sitemap: directive.
Output: source, total URLs, page-type breakdown, samples.

### 2. Compare & find gaps
- Page types compare karo (Counter output)
- Gaps = competitor ke pages jo client ke paas nahi:
  - competitor has `blog/`, client nahi → content gap
  - competitor has `services/air-valves/` (deep service pages), client only `services.html` → depth gap
  - competitor has `industries/hospital/`, client nahi → topic gap
- Bilingual check: Saudi clients = /ar/ sections missing = HUGE local SEO gap

### 3. Deliverable — report structure
```
[Client] SEO Gap Report vs [Competitors]
- Sitemap status: client (N urls) vs comp A (N) vs comp B (N)
- Page types table
- Top 5 gaps (ranked by revenue relevance)
- 3 quick wins (fixable this week)
- Upsell hook: "Ye gaps close karne ke liye N content pages + on-page fixes"
```

## Pitfalls
- Sitemap NOT FOUND ≠ no SEO — Netlify/CF Pages auto-generate, WordPress needs plugin (Yoast/RankMath); missing sitemap itself = finding #1
- Some sites block bots (403) — try alternate domains (www, region subdomain)
- Sitemap index → fetch child sitemaps too (re.findall on <loc> gives both, filter)
- Large sites (10k+ URLs): cap analysis at first 500 URLs, note it
- Shopify stores: /sitemap.xml auto-exists (products/collections/pages/blogs)
- Compare same-language only (AR vs EN separately) unless checking bilingual gap

## Verification
- Report me har gap ke saath actual URL cite karo (competitor ka page link)
- Sitemap source URL hamesha report me include karo
