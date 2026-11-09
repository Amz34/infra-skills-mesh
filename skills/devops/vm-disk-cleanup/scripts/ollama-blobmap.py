#!/usr/bin/env python3
"""ollama-blobmap — which model tag actually owns which blob bytes.

Why: `ollama list` ka "SIZE" model ka poora weight batata hai, lekin do tags
(e.g. qwen2.5:7b aur qwen2.5:7b-64k) aksar SAME blob set share karte hain —
ek tag delete karne se 0 bytes free hote hain. Ye script per-tag
"exclusive" bytes nikalta hai (= jo us tag ko delete karne se asal me milega),
plus kisi manifest se referenced na hone wale orphan blobs.

Usage:
  python3 ollama-blobmap.py                # human table
  python3 ollama-blobmap.py --json         # machine output
  OLLAMA_MODELS=/path python3 ollama-blobmap.py
"""
import argparse, json, os, sys
from collections import defaultdict

ROOT = os.environ.get("OLLAMA_MODELS") or os.path.expanduser("~/.ollama/models")


def human(n):
    for u in ("B", "K", "M", "G", "T"):
        if n < 1024 or u == "T":
            return f"{n:.1f}{u}" if u != "B" else f"{n}B"
        n /= 1024.0


def blob_path(digest):
    return os.path.join(ROOT, "blobs", digest.replace(":", "-"))


def scan(verbose=False):
    man = os.path.join(ROOT, "manifests")
    tags, used = {}, set()
    for dirpath, _dirs, files in os.walk(man):
        for fn in files:
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, man).replace(os.sep, "/")
            try:
                with open(p) as fh:
                    m = json.load(fh)
            except Exception as e:  # corrupt/partial manifest
                if verbose:
                    print(f"  ! skip {rel}: {e}", file=sys.stderr)
                continue
            layers = list(m.get("layers") or [])
            if isinstance(m.get("config"), dict):
                layers.append(m["config"])
            digests, total = [], 0
            for L in layers:
                d = L.get("digest")
                if not d:
                    continue
                digests.append(d)
                used.add(d)
                bp = blob_path(d)
                total += os.path.getsize(bp) if os.path.exists(bp) else (L.get("size") or 0)
            tags[rel] = {"total": total, "digests": digests}
    # reference count per blob -> exclusive bytes per tag
    refcount = defaultdict(int)
    for t in tags.values():
        for d in set(t["digests"]):
            refcount[d] += 1
    for t in tags.values():
        t["exclusive"] = sum(
            (os.path.getsize(blob_path(d)) if os.path.exists(blob_path(d)) else 0)
            for d in set(t["digests"]) if refcount[d] == 1
        )
        t["shared_with"] = sorted(
            o for o, ot in tags.items()
            if o != t and set(ot["digests"]) & set(t["digests"])
        )
    blobs_dir = os.path.join(ROOT, "blobs")
    orphans, orphan_bytes = [], 0
    if os.path.isdir(blobs_dir):
        for fn in os.listdir(blobs_dir):
            if not fn.startswith("sha256-"):
                continue
            digest = "sha256:" + fn[len("sha256-"):]
            if digest in used:  # referenced by some manifest -> not orphan
                continue
            orphans.append(fn)
            orphan_bytes += os.path.getsize(os.path.join(blobs_dir, fn))
    return tags, refcount, orphans, orphan_bytes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    if not os.path.isdir(ROOT):
        sys.exit(f"no ollama model store at {ROOT} (set OLLAMA_MODELS)")
    tags, refcount, orphans, ob = scan(a.verbose)
    out = {
        "root": ROOT,
        "tags": {k: {"total": v["total"], "exclusive": v["exclusive"],
                     "shared_with": v["shared_with"]} for k, v in sorted(tags.items())},
        "orphan_blobs": len(orphans), "orphan_bytes": ob,
    }
    if a.json:
        print(json.dumps(out, indent=2))
        return
    print(f"ollama store: {ROOT}\n")
    print(f"{'tag':<46}{'total':>10}{'freed if deleted':>18}")
    for k, v in out["tags"].items():
        print(f"{k:<46}{human(v['total']):>10}{human(v['exclusive']):>18}")
        if v["shared_with"]:
            print(f"    shares blobs with: {', '.join(v['shared_with'])}")
    print(f"\norphan blobs (no manifest ref): {len(orphans)}  {human(ob)}")
    print("NOTE: 'freed if deleted' = exclusive bytes only. Shared tags ko saath"
          " delete kiye bina 0 gain — dono ka exclusive dekh kar decide karo.")


if __name__ == "__main__":
    main()
