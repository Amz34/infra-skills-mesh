# Meter over-statement + dead-sampler detection (the error can run the OTHER way)

2026-09-26. User: *"its looking like consuming more token check out expertly and QA urself"*.
Answer: **token volume was DOWN ~40% week-over-week and real spend was ~$0.34/day.** The
"consuming more" impression was produced by our own tooling — and by a monitor that had been
dead for 15 days, so no data existed to contradict it.

## The three numbers, same window

| Source | 7-day run-rate | vs reality | Why |
|---|---|---|---|
| `sessions.estimated_cost_usd` (state.db) | ~$7.98/7d ≈ **$34/mo** | **3.4× high** | raw tokens × a card, peak-window-blind in the other direction, `$0.00` buckets still counted as calls |
| `ds_spend_reconcile.py` (peak-aware card) | ~$15.43/7d ≈ **$66/mo** | **6.5× high** | prices the whole window at peak rates; workload was largely off-peak |
| **balance ledger (ground truth)** | $5.29 / 15.6 d = **$0.34/day ≈ $10/mo** | — | `$7.06` (10 Sep) → `$1.77` (26 Sep), no top-up recorded in between |

Token volume, same comparison (all profiles, trailing 7d vs previous 7d):
`api_call_count` 15,339 → **8,937**; input 54.3M → **32.7M**; output 15.2M → **8.2M**;
cache-read 1.14B → **659M**. Everything down ~40%.

**Rules that follow**

1. **Balance drain is the only ground truth.** Headline the drain-derived run-rate; present
   the tracked number explicitly as an *upper bound* and label which is which. Never let the
   user make a spending decision on the tracked number alone.
2. **Test BOTH directions of error.** The rest of the skill hunts *under*-reporting
   (untracked direct-API burn). Over-statement is equally likely on an
   off-peak-heavy workload and produces a false "we are burning too fast" alarm.
3. **Prove the instrument is alive BEFORE quoting any delta.** A sampler that died silently
   is indistinguishable from "no spend": the `ds-balance-sampler` cron was dead for 15 days
   (newest sample 11 Sep) → no alerts, no series, nothing to compare against.
4. **Group `session_model_usage` by `model`, not only by `task`.** Untabled models report
   `$0.00` with real call counts — `deepseek-flash` had 2.32M input / 1.78M output / 651
   calls at `$0.00` and therefore appeared in *no* cost ranking. Also `compression` showed
   317 calls / 1.05M output tokens at $0 in the same sweep.
5. **Quote context-per-call as the efficiency metric** —
   `SUM(input_tokens+cache_read_tokens) / SUM(api_call_count)`. Measured 86k (default) /
   92k (indaz) tokens per call: 46 telegram sessions / 7,012 calls → **604M context tokens
   per week**. Call count and session count are the wrong dials; context size is the cost.

## Instrument-liveness check (do this first)

```bash
python3 - <<'PY'
import json,datetime,os
p=os.path.expanduser('~/ops/observability/ds_balance.jsonl')
rows=[json.loads(l) for l in open(p) if l.strip()]
n=rows[-1]; ts=n.get('ts') or 0
age=(datetime.datetime.utcnow()-datetime.datetime.utcfromtimestamp(ts)).total_seconds()/3600
print('samples',len(rows),'newest',n.get('iso'),'age_h',round(age,1),'balance',n.get('total'))
print('distinct balances:',sorted({r.get('total') for r in rows})[:8])
PY
```

- `age_h > 1` → the sampler is dead → **reinstall the cron before analysing anything**:
  a `*/30` `no_agent` cron whose `script` is a wrapper in `~/.hermes/scripts/`
  (`exec python3 "$HOME/ops/scripts/ds_balance_log.py"` — absolute/`~/ops` paths are
  rejected by the cron API), then run the sampler once by hand to write a fresh sample.
- One distinct balance across many samples = samplers all inside one unchanged window —
  **that is not evidence of zero spend**, it is evidence of a too-short window.
- The alert threshold works and is worth keeping: the restored sampler immediately reported
  `DeepSeek balance LOW: $1.77 (threshold $5.00)`. At the measured $0.34/day that is
  **~5 days of runway** — the real emergency in the incident, and the reason a dead
  sampler matters more than any cost-table debate.

## Root-cause list for "why does it LOOK like we burn more"

- a tracker priced at peak for an off-peak workload (this case, 6.5×);
- `$0.00`-priced model buckets contributing call counts but no cost (invisible in rankings);
- overhead buckets that inflate totals without being "user work" — measured
  `background_review` **12.2%** of tracked spend and `compression` ~5× the cost *per call*
  of normal work;
- **one agent-mode cron every 30 min** (48 LLM runs/day) among 67 jobs — the only kind of
  cron that can burn tokens at all (`hermes cron list` → read the `Mode:` line; script-only
  jobs are free);
- 30-day averages vs 7-day run-rate: quote the run-rate, but state that it is an *upper*
  bound until the balance ledger confirms it.
