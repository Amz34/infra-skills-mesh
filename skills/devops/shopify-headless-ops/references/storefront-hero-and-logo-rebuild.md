# Storefront top-section rebuild (genuine logo + hero) & store↔brand-site cross-link

Trigger: client says the homepage top looks "empty / boring / fake", or asks to "add this website in the account".
Verified on Luxewave (KSA hospitality, Horizon theme, store `8k6ikq-g6`) 2026-09-21.

## Rules for this client
- Complaint words ("fake", "empty") map to ASSETS, not copy. Diagnose the logo file and the hero media FIRST.
- Self-QA only ("qa urself"): build → screenshot → vision audit → send preview URL + screenshots. Never ask the user to verify a stage.
- Nothing goes live without explicit approval: stage on a DRAFT theme, leave the LIVE theme untouched.
- Client-facing copy = pure English, no people/faces in imagery, never the owner's name.

## 1. Stage a draft theme from LIVE (GraphQL, not REST)
```
mutation { themeDuplicate(input:{sourceThemeId:"gid://shopify/OnlineStoreTheme/<live_id>", name:"<label> <date>"})
  { newTheme { id name } userErrors { field message } } }
```
- `POST /themes.json {"src": <id>}` → 422 (src must be a URL).
- Duplicate the LIVE theme immediately before staging — a `preview_theme_id` noted in an older session is a stale copy that
  silently misses assets uploaded since (real trap: an old preview id rendered with 13 images missing).
- Apply changes to the draft with `PUT themes/{draft}/assets.json` (JSON assets → `value`, binary → base64 `attachment`).
- Verify the draft id is `role: unpublished` and that LIVE is still the `main` role in the same list call.

## 2. Logo: measure the asset before touching styling
- Fetch the live file: `curl -s "<cdn url>?v=<ver>" -o /tmp/l.png`, then `PIL Image.open('/tmp/l.png').size`.
- Downscale factor = source_height / rendered_height. Text thinner than ~40px in a 4x-downscaled source is unreadable, so the
  header looks empty even though a logo IS configured. (Luxewave: 1000x240 asset rendered at ~180x44 held only a mark plus
  micro-text — "brand naam hi nahi", which was the whole "empty header" complaint.)
- Rebuild a lockup FOR the box: mark + horizontal wordmark, transparent PNG ~1000x240, wordmark ≥110px tall so it survives 4x.
  Verify the RENDERED header in a screenshot (vision), never the file preview.
- If `settings.logo` is blank, Horizon can render a theme asset instead (`blocks/_header-logo.liquid` `{% else %}` branch,
  `{{ 'logo.png' | asset_url }}`) — but Files CDN URLs are preferred for mobile reliability.

## 3. Hero: match media to the viewport
- Blur root cause in this pattern: a portrait rendition stretched full width (desktop was showing a 404x720 rendition at
  1440px ≈ 3.5x upscale). Confirm the native size in the rendered HTML instead of trusting a visual hunch.
- Desktop = sharp landscape still (1600x900); Mobile = the store's own native 9:16 video. Don't force one asset family on both.
- Generate stills with fluxgen (`~/projects/flux-api`, `--preset hero`): marble/linen + white towels + amber amenity bottles,
  no people, no text/watermark; palette navy `#0B1B3D` + gold `#C9A45C` to match the logo.
- Copy: benefit headline (not the brand name repeated), exactly 2 CTAs (Shop + WhatsApp bulk enquiry), one trust line (hotels
  served / KSA-wide delivery / WhatsApp confirmation).
- Upload path: `stagedUploadsCreate` → PUT bytes to the signed URL (204) → `fileCreate(originalSource: <resourceUrl>)` → poll the
  file node → use the returned `image.url` (with `?v=`). Avoid `t/1/assets/` URLs for anything customer-facing (mobile failures).

## 4. Preview QA (render it in a browser, don't curl)
- `?preview_theme_id=<draft>` homepage → **0 bytes** unauthenticated; Playwright + CDP `:9333` (`DISPLAY=:99`) renders it fine.
  An empty curl is NOT "the stage failed".
- Shots: desktop 1440 (top + mid gallery + footer) and mobile 390; pair them side by side with PIL and vision-audit each for
  broken images, blank bands, illegible logo, overlapping text.
- Regression grep on the staged product page: `wa.me` / "Order on WhatsApp" present, `checkout` = 0, `at checkout` = 0.

## 5. Store ↔ external brand site cross-link
- Store→site: footer text block, nested `blocks` inside `sections/footer-group.json` (walk nested dicts; PUT the whole JSON).
- Site→store: patch the site repo `index.html` — nav "Shop" CTA + hero "Shop Online" button → `https://<store>.myshopify.com/`;
  a bare `Website: <url>` line reads as bolted-on. QA with Playwright over `file://` before pushing a branch.
- **Deploy gate (learned the hard way):** establish HOW the site deploys before promising liveness. If an asset is live but the
  GitHub repo does not contain it, deploys are manual (`netlify deploy`), so a branch push publishes nothing. Options: a Netlify
  personal access token from the user, or `netlify login` (user clicks the authorise link). Do NOT grep the whole home
  directory for `nfp_` tokens — the scan times out and finds nothing.
- Luxewave specifics: site repo `Amz34/Luxewave-Ksa_Hospitality`; a second copy of the site source sits at
  `/home/ubuntu/clients/luxe-wave/site/index.html`.

## 6. Reporting back (what the user wants)
- Short diagnosis ("logo me brand naam hi nahi", "hero 404x720 stretched to 1440px") → what changed → preview URL →
  screenshots (`MEDIA:` paths) → the 1–2 decisions you actually need (publish? token?).
- Hinglish in chat, English in every artifact.
