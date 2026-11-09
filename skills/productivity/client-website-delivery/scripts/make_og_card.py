#!/usr/bin/env python3
"""Generate a 1200x630 OG social card for a client site.

Usage: edit the BRAND section below, then run from the site root:
    python3 make_og_card.py
Output: assets/img/og-card.png — reference it from og:image / twitter:image
and add og:image:width=1200 / og:image:height=630 beside it.

LinkedIn (and most socials) require ~1.91:1 for a clean preview card; a
plain logo upload often fails or renders tiny. This produces a branded
card from an existing logo PNG.
"""
from PIL import Image, ImageDraw, ImageFont
import os

# --- BRAND SECTION (edit per client) ---
SITE_ROOT = "."                                  # where assets/ lives
LOGO = "assets/img/logo.png"                     # relative to SITE_ROOT
BRAND_NAME = "AVVS"                              # big brand word
BRAND_SUB = "Air Valve System"                   # subtitle
LINES = [
    "Precision Venturi Valves · Isolation Room Controllers",
    "Hospital Monitoring & Maintenance — Worldwide",
]
URL_TEXT = "avvs-triatek.pages.dev"              # shown in footer band
ACCENT_RGB = (212, 175, 55)                      # gold accent line
BAND_RGB = (11, 59, 79)                          # dark navy footer band
# --- END BRAND SECTION ---

W, H = 1200, 630
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

def load_font(size, bold=False):
    for p in FONT_PATHS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def main():
    img = Image.new("RGB", (W, H), "#0D9488")    # teal = medical precision
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, H - 90, W, H], fill=BAND_RGB)

    # Logo on the right
    logo = Image.open(os.path.join(SITE_ROOT, LOGO)).convert("RGBA")
    logo.thumbnail((440, 440))
    img.paste(logo, (W - logo.size[0] - 70, (H - logo.size[1]) // 2 - 20), logo)

    # Text on the left
    draw.text((70, 130), BRAND_NAME, font=load_font(72, bold=True), fill="#FFFFFF")
    draw.text((74, 240), BRAND_SUB, font=load_font(40), fill="#E6F7F5")
    y = 330
    for line in LINES:
        draw.text((70, y), line, font=load_font(34), fill="#C9F2EE")
        y += 55
    draw.rectangle([70, 96, 300, 104], fill=ACCENT_RGB)
    draw.text((70, H - 70), URL_TEXT, font=load_font(26), fill="#8FD8D0")

    out = os.path.join(SITE_ROOT, "assets/img/og-card.png")
    img.save(out, "PNG")
    print(f"Saved {out} {W}x{H}")

if __name__ == "__main__":
    main()
