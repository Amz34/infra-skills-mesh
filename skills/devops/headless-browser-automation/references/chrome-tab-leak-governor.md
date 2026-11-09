# Chrome tab leak governor (automation Chrome, CDP :9333)

Use when: `INFRA SENTINEL reaped N leaked chrome renderer(s)`, Chrome RSS creeping to GBs on the
automation VM, or you are about to "fix" a browser memory problem by killing processes.

## The trap (cost hours if you get it wrong)
Renderer-process count is **not** the leak signal. Chrome coalesces same-site tabs into one renderer,
so killing a renderer also destroys every tab sharing it, while tabs whose renderer sits under the cap
survive forever. Observed 2026-09-12: **37 CDP page targets, only 7 renderers** — repeated renderer
reaps every ~30 min (30->13, 22->15, 10->7) never fixed it.

Actual root cause: browser sessions open a NEW tab per task and nothing closes them. The 37 targets
were duplicates (8x one client URL, 3x one login page, 14x two `file://` previews).

## The fix that is deployed
- **Tab governor** `~/ops/scripts/chrome_tab_guard.py`, user timer `chrome-tab-guard.timer` (10 min,
  linger=yes). Rules: protected keep-list / `devtools://`; exact-duplicate URL → keep one; close
  `file:///tmp/*`, `about:blank`, `chrome://newtab`; when over `SOFT_CAP=14`, close longest-idle tabs
  whose URL was unchanged for `IDLE_RUNS=6` runs (~1h); `browser_harness.daemon` >10h with no live
  socket → SIGTERM. Silent when there is nothing to do.
- **cgroup caps** on `chrome-automation.service` (`MemoryHigh=1.8G`, `MemoryMax=3.0G`, `TasksMax=300`,
  `OOMPolicy=stop`) so a runaway is recycled inside its own cgroup, never taking the VM down.
- **infra-sentinel demoted to backstop**: `CHROME_IDLE_H=12h`, `CHROME_CAP=22`,
  `CHROME_FOOTPRINT_GB=2.4` (cgroup footprint — was `CHROME_RSS_GB=2.8`, a ps-RSS number, see below).

Result: 37 → 12 tabs, renderers 10 → 1, Chrome footprint 1.3GB → 150MB, sentinel "0 alerts / 0 actions".

## Never measure Chrome memory with a `ps` RSS sum (2026-09-12, cost a false alert)
Every Chromium renderer maps the same zygote/code/heap pages, so summing `ps -o rss` **counts shared
memory once per process**. Measured that day: ps sum = **2367MB**, real footprint across the chrome
cgroups = **749MB** (3.2x inflation). That crossed the watchdog's 1800MB gate and fired
"⚠️ VM PRESSURE ALERT — triggered: chrome" on a perfectly healthy browser.

Use the shared lib (single source of truth for all ops scripts):
```bash
. /home/ubuntu/ops/scripts/lib/cgroup_mem.sh     # bash
chrome_cgroup_mb ; chrome_renderer_count ; disk_swap_used_mb ; zram_swap_used_mb ; mem_available_mb
```
It sums `systemctl --user show <unit> -p MemoryCurrent` over every unit matching `chrome`
(cgroupfs fallback if the user manager is unreachable). Python side: `infra_sentinel.chrome_usage()`
/ `disk_swap_mb()`. `ps` is still fine for *counting* renderers and for ranking top-RSS offenders —
just never sum RSS as a memory claim. Corollary: after a fix that pages memory back in, top-RSS rows
grow with no leak, so a growth gate must ignore RSS rise offset by a swap drop
(`resource_watchdog.sh` does: alerts only when `swap_freed < 0.6 * top5_growth`).

## Stale DISK swap is the residue a heavy render leaves behind
A 2400x2400 Chrome screenshot render pushed ~3.2GB into the disk swap tiers; it sat there for a day
(every later page-in paid disk I/O, and the swap% metric stopped meaning anything). zram re-fill is
by design (zram-tuned swappiness) — **only disk swap is waste**. Reclaim it, guarded:
```bash
DRY_RUN=1 bash ~/ops/scripts/swap_reclaim.sh    # plan
bash ~/ops/scripts/swap_reclaim.sh              # act (needs root: script uses sudo -n)
```
Guards: refuses to start under 3GB MemAvailable, skips any tier whose reclaim would leave <1.5GB,
smallest-used tier first, re-arms each tier empty right after. `infra-sentinel` runs it automatically
when disk swap ≥1GB **and** MemAvailable ≥4GB; RAM-short boxes are deliberately left alone.

## Orphaned automation chrome (check before blaming the governor)
An abandoned automation flow can leave a whole Chrome instance attached to the VNC desktop profile:
```bash
systemctl --user list-units --all --no-legend | grep -i chrome   # scopes: app-com.google.Chrome-<pid>, hermes-worker-*.scope
ps -eo pid,etimes,args | grep chrome-vnc                         # dead localhost OAuth callback => orphan
systemctl --user stop app-com.google.Chrome-<pid>.scope hermes-worker-proc_<id>.scope
```
2026-09-12: a 47h-old `chrome-vnc` window still pointed at `http://127.0.0.1:53682/auth?...` whose
callback server was long gone — 135MB + 2h57m CPU. `chrome_reaper.sh` deliberately excludes the
chrome-vnc profile from reaping, so these need a manual scope stop.

## Operate
```bash
systemctl --user status chrome-tab-guard.timer
python3 ~/ops/scripts/chrome_tab_guard.py --dry-run --verbose   # what it would close
tail -5 ~/ops/observability/chrome-tab-guard.jsonl              # trail of real closes
echo "dash.cloudflare.com" >> ~/ops/chrome_tab_guard_keep.txt   # pin a long-lived tab
systemctl --user disable --now chrome-tab-guard.timer           # kill switch (leak returns in hours)
```

## Mechanics you will need
- Enumerate: `curl -s http://127.0.0.1:9333/json/list` (fields `id`, `url`, `type`).
- Close a tab: `curl -s "http://127.0.0.1:9333/json/close/<targetId>"` — this Chrome build returns
  **HTTP 200 with an empty body**, so the response is NOT a success signal. Verify by re-listing and
  checking the target id is gone (the guard reports `ok` that way).
- Create a tab (smoke test): `curl -s -X PUT "http://127.0.0.1:9333/json/new?about:blank"`.
- **Do NOT use `Target.getTargets`' `attached` flag as an "in use, don't close" signal in this stack**:
  browser-harness connects with `Target.setAutoAttach`, so every target reports `attached=true` and the
  guard would protect all of them (it defaults to ignoring that flag for this reason).

## Design rules if you extend it
- Close only provably redundant tabs immediately (duplicate URL, throwaway preview). Everything else
  waits for a documented idle streak, so a paused task does not lose page state.
- Keep it silent on no-op runs — it runs 144x/day.
- Tabs are throwaway: the harness re-opens on next use, so the guard is safe to keep enabled.
