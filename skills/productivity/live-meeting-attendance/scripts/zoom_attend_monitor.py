#!/usr/bin/env python3
"""Stable monitor for a live-meeting capture run (Hermes cron monitor_script mode).

Deterministic output: it changes ONLY when the meeting ends (ENDED flag appears)
or when a new watch-word mention shows up in the captured captions/chat.
Unchanged output => the cron tick is suppressed (no LLM, no message).

Usage: zoom_attend_monitor.py [run_dir]
Env:   ZOOM_RUN_DIR (default ~/ops/zoom-attend/run)
       ZOOM_WATCH   (default "aamir,sanad,zameer" — user/client names to alert on)
"""
import os
import re
import sys

RUN = sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
    "ZOOM_RUN_DIR", os.path.expanduser("~/ops/zoom-attend/run"))
words = [w.strip() for w in os.environ.get("ZOOM_WATCH", "aamir,sanad,zameer").split(",") if w.strip()]
pat = re.compile("|".join(re.escape(w) for w in words), re.I) if words else None


def rd(name):
    try:
        with open(os.path.join(RUN, name), errors="ignore") as fh:
            return fh.read()
    except Exception:
        return ""


caps = rd("captions.txt")
chat = rd("chat.txt")
lines = [l.strip() for l in (caps + "\n" + chat).splitlines() if l.strip()]
mentions = sorted({l[:160] for l in lines if pat and pat.search(l)})[:20]

print("STATE=" + ("ENDED" if os.path.exists(os.path.join(RUN, "ENDED")) else "LIVE"))
print("CAPTION_LINES=%d" % len([l for l in caps.splitlines() if l.strip()]))
print("DONE=%d" % int(os.path.exists(os.path.join(RUN, "DONE"))))
print("MENTIONS=%d" % len(mentions))
for m in mentions:
    print("MENTION: " + m)
