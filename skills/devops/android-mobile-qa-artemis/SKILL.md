---
name: android-mobile-qa-artemis
description: Use when QAing Android apps or phone UI automation.
version: 1.0.0
author: Hermes
license: Apache-2.0
metadata:
  hermes:
    tags: [android, qa, mobile, artemis, redroid, adb, mcp]
    related_skills: [app-store-distribution, dogfood, computer-use, headless-browser-automation]
---

# Android / Mobile QA with Google ARTEMIS (+ redroid device lane)

## When to Use

- A task needs **real phone UI automation**: install-and-smoke an APK, walk a signup/checkout flow,
  verify deep links, screenshot-verify a build, or reproduce a mobile-only bug.
- Before shipping an Android build to a store and you need device evidence (see `app-store-distribution`).
- When someone says "test/QA the mobile app", "check the phone UI", "does it work on Android".

ARTEMIS is a Google OSS multimodal Android agent (screenshot + tool calls via Gemini) driven by an MCP
server, so Hermes can call it as a tool. Do not attempt the stock Android emulator on this VM (see
Pitfalls: no `/dev/kvm`).

## Why this lane exists

Our VM (`VM.Standard.A1.Flex`, ARM64, no `/dev/kvm`) **cannot run the stock Android emulator**
(x86_64 emulation needs hardware acceleration). It **can** run `redroid` — Android-in-Docker, native
ARM64, no KVM — because the host kernel ships the `binder_linux` module.

## Prerequisites (already installed on this VM, verify before assuming)

```bash
grep -c binder /proc/filesystems            # 1 => binder module loaded (else: sudo modprobe binder_linux devices="binder,hwbinder,vndbinder")
ls ~/projects/artemis/.venv/bin/artemis     # ARTEMIS venv (uv-managed, Python 3.12)
adb version                                  # Android Debug Bridge 1.0.41+ required
```

Repo: `~/projects/artemis` (clone of `github.com/google/artemis`). Env file `~/projects/artemis/.env`
holds `GOOGLE_API_KEY` (Gemini multimodal = the phone operator; every task costs Gemini tokens).
Wrapper + device scripts live in `~/ops/artemis/`.

## Steps

### 1. Start the device lane (no KVM)

```bash
~/ops/artemis/redroid-start.sh        # creates/restarts container redroid-qa, waits for boot, prints Android version
```
- Image `redroid/redroid:13.0.0-latest`, `--privileged`, memory capped by `REDROID_MEM` (default `2g`),
  adb published on **127.0.0.1:5555 only**.
- Adb: `adb connect 127.0.0.1:5555` → `adb devices` must show `device`.
- Boot check: `adb -s 127.0.0.1:5555 shell getprop sys.boot_completed` → `1`.
- Stop when idle (memory is tight on this VM): `~/ops/artemis/redroid-stop.sh`.

### 2. Readiness + helper APK

```bash
cd ~/projects/artemis && export PATH="$HOME/.local/bin:$PATH"
uv run artemis doctor                 # expect: LLM key OK, Device/Emulator OK
uv run artemis helper install         # installs ArtemisAccessibilityHelper.apk + enables the service
uv run artemis helper status          # Installed yes / Service answering yes
```
`uv run artemis helper parity` dumps the screen with helper vs UIAutomator2 and compares — use it when
the helper looks stale after a device restart.

### 3. Run a task (CLI)

```bash
uv run artemis run "Open the Settings app, open About phone, report the Android version and model"
```
Runs take 2-6 min. Verify progress **with evidence, not vibes**:
```bash
adb -s 127.0.0.1:5555 shell "dumpsys window | grep -i mCurrentFocus"   # which app is in front
adb -s 127.0.0.1:5555 exec-out screencap -p > /tmp/phone.png            # atomic screenshot proof
docker stats --no-stream redroid-qa                                     # container alive, <2GiB
```

### 4. Hermes tool access (MCP)

Registered as stdio MCP server `artemis` via `~/ops/artemis/mcp-stdio.sh` (cd into repo, source `.env`,
exec `.venv/bin/python -m mcp_server`). Tools: `mobile_run_task`, `mobile_manage_task`,
`mobile_get_device_state`, `mobile_inspect_trace`, `mobile_diagnose`.
Re-register non-interactively (the prompt cancels otherwise):
```bash
printf 'y\n' | hermes mcp add artemis --command /home/ubuntu/ops/artemis/mcp-stdio.sh
hermes mcp list && hermes mcp test artemis
```
Newly added MCP tools only appear in a **new** Hermes session.

### 5. Focus hygiene BEFORE any app-launch task (the #1 cause of "foreground: None")
Redroid can leave the **notification shade / a stuck overlay holding window focus**. ARTEMIS's
`launch_app` polls the foreground package, never matches, retries and fails with
`Timeout waiting for app to reach foreground` → `Current foreground: None`.
```bash
~/ops/artemis/qa_smoke.sh preflight     # asserts boot_completed=1 + collapses shade + reads mCurrentFocus
```
Healthy output ends with `mCurrentFocus=Window{... com.android.launcher3/...QuickstepLauncher}`.
Manual fix: `adb -s emulator-5554 shell cmd statusbar collapse && adb -s emulator-5554 shell input keyevent KEYCODE_HOME`.
`qa_smoke.sh preflight|run "<task>" [timeout_s]` also runs tasks from a log under `~/ops/artemis/logs/`
so a dead agent process can't leave the device locked.

### 6. Register the lane with every coding agent (the post's actual claim)
```bash
~/ops/artemis/register_mcp_all.sh       # idempotent; writes + verifies all five
```
| agent | config written | verify |
|---|---|---|
| Claude Code | `claude mcp add --scope user artemis …` | `claude mcp list` → `artemis ✓ Connected` |
| Codex CLI | `~/.codex/config.toml` `[mcp_servers.artemis]` | `codex mcp list` |
| OpenCode | `~/.config/opencode/opencode.json` → `mcp.artemis` | `opencode` → MCP panel |
| Cursor | `~/.cursor/mcp.json` | Cursor → Settings → MCP |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | Windsurf → Cascade → MCP |
Antigravity uses the same `mcpServers` JSON shape — paste the same block.

### 7. Real-phone lane (HONOR X7c 5G) over Tailscale — verified 26-Sep-2026
Redroid has no GMS, so store/login flows need the physical phone. Endpoint: **`100.78.185.51:5555`**
(tailnet peer `honor-x7c-5g`), model `ALT-NX1`, Android 15, USB serial `A66GBB5518901001`.
Run a task: `bash ~/ops/artemis/run_phone_qa.sh 100.78.185.51:5555 "<task>" 900` (see
`~/ops/artemis/PHONE-LANE.md`). Watchdog: cron `phone-lane-watchdog` (*/10, `no_agent`, silent on pass)
→ `~/.hermes/scripts/phone_lane_check.sh`.

**Do NOT waste time on `adb pair` over Tailscale.** The *wireless-debugging pairing service* does not
listen on the VPN interface: a full 1024-65535 scan of the phone while the pairing dialog was open
showed only adbd's own TLS port (43445), never the pairing port — every `adb pair` fails with
`Failed: Unable to start pairing client.` (adbd itself binds all interfaces; the pairing service does
not, so `adb connect` reaches the phone and then answers `unauthorized`.) A watcher that re-scans every
~20 s for 15 min confirms it; don't re-litigate this.

Working recipe (needs a USB host once — Aamir's Windows laptop `msi`):
1. Phone: Developer options → USB debugging ON → cable → tap **Allow** (`Always allow`) → `adb devices` = `device`.
2. On the USB host: `adb tcpip 5555` (phone's adbd starts listening on all interfaces).
3. Copy that host's adb key to this VM and authenticate with **vendor keys** (keeps our default key intact
   for the redroid lane):
   ```bash
   mkdir -p ~/.android/vendor_keys && cp <uploaded>adbkey ~/.android/vendor_keys/msi_adbkey
   cp <uploaded>adbkey.pub ~/.android/vendor_keys/msi_adbkey.pub
   tr -d '\r' -i ~/.android/vendor_keys/msi_adbkey*      # CRLF kills adb's key parser → silent unauthorized
   export ADB_VENDOR_KEYS="$HOME/.android/vendor_keys"
   adb connect 100.78.185.51:5555                        # → "connected", devices: <ip>:5555 device
   ```
   Key transfer trick that keeps secrets out of chat: serve the file from the VM over the tailnet
   (`python3 -m http.server <port> --bind <vm-tailnet-ip>`) and `curl.exe -o` it on the laptop, then
   `scp -i <key> ... ubuntu@<vm-tailnet-ip>:/tmp/` back up. Chat redaction makes pasted keys unusable.
4. Keep the screen awake before/while driving it: `adb -s <ser> shell input keyevent KEYCODE_WAKEUP`,
   `svc power stayon true`, `settings put system screen_off_timeout 1800000` (AOD focus = task stalls).
5. Target it explicitly: `ARTEMIS_SERIAL=<ser> ARTEMIS_DEVICE_ID=<ser> ADB_DEVICE_SERIAL=<ser>`.
   **Pitfall:** `qa_smoke.sh` uses `SERIAL="${ARTEMIS_SERIAL:-emulator-5554}"` — forget these three and the
   "phone" run silently drives the emulator (preflight still prints `ANDROID: 13`). Sanity check: preflight
   must print `ANDROID: 15` and a `com.hihonor.*` focus.
6. Evidence per run: `run_phone_qa.sh` wraps `qa_smoke.sh` and writes
   `~/ops/artemis/evidence/<UTC-stamp>/` = `REPORT.md`, `00_start.png`, `99_end.png`, `video.mp4`,
   `run_outcome.json`, `check_ledger.jsonl`, `check_streams.jsonl`, `notes/`, `stdout.log`
   (evidence video = PNG frames -> mp4 via `qa_evidence.py`; `screenrecord` fails
   `unable to start codec (err=-12)` while ARTEMIS holds the encoder, so the lane passes
   `ARTEMIS_EXTRA_ARGS=--without-video-recording-tools` and captures with `screencap` instead).
   Speed: repo default `agent.flash.max_turns = 0` (unlimited) → 15-min grinds; set 15 in
   `~/.config/artemis/artemis.jsonc`, and keep `artemis-daemon.service` (systemd `Restart=always`) warm.

**ARTEMIS video traces need scrcpy ≥ 3.x.**

**Speed + safety knobs (measured 2026-09-26):**
- `artemis run` defaults to `--profile pro` (~6-15 min/run). Force `--profile flash` for the fast lane
  (~1.5-3 min); narrow single-fact tasks behave best.
- `--locked-app <package>` pins the agent to one app — without it a run tapped a notification and landed
  inside a messaging app mid-run. Lock `com.android.chrome` for web cases, `com.android.settings` for system ones.
- Suites: `qa_suite.py suites/<file>.json` (per-case `package`/`profile`) -> `SUITE_REPORT.md` + one bundle per case.
- Client deliverable: `qa_report.py <bundle|suite_dir>` -> A4 PDF (Chrome `--headless=new --no-pdf-header-footer --print-to-pdf`).
- Orphaned sessions keep running after you kill the wrapper: `sudo systemctl restart artemis-daemon` to clear them.
- Prefer the MCP path when driving from an agent: `mobile_run_task(task_desc, model="Pro",
  verification_level="checkpoints", expected_output_desc=..., device_serial=...)` → `notes/output.md` report. Ubuntu's 1.25 server dies on Android 15
(`NoSuchMethodException: SurfaceControl.createDisplay` and
`IClipboard$Stub$Proxy.addPrimaryClipChangedListener`) → every trace `recording.mkv` was 0 bytes.
Fix in place: scrcpy **3.3.4** built from source for arm64 (SDL2) at `/opt/scrcpy-3.3.4/` with the v3.3.4
release `scrcpy-server` next to the binary; `~/.local/bin/scrcpy` execs it (no flag translation).
Build: `meson setup build --buildtype=release && ninja -C build app/scrcpy` — skip the `server/` target
(needs gradle); download the prebuilt server asset instead.

Caveat: a phone **reboot** reverts adbd to USB-only → re-run step 2 from the laptop's `platform-tools`.
Legacy helper `~/ops/artemis/phone_connect.sh check` still lists tailnet nodes + adb devices.

## Pitfalls

- **No `/dev/kvm`** → do not attempt `sdkmanager`/`emulator`/AVD; it fails with "x86_64 emulation
  currently requires hardware acceleration". redroid is the workaround; ARM64 host must match the
  image arch (tags are multi-arch — check with `docker manifest inspect`).
- **`--privileged` is required by redroid** (binder devices). Bounded by: loopback-only adb port,
  memory cap, on-demand start. Never publish 5555 on a public interface.
- Memory: container sits ~1.0-1.1 GiB at idle. This VM runs many services — start redroid per task,
  stop it after. Watch `free -m`; zram is usually near full.
- Port **8000** is taken by another service on this VM (`geo-auditor`) → the ARTEMIS daemon/web UI
  warns "Port 8000 is held". Fixed here: `ARTEMIS_DAEMON_PORT=8092` in `~/projects/artemis/.env` **and**
  at the top of `~/ops/artemis/mcp-stdio.sh` (a new Hermes session picks the env up; the MCP stdio path
  itself opens no port).
- **Free-tier Gemini 429/503:** a long task will hit `Too Many Requests` (retryDelay ~7s) and 503
  "high demand". ARTEMIS retries internally, so the wall-clock cost is what kills the run, not the
  error. Budget **≥900 s** for a 3-step task (`qa_smoke.sh run "<task>" 900`) and keep tasks atomic.
- **Free-tier Gemini is ~20 requests/day PER MODEL** — a task burns 9-14 calls, so one long run can
  exhaust the default (`gemini-3.8-flash` / `gemini-3.7-flash` die first) and the run then hangs on
  `Pausing execution to wait for resume signal...` instead of failing. Check and rotate:
  `python3 ~/ops/artemis/model_quota_probe.py` (per-model OK/EXHAUSTED, cheapest-first; `--best` prints
  one model name). **`ARTEMIS_DEFAULT_MODEL` does NOT win over the loaded jsonc** — proved 26-Sep-2026:
  env said `gemini-3.5-flash-lite` while the log kept showing `"model": "gemini-3.7-flash"` at 429. The
  working lever is `python3 ~/ops/artemis/set_model.py <model>`, which rewrites `default.model` in
  `~/.config/artemis/artemis.jsonc` (comments preserved, one `.bak`); `qa_smoke.sh run` now calls
  probe→set_model automatically (disable with `ARTEMIS_SKIP_MODEL_ROTATE=1`). The 429 body names the
  limit exactly: `quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier`, `quotaValue: 20`.
  `gemini-2.5-flash` / `gemini-2.0-flash` are 404 on this key (retired for new users).
- `scrcpy` 1.25 (Ubuntu jammy) rejects ARTEMIS's 2.x flags (`--no-window`) → every run logged
  `Failed to start scrcpy segment: scrcpy: unrecognized option '--no-window'`. Fixed with a shim at
  **`~/.local/bin/scrcpy`** (first on PATH): `--no-window`→`--no-display`, `--video-bit-rate V`→
  `--bit-rate V`, `--capture-orientation=@` dropped; pass-through when the real binary is ≥2.x.
  Verified: recording redroid for 12 s wrote a playable matroska file (`Recording started to matroska
  file`). Don't install via snap here (the snap install hung >5 min on this VM).
- `scrcpy` present → the diagnose "optional video toolchain" warning is
  cleared; screen recording of a QA run is available.
- `notify-send` is missing on the headless VM → desktop notifications are silent by design.
- Redroid has **no Google Play Services / accounts**: GMS-dependent flows (login, Maps, Play billing)
  cannot be tested here. For those, drive a real phone over adb (wireless debugging + reachable host).
- The MCP prompt `Enable all 5 tools? [Y/n/select]` cancels on non-interactive stdin: pipe `y`.
- **LLM hard timeout:** ARTEMIS aborts any single LLM call after 180 s → `TimeoutError: LLM call
  timed out after 180 seconds` on long/complex tasks (common on a busy free-tier Gemini key). Fixed
  here by an env knob: `ARTEMIS_LLM_HARD_TIMEOUT=420` in `~/projects/artemis/.env` (patch in
  `artemis/services/llm.py::_llm_hard_timeout_default`). Still keep each task short and atomic — one
  screen goal per task — and split long flows.
- **Cost:** every task spends Gemini multimodal tokens (screenshot per step). Batch steps into one
  task instead of many tiny runs.
- **Testing this repo:** use `uv run pytest tests/unit` (project venv). `hermes verify --json` inside
  `~/projects/artemis` reports `ok:false` on an interpreter mismatch (bare `pytest` with no
  `langchain_core`) even though its own `uv sync` bootstrap passes. Known pre-existing failures on a
  clean clone: `tests/unit/runtime/test_awake_service.py` and
  `tests/unit/test_unified_controller_video.py` (8 failed) — not caused by local patches; confirm with
  `git stash push -- artemis/services/llm.py` before blaming your change.
- Governance: surfaces are declared in `~/ops/observability/autonomy.json` —
  `artemis-mcp` (L4 internal-only, kind `container`), `redroid-qa-device` (L3 gate_required),
  `artemis-mobile-qa-lane (redroid + adb, honour-x7c optional)` (**L4 notify-owner, kind `cron`,
  `unit: artemis-lane-selfcheck`**). The audit only treats cron/systemd-timer/service/bot kinds as
  must-be-live, so a `container`/`service` entry with no matching unit is reported as a DEAD
  declaration — bind every new entry to a cron/unit that actually exists. Re-run
  `python3 ~/ops/scripts/autonomy_audit.py` after touching any of them (expect 0 block findings).
- **Continuous self-QA:** Hermes cron `artemis-lane-selfcheck` (03:45 UTC daily, `no_agent`) runs
  `~/.hermes/scripts/artemis_lane_selfcheck.sh` → lane check + focus hygiene + helper-APK presence;
  silent on pass, alerts this chat on failure. Monetization is gated on the same lane:
  `~/ops/verify/check_artemis_lane.py` is the `proof_check` of offer `android-app-qa-report`
  (gate re-run: `python3 ~/ops/monetize/offer_gate.py --spec offers.json --checks ~/ops/verify/checks-monetize.json --gate`).

## Verification checklist (done = all four)

1. `adb devices` shows the redroid device as `device`.
2. `uv run artemis doctor` reports Device/Emulator ✔ OK and LLM key ✔ OK.
3. `artemis helper status` → Service answering yes.
4. A task ran end-to-end and you hold a **screenshot + focus dump** as proof.
