---
name: shopify-whatsapp-bot
description: Shopify webhook to WhatsApp alert and AI bot integration.
---

# Shopify + WhatsApp/AI Bot Integration

Sanad ka Shopify product line: store owner ke liye WhatsApp order alerts + AI support bot (bilingual EN+AR). Recurring MRR model — WP Care Plan jaisa.

## Architecture

```
Shopify Store ──webhook──► handler.py (FastAPI) ──► WhatsApp Baileys bridge (:3000)
     │                          │                        └── owner/customer alerts
     └── Storefront API ◄────── bot (DeepSeek RAG on store data)
```

- Webhooks: `orders/create`, `carts/update`, `customers/create`
- APIs: Admin API (owner ops), Storefront API (customer-facing), both REST + GraphQL
- Free dev store: Shopify Partners → Stores → Add → Development store (no card)

## Key Steps

1. **Dev store setup** (user step, 5 min): shopify.com/partners → signup → dev store → note `<store>.myshopify.com`
2. **Admin API token**: Settings → Apps and sales channels → Develop apps → Create app → Admin API scopes (`read_orders`, `write_orders`, `read_customers`, `read_products`) → install → copy Admin API access token
3. **Webhook setup**: Develop app → Webhooks → add endpoint `https://<VM_IP>:8644/shopify/orders/create` → `orders/create` topic (auth: `X-Shopify-Hmac-SHA256` header verify)
4. **Handler**: FastAPI app on :8644 (webhook already enabled in Hermes config) — verify HMAC, format message, POST to Baileys bridge /send endpoint
5. **Baileys send**: bridge.js :3000 — `POST /send {to: '<num>@s.whatsapp.net', text: '...'}` (see WhatsApp Oracle bridge)

## Pitfalls

- Webhook URL must be **HTTPS** — VM pe use Cloudflare tunnel OR set `X-Shopify-Test` local testing; production: CF tunnel/free tier
- HMAC verify **karna hi** — warna koi bhi fake order bhej sakta hai
- Dev store webhook retries: Shopify retries 4x with backoff — handler idempotent rakho (order ID dedupe)
- Baileys bridge internal hai (:3000 localhost) — handler ko localhost se call karo, public nahi
- Shopify API rate limit: REST 2 req/s bucket, GraphQL 50 points — batched calls use karo
- Arabic/EN messages: WhatsApp pe Arabic text fine hai — UTF-8 ensure karo

## Verification

- Test webhook: "Send test notification" in app webhook settings OR curl with HMAC
- Verify: fake order → handler log → WhatsApp pe owner alert aana chahiye
- `curl -X POST :8644/shopify/orders/create` with correct HMAC header — 200 expected
