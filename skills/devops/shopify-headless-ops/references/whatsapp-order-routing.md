# Routing Shopify orders to WhatsApp (checkout de-coupled from any gateway)

Use when a merchant wants orders placed via WhatsApp instead of an online gateway
(e.g. prices are attention-grabbers / not final, no payment integration wanted yet).
Goal: client never has to "connect" a gateway, nothing charges automatically, orders
still land in Shopify admin for fulfilment.

## Where the money/CTA paths live in Horizon (and most 2.0 themes)
| Path | File | What to change |
|---|---|---|
| Product page primary CTA | `blocks/buy-buttons.liquid` (Horizon) / `sections/main-product.liquid` (Dawn) | inject a WhatsApp anchor right after the add-to-cart `{% content_for 'block', type: 'add-to-cart' %}` |
| Product page dynamic/accelerated checkout ("Buy now" -> PayPal/Shop Pay) | `blocks/accelerated-checkout.liquid` (`{{ form_obj \| payment_button }}`) | remove the `payment_button` filter; empty the capture so the wrapper degrades to nothing |
| Cart page + cart drawer CTA | `snippets/cart-summary.liquid` | replace `<button id="checkout">` with the WhatsApp anchor; blank `{{ content_for_additional_checkout_buttons }}` |

Verify with grep before editing, so you do not miss a path:
```bash
grep -rl "payment_button\|content_for_additional_checkout_buttons" .   # -> 2 files
grep -rl 'id="checkout"\|name="checkout"' .                            # -> cart-summary
```

## Prefilled message (product page) — inside a block, `product` is `closest.product`
```liquid
{%- assign lw_phone = '966574268856' -%}
{%- capture lw_text -%}
Hello Luxewave, I would like to order:
{{ product.title }}
{{ shop.url }}{{ product.url }}
Please confirm availability and the final price.
{%- endcapture -%}
<a href="https://wa.me/{{ lw_phone }}?text={{ lw_text | strip | url_encode }}" target="_blank" rel="noopener">Order on WhatsApp</a>
```
Cart version loops `cart.items`: `- {{ item.product.title }}{% unless item.variant.title == 'Default Title' %} ({{ item.variant.title }}){% endunless %} x{{ item.quantity }}`.
Do NOT put prices in the message when the catalog prices are placeholders.

## Styling
Inline style only (no theme CSS/assets dependency, survives theme edits):
`display:flex;align-items:center;justify-content:center;width:100%;box-sizing:border-box;padding:14px 18px;border-radius:8px;background:#25D366;color:#fff;font-weight:600;font-size:15px;text-decoration:none;`
Keep the theme's own class (`cart__checkout-button button`) on the cart anchor so layout/spacing still matches.

## Deploy safely (preview gate)
1. `GET /admin/api/<ver>/themes.json` – find `role: main` and an unpublished theme to use as staging.
   `POST /themes.json` with `src=<theme_id>` is NOT supported (400) – a duplicate can only be made from the admin UI or by copying assets.
2. Copy live -> staging for the files you touch (`PUT themes/<staging>/assets.json {"asset":{"key":...,"value":...}}`)
   plus `config/settings_data.json`, `layout/theme.liquid`, the relevant `sections/*.json` + `templates/*.json` for fidelity. ~2 req/s -> sleep 0.35s.
3. Apply edits to staging, then preview anonymously (verified to work with no login):
   `https://<store>.myshopify.com/products/<handle>?preview_theme_id=<staging_id>`
4. QA loop: fetch live + preview HTML and diff markers:
   `lw-wa-order` / `wa.me/<num>` present, `payment_button` + `acceleratedCheckout` absent, and the live page must still show the OLD state (proves prod untouched).
5. Visual QA with Playwright `channel='chrome'` (system Chrome; the playwright venv usually has no browsers installed):
   count `a.lw-wa-order`, decode `href` text=, click `button[name="add"]`, then `/cart?preview_theme_id=` and assert `button#checkout` count == 0. Screenshot desktop 1440 + mobile 390.
6. Publish only after owner approval (`PUT /themes/<id>.json {"theme":{"role":"main"}}` publishes). Rollback = republish the previous theme id; keep `.orig` copies of every edited asset.

## Gateway reality checks
- There is **no Admin API** for payment gateway settings: `payment_gateways.json` -> 404, no GraphQL mutation. Disabling PayPal is an admin-UI action only.
- "Not connecting PayPal" diplomatically = leave the gateway untouched in admin, but remove every PayPal/accelerated button from the storefront so nobody reaches the gateway. If the merchant later wants it fully off: Settings -> Payments -> Manual payment methods (add "Order on WhatsApp / bank transfer") **first**, then deactivate PayPal (else checkout becomes a dead end).
- Check where a completed order's money went by reading the order's transaction `receiptJson` (`receipt.payee_email`, `merchant_id`, `paypal_fee`, receivable currency) - see `references/payment-gateway-forensics.md`.
