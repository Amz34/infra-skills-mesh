# Versioned workflow JSON export + Drive mirror (built 2026-09-10)

Why: the encrypted archive carries `database.sqlite`, which can restore the whole instance but cannot
answer "what changed since last week?" or "re-import just this one workflow". Answering those needs a
**per-object, versioned, diff-able** second layer on top of the DB snapshot.

## Shape

```
~/ops/scripts/n8n_export_workflows.py
  → ~/ops/backups/n8n-workflows/<YYYY-MM-DD>/<slug>__<workflowId>.json   (one file per workflow)
  → ~/ops/backups/n8n-workflows/<YYYY-MM-DD>/summary.json               (id, name, active, node count)
  → retention: last 8 dumps (older date dirs removed)
  → mirror:    gdrive:Hermes-Telegram-Backup/n8n-workflows/<date>/        (rclone copy)
```

- One file per workflow (name+id in the filename) is what makes `diff <dateA>/<dateB>/x.json` useful;
  a single combined dump forces you to slice JSON before every comparison.
- `--verbose` prints the per-step detail; the default run prints only failures.

## CLI facts learned here

- Export verb is **`export:workflow`** (singular) in n8n 2.x. `export:workflows` →
  `Error: Command "export:workflows" not found`, rc=1, empty output. Confirm verbs with
  `/home/ubuntu/.local/bin/n8n --help` rather than trusting memory.
- Run everything with `HOME=/home/ubuntu` set explicitly — in this environment a bare `~` in a
  terminal resolves to the **invertio** profile home, so a script that trusts `~` writes/looks in the
  wrong place.

## Failure semantics (the important part)

The local dump and the Drive mirror are graded differently:

- **Local dump fails** → nothing was backed up → non-zero exit, print the error.
- **Drive mirror fails** → local dump is intact, but the *offsite* layer is broken → still
  **non-zero exit** plus a one-line reason, e.g.
  `drive upload FAILED (401 Invalid Credentials) — local dump kept at <path>`.

Rationale: the nightly backup already degrades to local-only on any Drive problem, and nobody reads
that job's journal. A weekly job that stays silent while the mirror is dead lets the offsite layer rot
for months — exactly the failure this export was added to avoid. Wired through a `no_agent` Hermes
cron, a non-zero exit becomes a Telegram alert for free, so the job doubles as the **offsite-health
canary**.

## Wiring

- Script: `~/ops/scripts/n8n_export_workflows.py`
- Shim (cron scripts must live under `~/.hermes/scripts/`): `~/.hermes/scripts/n8n_workflow_export_weekly.sh`
  — runs the script, and on any failure echoes the tail of its output and propagates the non-zero exit;
  silent otherwise.
- Hermes cron job: `n8n-workflow-export-weekly`, `30 5 * * 0` (Sunday 05:30 UTC), `no_agent=True`,
  `deliver=origin`. Sunday 05:00 already runs the n8n restore drill, hence the 05:30 slot.

## Verified 2026-09-10

- `python3 ~/ops/scripts/n8n_export_workflows.py --verbose` → rc=0, 5 workflow JSON files + `summary.json`
  for the date dir; duplicates across dates diff cleanly.
- Shim with a broken mirror → rc=1 and a single actionable line (Drive token issue tracked separately;
  see the `cloud-vm-backup-dr` skill — root has no rclone config, and the 401 triage order lives in
  `references/rclone-google-drive-headless-oauth.md` sections 8–9 there).
