# Enquiry-form QA + bot pairing (multi-market brand-site fleets)

Companion to `lead-form-telegram.md`. That file builds the form; this one is the **QA pass** and
the pairing failure that only shows up on live traffic.

Context: the AZ advisory family (`~/clients/invertio/advisory-site/build/sites.py`) generates one
edition per market → each deployed as its **own** Cloudflare Pages project with its own
`functions/api/enquiry.js`. Fleet rule: **each market gets its own owner-facing Telegram bot**
(`@FLworkAz_Bot`/azwork, `@IndAzConsults_Bot`/indaz, `@KsaAzConsults_Bot`/ksaaz).

## 1. The pairing that breaks silently

Site form → Pages Function → Telegram chat, with the destination held in **project secrets**
(`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`). Functions read env **at deploy time**, and secrets are
per project (preview env does not inherit production's).

⇒ A site deployed **before** its market's bot existed keeps delivering into the **previous** bot's
DM. Real case (2026-09-21): the KSA edition's last deploy predated @KsaAzConsults_Bot, so KSA
enquiries were landing in the **India** bot's chat — a cross-brand leak visible from neither side
until a test lead was submitted.

**Detect:**
1. `npx wrangler@3 pages deployment list --project-name <p>` → newest deploy date; compare with
   when the market's bot went live.
2. Cloudflare's API **cannot read secret values back** — you cannot audit this remotely. Prove it
   empirically: submit ONE clearly-labelled test lead (`QA TEST — …`, throwaway address) and ask the
   owner which bot chat received it.
3. Ask the owner to confirm receipt — that single question is what converts suspicion into proof.

**Fix:** re-point the secrets + redeploy ONE time:
```bash
printf '%s' "$NEW_TOKEN" | npx wrangler pages secret put TELEGRAM_BOT_TOKEN --project-name <p>
printf '%s' "$CHAT_ID"  | npx wrangler pages secret put TELEGRAM_CHAT_ID  --project-name <p>
npx wrangler@3 pages deploy . --project-name <p> --branch master   # secrets need the redeploy
```
A production redeploy is a **user-approval step**: present it as a choice (redeploy now / preview
first / leave it) and list the local drift that would ship with it (here: an unpushed nav CSS
tweak + fresh sitemap dates). Keep `CLOUDFLARE_API_TOKEN` unset for inspection-only wrangler calls
(`env -u CLOUDFLARE_API_TOKEN …`) so a read command can never become a deploy.

## 2. Form QA matrix — run this on every edition

Spoof a browser UA (pages.dev 403s default urllib/requests agents):

1. POST the EN form → expect `303` → `/thanks` (or a JSON `{ok:true}`).
2. POST the `/ar` form → same; confirm the AR page is genuinely RTL **and** the handler accepts
   that edition's hidden market tag. An unknown tag is a **silent mis-route, not an error** —
   allowlist tags in the Function.
3. Honeypot (`website`) filled → expect the fake-success path with **no** Telegram send.
4. Missing contact method → expect the error path, never a silent ok.
5. `GET` on the endpoint → redirect, no send.
6. **Brand-leak grep of the generated HTML, both directions:** India-only portals/words in the KSA
   edition and vice versa (this family's leak class). One stale string is client-visible.
7. Live checks: extensionless URLs 200, a deliberate 404 behaves, security headers present
   (HSTS, CSP, XFO, COOP/CORP, permissions-policy), mobile fit at 320/360/390.
8. **Local-vs-live hash compare of `public/`** before any redeploy, so you know exactly what a
   redeploy would change — that converts "should be fine" into an approval fact.

## 3. Harness notes for this generator family

- `build/sites.py` regenerates every edition; `build/qa_sites.py` is the build gate (~21 pages,
  expect `0 findings`).
- `build/qa_mobile_fit.py` takes **no URL argument** — it sweeps the local HTML at 320/360/390;
  passing a URL fails. Run it bare.
- `build/verify_live.py`'s full-URL sweep can exceed a 300s foreground timeout: run it in the
  background or check a bounded subset, and pair it with a small script that asserts status +
  headers per URL.

## 4. Reporting the result (this is what "expertly QA it" means here)

Split the report into separate, plainly-labelled lines:
1. site/build QA (what passed, with counts);
2. bot side (metadata verified by read-back, avatar verified by round-trip);
3. **the leg you could not prove** + exactly what you need (approval, or the owner confirming
   which chat received the test lead) — including rollback.

Never fold an unverified delivery path into a "fully operational" claim. A named gap plus the exact
next action is the deliverable; a smooth summary that hides the unverified leg is not.
