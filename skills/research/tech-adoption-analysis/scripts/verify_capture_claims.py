#!/usr/bin/env python3
"""Verify live-capture claims against ALL three evidence sources before quoting them.

A recorded seminar / masterclass / webinar leaves three artifacts that disagree:
audio transcript  ·  audience chat  ·  slide screenshots. The transcript is ASR (it garbles
product names and numbers), the slides are authoritative for what was SHOWN, and only the
transcript proves what was SAID. So every claim that will go into a plan or a report gets
classified per source first: verbatim in the transcript? slide-only? paraphrase-only (our
reading)? absent altogether?

Never hand-roll these greps again — running the same script keeps verdicts comparable
session to session, and it emits the `[src: ...]` tag the reply has to carry.

Usage
    verify_capture_claims.py <run_dir> --claims "fixed-size cuts table rows" "six stages"
    verify_capture_claims.py <run_dir> --claims-file claims.txt --ocr
    verify_capture_claims.py <run_dir>                     # index stats only

Expected layout (any subset; missing sources are reported, not fatal):
    <run_dir>/transcript.txt | .md | .json   audio transcript (Speaker + timestamp lines help)
    <run_dir>/shots/*.png                    slide screenshots -> OCRed into <run_dir>/slide_ocr.txt

Output: per claim, one block with a per-source verdict (VERBATIM / PARTIAL <ratio> / NOT FOUND),
the best matching line with its timestamp or shot filename, and the provenance tag to paste.

Exit codes: 0 = ran (the verdicts are the output), 2 = run_dir missing.
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys

TS = re.compile(r"(\d{1,2}:\d{2}(?::\d{2})?)")
SHOT = re.compile(r"^=== (.+?) ===$", re.M)


def norm(s: str):
    """Lowercase alphanumeric-only, with an offset map back into the raw text."""
    out, m = [], []
    for i, ch in enumerate(s):
        if ch.isalnum():
            out.append(ch.lower())
            m.append(i)
        else:
            out.append(" ")
            m.append(i)
    return re.sub(r"\s+", " ", "".join(out)).strip(), m


def load_transcript(run_dir: str):
    for name in ("transcript.txt", "transcript.md"):
        p = os.path.join(run_dir, name)
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                return p, fh.read()
    p = os.path.join(run_dir, "transcript.json")
    if os.path.isfile(p):
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                data = json.load(fh)
        except (ValueError, OSError):
            return p, ""
        if isinstance(data, dict) and isinstance(data.get("text"), str):
            return p, data["text"]
        if isinstance(data, list):
            lines = []
            for seg in data:
                if isinstance(seg, dict):
                    t = seg.get("text") or ""
                    if seg.get("start") is not None and t:
                        lines.append(f"[{float(seg['start']):.0f}s] {t}")
                    else:
                        lines.append(t)
            return p, "\n".join(lines)
    return None, ""


def ocr_shots(run_dir: str, force: bool = False):
    """OCR every shots/*.png into one greppable dump, each shot name-tagged for citation."""
    shots = os.path.join(run_dir, "shots")
    out = os.path.join(run_dir, "slide_ocr.txt")
    if not os.path.isdir(shots):
        return None, "no shots/ dir"
    if os.path.isfile(out) and not force:
        with open(out, "r", encoding="utf-8", errors="replace") as fh:
            return out, ""
    pngs = sorted(f for f in os.listdir(shots) if f.lower().endswith((".png", ".jpg")))
    if not pngs:
        return None, "shots/ is empty"
    chunks, failed = [], []
    for name in pngs:
        try:
            res = subprocess.run(["tesseract", os.path.join(shots, name), "stdout"],
                                 capture_output=True, text=True, timeout=120)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            failed.append(f"{name}:{type(exc).__name__}")
            continue
        chunks.append(f"\n=== {name} ===\n{res.stdout}")
    if not chunks:
        return None, "tesseract unavailable or every shot failed: " + ", ".join(failed)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("".join(chunks))
    return out, ("ocr-failures: " + ", ".join(failed)) if failed else ""


def stamp(raw: str, pos: int) -> str:
    """Nearest timestamp at/before pos, else the shot filename the match sits under."""
    head = raw[max(0, pos - 600):pos]
    ts = TS.findall(head)
    marks = SHOT.findall(raw[:pos])
    tag = f"[src: shot {marks[-1]}]" if marks else "[src: transcript]"
    return f"{tag} @{ts[-1]}" if ts else tag


def find(raw: str, claim: str, window: int):
    """(kind, ratio, excerpt, tag) for one claim against one source."""
    nr, nr_map = norm(raw)
    nc, _ = norm(claim)
    if not nc or not nr:
        return "NOT FOUND", 0.0, "", ""
    hit = nr.find(nc)
    if hit >= 0:
        a, b = nr_map[hit], nr_map[min(hit + len(nc), len(nr_map) - 1)]
        lo, hi = max(0, a - window), min(len(raw), b + window)
        return "VERBATIM", 1.0, " ".join(raw[lo:hi].split()), stamp(raw, a)
    best, best_line = 0.0, ""
    for line in raw.splitlines():
        line = line.strip()
        if len(line) < 25:
            continue
        r = difflib.SequenceMatcher(None, norm(line)[0], nc).ratio()
        if r > best:
            best, best_line = r, line
    return ("PARTIAL" if best >= 0.60 else "NOT FOUND"), best, best_line[:300], ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir")
    ap.add_argument("--claims", nargs="*", default=[])
    ap.add_argument("--claims-file")
    ap.add_argument("--window", type=int, default=260, help="context chars around a verbatim hit")
    ap.add_argument("--ocr", action="store_true", help="(re)OCR shots/ into slide_ocr.txt")
    ap.add_argument("--force-ocr", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(args.run_dir):
        print(f"run_dir not found: {args.run_dir}", file=sys.stderr)
        return 2

    claims = list(args.claims)
    if args.claims_file:
        with open(args.claims_file, "r", encoding="utf-8") as fh:
            claims += [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]

    sources = {}
    tp, ttext = load_transcript(args.run_dir)
    if tp:
        sources["transcript"] = (os.path.basename(tp), ttext)
    ocr_wanted = args.ocr or args.force_ocr
    op, oerr = ("", "")
    if ocr_wanted:
        op, oerr = ocr_shots(args.run_dir, force=args.force_ocr)
    else:
        cand = os.path.join(args.run_dir, "slide_ocr.txt")
        op = cand if os.path.isfile(cand) else ""
    if op:
        with open(op, "r", encoding="utf-8", errors="replace") as fh:
            sources["slide_ocr"] = (os.path.basename(op), fh.read())
    chat = os.path.join(args.run_dir, "chat.txt")
    if os.path.isfile(chat):
        with open(chat, "r", encoding="utf-8", errors="replace") as fh:
            sources["chat"] = ("chat.txt", fh.read())

    print(f"run_dir  : {os.path.abspath(args.run_dir)}")
    for name, (fn, txt) in sources.items():
        print(f"  {name:10s} {fn:18s} {len(txt):>8,} chars")
    if oerr:
        print(f"  ! {oerr}")
    if not sources:
        print("no evidence sources found (need transcript.*, shots/*.png, chat.txt)")
        return 0
    if not claims:
        print("\nno --claims given: index built, nothing classified")
        return 0

    for i, claim in enumerate(claims, 1):
        print(f"\nCLAIM {i}: {claim}")
        verdicts = {}
        for name, (_fn, raw) in sources.items():
            kind, ratio, excerpt, tag = find(raw, claim, args.window)
            verdicts[name] = (kind, ratio, tag)
            if kind == "VERBATIM":
                print(f"  {name:10s} VERBATIM {tag}")
                print(f'             >> "{excerpt}"')
            elif kind == "PARTIAL":
                print(f"  {name:10s} PARTIAL  {ratio:.2f}  best line: {excerpt}")
            else:
                print(f"  {name:10s} NOT FOUND")
        t = verdicts.get("transcript", ("NOT FOUND", 0.0, ""))
        s = verdicts.get("slide_ocr", ("NOT FOUND", 0.0, ""))
        if t[0] == "VERBATIM":
            print(f"  VERDICT  : speaker said it — cite {t[2]}")
        elif s[0] == "VERBATIM":
            print(f"  VERDICT  : SLIDE-ONLY — cite {s[2]}; do NOT attribute it to the speaker")
        elif max(t[1], s[1]) >= 0.60:
            src = "transcript" if t[1] >= s[1] else "slide_ocr"
            print(f"  VERDICT  : paraphrase-only (best {max(t[1], s[1]):.2f} in {src})"
                  " — write 'our reading, not his words'")
        else:
            print("  VERDICT  : NOT FOUND in any source — drop the claim and say it was not said")
    return 0


if __name__ == "__main__":
    sys.exit(main())
