---
name: infra-dashboard-ops
description: Use when working on private infra dashboard (hermes-vnic).
version: 1.0.0
author: hermes
license: MIT
metadata:
  hermes:
    tags: [dashboard, monitoring, collector, sqlite, sw-js, qa]
    related_skills: [hermes-token-cost-ops, canvas-dashboard-iteration]
---

# Infra Dashboard Ops (hermes-vnic / invertio infra-dashboard)

Aamir's private live-monitoring dashboard: local `http://127.0.0.1:8765/`, public `https://hermes-vnic.tail34b7f2.ts.net/` (Tailscale funnel). Project: `/home/ubuntu/clients/invertio/infra-dashboard/`.

## Architecture (pipeline)

```
collector.py  --(every ~2 min, systemd)-->  status.db (snapshots table, one JSON row per tick)
server.py     --(reads latest snapshot, /data.json + /history.json, ~10s cache)-->  HTTP :8765
web/index.html --(polls /data.json every 20s; re-renders when payload ts changes)-->  UI cards
web/sw.js     --(service worker; freshness-first: **NO fetch handler** since v48, always network — the cache-first stale-shell class of bug is gone; see "Stale page" section)
```

- `collector.py` = data brain. Pulls host/group stats + DeepSeek balance + Hermes usage DBs, writes snapshot payload JSON into `status.db` (SQLite, table `snapshots(ts, payload)`). Run manually: `python3 collector.py`.
- `server.py` = thin JSON builder. **Top-level payload keys are a FIXED list** — a new top-level field needs `"key": snap.get("key")` + **`sudo systemctl restart infra-dash.service`** (old code stays in memory otherwise). **BUT the `host` dict is passed through wholesale**: new `host.*` sub-fields (rom_map, ram_map, storage_pie…) appear in /data.json with ZERO server change and no restart.
- `web/index.html` = single-file UI + inline JS (no build step). Every visible card has an HTML block + a `draw*()` function; the refresh loop calls `renderAll()`, which calls each drawer in order — new panels hook in there.
- Frontend idioms to reuse: `makeDonut(svgEl, segs, centerText)` for pie/donut (segments `{v, color, title}`), CSS vars `--dim/--faint`, card grid rows. Provider color map + `apiColor()` prefix-palette live in the API-usage card JS.

## Add-a-live-panel workflow

1. **Collector**: write `collect_x()` returning a dict; include it in the snapshot payload dict. Use **read-only SQLite URI** (`file:...?mode=ro`, short timeout) for any query against live Hermes DBs — the gateway writes every turn and must never be locked.
2. **Server**: add passthrough line + `sudo systemctl restart infra-dash.service`; verify with `curl -s http://127.0.0.1:8765/data.json`.
3. **Frontend**: HTML card + `drawX()` + hook into `renderAll()`.
4. **Freshness**: `sw.js` has had **no fetch handler since v48** (see "Stale page / 'reflect nahi ho raha'" below), so `index.html` itself needs no cache version bump any more. But every **separate asset file** (`agentic-map.js`, extra `.css`) is still subject to the browser HTTP cache — bump its query string in `index.html` (`agentic-map.js?v=N` → `N+1`) whenever that module changes, else QA and real users keep running the OLD module while the HTML looks fresh. Also bump `<meta name="dash-build" content="vN">` (the header build badge + the auto-reload check compare it).
5. **Run `python3 collector.py` once manually** after code changes — the timer only fires every 2 min, and until it does, status.db holds an OLD-format snapshot and browser QA will report your new fields missing. (Classic false "bug".)
6. Verify snapshot: `sqlite3 status.db "SELECT payload FROM snapshots ORDER BY ts DESC LIMIT 1"` and check the new key.

## Live health probe (`/data.json`) — "prod theek hai?" in one pass

Use this instead of reading source when the question is "is the dashboard/box healthy right now?":

1. `systemctl is-active infra-dash.service`; the collector is a **system** one-shot timer —
   `systemctl list-timers --all | grep infra` (expect every ~2 min) and
   `journalctl -u infra-dash-collector.service -n 6 --no-pager` for the per-tick `snapshot … ok` line.
   (Note: `systemctl --user is-active infra-dash.service` reports **inactive** — prod runs at system scope.)
2. Freshness = `status.db` **mtime** vs now, plus the payload's own `updated_age_s` (observed ~35s).
3. `curl -s http://127.0.0.1:8765/data.json` → top-level keys are the fixed list
   `api, avail, eco, fixes, groups, host, iso, now, ok, ts, updated_age_s`.
4. Anything not-up = walk **`groups[].items[]`** and read **`st`**. An item is
   `{k, label, st, ms, detail, nomon}`; services live inside groups ("Web services", "Docker containers",
   "systemd services", "Public sites (external)", …), not in a flat `services` array.

A healthy box reads e.g. `58 items, 57 up, 0 down, 1 warn` (the standing warn is the agent memory store).
Probe script + teardown checklist: `references/live-health-probe.md`.

## Prod-change protocol (backend files) — stage, prove parity, then ask

Any item touching `server.py` / `collector.py` / unit files: **stage a copy, prove
zero behaviour change, present the diff, apply only on GO** (Aamir's flow:
*"prod change → pehle diff dikhaunga, approval ke baad"*).

1. Stage: copy the candidate to `/tmp/dash-staging/server.py`, symlink prod
   `status.db` + `web/` next to it, run on a **free** port with `DASH_PORT` set
   (8766 = crashproof, 8799 = OpenUI spike proxy). `BASE = dirname(server.py)`, so
   the copy's scratch files land in /tmp — prod dir untouched.
2. Parity proof: `sha256sum` of `/` on private + public Host (byte-identical),
   **key sets** (not values) for `/data.json`, `/history.json`, `/fleet.json`,
   same status for 404/traversal/HEAD/POST.
3. **Gate baseline BEFORE the change** (`DASH_URL=… verify/drive.py` → PASS 58/58),
   so a post-change failure is attributable; the apply script re-runs it as the
   acceptance gate.
4. Sweep the NEW behaviour (proxy `X-Forwarded-For` capture, 40-way parallel
   appends → 0 malformed lines, rotation, bad query params, private-only endpoint
   answering `{"ok":false,"private":true}`).
5. Apply = `templates/apply-with-rollback.sh` (backup → install → compile with the
   prod interpreter → restart → parity → gate → **auto-rollback on any failure**).
   Restart with **`sudo -n systemctl restart infra-dash.service`** — prod runs at
   SYSTEM scope (`/etc/systemd/system/infra-dash.service`, `User=ubuntu`), so
   `systemctl --user restart` aborts with *"Unit infra-dash.service not found"* → the
   script calls `rollback` on a false failure. `sudo -n` works (passwordless) on this VM.

**Shipped 2026-09-13 (approved):** the access-log landed in prod `server.py` —
`+118 / changed 3` lines, add-only. Backup `backups/server.py.accesslog-<ts>`; patch kept at
`~/ops/patches/infra-dash-accesslog-20260913.diff`; post-change gate **PASS 58 rows / 58 services**
(`verify/evidence/2026-09-13-health-tiles.*`). Verified after apply: prod `server.py` md5 = staged md5
(`da2c421158cf0b2ae0b3a1ada4c51e20`), `/`, `/data.json`, `/history.json`, `/fleet.json`, `/access.json`
all 200, public Host still answers `{"ok":false,"private":true}`, prod `access.log` 22 lines /
0 malformed / exact 12-key schema, `X-Forwarded-For: 203.0.113.77` captured as `ip`, `/access.json`
does **not** log itself, service `active`+`enabled`. Live even the UI/page bytes: unchanged
(`web/index.html` + `collector.py` still mtime 2026-09-10 → prod UI untouched).

Full recipes incl. the staged access-log design: `references/prod-server-change-protocol.md`.

## QA loop (evidence-based, per Aamir's engineer spec)

Never say "ho gaya" — prove it:

1. `python3 -m py_compile collector.py server.py`.
2. JS syntax: extract the inline script (`python3 -c` with `re.search(r"<script>(.*?)</script>", html, re.S)`) → `/tmp/inline.js` → `node --check`. Fuzzy patches can duplicate/leave braces — always check after HTML/JS patches.
3. **Deterministic data proof on DB copies**: live Hermes DBs drift between your collector run and your ground-truth query (gateway bills a call every turn — cents appear mid-QA). Copy DBs to /tmp, run both aggregation paths against the SAME copies, compare exactly (respect rounding: collector `round(x,4)` vs raw SUM → tolerance ~1e-4, not 1e-9).
4. Browser DOM assertions via `browser_exec` (cache-bust URL `/?fresh=<ts>`): `document.querySelector('#...').innerText` / shapes count; after a sw.js bump, purge first: `navigator.serviceWorker.getRegistrations().then(rs=>rs.forEach(r=>r.unregister()))` + `caches.keys().then(ks=>ks.forEach(k=>caches.delete(k)))` then reload.
5. Evidence: screenshot → `cp ~/.config/browser-harness/tmp/shot.png <project>/qa_<feature>.png`, attach via `MEDIA:` path. Final report: what changed, per-bug evidence, files touched, user action needed (e.g. hard refresh for new SW).

## ROM+RAM memory map (interactive listing, shipped 2026-09-08)

"Storage & memory map" card = bottom of tiles view, two tabs. Click any row with children to expand (no page reload, data already in payload).

- **ROM · disk tab** (data `host.rom_map`, rebuilt hourly — separate cache file `/tmp/.invertio_rom_map.json`, TTL 3600 like SP; full cold collector run measured 18s): `{fs_total_mb, fs_free_mb, home_mb, dirs:[{n,mb,sub?}] (top ~12 ~/ dirs, big ones expandable), conns:[{n,mb,sub?}] (Hermes default/core + each profile), skills:{total_mb, rows:[{n,mb}]} (core + archive + per-profile), files:[{n,mb}] (find >50MB, top ~12), docker:[{n,mb}] (image list)}`. du rows are dirs only — big files inside a dir (e.g. profile `state.db`) appear in `files`, not in that dir's sub rows.
- **RAM · live tab** (data `host.ram_map`, every tick ~2.4s): `{total/used/avail/cache/swap mb from /proc/meminfo, conns:[{n,mb,procs}] (host processes aggregated by connection), procs:[{pid,n,mb,conn,cmd}] (top ~15), docker:[{n,mb,procs}] (docker stats cgroup usage)}`. Container processes (via cgroup) are labelled "Docker · <name>" in procs but **excluded from conns aggregation** — docker stats rows are the cgroup truth, conns must stay host-only or you double-count.
- UI = `MM` IIFE module: `MM.render()` hooked into `renderAll()`; expandable rows are `div.mmrow` + hidden `.mmsub` toggled by delegated click on `#mmBody`; tab buttons reuse class `.am` BUT `#apiMode .am` CSS is scoped to that card — the memory-map tabs carry their own `<style>` block in the card HTML (prefixed `.mm*` classes).
- **Bars over pie** (deliberate): pie is readable only for 2-6 slices; these listings have 12-40 rows with long paths — sorted horizontal bars (width ∝ share of section max) + expand-on-click + `title` attr for full path give exact values without label collisions. Keep donuts only for summary cards.
- server.py: untouched (host passthrough). sw.js bump still required for the HTML change.

## Fleet console placement (reworked 2026-09-10 — **no tab**)

Aamir's ruling: the fleet **screen** was "out of context" ("woh out of context screen hai"), so the
console is **not a tab**. Its details are the **LAST block of the Memory card** on the main page, and
the main-page `<h1>` is `Az. private infra Dashboard`.

- Markup: `#fleetPieWrap` (heading `fleet · parallel agent children` + `#fleetPie` donut +
  `#fleetPieMeta` + `#fleetRows`) sits immediately after `<div id="mmBody"></div>`, inside `#mmCard`.
  `FLEETPIE` (plain page code) draws the donut; `fleet/wire_dashboard.py` injects the detail table as
  `<script id="fleetTab">` (private host only).
- Must **not** exist: `data-v="fleet"`, `#fleetSec`, a "Fleet" nav button. Deep link `#fleet` opens
  the **Memory** view. Keep the name *fleet* for the console (ids, `/fleet.json`, script id, label).
- Public host: `/fleet.json` = `{ok:false, private:true}` and `FLEETPIE.draw()` hides
  `#fleetPieWrap` — private-only UI must never add pixels to the public layout.
- Gates: `bash gate/fleet_check.sh` (→ **`fleet/check_tab.py`**, 11 checks) and
  `python3 verify/qa_fleet_block.py` (15 CDP checks + clipped screenshot of the block). Keep
  `verify/drive.py` and `python3 fleet/wire_dashboard.py --check` in the same pass.

## Stale page / "reflect nahi ho raha" playbook

Aamir's recurring complaint: *"maine deploy kiya, par mere infra pe reflect nahi ho raha"*. Four independent
layers can each produce that symptom — check them **in this order** (server → data → SW → render), never
start by re-editing the frontend.

1. **Is the SERVER serving the new markup?** `curl -s https://hermes-vnic.tail34b7f2.ts.net/ > /tmp/tl.html`
   then `grep -c '<marker>' /tmp/tl.html` (e.g. `amSec`, `buildtag`, `agentic-map.js?v=N`). 200 + markers
   present ⇒ browser/cache problem, not deploy. (Public tailnet host serves `index_public.html` by design —
   private-only sections are ABSENT there; test the private URL when in doubt.)
2. **Is the DATA fresh?** Read `iso` / `updated_age_s` in `/data.json`. Hours-old `iso` = the collector has
   been failing, and every "empty section / blank card" on the page is innocent.
   `journalctl -u infra-dash-collector.service -n 20 --no-pager` → `sqlite3.OperationalError: database is
   locked` means the lock chain in (2b).
   2b. **status.db lock chain (root cause found 2026-09-15).** `status.db` was in **rollback-journal** mode
   (`PRAGMA journal_mode` → `delete`): server.py's `build_data()` runs long read queries over 5,857 rows with
   `json_extract` (~20 s) and each held a SHARED lock, so the collector's write+commit got `database is
   locked` **every 2 min** → snapshots frozen (10:28) → `/data.json` took 19–60 s or hung → page never
   populated. Also: `/data.json` building in ~20 s in-service vs 4.2 s standalone = memory starvation.
   Fix (both, in this order):
   - `sudo systemctl stop infra-dash.service` → `python3 -c "import sqlite3;c=sqlite3.connect('status.db',timeout=30);print(c.execute('PRAGMA journal_mode=WAL').fetchone())"` → restart.
     **WAL is persistent and is the actual fix** (readers no longer block the writer). The mode switch itself
     is refused while any other connection holds the DB, so the service must be STOPPED first.
   - `sudo systemctl set-property infra-dash.service MemoryMax=1.5G` — the old 400 M cap (on a box with ~5 G
     free) made builds 5× slower and starved the requests.
   - Result to expect: collector tick `Finished` (no lock error), `iso` seconds old, `/data.json` **cold 2.2 s /
     warm 0.003 s** (0.003 s = the 10 s in-process cache hit).
   - If a `status.db-journal` file lingers, a crashed writer left a hot journal → every writer blocks until
     recovery; check `ls -la status.db*` and `sudo fuser -v status.db` for the actual holder.
   2c. **Missing index on `snapshots(ts)` (root cause found 2026-09-16 — the big one).** `/data.json` =
      latest snapshot **+ 24 h and 7 d availability per check**, and `availability()` scans
      `SELECT ts,payload FROM snapshots WHERE ts >= ?` **twice per request**. The table had **no index on
      `ts`** (only `sqlite_autoindex_billed_days_1` existed), so every request did two FULL SCANS of a
      **234 MB / 6.7 k-row** table (avg payload 39 KB, 194 MB of JSON parsed in Python). Measured on this
      VM: **117.6 s** first byte, with MemoryMax reverted to 512 M.
      - Diagnose: `sqlite3 status.db "select name from sqlite_master where type='index'"` (expect
        `idx_snapshots_ts`), `systemctl show -p MemoryMax infra-dash.service` (512 M = starved; want 1.5 G),
        and the size: `ls -la status.db` / `select count(*),avg(length(payload)) from snapshots`.
      - Fix: `CREATE INDEX IF NOT EXISTS idx_snapshots_ts ON snapshots(ts)` (instant, non-destructive —
        NOT a VACUUM/REINDEX) + `sudo systemctl set-property infra-dash.service MemoryMax=1536M` +
        restart. Result 2026-09-16: **cold 3.1–3.6 s, warm 0.002 s**, collector snapshots fresh.
      - MemoryMax persistence: verify the drop-in really exists —
        `/etc/systemd/system.control/infra-dash.service.d/50-MemoryMax.conf`. A `set-property` run with
        `--runtime` (or a later revert) silently leaves the unit back at 512 M. `MemoryHigh` lives in its
        own `50-MemoryHigh.conf`.
      - Focus-mode caveat: after `~/ops/focus-firewatch/disable-projects.sh`, the dashboard reports
        `service: invertio-agent-pipeline` **down** (it is one of `SYSTEMD_UNITS` in collector.py) plus the
        ad-hoc probes 3001/4173 (no owning unit — dev servers, unfixable by design). Resume the dashboard
        scope with `~/ops/focus-firewatch/dashboard-resume.sh`; full revert with `restore-all.sh`.
3. **Is the SW serving a stale shell?** `web/sw.js` must have **no `fetch` handler at all** (v48+): it only
   `skipWaiting()`s, purges every cache on activate, and unregisters leftovers. A `fetch` handler with a
   fallback (`caches.match(req).then(r => r || caches.match('/'))`) serves the OLD page forever, and if the
   promise never settles the request hangs with **no network entry and no console error** — invisible in
   devtools. Recovery recipe for a client stuck on the old SW: unregister + delete caches + reload.
4. **Is the section inside a HIDDEN tab?** A renderer that measures its host width does nothing (or renders
   0-width) while the tab is `display:none`. Every new tab-hosted section needs a **tab-show hook**
   (click handler + `IntersectionObserver`/`MutationObserver` on the section class) that re-renders on
   reveal, not just on the 20 s data poll.
5. Belt-and-braces for the user: header **build badge** (`<meta name="dash-build">` vs the served value) +
   a **hard-refresh button** (unregister SW + delete caches + reload) + auto-reload when the fetched build
   differs. Long-lived nginx-style caches on the user's side then self-heal without support ping-pong.

**QA-probe hygiene**: every browser QA script must CLOSE the tabs it opened (`Target.closeTarget`, or
`curl http://127.0.0.1:9334/json/close/<id>`). Leaked probe tabs keep the 20 s `/data.json` poll alive —
36 established connections were measured at once, saturating 2 vCPU and masquerading as "the server hangs".
Per-endpoint timing that shows slow/hanging responses therefore must be confirmed on a quiet box before you
believe it.

Deep transcript + exact commands/numbers: `references/freshness-and-lock-debugging.md`.

## Service control plane — star / stop / remove (shipped 2026-09-16)

Full playbook (guards, semantics, row-layout traps, QA/parity suites, registry hook):
`references/service-control-plane.md`. Reminder: any new mutating surface must be declared
in `~/ops/observability/autonomy.json → surfaces` before it ships.

`web/services-control.js?v=2` + `controls.py` + `GET /services.json` +
`POST /svc/action`. Nav item sits beside Agent map, deep link `#svc`, default
filter = Active (the "active list" Aamir asked for).

Hard rules when touching it:

- **private hosts only** — the public `Host` (`aslove7…`) gets an empty stub. The
  section is deliberately absent from `index_public.html`; never add it there.
- guards live in BOTH `server.py` (Host / `X-Dash-Control` header / origin) and
  `controls.py` (unit-name regex, unit-must-exist, protected list, confirm flag,
  kill switch). Never relax one side because "the UI hides the button".
- protected = `PROTECTED` regexes + `~/.config/infra-dash/protected.txt` +
  `critical_services` in `~/ops/observability/autonomy.json`. New critical units go
  in the registry first, then the code picks them up.
- `remove` = `disable --now` (docker: `--restart=no` + stop) → reversible; **never**
  delete a unit file from the UI or CLI. Static units (no `[Install]) cannot be
  disabled: controls.py reports "stopped; nothing to disable (unit is static)"
  rather than claiming success.
- every accepted action appends `~/.config/infra-dash/control-audit.jsonl`; kill
  switch `~/.config/infra-dash/control-enabled` (absent ⇒ `armed:false`, read-only).
- asset edits: bump `?v=N` on the JS **and** `meta name=dash-build` (this feature =
  v51) — both are cached.
- deep links only work for ids present in `const VIEWS=[...]`; a new view must be
  added there or `#svc` silently opens Panels (this is the bug QA caught).

Verify after any change: `python3 verify/svc_qa.py` (21 checks, exit 0),
`python3 verify/parity_services.py` (12 checks — old endpoints key/byte-stable,
public stub intact), `python3 verify/drive.py` (59/59 PASS gate).

## One-glance registry — projects, websites, schedules, services (2026-09-16)

Whole-infra register in one view. Data comes from `registry.py` (not the read-only
panels feed) and merges curated knowledge with live probes:

- `registry.py` -> `registry.json`: 90 projects (28 curated `SEED` + workspace
  dirs), 10 websites HTTP-probed (8 live), 269 services, 120 declared schedules
  + **35 systemd timers (all, ours + OS)**, 5 MCP servers, autonomy policy
  findings from `~/ops/scripts/autonomy_audit.py --json`.
- Each `SEED` entry has a `match` substring list; units/crons/dirs are linked
  automatically by matching it, so adding a project is a one-line edit.
- `GET /registry.json` = private hosts only (public host gets an empty stub,
  same guard as /fleet.json).
- UI: nav **One glance** (`data-v="glance"`, deep link `#glance`), tabs
  projects | websites | schedules | services | safety, search + refresh.
  Renderer `web/glance-core.js` is pure `(root, data)`; `web/glance.js` only
  fetches/refreshes. Also add the view to `setView()` in index.html — the
  view switcher is explicit, not generic.
- Keep new CSS scoped `#glanceSec` and never reuse global class names (`.chip`,
  `.mono`): the dashboard's own rules leak in and pills overlap the table.
- Standalone artifact: `python3 verify/one_glance.py` -> `web/one-glance.html`
  (single file, embedded snapshot, offline-safe, refresh when served) +
  `verify/evidence/one-glance-<date>.html`. Root element id must be `glanceSec`
  or the scoped CSS does not apply.
- Crash-proofing: `remove` = stop + disable; protected units (100, from
  `autonomy.json critical_services`) and **crash-prone** units get no delete
  button, and controls.py refuses them. Crash-prone = SubState=auto-restart,
  or Result=start-limit-hit, or NRestarts>=5 while failed. Never flag oneshot
  `exited` units as crash-prone.
- Crash-proof drop-ins: `[Unit] StartLimitIntervalSec=0` (never give up) for
  always-on units, bounded StartLimitIntervalSec/Burst for broken ones.
- QA: `verify/registry_qa.py` (46) + `svc_qa.py` (21) +
  `parity_services.py` (12) + `drive.py` gate. Bump `dash-build` in index.html
  AND the tag asserted in parity_services.py on every asset edit.
- Long-line hazard: write patches/scripts with <90-char lines — the harness
  truncates long tool arguments and can write `...[truncated]` into the file.
  After every file write, read it back before trusting it.
- **Health semantics (cost a false "down" row):** `401/403` from a site probe
  means UP (auth-gated), only `0`/`>=400`-other degrades; oneshot/wave units
  (`inactive` + `Result in ("","success")`) are not load-bearing — exclude them
  from `long_running` or backup/wave timers flip healthy projects to down.
  `p["units"]` must project `long_running`/`unit_type` or `u.get(...)` is None
  and every project reads 0/N.
- **Registry edits are not live until restart:** `server.py` caches the built
  registry in memory, so `GET /registry.json` keeps serving the OLD build after
  `registry.py` changes (stale chips in screenshots → looks like the fix
  failed). `sudo -n systemctl restart infra-dash.service`, re-curl, check
  `Counter(p['health'])`.
- **User-scope units need the user bus env:** pass
  `env={"XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}"}` to every
  `systemctl --user` call, else the unit looks absent and crash detection
  silently misses it (munder-app was missed exactly this way).
- Full detail (data model, code snippets, renderer traps, QA list):
  `references/one-glance-registry.md`.

## Speed fix — "page slow, loading much time" (2026-09-18)

> Class-level write-up of this same fix (root-cause theory, generic fix shapes, proof
> protocol, triage script): skill `saas-performance-diagnosis`, Step 0.8 +
> `references/self-hosted-app-cache-stampede.md`. Use that when the complaint is *any*
> self-hosted app, this section when it is this dashboard.

Symptom: access.log showed `/data.json` **11–419 s**, `/history.json` 131 s,
`/services.json` 181 s; service pinned at MemoryHigh (RSS 972 MB, 26% CPU), 75 sockets on
:8765 held by the server process itself.

Root causes (measured, in impact order):
1. **No single-flight lock** — every poll that missed the 10 s cache ran a *full* rebuild in
   parallel: `db_rows_since(0)` returned the entire 332 MB `snapshots` table and
   `availability()` json.loads'd ~500 MB per build. N tabs = N parallel rebuilds → GIL + RSS
   storm → 400 s latencies.
2. Availability/history parsed 40 KB payloads instead of compact status rows.
3. `RETENTION_DAYS = 14` while the widest window is 7 d.
4. `registry.build()` (~7 s: external URL probes run sequentially, 8 s timeout each) ran on
   the request path behind only a 120 s TTL.

Fix (reversible, zero client impact):
- `server.py`: `_build_locks` + double-checked locking for /data.json, /history.json,
  /diff.json, /peaks.json, /services.json; `_svc_cache` (20 s); background `_warm_thread`
  (90 s) calling `registry.build()` + `controls.list_services()` so no user request pays it.
- `collector.py`: writes compact `item_states(ts, k, st, PRIMARY KEY(ts,k))` every tick —
  same skip rules as `flatten()` (skip `nomon`, skip empty `k`); payload retention 8 d +
  `ITEMS_RETENTION_DAYS = 8`.
- `server.py` read path: `items_since()` + `avail_from_items()` and **fallback to the payload
  scan when the table is absent** → pre-fix databases keep working.
- `registry.py`: `build()` = cache check + `_BUILD_LOCK` + `_assemble()` (body unchanged);
  probes fanned out via `ThreadPoolExecutor(6)` with a 4 s timeout.
- One-off compaction: `VACUUM INTO /tmp/status_compact.db` (read-only on the source), swap the
  file during the restart, keep `status.db.prev` as instant rollback, and checkpoint/remove
  `status.db-wal`/`-shm` before swapping.
- Backfill existing history once: parse every payload into item rows — kept in the repo as
  `tools/backfill_items.py` (idempotent, safe to re-run).

Measured after: `/data.json` **0.002 s** (cold 0.45 s), `/registry.json` 0.003 s,
`/services.json` 0.001 s warm (1.16 s cold), `/history.json` 0.08 s, `/diff.json` 0.001 s,
index 0.002 s; **RSS 972 → 58 MB**, CPU 5%, sockets 0.

Never-skip proofs: cross-check API `avail` == items path == payload path for every key
(`python3 tools/avail_crosscheck.py` → 0 mismatch), gate `python3 verify/drive.py` exit 0
(59 rows rendered + evidence), and re-check
public redaction (`eco`, `fixes`, `api.billed` stripped when Host contains `aslove7`).
Pitfalls: server/registry edits are dead until `sudo systemctl restart infra-dash.service`;
keep item-state skip rules identical to `flatten()` or availability silently drifts; very long
inline one-liners in this repo get truncated — write a script file and read its output.

## Pitfalls (all hit in real sessions)

- **All-time-window $0 bug**: time-window cutoff as `0` computes `now - 0 = now` → matches only future rows → empty. Use a `None` sentinel meaning "no cutoff", not 0.
- **Sub-cent noise**: slices < $0.01 render as "$0.00" legend rows — skip them in slice lists (keep them in totals). Threshold 0.01 USD, not 0.001.
- **Provider label aliases**: provider keys from DBs are not display labels (`gemini` → "Gemini (Google)", `zai`, `custom` = local/free-proxy). Keep a `PROV_LABEL` map; unknown keys fall into "Other".
- **model vs provider mismatch rows**: same model id can appear under several billing providers (fallback reroutes, free proxy routes). Group by model across all DBs for true per-model spend.
- **Data sources**: 5 DBs — `~/.hermes/state.db` + `~/.hermes/profiles/*/state.db` (invertio, whatsapp, ...). Per-session rows, live-written every gateway turn. See `references/usage-cost-sources.md` for schema + SQL + balance API details.
- **`ps -o` columns are space-PADDED**: naive `line.split(" ", N)` silently skips most rows (was 380/386). Use `line.split(None, 3)` (or `re.split(r"\s+", line, 3)`) on `ps -eo pid,comm,rss,args`.
- **`du -s` conflicts with `--max-depth`** (`du: warning: summarizing conflicts with --max-depth=1`): scan subdirs with bare `du -xk --max-depth=N <dir>` (no `-s`); rows come back `KB\tpath` — `split("\t",1)`. The scanned root itself appears as a row (use it as the subtree total — no second `du -sk` pass needed).
- **Human-size parser vs MiB**: `s.upper()` turns "66.3MiB" into "66.3MIB", so `([KMGT]?B)` never matches — parse with `re.match(r"([\d.]+)\s*([KMGT]?i?B)", s.upper(), re.IGNORECASE)`. Docker stats MemUsage = `"81.21MiB / 11.65GiB"` (split on `/`); docker image `.Size` is already human (e.g. "1.2GB").
- **Container RAM attribution**: process args don't say which container they're in. Read `/proc/<pid>/cgroup`, regex `docker[-/]([0-9a-f]{12,64})`, map id→name with one `docker ps --format '{{.ID}}\t{{.Names}}'` call. Do this BEFORE generic classifier rules.
- **Classifier rule ORDER matters** (chrome): check `browser-use/chrome-signal` → `google-chrome-headless/scoped_dir` → generic `user-data-dir=...profiles/<p>/` → `.config/google-chrome` last — the headless path CONTAINS the string ".config/google-chrome", so the desktop rule must never run first. Chrome trees are keyed by user-data-dir, and crashpad-handler processes carry `--user-data-dir` too.
- **Hermes process labelling** (gateways/profiles): args contain `-m hermes_cli.main` with optional `--profile <p>` (no flag = default). Path rules: `profiles/<p>/` in args → "Hermes · p" (bridges/cron children); `hermes-agent/hermes serve` → default webui; `.caveman`/`browser_harness` → Hermes tooling. Project one-offs under `~/projects/<name>/` → bucket `"project · <name>"` (avoids a giant "Other").
- **Cold hourly tick can exceed systemd one-shot 90s**: storage_breakdown + rom_map both rebuild on the same hour boundary (same TTL). Drop-in `/etc/systemd/system/infra-dash-collector.service.d/override.conf` sets `TimeoutStartSec=300`. Time a cold run yourself (`time python3 collector.py` after `rm -f /tmp/.invertio_rom_map.json`) before assuming tick length.
- **Long multi-branch regex in search_files returns "? matches"** on this host — for exact anchors use `grep -nE` via terminal + solo small `read_file` chunks (batched parallel reads get collapsed in the transcript; solo reads return full content).
- **A staged copy silently targets prod's port if you forget `DASH_PORT`** → `OSError: [Errno 98] Address already in use`, which reads like a crash but is just the default 8765. Check free ports first (`8766` = `~/crashproof/server.py`, `8799` = OpenUI spike proxy). And kill the staged copy **by port** (`ss -tlnp | grep ':8768'` → `pid=`), never `pkill -f 'dash-staging/server.py'` — the cmdline is only `/usr/bin/python3 server.py`, so the pattern matches nothing and you end up testing stale code. Compile with the **prod** interpreter too: the unit runs `/usr/bin/python3` (3.12), while the workspace `python3` is uv's 3.11.
- **Long chained shell one-liners come back elided**: a big `{ echo …; grep …; cat … }` block can return just `exit 0, 1 lines output`, and an over-long command string can arrive mangled mid-word. Keep terminal commands short, and when you must read the body: `cmd > /tmp/out.txt 2>&1` then `read_file /tmp/out.txt` (same for any tool output too big to trust). **Inline `python3 -c "…"` inside such a command is worse than elided — it lies**: a line-by-line JSON validator run that way reported `lines 42 malformed 42` (every line "bad") and another run returned empty output; the same code as a `write_file`d `/tmp/chk.py` returned `42 lines, 0 malformed`. Write the checker to a file and run that.
- **Restart only what changed**: collector code needs no service restart (next tick picks it up; or run manually), server.py changes need `infra-dash.service` restart — **`sudo -n systemctl restart infra-dash.service`** (system unit; `systemctl --user restart` says *"Unit not found"* and a rollback-guarded script reads that as a failed deploy — it rolled prod back to the old file and still served 200, i.e. a silent no-op that looks like a failure).
- **Access log = prod `access.log` (JSONL), query via `/access.json`**: one line per request
  `{ts, iso, ip, xff, host, method, path, status, bytes, ms, ua, ref}`, rotation 5 MB → `.1` → `.2`,
  override dir with `DASH_ACCESS_LOG`. `ip` honours `X-Forwarded-For` (so the real client survives
  Caddy/Tailscale), `/access.json` is **private-host-only** (public → `{"ok":false,"private":true}`)
  and excludes itself from the log. This exists because the OpenUI preview's 240 requests were
  unattributable — never diagnose traffic on this dashboard without it.
- **A moved/hidden UI element is not done until every text site moves**: sweep `index.html`, the
  `collector.py` card text, `server.py`, `verify/features/*.md` (+ its row in that dir's README),
  `gate/*.sh` step labels, `gate/*.md`, `fleet/README.md`, `fleet/runner.py` strings and `sw.js`
  comments for the old wording, then re-grep for the old name and run the gates. Checklist:
  `references/ui-relocation-sweep.md`.
- **Gates live with their subject, not with the dashboard**: the fleet placement gate is
  `clients/invertio/fleet/check_tab.py` (invoked by `gate/fleet_check.sh`). A copy written under
  `infra-dashboard/fleet/` is dead code — write it where the runner actually looks.
- **`ss -ltn | grep ":8765 "` probes give false SKIP** inside chained subshells: the gate then
  prints `SKIP: dashboard not running`, exits 0, and looks green. `gate/fleet_check.sh` now uses a
  `/dev/tcp` connect probe with 5 retries — if any gate prints SKIP but `curl` answers, re-run
  before believing it.
- **Storage card is generic; granular breakdown = Memory map card**: the storage-split donut shows filesystem totals only. Per-file/skill/connection (ROM) + RAM live breakdown lives in the **Memory map** card at the bottom of the tiles view — `host.rom_map` (hourly-cached du/find scan) + `host.ram_map` (per-tick ps/cgroup/docker scan). See "ROM+RAM memory map" section below + `references/memory-map-collectors.md`. The static one-off audit artifacts `~/ops/space-audit-2026-09-08.{json,md}` predate it; `vm-disk-cleanup` has the filesystem-audit side.
- **A health probe on the wrong key silently reports ALL-CLEAR**: `/data.json` items carry `st` — there is
  no `status`, no `level`, no `ok` per item. A probe written against those keys finds nothing, prints
  `0 down`, and you tell Aamir "sab theek" while an item is `warn`. Dump the shape first
  (`json.dumps(groups[0], ensure_ascii=False)[:400]`) or read `key`+`st` per item; a group's checks also
  live under `items`, not `checks` (`.get("checks") or []` → silent empty list).
- **Adoption close-out is part of the deliverable**: after a spike/preview, "measured X" is not an answer —
  state what goes into prod NOW, what does NOT, and what event would reopen it. From the OpenUI spike:
  panel layer **not** into prod (ARM generation ~193 s/panel with no GPU, OUI-1 model absent, and it adds a
  generated-text→UI path to a private dashboard that already shows 58 live checks for no gain); the two
  cheap independent wins that survived were **request logging at the origin server** (attribution, which
  this repo lacks) and a written **tunnel-hygiene rule** (private dashboard never on a naked quick tunnel;
  share a copy-preview). Full verdict + revisit triggers: `references/live-health-probe.md`.
- **No-build pages preview by COPY, never by edit**: when a change to `web/index.html` needs Aamir's approval before prod, build a *copy* (`make_preview.py` pattern) that reads the original read-only and injects the new layer, serve it from a scratch server, comment out the SW registration, and prove prod is untouched with `stat -c '%n  %y'` on `web/index.html`/`server.py`/`collector.py`/`infra-dash.service`. Never patch prod "temporarily" to demo.
- **Recorded numbers must stay regenerable**: if you append evidence to a generated report from outside its generator, the reproducibility check (regenerate → compare) fails the moment someone re-runs the generator. Put the section inside the generator (`report.py` reading `out/preview-measure.json`), not in a helper script that writes the same file.

## One-glance register: bots, memory/RAG, stacks, gaps, watchers (2026-09-16)

`registry_ext.py` (imported inside `registry.build()`) adds the "everything else" sections. After any change run `python3 verify/run_qa.py` and read the outcome in the register's Watch tab (ledger `verify/qa-ledger.jsonl`).

- **Bots & channels** — `collect_bots()` reads env files for token *names*, then calls Telegram `getMe` / Discord `@me` for live identity. Never print or store the values. Real result: 3 bots (Zma1_bot, Invertio1bot, Amz/discord) + 8 channels, of which whatsapp/webhook/teams have no credential (report as *info*, not warn).
- **Memory census** — `collect_memory()`: MEMORY.md/USER.md per profile with byte counts, knowledge trees (files + bytes), stores (state.db size/sessions/messages, kanban, evidence, backups) and ChromaDB collections with vector counts via `sqlite3` on `~/ai-stack/chroma/chroma.sqlite3` (join `embeddings`→`segments`→`collections`).
- **Self-audit gaps** — `collect_gaps(data)` emits `{id, sev, area, finding, fix}`; the `fix` field is a runnable command, which is what makes the tab actionable. Severity rules that mattered: a channel with no credential is *info*; a profile gateway that is inactive with **no bot** is *info* (archived profile); one-shot units are never "no restart policy".
- **Timers on the host** — `collect_units` lists services only (`--type=service`), so a `CORE_UNITS` entry ending in `.timer` must be resolved from `systemctl list-timers` + `is-enabled`; otherwise every timer reports "missing".
- **Watchers** — `collect_watchers()` keyword-filters every Hermes cron (watch/guard/monitor/backup/drill/audit/health/qa/maintenance), matching systemd timers, plus curated external layers (CF Worker `hermes-watch`, UptimeRobot, `svc-watch.py`). Paused watchers surface as info gaps with their cron id instead of being silently resumed.
- **Pitfalls** — pane functions are hoisted inside the render function, so a global find/replace on a *call* like `servicesPane(x)` can rewrite the *definition* too (symptom: `ReferenceError: X is not defined`, blank body, and `node --check` still passes because the file is valid). Grep `function <name>` after every bulk edit. Wrap the pane dispatch in `safe(fn, arg)` so one broken pane cannot blank the artifact.
- **Per-tab evidence without CDP** — `one-glance.html` honours `#tab` (`#watch`, `#gaps`, `#bots`...), so headless Chrome `file://...#<tab>` gives a screenshot per tab.

## Autonomy governance: fix a sentinel violation permanently (2026-09-16)

`~/ops/scripts/autonomy_audit.py` (called by `~/ops/scripts/infra_sentinel.py`) enforces: **L4 + effect not in (internal, notify-owner) is a P1 block** ("autonomous surfaces may not touch third parties"), and **effect in (external, money) needs L0/L1, or L3 + `gate_required: true`**. So a public tunnel/service is declared **L3 + gate_required: true** (+ a `reversal:` line) - that is the honest classification, not a workaround, because the exposure needs owner approval.

Gotchas found while clearing the `firewatch-tunnel` violation:
- `critical_services` must hold **bare unit names** (`ssh`, `infra-dash`), never `ssh.service`: the audit matches live systemd names, so the suffixed form reports *stale* and the dashboard's `is_protected()` silently stops protecting it. Normalise inside `is_protected()` (`^name$`, `^name\.`, `^name-`) so both forms match.
- A declaration with no live surface reports *dead*: either create the surface (e.g. a real `registry-refresh.py` cron named exactly like the declaration) or drop the declaration.
- Verify with `python3 ops/scripts/infra_sentinel.py` - it must print **nothing**; clearing the audit is not enough, the watchdog itself has to fall silent.
- After any registry/controls edit: rebuild (`verify/one_glance.py`), restart `infra-dash`, rerun `verify/run_qa.py` (61 checks), bump the build tag.

## Deliverable style (Aamir)

Independent-engineer loop: implement → artifact + proof → self-QA against ground truth → honest report with evidence files/diffs. Reply concise Hinglish. One-off small fixes: skip the ceremony, keep the proof (verify the endpoint/file, say what changed).

References: `references/usage-cost-sources.md` — Hermes state.db schema/SQL + provider keys + DeepSeek balance API + window semantics. `references/memory-map-collectors.md` — rom_map/ram_map collector recipes: payload shapes, verified parsing snippets (ps/du/human-size/cgroup), connection-classifier rules, cache pattern, MM UI conventions, verification checklist. `references/qa-render-checks.md` — CDP render-QA recipe for any section (live page, not the source file): throwaway headless Chrome, the click-before-assert rule, donut/SVG assertions, deep-link and hidden-view traps, fleet-block invariants. `references/ui-relocation-sweep.md` — every text site to sweep when a card/tab/panel moves or dies. `references/generative-ui-panel-layer.md` — OpenUI Lang panel layer: turn panels from hand-written code into generated data (generate-once/execute-forever, `Query`→`toolProvider` over our endpoints, no-build IIFE vendored locally). **Spike built + measured** in `~/clients/invertio/infra-dashboard/spike-openui/` (runtime on-box, generation off-box, 72.5% token saving on a real panel, 37/37 checks) — prod untouched; includes measured baseline of this UI service, the pitfalls (thundering-herd on `/data.json`, small-model few-shot requirement), the **copy-only pilot preview** (`make_preview.py` → `preview/index.html`; injected tool map, SW disabled, dark palette scoped from the library's own dark block, 21/21 preview checks), the OUI-1 model does-not-run-here finding, and a section on writing this repo's **ad-hoc verifiers** (normalize `1,364`→`1364`, count checks dynamically, assert the artefact's real JSON shape). `references/live-health-probe.md` — copy-paste "is prod healthy?" probe over `/data.json` (exact group/item schema, `st` field), the preview→share→close teardown checklist (530 vs 200 proof, tunnel usage/attribution limits), and the OpenUI rollout verdict (what not to put in prod + revisit triggers). `references/prod-server-change-protocol.md` — staging-first, parity-proven, approval-gated changes to prod backend files: staged copy over symlinked DB/web, sha256 page parity, edge/concurrency/rotation sweeps, gate baseline before + after, apply-with-rollback (`templates/apply-with-rollback.sh`), and the staged access-log design (JSONL fields, 5 MB×2 rotation, private-only `/access.json`, self-noise excluded). `references/live-regression-panel.md` — shipping a live "fixes" panel: probes not prose, the four touch points for a new payload key, gate pitfalls (row-class invariants), honesty rules. `references/freshness-and-lock-debugging.md` — full "reflect nahi ho raha" case: status.db WAL fix (with the stop-before-switch rule), MemoryMax starvation, the no-fetch-handler SW, the cheap→expensive diagnostic ladder, probe-tab CPU trap.
