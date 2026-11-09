# Text-Only Visual QA — verify user visual complaints without seeing images

Use when the model is TEXT-ONLY but the user sends screenshots/photo reviews
of a website ("gaps between sections", "text blurred", "looks generic") and
you must diagnose + verify fixes. Proven 2026-09-02 estelar-demo v2→v3.
Ground truth = DOM + pixels measured programmatically, never vibes.

## What the user's photos are

Files land in `~/.hermes/cache/images/` (e.g. `img_f148356df7b3.jpg`).
Confirm they are real images first: `file` magic bytes (base64-as-text
saved as .png is a known trap — decode first).

## Pixel forensics (PIL + numpy) — what screenshots actually show

- **Dark-band / void detection**: row-mean brightness per horizontal strip;
  ~440px near-black bands in a screenshot = giant empty region (real "gap"
  symptom) vs. dark dusk imagery that is intentional content.
- **Blur proxy**: luma variance per region (≈670 vs ≈634 = soft vs sharp),
  Laplacian variance. "Blurred text" in a photo is usually NOT css blur —
  it is a ghosted opacity state from reverse-stagger animations (text stuck
  at opacity 0.4–0.6 while scrolling up).
- **Layout scale**: 624 CSS px wide @ dpr 1.6 tells you the user is on a
  phone — check mobile breakpoints, not desktop.
- **ASCII brightness grids** (chars over a downscaled luma map) let you
  "see" composition in text.

## DOM truth — the definitive gap/blur test (browser_exec)

Pixel voids lie (dark imagery ≠ gap). Measure the live page instead:

1. Section heights: `document.querySelector('#featured').offsetHeight` —
   8,315px @ 844px viewport was the smoking gun (300vh sticky tracks).
2. Element-free viewport rows: while scrolling, check whether ANY element
   intersects each viewport slice. Real gap = a viewport row with no
   intersecting element. Count = 0 after fix.
3. Computed opacity at rest AND mid-track: ghost state = < 1.0 while the
   text is pinned/visible.
4. CSS truth: `getComputedStyle(el).opacity/fontSize/fontFamily` — verify
   fixes landed (font swap, 17px base, opacity 1.0).

## Order of operations

1. Read the user's words for the SYMPTOM; never argue with the photo.
2. Forensics on the photos (bands, variance, layout) → hypotheses.
3. Read the component source — the REAL root cause is in the animation code
   (track heights, scrub windows, stagger params), not the pixels.
4. Fix in source; rebuild; re-measure DOM + forensics until numbers pass.
5. Compose PIL review sheets (EN grid + AR grid, resize ≤760w) for Telegram.

Related: sticky scroll-stack root cause + fix parameters in
references/react-vite-premium-build.md ("Sticky scroll-stack pitfalls").
