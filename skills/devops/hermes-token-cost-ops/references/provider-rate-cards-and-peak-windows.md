# Provider Rate Cards, Peak Windows, and Subscription-vs-API

Condensed from a 2026-09-10 audit (DeepSeek repriced 2026-08-16; Hermes'
shipped `usage_pricing.py` snapshot was still the retired card, which is why
the audit first reported ~$51/mo when the real run-rate was ~$95/mo).
**Re-derive every number from the live pricing page before quoting it in a
client-facing comparison — prices move, the method doesn't.**

## DeepSeek V4.1-Flash — per 1M tokens (cache-hit / cache-miss in / out)

| Window | Cache hit | Miss input | Output |
|---|---|---|---|
| Off-peak | $0.003 | $0.15 | $0.60 |
| Peak (2×) | $0.006 | $0.30 | $1.20 |

Peak = **01:00–04:00 and 06:00–10:00 UTC, Mon–Fri**
(IST equivalent: 06:30–09:30 and 11:30–15:30). Weekends off-peak all day.
Old (retired) card, do not quote: $0.14 in / $0.28 out / $0.0028 cache.

Pricing page: `https://api-docs.deepseek.com/quick_start/pricing`.
`web_extract` on that URL returns a thin page; the table content needs
`browser_exec` + `js()` innerText of the `table` elements (or a curl +
HTML-strip fallback). Balance only: `GET /user/balance` (no usage/history).

## Cache economics — the whole reason DeepSeek wins here

Agent harnesses re-send context every call, so the workload is
cache-dominated. Measured 30d shape: **111M miss-in, 69M out+reasoning,
2,390M cache-read** → cache-hit ratio ~96%, and at off-peak the cache line
costs $7.17 of a $65 bill. At full peak rates the whole miss volume re-priced
would be ~$331 for those cache tokens alone → **caching is doing the heavy
lifting; any change that breaks prompt-prefix stability (provider switch,
prefix churn, history rewrites) silently 10×'s the bill.**

Equivalent API cost of the same measured workload (with cache reads priced
at the alternative provider's cache rate): Claude Haiku 4.5 ≈ $600/mo,
Claude Sonnet 4.5 ≈ $1,800/mo, because their cache-read price
(~$0.10–0.30/M) is 30–100× DeepSeek's $0.003/M. Baseline API rates for the
comparison: Sonnet 4.5 $3/$15/$0.30, Haiku 4.5 $1/$5/$0.10 per M
(in/out/cache) — verify before quoting; GPT-5 series numbers from the same
audit were incomplete, re-derive.

## Cost attribution (where a ~$100/mo Hermes bill actually goes)

`sessions` → per-session totals. `session_model_usage` → per-task split
(columns: `task, provider, model, input_tokens, output_tokens,
reasoning_tokens, cache_read_tokens, api_call_count, estimated_cost_usd,
first_seen, last_seen, session_id`). 30d measured, all profiles:

| task | spend | share | calls |
|---|---|---|---|
| main agent work | $23.20 | 72.1% | 28,432 |
| `compression` | $5.14 | 16.0% | 1,228 |
| `background_review` | $3.47 | 10.8% | 2,775 |
| `approval` | $0.38 | 1.2% | 3,601 |

Token split at the same time: output+reasoning was **64% of the bill**,
input ~26%, cache ~11% → output-side discipline (`reasoning_effort`, max
tokens on helper scripts, model tier per task) beats input trimming by a
wide margin. Per-call cost of a compression call was ~5× a normal call,
because each one replays the whole context.

Trailing-7d run-rate vs 30d average, same data: 7d ≈ $94/mo off-peak,
30d ≈ $66/mo → **quote the trailing week**; a ramping workload makes the
monthly average flatteringly low.

## Levers with measured order of magnitude (~$100/mo baseline)

| Lever | Change | Est. $/mo |
|---|---|---|
| reasoning discipline | `reasoning_effort: medium → low` on routine profiles | $15–25 |
| background review | `agent.verify_on_stop: false` on high-volume profiles | $10–12 |
| compression tuning | `compression.threshold_tokens 60k→90k`, `threshold 0.5→0.6` | $6–8 |
| off-peak batch shift | only agent/batch jobs — script-only crons save $0 | $4–6 |
| free-chain routing | routine/bot chatter → Gemini free / local qwen | $10–20 |

≈ $45–60/mo reparable with zero capability loss → always present this
before recommending a migration off the metered API.

## Subscription vs API — structural facts, not opinions

- **$20 Claude Pro**: no API usage included; Claude Code CLI is included, but
  Anthropic's consumer ToS prohibits routing subscription credentials through
  third-party/automated harnesses (enforced from Apr 2026) → ToS violation +
  ban exposure. 5-hour rolling + weekly caps assume ordinary human usage.
- **$20 ChatGPT Plus**: Codex CLI included, **zero API credit** — API is
  separately metered. Same cap model.
- A Hermes gateway/6-profile/bot/cron stack issued ~36k API calls and 2.4B
  cache tokens in 30d — structurally impossible on either subscription.
- Honest framing that landed with the user: subs buy *hands-on frontier
  quality* (Opus/GPT-5.x on real coding/reasoning), automation must stay on
  metered API; the winning package is **optimised API (~$50) + optional $20
  Claude Pro**, i.e. cheaper than today's bill *and* better quality.
