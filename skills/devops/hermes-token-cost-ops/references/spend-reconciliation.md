# Spend Reconciliation — "I spent ~$X" vs tracked estimates

Worked context: 2026-09-03. User claimed ~$50 DeepSeek spend; tracked
session cost across 6 profiles was ~$16–20. The reconciliation method
below settled the dispute structure (final exact split needs the user's
console top-up records — see §4).

## 1. What each data source can and cannot prove

| Source | Shows | Doesn't show |
|---|---|---|
| `GET https://api.deepseek.com/user/balance` | CURRENT split only: `total_balance`, `granted_balance`, `topped_up_balance` | ANY history — no consumption ledger, no top-up records, no dates |
| Hermes `state.db` sessions tables (per profile) | Token sums per session since profile creation | Pre-migration usage; direct-API script usage; anything before the DB window |
| Provider web console (platform.deepseek.com usage/top-up, platform.kimi.ai/console/account) | Top-up ledger + consumption — the GROUND TRUTH | — (but OTP login-walled; ask user for screenshots) |

Reconciliation formula: `lifetime consumption = Σ top-ups (console) −
current balance (API)`. E.g. ~$50 topped up, $0.70 remaining → ~$49.30
consumed. This is how a "~$50" claim and a "$20 tracked" number are both
true at the same time.

## 2. Recompute tracked usage at official rates

Never quote the `estimated_cost_usd` column alone — recompute from raw
tokens × the model's real $/M. Hermes' own pricing snapshot lives at
`~/.hermes/hermes-agent/agent/usage_pricing.py` (dict: model name →
`(input $/M, output $/M, cache_read $/M)`), dated in a comment.
DeepSeek v4-flash: the card displayed there can be **stale** — it still
carried the retired **$0.14 / $0.28 / $0.0028** triplet for weeks after the
2026-08-16 reprice. Current card (off-peak / peak, per M: cache-hit /
miss-in / out): **$0.003/$0.15/$0.60** and **$0.006/$0.30/$1.20**, peak =
01:00–04:00 & 06:00–10:00 UTC Mon–Fri. See
`provider-rate-cards-and-peak-windows.md`.
`est ≈ input×rate_in + output×rate_out + cache×rate_cache` (reasoning
tokens are NOT billed separately — including them over-counts ~20%).
Re-derive rates before quoting; the constants in the snippet below are the
retired ones kept only to show the shape of the sum.

Aggregate across ALL profiles:

```python
import sqlite3, glob
R_IN, R_OUT, R_CACHE = 0.14, 0.28, 0.0028   # deepseek-v4-flash official
grand = {"sessions":0,"in":0.0,"out":0.0,"cache":0.0,"reas":0.0}
for d in glob.glob('/home/ubuntu/.hermes/**/state.db', recursive=True):
    db = sqlite3.connect(f'file:{d}?mode=ro', uri=True)   # ro URI always works
    s = db.execute("""SELECT COUNT(*), COALESCE(SUM(input_tokens),0),
        COALESCE(SUM(output_tokens),0), COALESCE(SUM(cache_read_tokens),0),
        COALESCE(SUM(reasoning_tokens),0) FROM sessions""").fetchone()
    db.close()
    for k,v in zip(grand, s): grand[k] = grand[k] + (v or 0)
cost = grand["in"]/1e6*R_IN + (grand["out"]+grand["reas"])/1e6*R_OUT*0 + grand["cache"]/1e6*R_CACHE
```

Measured baseline (all profiles, 9 Aug–3 Sep 2026, 430 sessions): 61.2M
input + 15.9M output + 9.2M reasoning + **1,596M cache-read** → ~$20 at
official rates. Cache reads at $0.0028/M are the whole reason agent-style
workloads (huge context replay every call) are cheap on DeepSeek native.

## 3. The untracked-spend gap (the usual answer to "where's the rest?")

Scripts that read `DEEPSEEK_API_KEY` and call the provider directly NEVER
appear in any Hermes session DB. Find them:

```bash
grep -rl DEEPSEEK_API_KEY ~/.hermes/scripts ~/clients ~/projects 2>/dev/null
# also: grep -oE '^[A-Z_]+=' ~/.hermes/.env | sort   # which shared keys exist
```

Consumers found 2026-09-03 on this VM (all burn the SAME shared key):
ai-lead-qualifier scorer (live Sanad/AVVS sites), carousel generator,
lead_pipeline, resume/brief generator bots, invertio multi-agent repo
(`api_balance.py`, agent `llm.py`), luxewave `deepseek_ask.py`, aone
disable scripts, `deepseek_balance_watch.sh` cron. Classify each by burn
weight before concluding; a live client-facing scorer with long context
can out-burn all Hermes sessions combined.

DB coverage window caveat: profile `state.db` only reaches back to profile
creation / last VM migration (e.g. 9 Aug 2026). Everything earlier is
invisible — say so explicitly instead of implying the DB is complete.

## 4. Live-balance burn evidence + console handoff

- Balance sampled hours apart during agent activity demonstrates burn on
  the user's own key: $0.75 → $0.70 across ~half a day of sessions.
- Provider consoles are OTP login-walled; no stored credentials, never
  guess. Ask the user for TWO screenshots to finish an exact
  reconciliation: (a) platform.deepseek.com Usage/top-up records
  (total topped-up + consumption), (b) platform.kimi.ai/console/account
  (balance + usage). Offer the formula so they can self-verify instantly.

## 5. DeepSeek native vs Kimi/Moonshot rates (published, Sep 2026)

Per 1M tokens: input / cache-hit / output.

| Provider/model | Input | Cache hit | Output |
|---|---|---|---|
| DeepSeek v4-flash (native; off-peak / peak, 2026-08 card) | $0.15 / $0.30 | $0.003 / $0.006 (2% of input) | $0.60 / $1.20 |
| Kimi K2.5 | $0.60 | $0.10 | $3.00 |
| Kimi K2.6 | $0.95 | $0.16 | $4.00 |
| Kimi K3 | $3.00 | — | $15.00 |

Same measured workload on Kimi K2.6 ≈ $400+/mo (1,596M cache × $0.16
dominates) vs ~$20 on DeepSeek native → **~20× cheaper for cache-heavy
agent loops** (magnitudes shift with each DeepSeek reprice; the ‑direction
of the cache-price gap does not — re-verify before quoting $-figures).

Measured again 2026-09-10 at the new card over 30d (111M in / 69M out /
2,390M cache): DeepSeek ≈ $66–77/mo mixed-peak, while the same tokens on
Claude Haiku 4.5 ≈ $600/mo and Sonnet 4.5 ≈ $1,800/mo — the gap widened,
because DeepSeek's cache-hit stayed at 2% of input while Claude's cache
read is $0.10–0.30/M. Structural consequence: **do not migrate a
cache-heavy agent harness to a provider whose cache-read price is higher
than its input discount is worth.** DeepSeek's cache-hit price (2% of input) is the strategic
edge for agent harnesses that replay context every call; Kimi's cache
discount is only ~17%. Kimi's genuine edge is K3 output quality on
complex coding — a quality tradeoff, never a cost win at this workload
shape. Re-derive rates from the live pricing pages before quoting them in
a client-facing comparison (prices change; the method doesn't).
