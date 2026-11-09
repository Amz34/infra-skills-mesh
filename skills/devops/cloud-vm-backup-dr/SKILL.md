---
name: cloud-vm-backup-dr
description: Use when setting up cloud VM backup/DR or Drive OAuth.
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [backup, disaster-recovery, rclone, google-drive, watchdog, oauth]
    related_skills: [hermes-cloud-vm-ops, google-workspace]
---

# Cloud VM Backup & Disaster Recovery

Sole-entrepreneur "system immunity" pattern: koi bhi cloud VM (Oracle free-tier, etc.) ko failure-proof banane ke liye — automated encrypted offsite backups, one-command restore, self-healing watchdog. Verified working on Oracle Always-Free (Ubuntu 24.04 ARM64).

## When to use
- User bolta hai "system block/cancel na ho", "backup setup", "recovery", "kuch bhi ho jaye turant uth jaye"
- Kisi bhi VM pe Google Drive/offsite backup connect karna ho
- Services auto-restart + alert chahiye

## Core layout (established at ~/ops/)
| File | Role |
|---|---|
| `backup.sh` | Encrypted tar.gz (gpg) + MySQL dump + rclone upload to `gdrive:Hermes-Telegram-Backup/`; flags: `--no-drive`, `--upload-only` (repair mode: skip the dump, re-run JUST the Drive leg for the newest archive on disk — added 2026-09-15), `KEEP_LOCAL=3`, `KEEP_REMOTE=3` (rotation); tar MUST exclude `ops/backups` + `ops/logs` (see gotcha 7) |
| `restore.sh` | `list` (local + Drive), `pull` (Drive→local), `restore` (full extract; since 2026-09-10 it also copies back **cron/, state.db, profiles/**; `RESTORE_DRY_RUN=1` skips systemd/crontab writes; `HOME=<sandbox>` gives a non-destructive drill) |
| `verify/restore_verify.sh` | Asserts a restored home is usable: quick_check=ok, session/message counts, cron job count, skills/memories presence. `RESULT: N passed, F failed` |
| `verify/restore_drill.sh` | Weekly automated drill: restores newest archive into `/tmp/restore-drill-run` (via `HOME=`), verifies, silent on success / loud + exit 1 on failure. Cron `restore-drill-weekly` |
| `verify/drive_md5_parity.py` | **Third leg of the sanad-backup gate (added 2026-09-15): the off-VM object's CONTENT matches the local archive.** `rclone lsf` finding the name is NOT proof — the 09-15 probe was already listed on Drive by NAME while rclone was still re-sending it (it printed `Copied (new)` only later, 03:41:56) — so landing-before-success is real. Compares the local md5 against Drive's own `md5Checksum` (no download): prints `md5-parity-ok <hash>`, exit 0 = match, 1 = MISMATCH, **2 = UNVERIFIABLE** (remote not queryable — an unproven claim is not a pass). `--timeout 420` in `backup.sh` because gate.py's 120s default loses to a cold page cache (~35 MB/s disk) |
| `watchdog.sh` | Every 5 min: service check + auto-restart + Telegram alert (token from `~/.hermes/.env`, chat id from `channel_directory.json` or DM) |
| `disk-manager.sh` | `report` (largest dirs), ZIP-compress cold files |
| `kb/recovery.md` | Runbook: har failure ka fix path (Oracle reclaim, token expiry, disk full) |

## Scheduling — systemd timer beats crontab (verified 2026-09-01, hardened 2026-10-03)
**Two ticks: 02:30 primary + 06:30 safety net** (drop-in `sanad-backup.timer.d/retry.conf`). Single tick
ka matlab tha: ek fail = archive 36h stale aur recovery next night tak nahi. Ab 06:30 ka run
`backup.sh` ke andar decide hota hai: aaj ka archive nahi → full build; local hai Drive pe nahi →
`upload-only` repair; dono ok → quiet `exit 0`. Missed runs catch up after reboot via `Persistent=true`,
journald logging, no user crontab dependency:
```
# /etc/systemd/system/sanad-backup.service
[Unit]
Description=Daily encrypted backup to Google Drive
After=network-online.target
[Service]
Type=oneshot
ExecStart=/usr/bin/sudo -E /usr/bin/bash /home/ubuntu/ops/backup.sh
User=ubuntu
Nice=10
IOSchedulingClass=idle
StandardOutput=journal
StandardError=journal
[Install]
WantedBy=multi-user.target

# /etc/systemd/system/sanad-backup.timer
[Unit]
Description=Daily backup trigger
[Timer]
OnCalendar=*-*-* 02:30:00
Persistent=true
# --- drop-in: /etc/systemd/system/sanad-backup.timer.d/retry.conf (2026-10-03) ---
# comments apni line pe (systemd inline `#` support nahi karta)
# [Timer]
# OnCalendar=
# OnCalendar=*-*-* 02:30:00
# OnCalendar=*-*-* 06:30:00
# Persistent=true
# RandomizedDelaySec=0
[Install]
WantedBy=timers.target
```
Enable: `sudo systemctl daemon-reload && sudo systemctl enable --now sanad-backup.timer`.
NOTE: agent `write_file` REFUSES `/etc/systemd/system/` paths — write via `sudo tee /etc/systemd/system/...` heredoc in terminal.
Watchdog: keep `*/5 * * * * bash ~/ops/watchdog.sh` in the USER crontab (or its own timer) — that one is a user-space script, not a system unit.

Rotate: keep 3 local + 4 remote so free-tier Drive (15GB) never fills; one ~600MB encrypted backup ≈ 12GB headroom.

## Critical gotchas
1. **Google OAuth auth-code is SINGLE-USE.** Exchange it once and save the token file immediately — verifying with a test curl then re-exchanging fails with the same code. If lost, ask user to redo the login link.
2. **Never `rclone config create ... token '...'`** — it re-triggers the interactive OAuth flow and hangs. Write the token JSON directly into `~/.config/rclone/rclone.conf`.
3. **`"expiry"` value decides whether rclone EVER refreshes — and a far-future sentinel is the same trap as an empty one** (root cause of the 2-night DR outage 2026-09-11→12, verified 2026-09-12). rclone refreshes the access_token **only when the stored `expiry` is in the past**; with `"expiry": ""` *or* `"expiry": "2035-01-01T00:00:00Z"` it believes the ~1h token is valid forever, never refreshes, and every later run dies `401 Invalid Credentials` while the `refresh_token` is perfectly healthy. **Write the REAL expiry** (`now + expires_in`, RFC3339) — then rclone self-heals on its own. Proven: expiry forced 2h into the past → `rclone lsf` succeeded and rclone wrote back a fresh token by itself. Never write a sentinel date.
4. **`rclone about gdrive:` can fail transiently** with API quota errors right after upload; `rclone lsl/lsf/size` usually still work — use those for verification.
5. **Drive OAuth token ≠ Gmail SMTP.** Sending email needs a separate Gmail App Password (16-letter); don't assume Drive auth covers mail.
6. Backup script must be **read-only on live services** — mysqldump via `docker exec`, no container restarts. User's hard rule: "bina system tode safely kaam karo".
7. **RECURSIVE TAR BUG (Drive-killer, verified 2026-09-01):** `tar -C ~ ops` me agar `--exclude='ops/backups' --exclude='ops/logs'` na ho to backup khud apne past backups ko include karta hai → size har roz doubles: 465MB → 949MB → 1.9GB → 3.8GB → 7.5GB → 15GB+ (Drive 15GB quota blow). Growth-series ya `du -sh ops/backups` se detect karo; tar command me hamesha excludes laga ke `bash -n` verify karo. Fresh fixed backup ≈ 600MB.
8. **rclone 401 "Invalid Credentials"** after idle/after upload = stale access_token (~1h TTL); stored refresh_token is long-lived → fix via direct refresh exchange (no user login). Exact recipe: `references/rclone-google-drive-headless-oauth.md` section 7.
9. **rclone chunked upload = remote pe file tab tak invisible** jab tak complete na ho; `lsl` partial size nahi dikhata. Verify via process wait + `rclone check --size-only` (exact byte match, 0 diffs) after EXIT=0.
10. **`set -euo pipefail` + unguarded command substitution = silent DR failure (verified 2026-09-10, ~3 weeks undetected).** `REMOTE_FILES=$(timeout 60 rclone lsf ... | grep ... | sort -r | tail -n +5)` — jab bhi Drive down hota, substitution fail → pipefail → script us line pe abort → **local rotation (jo uske NEECHE thi) kabhi chalti hi nahi** → 11 archives/16GB jam, aur unit har raat `FAILED` (status=1) bina kisi ko bataye. Fix: drive steps ko `|| true` se guard karo, rotation ko hamesha chalao, aur exit code ko meaning do (`exit 4` = local ok, off-VM stale). **Detection:** `journalctl -u sanad-backup | grep "Failed to start"` + `systemctl is-failed sanad-backup` + archive count > KEEP_LOCAL. Lesson: har `$( ... )` assignment jo network call karti hai usay guard karo — warna ek remote hiccup poori script ka tail maar deta hai.
11. **Backup jo restore-test na hua ho = backup nahi.** 2026-09-10 drill se 3 gaps nikle jo mahino se the: (a) `state.db` (poori session history) archive me hi nahi thi — `backup.sh` sirf config/skills/memories/cron copy karta tha; (b) `profiles/` (per-profile skills/memories/cron/state.db) bilkul nahi; (c) `restore.sh` `cron/` kabhi copy-back nahi karta tha (jobs.json archive me thi!) → 25 cron jobs restore pe gayab. Fix: `sqlite3 DB ".backup 'dest'"` se WAL-safe snapshot (cp mat karo — torn copy), profile tars with `--exclude='./home' --exclude='./cache' --exclude='./bin' --exclude='./lsp' --exclude='./platforms'`, aur restore me cron/state.db/profiles blocks. **Rule: naya file archive me add karne ke baad restore path me uska copy-back bhi add karo, phir drill chalao.**
12. **`restore.sh` ka `DRIVE_FOLDER` backup.sh se match karna chahiye** (`Hermes-Telegram-Backup`). Ek waqt `Sanad-Backup` tha → `restore.sh list/pull` chup-chaap kuch nahi dhoondhta tha.
13. **`hermes backup -q -l LABEL` `-o` ko IGNORE karta hai** — quick mode `~/.hermes/state-snapshots/<stamp>-<label>/` me likhta hai (config.yaml, .env, auth.json, cron/jobs.json, executions.db, state.db — 854MB, ~66s). Use: pre-upgrade fast snapshot. Restore: `HERMES_HOME=<sandbox> hermes import <zip>` full-zip ke liye; aur **`HERMES_HOME` env var hi home resolution me sabse pehle aata hai** (`hermes_constants.get_hermes_home`) — isse koi bhi restore/import live home ko chhue bina sandbox me test ho sakta hai. NOTE: `-q` snapshot ka koi auto-rotation nahi — purane snapshots khud saaf karo.

14. **Offsite upload silently skipped when the backup runs as root (verified 2026-09-10).** `sanad-backup.service` ka ExecStart `/usr/bin/sudo -E /usr/bin/bash /home/ubuntu/ops/backup.sh` hai → script **root** ke roop me chalti hai, aur root ke paas **koi rclone config nahi** (`/root/.config/rclone/` exist hi nahi karta) → har Drive step `rclone gdrive not ready — archive kept locally` keh ke aage badh jata hai. Nateeja: mahino tak locally green backup (daily archive, rotation, `systemctl status` theek, timer theek) aur **zero off-VM copy** — bilkul wahi failure mode jiske liye offsite backup banaya gaya tha. Diagnose: `sudo -n env rclone about gdrive:` → "didn't find section in config file" (as ubuntu same command 401/config-detected dega — difference hi root-vs-user ka proof hai). Fix (token duplicate karne ki zarurat nahi, single source of truth): backup.sh ke top pe `export RCLONE_CONFIG="${RCLONE_CONFIG:-/home/ubuntu/.config/rclone/rclone.conf}"` (root ubuntu ki 600 file padh sakta hai). **Rule: systemd/cron se chalne wale har script ka `whoami` + `echo $HOME` verify karo — root vs ubuntu ka config/token split sabse chup-chaap wala DR hole hai.**
15. **Offsite mirror failure must be LOUD (canary pattern).** Nightly backup kisi bhi Drive problem pe local-only degrade hota hai — agar us path ka failure silent ho to offsite layer mahino tak sad jata hai (nightly job ka journal koi nahi padhta). Working pattern (2026-09-10): jis bhi script me Drive mirror fail ho → local dump rakho par **non-zero exit + ek-line clear reason** (`drive upload FAILED (401 Invalid Credentials) — local dump kept at <path>`), aur usay no_agent Hermes cron me wire karo → failure apne aap Telegram alert ban jati hai. Shim ka contract: healthy = bilkul silent, fail = loud.
16. **DB snapshot ≠ diffable backup (granularity layering).** Encrypted DB/home archive poora world restore karta hai par ye sawaal answer nahi kar sakta: "kal se is object me kya badla" ya "sirf ek object wapas import karo". Sasta second layer add karo: per-object versioned export (n8n example: `/home/ubuntu/ops/scripts/n8n_export_workflows.py` → `~/ops/backups/n8n-workflows/<date>/*.json`, last 8 retain, Drive mirror) — isse dates ke beech `diff` aur single-object re-import dono possible. Local dump verified; mirror pe gotcha 15 ka loud-failure rule lagao.

17. **OAuth "safal" ≠ sahi account (verified 2026-09-10).** `rclone config reconnect` / koi bhi browser login **browser ka default Google session** authorize karta hai → re-auth ke baad token chup-chaap **doosre account** ka ban sakta hai. Symptoms: `rclone lsf gdrive:Hermes-Telegram-Backup/` → `directory not found`, `rclone about gdrive:` ~40 MiB / 15 GiB (asli folder ~3.8 GiB), `lsd` me ajnabi folders — remote chalta rehta hai, isliye nightly backup + mirror "success" dikhate rehte hain. **User se dobara login karane se PEHLE** newest archive se purani config nikaal ke uske `refresh_token` ko refresh karo (bina login original account wapas aa jata hai) → full recipe: `references/rclone-wrong-account-recovery.md`. Baad me `rclone lsf` + `rclone size` se assert karo — "user ne login kar diya" proof nahi hai; login handover me account ka naam likho (`azengineeringapp@gmail.com`) + "Use another account".

18. **Off-VM copy must be PROVEN by the nightly run itself, not by a log line** (added 2026-09-12). `backup.sh` now ends with a **verification gate** (`~/ops/verify/gate.py`, registry level L3/external/gate_required): (a) `gate.py file "$ENC_FILE" --min-bytes 1000` — the local archive is a real GPG file of sane size, (b) `gate.py cmd "rclone lsf gdrive:$DRIVE_FOLDER/$(basename "$ENC_FILE")" --expect 0 --contains "<name>"` — the object lists back from Drive by name. Both runs are recorded in `~/ops/verify/reports/gate-*.jsonl`; a failure writes a dead-letter row to `~/ops/observability/backup-deadletter.jsonl` and stays loud, but never deletes anything (the DR copy remains recoverable). Why: the Sep-11/12 outage produced only one line inside `journalctl` — nobody reads the journal. Wire the same trick into any mirror/export job.

19. **Never kill an in-flight upload that reads `0 B / 1.4 GiB, 0%`** (learned the hard way 2026-
    09-12: killed a healthy copy at 16 min and had to restart it). `rclone`'s chunked Drive upload
    reports progress only as each chunk commits, and the first commit can take minutes — 0 B means
    "first chunk in flight", not "stalled". Check with `--stats 30s -v` into a log file instead of
    judging from a preview, and sanity-check the uplink separately (5 MB test file). Measured on the
    Oracle free-tier VM: **~2-5 MiB/s up**, i.e. a 1.4 GB archive legitimately takes **10-35 min**,
    so the per-file `timeout` in a wrapper must be generous (`1200s` is fine; `120s` is not). A small
    upload test also separates "Drive/token broken" from "just slow".

20. **Upload strategy: the BODY moves fine — it is the COMMIT that takes minutes, and rclone's 5m
    default idle timeout kills it and re-sends the whole archive** (root-caused 2026-09-13 on the real
    unit; three separate symptoms, one cause). What the logs actually show for a 1.5 GiB archive at
    ~5 MiB/s: the byte count reaches the full size, then the reported speed *decays* (417 KiB/s →
    60 KiB/s → 8.7 KiB/s → 1.25 KiB/s → 185 B/s) while nothing new moves — that plateau is the
    finalize/commit phase, and rclone times out at `--timeout` (default **5m**) **during it**,
    discards the attempt and restarts the file from byte 0 (the progress flipping to "50%" of a
    doubled total is that restart; on 2026-09-13 02:37 it burned ~6 attempts / 30 min / 8.477 GiB and
    gave up, so the whole night's off-VM copy was lost with no ERROR line). Proof it is the commit
    and not the uplink: a 100 MiB probe uploaded at 2.35 MiB/s and committed, but took **252 s**
    wall-clock for ~42 s of data movement — the rest was the commit. Fixes now in `backup.sh`:
    `--timeout 15m` (never the 5m default) + `--transfers 1 --retries 2 --low-level-retries 15
    --contimeout 60s`, per-attempt wall `SINGLE_WALL=2700` / `RESUMABLE_WALL=1500`. **Strategy ORDER corrected 2026-09-15 —
single-shot FIRST**
(`--drive-upload-cutoff 2G`), resumable only as fallback (`--drive-upload-cutoff 8M --drive-chunk-size 32M`):
measured across 2026-09-13/14/15 the *resumable* path **never once committed** on this VM — all three
nights reached 100 % of the body, then the chunk-assembly finalize trickled at 5–800 B/s instead of
returning, the trickle kept resetting `--timeout` so it never aborted, and the wall killed it
every night (logs show 2–4× the archive size pushed = ~35 min of saturated uplink for nothing).
Single-shot commits in **~11–24 min**. Its only weakness is that any hiccup re-sends the whole archive
from zero — which is exactly why the resumable fallback stays in place.
**Plan for MULTIPLE whole-file passes, not one — but never count passes from the counter.** The
finalize is flaky on this uplink. Calibration from runs that actually committed: 2026-09-14 ended at
exactly **2.0×** the file size (1.726 GiB archive → `3.451 / 3.451 GiB` when "Copied (new)" printed),
2026-09-15 at **4.0×** (1.784 GiB → `7.137 / 7.137 GiB`, committed 03:24) — i.e. at least one full
re-send before the commit, all of it with **no error line at ANY verbosity**. The counter is NOT an
attempt counter — its shape differs run to run (09-14 ended at 2.0×, 09-15 at 4.0×, and the 20 MiB
probe's total was already 2× before a byte moved), and post-landing re-sends inflate it too. An earlier
reading of this same log as "4 passes" was exactly the trap the two measurement traps below warn about.
What IS measurable per night is the WALL the run consumes — 09-15 used 26 of 35 min (74 %) — which is why
the per-attempt wall is now an argument: `SINGLE_WALL=2700` / `RESUMABLE_WALL=1500` instead of a flat 2100s. Check Drive quota before blaming
the network: `rclone about` showed 10.4 GiB free and `trashed: 0` on 09-15. Two measurement traps to keep
    in mind when reading these logs: (a) the `--stats-one-line` counter reports **twice** the file
    size as "total" (100 MiB file → "200 MiB"), so a run sitting at "50%" has actually sent the whole
    file — do NOT kill it, and do not read it as a re-send; (b) an INFO-only log can end with no
    `ERROR` line at all, so judge by `rclone lsf` (object present = success), never by the absence of
    errors. Diagnostic that separates the cases: `rclone copy --dry-run -vv <file> <remote:dir>` →
    "Need to transfer - File not found at Destination" means the source/dest mapping is fine and the
    *upload* is the problem; if a small (5 MB) test file uploads fine but the big one never commits,
    it is the session/commit path, not credentials.

**The 20 MiB probe (2026-09-15) is the decisive measurement: this is NOT a size problem.**
`~/ops/logs/rclone-probe-20mib-20260915.log` — ran 03:39:03 → 03:41:56, `RCLONE_EXIT=0`, and needed
**3 whole-file attempts** (2–5 MiB/s bursts decaying to 65 KiB/s at each finalize, then a re-send from
byte 0) before `Copied (new)`. It was already listed on Drive **by name** while rclone was still
re-sending it, so a name match proves nothing — md5 parity does. Because 20 MiB fails exactly as 1.8 GiB
does, splitting archives into smaller parts would likely **not** fix the finalize: attribution first.
    Full evidence, the reusable 20 MiB probe recipe and the `--stats-one-line` counter traps live in
    `references/rclone-drive-finalize-flakiness.md`; the open diagnostic is `--dump=headers` on the next
    flaky night (never `-vv` — it logs the OAuth token).

21. **Two false-negative traps in the nightly path (fixed 2026-09-12, both found only by running the
    real unit).** (a) **`rclone about gdrive:` is not a readiness gate** — it rate-limits
    transiently, and `backup.sh` used it to decide "Drive is down", so one flaky call skipped the
    upload and left the DR copy stale with an innocent-looking log line. Use `rclone lsd gdrive:`
    (cheap, reliable) with retries. (b) **rclone rewrites `rclone.conf` as the RUNNING user** — the
    unit runs via `sudo -E`, so after a token refresh the file became `root:root 600` and every
    non-root rclone call (the sentinel's off-VM check, manual checks) died with `permission denied`,
    which reads as `OFF-VM COPY MISSING` (a false alarm pointing at the wrong layer). `backup.sh`
    now re-asserts `chown root:ubuntu` + `chmod 640` at the end of every run. Rule of thumb: any
    "the remote is unreachable" symptom must be confirmed with a *listing* before you touch
    credentials.

22. **A full Drive DEADLOCKS the old rotation order — make room BEFORE the upload, and count the
    TRASH** (root cause of the 2026-09-13 ⛔ sentinel alert, verified by hand that day). Symptoms the
    alert gave: `newest archive sanad-backup-20260913_023258.tar.gz.gpg not on Drive (remote newest:
    sanad-backup-20260912_093942...)`. Why: rotation (`prune_remotes_to`) ran only **after a
    *successful* upload**, so once Drive filled up the folder could never shrink again → the upload
    failed at 99% → rotation never ran → every following night fails identically. Space math that day:
    Drive `Total 15 GiB / Used 7.87 GiB / Trashed 2.46 GiB / Free 5.42 GiB` with **4 archives =
    5.35 GiB** and a 1.41 GiB archive per night — the folder was at `KEEP_REMOTE` already, so nothing
    was ever prunable *and* 2.46 GiB of **trashed** objects still counted against the quota.
    Fixes now in `backup.sh`: (a) **quota pre-check + make-room before uploading** —
    `drive_free_mb()` parses `rclone about gdrive: --json` (never as a readiness gate, see gotcha 21)
    and if `free < archive + MARGIN_MB` it prunes remotes down to `KEEP_REMOTE-1`, then
    `rclone cleanup gdrive:` (empty trash), then down to 2, logging each step and never touching the
    newest archive; (b) rotation deletes use `--drive-use-trash=false` so a rotated archive frees
    space **immediately** instead of sitting in trash for 30 days; (c) `KEEP_REMOTE=3` (was 4) — 3 ×
    ~1.5 GB ≈ 4.5 GiB leaves real headroom on a 15 GiB Drive that also holds Gmail/Photos usage;
    (d) `infra_sentinel.py` now warns **before** the wall: more than `KEEP_REMOTE` archives on Drive
    ("remote rotation not running; Drive will fill up") or `free < 4 × archive` ("quota nearly
    exhausted — rclone cleanup gdrive: to empty trash"). Manual recovery for a stuck folder:
    `rclone cleanup gdrive:` (trash), `rclone lsl gdrive:Hermes-Telegram-Backup/` (inspect),
    `rclone delete --drive-use-trash=false gdrive:<folder>/<old>`, then re-run the upload for the
    newest local archive and confirm with `rclone lsf`. A `rclone about` free-space number that looks
    "big enough" is not proof — the archive must be *listed* after the upload.

23. **A probe that cannot tell "error" from "empty" invents DR outages (fixed 2026-09-14).** `check_backups()` used `sh()`, which collapses rc!=0, stderr AND timeouts into `""` → every transient `rclone lsf` failure became the alert "OFF-VM COPY MISSING — rclone gdrive lists nothing (DR is local-only)". It fired 3× at 00:00–00:01 (09-11 / 09-12 / 09-14) while the off-VM copy was in fact present and byte-identical (`1520639999` B on both sides) — that minute is when the box is crushed (dpkg-db-backup + logrotate + chrome-reaper + the `*/30` cron cohort + collector). Fix shipped: `sh_rc()` keeps rc + stderr; `rclone_probe()` retries 3× (10s/25s backoff, `--retries 3 --low-level-retries 10`) returning `(ok, out, rc, err, tries)`; `check_backups()` now emits three distinct verdicts — listed+non-empty / listed+EMPTY (real gap) / **UNVERIFIED + the actual error text** (never "missing"); each failed attempt is logged as `backup_probe_fail` in `sentinel-events.jsonl`, and the once-a-day flag is now `date|sha1(problem-set)` so an unchanged problem stays quiet while a *changed* one still gets through. The cron moved `*/30` → `7,37 * * * *` to dodge the top-of-hour pile-up. Regression test: `python3 ~/ops/verify/tests/test_sentinel_probe_retry.py` (8 asserts). Lesson: never let a watchdog's healthy/unhealthy verdict come from a command whose failure mode is "empty output".

24. **A watchdog that does not know a job is RUNNING will cry wolf every single night (fixed
    2026-09-15).** Second ⛔ of the same shape: `newest archive sanad-backup-20260915_023021.tar.gz.gpg
    not on Drive (remote newest: sanad-backup-20260914_023209...)` — while the upload for that very
    archive *was in flight*. The sentinel cron ticks at `:07/:37`, the backup timer fires **02:30** and
    the Drive object only appears **03:10–03:23** (11–50 min to push ~1.8 GB through a 2-vCPU box), so
    any tick inside that window compared "newest local" against "newest remote", saw a perfectly
    normal 1-night gap, and called it a DR outage. Two fixes shipped:
    (a) **in-flight guard** — `backup_in_flight()` returns a reason string when
    `systemctl is-active sanad-backup.service` is `activating/active/reloading`, or when
    `rclone_backup_push_running()` sees an rclone process whose `/proc/<pid>/cmdline` mentions both
    `copy` and `sanad-backup-`; with the newest archive missing *and* a run in flight the sentinel
    logs `backup_upload_in_flight` to `sentinel-events.jsonl` and stays SILENT (DR still holds the
    previous night, so this is not a gap). **Do NOT implement that process check with
    `pgrep -af '<pattern>'`**: pgrep's own parent shell carries the pattern text in its command
    line, so the wrapper matches its own search and the answer is permanently TRUE — which would
    silently swallow every genuine off-VM alert (the one thing that check exists to raise). That
    bug shipped for ~30 min on 2026-09-15 and was caught only by running
    `verify/tests/probe_sentinel_backup.py` against the LIVE box — the unit test cannot see it
    because it shims `sh()`. Read `/proc` directly (or use `pgrep -x rclone`, name-only, which has
    no pattern to self-match).
    (b) **staleness measured in NIGHTS, never in files** — `nights_behind(newest_local, newest_remote)`
    parses `sanad-backup-YYYYMMDD_HHMMSS` via `ARCHIVE_RE`. `>= 2` nights behind → alert ("the nightly
    upload has been failing", not a transient tick) **even while a run is in flight**, because a run
    that has been broken for 3 days must not be excused by tonight's retry. Do NOT compare "older local
    archives missing from Drive": local retention (`KEEP_LOCAL=3`) is deliberately independent of
    remote retention (`KEEP_REMOTE=3`), so that check fires on healthy days.
    Also: the remote folder is NOT archives-only — it also holds `n8n-workflows/<date>/*.json`, so any
    name-based remote logic must filter with `ARCHIVE_RE` (`.gpg` suffix) before sorting/counting,
    otherwise "newest remote" can resolve to a workflow JSON.
    **Rule: a monitor's verdict must account for the job's OWN schedule.** Before alarming on "X not
    there yet", ask whether X is still being written.

25. **Never edit a shell script while it is executing (learned 2026-09-15, avoided a live incident).**
    `bash` reads a script file by byte offset and parses whole compound commands (`if ... fi`) up front;
    editing an earlier line in place shifts every later offset, so when the running shell returns to the
    stored offset it may execute the middle of an unrelated line. Caught mid-repair: the 02:30 backup was
    *still running* (resumable, `timeout 2100` due 03:10) when `backup.sh` was patched — the live rclone
    was still using the pre-edit order (proof bash had parsed the block from memory), and the post-block
    offset was stale. Safe handling: (1) `systemctl stop` on the unit (needs polkit → from a non-login
    agent shell use `sudo kill -TERM <script-pid> <timeout-pid> <rclone-pid>`), (2) verify with
    `pgrep -af`, (3) `systemctl is-failed` is now `failed` → **`sudo systemctl reset-failed sanad-backup.service`**,
    otherwise the sentinel's `is-failed` check fires a *different* alert right after the fix, (4) re-run
    the leg you interrupted via `bash backup.sh --upload-only`. Editing an unrelated *newer* line, or
    replacing the file by rename (`mv`), is safe — a running shell keeps the old inode.

26. **DR ka source of truth = aaj raat ka run, na ki memory note ya purani log line** (2026-09-16).
    Memory me months purani "offsite local-only / gdrive not ready" note padi thi jabki live chain
    green thi — purana `backup.log` warning (August ke `rclone gdrive not ready` lines) aur ab ka
    PASS ek saath exist karte hain, isliye **log tail alone kabhi verdict nahi deta**. Newest night
    ka verdict 4 read-only checks se lo (order me, ~20s):
    `systemctl is-failed sanad-backup` → `journalctl -u sanad-backup --since '-1d' | grep -iE 'PASS|FAIL|parity|Copied \(new\)'`
    → `rclone lsf gdrive:Hermes-Telegram-Backup/ | grep sanad-backup` (name listing = upload landed)
    → `ls -l ~/ops/backups/sanad-backup-*.tar.gz.gpg | tail -1` (local archive size/age sane, ~2GB).
    Sab ke baad hi "DR OK" likho — aur agar memory purana "DR band" kehti ho to memory ko correct
    karo, kyunki galat DR memory agli baar poori recovery planning ko skew karti hai.
    **rclone timeouts me unit ZAROORI hai** — `--timeout 15` Go duration parse error deta hai
    (`missing unit in duration`); hamesha `--timeout 60s` / `--timeout 15m`. Probe scripts
    (`rclone size <remote>: --json --timeout 60s`) isi wajah se fail hote hain, remote down nahi hota.
    **Archive size bounce normal hai** (rotation ke baad ~2GB, kuch raaton me 7.5GB wala purana
    recursive-tar bug series se confuse mat karo — see gotcha 7): size anomaly ko archive age +
    `rclone lsf` se cross-check karo, akele size se incident declare mat karo.

27. **`set -euo pipefail` + unguarded `VAR=$(cmd | grep …)` = poori nightly backup silently maut**
    (2026-10-03, real incident: archive 36h stale, Drive 36h purana). Root cause do bugs ka combo tha:
    (a) WordPress staging container rename ho gaya `wp-db` → `avvs-wp-db`, par guard `docker ps | grep -q wp-db`
    **substring** match karta hai (isliye `avvs-wp-db` pe bhi pass ho gaya), aur (b) uske baad
    `DB_USER=$(docker exec wp-db env | grep '^MYSQL_USER=' | cut -d= -f2)` — missing container → pipeline
    non-zero → `pipefail` → **assignment ka status non-zero** → `set -e` ne 02:35 pe poori script maar di.
    Archive bana hi nahi, upload hua hi nahi, par local logs me sirf "Dumping WordPress database..." dikha.
    **Rules:** (1) koi bhi optional leg (docker/network/parity) `VAR=$(… || true)` + `[ -n "$VAR" ]` se
    guard karo — optional cheez kabhi archive ko abort na kare; (2) container ko **exact** match se dhoondo
    (`grep -E '(^|[-_])wp[-_]?db$'`), substring se kabhi nahi; (3) `docker exec <ctr> env` se creds/DB name
    **auto-discover** karo (hardcode `wordpress/wordpress` rename ke baad chup-chaap galat DB dump karta hai);
    (4) dump ke baad `[ -s file ]` check + WARN, warna khaali file archive me chali jayegi.
    Audit command (sab .sh scripts): `grep -rnE '^\s*[A-Za-z_]+="?\$\([^)]*\|' --include="*.sh" . | grep -v '|| true'`

28. **Upload log ka % literal mat padho (2026-10-03):** `--retries 2` + low-level retries se rclone ke stats CUMULATIVE ho jate hain — 3GB archive par log "9.158 GiB / 12.211 GiB" (4x) dikha sakta hai, `grep -i error` khaali. Verdict = journal ka upload line + `rclone lsf gdrive:Hermes-Telegram-Backup`, log % nahi. Slow uplink (700 KiB/s) par wall khatam → `RESUMABLE_WALL=10800 bash backup.sh --upload-only` se rat me poora karo.

29. **Jab archive free Drive se bada ho jaye, Drive se ladna band karo — usi tenancy ka Always Free Object Storage bucket off-VM copy banao** (verified 2026-10-08, 3 raat Oct 6/7/8 fail hone ke baad). Symptoms: `systemctl is-failed sanad-backup` = failed; dono upload logs whole-file-size ke multiples pe khatam, `grep -i error` KHAALI; `rclone about gdrive:` = **Total 15 GiB / Used 4.73 / Free 8.56 GiB** jabki archive **4.997 GiB** aur ~0.3–1.6 GiB/raat badh raha (archive ka ~50% `state.db` hai) → `KEEP_REMOTE` ke liye jagah hi nahi bachti aur gotcha 20 ka finalize-trickle afford hi nahi hota. Local tars `KEEP_LOCAL` tak bhar jate hain, disk 77% pe atak jata hai — aur **reclaim levers (infra_reclaim/caches/journal/docker) "0 freed" report karte hain**, kyunki churn ka source backup hai, cache nahi.
    Fix shipped: `ops/scripts/oci_backup_upload.sh` + `backup.sh` leg 3a2 → **OCI bucket `hermes-backup` (Standard, me-jeddah-1) = Always Free 20 GB (object+archive combined)**, API-key auth `/home/ubuntu/.oci/config`, multipart put, **KEEP=2**, flock + verify-by-read-back. Measured: **5.1 GiB <2 min me commit + verified** usi uplink pe jahan rclone/Drive 75 min jalake commit nahi kar paya — provider-native network Drive ke finalize path se behtar hai.
    Gate rewired: off-VM claim Drive parity **ya** bucket leg se satisfy hoti hai; fail tabhi jab DONE legs down; dead-letter row me `"oci_ok"` add. `oci-free-guard.sh` ab bucket size sum kar ke >15 GB pe alert karta hai.
    Do implementation traps: (a) `oci os object head --query 'data."content-length"'` is CLI pe **"none"** deta hai → ACHHA upload bhi failed dikhta hai; verify `oci os object list --prefix <name>` + `size` se karo (name AUR bytes read-back); (b) `oci os object put --no-overwrite false` → `Error: Got unexpected extra argument (false)` — flags boolean hain, value mat do; (c) **lock file /tmp me mat rakho**: backup root se chalta hai aur Ubuntu ka `fs.protected_regular=2` dusre user ke file pe O_CREAT refuse karta hai → root ko `Permission denied`, flock fail, aur script chupchap **"another run holds the lock" bolke exit 0** = green run bina off-VM copy (2026-10-08 pe pakda gaya, gate command root se chala ke). Lock `ops/logs/.oci-backup-upload.lock` (mode 666) me rakho, lock sirf upload mode me lo (verify/list/dry read-only hain), aur lock open fail pe **loud exit** karo — silent skip kabhi nahi.
    Free-tier note: bucket ≤ ~15 GB rakho (2 × 5 GiB) taki object+archive 20 GB Always Free allowance me rahe; same tenancy = provider-level loss pe Drive copy (local + Drive + bucket = 3 copies) bachati hai.

## Headless Google OAuth → rclone (verified)
Full recipe with exact URLs/commands in `references/rclone-google-drive-headless-oauth.md` — user opens login link, copies redirect URL from address bar (error page is NORMAL), assistant exchanges code via curl and writes config.

## User-facing OAuth instructions (Telegram)
- "Use another account" click karo — **not** "Create account"
- Google "app not verified" screen → Advanced → "Go to rclone (unsafe)" — rclone's public client is safe
- After Allow, the "This site can't be reached" page is EXPECTED — copy the FULL URL from the address bar (contains `code=...`)

## Verification sequence (always run end-to-end)
1. `bash backup.sh` → encrypted .gpg exists locally
2. `rclone lsl gdrive:Hermes-Telegram-Backup/` → file present with sane size (chunked upload → invisible until complete; `rclone check --size-only` after EXIT=0)
3. `gpg -d ... | tar -xzf -` into a temp dir → critical paths present (configs, tokens, DB dump)
4. `bash restore.sh pull` → re-download from Drive works
5. **`bash ops/verify/restore_drill.sh`** → the one that actually matters: it RESTORES the newest archive into `/tmp/restore-drill-run` and proves the result is usable (`restore_verify.sh`: quick_check=ok, session/message counts > 0, cron jobs, skills, memories). Silent on success; loud + exit 1 on failure. Never ship a backup change without running this.
5a. **After ANY drill, check the sandbox is GONE** — `ls -d /tmp/restore-drill-run`. The restored home contains read-only directories (`dr-xr-xr-x`, e.g. `clients/luxewave/inbox/extracted/Shopify-Luxewave/Logo/Fnl`), and GNU `rm -rf` **cannot unlink the children of a directory without owner-write** → it printed `Permission denied` for those files, kept the sandbox, and still exited 0 (found 2026-09-13: 7.3M left behind per run, invisible because the drill still reported "11 passed, 0 failed"). `restore_drill.sh` now chmods the tree writable first (`rm_rf()` helper: `chmod -R u+w` → `rm -rf` → `sudo -n rm -rf` fallback → warns if anything survives). Same trap for any cleanup of restored/backed-up trees: `rm -rf` exit 0 is NOT proof of deletion — verify with `[ -e ]`.
5b. **`python3 ops/verify/tests/test_sentinel_backup.py`** → offline unit test of the alarm logic (shims BOTH shell helpers `sh()` **and** `sh_rc()` plus the alert flag, touches no Drive; 16 asserts, ~0.06s): healthy = 0 alerts, > `KEEP_REMOTE` remotes = rotation warning, low free space = quota warning, newest missing + job idle = off-VM warning, `rclone about` failure alone = silent, **newest missing + job in flight = silent** (`backup_upload_in_flight` logged), **≥2 nights behind + in flight = still alerts**, unit FAILED + newest missing = alerts. **Fixture trap worth remembering:** the first version shimmed only `sh()`, but the remote listing and the quota probe go through `sh_rc()` — so the "fake" Drive was never used and every case was silently hitting the REAL Google Drive (slow, and it made the in-flight cases pass for the wrong reason). If a *fake* makes no Drive-related assertion fail, prove the fake is actually on the path (`sh_rc` returns `(rc, out, err)`). Run it after any edit to `check_backups()` — and remember the once-per-day flag: a live sentinel run can look "green" simply because today's alert was already fired (`rm ~/ops/observability/backup_alert.flag` to force a fresh evaluation).

5c. **`python3 ops/verify/tests/probe_sentinel_backup.py`** → the LIVE-box counterpart (real `/proc`,
    real `systemctl`, real rclone listings; redirects the alert-flag path to `/tmp` so today's real
    flag survives). Exit 0 = "the next tick will be silent", 1 = "the sentinel would alert" (then look
    at the names/`nights_behind` it printed), **2 = a probe is lying** (e.g. `push=True` while
    `pgrep -x rclone` sees nothing → the process check is self-matching). Run this after ANY change to
    `check_backups()`: the unit test replaces `sh()`, so it structurally cannot catch a probe whose
    *shell command itself* is broken — which is exactly how the `pgrep -af` self-match reached a live
    sentinel run on 2026-09-15. Unit test = logic, live probe = the shell and the box.

5d. **`bash ops/tests/backup/run.sh`** → backup-script regression suite (added 2026-10-03): `bash -n`,
    the WordPress-dump block under shims (the optional leg whose unguarded `VAR=$(docker exec wp-db …)`
    aborted the 02:30 run → 36h stale archive), and the 06:30 safety-net decision block (full build /
    upload-only repair / quiet no-op). Exit 0 = all green. It extracts both blocks from the live
    `backup.sh` by pattern, so it can never drift from the shipped code.
6. Health alarm: `infra_sentinel.py` `check_backups()` — newest archive > 30h old, < 100MB, archive count > 6, off-VM copy missing, or `systemctl is-failed sanad-backup` → alert (max once/day **per problem-set** — `date|sha1(problems)` stamp — so a known gap stays quiet but a changed failure still alerts; a probe that could not list Drive is reported as UNVERIFIED with its error text, never as "missing").

## Crash-proof reboot (kernel updates, infra changes)
Agent can NEVER run `sudo reboot` (unconditional blocklist — by design). Crash-proof pattern:
backup verified → firewall persistence diff → services enabled → install post-boot verification
service → hand `sudo reboot` to user → next session reads the check log. Full checklist +
service/script in `references/crash-proof-reboot.md`.
