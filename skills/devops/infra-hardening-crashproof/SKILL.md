---
name: infra-hardening-crashproof
description: Use when hardening a cloud VM end-to-end.
---

# Infra Hardening — Crash-Proof Workflow

Full VM security lockdown in verified order. Har step verify, phir agla — kabhi bhi sab ek saath nahi.

## Order Matters (crash-proof sequence)
1. **Firewall first** (surgical iptables — NOT UFW; UFW flush karta hai Docker iptables rules)
2. **SSH hardening** (key-only, fail2ban)
3. **Malware scan** (rkhunter, chkrootkit, suspicious files)
4. **Backup fix/verify** (sabse pehle data safe karo — taake baad ke changes rollback ho sakein)
5. **Security patches** (apt upgrade)
6. **Reboot prep** (persistence verify) → **post-boot auto-check service** → **reboot**

## Firewall (iptables, Docker-safe)
```bash
# Docker published ports block (DOCKER-USER chain — restart pe Docker khud bana leta hai)
sudo iptables -I DOCKER-USER 1 -p tcp -m multiport --dports 3002,8080,8090 -j DROP -m comment --comment "harden-block-docker-published"
# Risky host ports (external interface only)
sudo iptables -I INPUT 1 -p tcp -i enp0s6 -m multiport --dports 111,7860,8001,8081,8090,8080,3002,20128,8644,8645,8765,8355,11434 -j DROP -m comment --comment "harden-block-risky-ports"
# VCN-internal lateral (10.0.0.0/16)
sudo iptables -I INPUT 2 -p tcp -i enp0s6 -s 10.0.0.0/16 -m multiport --dports 111,7860,8001,8081,8090,8080,3002,20128,8644,8645,8765,8355,11434 -j DROP -m comment --comment "harden-block-vcn-lateral"
```
- Interface naam check: `ip -br addr` (OCI = enp0s6)
- UFW use NAHI karo — Docker iptables rules flush kar deta hai → sites down
- Persist: `sudo apt install iptables-persistent` → rules `/etc/iptables/rules.v4` pe save. **Reboot se pehle HAMESHA `diff iptables-save rules.v4` karo.**

## SSH + Fail2ban
- Key-only: `/etc/ssh/sshd_config.d/99-hardening.conf` → PasswordAuthentication no, PermitRootLogin no, MaxAuthTries 3
- fail2ban jail: `/etc/fail2ban/jail.d/sshd.local` → enabled, maxretry 3, bantime 1h
- Ban check: `sudo fail2ban-client status sshd`
- SSH service restart: `sudo systemctl restart ssh` (Ubuntu = ssh, not sshd)

## Backup — Recursive Tar Pitfall (SABSE IMPORTANT)
**KABHI BHI** backup script me `tar -C ~ ops` mat karo bina exclude ke — `~/ops/backups` khud archive me aata hai → exponential growth (465MB → 949MB → 1.9GB → 3.8GB → 7.5GB → 15GB). Drive quota 15GB pe crash.

```bash
tar czf "$F" -C ~ --exclude='ops/backups' --exclude='ops/logs' ops
```
- Rotation: KEEP_LOCAL=3, KEEP_REMOTE=4 (15GB quota-safe)
- Upload verify: `rclone check --include <name> --size-only gdrive:...` + size match
- Schedule: **systemd timer** (cron se better — Persistent=true = missed runs reboot ke baad catch-up)
  `/etc/systemd/system/sanad-backup.{service,timer}` — Timer: `OnCalendar=*-*-* 02:30:00`, `Persistent=true`
- rclone 401 fix (headless): stored refresh_token se access_token re-exchange karo (refresh_token 2035 tak valid), client_secret config se.

## state.db Corruption (Hermes gateways) — detect / repair / prevent
**Symptom**: profile journal me har inbound message pe `single-entry routing save failed ... (database disk image is malformed); falling back to full index rewrite` + `state.db FTS write failed` → bot chalta rehta hai par error loop kabhi band nahi hota.
**Root cause class**: live state.db ka unclean kill / interrupted in-place maintenance (VACUUM, FTS teardown+backfill) → torn b-tree pages. `PRAGMA integrity_check` deta hai: "2nd reference to page N", "btreeInitPage() returns error code 11", invalid page. 153MB WAL + `TimeoutStopSec=60` (SIGKILL window) ise possible banate hain.
**Repair (data-preserving)**:
1. `python3 ~/ops/scripts/state-db-repair.py <profile|default>` — unit stop → backup (db+wal+shm) → copy → **logical rebuild** (CREATE tables → rows row-by-row → FTS `INSERT INTO fts(fts) VALUES('rebuild')` → indexes → triggers → user_version) → `integrity_check` == `ok` → counts match → swap → start + journal verify.
2. `.recover` NAHI chalta (sqlite3 CLI me SQLITE_ENABLE_DBPAGE_VTAB nahi hai). `REINDEX` / `VACUUM` / `VACUUM INTO` corrupt pages theek nahi karte (turant malformed) — sirf logical rebuild kaam karta hai.
3. Stale `<db>.fts_rebuild.lock` / `<db>.repair.lock` hatao — warna Hermes **fail-closed** reh jata hai aur FTS rebuild skip karta rehta hai (error permanently chipak jata hai).
**Prevention (deployed 2026-09-13)**: `hermes-state-db-guard.timer` (10 min, quick_check + auto-repair + Telegram alert) · `hermes-state-db-maintenance.timer` (03:35 UTC: VACUUM INTO snapshot + full integrity_check + WAL checkpoint) · gateway drop-in `TimeoutStopSec=180` · journald cap 800M/14d.
**quick_check cost control (2026-09-13, after a false "quick_check timeout" alert)**: a 1.19GB default state.db walked every 10 min = permanent disk read + a D-state task on 2 vCPU (it contributes to load average AND competes with everything else). Guard now: sqlite walk under `nice -n 19 ionice -c 2 -n 7` (yields, still progresses — **not** `-c 3`, idle class can starve forever); `QUICK_TIMEOUT=600` (one timer cycle, lock prevents overlap); DBs ≥ `BIG_DB_MB=400` swept only every `BIG_EVERY=3` runs (≈30 min), small profile DBs every run; the "could not run quick_check" alert fires only after `FAIL_STRIKES=3` **consecutive** failures, so one IO spike cannot page the user. A `quick_check` status of `deferred` in `~/ops/state/state-db-guard.json` is normal for the big DB, not a fault.
**Pitfalls**: corrupt DB par `SELECT count(*)` corrupt **index** se answer de sakta hai → verification me `... NOT INDEXED` use karo. `gateway_routing` derived cache hai (rows ka shortfall OK — Hermes sessions se rebuild karta hai; `entry_json` wale rows partially readable hote hain).

## Chrome Leak on Headless VMs — orphan *instances*, not just tabs (2026-09-13)
**Symptom**: sentinel pages `load average 4.5 on 2 vCPU` + `reaped 10 leaked chrome renderer(s): renderers 24->14, footprint 0.6GB->0.3GB` — and it pages **again** on the next tick.
**Root cause**: a *per-task* headless Chrome (own `--remote-debugging-port`, throwaway `/tmp/...` profile) whose client died. Parent pid becomes 1/systemd, `ss -tnp` shows **no ESTAB client** on its port, but the browser + ~5 renderers live forever. `chrome_tab_guard.py` only ever spoke to the shared automation port (9333), so nothing could reach them; the sentinel's renderer cap then reaped renderers blindly (each kill destroys whatever tab that renderer carried) and the browsers survived → alert repeats.
**Diagnosis in 60s**:
```bash
ps -eo pid,ppid,etimes,rss,args | grep -E "remote-debugging-port" | grep -v "type="   # one line per browser instance
ss -tnp | grep -E ":(9223|9231|9233)"   # ESTAB pair = live client; nothing = orphan
```
ppid=1/1231(systemd) + no ESTAB + age > 12 min = leaked.
**Fix (deployed)**: `chrome_tab_guard.py` **R5** (`reap_orphan_chrome`) — every chrome root exposing CDP, excluding `CDP_PORT` (9333) and the automation profile, with no non-chrome ESTAB client and age ≥ `CHROME_GUARD_ORPHAN_MIN=12`, is `orphan_seen` on the 1st run, SIGTERM on the 2nd (`CHROME_GUARD_ORPHAN_CONFIRM`), SIGKILL + profile-bound straggler sweep on the 3rd. Runs **before** the `cdp_alive()` check (must work with the shared CDP down); CLI `--orphans [--json]` for cheap external calls. Sentinel `check_chrome()` now calls `python3 ~/ops/scripts/chrome_tab_guard.py --orphans --json` **first** and skips the blunt renderer trim while orphans are being handled — blunt kills are the backstop, never the first response.
**Verify a fix like this end-to-end** (do not trust the live leak alone): launch a synthetic instance — `/opt/google/chrome/chrome --headless=new --remote-debugging-port=9299 --user-data-dir=/tmp/bc-chrome-guardtest about:blank &` — then `CHROME_GUARD_ORPHAN_MIN=0 CHROME_GUARD_ORPHAN_CONFIRM=1 python3 ~/ops/scripts/chrome_tab_guard.py --orphans --verbose` (must reap it, 0 leftovers), and unit-test the sentinel branch by importing the module and monkeypatching `chrome_usage`/`sh`/`reap_chrome` (reaper must NOT be called while an orphan event is present; must still be called on fallthrough). Test scripts: `~/ops/tmp/verify_orphan_fix.sh`, `~/ops/tmp/verify_load_alert.sh`.
**Result**: renderers 24 → 7 → 5, ~4GB RAM returned (the sentinel's guarded `swap_reclaim.sh` then pulled 2.6GB of disk swap back), load 4.5 → 1.4.

## Gateway Crash-Loop — wedged platform socket (Slack/aiohttp), 2026-09-15
Symptom Aamir ne report kiya: "infra slow" (load spikes, sluggish bot). Asal me ek gateway **crash-loop** chal raha tha.
- **Detect** (per unit, 10-min window):
  `for u in hermes-gateway hermes-gateway-luxewave ...; do echo -n "$u "; journalctl --user -u $u.service --since '-10 min' --no-pager -o cat | grep -c 'Traceback (most recent call last)'; done`
  Healthy = 0. Wedge = hundreds (incident me 240 + 120 per 10 min = ~13k lines/day, 130k/day lines Sep-14).
- **Root cause**: slack_sdk Socket Mode + aiohttp reuse a **closed** `aiohttp.ClientSession` after a websocket drop, so every retry raises instantly `RuntimeError("Session is closed")` (aiohttp/client.py:581) — session kabhi re-create nahi hota. Sep-13 20:30 pe dono gateways ka socket same second pe mara (network blip) → dono forever loop. Slack 34h dead raha aur koi alert nahi aaya.
- **Un-wedge**: sirf process restart kaam karta hai → `~/ops/scripts/slack_unwedge.sh` (luxewave restart → 15s → default restart → 75s → traceback count + socket evidence). Isko **transient unit** se chalao, warna jo gateway khud restart ho raha hai wo script ko bhi maar dega:
  `systemd-run --user --collect --on-active=150s --unit=slack-unwedge-$(date +%s) /bin/bash ~/ops/scripts/slack_unwedge.sh`
- **Permanent fix (teen layer)**:
  1. Ek Slack app = **ek** socket connection — Slack Socket Mode sirf default profile pe (`platforms.slack.enabled: false` client profiles me, e.g. luxewave). Refresh-token/duplicate socket = double failure surface.
  2. Unit guardrails (drop-in `~/.config/systemd/user/<unit>.service.d/99-guardrails.conf`, six gateway units): `CPUQuota=150%`, `MemoryAccounting=yes`, `MemoryHigh=2G`, `MemoryMax=3G`, `MemorySwapMax=1G`, `TasksMax=1024`, `LogRateLimitIntervalSec=30s`, `LogRateLimitBurst=400` → ek loop poori VM nahi kha sakta, journal spam capped, zram flood capped. `systemctl --user daemon-reload` ke baad running units pe **live** apply hota hai (restart ki zarurat nahi — PIDs unchanged, verify karo). ⚠️ Pehla version (`MemoryHigh=1G`, `MemoryMax=1500M`) **measured** ghalat tha: real working set 1.0G tha (soft limit ke upar baitha → 24,832 `high` reclaim events) aur history me peaks 2.6G–6.3G thay — yaani hard cap legit kaam ko OOM-kill kar sakta tha. Values history se upar rakho, aur audit ka tareeqa neeche wale section me hai.
  3. **Self-heal guard** (L4, `~/ops/scripts/gateway_storm_guard.py` + cron `gateway-storm-guard` `*/5 * * * *` no_agent): ≥60 tracebacks/10min = wedged → restart **deferred** (`systemd-run --on-active=8s`) taaki tick khud report kar sake even jab restart-able unit hi cron-host gateway ho; cooldown 30m, max 2 heals/hour, phir human escalate. Silent when healthy. Inspect: `gateway_storm_guard.py --status`. State: `~/ops/state/gateway-storm-guard.json`.
- **Pitfalls**: (a) `journalctl -u X` **--user** ke bina kuch nahi deta (yeh user units hain) — pehli baar 0 output isi wajah se aaya; (b) restart inline mat karo apne gateway ke andar se, apna hi turn mar jayega; (c) service ka `Restart=always` crash-loop **fix nahi karta** — loop process ke andar hai (exit nahi hota), isliye restart-on-crash kabhi fire nahi hua.

## Guardrail Trim — harm audit + crash-proof proof (2026-09-15)
Koi bhi systemd limit (CPUQuota/Memory*/TasksMax/LogRateLimit) "safe" tabhi hai jab ye 4 sawaal ka **jawab data se** mile:
1. **Kabhi fire hui?** → `cat /sys/fs/cgroup$(systemctl --user show <unit> -p ControlGroup --value)/memory.events` (`max`, `oom_kill`), `cpu.stat` (`nr_throttled`/`nr_periods`). Saare gateways pe `max=0 oom_kill=0` = kuch bhi kill nahi hua.
2. **Soft limit working set ke upar hai?** → `memory.current` vs `memory.high` + `memory.events` ka `high` counter. Baar-baar `high` badhna = kernel continuously reclaim kar raha hai (perf drag). Incident: gw `high=24,832` (cur 988M vs high 1G) → high 2G karne ke baad 75s me counter **0 delta**.
3. **Legit kaam ko maar sakti hai?** → `memory.peak` (systemd property + `memory.peak` file) vs `MemoryMax`. Peaks: gw 6.34G, invertio 4.34G, ops 2.58G — purana `MemoryMax=1500M` in se **neeche** tha → real OOM-kill risk tha. Naya cap 3G + `MemorySwapMax=1G`.
4. **Restart chain lockout-proof hai?** → `systemctl --user show <unit> -p Restart -p RestartUSec -p StartLimitIntervalUSec -p OOMPolicy -p TimeoutStopUSec -p KillMode` = `always` / `5s` / `0` (=start limiting OFF) / `stop` / `3min` / `mixed`. `NRestarts` > 0 (ops=1, whatsapp=14) proof hai ke systemd ne pehle bhi resurrect kiya.
Helpers: `python3 ~/ops/scripts/trim_status.py` (one-line-per-unit: cur/high/max/swap/peak/events/restarts) · `~/ops/scripts/trim_verify.sh` (apply+verify) · `~/ops/scripts/trim_churn_check.sh` (high-counter delta) · `~/ops/scripts/gateway_mem_watch.py [--status|--threshold N]`.
**Sentinel (L4, notify-owner)**: cron `gateway-mem-watch` `*/10 * * * *` no_agent → `~/.hermes/scripts/gateway-mem-watch.sh`; WARN at 80% of cap, ALERT on `oom_kill` increment / unexpected restart / unit down, WARN on swap > 1G; silent when healthy; state `~/ops/state/gateway_mem_watch.json`. Alert paths **injection-tested** (T1 threshold / T2 swap / T3 restart / T4 oom / T5 healthy-silent → `~/ops/scripts/gateway_mem_watch_test.sh`, log `~/ops/logs/gateway_mem_watch_test.txt`). Registry: `surfaces['gateway-mem-watch']` in `~/ops/observability/autonomy.json`; `autonomy_audit.py` → 0 block, 0 unclassified.
**Pitfalls (yeh teen mehnge thay)**:
- `StartLimitIntervalSec=` sirf **[Unit]** section me valid hai. `[Service]` me likho to systemd chup-chaap ignore karta hai ("Unknown key name ... ignoring" journal me). Naya directive add karne ke baad hamesha: `journalctl --user --since '-10 min' | grep 'Unknown key'`.
- Harness **gateway unit ko kill/restart karne se block karta hai** (apne hi gateway ke andar se) — aur theek hai. Restart-chain prove karne ke liye **throwaway lab unit** banao: same directives + `Restart=always`/`RestartSec=2`, phir 5 baar `systemctl --user kill -s SIGKILL` → har baar 2-3s me active (lab: `~/crashproof-lab/run.sh`, log `~/ops/logs/crashproof_lab.txt`).
- Memory-limit test me `bytearray(N)` **kaam nahi karta** — calloc zero-page charge nahi hota (peak 175M reh gaya, cap 192M). Pages ko **write** karo (`b"x"*16MB` chunks). Aur `MemoryHigh` pehle throttling/stall karta hai — cap tak pahunchne se pehle process ruk jata hai, is liye `oom_kill` sirf last resort hai (lab: `~/crashproof-lab/oom_test.sh`).
- `TimeoutStopSec` parity check karo: `hermes-gateway-ops` 60s pe tha (baaki 3min) → stop pe SIGKILL ka WAL window; ab sab 3min (`state-db-hardening.conf`).

## Load Alert on 2 vCPU — edge-triggered, attributed (2026-09-13)
A bare `load1 > 4.0` check on a 2-vCPU box fires on every healthy burst (one build / model load / sqlite walk saturates both cores) and the 15-min average then keeps it firing while an incident decays. Rule now in `sustained_load_alert()`: hot = `l15 > 3.0 AND l1 > 2.5` (sustained saturation *and* currently busy) or `l1 > 8.0`; the message names the top CPU holders (`ps -eo pcpu,comm --sort=-pcpu | head -3`); a `~/ops/observability/load_alert.flag` mtime gate suppresses repeats for 6h and is **unlinked on recovery**, so a genuinely new incident still alerts. Disk-swap pressure is already handled separately (auto `swap_reclaim.sh` when disk swap > 1GB and MemAvailable ≥ 4000MB).
**Patch-safety pitfall**: these ops scripts have no tests — after an index-based edit, `diff` the `.bak-orphanfix` copy and re-read the surrounding 10 lines. A block replacement anchored on the *first* match of a line you just inserted silently swallowed two neighbouring assignment lines (`entry["quick_check"] = status`) — the guard kept running but wrote `null` statuses.
Reboot se pehle banake enable karo — boot pe khud verify + log karta hai:
`/etc/systemd/system/sanad-postboot-check.service` → `ExecStart=/home/ubuntu/ops/scripts/post-reboot-check.sh` (After=network-online.target docker.service)
Script check karta hai: kernel, docker ps, gateway systemctl --user is-active, tunnel units, iptables harden rules count, fail2ban, sites HTTP 200 (curl), backup timer. Log: `/home/ubuntu/ops/logs/post-reboot-check.log`
**Pitfall**: log me "gateway INACTIVE" aa sakta hai agar check boot ke 6 min me chala — timing issue, live `systemctl --user is-active` se re-verify karo.

## Reboot
- Agent kabhi VM reboot nahi kar sakta (hardline block) — user se command lo: `sudo reboot`
- Reboot se pehle: gateway user-service enabled+linger, docker restart policies `--restart always`, firewall rules persisted, backup timer Persistent=true, post-boot check enabled
- External port verify: `for p in 7860 8001 8090; do timeout 3 bash -c "echo > /dev/tcp/$PUBIP/$p" && echo OPEN || echo BLOCKED; done`

## Fleet-wide crash-proof pass (system + user scope, 2026-09-16)

Ek-ek unit ke bajaye poore box pe ek pass: **pehle classify, phir do tier me apply.**

1. **Enumerate + classify** (system + user, alag-alag scope):
   `systemctl list-units --type=service --all --no-legend` (aur `--user` wala).
   Flapper = `SubState=auto-restart`, `Result=start-limit-hit`, ya
   `ActiveState=failed` + `NRestarts>0`. Per-unit proof:
   `systemctl show -p Restart -p RestartUSec -p StartLimitIntervalUSec -p NRestarts <u>`.
   **oneshot/wave units ko always-on mat samjho** — un pe `Restart=always` ek
   normal exit pe restart-storm bana deta hai. Exclude: `Type=oneshot` jo
   `inactive` + `Result in ("","success")` hai.
2. **Tier A — load-bearing always-on → never give up.**
   Drop-in: `/etc/systemd/system/<u>.service.d/50-crashproof.conf` (system) ya
   `~/.config/systemd/user/<u>.service.d/50-crashproof.conf` (user) —
   `[Service] Restart=always` + `RestartSec=3`, aur `[Unit] StartLimitIntervalSec=0`
   (0 = start limiting OFF; `[Service]` me likhna silently ignore hota hai).
   Phir `systemctl [--user] daemon-reload`.
3. **Tier B — genuinely broken / flapping → bounded, not infinite.**
   `StartLimitIntervalSec=600` + `StartLimitBurst=5`: loop ruk jata hai aur unit
   saaf `failed` dikhti hai (jo monitoring ko bhi dikhta hai) instead of
   silently burning CPU 24×7.
4. **Verification (per unit, apply ke baad)**: `systemctl show -p Restart
   -p RestartUSec -p StartLimitIntervalUSec` + `journalctl --since '-10 min' |
   grep 'Unknown key'` (typo'd directive chup-chaap ignore hota hai). Restart
   chain prove karne ke liye throwaway lab unit use karo (neeche ka pitfall).
5. **Naya governed surface ho to declare karo** — `autonomy.json → surfaces`
   (L2/L3 + gate_required), warna `autonomy_audit.py` block karega.

Real case: `munder-app.service` 360-restart flap loop chal raha tha; root cause
`~/munder-difflin/src` gayab (`203/EXEC`). Sahi handling = **Tier B + row ko
`down` dikhao + no-delete**, uninstall/mask nahi — aur user ko plain batao
"source folder gayab hai, isliye theek nahi kar sakta" (row chhupana ya
green dikhana galat hai). Containers ke liye drop-in nahi: `--restart
unless-stopped`.

## Pitfalls
- Localhost port check (`127.0.0.1`) hamesha OPEN dikhata hai — services wahan sunti hain; asal test public IP se karo
- iptables INPUT policy ACCEPT reh sakta hai — final REJECT rule hi effective guard hai
- rkhunter "possible rootkit" x11vnc false positive — context me dekhna, panic nahi
- apt list --upgradable grep count exit 1 = no upgradables (non-critical)
- **`systemctl list-units --failed` har hardening/QA pass me chalao** — silent failures hafton tak chhup jate hain aur disk/logs bharte rehte hain (aur koi monitoring nahi hoti). Real case 2026-09-21: `logrotate.service` 17 Sep se **failed** tha — `/etc/logrotate.d/hermes-ops-logs` me `su ubuntu ubuntu` tha par log files root-owned → har run "Permission denied" pe pura rotation **abort** (ek bhi log rotate nahi hua, 4 din). Fix order: config me `su root root` → `sudo logrotate -d <conf>` (dry, errors dikhao) → `sudo logrotate -f <conf>` → `sudo systemctl reset-failed logrotate.service && sudo systemctl start logrotate.service`. Cleanup/disk context: skill `vm-disk-cleanup`.
