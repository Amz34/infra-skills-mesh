# Horizon Theme Branding via Admin API (headless)

Full brand pass on Shopify's Horizon free theme without the theme editor. All asset writes:
`PUT /admin/api/2026-07/themes/{id}/assets.json` body `{"asset":{"key":"...","value":<text>}}` for JSON/Liquid,
`{"asset":{"key":"...","attachment":<base64>}}` for binaries (logo PNGs, hero JPGs — no size limit here).

## Asset map (Horizon)

| Key | What lives there |
|---|---|
| `config/settings_data.json` | `current` preset: `color_palette{background, foreground, color1, color2}`, `logo`, `logo_height`, `logo_height_mobile` |
| `sections/header-group.json` | announcement section + blocks (type `_announcement`, settings: text, font, font_size, letter_spacing, case) + header section (background_color_top, text_color_top, menu, divider) |
| `sections/footer-group.json` | footer section (`background_color`) + blocks (type `text` for a contact block: text, text_color, alignment, width) |
| `blocks/_header-logo.liquid` | logo markup — renders `settings.logo` via `render 'image'`, fallback `text_fallback: shop.name` |
| `templates/index.json` | homepage sections; hero = `media_type_1`, `image_1`, `overlay_color` (#RRGGBBAA), `overlay_style`, `section_height`, plus text/button blocks |
| `layout/theme.liquid` | sitewide injects (WhatsApp floating button) — insert before `</body>` |
| `sections/header-announcements.liquid`, `sections/footer.liquid` | use `render 'contrast-override', background_color: section.settings.background_color` → dark bg auto-flips text white |

Probe schemas headless: `GET .../themes/{id}/assets.json?asset[key]=<file>`; pull `{% schema %}` via regex
`re.search(r'{%\s*schema\s*%}(.*?){%\s*endschema\s*%}', text, re.S)` to learn setting ids/enums before writing.

## image_picker values — the #1 pitfall

Only `shopify://shop_images/<filename>` is accepted:
- `assets/luxe-wave-logo.png` → 422 `logo must be a valid shopify url`
- CDN URL → 422 `image_1 does not point to an applicable resource`
- `shopify://shop_images/<name>` passes validation but renders broken if the file isn't in Files.

### Logo without a Files upload
1. PUT logo PNG as theme asset `assets/luxe-wave-logo.png` (base64 attachment — no cap).
2. Patch `blocks/_header-logo.liquid`: wrap the original `render 'image'` container in
   `{% if settings.logo != blank %}` and add `{% else %}` rendering
   `<img src="{{ 'luxe-wave-logo.png' | asset_url }}" alt="..." width="176" height="44" class="header-logo__image"
   style="--header-logo-image-width: ...; --header-logo-image-height: {{ settings.logo_height }}px; ...">`
   (compute width from logo aspect: height × (w/h) rounded up).
3. Set `settings_data.json` `logo` = `""` (blank) so the fallback branch runs.

### Hero image without a Files upload
Files upload paths are capped (fileCreate `originalSource` data-URI ≤ 2048 chars — "originalSource is too
long"; REST `/files.json` → 406 on some setups). Reuse an image already in Files:
- `GET /products.json?fields=id,title,image&limit=50` → pick a tile by title, take `image.src`
- `fname = src.rsplit('/files/', 1)[1].split('?')[0]` → `image_1 = "shopify://shop_images/" + fname`

Note: `read_collections` scope may be absent even with products granted → `GET /collections.json` 403s;
products.json works. Don't chase the collections scope — use a product image.

## Menus: defaults are protected
- `menuDelete` on auto-created `main-menu`/`footer` → `userErrors: "Default menu cannot be deleted."`
- `menuUpdate` mutation args are TOP-LEVEL: `menuUpdate(id, title, handle, items)` — there is NO input
  object (`MenuUpdateInput` doesn't exist). Passing `menu: {...}` → "missing required arguments: id, title, items".
  `items` = `[MenuItemUpdateInput!]` (id optional for fresh items; title/type/url/resourceId per item).
- `Menu` type has no `itemsCount` field (undefinedField).
- Duplicate-handle problem: creating a menu with handle `main-menu` gives it handle `main-menu-1`; the theme
  renders the auto-created `main-menu` (3 default links), so your rich menu never shows.
- **Correct flow:** menuUpdate the DEFAULT menus with your items (keep their handles — theme references them),
  then menuDelete your duplicates (deletable, returns deletedMenuId).

## Verification without a storefront view
- PUT 200/201 = Liquid compiles AND schema enums valid (invalid settings 422 naming the offending field).
- Storefront is password-gated (302 → /password) → can't curl-render; re-fetch assets and confirm each PUT.
- Watch the handler: local HMAC test POST (see SKILL.md Webhook registration) → WhatsApp/owner alert proves
  the whole chain.

## General headless-bash pitfalls hit while doing this
- Long Python heredocs containing `&` (HTML entities, `&&`) trip the shell guard — write the script to a file
  with write_file first, then run it.
- `settings_data.json` color values in template JSON accept #RRGGBBAA (8-digit hex with alpha) fine.
- Shopify auto-suffixes duplicate handles (`main-menu-1`, `footer-1`) — check `menus(first:10)` before assuming
  your handle landed.
