#!/usr/bin/env python3
"""Safe /tmp reclaim for a shared VM (dry-run by default).

Usage:
  python3 clean-tmp-safe.py                    # report only
  python3 clean-tmp-safe.py --apply            # delete
  python3 clean-tmp-safe.py --cut-days 3 --apply

Safety rules (learned the hard way — see SKILL.md):
  * never touch a path referenced by a LIVE process (/proc/*/cmdline, cwd, exe, fd)
    — a Hermes worker may be serving a site straight out of /tmp
  * never touch X/ICE/font sockets or systemd-private-* dirs
  * only entries older than --cut-days (default 2)
  * print df before/after; nothing is deleted without --apply
"""
import argparse
import os
import shutil
import subprocess
import time

KEEP_NAMES = (".X11-unix", ".ICE-unix", ".font-unix", ".Test-unix", ".XIM-unix", ".tmp")


def referenced_paths():
    """Every /tmp path currently referenced by a live process."""
    refs = set()
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        base = "/proc/" + entry
        try:
            with open(base + "/cmdline", "rb") as fh:
                for tok in fh.read().split(b"\0"):
                    t = tok.decode("utf-8", "ignore")
                    if t.startswith("/tmp/"):
                        refs.add(t)
        except OSError:
            pass
        for name in ("cwd", "exe"):
            try:
                t = os.readlink(base + "/" + name)
            except OSError:
                continue
            if t.startswith("/tmp/"):
                refs.add(t)
        try:
            fds = os.listdir(base + "/fd")
        except OSError:
            continue
        for fd in fds:
            try:
                t = os.readlink(base + "/fd/" + fd)
            except OSError:
                continue
            if t.startswith("/tmp/") and " (deleted)" not in t:
                refs.add(t)
    return refs


def protected(path, refs):
    base = os.path.basename(path)
    if base in KEEP_NAMES or base.startswith("systemd-private-"):
        return True
    pref = path.rstrip("/") + "/"
    for r in refs:
        if r == path or r.startswith(pref):
            return True
    return False


def size_of(path):
    if os.path.islink(path) or os.path.isfile(path):
        try:
            return os.lstat(path).st_size
        except OSError:
            return 0
    total = 0
    for root, _dirs, files in os.walk(path, onerror=lambda e: None):
        for f in files:
            try:
                total += os.lstat(os.path.join(root, f)).st_size
            except OSError:
                pass
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cut-days", type=float, default=2.0,
                    help="only touch entries older than N days (default 2)")
    ap.add_argument("--apply", action="store_true", help="actually delete")
    a = ap.parse_args()

    cutoff = time.time() - a.cut_days * 86400
    refs = referenced_paths()
    print("# cut=%.1fd live_refs_seen=%d apply=%s" % (a.cut_days, len(refs), a.apply))
    print(subprocess.run(["df", "-h", "/"], capture_output=True, text=True).stdout.strip())

    victims, skipped, reclaimable = [], [], 0
    for name in sorted(os.listdir("/tmp")):
        p = "/tmp/" + name
        try:
            st = os.lstat(p)
        except OSError:
            continue
        if st.st_mtime >= cutoff:
            skipped.append((name, "recent"))
            continue
        if protected(p, refs):
            skipped.append((name, "protected/in-use"))
            continue
        sz = size_of(p)
        victims.append((p, sz, st.st_mtime))
        reclaimable += sz

    for p, sz, mt in sorted(victims, key=lambda x: -x[1]):
        tag = "DEL" if a.apply else "WOULD-DEL"
        when = time.strftime("%Y-%m-%d", time.localtime(mt))
        print("%s %9.1fMB %s %s" % (tag, sz / 1e6, when, p))
    print("# candidates=%d reclaimable=%.2fGB" % (len(victims), reclaimable / 1e9))
    for n, why in skipped[:15]:
        print("# keep %s (%s)" % (n, why))

    if not a.apply:
        print("# dry-run only — review, then re-run with --apply")
        return
    for p, _sz, _mt in victims:
        try:
            if os.path.isdir(p) and not os.path.islink(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
        except OSError as e:
            print("# FAIL %s: %s" % (p, e))
    print(subprocess.run(["df", "-h", "/"], capture_output=True, text=True).stdout.strip())


if __name__ == "__main__":
    main()
