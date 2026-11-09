# Store Build Part 2 — Pages, Discounts, Menus (scopes granted, 2026-07)

Extends `admin-api-store-build.md` (products/images/SEO). Validated 2026-08-22 on the Luxe Wave trial store: 7 pages + 2 discount rules + 2 menus, all via Admin API after the user added `write_content`, `write_discounts`, `write_menus` scopes.

## 0. Scope-add token behavior (CORRECTS an older claim)

Adding scopes to a custom app (Configure Admin API scopes → Save → Install app) does **NOT** necessarily rotate the token. Observed: the exact same `shpat_` token kept working AND gained the new scopes — `/pages.json` and `/price_rules.json` flipped 403 → OK with zero token change.
**Rule: after the user says scopes are added, re-probe the previously-403 endpoints with the EXISTING token before asking for a resend.** Only ask for a fresh token if the probe still 403s. (This contradicts older notes claiming the old token dies on scope add.)

## 1. Pages via REST (`write_content`)

```python
POST /pages.json {"page": {"title", "body_html", "author": "Luxe Wave", "published": True,
  "seo": {"title": f"{title} | Luxe Wave", "description": "..."}}}
```
- body_html = brand-styled: outer `<div style="max-width:800px;margin:0 auto;font-family:Inter,Arial;color:#1a2436;line-height:1.75;">`, `<h2>` sections with `border-left:4px solid #C9A45C;padding-left:12px;`, EN `<p>` + AR `<p dir="rtl" lang="ar">` pairs, navy CTA `<p style="background:#0B1B3D;color:#fff;...">` with gold link.
- Standard 7: About Us (CR number, certs, hotels served), Contact, Request a Quote, Privacy, Refund, Shipping, Terms (B2B-flavored — "produced to order", 48h damage window).
- **Contact info unknown?** Put `{{WHATSAPP}}` / `{{EMAIL}}` placeholders in the HTML, ask the user once, re-PUT later. Never invent a number/email.
- ~0.4s sleep between page POSTs; all 7 succeeded in one pass.

## 2. Discount codes via REST (`write_discounts`)

Legacy REST `price_rules.json` + `price_rules/{id}/discount_codes.json` STILL WORKS on API 2026-07 (the non-deprecated path is GraphQL `discountCodeBasicCreate` — REST is fine for a simple 2-rule setup).
```python
POST /price_rules.json {"price_rule": {"title": "Welcome — 10% off first order",
  "value_type": "percentage", "value": "-10.0",           # NOTE: negative string
  "customer_selection": "all", "target_type": "line_item", "target_selection": "all",
  "allocation_method": "across", "once_per_customer": True,
  "starts_at": "2026-08-22T00:00:00+03:00",               # Riyadh tz
  "prerequisite_subtotal_range": {"greater_than_or_equal_to": "500.00"}}}
POST /price_rules/{id}/discount_codes.json {"discount_code": {"code": "WELCOME10"}}
```
Pattern: WELCOME10 (10%, min 500 SAR, once per customer) + BULK5 (5%, min 5000 SAR).

## 3. Navigation menus via GraphQL (`write_menus`) — 2026-07 gotcha

`menuCreate` takes **FLAT arguments**, NOT an input object (older docs show `menuCreate(menu: MenuCreateInput!)` — that fails on 2026-07 with "MenuCreateInput isn't a defined input type"):
```graphql
mutation { menuCreate(title: String!, handle: String!, items: [MenuItemCreateInput!]!) {
  menu { id title } userErrors { field message } } }
```
`MenuItemCreateInput` has a **mandatory `type` field** (`MenuItemType` enum): FRONTPAGE, COLLECTION, COLLECTIONS, PRODUCT, CATALOG, PAGE, BLOG, ARTICLE, SEARCH, SHOP_POLICY, HTTP, METAOBJECT, CUSTOMER_ACCOUNT_PAGE. Omitting it → "Expected value to not be null for 0.type".
Item shapes:
- Home → `{title: "Home", type: "FRONTPAGE"}`
- Collection/page → `{title, type: "COLLECTION"|"PAGE", resourceId: "gid://shopify/Collection/<id>"}`
- Custom URL → `{title, type: "HTTP", url: "/..."}`

**Debug path when a mutation's type name is wrong:** introspect the mutation's args (`__type(name:"Mutation"){fields{name args{name type{kind name ofType{kind name ofType{kind name}}}}}}`), drill into the arg's INPUT_OBJECT name, then `__type(name:"<InputName>"){inputFields{name type{kind name}}}` for required fields, and `__type(name:"<EnumName>"){enumValues{name}}` for allowed values.
Main menu (Home + 7 collections + About + Quote + Contact) + footer menu (6 policy pages) — both OK in one pass, ~0.4s between mutations.
