# Domain flip economics + worked case (`priordock.com`, 2026-09)

All numbers below were read live during the session (registrar pages, RDAP/WHOIS, public sale
reports, API responses) — treat them as dated observations, re-verify before quoting to a user.

## Market comps (public, 2026)
| Datapoint | Value |
|---|---|
| `bot.ai` | $1.2M (Sedo, Feb 2026) |
| `orchestra.ai` | $250k — bought in 2021 for ~$2,901 (≈100×) |
| `.ai` total 2026 sales volume | $27.1M (+189% YoY) |
| `.com` public sale median | ~$549; 99.4% of sales under $10k |
| Industry sell-through | ~1% of names per year |

Implication to state honestly: median outcomes are three figures. A single-name flip is a
**buyer-selection** exercise, not a volume play.

## Fee / transaction matrix
| Channel | Fee |
|---|---|
| Afternic (network / buy-now) | 25% / 30% |
| Sedo | 10–20% |
| Atom (Squadhelp) | 7.5% / 4.5% |
| escrow.com | ~2.6% |
| Same-registrar account push | $0, **instant** |
| Cross-registrar transfer | ICANN **60-day lock** from registration, then day-61 |

## Registrar quotes captured (2026-09)
| Registrar | Price | Payment | Notes |
|---|---|---|---|
| Porkbun | $11.06 flat | PayPal, crypto | flat renewal, free privacy, API |
| Dynadot | $10.88 flat | PayPal, crypto, bank wire, Alipay | mature API |
| Namecheap | $10.98 promo → **$18.48 renewal** | card, PayPal | renewal cliff flagged to user |
| Spaceship | $5.98 → $11.98 | card, PayPal | Namecheap-owned |
| Njalla | ~$15 | crypto, PayPal | proxy owner, no API |
| Cloudflare Registrar | at-cost (.com ≈ $10.44) | card on file | Registrar API beta; `/registrar/*` → `403 code 10000` without `Registrar:Edit` |

## Worked flip timeline
1. **Name selection** — trendy AI stems measured ~96% taken (`agent*`/`prompt*`/`model*`; 7,668
   candidates → 3,458 "free", all junk). Pivoted to a vertical compound: `prior` + `dock` (11 chars)
   for prior-authorization vendors, whose rename pressure comes from CMS-0057-F (deadline 1 Jan 2027).
2. **Buyer list first** — 35 verified targets (36/36 domains resolving with MX, 11 published emails,
   33 contact-form URLs returning 200, 29 LinkedIn slugs taken from the companies' own sites).
3. **Registration** — user registered at Cloudflare Registrar (2026-09-11 23:09 UTC, expiry
   2027-09-11, NS `kim.ns.cloudflare.com` / `salvador.ns.cloudflare.com`). Payment/registrar
   comparison was supplied first (table above), but the user chose the account he already had.
4. **Wiring order that worked** (2 items stayed user-side):
   - attach domain to Pages project (`POST /accounts/<a>/pages/projects/<p>/domains`) → **stays
     `pending`**, DNS records NOT auto-created by the API; needs `Zone:DNS:Edit` or two manual proxied
     CNAMEs (`@`, `www` → `priordock-forsale.pages.dev`). `curl https://priordock.com` → `000` until then.
   - Email Routing enabled → **MX `route1/2/3.mx.cloudflare.net` + SPF `include:_spf.mx.cloudflare.net`
     confirmed via `dig`** (domain can receive mail with no mailbox).
   - destination verification link is behind Cloudflare **Turnstile** → headless click failed → link
     extracted from the inbox and handed to the user (no login needed). Rule creation before
     verification → **error 2054**.
   - lander rebuilt against the real domain, redeployed, form smoke-tested (`POST /api/inquiry` →
     `{"ok":true,"delivered":true}`).
5. **Outreach** — Wave 1 = 10 verified addresses, one per firm, 20 s pacing, From = genuine human
   name, Reply-To = `offers@<domain>`, no price in the first email (invite an offer + escrow route);
   day 4 / day 9 follow-ups only to non-responders.

Ask/floor recorded for this name: ask $2,400, floor $1,800, escrow ~2.6%, lease-to-own $250 × 12.

## Decision record (reversal conditions)
- Chose **Play A** (naming + launch kit pipeline) over blind portfolio flipping, because the database
  of buyer-side companies is the scarce asset, not the names.
- Blind cold-flipping is negative EV unless a watchdog (expiring-name monitoring in a vertical you
  already sell into) drives the buys.
- Registrar/API autonomy was **not** achievable with existing credentials — recorded as a scope wall,
  not re-attempted per flip.
