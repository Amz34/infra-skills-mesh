# Client-facing stills: text, label and symbol safety

Image models render text and script as confident gibberish. In client-facing work (carousels, ads, sites, video frames) that lands as a defect — and in Gulf/KSA work, garbled Arabic calligraphy on a religious article reads as disrespect.

## Prompt rules (append to every client-facing image prompt)
- `no text, no writing, no labels, no signage, no printed material, no watermark`
- Label-prone props: ask for `unbranded, plain glass bottle, no label` — never let a fake brand mark appear.
- **Never prompt calligraphy or written script** (Arabic/Hebrew/Devanagari/etc.) on religious, branded or packaging subjects. Swap in text-free equivalents that still read as the same object:
  - prayer mat → "plain cream woven fabric, simple grey trim, completely blank, no writing or motifs"
  - Qibla marker → "plain brushed brass arrow marker on a small wooden base, no engraving"
  - menu / info card → drop the card entirely; if text is genuinely needed, burn it in later with ffmpeg or HTML.
- Add the same prohibition to the theme/prompt-set `rules` array so every later batch inherits it.

## Verification gate (before the still enters any deliverable)
Tile and look:
```bash
ffmpeg -y -v error -pattern_type glob -i '*.jpg' -vf "scale=360:-1,tile=3x2" -frames:v 1 sheet.png
```
Inspect the sheet visually. Any tile with text, pseudo-script, brand marks or a wrong subject → regenerate that single still and re-sheet. Still-level checks catch this before any expensive render.

Free-lane cost: ~170 images/day (≈58 neurons each); on exhaustion the API returns `4006` → `--fallback pollinations` for filler, or wait for 00:00 UTC. These text-safety rules cost nothing and apply to any image lane.
