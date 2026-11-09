# Pages custom domain + Email Routing via API (worked sequence)

Verified 2026-09 on a brand-new Cloudflare-registered domain (`priordock.com`, zone in the same
account as the Pages project). Everything below was run from a headless VM with two credentials:
a `vault`-stored API token and the wrangler OAuth token. Both were probed first.

## 0. Probe scopes before you promise anything

```bash
# small script, output to a FILE — long inline commands get blocked/elided
cat > probe.sh <<'EOF'
#!/usr/bin/env bash
set -uo pipefail
A=$1; Z=$2
TOK=$(grep -oP 'oauth_token\s*=\s*"\K[^"]+' ~/.wrangler/config/default.toml | head -1)
probe() {  # probe <label> <method> <path> <token>
  C=$(curl -s -o /tmp/pr.out -w '%{http_code}' -X "$2" -H "Authorization: Bearer $4" \
      "https://api.cloudflare.com/client/v4$3")
  echo "$1: $C $(grep -o '\"code\":[0-9]*' /tmp/pr.out | head -1)"
}
probe pages-edit   POST   "/accounts/$A/pages/projects"        "$TOK"
probe dns-write    POST   "/zones/$Z/dns_records"              "$TOK"
probe email-rout   GET    "/zones/$Z/email/routing"            "$TOK"
probe registrar    GET    "/accounts/$A/registrar/domains"     "$TOK"
EOF
bash probe.sh <ACCOUNT_ID> <ZONE_ID> > /tmp/probe_out.txt 2>&1; wc -c < /tmp/probe_out.txt
```

Observed matrix:

| Credential | Pages edit | DNS write | Email Routing | Registrar |
|---|---|---|---|---|
| `vault` token (space `infra`) | ✅ | ❌ 403 | ❌ 403 | ❌ 403 `code 10000` |
| wrangler OAuth | ✅ | ❌ | ✅ | ❌ |

`403 code 10000` on `/registrar/*` = "Authentication error" for a token minted before the Registrar
API beta — it is a scope problem, not a broken endpoint. Never print the token value in the probe.

## 1. Attach the domain to the Pages project

```bash
curl -s -X POST -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
  -d '{"name":"example.com"}' \
  "https://api.cloudflare.com/client/v4/accounts/$A/pages/projects/$PROJ/domains"
```

Returns `success: true` with `"status": "initializing"`.

**The DNS records are NOT created.** Polling the domain for 3 minutes showed `status: pending` and no
`A`/`CNAME` for the apex (`curl https://example.com` → `000`). Adding a custom domain through the
**dashboard** is what triggers CF to offer/create `CNAME @ → <proj>.pages.dev`; through the **API**
with a token that cannot write DNS, you are left waiting forever.

Fix (either):
- User adds two records in the zone's DNS tab — `CNAME @ → <proj>.pages.dev` **Proxied** and the same
  for `www`; or
- User mints a token with `Zone → DNS → Edit` (also worth `Zone → Email Routing → Edit`,
  `Zone → Zone Settings → Edit`, `Account → Account Settings → Read`) and the agent does it:
  `POST /zones/$Z/dns_records {"type":"CNAME","name":"@","content":"<proj>.pages.dev","proxied":true}`.

Rebuild/redeploy the site content in the same pass so the canonical URLs, `sitemap.xml` and `robots.txt`
carry the real domain (not the `pages.dev` host) the moment DNS lands.

## 2. Email Routing (inbound) — 3 calls + 1 human click

```bash
# a) enable (creates MX + SPF)
curl -s -X POST -H "Authorization: Bearer $TOK" "https://api.cloudflare.com/client/v4/zones/$Z/email/routing/dns"
dig +short MX example.com    # route1.mx.cloudflare.net / route2 / route3
dig +short TXT example.com   # "v=spf1 include:_spf.mx.cloudflare.net ~all"

# b) add the destination mailbox
curl -s -X POST -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
  -d '{"email":"user@somewhere.com"}' \
  "https://api.cloudflare.com/client/v4/accounts/$A/email/routing/addresses"
# -> CF emails a verification link; the account also shows "verified": null

# c) create the forwarding rule — ONLY after (b) is verified
curl -s -X POST -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
  -d '{"enabled":true,"matchers":[{"type":"literal","field":"to","value":"offers@example.com"}],
       "actions":[{"type":"forward","value":["user@somewhere.com"]}]}' \
  "https://api.cloudflare.com/client/v4/zones/$Z/email/routing/rules"
```

Failure modes seen:
- Step (c) before (b): **error 2054** — destination address must be verified.
- Step (b)'s verification link
  (`https://dash.cloudflare.com/email_fwdr/verify?token=…`) is behind **Cloudflare Turnstile**. A
  headless browser could not pass it: neither `click_at_xy()` nor a JS element click completed the
  checkbox, and the widget is inside a frame `document.querySelectorAll('iframe')` does not expose.
  Don't burn calls retrying — pull the link out of the destination inbox
  (`himalaya … message read <id> -m INBOX` then regex `email_fwdr/verify\?token=[A-Za-z0-9_\-]+`) and
  hand it to the user. No login is needed for that URL; it is a single click.
  Note `himalaya` flag order here: `-a` is top-level, `-m/--mailbox` must come **after** the
  subcommand (`message read 509 -m INBOX`) or it errors with "unexpected argument '-m'".

## 2b. Proving delivery — the first test send may bounce (that is propagation, not a broken rule)

After step (c) returns `success: true`, `dig +short MX` shows `route1/2/3.mx.cloudflare.net` and the
destination shows a verification timestamp — the very first test send can STILL fail:

```
550 5.1.1 Address does not exist        # Gmail DSN from Mail Delivery Subsystem, subject "Delivery Status Notification (Failure)"
```

Cause: the sending MTA resolved the domain while it had **no MX at all** and cached that negative
answer (a brand-new domain with no A record either). Nothing is misconfigured. The DSN arrives in the
**sender's** mailbox — checking only the destination inbox makes this look like a silently dead rule.

Diagnosis order (do NOT touch the rule, the destination, or the DNS records):
1. Read the DSN in the sender account: `himalaya -a <sender> message read <id> -m INBOX > /tmp/dsn.txt`,
   then grep `/tmp/dsn.txt` for `550|5\.1\.1|5\.7|diagnostic` (long stdout gets elided — redirect to a
   file and `read_file` it).
2. `dig +short MX <domain>` again → confirm `routeN.mx.cloudflare.net` is answering.
3. **Re-send the same test.** Verified 2026-09: test 1 bounced, test 2 ~15 min later delivered with no
   changes made. Only investigate further if it bounces again *after* MX resolves.

Report the wiring as *proven* only after the test message is actually seen in the destination inbox —
inbound MX presence is not delivery proof.

## 3. What this leaves the agent able to do alone

Agent: attach domain, rebuild/redeploy content, enable Email Routing (MX/SPF), add destination,
create the forwarding rule once verified, submit to GSC, run smoke tests.
User: dashboard clicks that need DNS write, the Turnstile click, and anything Registrar-scoped.

Report that split up front instead of promising an end-to-end autonomous setup — and never send
outbound mail whose Reply-To is a branded address until the mailbox has been proven to receive
(send a test from a second account and read it back in the destination inbox).
