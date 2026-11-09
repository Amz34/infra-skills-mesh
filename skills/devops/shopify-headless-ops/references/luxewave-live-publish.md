# Luxewave (8k6ikq-g6.myshopify.com) — theme publish facts

## Theme IDs (updated 2026-09-21)
- LIVE / role=main: **`188437987631`** ("LW genuine-top 21-Sep") — published 2026-09-21 00:19Z
  (new logo + photo/video hero + footer website link). Customers see this.
- ROLLBACK candidate / unpublished: `187722826031` ("Horizon" = previous live) — keeps
  the WhatsApp-checkout lane, safe to re-publish if the new theme misbehaves.
- STAGE / unpublished: `187754447151` — OLDER COPY (created 2026-08-22), broken.

## How to duplicate + publish here (REST fails!)
- Duplicate: GraphQL `mutation { themeDuplicate(themeId: "gid://shopify/OnlineStoreTheme/<id>") {...} }`
  (REST `POST themes.json` with `src` returns 422).
- Publish: GraphQL `mutation { themePublish(id: "gid://shopify/OnlineStoreTheme/<id>") { theme { id role } userErrors { message } } }`
- Edit an asset: `PUT /admin/api/2026-07/themes/<id>/assets.json` body `{"asset":{"key":"...","value":"..."}}`;
  read back `GET .../assets.json?asset[key]=...`.
- Homepage hero lives in `templates/index.json` → `sections.video_hero_kD8xQ.settings.custom_liquid`
  (single HTML+cSS+JS blob). Desktop shows the 16:9 photo + a 9:16 **video card** on the right
  (native 404×720 rendered ~336×598 = sharp); mobile makes the same `<video>` full-bleed.
  Verify playback in preview/live with `qa_video.py` (checks `paused:false`, `currentTime>0`).

## HARD RULE: never publish the old stage theme
`187754447151` is missing 13 image assets that exist only on live
(`luxe-wave-hero.jpg`, `luxe-wave-logo.png`, 10x `ad_*.jpg`,
`WhatsApp Image 2026-08-2.jpg`). Publishing it would break the logo,
hero and ad blocks.

## Surgical edits (still the default for small changes)
`PUT /admin/api/2026-07/themes/<live-id>/assets.json`
body `{"asset": {"key": "...", "value": "..."}}`

## WhatsApp order lane (shipped 2026-09-21)
Files on live theme:
- `snippets/lw-wa-order.liquid` (new) — green CTA, wa.me/966574268856
- `blocks/accelerated-checkout.liquid` — capture block replaced by
  `{%- assign accelerated_checkout_button = '' -%}`
- `blocks/buy-buttons.liquid` — `{%- render 'lw-wa-order', product: product -%}`
- `snippets/cart-summary.liquid` — checkout button -> WhatsApp anchor

Locale copy (`locales/en.default.json`): 19x "at checkout" -> "confirmed on
WhatsApp" (incl. `shipping_discount_error`). Backups: `locale_backup/`.

## Verify (live, no preview param)
`python3 verify_wa_live.py` + `verify_wa_cart.py` + `qa_live_play.py`:
expect product wa_links=3 cta_visible=True checkout_btn=0 paypal_btn=0;
cart waCTA=1 chkbtn=0 paypal_btn=0 `at checkout`=0.
