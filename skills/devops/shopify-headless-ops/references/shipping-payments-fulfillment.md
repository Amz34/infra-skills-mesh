# Shipping rates, payments, fulfillment & order monitoring (verified Sep 2026, Luxewave KSA store)

Companion recipes for the Admin API side of a Shopify store: what is API-doable, what is
**UI-only forever**, and how to PROVE each state at the live checkout instead of trusting an API read.

## Scope → capability map (probe by calling, the scopes endpoint lies)

`/admin/oauth/access_scopes.json` can return empty / stale. Ground truth = call the endpoint:

| Capability | Needs | Observed |
|---|---|---|
| read orders / products / customers | `read_*` | ✅ |
| **create/update automatic discount** (`discountAutomaticFreeShippingCreate`) | `write_discounts` | ✅ (worked with a token that lacked `write_shipping`) |
| read/create webhook subscriptions | webhooks scope | ✅ create reached payload validation → 422 `address: must use a valid domain name` (**not** 403 = scope is fine) |
| `deliveryProfileUpdate` (edit shipping rates) | `write_shipping` (+ `read_shipping`) | ❌ 403 |
| `shopPolicyUpdate` (create refund/ToS/shipping policy) | `write_legal_policies` | ❌ 403 — policy bodies are anyway better written in the UI |
| `PUT /admin/api/<ver>/shop.json` (rename, tax, address) | — | **406 Not Acceptable always** — read-only wall, no mutation path exists |
| enable a payment provider | — | **UI-only, no API at all** |

## Shipping: how to make it FREE without `write_shipping`

You cannot PATCH the rate when the token lacks `write_shipping`. Use an **automatic
free-shipping discount** instead — it zeroes the shipping line at checkout and shows as a
discount line, and it combines with normal promo codes.

```graphql
mutation { discountAutomaticFreeShippingCreate(freeShippingAutomaticDiscount: {
  title: "Free shipping - Saudi Arabia", startsAt: "2026-09-20T00:00:00Z",
  destination: { countries: { add: ["SA"] } },   # buyer: ALL by default
  minimumRequirement: null                        # no minimum
  combinesWith: { productDiscounts: true, orderDiscounts: true }
}) { automaticDiscount { id title } userErrors { field message code } } }
```

Pitfalls (each one cost a round trip):
- `appliesOnOneTimePurchase` → INVALID unless the shop sells subscriptions. Omit.
- `combinesWith` with all three `true` → `INVALID_COMBINES_WITH_FOR_DISCOUNT_CLASS`.
  For the SHIPPING class accept only `{productDiscounts, orderDiscounts}` and **omit
  `shippingDiscounts`** (shipping discounts combining with shipping discounts is meaningless).
- GraphQL connection field is `automaticDiscountNodes` (plural) — `automaticDiscountNode` fails.
- Enum values are only introspectable on ENUM types (`__type(name:"X"){enumValues{name}}`);
  input-object fields need trial-and-error.

### Ground truth = a live checkout, not a REST read
`GET /admin/api/<ver>/shipping_zones.json` came back **200 with a zone and no rates at all**
while a real `قياسي SAR 25.00` rate was active in the UI. Never report "no shipping rate" from
that endpoint, and never report a shipping change as working without a checkout test.

**Read-only checkout verification recipe** (headless VM, no login needed):
1. Cart permalink: `https://<store>.myshopify.com/cart/<variant_id>:1` — works for any published product.
2. Drive it with Playwright against the already-running GUI Chrome:
   `connect_over_cdp("http://127.0.0.1:9333")` using `/home/ubuntu/.venvs/playwright/bin/python`.
   (Fresh `launch()` needs a login round; CDP attach reuses the live session.)
3. Fill the shipping address (Riyadh: city/postal/province), then read the shipping line +
   order summary: expect the original rate, a `FREE SHIPPING - <scope>` discount line, and
   `Shipping SAR 0.00`.
4. **Sellable-country ground truth**: enumerate the checkout `select[name="countryCode"]`
   options. Real case: shipping zone listed 28 countries but the select held exactly
   `value=SA` (count=1) → the store genuinely sells to Saudi Arabia only. Native-set the
   select via JS and read `options`, don't try to "select" a country that isn't offered.

## Payments (KSA reality)
- **Shopify Payments is NOT available to Saudi Arabia merchants** — PayPal (or another
  third-party gateway) is the only built-in-ish option; card payments need a KSA gateway.
- Amounts/verification: a paid test order (PayPal) shows up as `financial_status: paid` with
  the gateway receipt — that is the proof money moved.
- Options to offer a KSA client: **Moyasar, Tap, PayTabs, HyperPay** (cards, KYC 1–3 days) and
  **Tabby / Tamara** (BNPL); or **COD + bank transfer** as manual payment methods (no KYC,
  ~3 minutes, done in admin UI → Settings → Payments → Manual payment methods).
- Shopify charges a third-party transaction fee on non-Shopify-Payments orders (0.6% on
  Advanced) — mention it when recommending a gateway.
- Gateways require live refund / shipping / ToS / contact policies — a Privacy-only store
  will be rejected. Policies are UI-authored (`shopPolicyUpdate` needs `write_legal_policies`).

## Fulfillment & courier automation
Order lifecycle: order lands as **unfulfilled** → **Fulfill items** + tracking number (this is
exactly what a client's "how does fulfillment work" doc describes). Via API that needs
`read_merchant_managed_fulfillment_orders`, `write_merchant_managed_fulfillment_orders`,
`read_fulfillments`, `write_fulfillments` (+ `read_shipping`/`write_shipping` to touch rates)
— add scopes in the app, reinstall, and a NEW token must be issued.

Courier lanes for KSA (advice shape the user actually wants):
- **Self-delivery**: zero integration, COD cash in hand, best for bulky items / single-city. Fulfil manually.
- **Courier automation**: SMSA / Aramex / SPL / Naqel direct APIs, or aggregators **Torod / OTO**
  (KSA multi-carrier + Shopify apps). Fully automated chain = order → create shipment → AWB +
  label → push tracking number to Shopify → auto-fulfil → status/delivery sync → COD remittance.
- Prereqs before any connector work: client CR + IBAN + carrier business account + API keys.
- Honest scaling rule to state: integration payoff starts ~15–20 orders/day. Below that, the
  carrier dashboard is fine — build the alert lane first, not the shipment lane.

## Order monitoring — where an order actually "arrives"
Three real lanes, and the traps:

1. **Shopify admin → Orders** (+ mobile app with push). Always the source of truth.
2. **Email**: the customer gets "Order #N confirmed"; the merchant gets a separate "New order"
   notification routed by Settings → Notifications. **Trap: a Gmail/IMAP watcher on the store's
   own address only sees orders whose customer used that address** — it is NOT a reliable
   merchant alert lane for real customer orders. Don't build order alerting on IMAP.
   (What the sender display name shows is `shop.name` — an unrenamed store mails as `متجري`.)
3. **Webhooks**: the right automation lane, but registered addresses rot. Real case: two
   subscriptions (`orders/create`, `carts/update`) pointed at a
   `*.trycloudflare.com` **quick tunnel** whose URL had died → orders silently alerted nowhere.
   `curl -s -o /dev/null -w "%{http_code}"` the address first; `000` = dead.
   For a durable endpoint prefer a **Cloudflare Worker** receiver (HMAC-verify + forward to
   Telegram) over a tunnel — no process to keep alive, no URL churn. Named tunnels only if a
   domain is already in the CF account.

**Zero-dependency alert lane when webhook infra isn't ready yet:** a `no_agent` cron that
polls `GET /admin/api/<ver>/orders.json?status=any&limit=25&fields=id,name,created_at,total_price,financial_status,fulfillment_status,line_items,shipping_address`
every 5 minutes, keeps a state file, and prints an alert **only** on a new id or a changed
status. Silent ticks = no tokens, no spam. Pattern + pitfalls in the `cron-watchdog` skill
("state-file delta poller" variant). Keep the cron launcher under `~/.hermes/scripts/` and the
logic in the repo (`~/ops/luxewave/order_watch.py`).
