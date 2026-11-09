# Payment gateway & payout forensics via the Admin API (no admin UI)

Use when the question is money-shaped: *"customer pay karega to paisa kahan jayega?"*, *"kis PayPal account me aayega?"*,
*"kitni fee kati?"* — and the Shopify admin UI is unreachable (see dead lanes below) or the token has no `payment` scope.

## The one lane that works: `OrderTransaction.receiptJson`

The raw gateway receipt is exposed as a JSON **scalar** on every order transaction (needs only `read_orders`).
For PayPal Express it contains BOTH sides of the transfer plus the fee math — this is what answers "whose account?":

| Path inside `receiptJson` | Meaning |
|---|---|
| `purchase_units[0].payee.email_address` / `.merchant_id` | **MERCHANT account — where the money lands** |
| `purchase_units[0].payee.display_data.brand_name` | brand the buyer sees (often the raw store name, e.g. `متجري`) |
| `payment_source.paypal.email_address` / `.name` / `.account_status` | **PAYER** (buyer's PayPal, may be UNVERIFIED) |
| `purchase_units[0].payments.captures[0].id` / `.status` | capture id, `COMPLETED` |
| `…captures[0].seller_receivable_breakdown` | `gross_amount`, `paypal_fee`, `net_amount`, `receivable_amount`, `exchange_rate` |
| `payment_instruction.disbursement_mode` | `INSTANT` → straight to merchant balance |
| `soft_descriptor` | what prints on the buyer's card statement (uppercased, truncated ~22 chars) |
| `purchase_units[0].shipping` | rate name + `amount` vs `shipping_discount` → free-shipping proof |
| `purchase_units[0].payments.captures[0].id` + top-level `id` | capture id + PayPal order id for support tickets |

Query (edit version to the shop's current API version):

```graphql
query{ orders(first:5,sortKey:CREATED_AT,reverse:true){
  nodes{ name createdAt displayFinancialStatus test
    totalPriceSet{shopMoney{amount currencyCode}}
    transactions(first:10){ id kind status gateway processedAt
      amountSet{shopMoney{amount currencyCode}}
      fees{ amount{amount currencyCode} flatFee{amount currencyCode} rate rateName type }
      receiptJson } } } }
```

Then in Python: `json.loads(tx["receiptJson"])` and walk the dict.

## Pitfalls / dead lanes (do not burn calls on these)

- `receiptJson` is a scalar — `receiptJson{...}` in a selection set is invalid. Parse it in Python.
- REST `/admin/api/<v>/payment_gateways.json` → **404** (gone). GraphQL exposes no merchant-gateway-account
  field either; `OrderTransaction.gateway` is only the provider name string (`paypal`).
- `OrderTransaction.fees` came back **`[]`** on a capture that really did charge a fee, and
  `settlementCurrency`/`settlementCurrencyRate` were `null`. **Never conclude "no fees"** from those — read
  `seller_receivable_breakdown`. Treat `fees` as best-effort only.
- Admin-UI scraping is a dead end: `accounts.shopify.com` / `admin.shopify.com` sit behind a Cloudflare
  challenge — Playwright lands on the challenge page, not Settings → Payments. `receiptJson` is the reliable lane.
- `OrderTransaction` lookup: query transactions *through* the order node, not by transaction id, on API versions
  where the top-level `transaction(id:)` node is missing.
- Unknown-field discovery: `{__type(name:"OrderTransaction"){fields{name}}}` (also `TransactionFee`, `PaymentGateway`).
  Shopify's error text names the type (`Field 'X' doesn't exist on type 'Y'`) — read the type out of the error and
  introspect that.
- Harness truncation: a probe that prints one giant JSON blob returns "1 lines output". Print only the extracted
  labels (payee / payer / gross / fee / net / rate) or redirect to `/tmp/*.log` and read the file back.

## Interpreting the result for the user

- Shopify never "holds" the money: it lands **directly in the merchant account named in the gateway config**, minus
  the gateway's fee; Shopify only records the order. Say this explicitly when asked "Shopify me credit aayega?".
- If the payee is the owner's **personal** account (not a business account in the brand's name), say so plainly —
  for a client brand that mixes client revenue into personal funds; recommend a business account + a matching
  `soft_descriptor` (PayPal → Account Settings → Business info, 22 chars) so buyers don't see `AAMIR1ZAHRA` on
  their statement.
- USD-based PayPal accounts auto-convert: `receivable_amount` + `exchange_rate` show the SAR→USD leg. On tiny test
  captures the **fixed** fee dominates (observed: SAR 2.00 capture → SAR 1.26 fee, net SAR 0.74 = USD 0.19) — do NOT
  extrapolate that percentage onto real orders; quote the account's rate card for those.
- `test:false` on the order ⇒ it was a live charge, not a test transaction.
- KSA payout reality: Saudi-registered PayPal accounts are widely reported to allow withdrawal only to a US bank —
  tell the user to open Wallet → Transfer Money and read the eligible-bank list instead of promising a local transfer.
  Shopify Payments is unavailable to KSA merchants; the card/Apple Pay route is a local gateway
  (Moyasar / Tap / PayTabs / HyperPay) + Tabby/Tamara for BNPL.

## Verified example — Luxewave (2026-09-21, order #1001)

- Payee (money lands here): **aamir1zahran@gmail.com**, `merchant_id GFZYEPDSWUSY4`, brand display `متجري`.
- Payer: `azengineeringapp@gmail.com` (the owner's own test account, `account_status UNVERIFIED`) — a genuine live charge.
- Capture `04827803BG3986212`, `COMPLETED`, `disbursement_mode INSTANT`, gross SAR 2.00 / PayPal fee SAR 1.26 /
  net SAR 0.74 → USD 0.19. Soft descriptor on the buyer's statement: `PAYPAL *AAMIR1ZAHRA AA`.
- Same receipt proved the automatic free-shipping discount: shipping SAR 25.00 with `shipping_discount` SAR 25.00.
- Checkout offers exactly one method (verbatim `PayPal — You'll be redirected to PayPal`); no Apple/Google Pay.
