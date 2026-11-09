# Freshness + SQLite lock debugging (case: "not reflecting on my infra", 2026-09-15)

Escalating user report: *"Its not reflecting on my infra?"* / *"1. continue karke fully implement karo"* for a
new dashboard section. The frontend was fine; **three backend/infra faults and one SW fault** produced the
symptom. Chronological evidence and the exact commands.

## Symptom set
- New section rendered in an isolated test page but stayed empty on the live dashboard.
- `/data.json` sometimes answered, sometimes appeared to hang (`http=000` after 60 s / 90 s).
- `hasData:false` in the page → `state.data` never populated → renderers had nothing to draw.

## Root causes (in the order they were found)
1. **`status.db` in rollback-journal mode** (`PRAGMA journal_mode` → `delete`).
   `server.py`'s `build_data()` reads 5,857 snapshot rows with `json_extract` (~20 s per build) and holds a
   SHARED lock the whole time. The collector's write/commit then failed with
   `sqlite3.OperationalError: database is locked` **every ~2 min tick** → new snapshots stopped (frozen at
   10:28) → `/data.json` builds contended and took 18.8 s cold / 22.4 s warm (or appeared to hang).
2. **Memory starvation**: `infra-dash.service` had `MemoryMax=400M` (1 G earlier) on a box with ~5 G
   available. Same builder: **4.2 s standalone vs 20 s in-service** — that ratio is the tell.
3. **Service worker stale shell**: cache-first `/` plus a `respondWith` fallback meant the browser kept
   rendering the old HTML/JS; a non-settling handler hangs the request with no network entry.
4. **Hidden-tab render**: the section lived in a tab whose container was `display:none`, so the renderer's
   host-width measurement produced nothing until the tab was revealed — needed an explicit tab-show hook.

## Fix commands (exact)
```bash
cd ~/clients/invertio/infra-dashboard

# 0. who holds the DB? (a hot -journal file blocks every writer)
ls -la status.db*            # no -wal / -journal expected on a clean file
sudo fuser -v status.db      # named holders; here: only server.py (the reader)

# 1. WAL — the mode switch is refused while another connection is open, so STOP first
sudo systemctl stop infra-dash.service
python3 -c "import sqlite3;c=sqlite3.connect('status.db',timeout=30);print('before',c.execute('PRAGMA journal_mode').fetchone());print('after',c.execute('PRAGMA journal_mode=WAL').fetchone())"

# 2. stop starving the builder
sudo systemctl set-property infra-dash.service MemoryMax=1.5G

# 3. bring prod back, then fire one collector tick
sudo systemctl start infra-dash.service
sudo systemctl start infra-dash-collector.service
systemctl is-active infra-dash-collector.service      # want: active → then inactive=Finished (no lock error)

# 4. prove freshness + speed
curl -s -m 150 -o /tmp/d.json -w 'cold code=%{http_code} t=%{time_total} bytes=%{size_download}\n' http://localhost:8765/data.json
curl -s -m 60 -o /dev/null -w 'warm code=%{http_code} t=%{time_total}\n' http://localhost:8765/data.json
python3 -c "import json;d=json.load(open('/tmp/d.json'));print(d['iso'],d['ok'],len(d.get('groups') or []))"
```
Observed after the fix: `cold 2.20 s / warm 0.003 s`, `iso` seconds old, `ok:true`, 11 groups,
31 agent-run edges. Feature gate `python3 verify/drive.py` → exit 0, *"PASS: 59 rows rendered for 59
reported services; evidence written and kept"*, `data_age_s=55` (was hours).

## Diagnostic ladder (cheap → expensive)
| Check | Command | Reads as |
|---|---|---|
| Server serves new markup? | `curl -s <url> > /tmp/tl.html; grep -c '<marker>' /tmp/tl.html` | 0 ⇒ deploy/cache, not data |
| Per-endpoint timing | `curl -s -m 20 -o /dev/null -w 'code=%{http_code} t=%{time_total}\n' http://localhost:8765/<path>` | slow/hang ⇒ server side |
| Collector healthy? | `journalctl -u infra-dash-collector.service -n 20 --no-pager` | `database is locked` ⇒ WAL/keychain |
| DB mode + holders | `PRAGMA journal_mode`, `sudo fuser -v status.db`, `ls -la status.db*` | `delete` + reader holders ⇒ fix #1 |
| Starvation | `systemctl show infra-dash.service -p MemoryMax -p MemoryCurrent` | cap ≈ current ⇒ fix #2 |
| Data age | payload `iso` / `updated_age_s` | hours ⇒ collector dead, UI innocent |
| SW design | `grep -c 'fetch' web/sw.js` | >0 ⇒ stale-shell class bug |

## Service-worker pattern that ended the class of bug
`sw.js` with **no fetch handler**: on `install` → purge every existing cache + `skipWaiting()`; on `activate`
→ delete caches + `clients.claim()`; plus an unregister of any legacy registration. HTML therefore always
comes from the network. Pair it with:
- `<meta name="dash-build" content="vN">` and a header badge that compares badge-vs-served value;
- a **hard-refresh button** (`navigator.serviceWorker.getRegistrations()` → unregister, `caches.keys()` →
  delete, `location.reload(true)`);
- auto-reload when a background fetch shows a newer build than the loaded one.
Static assets still need `?v=N` bumps — the HTTP cache is a separate layer from the SW.

## Related trap: probe-induced CPU saturation
Leftover headless-Chrome tabs from QA keep the 20 s `/data.json` poll running. 36 established connections
were observed, with the box (2 vCPU) at load ~5, which looked exactly like "the dashboard server hangs".
Always end a QA script by closing its tabs (`Target.closeTarget` / `curl http://127.0.0.1:9334/json/close/<id>`),
and re-measure timings on a quiet box before reporting a server fault.
