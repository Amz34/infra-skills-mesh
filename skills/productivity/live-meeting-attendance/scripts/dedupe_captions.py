#!/usr/bin/env python3
"""Dedupe a scraped caption log and print it in chronological order (context-safe).

WHY: the Zoom web client re-renders the whole rolling caption panel on every
poll, so a captions.txt from a one-hour meeting is the same spoken text repeated
5-8x and can exceed 100K chars. Reading it whole blows the context window (and a
single read_file / big print of it can come back elided = empty). Dedupe and
slice in code first, in a few small calls.

RULE: per timestamp keep the LONGEST variant (the rolling caption grows to the
full sentence before the next one starts), in first-seen order. Untimestamped
lines (e.g. a paste of chat) are kept as individual entries, undeduped.

Usage:
  python3 dedupe_captions.py captions.txt                    # everything
  python3 dedupe_captions.py captions.txt 15:40 16:05        # one time window
  python3 dedupe_captions.py captions.txt 15:40 16:05 --chars 110
  python3 dedupe_captions.py captions.txt --limit 120        # cap output
"""
import re
import sys

TS = re.compile(r"^\[?(\d\d:\d\d(?::\d\d)?)\]?\s*(.*)$")


def rows(path):
    seen = {}      # timestamp -> index in out
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            s = raw.strip()
            if not s:
                continue
            m = TS.match(s)
            ts = m.group(1) if m else ""
            txt = (m.group(2) if m else s).strip()
            if not txt:
                continue
            if ts:
                if ts in seen:
                    i = seen[ts]
                    if len(txt) > len(out[i][1]):
                        out[i] = (ts, txt)
                    continue
                seen[ts] = len(out)
            out.append((ts, txt))
    return out


def main():
    args = sys.argv[1:]
    opts = {}
    pos = []
    i = 0
    while i < len(args):
        if args[i] in ("--chars", "--limit"):
            try:
                opts[args[i]] = int(args[i + 1])
                i += 2
                continue
            except (IndexError, ValueError):
                print("bad value for %s" % args[i])
                return 1
        pos.append(args[i])
        i += 1
    if not pos:
        print(__doc__)
        return 1

    path = pos[0]
    lo = pos[1] if len(pos) > 1 else ""
    hi = pos[2] if len(pos) > 2 else ""
    all_rows = rows(path)
    keep = [r for r in all_rows if (not lo or r[0] >= lo) and (not hi or r[0] <= hi)]
    if opts.get("limit"):
        keep = keep[:opts["limit"]]

    print("# %s: %d unique lines, printing %d%s"
          % (path, len(all_rows), len(keep),
             (" (window %s-%s)" % (lo, hi)) if (lo or hi) else ""))
    for ts, txt in keep:
        if opts.get("chars") and len(txt) > opts["chars"]:
            txt = txt[:opts["chars"]] + "..."
        print(("[%s] %s" % (ts, txt)) if ts else txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
