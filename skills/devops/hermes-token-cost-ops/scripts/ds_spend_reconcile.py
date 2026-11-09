#!/usr/bin/env python3
"""Reconcile actual DeepSeek balance drain vs Hermes-tracked token spend.

    untracked burn = actual drain (from balance samples)
                     - Hermes-tracked spend (recomputed at the CURRENT card)

The gap is what direct-API consumers (client scorers, bots, deploy scripts)
burn with the same shared key and never record in any session DB.

Usage:  python3 ds_spend_reconcile.py [days]      # default 7

Notes / pitfalls baked in:
  - balance samples: ~/ops/observability/ds_balance.jsonl (see
    ds_balance_sampler.py; cron `ds-balance-sampler` every 30 min).
    Needs >=2 samples inside the window; do NOT extrapolate from one.
  - `estimated_cost_usd` in the DB is priced at whatever card Hermes has
    loaded -> stale after a provider reprice. Trust it for RANKING only;
    totals here are recomputed from raw tokens.
  - rates below are DeepSeek V4.1-Flash (2026-08-16 card), off-peak and
    peak. Re-derive from the live pricing page before quoting.
  - peak-hours share is approximated from each session's `last_seen` hour
    (within ~10%); good enough to size a lever, not for invoicing.
"""
import glob
import os
import sqlite3
import sys
import time

# cache-hit, cache-miss input, output — per 1M tokens
OFF_PEAK = (0.003, 0.15, 0.60)
PEAK = (0.006, 0.30, 1.20)          # 2x, 01:00-04:00 & 06:00-10:00 UTC Mon-Fri
LEDGER = os.path.expanduser("~/ops/observability/ds_balance.jsonl")

DBS = [("default", os.path.expanduser("~/.hermes/state.db"))] + [
    (p.split("/")[-2], p)
    for p in sorted(glob.glob(os.path.expanduser("~/.hermes/profiles/*/state.db")))
]


def is_peak(ts: float) -> bool:
    t = time.gmtime(ts)
    if t.tm_wday >= 5:                                  # Sat/Sun = off-peak all day
        return False
    hour = t.tm_hour
    return 1 <= hour < 4 or 6 <= hour < 10


def tracked(since: int):
    """-> (per_profile_cost, totals, peak_share) at the current card."""
    tot = {"in": 0.0, "out": 0.0, "cache": 0.0, "calls": 0, "usd": 0.0}
    per, peak_tok = {}, 0.0
    for name, db in DBS:
        if not os.path.exists(db):
            continue
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            rows = con.execute(
                """SELECT COALESCE(SUM(input_tokens),0),
                          COALESCE(SUM(output_tokens),0)+COALESCE(SUM(reasoning_tokens),0),
                          COALESCE(SUM(cache_read_tokens),0),
                          COALESCE(SUM(api_call_count),0)
                   FROM session_model_usage WHERE last_seen>=?""", (since,)).fetchone()
            hours = con.execute(
                """SELECT last_seen, COALESCE(input_tokens,0)+COALESCE(output_tokens,0)
                   FROM session_model_usage WHERE last_seen>=?""", (since,)).fetchall()
            con.close()
        except sqlite3.Error:
            continue
        tin, tout, cache, calls = (float(x or 0) for x in rows)
        usd = tin / 1e6 * OFF_PEAK[1] + tout / 1e6 * OFF_PEAK[2] + cache / 1e6 * OFF_PEAK[0]
        per[name] = per.get(name, 0.0) + usd
        tot["in"] += tin; tot["out"] += tout; tot["cache"] += cache
        tot["calls"] += int(calls); tot["usd"] += usd
        for ts, tk in hours:
            if ts and is_peak(ts):
                peak_tok += float(tk or 0)
    total_tok = tot["in"] + tot["out"] or 1.0
    return per, tot, peak_tok / total_tok


def samples():
    out = []
    if os.path.exists(LEDGER):
        for line in open(LEDGER):
            line = line.strip()
            if line:
                try:
                    import json
                    out.append(json.loads(line))
                except ValueError:
                    pass
    return out


def main() -> int:
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    since = int(time.time()) - days * 86400
    per, tot, pshare = tracked(since)
    off = tot["usd"]
    blended = off * (1 - pshare) + off * 2 * pshare     # peak tokens cost 2x
    print(f"=== DeepSeek spend reconciliation (last {days}d) ===")
    print(f"Hermes-tracked token spend (current card) : ${blended:8.2f}   "
          f"[{tot['calls']:,} calls, peak-token share {pshare:.1%}]")
    for name, usd in sorted(per.items(), key=lambda kv: -kv[1]):
        if usd > 0.005:
            print(f"    {name:<12} ${usd:8.2f}")
    print(f"    tokens: in {tot['in']/1e6:.1f}M  out+reasoning {tot['out']/1e6:.1f}M  "
          f"cache {tot['cache']/1e6:.0f}M")

    inwin = [s for s in samples() if s.get("ts", 0) >= since]
    if len(inwin) < 2:
        print(f"Actual drain                             : n/a  "
              f"(need >=2 balance samples in window; have {len(inwin)})")
        print("    -> sampler runs every 30 min; re-run after ~24h. "
              "Never extrapolate the untracked delta from one sample.")
        return 0
    drain = inwin[0]["total"] - inwin[-1]["total"]
    print(f"Actual drain (balance {inwin[0]['iso']} -> {inwin[-1]['iso']}): ${drain:8.2f}")
    print(f"UNTRACKED burn (direct-API scripts/apps)  : ${drain - blended:8.2f}")
    print(f"    burn ${drain / days:.2f}/day -> balance {inwin[-1]['total']:.2f} "
          f"lasts ~{inwin[-1]['total'] / max(drain / days, 1e-9):.1f} days")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
