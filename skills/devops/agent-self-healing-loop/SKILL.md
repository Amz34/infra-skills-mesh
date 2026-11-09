---
name: agent-self-healing-loop
description: Use when making an agent fleet self-healing or crashproof.
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [self-healing, crashproof, watchdog, systemd, cron, reliability]
    related_skills: [cron-watchdog, agent-autonomy-governance, infra-hardening-crashproof, hermes-cloud-vm-ops]
---

# Agent self-healing loop (crashproofing a VM agent fleet)

## When to Use

Use when asked to make agents "self-healing", "self-QA", "crashproof", to find and delete
broken agents, to review a vendor's self-healing agent feature, or to raise uptime of a
long-running agent fleet on a VM.

## The loop (four beats)

```
DETECT   -> every failure surface: cron jobs, declared-critical units, registry drift, lanes
CLASSIFY -> transient | auto_healable | needs_code_fix      (from the evidence TEXT)
HEAL     -> auto_healable fixed NOW (cooldown + 1 action/tick); nothing else is touched
DRAFT    -> needs_code_fix becomes a draft fix under ~/ops/selfheal/drafts/ - LIVE CODE IS
            NEVER MODIFIED AUTOMATICALLY; a human approves
STRIKE   -> >=3 consecutive failures -> auto-pause the surface, announce once
```

Reference implementation: `~/ops/scripts/self_heal.py` (stdlib only, `--dry-run`,
`--json`, `--selftest`, `--no-pause`), shim `~/.hermes/scripts/self_heal.sh`,
cron `every 15m` with `--no-agent` so **empty stdout = silent**.

## Non-negotiable design rules

1. **Silent when healthy.** A watchdog that talks every tick gets parked (that is exactly
   why `infra-sentinel` was paused on 16 Sep). Print nothing when there is nothing to say.
2. **Draft, never apply.** The vendor feature that impresses is "tests the fix before it
   reaches you, and never changes the live agent without approval". Keep that property.
3. **Throttle.** Per-surface alert throttle (~6h) + per-tick caps (1 heal, 3 drafts). One
   disruptive action per tick, never a restart storm.
4. **Cooldown heals.** Never restart the same unit twice inside ~15 min.
5. **Do not fight the operator.** A `masked` or `disabled` unit is an explicit human
   decision: report it, never unmask/enable it automatically.
6. **Change-driven reporting beats raw polling.** Wrap a chatty checker in a de-dupe shim
   that prints only new/changed condition lines (`~/ops/scripts/sentinel_cron.py`,
   state file `~/ops/observability/sentinel-alerts.state`).

## Crashproofing: the holes that actually bite

- `Restart=always` alone is NOT crashproof. Default `StartLimitIntervalSec=10s` +
  `StartLimitBurst=5` means a fast crash-loop gets **permanently** stopped
  ("start request repeated too quickly") and stays dead.
  Fix: drop-in `[Unit] StartLimitIntervalSec=0` (+ `[Service] Restart=always`,
  `RestartSec=3`, `OOMPolicy=continue`). Reference:
  `~/ops/scripts/apply_crashproof_dropins.py` (idempotent, verifies holes == 0).
- Property name trap: on systemd >= 229 read `StartLimitIntervalUSec` (0 == disabled).
  `systemctl show -p StartLimitIntervalSec` returns **empty** and will fool your checker.
  Also: `show -p A -p B --value` returns values in systemd's own order, not yours -
  query one property at a time.
- **The dead-unit trap:** a unit that hit the start limit is in `failed` and a plain
  `start`/`restart` is a no-op. Always `systemctl reset-failed <unit>` FIRST.
- A watchdog that dies takes its whole lane with it. Real example here: `infra-sentinel`
  was paused -> a dangling venv interpreter went unrepaired -> `Unlimited-OCR result
  watchdog` died with `No such file .../venv/bin/python` and got auto-paused at streak 3.
  Re-enable the meta-watchdog before trusting any downstream repair.

## Finding the broken agents (do this before building anything)

- `systemctl --user list-units --state=failed` + `--user list-unit-files` and compare
  against `critical_services` in `~/ops/observability/autonomy.json`.
  Declared scope is often WRONG (units declared `user` that are really system units ->
  the checker reports `not-found` and you "fix" a service that was never broken).
- `python3 ~/ops/scripts/autonomy_audit.py` prints `DEAD declarations` and
  `stale critical declarations` - that IS the dead-agent list. Do not re-implement drift
  matching; parse the auditor so the two layers can never disagree.
- Registry keys carrying a parenthetical suffix (`infra-disk-watch (disk watchdog,
  cron 05:00)`) never match the live name -> add an `aliases` list to the entry.
- Names contain commas: split declaration lists with a paren-aware splitter, not `.split(",")`.
- Cron store `~/.hermes/cron/jobs.json`: `enabled=false` + `failure_streak` + `paused_at`
  is the graveyard. Classify before deleting: broken (dangling interpreter), duplicate
  (another job/crontab entry does it), expired one-shot (date passed, 0 runs), superseded.
  Back up `jobs.json` first and print a restore hint. Reference:
  `~/ops/scripts/prune_cron_jobs.py`.
- Pruning jobs leaves DEAD registry declarations behind - re-run
  `python3 ~/ops/scripts/reconcile_autonomy.py --drop-dead` afterwards.
- Raw `crontab` entries are invisible to the governance auditor and fail silently forever.
  Migrate them to Hermes cron (`--no-agent` + a shim) so they get visibility, the
  3-strike pause and self-heal coverage. `hermes cron pause|resume|remove <job_id>` is the
  official path - do not hand-edit `jobs.json` for single-job changes.
- Hermes cron ALREADY has consecutive-failure auto-pause (default threshold 3,
  `failure_streak` in `jobs.json`). Check it before re-implementing it.

## Verify for real (do not stop at "script written")

```bash
python3 ~/ops/scripts/self_heal.py --selftest         # pure-function checks
python3 ~/ops/scripts/self_heal.py --dry-run --json    # full collection, no writes
# live heal proof: declare a throwaway unit, stop it, run the healer, expect
# "start <unit> -> active", then remove the unit AND its declaration.
bash ~/.hermes/scripts/self_heal.sh                    # must print NOTHING when healthy
```

Pitfalls found while building: `--dry-run` must not write drafts/state/logs (gate
`write_draft`, `save_json` and `log_event` on a module-level `_DRY`); the enabled-state
check for healability must be a deny-list (`disabled|masked|not-found`) - `static` and
`indirect` units are perfectly healable; registry drift belongs in ONE digest line, not
one draft per dead letter.

## Second pass: make the governance auditor clean, and retire without losing anything

- **Every lane checker must respect the operator's pause flag BEFORE it probes.** Real bug
  (2026-09-26): `~/.hermes/scripts/phone_lane_check.sh` probed tailscale/adb while the whole
  ARTEMIS lane was deliberately off (`~/.config/artemis/lane_paused`), cried "PHONE LANE DOWN",
  took 3 strikes and got itself auto-paused -> silently dead forever. Fix is three lines, as
  the FIRST thing after the PATH exports:
  `if [ -f "$HOME/.config/artemis/lane_paused" ]; then exit 0; fi`. Then `hermes cron resume`
  - it works again on its own, and resume at 08:11 reset `failure_streak` to 0 (verify that,
  do not assume).
- **An external-effect cron needs a REAL gate, not just a declaration.** Registry policy P2
  wants `gate_required: true` at L3 for an external effect, and the auditor then checks the
  job's script for `gate.py|gated.sh|...` (P4). Wire it fail-closed where the side effect
  happens:
  `if ! python3 ~/ops/verify/gate.py file site/index.html --min-bytes 40000 --contains X; then
  echo ALERT...; exit 1; fi` immediately BEFORE the publish command. Test the gate call by
  hand first so it is proven to PASS on a good artifact.
- **The auditor only reads the job's own script, and a Hermes shim is 3 lines of `exec`.** If
  the gate lives in the worker (`github_growth_daily.sh -> growth/daily_refresh.sh`) the gate
  is invisible and P4 fires. Fix the auditor, not the design: follow ONE delegation hop
  (`_delegated_bodies()` in `autonomy_audit.py`) and use that expanded text ONLY for the
  `gate_wired` check - keep `external_hint` on the shim so the other policies do not change
  meaning. After the patch, diff the audit output: exactly one finding should disappear.
- **`OBS` notes ("confirm it only writes locally") are lexical only.** Resolve them with
  evidence, not with silence: declare `obs_confirmed: "<date: what was scanned, what was
  found>"` and let the auditor re-check on every run with a HARD external-verb regex
  (`curl -X POST/PUT|wrangler|gh api|git push|requests.post|boto3|aws s3|--upload-file`).
  No hard verb -> silent; a verb appears later -> escalate to a `report` finding, so the
  confirmation cannot rot. Grep the worker too, otherwise `delite_lane.sh -> run_lane.sh` reads
  clean while the real work happens one hop away.
- **Retiring jobs needs a tier, an archive and a doc sweep.** Tier-2 = paused (`enabled=false`)
  + no run for N days + not referenced by any enabled job's `context_from`; enabled jobs are
  immune, always. Keep the full records in `~/ops/registry/retired-cron-jobs-<ts>.json`
  alongside the `jobs.json` backup (`prune_cron_jobs.py --stale-days 14 --apply`) - a paused
  campaign can be re-created from the archive with its own prompt, schedule and script.
  Then `reconcile_autonomy.py --drop-dead` (a prune creates one DRIFT "dead letter" per
  retired job) and re-audit: expect `0 block, 0 report, 0 observe`.
- **Grep the runbooks for retired job ids.** `ops/artemis/DISABLE-artemis.md` still told the
  operator to `hermes cron resume <id>` for a job deleted that morning. A dead id in a
  re-enable path is worse than no doc: replace it with the exact
  `hermes cron create --name ... --schedule ... --script ... --no-agent --deliver origin`.
- After any cron-store change, re-run the registry artifacts (`registry-refresh.py`,
  `registry-self-qa.py`) so the "one glance" view matches reality, and confirm
  `hermes cron status` still says the gateway is running with the new job count.

## Pressure rectifier: act BEFORE the alerter, and never become the spam itself

Built 2026-10-02 after `vm-resource-watchdog` paged for iostall. Reference:
`~/ops/scripts/pressure_guard.py` (shim `~/.hermes/scripts/pressure_guard.sh`, tests
`~/ops/scripts/test_pressure_guard.py`, cron `2-57/5 * * * *`, ledger
`~/ops/pressure/pressure-ledger.jsonl`, state `~/ops/state/pressure_guard.json`).

- **A rectifier must fire BEFORE the alerter, at the alerter's OWN threshold.** The
  watchdog's iostall bar is PSI `io avg300 = 8`; a rectifier that only sheds at 20 never
  prevents the page. Set the cheap-reclaim trigger equal to the alert bar (`IO_RECLAIM = 8`)
  and keep the destructive tier higher (`IO_SHED = 20`). Offset the cron a couple of minutes
  ahead of the alerter (`2-57/5` vs the watchdog's `5,35`).
- **De-dupe is mandatory - the rectifier is the usual SECOND source of spam.** Log every run
  to the ledger, but DELIVER only when it is news: level rose, a NEW action ran, signals
  measurably worsened (mem_avail down >=4 pts, io300 up >=8), or the cooldown expired. Reset
  the window on recovery (L0/L1) so the next real incident pages immediately. Steady-state
  cooldown 6h. Acceptance proof: real run #1 = ~165 bytes, real run #2 = 0 bytes.
- **`--dry-run` must not write state.** A dry probe that saves state poisons the de-dupe
  window and silently suppresses the next real incident.
- **RAM alone is a terrible trigger on a chronically-full box.** With 12 containers + 9
  gateways, steady-state available RAM sits at 25-38%; a `mem_avail < 30%` trigger would shed
  every 5 minutes forever. Drive on PSI io (the actual iostall) + swap-DISK usage, and keep
  the RAM tiers low (L2 <18%, L3 <13%, L4 <9%).
- **Two-class ladder:** L2 = cheap and reversible (reap stale chrome, break MCP respawn
  loops, unload an idle ollama model *only if* no client is connected); L3 = shed optional
  containers, auto-restored after 2 clean runs. Never auto-shed what a live lane or the
  operator watches (`freqtrade-dryrun`, the payments demo DB).
- **`DISABLED_CONTAINERS` is separate from `OPTIONAL_CONTAINERS`.** Duplicates/leftovers
  (`restart=no`) may be stopped if they reappear but must NEVER be auto-restored - otherwise
  the rectifier resurrects the exact spam you deleted.

## Three failure classes that all read `last_status: error` in `hermes cron list`

- **Script bug** -> fix and resume.
- **The verifier working correctly** -> a FAIL is real signal. The daily Layer-3 job is
  parked on a genuine `checks-monetize` failure; resuming only makes it re-fail and
  auto-pause again. Fix the failing claim first, then resume.
- **Exec-bit bug, not an outage.** A shim doing `exec bash $HOME/ops/verify/x.sh` or
  `exec <script>` dies with **exit 126** when the TARGET lacks `+x`. Audit every exec/bash/
  python target of `~/.hermes/scripts/*.sh` for the execute bit - `ram_ladder_watch.sh` sat
  paused for exactly this. Chmod the whole class, not just the one that failed. Two sibling
  traps: a script the wrapper `exec`s also needs `+x` (`mcp_loop_fix.sh` was `rw-rw-r--`),
  and `pgrep -c` prints `0` **and exits 1** when there are no matches, so a `|| echo 0`
  fallback appends a second `0` (`n="0\n0"`), `[ "$n" -eq 0 ]` dies with "integer expression
  expected", and the health check reports a FALSE FAIL while the box is actually fine. Drop
  the fallback, and prefer `ps -eo args= | grep -c '[i]magineartofficial/mcp'` over `pgrep -f`:
  the bracket trick self-excludes the grep process and any shell that merely quotes the
  pattern.
- **Disabling an MCP server in `config.yaml` does NOTHING to an already-running gateway.**
  `mcp_servers.ImagineArt.enabled: false` was set 26 Sep while the gateway process started
  21 Sep; the in-memory config kept an `npx @imagineartofficial/mcp@latest` respawn loop alive
  for days (`@latest` re-resolves on every spawn = continuous IO + ~190 MB per profile). Fix =
  restart the owning gateway unit. Run it from a cron/one-shot - a restart issued from a shell
  INSIDE that same gateway gets the command blocked - then assert the respawn count is 0.

## Health-probe false positives: "DOWN" that is really a stall

The 2026-10-18 WhatsApp alert storm (`wa-health-watch.sh`, 1 alert / 10 min on a bridge that
was alive and connected for days) had three separate defects. Any single-shot localhost probe
can repeat them:

1. **One probe = no verdict.** Under CPU/IO starvation a Node event loop stalls past any
   timeout you pick (host had 2 vCPU, load ~8, swap ~8 GB; idle latency was 2 ms). Require
   N probes with backoff (3 x 6 s) before declaring a fault.
2. **Classify by what you can still observe**, never by the probe alone:
   port closed = `down` (crash) · port listening + no HTTP = `hung` (stall, NOT a logout) ·
   HTTP with `status != connected` = `disconnected` (the only case that needs re-pair).
   Emitting "session logout, re-pair" for a stall sends the operator to the wrong fix.
3. **Recovery must not re-arm the throttle.** Saving `ok` on ONE good poll restarted the
   cooldown, so a flapping bridge alerted every tick forever. Keep `last_alert` across
   recovery, require N consecutive good polls (3) to clear, and keep the fault state until
   then. Throttle the same severity for the whole window; allow a severity increase only
   after a short floor (5 min).

Also: trust a cached port file only if it answers (else scan the range) or a stale
`bridge_port` fakes a DOWN; put host load/swap/bridge-RSS in the alert body so triage needs
no shell; emit exactly one closure line on real recovery. Fix the starvation too - the
bridge runs in the gateway cgroup (`CPUWeight=1000` via guardrails), so the cheap targeted
win is `sudo renice -n -5` on `bridge.js` re-applied from an existing 5-min guard (respawns
reset nice). Test the classifier against real fake servers (healthy / hang / closed / wrong
status / flap / stale port) with a throwaway state file - the fixtures caught two bugs the
real bridge never would (strict JSON spacing, base-class status leakage).

## Vendor feature parity note

A vendor product pitching "self-healing agents" is selling: failure detection,
auto-drafted fixed version, test-before-apply, and 3-strike auto-pause. Hermes cron already
ships the 3-strike auto-pause natively, so only the heal/draft layer is new work. If asked
to buy the vendor (e.g. Airtop: no official CLI on npm/PyPI, free tier 1,000 credits +
10k one-time, paid from $29/mo), price it against local equivalents
(`chrome-automation` CDP, `browser_exec`, `impfetch`) before spending.
