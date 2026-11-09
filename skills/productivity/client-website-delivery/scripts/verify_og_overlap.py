#!/usr/bin/env python3
"""Verify an OG card has no text/logo overlap.

Counts non-background pixels in three horizontal zones of a 1200x630 card:
text zone (left), gap zone (middle), logo zone (right). The gap zone must be
essentially empty — if not, text and logo collide (the classic "tagline over
logo" bug that makes LinkedIn previews look broken).

Usage:
  python3 verify_og_overlap.py <card.png> [text_x1] [gap_x0] [logo_x0]

Defaults target a 1200x630 card with text ending at x=750, gap 750-800, logo
starting at x=800. Adjust the BG color below if your card's background isn't
white. Exits 0 (clean) or 1 (overlap detected).
"""
import sys

from PIL import Image

W, H = 1200, 630
BG = (255, 255, 255)  # card background color


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "assets/img/og-card.png"
    tx1 = int(sys.argv[2]) if len(sys.argv) > 2 else 750
    gx0 = int(sys.argv[3]) if len(sys.argv) > 3 else 750
    lx0 = int(sys.argv[4]) if len(sys.argv) > 4 else 800

    img = Image.open(path).convert("RGB")
    px = img.load()

    def count(x0, x1):
        n = 0
        for y in range(0, H, 2):       # 2px sampling: fast, plenty precise
            for x in range(x0, x1, 2):
                if px[x, y] != BG:
                    n += 1
        return n

    text = count(0, tx1)
    gap = count(gx0, lx0)
    logo = count(lx0, W)
    print(f"text zone: {text} non-bg px | gap zone: {gap} | logo zone: {logo}")

    if gap <= 2:  # sampling tolerance for anti-aliasing edges
        print("OK: no overlap between text and logo zones")
        return 0
    print("OVERLAP: gap zone is not empty — text and logo collide")
    return 1


if __name__ == "__main__":
    sys.exit(main())
