#!/usr/bin/env python3
"""Generic no-agent delta watchdog: silent unless a NEW tracked item appears.

How it works with a Hermes cron job:
  - no_agent=True, schedule e.g. '0 9 1 * *' (monthly), script=<this file>.
  - First run writes the baseline state file and prints NOTHING (silent tick).
  - Later runs compare current findings vs saved state; print ONLY the delta.
  - Cron delivers stdout verbatim; empty stdout = silent, zero tokens spent.

Customize the three marked blocks (WATCH_NAME / SOURCES / STATE_FILE), then
verify with:  python3 <file>; echo "exit=$?"   (expect silent + state file).
"""

import json
import urllib.request
from pathlib import Path

# --- CUSTOMIZE ---
WATCH_NAME = "example-project"          # used in alert wording
STATE_FILE = Path.home() / ".hermes" / "scripts" / f"{WATCH_NAME}_watch_state.json"

def sources() -> list[str]:
    """Return the current list of known/available items (ids, slugs...).
    A brand-new item appearing here that is not in the state file triggers
    an alert. Keep the fetch cheap and bounded."""
    found: list[str] = []
    # Example 1: Hugging Face org + search (params, "research release" flags)
    for url in (
        f"https://huggingface.co/api/models?author=ORG&limit=50",
        "https://huggingface.co/api/models?search=PROJECT&limit=50",
    ):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
            with urllib.request.urlopen(req, timeout=20) as r:
                for m in json.load(r):
                    found.append(f"hf:{m['id']} ({m.get('downloads', 0):,} dl)")
        except Exception:
            pass  # transient network/API error -> stay silent, never alert
    # Example 2: OpenRouter = "public API exists" signal
    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/models", headers={"User-Agent": "curl/8"})
        with urllib.request.urlopen(req, timeout=20) as r:
            for m in json.load(r).get("data", []):
                if "PROJECT" in m["id"].lower():
                    found.append(f"api:{m['id']}")
    except Exception:
        pass
    return sorted(set(found))
# --- END CUSTOMIZE ---


def load_state():
    if STATE_FILE.exists():
        try:
            return set(json.loads(STATE_FILE.read_text()).get("known", []))
        except Exception:
            return set()
    return None  # no state yet => first run, baseline only


def save_state(items: list[str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"known": sorted(items)}, indent=2))


def main() -> None:
    current = sources()
    if not current:
        # No source reachable AND no state: still baseline silently.
        if load_state() is None:
            save_state([])
        return
    prev = load_state()
    if prev is None:                      # first successful poll = baseline
        save_state(current)
        return
    new = [x for x in current if x not in prev]
    save_state(current)
    if new:                               # only real delta reaches the user
        print(f"[{WATCH_NAME}] Naya variant/API mil gaya:")
        for item in new:
            print(f"  - {item}")


if __name__ == "__main__":
    main()
