# Render QA for the infra dashboard (proven 2026-09-10)

Verify a UI change against the **live** dashboard (`http://127.0.0.1:8765/`), never against the
source file alone. `verify/drive.py` covers the tiles view; use this recipe for any other section.

## Recipe (no browser daemon — it is blocked for 127.0.0.1)
1. Import the shared driver instead of rewriting CDP:
   ```python
   sys.path.insert(0, "/home/ubuntu/.hermes/skills/devops/headless-browser-automation/scripts")
   import cdp_cli                      # Tab(ws_url), pick(port, sel), tabs(port)
   ```
   Run it with the venv that has `websockets`: `/home/ubuntu/.venvs/gws/bin/python`.
2. Launch a throwaway headless Chrome on its own port + profile (ports 9222/9223 belong to other
   work — do not hijack them):
   ```python
   subprocess.Popen(["google-chrome","--headless=new","--no-sandbox","--disable-gpu",
     "--remote-debugging-port=9251","--user-data-dir=/tmp/chrome-<task>",
     "--no-first-run","--window-size=1400,2600","about:blank"])
   ```
   Poll `http://127.0.0.1:9251/json/version` until it answers, then
   `cdp_cli.Tab(cdp_cli.pick(9251,"about:blank")["webSocketDebuggerUrl"])`.
3. `Tab.call("Page.enable")` → `Tab.nav(url)` → `time.sleep(2.5)` (the page fetches `/data.json`).
4. **Click the nav tab before asserting.** Sections other than the tiles view are `display:none`
   until `[data-v="<id>"]` (`mm`, `eco`, `term`, …) is clicked — `offsetParent` is `null` and every
   rect is 0×0 otherwise, which looks exactly like a failed render.
5. Assert on the rendered DOM with one `Runtime.evaluate` returning `JSON.stringify(...)`
   (element presence, exact heading text, parent id, **last child of the card**, `offsetParent`,
   rect width/height, legend/meta text) and cross-check numbers against the real source of truth
   (`fleet/state.json`, `collector.py` output) — never just "something rendered".
6. Screenshot proof: `Page.captureScreenshot(format="png", clip={x,y,width,height,scale})` around the
   element rect (call `window.scrollTo(0,0)` first, clip is page-relative). Read the PNG back with
   PIL only if that interpreter has it — otherwise the DOM/SVG assertions carry the evidence.
7. `proc.kill()` in a `finally:`.

## Gotchas that cost time
- `makeDonut(box, slices, size, thick)` builds **`<circle>` elements with `stroke-dasharray`**, not
  paths: assert `circles` count (1 track `#0a1120` + one per slice), `stroke` colour and the
  dasharray, e.g. a 100% single slice = `"361.28 0.00"`.
- Slices accept `{v, color, title, cursor, cls, onclick}`; `title` wires `showTip`/`moveTip`/`hideTip`
  for free. Shared helpers already global: `$(sel)`, `esc(s)`, `showTip`, `moveTip`, `hideTip`,
  `makeDonut`, `centerText`.
- Modules are `const NAME=(function(){…})()` declared after `renderAll()`; adding `NAME.render()`
  to `renderAll` is safe (TDZ only matters at call time, which is post-load).
- Any element rendered while its section is hidden measures 0 — `centerText` falls back to 150 and
  the label re-fits only on the next render. Wire a `[data-v="<id>"]` click hook to re-render.
- Bump `sw.js` `CACHE` (`infra-dash-vNN`) whenever `index.html` changes, otherwise the PWA keeps
  serving the previously precached copy — a stale page looks like a broken deploy.
- Verify the served bytes too: `curl -s http://127.0.0.1:8765/ | grep -c <new-marker>` and
  `curl -s .../sw.js | grep -o "infra-dash-v[0-9]*"`.
- Patch script files with the `patch` tool, not inline `python3 - <<PY` heredocs (they fail with
  "here-document delimited by end-of-file" in this shell).

## fleet block (tail of the Memory card) — proven 2026-09-10
- Rework 2026-09-10: the fleet console has **no tab**. Its details are the **LAST block of
  `#mmCard`** (pie `#fleetPie` + table `#fleetRows` + meta `#fleetPieMeta`), the main page `<h1>` is
  `Az. private infra Dashboard`, and `data-v="fleet"` / `id="fleetSec"` must **not** exist. The
  console keeps the name *fleet* (ids, `/fleet.json`, script id `fleetTab`, block label).
- Gate: `bash /home/ubuntu/clients/invertio/gate/fleet_check.sh` (→ `fleet/check_tab.py`, 11 checks,
  skips when the service is stopped). Full CDP QA lives in the repo:
  `python3 infra-dashboard/verify/qa_fleet_block.py` → 15 checks + clipped screenshot
  `/tmp/fleetpie_card.png`.
- **Deep link `#fleet`**: navigate with `Tab.nav(url + "#fleet")`. The click hook runs **on load**,
  so assigning `location.hash` *after* load does nothing — the view stays `hidden`, every rect is
  0×0 and it looks exactly like a failed render.
- Hidden-view trap: only assert `wrap.offsetParent !== null` after the Memory view is open;
  donut sizes are 0×0 while the section is `display:none` (the SVG still exists → "segments drawn"
  can pass while "sized 130px" fails).
- Row counting: the table's header cell text has no spaces (`taskstatusdurexittokenscharsnote`), so
  filter it explicitly instead of a `/^task\s/` regex.
- Public layout: `/fleet.json` returns `{ok:false, private:true}` on the public host and
  `FLEETPIE.draw()` hides `#fleetPieWrap` for that payload — keep it that way.
- After editing `wire_dashboard.py`, run `python3 fleet/wire_dashboard.py --check` (5 checks) — the
  injected script is duplicated between that file and `index.html`, so both copies must move together.
