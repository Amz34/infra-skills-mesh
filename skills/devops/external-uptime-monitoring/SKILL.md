---
name: external-uptime-monitoring
description: Use when a server needs alerting that outlives it.
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [monitoring, uptime, cloudflare-workers, redis, alerting]
    related_skills: [cron-watchdog, infra-hardening-crashproof, cloudflare-pages-workers-ops]
---

# External uptime monitoring + alert queue

## When to Use
- "Koi external probe nahi hai — VM mar gaya to client complaint tak pata nahi chalega"
- A client site / Pages project / tunnel needs uptime monitoring with alerts that reach a human
- Async work needs retries + dead-letter instead of `cron + log files`
- Alerts must survive the monitored host dying (so the probe/alert path must be off-host)

Use when the ask is "koi external probe nahi hai — VM mar gaya to pata nahi chalega", when
adding client-site monitoring, or when async alerts need retries instead of cron+files.

## Why two layers
| Layer | Runs on | Catches |
|---|---|---|
| Edge probe (Cloudflare Worker) | CF edge | whole-VM death, client site down, DNS/TLS breakage |
| Local watchdog (`svc-watch.py`) | the VM itself, cron */10 | degraded-but-alive: disk, redis, worker, containers, gateway procs, backup freshness |
| Alert queue (Redis) | the VM | delivery retries + dead-letter for whatever the watchdog finds |

Edge probe must never depend on the monitored host, otherwise a dead host also kills the alert.

## Step 1 — edge monitor (Cloudflare Worker, free)
```bash
mkdir -p ~/cf/hermes-watch/src && cd ~/cf/hermes-watch
# wrangler.toml: name, main=src/index.js, compatibility_date, [triggers] crons=["*/5 * * * *"]
npx --no-install wrangler whoami                 # confirm account (OAuth token in ~/.wrangler)
npx --no-install wrangler kv namespace create WATCH_KV     # paste id into wrangler.toml
printf '%s' "$TOKEN"  | npx --no-install wrangler secret put TG_BOT_TOKEN
printf '%s' "$CHAT"   | npx --no-install wrangler secret put TG_CHAT_ID
printf '%s' "$RANDOM" | npx --no-install wrangler secret put ADMIN_TOKEN   # save to ~/ops/secrets/
npx --no-install wrangler deploy                 # prints https://<name>.<subdomain>.workers.dev
```
Worker shape: `DEFAULT_TARGETS` array (id/name/url/optional keyword) seeded into KV key
`targets`; per-target state in KV `s:<id>`; one `hb` heartbeat key; `fetch` serves `/` (HTML),
`/status` (JSON), `/run?t=ADMIN_TOKEN&force=1`; `scheduled` runs checks. Alert after 2
consecutive fails, once; one recovery alert; no repeat spam while down. Keyword check catches
"200 but page is broken". State is written **only when the material state changes** (see the KV
budget section below) and every KV write goes through `safePut()` so a 429 can never stop alerting.

Response shapes (they differ — don't assume):
- `/run` → `{"at": ts, "writes": 1, "write_errors": [], "results": [ {id,name,url,status,ms,ok,fails,alerted,since,last_check,last_ok} ], "alerts": [ {id,kind:"down"|"recovered",sent:{ok,status,message_id}} ]}`
- `/status` → `{"heartbeat": {at,total,down,targets[]}, "last_run": {at,total,down}, "targets": [ ...merged rows... ]}`
- `/status` is edge-cached 60s (`caches.default`): when validating right after a forced `/run`,
  re-fetch after ~70s or you'll read the pre-run payload.

## KV write budget — the free tier is ACCOUNT-WIDE (read before writing any state)
KV free tier is **per account per UTC day**: read 100k / write 1k / delete 1k / list 1k. One
Worker that writes state on every probe run spends it for *every* Worker on the account; once
the budget is gone, writes fail with 429 for all of them. Real incident (2026-09-17): this
worker wrote 12 keys per run (11 `s:<id>` + `last_run`) × 288 runs/day (cron `*/5` per-UTC-day)
= **3,456 writes/day = 346% of the budget** → Cloudflare
`[Alert] KV daily operation limit 50% reached` email; account was at 68% by 04:40 UTC and the
client analytics + chat rate-limiter were silently getting failed writes.

Write-cost rules for any probe/telemetry Worker:
- **Diff before write.** Keep `material(state)` = `ok|fails|alerted|status|has-error` (*never*
  ms / timestamps / volatile error strings) and `put` only when it differs from the stored
  record. Steady state = **0 writes**.
- **Cap the failure counter** (`fails = min(prev+1, FAIL_THRESHOLD)`), otherwise a permanently
  dead target writes on every single run (288/day per target).
- **Freshness = one heartbeat key, ≤1/hour** (24 writes/day) holding `{at,total,down,targets[]}`;
  write it early when the down-count or target count changes. The status page merges heartbeat
  vs state record by newest `last_check`, so the display stays fresh while writes stay near zero.
- **Never let a write failure kill the run**: `safePut()` catches and collects `write_errors`;
  alerting must survive an exhausted budget.
- Cost proof lives in the repo: `node test/kv-budget.test.mjs` (9 tests) and
  `node test/budget-report.mjs` (measured: healthy 35 writes/day = 3.5%, 1 dead target 36,
  all 11 dead 46, 1 flapping hourly 70 → worst case 7% of the budget).

Guard rails (do both — code discipline plus an independent watchdog):
```bash
python3 ~/ops/scripts/cf_kv_usage.py             # today per namespace/action (GraphQL)
python3 ~/ops/scripts/cf_kv_usage.py --watch 15  # 15-min sampled burn rate (per namespace)
python3 ~/ops/scripts/cf_kv_usage.py --guard --dry-run   # watchdog verdict, no Telegram
python3 ~/ops/scripts/cf_kv_usage.py --guard     # watchdog: silent if healthy, TG if not
python3 ~/ops/scripts/kv_delta_check.py 900      # before/after write rate over 15 min
python3 ~/ops/scripts/hw_probe.py                # live /status + forced-run summary
```
Cron (installed): `*/30 * * * * /usr/bin/python3 /home/ubuntu/ops/scripts/cf_kv_usage.py --guard >> /home/ubuntu/ops/logs/kv-guard.log 2>&1`
- WARN at 60% used / 70% projected, CRITICAL at 85% / 95%; the projection is skipped until 10%
  of the UTC day has elapsed; dedup (same level ≤1/6h, escalation immediate) in
  `~/ops/state/kv-guard.json`; alert goes straight to Telegram (not via the queue/gateway, so a
  dead VM still gets the warning).
- GraphQL gotcha: KV analytics only expose the `date` dimension — `dateHour` returns
  `unknown field "dateHour"`, so sub-day burn must be **sampled** (`--watch`), not queried.
- Know the other writers on the account: `projects/aone-chat-worker` (1 KV put per rate-limited
  request) and `clients/AVVS-Triatek/site/functions/api/t.js` (**2 puts per pageview** — 500
  views/day alone would consume the whole daily budget). Merge day+lifetime into one key
  (1 put/view) or move analytics to Cloudflare Web Analytics before driving traffic to such a site.

Recovery is only proven when the *same target id* goes broken → fixed. Deleting the broken
target from KV emits nothing (the state key just goes stale) — test it properly:
1. KV `targets` = `[{id:"p2-recovery-test", url:<healthz>, keyword:"__never__"}]`, wait 75s, `/run` twice → `kind:"down"` + `message_id`
2. KV `targets` = same id with `keyword:"ok"`, wait 75s, `/run` → `kind:"recovered"` + `message_id`, `alerted:false`
3. delete the KV override (falls back to `DEFAULT_TARGETS`), wait 75s, `/run` → target count back to full

## Step 2 — verify alerting for real (do NOT skip)
Break something on purpose, run twice, check the Telegram `message_id` in the response:
```bash
T=$(cat ~/ops/secrets/hermes-watch-admin.token)
curl -s -A "Mozilla/5.0" "https://hermes-watch.<sub>.workers.dev/run?t=$T"
# point a target at a wrong keyword via KV, wait 75s, run twice -> DOWN alert
# delete the KV override, wait 75s, run again -> RECOVERY alert
```
An untested monitor is not a monitor.

## Step 3 — local watchdog producer
`~/ops/scripts/svc-watch.py`: checks dict of (disk %, redis ping, queue worker unit, gateway
process count, docker container health, newest backup artefact age), compares against
`~/ops/state/svc-watch.json`, and only on state change enqueues a `notify` job. Flags:
`--dry-run` (no writes), `--self-test` (inject synthetic failure to prove the path).
Cron: `*/10 * * * * /home/ubuntu/.venvs/data/bin/python /home/ubuntu/ops/scripts/svc-watch.py >> ~/ops/logs/svc-watch.log 2>&1`

## Step 4 — alert queue (Redis)
```bash
# redis:7-alpine, 127.0.0.1 bind, requirepass from ~/ops/secrets/hermes-redis.pass, AOF on
docker run -d --name hermes-redis --restart unless-stopped -p 127.0.0.1:6379:6379 \
  -v ~/ops/redis/data:/data redis:7-alpine \
  redis-server --requirepass "$PASS" --appendonly yes --maxmemory 256mb --maxmemory-policy noeviction
```
Topology: `hermes_queue.py` (enqueue/take/requeue_or_dead/stats) + `worker.py` (systemd
`hermes-queue-worker`, venv python) + keys `hermes:jobs` / `hermes:done` / `hermes:dead`.
Handlers: `notify` (Telegram via `TELEGRAM_BOT_TOKEN` from `~/.hermes/.env` and
`TELEGRAM_HOME_CHANNEL`), `site_check`, `echo`.

## Pitfalls (all hit in practice)
1. **Never name the module `queue.py`** — shadows stdlib `queue`; redis-py dies with
   `ImportError: cannot import name 'Empty'`. Use `hermes_queue.py`.
2. **UptimeRobot free plan API is read-only**: `newMonitor`/`editMonitor` return
   `access_denied: You are not allowed to use some settings with your current plan`, and
   free API is capped at 10 req/min (`Rate limit exceeded, retry in N seconds`). Use the UR
   dashboard for edits, or build the CF Worker instead. Also: UR monitors created earlier may
   have **no alert contact attached** — silently useless.
3. **Python urllib gets 403 from workers.dev** — send a browser User-Agent (or use curl).
4. **KV reads cache ~60s** — after editing `targets`, wait ~75s before trusting a run.
5. `redis` BRPOP socket timeouts are normal; swallow `TimeoutError`, don't log as loop errors.
6. Bearer of the Telegram alert = the Hermes bot token; a Worker that only *sends* messages
   will not conflict with the polling gateway (no 409).
7. Monitoring target should be a URL that actually exists: `.pages.dev` for an empty Pages
   project returns 404 and an unregistered custom domain returns NXDOMAIN → false "outage".
8. **`--dry-run` must not persist dedup state.** A watchdog that records "alerted" while
   suppressing the send silences the next real alert for the whole dedup window. Keep
   `if dry_run: return` *before* `save_state()` — hit and fixed in `cf_kv_usage.py`.
9. Use `force=1` to test the probe path without spamming Telegram (state still updates, sends
   are tagged `sent.skipped = "forced run"`).
10. Cloudflare analytics has ~1–5 min latency: a 1-minute sampled delta can read `write=0` even
    though runs happened. Judge budget changes over ≥15 min (`kv_delta_check.py 900`).

## Verification checklist
- `systemctl is-active hermes-queue-worker` = active, `is-enabled` = enabled
- `docker ps` shows hermes-redis with `127.0.0.1:6379->6379`
- `hermes_queue.py stats` → done>0, dead=0
- `/status` JSON → all targets ok, last_run total matches target count
- one deliberate DOWN + one RECOVERY alert observed with Telegram `message_id`
- `node --test ~/cf/hermes-watch/test/kv-budget.test.mjs` → 9/9 pass, and
  `node ~/cf/hermes-watch/test/budget-report.mjs` → worst case <10% of the 1,000 writes/day
- live cost of a forced run: `python3 ~/ops/scripts/hw_probe.py` → `writes: 1` when nothing
  changed (was 12 before the fix), and `python3 ~/ops/scripts/kv_delta_check.py 900` → 0 extra
  writes over 15 min in steady state
- `python3 ~/ops/scripts/cf_kv_usage.py --guard` → prints nothing and exits 0 on a healthy day
  (one real Telegram alert observed once, so the path is proven)
