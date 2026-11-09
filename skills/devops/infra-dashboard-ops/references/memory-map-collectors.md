# Memory map collectors — ROM (disk) + RAM (live) recipes

Shipped 2026-09-08 in `collector.py` (functions `rom_map()`, `collect_ram(ts)`, helpers `_du_rows`, `_du_one_mb`, `_human_mb`, `_ram_conn`) + `web/index.html` MM module. server.py untouched (host dict is pass-through). All snippets below are the VERIFIED working forms.

## Payload shapes (as served in host.*)

```
rom_map = { asof, fs_total_mb, fs_free_mb, home_mb,          # du root row of ~/ (one pass)
  dirs:    [{n, mb, sub?:[{n,mb}…]}…],   # top ~12 of `du -xk -d1 /home/ubuntu`; children only for big dirs (.hermes, ops, uocr, .local, projects, clients)
  conns:   [{n, mb, sub?:[{n,mb}…]}…],   # Hermes · default (core) + Hermes · <profile> per .hermes/profiles/* ; profile sub = its top dirs
  skills:  {total_mb, rows:[{n,mb}…]},   # core skills, archive dir, per-profile skills — computed FIRST (core_mb needs the total)
  files:   [{n, mb}…],                   # find /home/ubuntu -xdev -type f -size +50M, top ~12
  docker:  [{n, mb}…] }                  # docker image ls --format '{{.Repository}}:{{.Tag}}\t{{.Size}}'
ram_map = { asof, total_mb, used_mb, avail_mb, cache_mb, swap_total_mb, swap_used_mb,  # /proc/meminfo
  conns:  [{n, mb, procs}…],   # host processes only (container procs excluded — no double count)
  procs:  [{pid, n, mb, conn, cmd}…],    # top ~15 by RSS, >=1MB
  docker: [{n, mb, procs}…] }            # docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}'
```

## Verified parsing snippets

```python
# ps: columns are space-padded -> split(None, N) or regex \s+
for ln in run_cmd(["ps", "-eo", "pid,comm,rss,args", "--no-headers"], timeout=20).splitlines():
    p = ln.strip().split(None, 3)
    if len(p) < 4: continue
    pid, comm, rss, args = int(p[0]), p[1], int(p[2]), p[3]

# du subtree scan: NO -s flag (conflicts with --max-depth); root row = subtree total
def _du_rows(d, maxdepth=1, timeout=120, xdev=True):
    cmd = ["du", "-k", "--max-depth=%d" % maxdepth] + (["-x"] if xdev else []) + [d]
    out = run_cmd(cmd, timeout=timeout)
    rows = []
    for ln in out.splitlines():
        t = ln.split("\t", 1)
        if len(t) != 2: continue
        try: kb = int(t[0].strip())
        except: continue
        p = t[1].strip()
        if not p or p == d: continue      # capture root row separately if you want the total
        rows.append({"n": p, "mb": max(1, round(kb / 1024))})
    rows.sort(key=lambda r: -r["mb"]); return rows

# human sizes: uppercase kills the 'i' in MiB -> IGNORECASE pattern
def _human_mb(s):
    s = s.strip().split("/", 1)[0].strip()
    try: return max(1, int(s) // 1048576)         # bare bytes
    except: pass
    m = re.match(r"([\d.]+)\s*([KMGT]?i?B)", s.upper(), re.IGNORECASE)
    if not m: return 0
    mult = {"B": 1, "KB": 1024, "MB": 1048576, "GB": 1073741824}.get(m.group(2).replace("I", ""), 1)
    return max(1, round(float(m.group(1)) * mult / 1048576))

# container attribution: /proc/<pid>/cgroup -> docker id -> name (run BEFORE generic rules)
dnames = {}
for ln in run_cmd(["docker", "ps", "--format", "{{.ID}}\\t{{.Names}}"], timeout=15).splitlines():
    t = ln.split("\t", 1)
    if len(t) == 2: dnames[t[0]] = t[1]
...
with open("/proc/%d/cgroup" % pid) as cf: cgc = cf.read()   # world-readable
mm = re.search(r"docker[-/]([0-9a-f]{12,64})", cgc)
dk = dnames.get(mm.group(1)) or mm.group(1)[:12]            # prefix fallback
```

## Connection classifier (ordered rules)

1. `chrome`/`chrome_crashpad` comms by user-data-dir: `browser-use/chrome-signal` → "Chrome · invertio (browser-use)"; `google-chrome-headless/scoped_dir` → "Chrome · invertio (headless 9223)"; `user-data-dir=…profiles/<p>/` → "Chrome · p"; `.config/google-chrome` LAST → "Chrome · desktop (X11)" (headless path contains that string!).
2. `hermes_cli.main` in args → `--profile <p>` ? "Hermes · p" : "Hermes · default". `hermes-agent/hermes serve` → default webui.
3. `whatsapp-bridge` or `profiles/whatsapp` → "Hermes · whatsapp (bridge)".
4. infra-dashboard / n8n / omniroute / ollama args → their own buckets.
5. docker engine comms → "Docker engine"; kernel threads (`[` args) → skip.
6. `cloudflared` → "cloudflared tunnels"; `signal-cli*` → "Signal CLI (Hermes default)"; `.caveman`/`browser_harness` → "Hermes tooling".
7. Project one-offs: `/projects/<seg>/` in args → "project · <seg>"; `clients/invertio/` → "invertio scripts" (kills the mega-"Other" bucket).
8. Fallback OS-services comm list (sshd, postfix, cron, chronyd, fail2ban…) then "Other".
Rule order is load-bearing — docker/cgroup first in collect_ram, chrome before desktop, hermes before project paths.

## Cache pattern (hourly heavy scans)

```python
ROM_CACHE = "/tmp/.invertio_rom_map.json"   # separate file from SP cache, same TTL
if os.path.exists(ROM_CACHE) and time.time() - os.path.getmtime(ROM_CACHE) < SP_TTL:
    data = json.load(open(ROM_CACHE))
    if data.get("home_mb"): return data
```
Write the cache only after a FULL successful build; if a sub-scan fails keep partials (worse case = next tick retries). Measured: full cold collector run 18.3s; collect_ram alone ~2.4s/tick. Both SP and ROM caches share TTL so they rebuild the same hour → that one tick is the heaviest; systemd drop-in `TimeoutStartSec=300` (one-shot default is 90s and WILL kill a cold 2-3 min tick). Test cold timing yourself: `rm -f /tmp/.invertio_rom_map.json && time python3 collector.py`.

## MM UI conventions (index.html)

- Card HTML + scoped `.mm*` <style> inserted after `<div id="panels"></div>` (bottom of tiles view, before `</div><!-- /tilesSec -->`).
- `const MM = (function(){…})()` with `MM.render()` added to `renderAll()`'s call list (MM declared after renderAll is fine — renderAll only runs post-parse). Tab state `var tab`, delegated click on `#mmBody`: rows with `.has-sub` toggle `.open` (CSS shows `.mmsub`); children are ALWAYS in the DOM (hidden), so row counts don't change on expand.
- Rows: `flex-wrap:wrap` on `.mmrow` so `.mmsub{flex:1 1 100%}` wraps to its own line; bar width = mb/section-max (min 1.5-2% so tiny rows stay visible); section-scale differs per list — never use a global scale or small rows vanish.
- RAM tab reuses the same rowHTML for conns (children = `procs` filtered by conn, top ~6) and docker; "usage bar" = stacked segments (used % → color: >85 down, >70 warn, else up; then cache, then track).
- Tab buttons reuse class `.am` for look-alike styling BUT `#apiMode .am` CSS is scoped — copy the styles under your own id selector.
- Data is already in the payload on every poll — no extra fetch, expand is pure CSS/DOM.

## Verification checklist (what proved it end-to-end)

1. `python3 -m py_compile collector.py`; extract inline scripts (`<script>(.*?)</script>` blocks, count may be >1) → `node --check`.
2. Standalone collector tests: `python3 - <<PY` calling `rom_map()`/`collect_ram(ts)` directly; assert dirs/files totals against the static audit artifacts (`~/ops/space-audit-2026-09-08.json`) — exact cross-check of du values.
3. Manual full run `time python3 collector.py` → writes snapshot with new keys NOW (timer is 2-min; without this, browser QA falsely reports missing fields).
4. `curl -s http://127.0.0.1:8765/data.json` AND the tailnet URL — confirm `rom_map`/`ram_map` present in host (proves pass-through, no server restart).
5. `grep -c` the tailnet page HTML for the new card markup + `curl …/sw.js | grep CACHE=` = new version.
6. Browser DOM QA: assert row counts per section, click an expandable row, switch tab, assert no errbox text. Screenshots → `/home/ubuntu/ops/qa-mm-<date>/` and attach via MEDIA:.
