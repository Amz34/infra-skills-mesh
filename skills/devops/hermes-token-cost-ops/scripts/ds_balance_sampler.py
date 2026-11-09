#!/usr/bin/env python3
"""DeepSeek balance sampler — append a timestamped sample to JSONL.

Purpose: DeepSeek exposes no usage endpoint, so untracked spend (direct-API
scripts/apps) can only be measured as `actual drain - Hermes-tracked spend`.
That needs at least two balance samples spanning the window.

Silent on success (safe for a `no_agent` cron: empty stdout = no message).
Prints ONLY when the balance is low or the fetch fails, so the cron doubles
as a low-balance watchdog.

Cron wiring (proven 2026-09-10):
  - real logic  : ~/ops/scripts/ds_balance_log.py  (or this file)
  - wrapper     : ~/.hermes/scripts/ds_balance_sampler.sh  <- cronjob `script`
                  must be RELATIVE to ~/.hermes/scripts/ (absolute paths are
                  rejected); wrapper = exec python3 "$HOME/ops/scripts/..."
  - cron        : `*/30 * * * *`, no_agent = true, script = ds_balance_sampler.sh

Env: DEEPSEEK_API_KEY, read from ~/.hermes/.env if not exported.
"""
import json
import os
import re
import time
import urllib.request

LEDGER = os.path.expanduser("~/ops/observability/ds_balance.jsonl")
LOW_BALANCE = 5.0     # alert threshold (USD)
ENV_FILE = os.path.expanduser("~/.hermes/.env")


def api_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key
    try:
        with open(ENV_FILE) as fh:
            for line in fh:
                m = re.match(r"\s*(?:export\s+)?DEEPSEEK_API_KEY\s*=\s*(.+)", line)
                if m:
                    return m.group(1).strip().strip("'\"")
    except OSError:
        pass
    return ""


def main() -> int:
    key = api_key()
    if not key:
        print("ds_balance_log: DEEPSEEK_API_KEY not found (checked env + ~/.hermes/.env)")
        return 1
    req = urllib.request.Request(
        "https://api.deepseek.com/user/balance",
        headers={"Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.load(resp)
    except Exception as exc:                                   # noqa: BLE001
        print(f"ds_balance_log: balance fetch failed: {exc}")
        return 1

    info = (payload.get("balance_infos") or [{}])[0]
    sample = {
        "ts": int(time.time()),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "currency": info.get("currency", "USD"),
        "total": float(info.get("total_balance") or 0),
        "topped_up": float(info.get("topped_up_balance") or 0),
        "granted": float(info.get("granted_balance") or 0),
        "available": bool(payload.get("is_available", True)),
    }
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a") as fh:
        fh.write(json.dumps(sample) + "\n")

    if sample["total"] < LOW_BALANCE:
        print(
            f"DeepSeek balance low: ${sample['total']:.2f} {sample['currency']} "
            f"— top up before the gateway/client bots run dry."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
