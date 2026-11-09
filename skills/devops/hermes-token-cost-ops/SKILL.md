---
name: hermes-token-cost-ops
description: "Use when API balance drains fast or tokens overconsume."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, tokens, cost, balance, compression, sessions, deepseek]
---

# Hermes Token & Cost Ops

## When to Use

- User reports API balance draining fast or asks "tokens zyada consume ho
  rahe hain / balance drain ho raha hai kya wajah"
- Routine provider balance checks (DeepSeek, Gemini) show unexpected drops
- A long-running gateway session's context keeps growing and cost is climbing
- User weighs a $20 subscription (Claude Pro / ChatGPT Plus) against an API
  bill of ~$100/mo and asks "kaam chalega kya / difference kya hai / fayda
  nuksan batao" — answer with measured usage, structural facts (no API key on
  subs), and the optimised-API alternative before agreeing to switch
- User has ~$0 / near-zero API balance and wants the system to keep running
  on free models ("free models rotate karo, drain se pehle doosra linked")

Diagnose and fix API balance drain / token overconsumption in a running
Hermes gateway — and in deployed endpoints that share the same API key.

## Diagnosis (in order)

### 1. Balance — confirm the drain is real

```bash
KEY=$(grep -oP 'DEEPSEEK_API_KEY=\K.*' ~/.hermes/.env | head -1)
curl -s --max-time 10 "https://api.deepseek.com/user/balance" \
  -H "Authorization: Bearer $KEY"   # → total_balance
```

**What `/user/balance` can and cannot tell you:** it returns ONLY the
current split (`total_balance` / `granted_balance` / `topped_up_balance`)
— no historical consumption, no top-up ledger, no dates. Lifetime spend
is NOT derivable from the API alone; the formula is
`Σ top-ups (console) − current balance = true lifetime consumption`.

### 2. Find the cost-driving session (state.db)

Hermes tracks per-session cost in `~/.hermes/state.db` (`sessions` table +
`session_model_usage`). The killer query:

```sql
SELECT id, title, message_count, api_call_count,
       input_tokens, output_tokens, cache_read_tokens,
       estimated_cost_usd, actual_cost_usd, last_activity_at
FROM sessions
ORDER BY estimated_cost_usd DESC NULLS LAST LIMIT 10;
```

**The hidden multiplier is `cache_read_tokens`** — it shows how many tokens
were re-sent per call. A session with 554 messages can carry ~255K tokens of
context per API call and 100M+ cache-read tokens over its life. With 3-10
API calls per user turn, one giant session alone can burn $2+ in 2 days.

### 3. Check gateway logs for retry storms

```bash
journalctl --user -u hermes-gateway --since "yesterday" --no-pager \
  | grep -iE "Context:|Rate limited|Final error|Quota exceeded"
```

Signs of trouble: `Context: N msgs, ~250,000+ tokens` lines, repeated
`429`/`RESOURCE_EXHAUSTED` from a fallback provider (each retry re-sends
the whole context — 3 retries × 255K tokens of pure waste).

## Whole-agent / per-profile usage audit

For "what has our usage actually cost till now?" questions, each Hermes
profile keeps its own DB at `~/.hermes/profiles/<name>/state.db` with a
`sessions` table of per-session usage. Aggregate across ALL sessions:

```python
import sqlite3
db = sqlite3.connect('file:/home/ubuntu/.hermes/profiles/<name>/state.db?mode=ro', uri=True)
rows = db.execute("""
  SELECT COUNT(*), SUM(input_tokens), SUM(output_tokens),
         SUM(cache_read_tokens), SUM(reasoning_tokens),
         SUM(api_call_count), ROUND(SUM(estimated_cost_usd),2)
  FROM sessions""").fetchall()
```

Baseline sanity (invertio profile agent, 2026-09, 54 sessions/~30d): 10.1M
input + 2.85M output + 199M cache-read tokens, 3,039 API calls, est ~$2.76 —
cache_read dominance means context caching is working; a whole always-on
agent runs at ~$3/month on DeepSeek. Treat `estimated_cost_usd` as an order
of magnitude (billing columns are often 0/'unbilled'); cross-check the live
balance with the PROFILE's own key in `~/.hermes/profiles/<name>/.env`.

- **Live profile DBs refuse plain connects** (guard/write-lock, exit 1) —
  the read-only URI form above always works; run it from execute_code.
- **Paid-subscription decisions** ("is X worth subscribing to?"): anchor on
  measured usage, not vibes — (1) actual all-agent cost is the
  subscription's real competitor, (2) evidence-check whether the tool was
  EVER used by searching the profile `messages` table, (3) fit vs the
  actual delivery pipeline + credit mechanics (monthly credits expire =
  retention hook). Worked example, queries, and the verdict framing that
  landed (v0 Premium $20/mo): `references/agent-usage-audit.md`.
- **Pitfall:** `content LIKE '%toolname%'` on profile `messages` also hits
  compaction-handoff boilerplate (system summaries re-mention tool names) —
  print actual rows and restrict `role IN ('user','assistant')` before
  concluding "never used".

### Reconciling "I spent ~$X" claims (user disputes your estimate)

Tracked cost (~$20) vs the user's claimed spend (~$50): the gap is almost
never bad arithmetic — it's untracked burn + coverage windows. Worked
method, scripts, and the DeepSeek-vs-Kimi rate table:
`references/spend-reconciliation.md`. Order of checks:

1. **Coverage window** — profile `state.db` only holds sessions since
   profile creation / last VM migration; older usage is invisible. Say so
   instead of implying the DB is complete.
2. **Untracked direct-API consumers** — `grep -rl DEEPSEEK_API_KEY
   ~/.hermes/scripts ~/clients ~/projects`: scripts calling the provider
   with the same shared key never write to any session DB (found: live
   ai-lead-qualifier scorer, carousel gen, lead_pipeline, resume/brief
   bots, demo multi-agent repos). A live client-facing scorer can
   out-burn every Hermes session combined.
3. **Recompute at official rates** — don't trust `estimated_cost_usd`
   alone; multiply token sums by the model's $/M triplet from
   `~/.hermes/hermes-agent/agent/usage_pricing.py`
   (reasoning NOT billed separately). Cache reads ≈ free → 1.6B cache
   tokens ≈ $4.5. **The card you find in that file may be STALE** — Hermes'
   built-in snapshot keeps pre-change numbers after a provider repriced
   (it still carried the retired $0.14/$0.28/$0.0028 DeepSeek card for
   weeks after the 16 Aug 2026 change). Always re-derive from the live
   pricing page first; current cards + off-peak windows:
   `references/provider-rate-cards-and-peak-windows.md`.
4. **Live balance as burn evidence** — balance sampled hours apart during
   agent activity ($0.75 → $0.70) demonstrates the burn rate on the user's
   own key; "$0.70 left after a ~$50 top-up" is itself consistent with
   ~$49 lifetime consumption.
5. **Provider consoles = OTP login-walled** — platform.deepseek.com and
   platform.kimi.ai/console/account need the user's login; no stored
   creds, never guess. Ask for screenshots of the top-up/usage pages to
   finish exact reconciliation; for rate-only comparison use the table in
   the reference (DeepSeek native ≈ 20× cheaper than Kimi K2.6 on
   cache-heavy agent workloads).

### Direction of error: our meter can OVER-state — test BOTH ways (2026-09-26)

Everything above hunts *under*-reporting. Measured on this VM the error ran the
other way and was bigger (user: "lagta hai zyada consume ho raha hai"):

| Source, same 7-day window | Run-rate | vs reality |
|---|---|---|
| `sessions.estimated_cost_usd` | ~$7.98/7d ≈ $34/mo | **3.4× high** |
| `ds_spend_reconcile.py` peak-aware card | ~$15.43/7d ≈ $66/mo | **6.5× high** |
| **balance ledger (ground truth)** | $5.29 / 15.6d = **$0.34/day ≈ $10/mo** | — |

…and token *volume* was **down ~40% WoW** (calls 15,339 → 8,937; input 54.3M →
32.7M; cache-read 1.14B → 659M). "Consuming more" was a **display artifact**, not
a trend. Rules:

- **Balance drain is the ONLY ground truth.** Headline the drain-derived
  run-rate; quote the tracked number as an explicit *upper bound* and say which
  is which. Never let a spend decision rest on the tracked number alone.
- **Prove the instrument is alive BEFORE quoting any delta** — a silently dead
  sampler looks exactly like "no spend". The `ds-balance-sampler` cron had been
  dead **15 days** (newest sample 11 Sep) → no alerts, no series. Check the
  newest `ts` age in `ds_balance.jsonl` (>1 h = stale), reinstall the cron, and
  take a fresh sample before analysing. (Restored sampler immediately reported
  `balance LOW: $1.77 (threshold $5.00)` = ~5 days of runway at $0.34/day.)
- **Group `session_model_usage` by `model`, not only `task`** — untabled models
  report `$0.00` *with* real call counts (`deepseek-flash`: 2.32M in / 1.78M out
  / 651 calls at $0.00) and vanish from every ranking.
- **Headline `SUM(input+cache_read)/SUM(api_call_count)`** — context **per call**
  is the cost dial (measured 86–92k tokens/call; 7,012 calls → 604M context
  tokens/week). Session/call counts are the wrong dials to optimise.
Worked numbers, the liveness snippet, and the sampler-reinstall procedure:
`references/meter-overstatement-and-sampler-liveness.md`.

## Current DeepSeek card + peak windows (READ THIS BEFORE QUOTING $/mo)

Rates change without notice and the change is easy to miss because the
*shape* of the workload hides it. DeepSeek V4.1-Flash (live 16 Aug 2026),
per 1M tokens — cache-hit / cache-miss input / output:

| Window | Cache hit | Miss input | Output |
|---|---|---|---|
| Off-peak | $0.003 | $0.15 | $0.60 |
| Peak (2×) | $0.006 | $0.30 | $1.20 |

Peak = **01:00–04:00 and 06:00–10:00 UTC, Mon–Fri** (= 06:30–09:30 and
11:30–15:30 IST). Weekends are off-peak all day. Full cards (DeepSeek,
Claude Sonnet/Haiku, GPT-5) + cache economics + the subscription-vs-API
structural facts: `references/provider-rate-cards-and-peak-windows.md`.

**Rule: quote the run-rate from the trailing 7 days at the CURRENT card.**
A 30-day average silently understates the bill when activity ramped
(measured case: 30d average ≈ $66/mo vs 7d run-rate ≈ $94/mo → the user's
"~$100/month" was right and the average was the misleading number).
On this VM `date` is UTC and cron schedules are UTC — do the peak math in
UTC, then convert to IST for the user.

### Task-level overhead attribution — where the money actually goes

`sessions` gives per-session totals; `session_model_usage` is the table
that splits the bill by *what kind of call* it was (`task`, `provider`,
`model`, `input_tokens`, `output_tokens`, `reasoning_tokens`,
`cache_read_tokens`, `api_call_count`, `estimated_cost_usd`,
`first_seen`/`last_seen`). Group by `task` across all profiles:

```python
for n, db in DBS:   # state.db + profiles/*/state.db, read-only URI
    for task, usd, calls in c.execute("""SELECT COALESCE(task,''),
            SUM(estimated_cost_usd), SUM(api_call_count)
        FROM session_model_usage WHERE last_seen>=? GROUP BY 1""", (since,)):
        cost[(n, task)] += usd; cnt[(n, task)] += calls
```

Measured baseline (30d, all profiles): main agent work 72.1% of spend,
**`compression` 16.0%** (1,228 calls — ~5× the cost *per call* of normal
work, because each one re-sends the whole context), **`background_review`
10.8%** (2,775 calls, i.e. `agent.verify_on_stop: true`), `approval` 1.2%.
→ **~27% of the bill is Hermes' own overhead, not user work.** Those two
buckets are the real budget levers; quote them before proposing a
provider switch.

### Instrumented untracked-burn reconciliation

The provider API has NO usage endpoint (only `/user/balance`), so the
untracked delta (direct-API client scripts + apps) must be measured as
`actual drain − Hermes-tracked spend`. Wire it once:

- `~/ops/scripts/ds_balance_log.py` — appends `{ts, iso, currency, total,
  topped_up, granted, available}` to `~/ops/observability/ds_balance.jsonl`
- `~/ops/scripts/ds_spend_reconcile.py [days]` — tracked spend per profile
  at the current card vs actual drain → prints the untracked delta
- cron `ds-balance-sampler` (`*/30 * * * *`, `no_agent`) for the samples;
  needs ≥2 samples spanning the window, so report the delta only after
  ~24h — never extrapolate from one sample.
- **cronjob API quirk:** `script` MUST be relative to `~/.hermes/scripts/`;
  an absolute or `~/ops/...` path is rejected. Put a one-line wrapper
  there (`exec python3 "$HOME/ops/scripts/<real>.py"`) and keep the logic
  in `~/ops/scripts/`. Skill copies of both scripts:
  `scripts/ds_balance_sampler.py`, `scripts/ds_spend_reconcile.py`.
- Nothing in `~/.hermes/scripts/` that cron runs may be *assumed* free OR
  billable — grep it for LLM endpoints before saying either.

### Config levers that cut cost without losing capability

Ranked by measured impact at a ~$100/mo run-rate (output+reasoning was
64% of the bill, input only ~26% — so token *output* discipline first):

| Lever | Change | Est. saving/mo |
|---|---|---|
| reasoning discipline | `reasoning_effort: medium → low` on routine profiles | $15–25 |
| background review | `agent.verify_on_stop: false` on high-volume profiles | $10–12 |
| compression tuning | `compression.threshold_tokens 60k→90k`, `threshold 0.5→0.6` | $6–8 |
| off-peak batch shift | only agent/batch jobs, not script-only crons | $4–6 |
| free-chain routing | routine/bot chatter → free tier / local model | $10–20 |

Sum ≈ $45–60/mo with automation intact — beat that before recommending a
subscription migration. Config changes alter behaviour: propose with the
numbers, apply after an explicit yes, and measure before/after.

### Permanent off-peak cron rule (Aamir, 2026-09-27) — already installed

**Rule: every cron job that can call an LLM fires only in DeepSeek off-peak
hours** (peak = 01:00–04:00 and 06:00–10:00 UTC Mon–Fri; weekends free). This
is saved permanently, not a per-session suggestion — check for it before
proposing any new schedule:

- Policy doc: `~/brains/ops/rules/cron-offpeak-only.md`
- Enforcer: `~/ops/scripts/cron_offpeak_guard.py` (wrapper
  `~/.hermes/scripts/cron_offpeak_guard.sh`) — scans 35 days of fire times,
  rewrites violating hour fields to the mid-off-peak anchors **05:00 / 11:00**
  (minute + day fields preserved), wildcard-hour jobs → hours `0,4,5,10-23`.
  Fixes disabled jobs too, so a resumed job can't return on a peak schedule.
- Automator: cron job `cron-offpeak-guard`, hourly `17 * * * *`, `no_agent`
  → prints only when it actually reschedules something, so a new peak job is
  caught within the hour. Manual: `--apply` / `--json` / `--include-scripts`.
- **Billable** = `no_agent: false` OR a `monitor_script`/`monitor_url` present
  (a monitor job invokes the agent whenever the monitor output changes).
  Script-only jobs are exempt on purpose: they burn $0 tokens and moving them
  also blinds 24/7 crash watchdogs for 7h/weekday — a fake saving.
- Honest limit: a job that *starts* off-peak but runs long enough to cross
  into a peak window is not fixable by scheduling; keep long agent jobs short.

## Root causes

1. **Session bloat + compression too loose.** Default `compression.threshold`
   is 0.5 of context — with no `threshold_tokens` cap, a long conversation
   grows until every call re-sends a huge context.
2. **Fallback provider on an exhausted free tier.** Gemini free tier caps at
   ~250K input tokens/day; once hit, every fallback attempt returns 429 and
   Hermes retries 3× with the full context. The retries cost time and tokens
   even when the primary provider would have succeeded.
3. **Monster archived-able sessions.** Old sessions that are never archived
   keep their token history and can be resumed accidentally.
4. **Deployed LLM-proxy endpoint sharing the key.** A client/demo chat
   widget (Cloudflare Pages Function calling `api.deepseek.com` with
   `env.DEEPSEEK_API_KEY`) is public, unauthenticated, CORS `*` — anyone
   with the URL can chat or script the endpoint directly and burn the same
   balance Hermes uses. Full audit + fix recipe:
   `references/deployed-llm-endpoint-token-burn.md`.

## Fixes (safe, in order)

### Compression caps — set explicit token thresholds

```bash
hermes config set compression.threshold_tokens 90000      # compress at 90K
hermes config set compression.proactive_prune_tokens 60000  # prune old ctx at 60K
hermes config set compression.protect_last_n 12           # keep last 12 msgs safe
```

`threshold_tokens` (absolute) is more reliable than the 0.5 ratio alone for
long-running gateway sessions. `protect_last_n` ensures recent context is
never cut. Config changes apply without restarting anything for next turns.

### Archive stale monster sessions

```python
import sqlite3, os
conn = sqlite3.connect(os.path.expanduser('~/.hermes/state.db'))
cur = conn.cursor()
cur.execute("""
    UPDATE sessions SET archived = 1
    WHERE id = '<monster-session-id>'
      AND last_activity_at < strftime('%s','now') - 172800  -- 2+ days stale
""")
conn.commit()
```

**Never archive the CURRENT chat's session** — that's the one the user is
talking to. Identify it by matching `last_activity_at` to the live
conversation before touching anything.

### Fallback hygiene

Two valid chain designs — pick by budget:

- **Paid-primary (normal ops):** primary = reliable paid provider; fallback
  should be a reliable paid/ample provider, not a daily-capped free tier
  (retry storms re-send full context). Drop exhausted free fallbacks.
- **Free-first rotation (zero/near-zero budget — proven 2026-08-27):** when
  the user has <$1 balance and no budget, invert the chain: main = most
  generous free tier, all free tiers as fallbacks, the paid provider LAST as
  an emergency reserve that should almost never fire. Full recipe, verified
  free-tier limits, watchdog script: `references/free-tier-rotation.md`.

### Free-tier quota is PER MODEL, not per key — probe before long runs

Google's free tier caps **daily requests per model per project**
(`GenerateRequestsPerDayPerProjectPerModel-FreeTier`); on our key
`quotaValue: "20"`. Verified once: the SAME key 429s on `gemini-3.8-flash`
while `gemini-3.7-flash`, `gemini-3.5-flash`, `gemini-3.1-flash-lite` and
`gemini-robotics-er-2-preview` answer 200 — so "key dead" is the wrong
diagnosis, "that MODEL is spent today" is the right one.

Consequence: an agent/job that looks **hung** for 10–15 min with no error is
usually a **quota storm** — the framework honours the 429 `retryDelay`
(6–11 s) and retries forever (one aborted run logged **234 × 429**). Read the
process log / gateway journal and count the 429s before blaming latency; the
fix is routing, not a longer timeout.

Budget maths: one multi-step agent task ≈ 20 requests ⇒ a default+fallback
chain of two models is only **~40–60 LLM calls/day**. Keep agent tasks short
and atomic, and treat a billing-enabled key as the *prerequisite* for routine
automation (the timeout knob and the extra fallback are only cushions).

Probe before a long run: `scripts/probe_gemini_quota.sh [model ...]`
(reads `GOOGLE_API_KEY` from the env or a project `.env`; never echoes it).

### Verify the RESOLVED route, not the config file you wrote

Frameworks resolve provider/model config by walking candidate filenames and
**stopping at the first hit**, and an env override usually outranks every
file. ARTEMIS: `artemis.jsonc` → `artemis.json` → `llm-config.json`, each
shadowed by `ARTEMIS_<UPPER_FILENAME>` (`.`/`-` → `_`, e.g.
`ARTEMIS_ARTEMIS_JSONC`). A hand-written `~/.config/artemis/llm-config.json`
was therefore **silently ignored** while the repo shipped
`config/artemis.jsonc`: the run kept burning the exhausted model and the
"fix" looked like it had failed. Working override = copy the winning filename
into our own config dir, point the env var at it, then print what actually
loaded before claiming success (ARTEMIS:
`get_default_llm_config()` and read each node's `.model`)

- `hermes fallback list` shows the chain; `hermes config set
  fallback_providers '[<json array>]'` accepts the JSON array directly
  (proven 2026-08-27) — no python YAML write needed.

### Adding a NEW fallback provider (Mistral / any OpenAI-compatible)

Hermes ships NO per-vendor plugin for Mistral — the built-in `custom`
provider (`~/.hermes/hermes-agent/plugins/model-providers/custom/`) handles
any OpenAI-compatible endpoint, so Mistral plugs in there (proven 2026-08-27):

- `hermes fallback list` / `hermes fallback add` CLI exists. For array
  edits, `hermes config set fallback_providers '[<full json array>]'`
  works directly (proven 2026-08-27 — chain was rebuilt this way). Only
  if `config set` misbehaves on a complex value, fall back to a python
  YAML write on `~/.hermes/config.yaml` respecting the existing
  `fallback_providers:` block shape (baseline: DeepSeek main + Gemini
  fallback).
- Custom-provider entry: `provider: custom`, `model:` (e.g.
  `mistral-small-latest`), `base_url: https://api.mistral.ai/v1`, and
  `key_env: MISTRAL_API_KEY` — confirm the exact key names against the
  custom plugin's source / an existing entry before writing.
- Mistral free eval tier = rate-limited, NO card required → ideal as a
  2nd/3rd fallback for resilience, zero cost, plus an EU data-residency
  ("sovereign AI") sales point for Gulf/European clients.
- **Z.ai GLM-4.7-Flash is a NATIVE provider** — no custom plugin needed:
  entry is just `{"provider":"zai","model":"glm-4.7-flash","key_env":"ZAI_API_KEY"}`
  (env var `ZAI_API_KEY` or `GLM_API_KEY`). Free tier ~1000 req/day; an
  occasional 429 "service temporarily overloaded" is capacity, not quota —
  wait 30-60s and retry. Signup gotcha: email+password with a server-side
  Aliyun captcha (no OTP route, no Google OAuth) → solve via VNC human
  handoff. Full verified flow + key-verify curls:
  `references/free-tier-rotation.md` § "Z.ai signup + free key".
- Account signup + Google OAuth flow from a datacenter IP (app-password
  rejection, "Account recovery" phone-prompt handoff, icon-only aria-label
  buttons) → `headless-browser-automation` skill,
  `references/ai-provider-console-signup.md`.

## Deployed endpoint burning your key

Signs: balance drops correlate with a live demo/client site, or user asks
"will this site consume our tokens?". Audit (all read-only, no cost):

```bash
cd ~/projects/<site> && npx wrangler pages secret list --project-name <name>
# → does DEEPSEEK_API_KEY exist? read functions/api/chat.js + wrangler.toml
grep -oE '^[A-Z_]+=' ~/.hermes/.env | sort   # which keys are shared
```

A Pages Function calling `api.deepseek.com` with the same key as Hermes +
no auth + CORS `*` = open token faucet. Two controls (see reference file
for code):

1. **Rate limit** — KV-backed per-IP counter (10/min, 60s TTL), checked
   BEFORE body parsing so malformed/spam hits count too.
2. **Kill switch** — `wrangler pages secret delete DEEPSEEK_API_KEY`
   (no `--yes` flag → pipe `printf 'y\n' |`); site stays up, function
   replies "not configured". Schedule via no_agent cron + bash script.

## Verification

- `systemctl --user is-active hermes-gateway hermes-gateway-whatsapp` — both
  still active after config changes (nothing restarts, so nothing breaks).
- Balance check again after a day of use: should stabilize.
- `journalctl --user -u hermes-gateway | grep "Context:"` — sessions now
  compress well before 250K.

## Pitfalls

- **Switching `model.default`/`model.provider` silently breaks enabled
  cron agent jobs:** the config command warns about jobs with stored
  `model_snapshot` differing from the new global model — those jobs "fail
  closed" on their next run instead of following the new model. Pin each
  affected job: `hermes cron edit <job_id> --provider <p> --model <m>`.
  `no_agent` script jobs (watchdogs) are unaffected.
- **Stale `model.base_url` survives provider switches:** when moving OFF a
  custom-endpoint provider (e.g. DeepSeek) you must `hermes config unset
  model.base_url` — otherwise the old endpoint URL keeps being used with the
  new provider's key.

- Don't hand-edit config.yaml — use `hermes config set` (stray indent breaks
  the live gateway).
- `compression.threshold_tokens` shows as `***` in `hermes config get` even
  though it's a number — verify via `grep threshold_tokens config.yaml`.
- cost columns (`estimated_cost_usd`) can be 0/None for providers without
  price tables — rely on `cache_read_tokens` + `api_call_count` as the real
  signal.
- User tip: for very long chats, tell the user `/new` starts a fresh session
  (smaller context = cheaper turns) — compression is automatic after the
  caps above, but a fresh session is the cheapest reset.
- **Never promise off-peak/cron-shift savings without checking whether the
  jobs are billable.** Re-audited 2026-09-27 (51 jobs): **7 billable, 44
  `no_agent` script jobs** that call no LLM at all. Only the billable subset
  is worth moving → measured saving ~$4–6/mo, NOT the headline lever. Verify
  with `hermes cron list` (read the `Mode:` line per job) plus a grep of each
  script for provider endpoints, and if you already quoted a saving number,
  correct it explicitly in the next reply. A wrong-but-confident saving is
  worse than no estimate. Script-only jobs also mean the *token* bill comes
  from interactive sessions + gateway traffic, not scheduling. The earlier
  \"all 13 crons are script jobs\" note held in Aug 2026 and is now stale — the
  fleet grew and agent jobs appeared.
- **The off-peak rule is PERMANENT and auto-enforced** (Aamir, 2026-09-27) —
  do not re-litigate it per session, and never schedule a new LLM-billable
  cron inside 01:00–04:00 / 06:00–10:00 UTC Mon–Fri. Guard + policy:
  § \"Permanent off-peak cron rule\" below, `~/brains/ops/rules/cron-offpeak-only.md`.
- **Own your number corrections out loud.** When better data changes the
  headline (e.g. 30d average $66/mo → trailing-7d run-rate $94/mo at the
  current card), say "my earlier figure was wrong" before presenting the new
  one; the user is making a spending decision on it.
- **`estimated_cost_usd` is priced with whatever card Hermes has loaded** —
  stale after a provider reprice, and 0/None for untabled providers. Fine
  for ranking/attribution (which task/profile burns most), never for the
  total; recompute totals from raw tokens × the live card.
- **Subscription ($20 Claude Pro / $20 ChatGPT Plus) vs API — the structural
  facts to lead with:** subscriptions ship NO API key (ChatGPT Plus has zero
  API credit; Claude Pro excludes API usage), so a gateway/bot/cron stack
  dies on them; Anthropic's consumer ToS bars subscription-powered
  third-party harnesses (enforced Apr 2026) → routing Hermes through a sub's
  OAuth risks a ban; and 5-hour/weekly caps cannot carry a ~28k-call/month
  automated pattern. Subs buy hands-on frontier quality, not automation —
  keep automation on metered API and compare against the *optimised* API
  bill, not the current one.
