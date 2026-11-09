---
name: vm-disk-cleanup
description: Use when a cloud VM disk is full or cleanup is requested.
version: 1.0.0
author: Hermes
metadata:
  hermes:
    tags: [devops, vm, cleanup, disk, storage, oracle-cloud]
---

# VM Disk Cleanup (safe storage reclaim)

User asks "check what are spam/trash/useless files in VM" or disk >85% full. Two-phase:
**AUDIT first (no action)** — user ka "no action first advice" mode = sirf report; phir **EXECUTE** sirf user-approved scope ke liye.

## Phase 1 — Audit (read-only)
```bash
df -h /                                  # overall pressure
du -sh /home/ubuntu/* | sort -rh | head  # top-level suspects
du -sh /home/ubuntu/.* | sort -rh | head # hidden dirs (.local/.cache/.npm...)
du -sh /var/cache/apt /var/log; journalctl --disk-usage
docker system df                          # reclaimable images/volumes
find /home/ubuntu -maxdepth 3 \( -name "*.tar.gz" -o -name "*.zip" -o -name "*.deb" -o -name "*.log" \) | head
```
Break down big dirs (`~/.local/*`, `~/.hermes/*`, `~/.cache/*`) before advising.

**CRITICAL — process check before ANY delete candidate:**
```bash
ps aux | grep -E "<candidate path>" | grep -v grep
systemctl --user list-units | grep -i hermes   # hermes-worker-proc_* scopes
```
Hermes worker scopes run site preview servers **FROM /tmp** (e.g. `cd /tmp/aslove_staging && python3 -m http.server 8931`). Deleting a /tmp dir a worker is serving breaks the site silently — process keeps running but requests 404. Restore source = `~/backups/*-pre-deploy-*` if present.
Reusable guard: `scripts/clean-tmp-safe.py` (dry-run default; skips anything referenced by a live process, keeps `.X11-unix`/`.ICE-unix`/systemd-private, `--cut-days` default 2).

**The same rule applies before KILLING a process to free RAM** — host `ps` shows container processes too. 2026-09-15 pid 2832 looked like a stale duplicate uvicorn (no listening socket of its own, 587MB resident-in-swap) → `/proc/2832/cgroup` showed `.../docker-<id>.scope` = **open-webui's own main process**. `cat /proc/<pid>/cgroup` (+ `docker inspect` the scope's container) is the ground truth for ownership; killing without it kills a running client container.

**Safety grep before deleting model/dependency dirs:**
```bash
grep -rl "<path>" ~/.hermes/config.yaml ~/.hermes/skills ~/.hermes/scripts ~/ops
```
Empty = no skill/connector reference = safe. Also `ps aux | grep <binary>` for live loaders.

## Phase 2 — Tiering (report to user, no action)
- **Tier 1 — safe/regenerable:** `npm cache clean --force`; `rm -rf ~/.npm/_npx` (npx cache, often 400M+); `uv cache clean` (binary ~/.hermes/bin/uv; cache ~/.cache/uv — **~/.local/share/uv = real installs (tools/ + python/), never touch**); `rm -rf ~/.cache/huggingface`; `apt clean`; `journalctl --vacuum-size=20M`; stale /tmp venvs (skip any with live process).
- **Tier 2 — conditional (confirm first):** downloaded ML models (`~/models` GGUF etc. — verify no refs), local TTS models (`~/.local/share/tts/xtts_*`), `docker system prune` dangling images (running containers untouched). These are the BIG wins (GBs).
- **Tier 3 — in use, never:** `.hermes` core + state.db, `~/.local/lib/node_modules` (global npm backing live services: caveman/omniroute/n8n/netlify), venvs of running services (openviking etc.), `clients/`, `ops/`, `sanad-site/`, running containers, `certbot-venv` if `systemctl list-timers | grep certbot` active (SSL renewal connector).

## Phase 3 — Execute + verify
- Delete EXACTLY the approved scope. State what you're keeping and why.
- `df -h` before/after.
- Connector health sweep after: `systemctl is-active` for caddy/n8n/caveman/switchyard/omniroute/openviking/luxewave/docker + **`systemctl --user`** gateways (hermes-gateway*, hermes-serve, signal-cli) + `docker ps` + curl any preview sites that were running (expect 200).

**Full-listing audits** (Aamir's "occupied space list out karo"): run `scripts/disk-audit-scan.sh` → ground-truth evidence in `/tmp/audit/` (home/hermes/profile/skills/top-files/tmp/var/docker). Parse those files into a timestamped artifact (`~/ops/space-audit-YYYY-MM-DD.json` + `.md`) programmatically — never from transcript memory.

## Cleanup ≠ Speed — imposter-fix guard (2026-09-15)
A cleanup request frequently arrives **bundled with a slowness complaint** ("phir bhi infra slow hai — irrelevant files/cache delete karenge?"). Answering only the disk half is the failure mode: the user deletes, feels nothing, loses trust. Order of operations:
1. **Measure the bottleneck BEFORE deleting anything.** Host triage (skill `saas-performance-diagnosis` → Step 0.7 / `scripts/host-triage.sh`). Disk ≥20–30% free + `vmstat` `wa` ≥40% with `us` ≤15% + non-zero `si/so` ⇒ the box is **memory-bound**; cleanup cannot fix that.
2. **State it plainly in the same message as the reclaim report**: "cleanup = hygiene, ~0 speed gain here" — then give the real cause and the remedy ladder.
3. Still do the safe Tier-1 reclaim, but route every probe to a file (`~/ops/logs/*.txt`, `/tmp/audit/`) and re-derive numbers by reading those files — never quote from the transcript.
4. List explicitly what you did **NOT** touch and why (backups ~9.5G, docker images in use, `__pycache__`, venvs, "no service was stopped or killed").
Worked case, numbers, and the framing that landed: `references/cleanup-vs-speed.md`.

## Mail spam alongside disk (Gmail via himalaya, 2026-09-15)
"Caches **aur** spam delete karo" = two jobs; the mail half is triage, not `--permanent` on everything.
```bash
export PATH=$PATH:$HOME/.local/bin
himalaya envelope list -a gmail -m "[Gmail]/Spam"        # READ each suspicious uid first
himalaya message read -a gmail -m "[Gmail]/Spam" <uid> > /tmp/audit/m<uid>.eml   # to file, never to stdout
himalaya message move -a gmail -f "[Gmail]/Spam" -t INBOX <uid>          # rescue: form leads/subscribers
himalaya message delete -a gmail -m "[Gmail]/Spam" <uids…>               # spam -> Trash (reversible)
himalaya message delete -a gmail -m "[Gmail]/Trash" <uids…> --permanent  # purge test artifacts
```
- Bounce reports (`Undeliverable`, To: = our own address) are **list hygiene data, not spam**: grep `X-Failed-Recipients`/`Final-Recipient` into a suppression file (`~/ops/cold-email/suppression.txt`), then delete the mail.
- Form submissions (FormSubmit website enquiry / email-gated download) misfiled as spam ⇒ **move to INBOX**, never delete.
- Gmail `-f`/`-t` go through the alias map but unmatched names pass verbatim, so raw `INBOX` / `[Gmail]/Spam` work. Deleted-from-Trash = permanent; that is the point of step 2.
- Purge by uid list: `himalaya envelope list … | awk -F'│' 'NF>2 {gsub(/ /,"",$2); if ($2 ~ /^[0-9]+$/) print $2}'`.

## After every sweep — kill the REGROWTH (2026-09-21)
Sep-15 sweep 97G pe khatam hua; Sep-21 tak wapas 131G — wahi levers dobara bhar gaye. Jo cleanup 6 din me wapas bhar jaye woh cleanup nahi, churn hai. Order:
1. **Filler dhoondo, delete se pehle.** `du -xBM -d1` usual suspects pe + har backup/snapshot job ki apni retention padho:
   `grep -nE "KEEP|retention|rotate|snapshots" ~/ops/backup.sh ~/ops/scripts/state-db-maintenance.py`
   Real case: `state-db-maintenance.py` me `KEEP_SNAPSHOTS=7` × ~2G default state.db = ~17G **rolling churn** — yahi asli wajah thi ke disk 6 din me 68% pe laut aayi.
2. **Policy align karo, churn se ladо nahi.** `KEEP_SNAPSHOTS=3` + `KEEP_REPAIR_DIRS=2` (newest hamesha bachta hai → zero data-loss risk). Docstring bhi update karo taake change self-documenting rahe. `~/ops/backup.sh` ki `KEEP_LOCAL=3` jaan-boojh kar chhori (sanad archive ~3.5G/tar, ~10G rolling = 193G disk pe affordable) — report me bataya.
3. **Retention change ko sandbox-test karo**, hand-edited keep-count pe bharosa nahi: module import karo, `NIGHTLY`/`BACKUP_ROOT` tmpdir pe monkeypatch, fake snapshot naam banao, `prune()` chalao, assert karo exactly N newest + N repair dirs bache aur purane gaye. Recipe + pa poora check-list: `references/post-cleanup-selfqa.md`.
4. Change ke **baad** canonical QA dobara: `~/ops/verify/daily_selfqa.sh` (exit 0) + apna deterministic verifier (`~/ops/verify/cleanup_selfqa_<date>.py`).

## Pitfalls
- **Never sweep `*.exe`/`*.dll` out of global `node_modules` by extension.** `@anthropic-ai/claude-code` ships its Linux binary as `bin/claude.exe` (its npm `bin` map: `"claude": "bin/claude.exe"`), so an "unusable Windows binary" pass deleted the live `claude` CLI (symlink in `~/.local/bin` broke, 203M freed → net 0). Check `grep -A3 '"bin"' <pkg>/package.json` first. Recovery: `npm i -g <pkg>@<exact-version> --force` (get the version from the package.json BEFORE deleting). Genuinely-unused win32 payloads (onnxruntime-node `win32/*` dlls, `agent-browser-win32-*.exe` while `linux-arm64` exists) are safe.
- **Byte-identical big files: hardlink, don't delete.** Two 6.4G copies of the same safetensors (e.g. `uocr/model_dl/…` vs `uocr/kaggle_dataset/…`) → `md5sum` both, then `ln -f A B` ⇒ same inode, both paths keep working, full copy freed. Verify `stat -c '%h %i %n' A B` shows links=2 + one inode. Prefer this over deletion when either path may be referenced.
- **`lsof +L1` size column lies for sparse/memfd files.** A `.NET` process (devtunnel host) held `/memfd:doublemapper` reported as ~11.9G; `stat -L -c '%s %b %B'` showed 48,200 blocks × 512B = **24MB actual**. Always read `blocks`, not `size`, before blaming/pkill-ing a process for "holding N GB".
- **`fuser -m <path>` is useless here** (it lists every process using the *filesystem*). Use `lsof +D <dir>` (or `lsof | grep <dir>`) per candidate and require an empty result before `rm -rf`.
- **Same-day state-db repair artifacts**: `/tmp/state-db-repair-*/src.db` may be a byte copy of the corrupt DB already preserved under `ops/backups/state-db/state-db-repair-*/corrupt/`. Verify identity (`md5sum` both) → then the /tmp scratch is safe to delete, while the preserved `state.db.corrupt` of the SAME day stays (crash evidence).
- **`docker system df` overstates reclaimable**: after removing an unused child image it reported 9.77G reclaimable (98%) because the figure counts layers shared by ACTIVE containers; the real gain from `eval-workday-calc:latest` was 0B. Only trust `docker image prune -a --dry-run` against known-unused tags.
- **Superseded backups: verify the newer copy exists, then delete** — nightly state-db keep newest 2 + newest repair pair per profile; `sanad-backup-*.tar.gz.gpg` keep newest 2; old `state-snapshots/*-drill` only when newer nightly backups exist. Say which copies remain in the report.
- **Long/multi-line shell commands get elided in this harness** (result comes back as "… -> exit 0, 1 lines output"): write output to a file (`> /tmp/audit/x.txt`) and read it back with `read_file` instead of piping to stdout.
- **`du -s` + `--max-depth=N` = conflict error + EMPTY output** (`du: warning: summarizing conflicts with --max-depth=1`). For full listings use `du -xBM --max-depth=1 <dir>` — drop `-s`; `-x` keeps to one filesystem; MB = MiB (1M blocks).
- **Plain du lies about root-owned dirs**: unprivileged runs can't traverse `/var/lib/docker` etc. → `/var` may show ~1.6G while the real total is 13G+. Cross-check `df -h` used vs your du sums; any gap → `sudo du -xBM -d1 /var /var/lib/docker /var/lib/containerd`.
- **Docker on containerd image store**: modern engines keep image layers in `/var/lib/containerd`, NOT `/var/lib/docker/overlay2` — `/var/lib/docker` can be ~2G while `docker system df` claims ~10G images. Detect: `sudo ls /var/lib/docker` shows no overlay2 dir → `sudo du -xBM -d1 /var/lib` to find where the GBs actually live.
- **`docker system df` reclaimable % is optimistic** (often ~98%, counts dangling old builds/untagged snapshots). Confirm exact scope with `docker image prune -a --dry-run` before pruning anything.
- **Never quote audit numbers from memory or transcript** — compaction strips exact byte values and recalling them invites fabrication. Re-run scans into evidence files (`/tmp/audit/*.txt`), then generate the JSON/MD artifact by PARSING those files programmatically; final QA = re-run 2–3 spot du/docker commands and compare vs the artifact.
- **Duplicate big-file check before flagging reclaimable**: `cmp -s a b && echo IDENTICAL` — e.g. two 6.4G safetensors copies confirmed byte-identical before recommending deletion of one.
- **Top files by size**: `find /home/ubuntu -xdev -type f -size +20M -printf '%s\t%p\n' | sort -rn | head -30` (bytes → convert).
- Hermes gateways = user-level units — `systemctl status hermes-gateway-X` at system level returns EMPTY; check `systemctl --user`. Don't report a connector dead when it's just user-scoped.
- aslove_staging incident (2026-08-25): deleted live-served /tmp dir → 404 → restored from `~/backups/aslove-pre-deploy-20260824-121715`. Always process-check /tmp first.
- "Recommended wala kardo" = execute Tier 1 + the biggest Tier 2 item, nothing more.
- Oracle bloat services (ModemManager, fwupd, iscsid, unified-monitoring-agent) waste RAM, not disk — not cleanup targets.
- Bash history — trivial, optional.
- **`__pycache__` — never delete it chasing speed**: it regenerates on the next import, so the deletion is a one-off stall that makes the next run *slower*, not faster. Only worth it in a genuine disk emergency.
- **Fix the emitter BEFORE vacuuming its logs**: a wedged/crash-looping unit refills `/var/log` within hours (438M of `syslog.1` in ~2 days here). `journalctl --vacuum-size` + deleting rotated logs is step 2; step 1 is silencing the loop (skill `infra-hardening-crashproof` → Gateway Crash-Loop).
- Oracle Always Free ARM is at **4 OCPU / 24GB** tenancy-wide while the main box runs 2/12 — "buy more" is not needed to fix a RAM-starved box; see `oci-cloud-vm-ops`.
- **logrotate chup-chaap abort = hidden filler.** `logrotate.service` 17 Sep se **failed** tha: `/etc/logrotate.d/hermes-ops-logs` me `su ubuntu ubuntu` tha par log files root-owned → har run "Permission denied" pe pura rotation chhod deta (kuch bhi rotate nahi). Fix: `su root root` → `sudo logrotate -d <conf>` (dry) → `sudo logrotate -f <conf>` → `sudo systemctl reset-failed logrotate.service && sudo systemctl start logrotate.service`. Syntax sweep: `sudo logrotate -d /etc/logrotate.conf 2>&1 | grep -iE "error|unknown"`. (`systemctl list-units --failed` hamesha shamil karo audit me — failed units disk/logs silently bharte hain.)
- **Ollama model delete ka gain blob-sharing pe depend karta hai.** `qwen2.5:7b` aur `qwen2.5:7b-64k` same 4.68G blob set share karte hain → sirf ek hatane se **0 bytes** mile; dono hatane se 4.7G. Decide se pehle map: `python3 scripts/ollama-blobmap.py` (per-tag unique vs shared bytes, aur kisi manifest se referenced na hone wale orphan blobs). Delete: `curl -sX DELETE localhost:11434/api/delete -d '{"model":"<tag>","name":"<tag>"}'` (dono keys), 5s baad `ollama list` se confirm.
- **Hardlink dedupe ka gain claim karne se pehle `stat` karo.** `stat -c '%i links=%h %n' A B` — links already 2 = pichla pass hi hardlink kar chuka, naya gain **0**. Is session me "6.2G duplicate safetensors" ka asli reclaim 0 tha (inode 4472504, links=2). Restore bhi dekho: agar koi path delete ho gaya ho to `ln -f` wapas nahi bana sakta — pehle `cmp -s` chalao.
- **Chrome regenerable cruft (NON-live profiles) — safe list**: `scoped_dir*` (har launch pe nayi random dir, purani kabhi delete nahi hoti — 538M tak jama hui thi), `Default/Service Worker/CacheStorage`, `component_crx_cache`, `WasmTtsEngine`, `optimization_guide_model_store`, `OnDeviceHeadSuggestModel`. Identity/logins (`Login Data`, `Cookies`, `Preferences`, `Local State`) aur live automation profile (CDP 9333) kabhi touch nahi karo — warna logins/automation toot jate hain.
- **Mail Trash purge irreversible hai.** Personal / job-application threads Trash me pade ho to default = **chhoro**, report me count batao aur poocho (human decision). Spam folder khali hona bhi valid finding hai — delete karne ke liye kuch nahi. `himalaya envelope list -m "[Gmail]/Trash" -s 100 > file` se count nikaalo (alias map ke bina bhi raw mailbox naam chalta hai).
