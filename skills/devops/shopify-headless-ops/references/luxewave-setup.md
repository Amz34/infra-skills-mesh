# Luxewave Shopify — Store Build State (as of 2026-08-22, post-catalog)

Active project: Luxewave (Luxe Wave Company) store setup, from scratch, headless VM.

## Store & app

- **Store:** `8k6ikq-g6.myshopify.com` — **LIVE + PUBLIC** (2026-08-22: password OFF, plan **Advanced**; shop.json `password_enabled=false`, products.json 200, currency SAR). `luxewave.myshopify.com` is NOT this store (404).
- **Active app:** "Luxe wave- Luxury Hospitality". **Admin API token `shpat_...` VALID** (verified: shop.json 200, 33 products live). client_id `1cf91d2e9659c6c61dfb9d3a377dfca7`; user-labeled "client_secret" is `shpss_f4d0...` (shpss_ prefix — storefront format; webhook HMAC unverified until tested).
- **Creds file:** `~/clients/luxewave/.env` (chmod 600) → SHOPIFY_STORE, SHOPIFY_APP_NAME, SHOPIFY_CLIENT_ID, SHOPIFY_ADMIN_TOKEN. Old app "Hospitality Luxewave" (client_id `c2109c6b...`) NOT installed (401) — stale, don't reuse.
- **Granted scopes (updated):** products, themes, menus, discounts, webhooks — branding/menus/webhooks all done via API. **collections NOT granted** (403). **Store rename status:** Business entity set to "Luxe Wave- Luxury Hospitality" by user (legal name only); **Store name STILL `متجري`** — user must edit Settings → Store details → **Store name** field (NOT Business entity); verify via shop.json `name` + storefront `<title>`.

## Build status (API-driven, this session)

- **33 products** (guest amenities, SAR box prices, EN+AR body, tags) + **7 smart collections** (Guest Amenities, Soaps, Hair Care, Body Care, Amenity Kits, Slippers & Footwear, Room Essentials) — `build_catalog.py`.
- **40 brand tiles** (33 product + 7 collection covers) — navy/gold PIL generator `make_tiles.py`, no-faces-safe, uploaded via base64 attachment (`upload_images.py`, title-matched — handles auto-slug "20ml"→"20-ml" so never match by handle).
- **SEO** — 33 products + 7 collections, EN+AR meta (GraphQL `productUpdate/collectionUpdate(seo:)`, covered by write_products) — `apply_seo.py`.
- Full recipe + pitfalls: `references/admin-api-store-build.md` in this skill.

## Brand facts (from ZIP PDFs)

- Luxe Wave Company — KSA hospitality supplier. CR `7050248579`, Riyadh, +966-574268856 (CORRECT number as of 2026-09-03; older +966 57 426 8856 was replaced storewide — theme announcement/footer/wa links + apply_theme_branding.py already updated; never re-inject574268856), azengineeringapp@gmail.com. Tagline: "Luxury in Every Touch".
- Serves 135+ 4H/5H hotels; certs: GMPC, ISO 9001, SFDA Registered, SASO.
- Product lines: **Guest amenities** (27 SKUs in price list — soaps 15/20/30g, shampoo/gel/lotion/conditioner 10-30ml, dental/shaving/sewing/vanity kits, slippers, loofah, coasters, mouthwash…), **Bed & bath linen** (Oasis line), **Hotel equipment** (trolleys, safes, irons, signage, prayer rugs, Qurans).
- B2B angle: sample pack request, quote requests, bulk tiers, 24h delivery promise.

## Assets

- ZIP source: `~/clients/luxewave/inbox/extracted/Shopify-Luxewave/` (logos, price list, private-label catalogue, company profile, brochures/magazines).
- Catalogue renders: `~/clients/luxewave/assets/products/cat-01..30.png` — ghostscript (`gs -q -dSAFER -dBATCH -dNOPAUSE -sDEVICE=png16m -r120 -o "out-%02d.png" in.pdf`; poppler-utils IS installed as of 2026-08-22 — `pdfimages`/`pdftoppm` available). OCR'd via tesseract → **catalogue is a private-label design guide (bottle shapes, SKU codes), NOT product photos** — hence generated tiles.
- Media intake: zip = PDFs only (no standalone product photos). `pdfimages -all` on catalogue → 511 tiny thumbnails (1-8KB, unusable); `pdftoppm -r 150` page renders → 1772x1182 usable crops. Real product photos PENDING from user — Drive folder `11n2oHfY_Vhg9MvuiYxVuAHA3sGATbijM` is private (gdown 401, rclone token expired) — awaiting public share or chat upload. Full workflow: `references/client-media-intake.md`.
- Brand tiles: `~/clients/luxewave/assets/tiles/*.jpg`; logo `assets/logo-512.png`, `favicon-512.png`.
- Scripts: `~/clients/luxewave/{build_catalog,make_tiles,upload_images,apply_seo}.py`.

## Webhooks (LIVE 2026-08-22)

- orders/create + carts/update → WhatsApp alerts: `~/sanad-site/shopify-webhook/shopify_webhook.py` (:8645, HMAC verify with the real API secret in its `.env`), Baileys bridge :3000, cloudflared `--protocol http2 --logfile /tmp/luxewave-tunnel.log`, watchdog `~/clients/luxewave/watch_webhook.sh` (copy at `~/.hermes/scripts/`) via no_agent cron */5 — re-registers webhooks when the tunnel URL rotates. Pipeline test = HMAC-signed simulated order → 200.
- **STATUS 2026-09-20 — this lane is DOWN:** both subscriptions (`orders/create`, `carts/update`) still point at `https://scheme-bag-carlos-mustang.trycloudflare.com/...` and that quick-tunnel URL is dead (`curl -s -o /dev/null -w "%{http_code}"` → `000`). The user's sample order #1001 alerted NOWHERE as a result. Fix = stable receiver (Cloudflare Worker with HMAC verify → Telegram) rather than another quick tunnel; the API token CAN manage webhooks (create reached payload validation → `422 address: must use a valid domain name`, i.e. NOT a 403 scope error), so once a real endpoint exists the subscription can be created/updated over the API without adding scopes. Interim safety net = the 5-minute `luxewave-order-watch` poller (see Orders above).

## Audit + payments state (2026-09-20)

- **Store name STILL `متجري`** — now confirmed live on the checkout header ("متجري Checkout") and PayPal receipt. `PUT /admin/api/2026-07/shop.json` → **406 (endpoint removed)**; there is no API for store rename → admin only (Settings > Store details > Store name).
- **Payments: ONLY PayPal** at checkout (verified on live checkout) — no mada/card/Apple Pay/BNPL/COD. **Shopify Payments is NOT available to Saudi merchants** (Shopify community requests + KSA guides), so KSA stores need third-party gateways (Moyasar, Tap, PayTabs, HyperPay) + Tabby/Tamara + manual methods. **Admin API cannot enable payment providers at all** — UI-only, and gateway onboarding needs CR + IBAN + KYC. Plan: manual COD + bank transfer first (no docs, paid via Settings > Payments > Manual payment methods), then gateway.
- **PAYOUT VERIFIED 2026-09-21 (from `receiptJson` of order #1001, no admin UI needed):** the PayPal merchant account receiving customer money is **`aamir1zahran@gmail.com`** (`merchant_id GFZYEPDSWUSY4`, buyer-visible brand `متجري`, soft descriptor `PAYPAL *AAMIR1ZAHRA AA`) — i.e. the owner's PERSONAL PayPal, not a Luxewave business account, so client revenue lands in personal funds. Capture `04827803BG3986212` COMPLETED / INSTANT, gross SAR 2.00, PayPal fee **SAR 1.26**, net SAR 0.74 → USD 0.19 (USD-based account ⇒ auto FX). Payer on that order was the owner's own test account `azengineeringapp@gmail.com`. Recommended follow-ups given to the client: PayPal Business in the Luxewave name + matching soft descriptor, and (if cards/mada/Apple Pay are wanted) a KSA gateway — Shopify Payments is unavailable to Saudi merchants. Method + interpretation rules: **`references/payment-gateway-forensics.md`**.
- **Shipping zones:** Domestic = Saudi Arabia with rate `قياسي` SAR 25.00 / 3-5 business days (exists, seen at checkout); International zone lists 28 countries but is **inactive — the checkout Country/Region selector offers ONLY Saudi Arabia** (`select[name="countryCode"]` has 1 option; verified on the live checkout). PITFALL: REST `shipping_zones` returns **empty rate arrays for BOTH zones even though the domestic rate exists** — never conclude "no rates" or "28-country coverage" from REST; verify at the live checkout.
- **All 40 products priced SAR 1.00** (placeholder) — flag before driving traffic.
- **Policies:** only Privacy policy published (no refund/shipping/ToS/contact) — gateway KYC reviews these. `shopPolicyUpdate` → ACCESS_DENIED (`write_legal_policies`).
- **App scopes (22):** products, orders, customers, discounts, price_rules, content, themes, inventory, navigation, analytics. MISSING: shipping, fulfillments, locations, legal_policies, payment → so shipping-rate edits and fulfilment-with-tracking automation are impossible via API. Add in Apps > Develop apps > Configuration (token stays valid for admin-created custom apps).
- **Storefront API token = 401 UNAUTHORIZED** (dead) — any Storefront API integration broken.
- **Orders:** first real order **#1001** (2026-09-20, PayPal, Jeddah, 2 items × SAR 1 = SAR 2.00, `قياسي` SAR 25.00 → **FREE**, `financial_status: paid`, `fulfillment_status: unfulfilled`) — the automatic free-shipping discount proven on a real paid order, not just a probe. **Monitoring lane now live:** `~/ops/luxewave/order_watch.py` + cron wrapper `~/.hermes/scripts/luxewave_order_watch.py`, cron job `luxewave-order-watch` (`*/5 * * * *`, `no_agent`, silent unless a new order / status change), state `~/.local/state/luxewave_order_watch.json`. Alerts land in the chat, so nothing depends on the dead webhook tunnel.
- 1 customer / 8 pages / 1 blog. Horizon theme. Audit deliverable: `~/clients/luxewave/LUXEWAVE_SHOPIFY_AUDIT_2026-09-20.{md,pdf}`.

## Free shipping via API (2026-09-20, live + verified)

Automatic free-shipping discount, id `gid://shopify/DiscountAutomaticNode/1577531113775` ("Free shipping - Saudi Arabia", SA destination, no minimum, `context {all: ALL}`). Needs only `write_discounts`. Replace confirmed live checkout: `قياسي Original price SAR 25.00 / Discounted price FREE`, total shipping SAR 0.00.

```
mutation{ discountAutomaticFreeShippingCreate(freeShippingAutomaticDiscount:{
  title:"Free shipping - Saudi Arabia", startsAt:"2026-09-20T00:00:00Z",
  context:{all:ALL}, destination:{countries:{add:["SA"]}} }){
  automaticDiscountNode{id} userErrors{field message code} } }
```
PITFALLS: `combinesWith` with all three true → INVALID_COMBINES_WITH_FOR_DISCOUNT_CLASS; for the SHIPPING class only `{productDiscounts:true, orderDiscounts:true}` is accepted (`shippingDiscounts` must stay false) — that is what makes promo codes stack with free shipping. Default when omitted = none (false/false/false), so always `discountAutomaticFreeShippingUpdate` with the product/order combo after creating. `appliesOnOneTimePurchase` → INVALID unless the shop uses subscriptions. Revert: `discountAutomaticDelete(id:...)`. `destination {all:true}` for worldwide. Cosmetic alternative = edit the rate price to 0 in admin or via API once `write_shipping` is granted (`deliveryProfileUpdate` currently ACCESS_DENIED).

**Checkout verification recipe (no browser-use CLI on this VM):** `~/.venvs/playwright/bin/python` + `chromium.connect_over_cdp("http://127.0.0.1:9333")` (long-lived automation Chrome already running on port 9333), open `https://<shop>/cart/<variant_id>:1`, fill `input[name="email|firstName|lastName|address1|city|postalCode"]`, wait ~9s, read `body` innerText for "Shipping method"/"Cost summary", screenshot. Country change via `select[name="countryCode"]` times out (custom combobox) — use API/zone data instead.

## User interaction notes

- Aamir is non-technical with Shopify admin: give ONE step at a time, name the exact field AND its prefix (`shpat_`), verify prefix before storing, offer screenshot fallback (tesseract installed for OCR). This session: token pasted as "client_secret" was shpss_-prefixed — treat user field labels as unreliable, verify prefix.
- User directive: "use canvas all features in product photos and branding" — generated branded tiles = the approved visual system; reuse navy/gold + cert strip everywhere.
