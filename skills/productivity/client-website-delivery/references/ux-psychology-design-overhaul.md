# UX-Psychology Design Overhaul — "generic design" fixes (proven 2026-08-31)

Trigger: user says a delivered page looks "generic", "boxy", "dashboard-like",
"template-y", or "make the best as per this <LinkedIn/post URL>" (reference +
its COMMENTS both matter). Applied to Aamir's Topmate replica
(`~/projects/topmate-aamir/index.html`, 16 service cards) — replaced a light
boxy emoji-dashboard with a premium dark editorial design in one pass.

## The framework (Rasel Ahmed UX psychology, via LinkedIn post + comments)

Core principle from the comments: **value pehle samjho, design invisible ho**
— if the value isn't understood in the first 5 seconds, the rest of the
experience never gets a chance. Every design decision maps to one of 5 steps:

| Step | What it means | What we did on the page |
|------|---------------|-------------------------|
| **Attention** | Stops the scroll | Dark ink hero, huge serif display headline, radial gradient glows (emerald/gold/purple), photo in a ring, grain texture |
| **Perception** | Makes sense in seconds | Value-prop headline ("Your career moves the day you stop guessing"), microcopy, 5-second clarity — no wall-of-text |
| **Cognition** | No thinking required | 16 services grouped into 3 labelled categories (Career Calls / CV & LinkedIn / AI & Business Growth), consistent type+duration+price badges on every card |
| **Emotion** | Feels right | Trust layer: SCE number, money-back guarantee, "GCC insider" badge, testimonials, refined typography = premium not salesy |
| **Action** | One clear next step | Exactly ONE CTA per card + sticky mobile CTA + live countdown |

**Signature move:** add a "Designed around how your brain decides" strip that
literally renders the 5 steps (01 Attention — "Stops the scroll", … 05 Action
— "One clear next step") as a numbered journey row. The design itself then
proves the framework the user referenced — they see the post's theory made
concrete. Users notice this.

## Design system (the "not generic" recipe)

- **Type:** Fraunces (or Instrument Serif) for display headings + Inter for
  body — serif display is what reads as editorial/premium vs the default
  boxy-sans dashboard look. Google Fonts, two families max.
- **Palette:** deep ink `#0a0e1a` + warm paper `#f7f6f2` (NOT pure white),
  emerald/gold/purple radial gradients for glow accents. Kill the flat
  "primary button color on white cards" default.
- **Cards:** 1px hairline + radius 16 + hover translateY(-3px) + shadow;
  popular card gets a top accent line, not a garish badge.
- **No emoji as icons** — emoji-heavy badges read cheap/generic. Minimal
  inline SVG per category instead.
- **Motion:** IntersectionObserver fade-up reveal on scroll; real countdown
  (JS to midnight/local) instead of a static "offer ends soon".
- **Structure:** sticky blur nav, grouped section headers, full-width
  guarantee strip, dark footer. Never card-on-card-on-card everywhere.

## Verification recipe (always run before delivering)

```python
# 1. HTML validity
from html.parser import HTMLParser  # unclosed tags + errors must be empty
# 2. Grep counts — EXPECT to reconcile, don't trust raw numbers:
grep -oE 'class="service"' index.html | wc -l        # exact, NOT class="service
grep -c 'class="service popular"' index.html         # popular card counted separately
grep -oE '<h3>[^<]+' index.html | wc -l              # includes group + journey h3s
grep -c '<s>' index.html                             # strikethrough anchors
# 3. Tunnel/live render: curl 200 for root + photos, then browser_exec
#    screenshot → cp /home/ubuntu/.config/browser-harness/tmp/shot.png preview-x.png
#    → deliver via MEDIA: path so the user SEES the design, not just a URL
```

Pitfall: naive `class="service` grep double-counts `class="service popular"`.
Pitfall: `<h3>` count mixes service titles + group headers + journey steps —
reconcile against the expected breakdown (e.g. 16 svc + 3 groups + 5 journey
= 24), don't just match raw count to cards.

## Workflow notes

- Read the ENTIRE existing file before rewriting (4× read_file chunks for
  ~800 lines) so no product/price/CTA data is lost in the redesign.
- Preserve every href, price, WhatsApp CTA, countdown id, photo-onload logic,
  JSON-LD schema — redesign is visual, data must survive verbatim.
- Rewrite as ONE full `write_file` (not patch-by-patch) — faster and the
  HTML validity check catches mistakes.
- After redesign: live preview link + hero screenshot to user, ask approval,
  THEN prod deploy (never deploy a redesign without the user seeing it).
