# Shopify Scratch Store Build via Admin API

Build a full storefront catalog from a valid `shpat_` admin token with NO theme/pages/discounts scopes. Validated 2026-08-22 on a fresh trial store (33 products + 7 smart collections + 40 images + SEO, all via API).

## 0. Validate + audit (always first)

```bash
curl -s -H "X-Shopify-Access-Token: $T" https://<store>.myshopify.com/admin/api/2026-07/shop.json
# → name, country, currency, timezone; confirms token + which store
curl -s -H "X-Shopify-Access-Token: $T" .../products/count.json   # active count
curl -s -H "X-Shopify-Access-Token: $T" .../smart_collections.json?limit=250
```
Audit notes worth capturing: currency (SAR vs USD), plan (trial = password page ON), domain.

## 1. Scope probing (don't trust access_scopes.json)

`GET /admin/oauth/access_scopes.json` can return EMPTY even for a working token. Probe by calling endpoints:

| Endpoint / mutation | Scope needed | Works with product scopes? |
|---|---|---|
| `/products.json`, `/products/{id}/images.json` | read/write_products | ✅ |
| `/smart_collections.json` + `PUT ... {image}` | write_products (collections ride along) | ✅ |
| Metafields (REST or GraphQL `metafieldsSet`) | write_products | ✅ |
| GraphQL `productUpdate(seo:)`, `collectionUpdate(seo:)` | write_products | ✅ |
| `/pages.json` POST | write_content | ❌ 403 |
| `/themes.json`, theme assets | write_themes | ❌ 403 |
| `/price_rules.json` (legacy) | write_discounts | ❌ 403 |
| GraphQL menus | write_menus | ❌ 403 |

**Adding scopes = admin-only:** app's API credentials tab → Configure Admin API scopes → Save → Install app → copy NEW `shpat_` token. Non-technical user: one field, prefix spelled out.

## 2. Catalog creation (REST, one POST per product)

- Source of truth: client's price list (PDF → text). Keep `(title, price, packing, tag)` tuples in one Python list; derive AR names dict from the same file.
- body_html: EN line + packing + certs + delivery promise + `<p dir="rtl" lang="ar">` AR line.
- tags: `Guest Amenity, amenity, <category>` — categories drive smart collections (rule: tag contains).
- Smart collections: `POST /smart_collections.json` `{smart_collection: {title, handle, rules: [{column: "tag", relation: "equals", condition: "soap"}], published: true}}`. 7 collections: Guest Amenities, Soaps, Hair Care, Body Care, Amenity Kits, Slippers & Footwear, Room Essentials.

## 3. Product images — PIL brand tiles (no photos needed)

When the client has no usable product photos (catalogue = private-label design guide, NOT product shots), generate on-brand tiles with Pillow — 100% no-faces-safe, consistent storefront:

- 1200×1200, navy vertical gradient (`#0B1B3D`→`#12295C`), double gold frame (`#C9A45C`, rounded_rectangle).
- Brand block top: "LUXE WAVE" (Playfair Display, gold) + letter-spaced tagline (Inter).
- Per-category line-art icon drawn with PIL primitives (bottle/soap/kit/slipper/comb/cap/ring/pencil...) in gold.
- Title (Playfair, white, wrapped) + Arabic name (Noto Naskh/Sans Arabic, gold) + bottom cert strip "GMPC · ISO 9001 · SFDA · SASO".
- Fonts: variable TTFs (PlayfairDisplay, Inter, Noto) load fine via `ImageFont.truetype`; `set_variation` not needed at default instance.
- **PIL pitfall:** `rounded_rectangle(radius=35*s, width=10*s)` with float scale → `TypeError: 'float' object cannot be interpreted as an integer` inside `draw_arc`. Fix: `re.sub(r'(radius|width)=(\d+)\*s', r'\1=int(\2*s)', src)` over the generator file.
- Same generator makes collection covers (title + icon, no AR line).
- Arabic numerals in titles: use Arabic-Indic digits (٢٠ مل) — renders fine with Noto.

## 4. Image upload (base64 — no multipart needed)

```python
POST /products/{id}/images.json
{"image": {"attachment": "<base64>", "filename": "soap-15g.jpg", "position": 1}}
PUT /smart_collections/{id}.json
{"smart_collection": {"image": {"attachment": "<b64>", "filename": "coll-soaps.jpg"}}}
```
Sleep ~0.35s between calls (rate limit).

**CRITICAL matching pitfall:** Shopify auto-handle inserts dashes at digit/letter boundaries — "Body Lotion 20ml" → `body-lotion-20-ml`. Guessed handles WILL NOT match your local slugs. Fetch `/products.json?limit=250` and match tile files to products by EXACT title (parse the generator's `(title, ..., fname)` tuples with regex, reverse-map fname→title).
**Pagination pitfall:** a `page=` loop that breaks on empty/error silently returns 0 products while `/products/count.json` says 33 — single `limit=250` GET is enough for <250 items.

## 5. SEO (GraphQL, covered by write_products)

```graphql
mutation { productUpdate(product: {id, seo: {title, description}}) { userErrors { field message } } }
mutation { collectionUpdate(collection: {id, seo: {title, description}}) { userErrors { field message } } }
```
- Title: `"<Title> | Luxe Wave — <packing>"` (≤70 chars). Description: EN + certs + delivery + `| <AR>` (≤300).
- 33/33 products + 7/7 collections succeeded in one pass; sleep 0.25s between.

## 6. Storefront verification

```bash
curl -s -o /dev/null -w "%{redirect_url} [%{http_code}]\n" https://<store>.myshopify.com/
curl -s -o /dev/null -w "%{http_code}\n" https://<store>.myshopify.com/products.json
```
- root 302 → `/password` + products.json 401 = **password page ON** (trial/new store). Products are published but locked. Launch = user removes password (Settings → Preferences) + chooses plan — both admin-only.
- `meta.json` shows store name — trial stores default to "متجري" (Arabic for "my store"); rename is admin-only (Settings → Store details). Flag it to the user.

## 7. Admin-only items checklist (things API cannot do — hand to user as ONE session)

1. Add scopes (themes/content/discounts/menus/analytics) → Save → Install → resend token
2. Store name (Settings → Store details)
3. Remove password page + pick plan (launch)
4. Brand logo in theme header (once write_themes granted — or Settings → Brand)

## Workflow scripts (live at ~/clients/luxewave/)

`build_catalog.py` (products+collections), `make_tiles.py` (tile/cover generator — PIL, regex-fixed), `upload_images.py` (title-matched uploads), `apply_seo.py` (GraphQL bulk SEO). All read `~/clients/luxewave/.env` (SHOPIFY_STORE + SHOPIFY_ADMIN_TOKEN). Generalize the data lists for the next client build.
