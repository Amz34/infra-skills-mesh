#!/usr/bin/env python3
"""OCR a scanned PDF whose pages may be ROTATED or MIRRORED.

Why this exists: buyer-published tender / corrigendum scans frequently render at 90/180/270
degrees, or mirrored, and tesseract then returns reversed word-salad (e.g. "9202-80-EL" for
"18-08-2026") that looks like a hopeless scan. It is not: the page just needs re-rendering in the
right orientation. Reversing the OCR *text* does not work — the image must be transformed.

Method: score 8 orientation variants (0/90/180/270 deg x normal/mirrored) of a sample page against
a common-English-word list, pick the winner, then OCR every page at that orientation.

Usage:
    python3 ocr_orient.py <input.pdf> <output.txt> [dpi=200] [first_page=1] [last_page=0]
    (# last_page=0 means "to the end")

Requires pdftoppm + tesseract + Pillow (all present on the standard VM image).
"""
import glob
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageOps

WORDS = {
    "the", "and", "of", "for", "shall", "as", "to", "in", "is", "be", "by", "with", "or", "not",
    "any", "all", "company", "contract", "date", "page", "price", "work", "service", "bid",
    "tender", "period", "payment", "may", "will", "under", "from", "at", "on", "each", "this",
}


def variants(im):
    """8 orientations: 4 rotations x (normal, mirrored)."""
    mirrored = ImageOps.mirror(im)
    return [
        ("0", im),
        ("r90", im.rotate(90, expand=True)),
        ("r180", im.rotate(180, expand=True)),
        ("r270", im.rotate(270, expand=True)),
        ("mirror", mirrored),
        ("mirror_r90", mirrored.rotate(90, expand=True)),
        ("mirror_r180", mirrored.rotate(180, expand=True)),
        ("mirror_r270", mirrored.rotate(270, expand=True)),
    ]


def tesseract(im, psm="6"):
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        im.save(path)
        res = subprocess.run(["tesseract", path, "stdout", "--psm", psm],
                             capture_output=True, text=True)
        return res.stdout or ""
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def score(text):
    tokens = re.findall(r"[A-Za-z]{2,}", text.lower())
    return sum(1 for t in tokens if t in WORDS)


def pick_orientation(files, psm="6", sample=2):
    report = {}
    for path in files[:sample]:
        im = Image.open(path)
        for name, variant in variants(im):
            report[name] = report.get(name, 0) + score(tesseract(variant, psm))
    best = max(report, key=report.get) if report else "0"
    return best, report.get(best, 0), report


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    pdf, out_path = sys.argv[1], sys.argv[2]
    dpi = sys.argv[3] if len(sys.argv) > 3 else "200"
    first = sys.argv[4] if len(sys.argv) > 4 else "1"
    last = sys.argv[5] if len(sys.argv) > 5 else "0"

    tmpdir = tempfile.mkdtemp(prefix="ocr_orient_")
    prefix = os.path.join(tmpdir, "pg")
    cmd = ["pdftoppm", "-r", dpi, "-gray", "-f", first]
    if last != "0":
        cmd += ["-l", last]
    cmd += [pdf, prefix]
    subprocess.run(cmd, check=True)

    files = sorted(glob.glob(prefix + "-*.p?m"))
    if not files:
        print("no pages rendered from", pdf)
        return 1

    rotation, hits, report = pick_orientation(files)
    print("pages:", len(files), "| chosen orientation:", rotation, "| word hits:", hits)
    print("scores:", dict(sorted(report.items(), key=lambda kv: -kv[1])))
    if hits < 5:
        print("WARNING: every orientation scored near zero - the scan may be genuinely unusable")

    rotate_map = {"r90": 90, "r180": 180, "r270": 270}
    mirror = rotation.startswith("mirror")
    angle = rotate_map.get(rotation.replace("mirror_", "").replace("mirror", "0"), 0)

    def one(path):
        im = Image.open(path)
        if mirror:
            im = ImageOps.mirror(im)
        if angle:
            im = im.rotate(angle, expand=True)
        return tesseract(im)

    with ThreadPoolExecutor(max_workers=4) as pool:
        pages = list(pool.map(one, files))

    with open(out_path, "w") as fh:
        fh.write("\n".join(pages))
    print("written:", out_path, os.path.getsize(out_path), "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
