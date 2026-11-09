# Agentic mapping — arrow model section (added 2026-09-15)

New `#amSec` card inside the **Agent map** tab, below the board + support sections.
Files: `web/agentic-map.js` (module `window.AMAP`), CSS block `/* ---- Agentic mapping: 16:9 arrow model ---- */`,
`<script src="agentic-map.js?v=N"></script>` inserted immediately before the main inline `<script>`,
render call appended to `RUNS.render(); ARGMAP.render();` line.

## Layout (as built)
- Wide (host >= 900px): fixed **16:9 SVG**, `viewBox="0 0 1600 900"`, `width:100%;height:auto` → measured 1.78:1 at
  1600/1280/1024 viewports. Geometry is absolute (OWNER 20..58, HUB 76..152, rows at cap/bubble y pairs), so text
  can never reflow-overlap. Narrow (<900px): `#amflow` stacked cards with the same wiring in text.
- Content: OWNER → D1 hub fan (2 `cmd` + 8 `deleg`) → row bands (COMMAND/BUILD/INTELLIGENCE&GROWTH/ASSURANCE/NEW),
  `D2 → 8 gates` (amber dashed), BUILD bracket at y=410 → 3 `call` arcs, left return bus x=30 for 4 `verify`,
  right return bus x=1570 for 6 `new` rollouts. Legend 6 entries, counts + footer text inside the canvas.
- Text safety: every label measured with a hidden canvas `measureText` and ellipsized to the box width
  (`ell(txt,size,weight,maxW)`) — no post-hoc DOM fixing.

## Pitfalls learned (reuse these)
1. **`state` is a lexical global, not `window.state`.** An external `<script src>` cannot see `window.state`
   (it is `const`-declared in the inline script) and fails silently → `typeof state!=='undefined' ? state : window.state`.
2. CSS `display:none` on a container the JS shows by clearing the inline style (`el.style.display=''`) leaves it
   hidden. Give JS-managed containers no `display` rule in CSS, or set `display:block` explicitly.
3. Row-caption maps built from the geometry objects (`ROWS[0].cap` = a **y coordinate**) leak numbers into the UI.
   Always take caption text from `model.bands[].cap`, never from the layout constants.
4. `verify/drive.py` counts section rows (59 now: 58 + the latex-mcp probe added alongside) — a PASS means every
   reported service still renders a row.

## QA recipe (repeat after any change)
`python3 /tmp/amsec_qa.py` (CDP, port 9333): 4 viewports (1600x1000, 1280x900, 1024x900, 390x844 mobile) →
clicks the Agent map tab, waits for `#amSec .am-bub` / `.amfl-node`, then reports per-viewport
`overlap_n`, `clipped`, `page_overflow_x`, svg `ratio`, counts and `console_errors`, and writes
`/tmp/amsec-<name>.png` clipped to the section. Then confirm visually with `vision_analyze` on a 1:1 crop.
`window.__amAudit()` returns the geometric proof (bubble box intersections + out-of-canvas check).

## "Live pe reflect nahi ho raha" — 2026-09-15 close-out

The section rendered in an isolated page but the live dashboard showed an empty card. The cause was **not**
this file: `status.db` was lock-deadlocked (rollback-journal + a ~20 s reader holding SHARED locks) so
`/data.json` had no fresh data, `sw.js` served a stale shell, and the renderer had **no tab-show hook** — it
only ran on the 20 s data poll, so opening the Agent map tab showed nothing. Fix = tab-show hook
(`RUNS.render(); ARGMAP.render()` on tab click + a `MutationObserver`/visibility hook on the section) **plus**
the WAL + SW fixes in `references/freshness-and-lock-debugging.md`. Diagnostic rule: when a section is empty,
first prove the server serves the new markup (`grep -c amSec` on the fetched HTML) and that the payload is
fresh (`iso` / `updated_age_s`) before touching this module.

Final verified state (after cleanup of the temporary `window.__amStep` markers + `agentic-map.js?v=7` and
`<meta name="dash-build" content="v49">` bumps):
- desktop 1600×1000 → `svg` variant, ratio **1.78**, **23 bubbles / 31 arrows, `overlaps: []`,
  `out_of_canvas: []`**;
- mobile 414×896 → `flow` variant, **23 nodes**, `scrollW 390/390` (no horizontal overflow);
- `verify/drive.py` exit 0 → "PASS: 59 rows rendered for 59 reported services", `data_age_s=55`.
