---
name: domain-flip-ops
description: "Use when buying or reselling domain names (flips)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [domains, flipping, name-arbitrage, registrar, rdap, escrow, outreach]
    related_skills: [domain-email-provisioning, cloudflare-pages-ops, client-prospecting, cold-email-campaign-ops]
---

# Domain Flip Ops (acquire → wire → resell a name)

Operate domain names as an asset: verify availability honestly, pick a name a *named buyer class*
would want, register at the cheapest real registrar, put a live sale page + working Reply-To mailbox
on the domain itself, then run verified buyer outreach to close it (escrow / same-registrar push).

## When to use
- "Is `<name>` available?", "domain flip", "sell this domain", "name arbitrage", "domain reselling".
- Building or wiring a "This domain is for sale" lander, or a wave of emails offering a name.
- Any question about registrar pricing, registrar APIs, transfer locks, or escrow fees.

## 0 — The business model (state it honestly to the user)
At-cost registration (~$10.44/yr for `.com` at Cloudflare Registrar) → live lander on the domain →
targeted outreach to the few firms for whom the name *is* a product name → escrow sale at 50–200× the
fee. Sell-through industry-wide is ~1%/yr, so this only works with **buyer-side selection**, not volume.
Wrap it as replicable infrastructure (Pages lander, branded mailbox, GSC submit, alert/watchdog) if
the user is monetizing the *capability*, not just one name.

## 1 — Availability verification that can be trusted
`scripts/avail_check.py` implements this end-to-end (mandatory control tests built in):

| TLD | Check | Meaning |
|---|---|---|
| `.com` | `https://rdap.verisign.com/com/v1/domain/<name>` | 200 registered · 404 available · 429/000 unknown |
| generic | `https://rdap.org/domain/<name>` fallback | 200 / 404, field names vary per registry |
| `.ai` | `whois -h whois.nic.ai <name>` | "Domain Name:" block = taken; no match = free |

- **CONTROL TESTS ARE MANDATORY.** Always include known-taken names (`google.com`, `orchestra.ai`) in
  the same batch and abort if they read as free. This caught a `.ai` checker that reported 100% of
  several thousand candidates as available — a whole "opportunity list" that was pure artifact.
- Never conclude "available" from a single 404: report "likely available — registrar confirms at
  checkout", and re-check immediately before paying (drops get taken between curation and purchase).
- Nameservers tell you more than RDAP alone: `*.ns.cloudflare.com` may simply be the user's *own*
  other account, which is not the same as "available". A parked/whois-privacy domain still resolves.
- Datacenter-IP queries work for RDAP/WHOIS (no captcha); whole-portfolio `whois` loops get rate
  limited — pace them, or run RDAP per name.

## 2 — Name selection: buyer-first, not wordplay
- Trendy AI stems are picked clean: `agent*` / `prompt*` / `model*` `.com` measured ~96% registered
  (7,668 candidates → 3,458 "free", essentially all junk). Do not build a list from trending tokens.
- Headroom lives in **vertical keyword compounds** — the buyer's product category + a short noun
  (e.g. `prior` + `dock` for prior-authorization vendors). Score: pronounceable, ≤12 chars, no
  hyphen/number, obvious meaning inside the buyer's own pitch deck.
- **Name the buyer before registering.** In the worked flip the buyer class was funded prior-auth
  vendors with a regulatory deadline (CMS-0057-F, 1 Jan 2027) forcing a product rename. If you cannot
  produce ≥20 real companies who would plausibly want the name, don't buy it.
- Cross-check comps before promising a price (see §6) — never quote a "market value" you did not read.

## 3 — Registrar choice: price **and** payment method
| Registrar | 1st yr | Renewal | Payment | API |
|---|---|---|---|---|
| Cloudflare Registrar | at-cost (~$10.44 .com) | at-cost, no markup | card on file | Registrar API beta 2026 (needs `Registrar:Edit`) |
| Porkbun | $11.06 flat | $11.06 flat | PayPal / crypto | yes |
| Dynadot | $10.88 flat | ~flat | PayPal / crypto / wire / Alipay | yes, mature |
| Namecheap | $10.98 promo | **$18.48** ⚠ | card / PayPal | yes |
| Spaceship | $5.98 | $11.98 | card / PayPal | part of Namecheap |
| Njalla | ~$15 | ~$15 | crypto / PayPal | no (proxy owner) |

Ask about the payment method, not just the price — "card nahi lagana" sends users to Porkbun/Dynadot
(PayPal/crypto). Free privacy + flat renewal are the two features to compare on.

## 4 — Registration is a USER step (don't burn calls on it)
Cloudflare Registrar has historically been dashboard-only; the Registrar API (beta, 2026) returns
`403 code 10000` for any token minted without `Registrar:Edit` scope. Treat "register the name" as a
5-minute user action, give them the exact dashboard path, and do everything else yourself. Probe the
token first (probe pattern in `cloudflare-pages-ops` → `references/pages-custom-domain-email-routing-api.md`)
before promising autonomy.

## 5 — Wire the asset before you try to sell it
1. **Sale lander on the domain itself** — a Pages project with an inquiry form (Pages Function →
   Telegram alert) plus an offer/escrow CTA and a "make an offer" address. See `cloudflare-pages-ops`
   for the custom-domain attach + DNS gotchas (API-added domains stay `pending` until the apex CNAME exists).
2. **A working Reply-To mailbox** (`offers@<domain>`). Enable Email Routing (MX + SPF auto-created),
   verify the destination, then **prove it receives** by sending from a second account and reading it
   back. Confirmed live: `dig +short MX` → `routeN.mx.cloudflare.net`, SPF
   `include:_spf.mx.cloudflare.net`. The first test send commonly bounces (`550 5.1.1 Address does not
   exist`) because the sending resolver cached the domain *before* its MX existed — the DSN lands in the
   **sender's** inbox, so read it there, re-`dig` MX, and re-send before touching anything. Only a
   second bounce after MX resolves means something is actually wrong.
3. **Index the lander** (sitemap + robots + Search Console submission) so a buyer who googles the
   name finds the price/CTA instead of nothing.
4. Competitive differentiator worth naming in the offer: many "for sale" landers in the wild have
   **no MX at all** — no way to receive an offer at the domain, no SPF/TXT, no analytics (observed on
   a competing lander: Hostinger registration, Netlify DNS, ~205 words, no mail records). A wired
   domain reads as a serious seller.

## 5b — Inbound triage on a live lander (form and `offers@` are NOT the same inbox)

Two independent channels, and the user will ask about both ("`<domain>` ke emails kahan monitor
karein?"). Answer with the concrete destination, not "Cloudflare handles it":

| Channel | Where it lands | Archive? |
|---|---|---|
| Lander inquiry **form** (Pages Function) | Telegram alert only | ❌ none — a missed Telegram message is a lost offer |
| **`offers@<domain>`** (Email Routing) | forward → the verified **destination inbox** | ✅ in that mailbox |

- Audit the live config before answering — per-address rules, catch-all state, destination addresses:
  `domain-email-provisioning` → `references/cloudflare-email-routing-cli.md`. Note **catch-all off
  (`drop`) = only the addresses you created receive**; any `info@` / `hello@` you advertise on the
  lander silently bounces. Search the destination inbox for real history before describing it.
- **Most inbound is NOT a buyer.** Within days a live lander gets scraped into SEO/"we'll rank you on
  Google + ChatGPT", "your site is listed on `<directory>`", and backlink blasts. Tell-tales of a
  template blast: Gmail sender (no company domain), generic flattery ("I personally see a lot of
  potential in your website"), zero specific findings about *this* page, and a "may I send you a quote
  & price list?" permission hook. Nothing on a for-sale lander is rank-able, so the offer is worthless
  here — don't buy it, don't argue with it (reseller retainers run ~$300–1,500/mo for templated work).
  Also check what the blast reveals: a working reply proves the form/mailbox pipeline is alive.
- **Reply once, then stop** — that is the cheapest way to cut repeat spam, and it costs one email.
  English, no emoji, sent from a real mailbox (Email Routing cannot send as the domain), From display
  name = the seller:

  > Subject: Re: outreach to `<domain>` — please remove us from your list
  >
  > Thanks for the note. `<domain>` is a domain we hold for sale — it is not an operating business, and
  > the page has no content, traffic or customer base for SEO, AEO or GEO work to improve.
  > Please remove `offers@<domain>` from your outreach list.
  > If anyone in your network is looking for a `<vertical>` brand name, the domain itself is available —
  > offers go to `offers@<domain>`.

  Log the reply alongside the wave log so a second blast from the same sender is recognisable.

## 6 — Transaction mechanics (what to tell a buyer)
- **ICANN 60-day transfer lock**: a freshly registered domain cannot move to another *registrar* for
  60 days — but a **same-registrar account push is instant**. So: if the buyer is on the same
  registrar, closing is same-day; otherwise it is day-61, or push-then-they-transfer. Say this before
  promising a fast close, and keep the registration mailbox accessible (auth codes arrive there).
- **Fees (verify, don't quote from memory)**: escrow.com USD schedule is **$0–5,000 → 2.6%, minimum
  $50** (the older 3.25% table is superseded) → **$62.40** on a $2,400 sale, **$20** seller
  international-wire payout, **+$25** if the *buyer* pays by international wire, plus local GST/VAT on
  the fees. Marketplaces: Afternic 25% / 30% (network), Sedo 10–20%, Atom 7.5% / 4.5%, Efty $15–36/mo
  + 5%. Prefer escrow-style direct deals for a single-name flip; marketplaces only for their buyer pool.
- **Comps to cite, not invent** (public 2026 data): `bot.ai` $1.2M (Sedo, Feb 2026); `orchestra.ai`
  $250k after a ~$2.9k purchase (≈100×); `.ai` 2026 volume $27.1M (+189% YoY); `.com` public median
  ~$549 with 99.4% of sales under $10k. Price the name against *its* vertical, then hold a floor.
- Lease-to-own (e.g. $250 × 12) converts better than one big ask for a cash-tight SME buyer; state
  both prices up front.

## 6b — Settlement & payout rail (get this right BEFORE quoting a net number)
Full verified detail, field maps and checklists: `references/escrow-settlement-and-payouts.md`.
- **Escrow is a SALE-side tool only** — it plays no part in buying the name, and a new account links
  **no bank**. The disbursement method is supplied **per transaction at closing** (create → buyer
  funds → seller pushes + marks delivered → buyer inspects/accepts → seller enters payout details).
  Escrow will not advance without it. Never tell the user to "link the bank at signup".
- **Rails are narrow:** escrow pays **real bank accounts only** (no Wise/Payoneer/PayPal), and the
  **account-holder name must match the escrow profile name exactly** or the wire returns. Third
  parties cannot be paid — no family/company substitute.
- **Supported countries include Saudi Arabia ✅ and India ✅** (unsupported: Egypt, Pakistan, Yemen).
  Ask/verify the destination country before promising a rail.
- **India**: own-name **NRE** (or NRO) account, USD wire, purpose code **P1590** (< $10,000) or
  **P0017** (entity selling an intangible), ask for **e-FIRC**; bank+FX ≈ ₹600–1,600; GST not required
  below ₹20 lakh; non-resident foreign-source not taxable (resident <24-month hold = slab rate → "confirm with your CA", never state it as advice).
- **KSA**: single hop, no purpose code, no e-FIRC, personal income tax zero, incoming wire ≈ SAR 25–75
  + FX spread — cheapest paperwork, but verify the bank's exact English beneficiary spelling.
- **Settle individual-vs-business FIRST** (sale on your own name vs a company): it decides the escrow
  profile, the WHOIS registrant and the bank account designation — changing it later is a rebuild.
- Collect the closing data in **one ask** (holder name, account/IBAN, SWIFT, beneficiary address,
  phone for verification codes) rather than drip-feeding the user at closing time.
- **Signup is a user step** when Cloudflare Turnstile guards the form — prepare email + password (store
  it via `vault set <space> KEY=VAL`), then hand over a numbered click list; see
  `headless-browser-automation` → "Turnstile on a SIGNUP form".
- **The LOGIN page is Turnstile-walled too.** Do NOT hand login to the user's own browser — that loses
  the agent's session and every later profile/KYC field has to be dictated by hand. Render the agent's
  own CDP tab visibly (`cdp('Target.createTarget', …, newWindow=True)`), prefill email + password, and
  let the user click only the CAPTCHA checkbox over noVNC/RustDesk; the agent then fills the profile
  itself. Login recipe + Saudi National Address → escrow field map + IBAN mod-97 / SWIFT verification:
  `references/escrow-settlement-and-payouts.md`.

## 7 — Buyer outreach: verify, don't guess
Same discipline as `client-prospecting` / `cold-email-campaign-ops`, tightened for a name sale:
- Only **published** addresses and contact forms that return 200; LinkedIn slugs taken from the
  company's own site footer, never from search guesses. Blank beats fabricated — a wrong address in a
  domain offer kills credibility instantly.
- Verify each target domain resolves **and has MX** before adding it to the wave.
- **Tier the list by buying intent before writing any copy.** A = the name collides with their own
  live product (defensive purchase / a rebrand they are already being pushed into — e.g. a vendor whose
  product is literally `<stem>.ai`), B = adjacent-workflow vendors who could launch a second product on
  it, C = reserve. Only tier A belongs in wave 1; a tier-C name in the first wave dilutes the pitch.
- Wave 1 = 8–12 firms, one contact per firm, 20 s+ spacing, recipient-local business hours, logged.
- Copy shape: honest value, no price in the first email (invite an offer), name the escrow route,
  sign with a genuine human name, From = a real mailbox, Reply-To = `offers@<domain>`.
- Follow-ups day ~4 and ~9 only to non-responders; never re-pitch the same person twice.
- Keep the target list + wave drafts + sent log in the project dir so follow-ups and wave 2 are
  derivable, not remembered.

## Pitfalls
- **Trusting availability output without a control test** — the failure is silent and total (a bad
  `.ai` parser dressed up thousands of taken names as free). Control names first, always.
- **Sending outreach before the Reply-To mailbox receives.** Registration ≠ sellable. Prove inbound
  mail works (test send from another account, read it back) before the first cold email.
- **Cold-flipping blind portfolios = negative EV.** Renewal drag (~$11/name/yr) plus ~1% annual
  sell-through means only buyer-named names, or watchdog-driven selective buys (catch expiring names
  in a vertical you already have buyers for), are worth registering.
- **Promising registrar autonomy.** `403 code 10000` on `/registrar/*` is a scope wall, not a bug;
  registration stays a user step unless they mint a `Registrar:Edit` token.
- **Quoting a net payout without checking the rail.** Name-match rules, "real bank account only", and
  per-country support decide whether the money can even arrive — verify those before you quote the
  buyer's net (a returned wire after the domain is delivered is the worst possible outcome).
- **Treating escrow account creation as the blocker for selling.** It is free, links no bank, and is
  not needed until closing — never let a Turnstile wall on its signup stall the outreach/wave work.
- **`curl -s -o /dev/null -w '%{http_code}'` on a name you have not registered yet returns 000 —
  that is DNS, not availability.** Availability comes from RDAP/whois only.
- Deliverable files (XLSX/PDF/HTML) to this user are **pure English**; chat replies stay Hinglish.
- Brand isolation: a flip lander must never carry another company's name (HMW/Sanad/etc.).

## Verification
- [ ] Control tests passed in the same run as the candidate list
- [ ] Buyer class named with ≥20 real companies before registration
- [ ] `dig` MX + SPF on the domain, and a real test message received at `offers@`
- [ ] Lander live on the real domain (index 200, sitemap 200, form POST returns delivered:true)
- [ ] Inbound triage answered concretely: form-archive gap stated + `offers@` destination inbox named, catch-all state checked (§5b)
- [ ] Wave list: one contact per firm, every address published, sent log written

## References
- `references/domain-flip-economics.md` — verified 2026 registrar/comp/fee numbers and the worked
  `priordock.com` flip (timeline, wiring order, exact errors, decision record).
- `references/escrow-settlement-and-payouts.md` — escrow.com fee table, closing sequence, name-match
  rule, supported-country list, KSA vs India payout rails (purpose codes, e-FIRC, NRE/NRO), signup
  field map and the data-to-collect checklist.
- `scripts/avail_check.py` — availability checker with mandatory control tests; exits 1 when the
  method itself is unreliable.
