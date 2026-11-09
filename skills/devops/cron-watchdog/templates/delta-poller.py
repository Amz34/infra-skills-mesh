#!/usr/bin/env python3
"""Silent state-file delta poller — TEMPLATE.

Copy, then replace `fetch_records()` with the vendor API call and `format_alert()`
with the message the user should receive. Contract for a `no_agent` cron job:

  * prints the alert TEXT when a new/changed record appears
  * prints NOTHING when there is no change
  * prints NOTHING when the fetch FAILS (a failure must be indistinguishable
    from "no news", otherwise a 5-minute cadence turns into spam)

First run bootstraps the state file and stays silent.

Usage:  python3 delta_poller.py            # normal cron tick
        python3 delta_poller.py --selftest # prove BOTH paths before scheduling
"""
import json, os, sys, urllib.request, urllib.error

STATE = os.path.expanduser(os.environ.get("DELTA_POLLER_STATE", "~/.local/state/delta_poller.json"))
API = os.environ.get("DELTA_POLLER_URL", "")          # e.g. https://store.myshopify.com/admin/api/2026-07/orders.json?status=any&limit=25
TOKEN = os.environ.get("DELTA_POLLER_TOKEN", "")
# Fields that must be tracked for change detection. NEVER include volatile fields
# (updated_at, view counts, "last seen") or every tick looks like a change.
TRACKED = ("status", "fulfillment_status")


def fetch_records():
    """Return a list of dicts, each with an `id` and the TRACKED keys. Raise on failure."""
    if not (API and TOKEN):
        raise RuntimeError("DELTA_POLLER_URL / DELTA_POLLER_TOKEN not set")
    req = urllib.request.Request(API, headers={"X-Shopify-Access-Token": TOKEN,
                                              "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    key = next((k for k in ("orders", "records", "items", "data") if isinstance(payload.get(k), list)), None)
    return payload[key] if key else payload


def snapshot(rec):
    return {f: rec.get(f) for f in TRACKED}


def format_alert(rec, kind):
    return f"{kind}: #{rec.get('name') or rec.get('id')} — " + \
           ", ".join(f"{f}={rec.get(f)}" for f in TRACKED)


def main():
    selftest = "--selftest" in sys.argv
    try:
        records = {str(r["id"]): snapshot(r) for r in fetch_records()}
    except Exception:
        return 0                                  # silent: failure == no news

    try:
        prev = json.load(open(STATE)).get("records", {})
    except Exception:
        prev = None

    if prev is None and not selftest:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        json.dump({"records": records}, open(STATE, "w"))
        return 0                                  # bootstrap: announce nothing

    prev = prev or {}
    lines = []
    for rid, snap in records.items():
        if rid not in prev:
            lines.append(format_alert({"id": rid, **snap}, "NEW"))
        elif prev[rid] != snap:
            lines.append(format_alert({"id": rid, **snap}, "UPDATED"))

    if lines:
        print("\n".join(lines))

    if not selftest:                              # never corrupt state in a dry run
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        json.dump({"records": records}, open(STATE, "w"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
