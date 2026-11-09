# Changing a prod file on the dashboard box — staging-first, approval-gated

Use when the item touches a prod file (`server.py`, `collector.py`, `web/index.html`,
unit files). This is Aamir's private monitoring dashboard: a botched restart means
he cannot see his own infra.

## Hard rules

- **UI change → copy-preview** (`make_preview.py` pattern); **backend change →
  staged copy server**. Never edit prod to demo, not even "temporarily".
- **Diff first, approval second.** Aamir's stated flow: *"prod change → pehle diff
  dikhaunga, approval ke baad"*. Present: what changes / staging evidence / exact
  apply steps / rollback plan → ask GO. Choosing the work item is not the same as
  approving the deploy.
- Save the diff + the patched file outside the repo (`~/ops/patches/<file>-<date>.diff`)
  so the change survives an approval delay.
- Never leave a half-applied state: the apply script restores the backup on ANY
  failure (`templates/apply-with-rollback.sh`).

## Step 1 — stage the candidate as a copy

The repo has **no git**; `backups/<file>.<label>-<ts>` is the version convention.

```bash
PROD=/home/ubuntu/clients/invertio/infra-dashboard; ST=/tmp/dash-staging
rm -rf $ST; mkdir -p $ST
cp /tmp/server_new.py $ST/server.py
ln -s $PROD/status.db $ST/status.db
ln -s $PROD/web       $ST/web
cd $ST && DASH_PORT=8768 /usr/bin/python3 server.py      # run as a background process
```

- `BASE = dirname(server.py)`, so the staged copy writes its own scratch files
  (caches, `access.log`, …) into `/tmp/dash-staging` — prod dir stays clean.
- Pick a **free** port first: `ss -tlnp | grep -E ':(876[0-9]|8799)'` —
  **8766 is already taken by `~/crashproof/server.py`**, 8799 is the OpenUI spike proxy.
- **Always export `DASH_PORT`.** Omit it and the staged copy tries to bind prod's
  8765 and dies with `OSError: [Errno 98] Address already in use`. Harmless, but it
  costs a round-trip and looks like a crash.
- Compile with the **prod interpreter**: the unit runs `/usr/bin/python3` (3.12),
  while the workspace `python3` is uv's 3.11. `python3 -m py_compile` from the shell
  may be testing the wrong one.
- Kill the staged copy **by port**, not by name:
  `pid=$(ss -tlnp | grep ':8768' | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2); kill $pid`.
  `pkill -f 'dash-staging/server.py'` never matches — the cmdline is just
  `/usr/bin/python3 server.py`.

## Step 2 — parity is the proof of "zero behaviour change"

Same request set against staging and prod:

- **Page bytes**: `sha256sum` of `curl -s -H "Host: <host>" http://127.0.0.1:<port>/`
  for the private host *and* the public host → must be byte-identical.
- **JSON endpoints**: compare **key sets**, not values (`/data.json` carries
  `now`/`updated_age_s`, so bodies drift) for `/data.json`, `/history.json`, `/fleet.json`.
- **Response headers** for `/data.json` (Content-Type/Length) identical.
- **Non-regression on odd input**: static 404, traversal `/../etc/passwd`,
  `HEAD`/`POST` → same status as prod (`501` for HEAD/POST is pre-existing
  `BaseHTTPRequestHandler` behaviour, not your bug).

## Step 3 — gate baseline BEFORE the change

```bash
DASH_URL=http://127.0.0.1:8765 /usr/bin/python3 verify/drive.py   # pre-change
```

Expect `PASS: 58 rows rendered for 58 reported services` + evidence files in
`verify/evidence/`. Run it pre-change so a post-change failure is *attributable*,
and post-change as the acceptance gate (the apply script does this and rolls back
on non-zero). `verify/drive.py` takes `DASH_URL`, which is what makes it usable
against a staged port.

## Step 4 — prove the NEW behaviour, don't assume it

The sweep that was actually run for the access log (each line caught or confirmed
something real):

- **Real client IP behind a proxy**: `-H 'X-Forwarded-For: 10.9.9.9'` → the record
  must carry `ip: 10.9.9.9` (plus ua / referer / ms). `X-Forwarded-For` first hop
  wins; else `client_address[0]`.
- **Concurrency**: `seq 40 | xargs -P 40 -I{} curl -s -o /dev/null http://127.0.0.1:<p>/…`
  → line count matches, `json.loads` on **every** line = 0 malformed (append is
  lock-guarded; `ThreadingHTTPServer` makes this the real risk).
- **Rotation**: `head -c 6000000 /dev/urandom | base64 >> access.log`, then one
  request → `.1` created, active log restarts. Keep a bounded footprint
  (5 MB × 2 rotations ≈ 15 MB max).
- **Bad input**: `?hours=abc|-5|99999`, `?limit=0|-3|abc` → 200, no traceback in
  the server log.
- **Private-only endpoints**: on the public Host they must answer
  `{"ok":false,"private":true}` with HTTP **200** (that is the `/fleet.json`
  convention — not 403), and must add nothing to the public layout.
- **Self-noise**: the log-viewing endpoint (`/access.json`) must NOT append to
  `access.log`, or "who viewed" analysis is polluted by your own checks.

## Step 5 — the staged access log (SHIPPED 2026-09-13, approved "Go")

Why it exists: the repo had **zero request attribution** — during the OpenUI
preview, nobody could tell whether a real person ever loaded the link (only
cloudflared's aggregate 240 requests, all self-generated).

Design staged + verified: JSONL record per request
`{ts, iso(+%z), ip, xff, host, method, path, status, bytes, ms, ua, ref}` written
from a `try/finally` in `do_GET` (`_send` records status/bytes); 5 MB rotation to
`.1`/`.2`; `/access.json` = private-only summary (last 200 entries + `by_ip` /
`by_path` counts) and excluded from its own log; logger never raises into the
request path. Patch: `~/ops/patches/infra-dash-accesslog-20260913.diff`
(**+118 / 3 changed** lines — pure addition; the 3 changed lines are the
`host` variable being computed once; page bytes proved identical).

### Outcome (2026-09-13) — applied to prod, gate green

Flow that worked, end to end: stage copy → prove parity → show diff → **user "Go"** →
`bash /tmp/apply_accesslog.sh` (backup → install → `py_compile` with `/usr/bin/python3` →
`sudo -n systemctl restart infra-dash.service` → endpoint parity → **`verify/drive.py` gate** →
auto-rollback on any failure). Result: reinstalled prod `server.py` md5 == staged
`da2c421158cf0b2ae0b3a1ada4c51e20`; `/ /data.json /history.json /fleet.json /access.json` all 200;
public Host `{"ok":false,"private":true}`; **gate PASS 58 rows / 58 services** (evidence
`verify/evidence/2026-09-13-health-tiles.{dom.html,png}`); prod `access.log` = 22 lines, 0 malformed,
exact 12-key schema; `X-Forwarded-For: 203.0.113.77` logged as `ip`; `/access.json` did not log itself;
`web/index.html` + `collector.py` mtimes still 2026-09-10 (UI/collector untouched).

First apply attempt failed **for the wrong reason** — see the `SYSCTL` gotcha in
`templates/apply-with-rollback.sh`: the unit is **system-scope**, `systemctl --user restart` →
*"Unit not found"* → `rollback()` fired, restored the old file, and prod kept serving 200. The script's
rollback is what makes that class of mistake harmless; always re-check `md5sum` of the installed file
instead of trusting "rollback + 200" as either success or failure.

Query it like: `curl -s http://127.0.0.1:8765/access.json | python3 -m json.tool` (private host only) —
`entries` (last 200), `by_ip`, `by_path`, `count`, `first`, `last`.
