# Design detail — tokens, type, build order, evidence loop

Loaded on demand from `SKILL.md`. Use when the run actually needs the numbers.

## Token block (write this before any layout)

```css
:root{
  --ink:#101418;        /* text, near-black, never pure #000 */
  --surface:#f6f4ef;    /* page ground */
  --accent:#c8552b;     /* ONE accent, derived from the subject */
  --accent-2:#2f6f5e;   /* optional support, max 10% of area */
  --muted:#6b7280;      /* secondary text */
  --line:rgba(16,20,24,.12);
  --r:10px; --sp:1rem;  /* one radius scale, one spacing unit */
}
```

State the derivation in one line: *"accent = oxidized copper, taken from the client's existing
signage"*. A palette without a reason is decoration.

- 60/30/10 split: ground / ink / accent. Accent on ≤10% of the visible area.
- Type: one display face + one text face. Define a scale (12/14/18/28/44) and use only those steps.
  Body 16–18px desktop, line-height 1.5–1.65, measure 60–75ch.
- Contrast: 4.5:1 body, 3:1 large text and borders. Check the accent on the surface, not only on white.
- Fonts: system/self-hosted stacks. No `@import` from Google Fonts in a client deliverable unless
  the client accepts the third-party call (privacy + speed).

## Tokens are the only door

The token block is the single entry point for colour, space, radius and shadow. Inside the artifact
this means no escape hatches:

- no raw `#hex` / `rgb()` / `hsl()` outside `:root` (a tint belongs in the token block as
  `--accent-soft: hsl(var(--accent) / .12)`, not inline);
- no arbitrary values (`w-[437px]`, `bg-[#c8552b]`) — if the number is not on the scale, add it to the
  scale or use the nearest step;
- no `!important`, no `style="…"` on an element a class could cover;
- no per-component override: a button that needs a second look gets `variant="quiet"`, and the variant
  reads tokens. Copy-pasted component CSS that drifts from the tokens is the bug this rule prevents;
- one radius scale, one spacing unit — every gap is a multiple of it.

Check it mechanically before shipping: `grep -nE '#[0-9a-fA-F]{3,8}|!important|\[[0-9]+(px|rem)\]'`
and confirm every hit is inside the token block. HSL token format is preferred so opacity variants
(`hsl(var(--accent) / .3)`) stay derivable, but the discipline is the point — not the colour space.

## Five-question pre-flight (per element)

Ask for each element, in order: **Purpose** — why does it exist; **Hierarchy** — how important is it
relative to neighbours; **Context** — how does it sit with what surrounds it; **Accessibility** — can
every user read and operate it; **Performance** — what does it cost in load or interaction time.

Routing the answers: Purpose or Hierarchy unclear → **cut the element** (do not restyle it into
relevance). Accessibility or Performance weak → **fix it** (contrast, focus ring, target size,
`loading="lazy"`, no layout-shift animation). A five-question pass that only ever produces "fine,
keep it" means the questions are not being asked honestly.

## Pass 2 — critique, then build

Write down: the client, the visitor's single task, the one action (CTA), the three things the page
must prove. Critique the Pass-1 draft against those four lines; change the plan where it fails.
The critique stays in scratch output — with real tools (files, subagents) it is written to a file,
in one-shot mode it collapses silently into the artifact.

Build order: tokens → type scale → layout skeleton with real copy (no lorem ipsum) → states
(hover/focus/empty/error/loading) → responsive at 360 / 768 / 1280 → print/PDF if applicable
(`chrome-print-pdf-production`).

## Look at it (tool-driven runs)

Never ship a page you have not seen rendered. This VM has Chrome on CDP 9333
(`chrome-automation.service`, Xvfb :99) and `browser_exec` — load the page, call
`capture_screenshot()`, fix what the screenshot shows (overflow, clipping, contrast, wrapping, dead
space). Minimum two shots: 360px and 1280px wide.

## Interface writing

Labels are sentences a person says out loud. "Book a survey", not "Submit". One verb per button.
Errors say what happened and what to do next. No exclamation marks, no "Oops!", no emoji, no
marketing adjectives inside product UI. Client-facing copy is pure English, brand isolated, no
emoji, never Hinglish.

## RTL / Arabic edition

Add the Arabic edition through `bilingual-rtl-client-site`: real `dir="rtl"`, mirrored spacing and
icons, Arabic-capable font stack. Never a flipped screenshot, never a translation bolted into the
English layout.

## Related skills

`bilingual-rtl-client-site`, `humanizer`, `popular-web-designs`, `sketch`, `svg-vector-visuals`,
`chrome-print-pdf-production`, `html-canvas-interactive`.
