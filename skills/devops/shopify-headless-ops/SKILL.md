---
name: shopify-headless-ops
description: "Use when Shopify app/admin access chahiye headless VM pe."
version: 1.0.0
author: hermes
license: MIT
metadata:
  tags: [shopify, oauth, webhooks, headless, devops]
  related_skills: [shopify-whatsapp-bot]
---

# Shopify Headless Ops

Shopify integration on headless servers (no GUI browser): token types, OAuth flows that work without a browser, CLI 4.x pitfalls, webhook registration. Companion to `shopify-whatsapp-bot` (bot architecture) — this one is auth + plumbing on servers.

## When to Use

- Shopify app/admin access chahiye headless VM pe (no browser available).
- Webhook register karna ho, token validate karna ho, ya CLI auth flow me atke ho.
- User ke `.env` me Shopify tokens ho aur admin API 401 de raha ho.

## Token type prefixes (CRITICAL — 1-second check)

| Prefix | Type | Use |
|---|---|---|
| `shpat_` | Admin API token (custom app) | Admin REST/GraphQL — owner ops |
| `shpca_` | Client credentials token (new app flow) | Admin API, **no browser OAuth — headless-friendly** |
| `shpss_` | Storefront token | Public storefront ONLY — **cannot call admin API** |
| `shppa_` | Private app token | Legacy |

**Pitfall:** a `.env` var named `SHOPIFY_ADMIN_TOKEN` may actually hold a `shpss_` storefront token → admin API returns 401/exit. Always check the prefix before trusting the var name. `.env` me `shpss_` = storefront, `shpat_`/`shpca_` = admin-capable.

## Auth on headless VM — what works

### 1. Client credentials grant (BEST — no browser, no redirect)
New app flow (`use_legacy_install_flow = false` in shopify.app.toml):
```
POST https://<store>.myshopify.com/admin/oauth/access_token
{ grant_type: "client_credentials", client_id, client_secret }
→ { access_token: "shpca_..." }
```
Requires: app **installed on the store** + client_id AND client_secret. The secret is NOT the client_id — user's "API secret key" is often actually the Client ID; verify in the app's **API credentials** tab.

### 2. CLI `store auth` — DO NOT use on headless VM
- `open` npm package ignores BROWSER env; xdg-open hijack (`/usr/bin/xdg-open` → fake script writing `$1` to /tmp/auth-url.txt, original backed up to `.real`) CAN capture the authorize URL.
- BUT PKCE callback redirects to `http://127.0.0.1:<port>/auth/callback` — that lands on the **USER's device**, not the VM. Callback always times out. **Abandon this flow headless.**
- After hijack: restore with `sudo mv /usr/bin/xdg-open.real /usr/bin/xdg-open`.

### 3. Grant/install verification
- Admin URLs (admin.shopify.com/...) return 403 from the VM without a session — normal, not a failure. Completion only confirmable by the user or via API.
- Authorize URLs with state/code_challenge are ONE-TIME — expired after a missed callback, never reuse.

## Shopify CLI 4.x facts
- `app webhook subscribe` does NOT exist; webhooks live in `shopify.app.toml` → `[[webhooks.subscriptions]]` (topic + endpoint URL) and sync via `app deploy`.
- `app deploy` flow: org select → "(n) Connect to existing app" → pick existing app → releases get sequential names (`luxewave-2`, `luxewave-3`).
- `app info` (install URL), `config link --store`, `app dev` (no dev store) fail/hang — don't rely on them.
- Org/store discovery works: `organization list`, `store list --organization-id <ID>`.
- Keep `api_version` in toml aligned with the handler (e.g. 2026-07); scopes via `[access_scopes]`.

## Webhook registration
- Scopes via `[access_scopes]` in toml (`read_orders, write_orders, read_products, read_customers`) — deploy to sync.
- Webhook HMAC secret = the app's API **secret key**, NOT client_id. If the handler verifies with client_id, real Shopify webhooks will fail HMAC.
- HTTPS endpoint required — Cloudflare tunnel works.
- **Tunnel longevity:** cloudflared quick tunnels get a NEW random URL per restart — registered webhook addresses go stale. Run with `--protocol http2` (QUIC can stall on locked VMs) and `--logfile /tmp/luxewave-tunnel.log` so the URL is greppable. A silent no_agent cron every 5 min should: ensure handler+tunnel processes alive, compare each webhook's registered address vs the live URL, and PUT-update when changed (working pattern: `/home/ubuntu/clients/luxewave/watch_webhook.sh`).
- **Verify before trusting live delivery:** HMAC secret = API secret key (32-hex, `shpss_`-labeled in newer apps). Test locally — POST the real payload shape to the tunnel with `X-Shopify-Hmac-Sha256` = hex HMAC-SHA256 of the raw body; 200 = pipeline good. (REST `POST /webhooks/{id}/test.json` can return 406 on some versions.)

## Scratch store build via Admin API (REST + GraphQL)

Full store build (products, collections, images, SEO) from a valid `shpat_` token — works without theme/pages access. Full recipe + PIL brand-tile generator pattern: `references/admin-api-store-build.md`.

- **Granted-scope probe:** `/admin/oauth/access_scopes.json` may return empty — probe by calling endpoints. With ONLY product scopes these work: products, variants, images, smart/custom collections, metafields, and GraphQL `productUpdate(seo:)` / `collectionUpdate(seo:)`. Pages (`write_content`), themes (`write_themes`), discounts (`write_discounts`), menus (`write_menus`) return 403 without their scope. Adding scopes is admin-only: Configure Admin API scopes → Save → Install app → NEW `shpat_` token (ask user to resend).
- **Image upload = base64 attachment, no multipart:** `POST /products/{id}/images.json` `{image: {attachment: <b64>, filename, position}}`; collection covers via `PUT /smart_collections/{id}.json` `{smart_collection: {image: {attachment}}}`. This product-image path has NO 2048-char limit (that cap is only GraphQL `fileCreate` data-URIs) — multi-MB JPEGs upload fine as base64.
- **Verify what images are actually on products:** fetch `/products.json` and read each `images[0].src` — generated tiles vs real product photos are distinguishable by filename (`tiles/...` or `*-tile.jpg` = placeholder, real client photos have their own names). "Photos sahi add nahi hue" usually means tiles/placeholders are live, not that upload failed.
- **Client media intake (zip/Drive → product photos):** clients send a zip that contains PDFs (catalogue, price list, brochures) — product photos live INSIDE the catalogue PDF, not as standalone files. Extraction recipe: `pdfimages -all cat.pdf out` dumps embedded images but they're usually 1–8KB thumbnails (useless for "best resolution"); instead render pages `pdftoppm -jpeg -r 150 -f 1 -l N in.pdf page` → ~1772x1182 px page renders to crop from. If the catalogue is a design-guide (bottle shapes, SKU codes, no real shots — check via tesseract OCR), tell the user originals are needed. Full flow: `references/client-media-intake.md`.
- **Drive folder intake:** `gdown --folder <url>` works for PUBLIC ("Anyone with the link") folders without any auth. 401 from gdown = folder is private → don't fight it; ask the user to either flip sharing to "Anyone with the link" or upload files directly to the chat (fastest). rclone tokens expire — check `rclone config show` token expiry and don't assume a stale token works.
- **Password-page detection (trial/new stores):** root → `/password` (302) and `/products.json` → 401 means storefront locked; products ARE published but invisible. Live launch = user removes password + picks a plan (both admin-only).
- **Pitfall — Shopify auto-slugs digit boundaries:** "Body Lotion 20ml" → handle `body-lotion-20-ml` (dash between digits and letters). Never match local files to products by guessed handle — fetch products and match by EXACT title.
- **Pitfall — pagination loops lie:** a `page=` loop that treats empty/error as end returns "0 products" while `/products/count.json` says 33. For <250 items skip pagination: single `GET /products.json?limit=250`.

## Horizon theme branding via Admin API (write_themes)

Horizon (Shopify's default free theme) is fully brandable headless: colors in `config/settings_data.json` (`current.color_palette`: background/foreground/color1/color2), header/footer composition in `sections/header-group.json` / `sections/footer-group.json`, logo render in `blocks/_header-logo.liquid`, homepage in `templates/index.json`, sitewide injects in `layout/theme.liquid` (before `</body>`). PUT binary assets with base64 `attachment`, JSON assets with `value`.

- **image_picker settings accept ONLY `shopify://shop_images/<filename>`** — NOT `assets/...` paths (422 "must be a valid shopify url") and NOT CDN URLs (422 "does not point to an applicable resource"). The value passes validation but renders broken if the file isn't in Files.
- **Files upload is capped:** GraphQL `fileCreate` `originalSource` data-URI max **2048 chars** (big logos fail: "originalSource is too long"); REST `/files.json` can 406 outright. Two workarounds: (a) logo → patch `blocks/_header-logo.liquid` to render `{{ 'logo.png' | asset_url }}` in a `{% else %}` branch when `settings.logo` is blank; (b) hero → reuse an image ALREADY in Files — product images ARE Files entries, derive `fname = src.rsplit('/files/',1)[1].split('?')[0]` → set `image_1` = `shopify://shop_images/<fname>`.
- Horizon sections render `render 'contrast-override', background_color: section.settings.background_color` — dark `background_color` (navy) auto-flips text white, so navy header/footer/announcement bars are safe without explicit text-color settings.
- Menus: `menuDelete` refuses Shopify's auto-created defaults ("Default menu cannot be deleted"); `menuUpdate` takes **TOP-LEVEL args** `(id, title, handle, items)` — no input object (MenuUpdateInput doesn't exist; `menu:{...}` → "missing required arguments"); `Menu` has no `itemsCount` field. Correct flow: overwrite the default `main-menu`/`footer` with your items (the theme references those handles), then delete your own duplicates.
- `read_collections` scope can be missing even with products granted (collections REST → 403) — use products for image URLs.
- **Footer/global text typography lives in `sections/footer-group.json`** → `sections.<id>.blocks.<block_key>.settings`. Blocks can be NESTED one level inside a `group` block (`blocks.group_H6VpwJ.blocks.text_LWt8Pz`) — a top-level key lookup raises `KeyError`; walk nested `blocks` dicts. Fix a "fonts bohot large" complaint by setting `type_preset` + explicit size: `"type_preset":"custom"`, `"font":"var(--font-body--family)"` or `"var(--font-heading--family)"`, `"font_size":"1.125rem"` (18px, sub-heading) / `"0.875rem"` (14px, body), `"line_height":"normal"`, `"letter_spacing":"normal"`, `"case":"none"`. `blocks/text.liquid` schema allows `rte|paragraph|h1..h6|custom`; **custom is the only preset that honours `font_size`**. A text block left on `h2` renders ~2–3× body size — the usual culprit (inline `<h2>`/`<h3>` tags inside the text compound it: strip them).
- **PITFALL — theme asset PUT 422 `Setting 'text' is invalid`:** rich-text values need a tag on EVERY top-level node (`<p>…</p>`, `<ul>`, `<h2>`); a bare string (`"Join our email list"`) is rejected (`All top level nodes must be 'p'…`). `<a href>`, `<strong>`, `<br>` inside `<p>` are all fine. When a multi-block PUT 422s you can't tell which block — test one block per PUT.
- **Removing contact details sitewide = grep the theme assets, not the homepage:** loop `.json`/`sections/`/`blocks/`/`templates/` assets for the string, patch where it lives, then re-grep for 0 hits AND confirm the live page HTML has 0 hits. A `footer-group.json` edit propagates to every page instantly, no rebuild.
- **QA the RENDERED result, not the JSON:** `connect_over_cdp` + `page.locator('footer').screenshot()` at 1440 and 390 widths. Scan the DOM **after scrolling to the footer** — Horizon defers off-screen sections (`content-visibility`), so a pre-scroll `innerText` scan reports footer text as MISSING (false negative that looks like the edit failed). Good output: `Join our email list → 18px | P`, body lines `14px | P`, `email_in_dom: false`, and the `wa.me/…` href present. Convert plain `WhatsApp: <number>` text to a real `<a href="https://wa.me/9665…">` link while you're in there.
- **Automation Chrome is NOT auto-started after a gateway/VM restart** — CDP `:9333` dies and Playwright then throws `connect_over_cdp` timeout or `net::ERR_ABORTED` on goto. Relaunch with `DISPLAY=:99` exported (Xvfb socket `/tmp/.X11-unix/X99`), else Chrome exits `Missing X server or $DISPLAY`. Do NOT `pkill -f "user-data-dir=/…chrome-automation"` — the pattern matches your own shell's command line and kills the session (exit -15); use `pgrep -f 'chrome-auto[m]ation'`.
- Full recipe + JSON shapes: `references/horizon-theme-branding.md`.

## Draft-theme staging, preview QA & "top section looks fake"

- **Duplicate a theme via GraphQL, never REST:** `POST /themes.json {src: <theme_id>}` → 422 (`src` must be a URL). Use
  `themeDuplicate(input:{sourceThemeId:"gid://shopify/OnlineStoreTheme/<live_id>", name:"..."})` → returns the new gid
  (strip the prefix for the numeric `preview_theme_id`). Always duplicate the LIVE theme fresh for the current change —
  a preview id remembered from an earlier session is a stale copy that silently misses assets uploaded since.
- **`?preview_theme_id=<id>` renders in a BROWSER only:** the homepage returns **0 bytes** to curl unauthenticated
  (product pages with the same param DO return HTML). QA staged design work with Playwright/DISPLAY=:99 + CDP `:9333`,
  screenshot 1440 + 390 widths, then vision-audit the PNGs. An empty curl is NOT "staging failed".
- **Regression grep the staged theme before publish:** on a staged product/cart page confirm the WhatsApp CTA is still
  there and `checkout` / `at checkout` counts are still 0 — a design stage must not undo the order-routing changes.
- **Publish = GraphQL `themePublish`, then re-verify LIVE (never the preview URL):**
  `mutation { themePublish(id: "gid://shopify/OnlineStoreTheme/<id>") { theme { id role } userErrors { message } } }`,
  confirm with `{ themes(first: 10) { nodes { id name role } } }`. The stage becomes role `MAIN`; the previous live
  theme flips to `UNPUBLISHED` and stays in the list as a **one-click rollback** (`themePublish` it back) — say so to
  the user instead of pre-emptively backing it up. After publishing, re-run every check **without** `?preview_theme_id`
  on the real storefront: hero `<video>` `paused:false` + `currentTime>0` at 1440 **and** 390, new logo served from the
  bumped theme-asset path (`t/3/assets/...`, was `t/1`), hero image 200, footer `Website:` link present, product page
  "Order on WhatsApp" ≥ 1, and `checkout` / `at checkout` counts = 0. Re-runnable probe:
  `scripts/qa_theme_publish_check.py`.
- **Portrait-only hero video on desktop = native-size CARD, not hidden and not stretched:** when the store's only video
  rendition is portrait (404×720), full-width desktop play = ~3.5× upscale = the "fake/blurry" complaint. Give the
  section a 2-col grid (`grid-template-columns: minmax(0,1fr) auto`, gap ~46px), copy in the flexible column, and the
  portrait `<video>` in a right-hand card (`aspect-ratio:9/16; height:min(68vh,600px)` ≈ 336px wide, so the 404px source
  *downscales* = sharp), over a landscape photo + navy gradient scrim; let the SAME `<video>` go full-bleed below 899px.
  If the card lands on the LEFT, that's DOM order (the element is first in the markup), not a CSS bug.
- **Autoplay QA needs JS state, not a screenshot:** a paused/black `<video>` and a playing one look identical in a PNG.
  Assert via `page.evaluate`: `paused === false && currentTime > 0`, plus `videoWidth/Height`, `readyState`, `error`.
- **Text-presence checks: grep `innerHTML` (or a `fetch()` of the HTML), not `innerText`.** On a live homepage,
  `document.body.innerText` omitted the footer `Website: <url>` link (deferred/hidden section) while
  `document.documentElement.innerHTML` contained it twice — an innerText-only check reports a working edit as missing.
  Use innerHTML for *presence*, innerText only for *rendered/visible* readings.
- **Theme-asset blobs: build the big custom-liquid section in parts.** A full hero (CSS + markup + inline JS) is too big
  for one `write_file`/PUT — write chunk files (`lw_cssA..E.html`, `lw_bodyA..C.html`), assemble
  `cat lw_css*.html lw_body*.html > /tmp/hero.html`, sanity-check `wc -c` + `grep -c` on a key class, then PUT the
  assembled contents. Iterating = patch one chunk, re-`cat`, re-PUT.
- **"Empty / boring / fake" is an ASSET problem, not a copy problem — diagnose before rewriting copy.**
  (a) Download the live logo file and compare its pixel size to the box it renders in: a 1000x240 asset rendering at
  ~180x44 is a 4x downscale, so a mark-only logo with micro-text baked in reads as an empty header ("brand naam hi nahi").
  (b) Check the hero media's native resolution + aspect: a 404x720 portrait rendition stretched to 1440px desktop is a
  ~3.5x upscale — that IS the blur the user calls fake. Fix = logo lockup drawn for its box (mark + wordmark, sizes that
  survive the downscale) and a responsive hero (sharp landscape image on desktop, the store's native portrait video on
  mobile). Then self-QA with vision on the rendered screenshots and hand the user a preview URL — don't ask them to check.
- **Linking the store to its external brand site (both directions):** store→site = a footer text block link (nested
  `blocks` in `sections/footer-group.json`); site→store = patch the site repo's `index.html` (nav "Shop" CTA + hero
  "Shop Online" button → `https://<store>.myshopify.com/`) — a plain `Website: <url>` line reads as bolted-on. Before
  promising anything live, verify HOW the site deploys: if an asset is live but absent from the repo, deploys are manual
  (`netlify deploy`), so a git push alone publishes nothing → ask the user for a Netlify token or run `netlify login`.
  Don't hunt for `nfp_` tokens by grepping the whole home directory (times out, finds nothing).
- Full workflow (logo lockup reasoning, hero prompts, Files-CDN upload, cross-link + deploy gate):
  `references/storefront-hero-and-logo-rebuild.md`.

## Store launch state, plan & rename (one-shot probes)

`GET /admin/api/<ver>/shop.json` gives launch state in ONE call: `name` (display name), `plan_display_name` / `plan_name` (tier — "Advanced"/"unlimited" etc.), `country_name`, `currency`, `password_enabled` (`false` = storefront public), **`taxes_included`** (`true` = "All prices include tax"). Cross-check live: `GET /products.json` → 200 = public, 401 = still locked.

- **Tax settings + store address are ADMIN-UI-ONLY — API 406.** `PUT /admin/api/<ver>/shop.json` with `taxes_included: false` (VAT disable) OR address fields (`address1`/`city`/`zip`) → **406 Not Acceptable** (same read-only wall as rename). The `shop` resource update endpoint refuses these outright; there is no GraphQL tax mutation either. Only route = browser UI (Settings → Taxes and duties → region → deactivate VAT / uncheck "All prices include tax"; Settings → General → Store details → address). Read current state via `shop.json` `taxes_included` — that part IS readable.
- **Shopify Admin browser login is Cloudflare-walled from VMs** (proven 2026-08-22): `accounts.shopify.com` shows "Just a moment" Turnstile; clean UA + `--disable-infobars` GUI Chrome + real checkbox clicks did NOT pass from a datacenter IP (Oracle VM). Plan for **user-assisted login** (Google account / OTP step by the user, then drive the visible session) or have the user run the 30-second tax/address UI change themselves. Don't burn hours on the Cloudflare wall — full escalation ladder in `headless-browser-automation` skill.
- **API cannot rename the store:** no `shopUpdate` GraphQL mutation exists (probe mutation type fields → only shopLocale*/shopPolicyUpdate/...) and REST `PUT /shop.json` → 406. Admin-only, period. Theme workaround for the STOREFRONT: patch `snippets/meta-tags.liquid` (og_title/og_description/site_name/title — assign `page_title_display = page_title | replace: shop.name, 'Luxe Wave'`; title suffix guard `unless page_title_display contains 'Luxe Wave'`), `blocks/footer-copyright.liquid` (`{{ 'Luxe Wave' | link_to: routes.root_url }}`), `sections/header.liquid` (JSON-LD `"name": ... | json` + visually-hidden h1). Checkout + order emails still show real shop.name — final 30s admin rename needed there. Shopify-injected `initData:{"shop":{"name":...}}` in content_for_header stays old — internal JS, not user-visible.
- **Store rename pitfall:** Settings → Store details has TWO name fields. **Store name** = display name (checkout, emails, receipts, browser `<title>`); **Business entity** = legal name "used for financial products, markets, apps, and taxes". Users routinely edit Business entity and think the store is renamed — the display name stays the old one. ALWAYS verify a rename via `shop.json` `name` + storefront `<title>` before telling the user it's done. Rename never changes the myshopify URL.
- **Plan-tier leverage cheat:** Advanced ($399) differentiators = 0.6% 3rd-party payment fee, **Shopify B2B wholesale (Advanced/Plus only)**, Markets multi-currency + 2 languages, advanced report builder, live 3rd-party shipping rates, up to $8k Shopify credits, 15 staff. B2B/wholesale route justifies Advanced; low-volume retail → downgrade Shopify ($105)/Basic ($39). Full playbook: `references/store-launch-leverage.md`.

## Product videos, homepage video hero, theme-asset galleries

- **Video → product media (canonical flow):** `stagedUploadsCreate` → PUT bytes to signed URL (204) → `productCreateMedia(media: [{originalSource: <staged resourceUrl>, mediaContentType: VIDEO}])`. **NEVER call `fileCreate` first** — it registers the video and `productCreateMedia` then fails with `Duplicate external_video_id`. `productUpdateMedia` is an update, not an attach (no-op). Payload fields are `media` + `userErrors` (`mediaErrors` doesn't exist); input field is `mediaContentType` (`mediaType` doesn't exist). Proof of attach = product's media list, not Video status READY.
- **Homepage video hero:** Horizon's hero `video_1` setting rejects every URL form (CDN → "not applicable", `shopify://videos/<...>` → "must be valid"). Use a **`custom-liquid` section with raw `<video>` HTML** instead — no validation. Setting key is `custom_liquid` (not `liquid`). Overlay text needs `position:relative` on the wrapper or it floats against the page (overlap bug). Remove the old image `hero` section when adding a video hero — two heroes stack/overlap.
- **Swap hero video later (no re-creation):** the hero is `templates/index.json` → `sections.<id>.settings.custom_liquid`. Replace the old `src` (regex `//<store>.myshopify.com/cdn/shop/videos/c/vp/[a-f0-9]+` or the full mp4 URL) with the new one, PUT the whole index.json with `value` (JSON assets take `value`, binary take `attachment`). Verify via storefront HTML grep for the new fragment. GET vs PUT response shapes differ — don't unpack both as the same tuple.
- **Pick the LIGHTEST rendition for hero:** Shopify auto-makes 3–4 renditions (270x480 / 404x720 / HD-720p / HD-1080p, 1.6–4.8 Mbps). A 1080p 4.8Mbps hero "stills" on mobile data — user complains. Use **HD-720p (~1.6Mbps)** in the hero `<video>`; keep 1080p only for product pages. For KSA hospitality clients an **Arabic-voiceover video in the hero** is the attraction hook (fetch from the product whose media carries it via the GraphQL media query, then use its `sources[].url`).
- **Hero sound = muted autoplay + one-tap unmute button:** browsers block autoplay WITH sound everywhere (WhatsApp browser included), so the hero must start `muted`. User asked "sound nahi ayega?" — add a small overlay button whose onclick toggles `video.muted`. This is the standard hotel/luxury hero pattern; explain the browser rule to the user (it's not a store bug).
- **Theme-asset gallery (ad photos etc.):** `PUT themes/{id}/assets.json` with base64 `attachment` — flat `assets/` keys only (subfolders → 422). CDN `public_url` uses `t/1/assets/` path (the `themes/{id}/assets/` CDN URL 404s) — read it back from the asset GET. URL-encode filenames with spaces.
- **PITFALL — theme-asset URLs (`t/1/assets/`) fail on mobile/WhatsApp browsers:** server-side 200 but user's phone shows alt-text only (image not loading). Gallery ad photos rendered via theme assets = "media dikhai nahi dera" complaint. FIX: migrate images to **standard Files CDN URLs** — GraphQL `fileCreate` accepts a PUBLIC http URL as `originalSource` (no staged upload needed; `stagedUploadsCreate` IMAGE resource has signature quirks). New MediaImage appears with a UUID filename + new `?v=` timestamp; match by timestamp or UUID pattern `8-4-4-4-12`. Standard URLs are `cdn.shopify.com/s/files/1/<shop>/files/<uuid>.jpg` — these load on every browser.
- **Verifying videos are LIVE on product storefront pages (false negatives):** Admin-side proof = GraphQL `products(first:100){nodes{title handle media(first:10){nodes{mediaContentType status ... on Video{id sources{url format height width}}}}}}` — `status: READY` + sources = attached & processed. **Do NOT reuse product IDs from older sessions for `/products/{id}/media.json` — stale IDs 404.** Re-fetch and match by title. Storefront-side: `products/{handle}.json` **always returns `media: []`** (the JSON endpoint omits media — a false negative, NOT proof of missing video). Instead fetch the rendered product page HTML and regex `//<store>.myshopify.com/cdn/shop/videos/c/vp/[a-f0-9]+` — video URLs render **protocol-relative**, so a `https://cdn.shopify.com/videos/...` pattern matches NOTHING and falsely reports "no video". One match = one rendered video player. Shopify auto-generates 3–4 renditions per video (270x480 / 404x720 / HD-720p / HD-1080p); `sources[].url` uses the full https CDN form.
- Full working recipes + dead-end table: `references/product-video-and-media-upload.md`.
- Post-stage / post-publish QA probe (video playback state, copy presence, checkout-CTA counts, desktop+mobile shots): `scripts/qa_theme_publish_check.py`.

## Shipping rates, payments, fulfillment & order monitoring (verified 2026-09-20)

The post-launch half of a store: money in (payments), goods out (shipping/fulfillment), and
knowing an order happened at all. Full recipes + observed API results: `references/shipping-payments-fulfillment.md`.

- **Free shipping without `write_shipping`:** use `discountAutomaticFreeShippingCreate` (automatic
  discount, no minimum, `destination.countries.add: ["SA"]`, `combinesWith: {productDiscounts, orderDiscounts}`
  ONLY — all-three-true → `INVALID_COMBINES_WITH_FOR_DISCOUNT_CLASS`; `appliesOnOneTimePurchase` invalid
  unless subscriptions; connection field is `automaticDiscountNodes`). Edits the RATE is 403 without the scope;
  the discount is the API-doable route and it works on real orders.
- **Never report shipping from a REST read.** `GET /shipping_zones.json` returned 200 with a zone and
  *zero rates* while a live `قياسي SAR 25.00` rate existed. Ground truth = a real checkout: cart permalink
  `https://<store>.myshopify.com/cart/<variant_id>:1` driven by Playwright
  (`connect_over_cdp("http://127.0.0.1:9333")`, venv `/home/ubuntu/.venvs/playwright/bin/python` shows
  the rate, the FREE SHIPPING discount line, and `Shipping SAR 0.00`).
- **Sellable countries = enumerate the checkout `select[name="countryCode"]` options.** A zone can list 28
  countries while checkout offers only `SA` — that selector is the customer-facing truth.
- **Payments are UI-only, and Shopify Payments does NOT support KSA merchants.** Recommend third-party
  gateways (Moyasar/Tap/PayTabs/HyperPay) + Tabby/Tamara, or COD/bank-transfer manual methods; mention the
  third-party transaction fee. Policies (refund/shipping/ToS) are needed for gateway approval and
  `shopPolicyUpdate` is 403 without `write_legal_policies`.
- **Fulfillment automation needs its own scopes** (`read/write_merchant_managed_fulfillment_orders`,
  `read/write_fulfillments`) — without them a paid order stays `unfulfilled` and tracking can't be pushed.
  Courier lanes for KSA: SMSA/Aramex/SPL/Naqel direct, aggregators Torod/OTO; self-delivery = manual fulfil
  + COD cash. Prereqs = client CR + IBAN + carrier account; payout starts ~15–20 orders/day.
- **Order monitoring — don't build it on IMAP.** A Gmail watcher on the store's own address only sees orders
  whose customer used that address (customer confirmation ≠ merchant alert). Right lanes: Shopify admin/mobile
  app, Settings → Notifications for merchant email, and webhooks — but **`curl` the registered webhook address
  first**: a live-looking store can have subscriptions pointed at a dead `*.trycloudflare.com` quick tunnel
  (`000` = orders alert nowhere). Prefer a Cloudflare Worker receiver (HMAC + Telegram) over a tunnel; until
  that exists, a 5-minute `no_agent` cron polling `orders.json` with a state file gives silent-until-delta
  alerting (pattern: `cron-watchdog` skill, "state-file delta poller" variant).

## Reading user screenshots without vision tools
`tesseract <img> stdout` — OCR user-sent screenshots (Shopify dashboard states, grant pages, app lists) to confirm what the user sees. Small screenshots (300px-ish) OCR garbled → upscale 4x with PIL LANCZOS first (`im.resize((w*4,h*4), Image.LANCZOS)`), retry `--psm 4` / `--psm 6` when default output is noise.

## Verification
- `curl -s -o /dev/null -w "%{http_code}"` on admin URLs — expect 403 (session required), don't read as failure.
- Check token format first: `grep -oE '^[A-Z_]+=' .env` for var names; `sed 's/\(=.{6}\).*/\1.../'` for redacted prefix check.

## Project references
- `references/storefront-hero-and-logo-rebuild.md` — rebuild a "fake/empty" storefront top section (logo lockup sized for its render box, responsive hero media, draft-theme preview QA) and cross-link the store with an external brand site (deploy-linkage check).
- `references/whatsapp-order-routing.md` — route orders to WhatsApp and de-couple checkout from any gateway: exact files/anchors in Horizon (`blocks/accelerated-checkout.liquid`, `blocks/buy-buttons.liquid`, `snippets/cart-summary.liquid`), wa.me prefilled-message Liquid, staging-theme preview gate, marker-based QA loop, and why gateway settings can ONLY be changed in the admin UI.
- `references/luxewave-setup.md` (payment/payout questions → `references/payment-gateway-forensics.md`: read the merchant payee, payer, fee and free-shipping proof out of `OrderTransaction.receiptJson`) — Luxewave (KSA hospitality supplier) Shopify store build state: real store domain vs fake ones, app client_id, creds/asset paths, brand/product facts, stale-webhook warning, ghostscript PDF→image extraction (poppler absent).
- `references/store-launch-leverage.md` — plan-tier leverage playbook (Advanced vs Shopify vs Basic; B2B/Payments/Markets/reports/shipping/credits), store rename pitfall, one-shot launch probes.
- `references/shipping-payments-fulfillment.md` — scope→capability map (what's 403/406 vs doable), automatic free-shipping discount recipe + `combinesWith` pitfalls, live-checkout verification recipe, KSA payment options, fulfillment scopes + courier automation lanes, order-monitoring lanes (IMAP trap, dead-webhook check, polling fallback).
