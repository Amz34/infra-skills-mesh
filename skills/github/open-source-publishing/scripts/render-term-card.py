#!/usr/bin/env python3
"""Render captured terminal output as a dark 'terminal card' PNG.

Deterministic, offline proof screenshots for a published repo's README:
no browser, no image generation, no stock art, no faces -- just the real
command output, styled so a reader sees it at a glance.

Usage:
    render-term-card.py <input.txt> <out.png> "<command that produced it>"

Colour rules: a line containing E_ / FAIL / Error goes red; a line with
passed / clean / OK goes green; everything else stays default grey.

Fonts: DejaVuSansMono (Ubuntu/Debian: /usr/share/fonts/truetype/dejavu).
On macOS switch MONO/MONO_B to /System/Library/Fonts/Menlo.ttc.
Requires pillow (python3 -c "import PIL; print(PIL.__version__)").
"""
import sys
import textwrap
from PIL import Image, ImageDraw, ImageFont

MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
W, PAD, WRAP, LINE_H = 1200, 40, 96, 24

src, dst, title = sys.argv[1], sys.argv[2], sys.argv[3]
body = open(src).read().rstrip().splitlines()
lines = [chunk for line in body for chunk in (textwrap.wrap(line, WRAP) or [""])]

f = ImageFont.truetype(MONO, 16)
bold = ImageFont.truetype(MONO_B, 16)
H = 108 + LINE_H * len(lines)
im = Image.new("RGB", (W, H), "#0b0f14")
d = ImageDraw.Draw(im)
d.rounded_rectangle((16, 16, W - 16, H - 16), 14, fill="#121821", outline="#232c38", width=2)
for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):          # traffic lights
    d.ellipse((PAD + i * 24, 34, PAD + i * 24 + 12, 46), fill=c)
d.text((PAD, 60), title, font=bold, fill="#7d8590")

y = 96
for ln in lines:
    col = "#c9d1d9"
    if any(k in ln for k in ("E_", "FAIL", "Error", "error")):
        col = "#ff7b72"
    elif any(k in ln for k in ("passed", "clean", "OK", "success")):
        col = "#3fb950"
    d.text((PAD, y), ln, font=f, fill=col)
    y += LINE_H

im.save(dst)
print(dst, im.size)
