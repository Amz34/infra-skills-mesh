# KV write budget: attribution, write-amplification fixes, staged client patches

Cloudflare KV free tier per **account** per UTC day: 1,000 writes · 1,000 deletes · 1,000 lists ·
100,000 reads. Every Worker and Pages Function on the account shares the same allowance — when it
is exhausted, `put` fails with **429 for all of them** (uptime monitors, chat rate-limits, site
analytics), so one noisy producer is an account-wide incident. (Sep 2026: a probe Worker wrote
3,456/day = 346% of budget; account at 68% by 04:40 UTC.)

## 1. Attribute the writes before changing anything

`grep -r <BINDING_NAME>` over the home dir finds **nothing** — binding names live in the deployed
bundle at the edge, not in local config/`wrangler.toml` copies.

```bash
# a) per-namespace / per-action counts for the UTC day (GraphQL analytics; KV analytics only
#    expose the `date` dimension — `dateHour` errors with unknown field, so sub-day rate is
#    SAMPLED, not queried)
python3 ~/ops/scripts/cf_kv_usage.py                  # -> WATCH_KV=707, AVVS_ANALYTICS=2
python3 ~/ops/scripts/cf_kv_usage.py --days 5
python3 ~/ops/scripts/kv_delta_check.py 900           # sampled before/after rate over 15 min

# b) namespace id -> title
curl -s -H "Authorization: Bearer $CF_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/$ACCT/storage/kv/namespaces"

# c) which script binds it (Workers AND Pages Functions show up here)
curl -s -H "Authorization: Bearer $CF_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/$ACCT/workers/scripts"
#    then read each script's settings/bindings; or pull the deployed source:
#    ~/ops/workers/<name>-deployed/  <- grep `.put(` in the DEPLOYED bundle
```
Token lives in `~/.secrets/cloudflare.env`. The `infra` scoped token is account-read only
(DNS/AI edits need wrangler OAuth) — see `secrets-vault-ops`.

`cf_kv_usage.py --watch N` samples; a 1-minute delta can read 0 because CF analytics lags 1–5 min
— judge changes over ≥15 min.

## 2. Write-amplification fixes (highest value first)

1. **Diff before write.** Keep `material(state)` = `ok|fails|alerted|status|has-error` and `put`
   only when it differs. Steady state = 0 writes. (Never include ms/timestamps/volatile error text.)
2. **Cap counters** — `fails = min(prev+1, THRESHOLD)`; an uncapped counter writes on every run for
   a permanently dead target.
3. **One heartbeat key, ≤1/hour** holding the whole summary the status page renders.
4. **`safePut()` wrapper** that catches and collects `write_errors` — alerting must survive an
   exhausted budget.
5. **Drop write-only keys.** A Pages Function pageview tracker wrote `d:<date>` plus the lifetime
   key on every hit; nothing read `d:<date>` (`/api/stats` serves the lifetime key, which already
   carries `all.days[date]`). Removing the dead key: 2 puts → **1 put per pageview**. Always grep
   the key's consumers before deleting a write; then keep a `.bak-YYYYMMDD` next to the file.
6. **Deleting keys is not a fix.** Deletes spend their own allowance and refund nothing to the
   write counter; a healthy monitor has ~11 state keys + heartbeat and no "spam" to clean.
   Edge-cache purges are unrelated to KV quota.

## 3. Prove it with a local harness (Pages Function / Worker)

```js
// mock KV that counts ops; import the real handler and drive N requests
const kv = {n:{g:0,p:0}, _d:{}, async get(k){this.n.g++; return this._d[k]??null;},
            async put(k,v){this.n.p++; this._d[k]=v;}};
const { onRequestGet } = await import('/abs/path/functions/api/t.js');
for (let i=0;i<301;i++) await onRequestGet({request:new Request('https://x/api/t?p=/&r=g.com'), env:{AVVS_ANALYTICS:kv}});
console.assert(kv.n.p === 301, 'expect exactly 1 write per pageview');
```
Then confirm the fix is **live**: compare the local file mtime with the deployed build time from
the workers/scripts API (`modified_on`) — deployed older than the fix = the edge still runs the old
code.

## 4. Client-facing writes: stage, verify, then ask

Client-facing Workers/Pages changes follow the same discipline as client sites: patch locally, keep
the `.bak`, prove the write count in a local harness, and **do not deploy without approval** (offer
a preview branch first). Report the remaining risk in the user's terms: "today 2 pageviews, so it
does not matter yet — a busy day would have doubled writes into the cap."
