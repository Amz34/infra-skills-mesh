---
name: frontend-design
description: Use when designing a client-facing page or UI.
version: 1.2.3
author: Aamir Zameer (Hermes Agent), adapted from anthropics/skills `frontend-design` (Apache-2.0)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [design, css, frontend, client-work, no-faces, typography]
    related_skills: [bilingual-rtl-client-site, humanizer, popular-web-designs, sketch, svg-vector-visuals, chrome-print-pdf-production]
---

# Frontend Design (client-facing)

## When to Use

- Designing or redesigning a client-facing page, landing, dashboard or UI artifact.
- A page "looks like AI / like a template" and needs a real quality pass.
- An imagery or photography plan is needed for client work (hero, features, print).
- Not for: throwaway variant exploration (`sketch`), copying a known system
  (`popular-web-designs`), one-off artifact with no client (`claude-design`).

## Non-negotiables

1. **No human faces / living beings** in client-facing work — sites, emails, carousels, print,
   mockups. Inanimate subjects only: product, machine, surface, texture, sky, diagram. Exceptions:
   Aamir's own photo on his own approved profile, and the fire-lab line. Say the substitution out
   loud in the plan so nobody re-adds a stock photo.
2. **Client-facing copy is pure English**, one-word brand, no emoji, no AI-flavoured filler, never
   Hinglish.
3. **Brand isolation**: each client keeps its own palette and voice.
4. Bilingual builds go through `bilingual-rtl-client-site` (real RTL) — never a flipped screenshot.

## The five gates

1. **Tokens before layout.** Write the CSS custom properties (`--ink`, `--surface`, one `--accent`,
   optional `--accent-2`, `--muted`, `--line`, one radius, one spacing unit) and one derivation
   sentence ("accent = oxidized copper, from the client's signage"). A palette without a reason is
   decoration. Numbers, type scale, contrast ratios: `references/design-detail.md`.
   **Tokens are the only door.** Colour, space, radius and shadow reach the page through the token
   block — never as raw hex in a rule, never an arbitrary value, never `!important`, never a
   per-component override. If a component needs a different look, add a token or a named variant;
   do not patch it inline. (Verifiable: grep the artifact for `#`, `!important` and arbitrary-value
   brackets outside the token block.)
2. **Refuse the AI-default look.** Cream+terracotta+acid-green, purple→pink gradient hero, centered
   hero, three-card grid, "Trusted by" strip, emoji icons, shadow on everything — cut or invert.
   Full list + cures + imagery substitutions: `references/ai-default-traits.md`.
3. **Deliver the artifact, not the process.** See the output contract below.
4. **Look at it** (tool-driven runs): render it, `capture_screenshot()` at 360 and 1280 px, fix what
   the screenshot shows. Never ship a page you have not seen.
5. **Five questions per element.** Before an element ships, answer all five: **Purpose** (why does it
   exist), **Hierarchy** (how important is it), **Context** (how does it relate to its neighbours),
   **Accessibility** (can every user operate it), **Performance** (does it cost load or interaction
   time). An element that fails Purpose or Hierarchy is **cut**, not styled around. Failures on
   Accessibility or Performance are **fixed**, not noted.

## Output contract

One-shot answer (no scratchpad, no tools, no follow-up turn):

1. at most three lines of lead-in — the palette + derivation;
2. **one** fenced block with the **complete** artifact — never a fragment, never five little CSS/HTML
   pieces stitched by prose;
3. nothing after the block.

**Never abbreviate the artifact.** `<style>...</style>`, `<section hero>`, `<!-- rest of markup -->`
are not a deliverable: write every rule and every element, or cut a feature and say so. Be terse in
prose, complete in code.

**Critique requests.** When the ask is a review of an existing page rather than a build, every line is
a fix: name the property and value (`padding: 12px → 24px 32px`, `contrast 3.1:1 → 4.7:1`) or a
concrete before/after snippet. No adjectives, no "consider", no "feels cramped" — a finding that
cannot be pasted into the file is not a finding. Phrase each fix as `replace <x> with <y>` or
`property: value` (`padding: 12px → 24px`, `contrast: 3.1 → 4.7`). Hard ceiling: ≤8 findings,
≤350 words total, no intro paragraph — a long critique is a failed critique. Order by impact.

### Budget (hard numbers)

On a reasoning model the *completion* budget pays for deliberation **before any answer exists**: at
`--max-tokens 16000` one run spent 23,795 reasoning tokens and never emitted the artifact at all.
Final run at 48k (2026-09-29, layer-3 gate `pass 3/3`): landing **100% vs baseline 0%** (the
baseline's 5,442-word page dump fails *"stays a page, not an essay"*), imagery 100% = 100%,
critique 100% = 100% — and 157 words / 1,468 reasoning tokens vs the baseline's 1,170 / 6,191.
Keep the deliberation short and the prose tight; a truncated answer scores zero no matter how good
the reasoning was.

- **Prose budget: ≤120 words total**, everything outside the artifact block. One fenced block,
  ≤3 lines of lead-in, nothing after it.
- **Answer the five questions silently.** Never write out Purpose/Hierarchy/Context/Accessibility/
  Performance per element — the answers change the artifact, they are not part of the answer.
- **No gate recap, no done-check restatement, no process narration**, no "here's what I did",
  no option menus. Say only what the client must know to ship it.
- **Decide, don't deliberate.** Pick the first palette that satisfies the gates, state its one-line
  reason, commit. Never enumerate alternatives, never second-guess a choice already justified —
  hidden thinking is still billed against the same budget as the artifact. Two options maximum.
- **When the cap is near, cut features — never narrate and never abbreviate.** A smaller complete
  artifact beats a bigger truncated one; state the cut in one line.
- Long brief that genuinely needs a long artifact? Raise length only if the user asked for it.

Measured on `deepseek-v4-flash` (2026-09-14, `~/ops/evals/skills-bench/`): with this skill injected,
2 of 3 runs returned a skeleton with literal `...` placeholders and 1 spent 19k characters narrating
the process — 0 of 3 runs passed the artifact gate while a no-skill baseline passed 2 of 3. The
skill's process is real work; it is not the answer text. Narrate nothing, emit the file.

## Done-check

- token block present, one accent, ≤10% of area, contrast verified
- colour/space enter only through tokens: no raw hex or arbitrary values outside the token block, no
  `!important`, no inline component overrides (variants instead)
- every element answered the five questions; Purpose/Hierarchy failures were cut, Accessibility and
  Performance failures were fixed
- no AI-default trait survives; imagery is inanimate and the plan says so
- real copy, English, brand isolated, zero emoji
- artifact complete (no `...`), single fenced block, no appended explanation
- prose outside the artifact ≤120 words; five questions answered silently, never written out
- critiques: ≤8 findings, ≤350 words total, each ≤25 words, `property: value` or a before/after —
  adjective-only lines and intro paragraphs are failures, not style
- screenshots at 360 + 1280 inspected when tools are available
- after editing this skill: `~/ops/evals/skills-bench/skill_lint.py <dir>` → no hard fail, and
  re-benchmark with `run_bench.py --skill frontend-design --evals evals.example.json --runner deepseek --iterations 3 --with-baseline --max-tokens 32000 --ledger`
  (a 16k cap is spent on reasoning before the artifact is written — see Budget)

## Reference

- `references/design-detail.md` — token block, type scale, contrast, pass-2 build order, screenshot
  loop, interface writing, RTL edition, related skills.
- `references/ai-default-traits.md` — the full refuse list, copy cliches, cures, imagery substitutions.
- Upstream inspiration, read then rewritten (not copied): `anthropics/skills` → `frontend-design`
  (Apache-2.0); frozen copy at `~/ops/vendor/skills/anthropics/frontend-design/` with pinned commit
  and hashes in `~/ops/vendor/skills/anthropics/PROVENANCE.md`.
- Token-discipline rule + five-question pre-flight adapted (rewritten, not copied) from
  `mustafakendiguzel/claude-code-ui-agents` (MIT) — vendored 2026-09-29 at commit `e224ca06d45f`,
  frozen copy `~/ops/vendor/skills/mustafakendiguzel/claude-code-ui-agents/` with hashes in its
  `PROVENANCE.md`. Nothing else from that pack was adopted: it is a dormant one-day prompt dump
  (722★ on LinkedIn distribution, no commits since 2025-08-08).
