# Agent map v9 — responsive board (4:3 wide / stacked mobile) + QA recipe

Applied 2026-09-15 to `~/clients/invertio/infra-dashboard/web/index.html` (build v9, sw cache v40).

## What the "broken on phone" look actually was
The section was NOT the only culprit: `nav.sectabs` (6 tab buttons, no wrap) overflowed a 390px
viewport → the *whole page* laid out at ~504px wide, so the phone screenshot showed a squeezed,
right-clipped board. **Always audit page-level `documentElement.scrollWidth` first**; a one-line
tab-bar wrap (`@media (max-width:780px){.sectabs{flex-wrap:wrap}}`) fixed the squeeze.

## Ratio decision
- Board = **4:3** on wide screens (`@media (min-width:1500px){#mapSec .omleft{aspect-ratio:4/3}}`).
  Rationale: the chart body measures ~1.36:1 natural; 16:9 would leave half the canvas empty and
  shrink text. Measured after tuning: `.ommain` 1208x886 inside a true 4:3 box.
- `aspect-ratio` only holds if the box holds the CHART ONLY. Contracts / escalation ladder / legend
  must live outside it — that is why the module writes them into a sibling `#omsecs` element.
- <1150px: fluid stacked view (no canvas) — cards `repeat(auto-fit,minmax(235px,1fr))` (c3 bands
  `minmax(335px,1fr)`), 1 card/row on phones, plane rail becomes a 2x4 chip grid, arrows hidden
  (`#maparrows{display:none}` + the JS skips drawing below 1150px), link counts shown instead as
  `↔in/out` chips on every card.

## Pitfalls learned
- **Inline `style="grid-template-columns:repeat(cols,…)"`** on `.omnodes` beat every CSS breakpoint.
  Emit a class (`c3`/`c4`) instead; never inline grid templates you want to make responsive.
- `.arnwrap` is a **full-bleed** card (`width:min(1580px,100vw-22px)` + negative side margin), so it
  is WIDER than `#mapSec`. Screenshotting `#mapSec` clips the left rail — clip
  `#mapSec .card.arnwrap` (or the viewport) instead.
- Old rules with `overflow:hidden;white-space:nowrap` (ladder steps, band captions) survive an
  append-only CSS override unless the new rule sets `overflow`/`white-space` explicitly.
- Cascade-safe patching: append the new CSS block just before `</style>` (same specificity → later
  wins), and bump `sw.js` CACHE on EVERY index.html change.
- The module's link helper: `linkN(dd)` counts in/out edges from `data.agentruns.edges`; cache-free
  and cheap, used for the `↔i/o` chip.

## QA recipe (do this for every layout change)
`tests`-style CDP script (`/tmp/omv9_qa.py`, reusable): for each viewport
[(1600x1000 desktop), (1280x900 laptop), (1024x900 tablet), (390x844 mobile=true)] →
`Emulation.setDeviceMetricsOverride` → `#map` tab → click → evaluate an audit that returns:
`page_overflow_x`, section size, board ratio, node/band/arrow/rail counts, **pairwise text overlap
of leaf text elements** (excluding ancestor/descendant pairs), clipped-text list
(`overflow:hidden && scrollWidth>clientWidth+2`), console errors, then element-clip screenshot.
PASS bar: `overflow none · overlaps 0 · clipped 0 · console 0` on all four viewports.
Gates: `python3 verify/drive.py` (row count vs reported services) + `python3 verify/qa_fleet_block.py`.
