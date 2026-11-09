# Agent-run layer: task→designation resolver + live arrow org map

Deployed 2026-09-15 into `/home/ubuntu/clients/invertio/infra-dashboard` (private `Az. private infra Dashboard`, port 8765, `infra-dash.service`).

## What it answers
"Which agent/designation is being run for this task, right now?" — every live cron job and interactive agent
session on the box is mapped to one of the 24 roster designations (D1–D24) and shown two ways:

| Tab | Purpose |
|-----|---------|
| **Agent runs** | Task → designation resolver (type any task, get owning designation + its live runs) + flat run table |
| **Agent map** | Interactive SVG-arrowed org chart: tiers as bands, 31 topology links, click a node for detail, "live only" toggle |

## Files (all inside the dashboard repo)
- `agentruns.py` — read-only collector module. Sources: `~/.hermes/cron/jobs.json`, `~/.hermes/profiles/*/cron/jobs.json`,
  `~/.hermes/cron/executions.db`, `~/.hermes/state.db` + profile DBs, `~/ops/observability/autonomy.json`,
  `~/ops/verify/verify-ledger.jsonl`. Emits `agentruns` key into the snapshot.
- `agent-roles.json` — roster: `roles[]` (`d, role, tier, level, cost, plane, new, kw[]`) + top-level `edges[]`
  (`{a, b, k}` with `k ∈ cmd|deleg|gate|call|verify|new`; `a:"BUILD"` = hub anchor under the build tier).
- `collector.py` — 2 lines: `from agentruns import collect_agentruns` + `"agentruns": collect_agentruns(ts)` in the snapshot dict.
- `server.py` — 1 line passthrough `"agentruns": snap.get("agentruns")`.
- `web/index.html` — `#mapSec` (map) and `#runsSec` (resolver) sections, `ARGMAP`/`RUNS` modules, `VIEWS` list, `PL.setView` toggles.

## Data contract (payload `agentruns`)
`ok, ts, iso, roster_n, roster_version, roles[{d,role,tier,level,cost,plane,new,kw("a|b|c")}], runs[{task,src,d,role,level,cost,model,sched,state,status,ago,age_s,live}], live[], counts{tasks,jobs,jobs_on,sessions,mapped,cover_pct,live,roles_used,runs_24h,ok_24h,fail_24h,by_level,top_roles}, map{d→{live,tasks,jobs,fail,last,last_age,model,top[]}}, edges[], gov{}, errors[]`.

## Hard-won pitfalls
1. **Any `web/index.html` edit needs a `web/sw.js` CACHE bump** (`infra-dash-vNN`), else the service worker keeps serving the stale page and your change "doesn't work".
2. **Never lay out arrows while the section is hidden** — rects are 0×0, the SVG `viewBox` collapses to `0 0 1 1`, and with `preserveAspectRatio="none"` every path/arrowhead is scaled up into giant triangles all over the page. Guard with `if(!cr.width||!cr.height){svg.innerHTML="";return;}` and redraw on a `MutationObserver` over `#mapSec` class + resize + tab click.
3. **No SVG `<marker>` arrowheads** — draw explicit polygons; markerUnits vs scaled viewBox is a trap.
4. Top-level helpers in this page are `$` and `esc` (line ~584). `qs()` exists **only inside the `PL` module** — using it at top level throws `qs is not defined` and silently kills the whole script (no console error visible via CDP Runtime events).
5. Keep the snapshot payload lean: `/history.json`, `/diff.json` and startup re-parse **every** stored snapshot, so payload growth multiplies CPU 14 days deep. `agentruns` ≈ 26 KB (runs capped 30, sessions dropped, `kw` pipe-joined string → JS splits on `"|"`).
6. **Cache-thrash looks like a leak**: `/data.json` rebuild ≈ 1.3–2 s CPU and `DATA_CACHE_S = 10`. Many dashboard tabs open (my QA opened 7) → sustained 50–90 % CPU. Check `access.log` request rate + per-thread `/proc/<pid>/task/*/stat` before blaming a spin. `strace -f -c -p <pid>` showing only `ppoll` means the main thread is idle — the cost is in request handling.
7. **Test instances**: never start a second `server.py` for A/B tests without tracking its PID (`DASH_PORT=8799 ...`); one stray instance will keep the old DB cached and confuse port checks. `pgrep -f "DASH_PORT=8799"` inside a shell command also matches *your own* command line — use explicit PIDs.
8. `curl -X PUT` is required for CDP `/json/new?url=` (Chrome ≥ 111); GET returns no JSON.

## QA harness (reusable)
CDP on `127.0.0.1:9333` (chrome-automation.service, Xvfb :99):
- open target → `Emulation.setDeviceMetricsOverride(1560×1420)` → click `[data-v="map"]` (do **not** rely only on `#map` hash) → wait → assert visible section.
- Programmatic overlap audit: pairwise `getBoundingClientRect()` intersection over `.armnode`, `.maptier`, `.armkpi`, `.armchip` + `scrollWidth>clientWidth` clipping check + document horizontal overflow + "tiny node" check (width<120 px = labels will truncate).
- Then `Page.captureScreenshot` + `vision_analyze` on the PNG (full frame + one zoom crop).
- Close every target you opened (`Page.close` + `/json/close/<id>`) — leftover tabs keep polling and burn CPU.

## Verified state (2026-09-15)
24 nodes / 5 tier captions / 31 topology links / 7 KPI chips, zero overlapping pairs, zero clipped text, no horizontal overflow;
node widths ≥ 156 px (build 189 px, new band 254 px); server CPU ≈ 0 % with one dashboard tab open; `verify/drive.py` PASS (58 rows) and `gate/fleet_check.sh` exit 0.
