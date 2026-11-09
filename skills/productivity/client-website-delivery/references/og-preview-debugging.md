# LinkedIn/Social Link Preview Debugging (OG tags)

Symptom: client pastes `https://site.pages.dev` into a LinkedIn post (or
Post Inspector) and **no card preview appears**, even though `<meta og:*>`
tags exist.

## Root causes (in order of likelihood)

1. **OG tags point at a domain that isn't live yet.** When the site is on
   `<project>.pages.dev` but the build's OG/canonical tags reference the
   planned custom domain (`https://avvs-triatek.com/`), LinkedIn's crawler
   follows og:url → nothing resolves → no preview. Fix: point OG tags at
   the ACTUAL live URL (`.pages.dev`) until the custom domain is attached.
2. **Stale domain in non-HTML files.** `robots.txt` Sitemap line and every
   URL in `sitemap.xml` may still carry the dead domain. Crawlers read
   these; LinkedIn (and Google) can fail or index the wrong host.
3. **Image not 1.91:1 or too small.** LinkedIn prefers 1200×630. A logo
   (e.g. 1536×1024) often fails or renders tiny. Generate a proper social
   card.
4. **LinkedIn cache.** LinkedIn caches per-URL previews aggressively; the
   Post Inspector must be re-run, and an already-typed post keeps the OLD
   card — the user must delete the link from the post and paste it fresh.

## Fix workflow

1. **Global domain swap** across ALL files (not just the homepage):
   ```bash
   cd <site> && grep -rl 'old-domain.com' --include='*.html' . \
     | xargs sed -i 's/old-domain\.com/live.pages.dev/g'
   sed -i 's/old-domain\.com/live.pages.dev/g' robots.txt sitemap.xml
   ```
   Also update `og:url`, `og:image`, `twitter:image`, `rel=canonical`.
2. **Generate a 1200×630 OG card** (PIL, brand colors + logo + tagline +
   accent line + URL in footer) → save `assets/img/og-card.png`. See
   `scripts/make_og_card.py` for a reusable generator.
3. **Add dimensions** next to og:image:
   ```html
   <meta property="og:image:width" content="1200">
   <meta property="og:image:height" content="630">
   ```
4. **Redeploy, verify live:** curl with cache-buster
   (`https://site.pages.dev/?cb=$(date +%s)`) and confirm og:url/image
   show the live domain and the card returns 200.
5. **Tell the user the cache dance:**
   - Open https://www.linkedin.com/post-inspector/ , paste URL, Inspect
     2–3 times (async fetch).
   - In an EXISTING post: delete the link, paste it fresh — old card stays
     cached in the draft otherwise.

## Note

When the custom domain later gets attached, re-run step 1 in reverse
(`live.pages.dev` → `www.client.com`) — OG tags are per-deploy, not magic.

## "Cannot display preview" after all fixes = stale failed-fetch cache

If the HTML is verified correct (bot gets 200, card 200, no redirect) but
LinkedIn STILL says "Cannot display preview", LinkedIn has cached the FAILED
fetch of the old dead domain per-URL. Cache-buster: append a query param —
`https://site.pages.dev/?v=2` — LinkedIn treats it as a NEW URL and re-fetches
fresh. Once `?v=2` inspects fine, the bare URL also refreshes. Same `?v=2` /
`?cb=$(date +%s)` trick for curl-side verification.

## Card layout: text/logo overlap breaks the preview

A v1 card with the tagline drawn over the logo renders fine as a PNG but
looks broken in LinkedIn's thumbnail crop. Keep text and logo in separate
x-zones with a clear gap, and verify programmatically:
`python3 scripts/verify_og_overlap.py assets/img/og-card.png`
(gap zone must be ~0 non-background pixels).

## PIL pitfall in the generator

`draw.ellipse([x0, y0, x1, y1])` requires y1 > y0 (bottom edge greater than
top edge). A bottom-left decoration like `[-140, H-100, 20, 60]` crashes with
exit 1 because 60 < H-100. Fix: correct the ordering or drop the decoration.
