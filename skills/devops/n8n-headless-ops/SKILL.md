---
name: n8n-headless-ops
description: Use when running n8n headless — CLI imports, webhooks, auth.
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [n8n, automation, webhook, systemd, caddy, apify, devops]
    related_skills: [cloudflare-quick-tunnel, hermes-cloud-vm-ops]
---

> Reference: `references/deactivate-workflow-headless.md` — headless deactivate/reactivate of a workflow (SQLite `workflow_entity.active` + restart + audit-log verify), API 401 pitfalls, LLM-node token-audit pattern, code-node `fs` sandbox gotcha.
> **Update 2026-09-10 (corrected):** in this build `workflow_published_version` / `workflow_publication_trigger_status` are **empty and unused** — `workflow_entity.active` IS what the API writes and what runs. The real hazard is the **restored archive DB**: it carries `active=1` for whatever was live at backup time, so a sandbox that boots it resumes polling the live mailbox. Prove DR **without booting**; if you must boot, clear the flags on the exact DB the instance reads. Prefer the Public API `POST /workflows/{id}/activate|deactivate` **plus a restart** — see "Activation authority in n8n 2.x" below.
> Support files: `scripts/n8n_api.py` (list/activate/deactivate/**update (PUT a full body)**/probe cutover helper), `scripts/decode_execution_data.py` (flatted execution reader → per-node item counts), `references/single-mailbox-merge-case.md` (worked case: two pollers → one merged router, with the cutover/rollback runbook and timelines), `references/live-workflow-code-edit-case.md` (worked case: diagnosis → sandbox proof → prod PUT → rollback → residue cleanup for a digest/CSV data-loss bug).
> Also: `references/credential-hygiene-and-dr-hardening.md` — retiring a duplicate credential safely, the restore-path hole + weekly drill wiring, and the watchdog secrets-cache trap. One-off helpers used by these runs live in `~/work/n8n/`: `n8n_creds.py` (list / `cred-diff` / delete), `make_imap_cache.py`, `do_cred_cleanup.py`.
> Export/DR layer: `references/workflow-json-export-and-drive-mirror.md` — per-workflow versioned JSON export + Drive mirror, with the "mirror failure must exit non-zero" canary contract.
> Audit a mailbox overlap by **grouping credentials on `host`/`user`, never on credential name** — two differently-named records can point at the same mailbox, which is exactly how the duplicate poller hid. Recipe: list every workflow with an `imap` node, print its trigger's `credentials.imap.id`, then `n8n export:credentials --all --decrypted` and group.

# n8n Headless Ops

Manage n8n on a headless VM with no browser: import/export workflows & credentials via CLI,
expose webhooks through tunnels, add auth, and debug executions from logs/DB.

## When to Use

- Building/importing n8n workflows from the CLI (no editor UI).
- Creating credentials programmatically (Apify, DeepSeek, HTTP header auth, etc.).
- Exposing n8n webhooks publicly (cloudflared) and securing them.
- Debugging failed workflow executions from systemd logs + SQLite.

## Critical First Check: How is n8n RUNNING here?

**Before creating ANY service/unit, check BOTH system and user systemd scopes:**
`systemctl list-units | grep -i n8n` AND `systemctl --user list-units | grep -i n8n`.
On this VM n8n + its tunnel run as **SYSTEM units** (`/etc/systemd/system/n8n.service`,
`/etc/systemd/system/cloudflared-n8n.service`, `Restart=always`) — NOT user units.

Pitfalls that cost a session:
- Killing the n8n process → systemd `Restart=always` respawns it within seconds (looks like
  a "mystery respawner"). `process(action='list')` (Hermes PM) is NOT the respawner — check
  systemd system units first.
- Creating a duplicate user-level unit → port 5678 conflict → the new unit crash-loops
  ("port already in use") while the old one holds the port. Stop + disable the duplicate
  and keep ONE manager.
- n8n runs via `/etc/n8n/env` (EnvironmentFile) — already carries `N8N_BASIC_AUTH_*`.
  Effective node binary: `/home/ubuntu/.hermes/node/bin/node` (v22+; `/usr/bin/node` is too old).

## CLI Import/Export (n8n 2.x — regular single-main mode)

Command names: `import:credentials` / `import:workflow` / `export:credentials --all --decrypted`
/ `export:workflow --id <id>|--all --output=<file>` / `export:nodes` / `list:workflow` / `publish:workflow --id <id>`.
**`export:workflow` is SINGULAR in 2.x** — `export:workflows` (plural) exits 1 with
`Error: Command "export:workflows" not found` (cost a failed run 2026-09-10). When a CLI verb you
"know" stops resolving, run `n8n <verb> --help` / `/home/ubuntu/.local/bin/n8n --help` before
assuming the build is broken.

- **`id` field is REQUIRED** in imported credentials AND workflows (SQLite NOT NULL).
  Credential: `{"id": "CredID0001", "name": "...", "type": "httpHeaderAuth", "data": {...}}`.
  Workflow root: `{"id": "WorkflowID001", "name": "...", "nodes": [...], "connections": {...}, "active": true}`.
- `export:credentials --all --decrypted` shows the exact schema (type names, id format) —
  mirror it for imports.
- `export:nodes --output=nodes.json` dumps ALL node-type definitions → get exact typeVersions
  (webhook=2.1, httpRequest=4.5, code=2, respondToWebhook=1.5) and check whether a node
  exists at all (e.g. the Apify node is NOT in the base build — use HTTP Request instead).
- `--activeState fromJson` is **multi-main only** — in regular mode import inactive, then
  `publish:workflow --id <id>`. Publish prints "changes will not take effect if n8n is
  running" → **restart n8n after import** for the new version to load.
- After restart, **webhook registration is ASYNC (~30-40s)** — hitting the webhook too early
  returns 404 "not registered" even though the workflow shows active=1. Wait, or watch the
  journal for `Activated workflow "..."`.

## Webhook Workflow Gotchas

- **Webhook node output wraps the POST payload**: `$json.body.url`, NOT `$json.url`
  (headers/query/params are separate keys). Empty-body symptoms: downstream HTTP node gets
  400 with the actor's "field X is required".
- To return data synchronously: Webhook node `responseMode: "responseNode"` + a final
  `Respond to Webhook` node (respondWith: allIncomingItems).
- Production webhook URL: `<tunnel>/webhook/<path>`; test URL: `/webhook-test/<path>`.
- Debug failed executions: `sudo journalctl -u n8n --since "..." | grep -B5 error` shows the
  HTTP status + response body per node. DB (`~/.n8n/database.sqlite`, `execution_data` table)
  stores a compact/obfuscated format — logs are faster to read.

## Securing the Public Tunnel

n8n ignores `N8N_BASIC_AUTH_*` when **User Management is active** (owner user exists — check
`user_entity` rows) — the editor is protected by login but webhooks stay OPEN. Reliable
pattern: basic-auth reverse proxy in front, tunnel points at the proxy:

1. `caddy hash-password --plaintext '<pass>'` → bcrypt hash.
2. Caddyfile site on a free port (e.g. 5680) with `basic_auth` + `reverse_proxy 127.0.0.1:5678`.
3. Point cloudflared at the proxy port; verify: no-auth → 401, good-auth → 200, webhook
   no-auth → 401.

Caddy quirks on this VM (v2.11.4 build): the `admin off` / `admin localhost:PORT` global
directive BREAKS site parsing ("unrecognized directive: :5680") and `--admin off` is an
unknown flag. Workaround: `caddy adapt --config <caddyfile>` to JSON, inject
`"admin": {"listen": "127.0.0.1:2021"}` (free port), then `caddy run --config caddy.json`.
Run caddy as a user systemd unit (`~/.config/systemd/user/caddy.service`) — it coexists with
the pre-existing system caddy on :80/:443/:2019.

## Calling Apify/DeepSeek from a Workflow

Apify node is absent from the base build → use **HTTP Request nodes** with `genericCredentialType`
+ `httpHeaderAuth` credentials (one per service), hitting the same endpoints the CLI scripts use:

- Apify transcript (sync): `POST https://api.apify.com/v2/acts/<username>~<actor>/run-sync-get-dataset-items?timeout=240`
  body `{"videoUrl": "..."}` — tilde (`~`) separator is REQUIRED in API paths.
- DeepSeek: `POST https://api.deepseek.com/v1/chat/completions`, model `deepseek-v4-flash`,
  `max_tokens: 8000` (reasoning tokens count toward the budget — 3000 empties the response),
  `response_format: {"type": "json_object"}`.
- Credential type names: `apifyApi` (data: accessToken), `httpHeaderAuth` (data: name/value).
- Reference implementation + workflow JSON: `references/carousel-webhook-workflow.md`.

## Monitoring, Backup & Cron Discipline (added 2026-09-10)

**Keep n8n watchable — a dead IMAP poller looks *idle*, not broken.**

- Watchdog pattern (production-ready on this VM): `~/ops/scripts/n8n_watchdog.py`, run by a
  Hermes cron job **every 30m** with `no_agent=True` → stdout is delivered verbatim and
  **empty stdout = silent**, so it only speaks when something is wrong. Include a
  `--verbose` and a `--selftest` flag (inject a fake problem) so you can prove both paths.
- Watchdog checks worth having: `systemctl is-active n8n` (**system** scope), API reachable,
  **every expected workflow ID still has `active=true`**, **exactly ONE active IMAP/mailbox
  poller** (two pollers on one mailbox silently lose mail — see the one-mailbox rule below) and
  no retired workflow re-activated, execution error **streak**
  (≥2 consecutive newest errors — a lifetime error count is useless, the old broken era keeps
  it high forever) plus 24h error count, **IMAP credential LOGIN still succeeds**, SQLite
  `pragma integrity_check`, and the age of the last DB backup.
- Test credentials without the UI: `n8n export:credentials --all --decrypted` → cache
  `host/port/user/password` into a `0600` JSON and let the watchdog do a cheap `imaplib`
  LOGIN per tick. **Key variance:** some IMAP credentials use `secure`, others `ssl`.
- Backup: `sqlite3 ~/.n8n/database.sqlite ".backup '<dest>'"` is **WAL-safe on the LIVE
  database** — never `cp` a running SQLite file. 10.5 MB DB snapshots in <1 s. Keep a rolling
  local copy (KEEP 3) *and* fold it into the encrypted off-site archive.

### Hermes cron pitfalls that cost a session

- `schedule='30m'` is parsed as **one-shot** ("once in 30m", `repeat.times=1`) — the job fires
  once, sets `state=completed, enabled=false`, and silently stops existing. Use
  **`'every 30m'`** for recurring (sets `repeat=forever`).
- If you create a one-shot and *later* `update` it to `every 30m`, the stored `repeat.times=1`
  is **not** reset — it fires once more then disables itself. **Delete + recreate** instead.
- Verify in `~/.hermes/cron/jobs.json`, not in the tool's echo: look for
  `schedule.kind=interval`, `repeat.times=null`, `enabled=true`, `state=scheduled`.
- Cron `script` must be a **bare filename** resolvable under `~/.hermes/scripts/` (absolute
  paths are rejected). Keep the real script in `~/ops/scripts/` and drop a 5-line
  `runpy.run_path(...)` shim in `~/.hermes/scripts/`.

### CLI invocation pitfall

Use the wrapper **`/home/ubuntu/.local/bin/n8n`**. Calling
`~/.hermes/node/bin/node /usr/lib/node_modules/n8n/bin/n8n …` fails — n8n on this VM lives at
`/home/ubuntu/.local/lib/node_modules/n8n/` (a wrong-path attempt silently returns empty
stdout, which is easy to mistake for "no credentials exist").

### Reading the API for health

`GET http://127.0.0.1:5678/api/v1/executions?limit=50` with header `X-N8N-API-KEY` (from
`/etc/n8n/env`) gives `status` + `startedAt` per execution — sort by `startedAt` desc and count
the leading `error` streak. `GET /api/v1/workflows?limit=100` gives each workflow's `id`/`active`.

### Activation authority in n8n 2.x (learned the hard way, 2026-09-10)

- **Corrected 2026-09-10 — the earlier claim here was wrong.** Evidence: this instance has
  **0 rows** in `workflow_published_version` *and* `workflow_publication_trigger_status` while 3
  workflows are running with `active=1` → `workflow_entity.active` **is** authoritative here, and
  it is exactly what the Public API writes. The sandbox that seemed to "activate by itself" had
  been booted from a **restored archive DB whose rows still said `active=1`** (the archive was
  taken while both old pollers were live) — so the hazard is the *copy*, not a hidden table.
  Always check `select count(*) from workflow_published_version` before theorising about
  activation.
- Prefer the Public API for cutovers: `POST /api/v1/workflows/{id}/activate` and `/deactivate`
  (both 200; deactivate is idempotent; `activate` on a trigger-less workflow → 400
  "no trigger node"). Helper: `~/work/n8n/n8n_api.py` (key read from `/etc/n8n/env` at call
  time, never printed).
- **Deactivation does NOT take effect in the running process** — a "deactivated" workflow kept
  polling and double-processed an email 0.1 s after the API returned 200. `systemctl restart n8n`
  fixed it. Always restart, then verify: journal `Activated workflow "…"` lines +
  `GET /api/v1/workflows?limit=100` + `n8n_api.py list`.

### HTTP Request nodes replace the item payload (silent logging data loss)

- An `httpRequest` node (here `DeepSeek Classify`) returns the **API response as the item**, so
  every field the previous Code node added (`from`, `subject`, `date`, `messageId`, `text`) is
  gone downstream: the digest printed `From: undefined` and `Log to CSV` wrote empty
  `email_date`/`from`/`subject` (live-confirmed 2026-09-10; fix + evidence in
  `~/ops/kb/n8n-audit-and-plan.md` §10).
- Fix pattern — re-attach by **index** against the upstream node, with a bounds guard, and spread
  the metadata *after* `...item.json` so it wins:
  `const src = $('Normalize & Dedupe').all().map(i => i.json);`
  `let meta = src[i]; if (!meta) meta = src.length === 1 ? src[0] : {};`
  Index pairing is safe because the HTTP node runs once per item (order preserved); the guard
  degrades to blanks rather than mis-pairing if counts ever diverge.
- Whenever you add an HTTP/LLM node to a pipeline that also *logs* or *notifies*, re-read the
  output fields afterwards — empty columns fail silently. Builder script:
  `~/work/n8n/fix_digest_meta.py` (also emits the side-effect-free test copy).

### Editing a live workflow's code safely (PUT + restart, proven 2026-09-10)

Never hand-edit `~/.n8n/database.sqlite` for a code change, and never PUT a graph you rebuilt from
memory. Runbook that worked end-to-end:

1. **Dump the live graph read-only** (`sqlite3 'file:/home/ubuntu/.n8n/database.sqlite?mode=ro'`)
   and save the current body to `~/work/n8n/rollback/<thing>-before-<change>.json` **first** — that
   file *is* your rollback.
2. Patch the target node's `jsCode` **programmatically** (load the JSON, find the node by `name`,
   string-replace the snippet, re-`json.dumps`) — retyping the graph by hand is how graphs get lost.
3. PUT the full body: `python3 ~/work/n8n/n8n_api.py update <workflowId> <body.json>` (sends
   `{name, nodes, connections, settings}`) → expect **200**; print `active` + node count from the response.
4. **`sudo systemctl restart n8n`** — the running process keeps serving the OLD code until restart.
5. Verify the change landed: re-read the DB and assert the new snippet is present.
6. Prove on production with **one real email**, then read the newest execution + the output artifact
   back (`~/work/n8n/e2e_check.py` sends + waits, `~/work/n8n/e2e_readback.py` prints per-node items
   and the CSV). Assert on **real values** (digest `From:`/`Subject:`, filled CSV columns) — not on
   "execution status = success", which stays green even when every field is `undefined`.

Rollback = step 3 with the `rollback/` body, then step 4.

### Leaving no test residue (client-facing artifacts)

A green test still writes to production places: the report/CSV the client reads, the shared mailbox,
and the sandbox dir. Clean up as part of the task, not as an afterthought.

- Output file: filtered rewrite that drops **only** rows matching your test sender/subject, and keep
  a `<file>.pre-testfix.bak` beside it.
- Mailbox: `imaplib` login with the app password → `SEARCH` by subject → `STORE +FLAGS \Deleted` →
  `EXPUNGE`. Match `from … AND subject≈test` so real client mail can never be caught; afterwards
  re-search and report deleted-vs-kept.
- Sandbox: `rm -rf` it. A "copy of the prod DB" also contains `config` (**the encryption key**) and
  decrypted credentials — never leave it in `/tmp`.

### One mailbox = one poller (merging duplicate IMAP workflows)

- **Never leave two ACTIVE workflows polling the same mailbox.** With `postProcessAction: read`
  (+ `trackLastMessageId`) both triggers compete for the same UNSEEN set: whichever polls first
  consumes and marks it read, the other silently sees nothing → mail lost at random, and the
  loser flaps with `read ECONNRESET`. Two *credential records* for the *same* mailbox (here
  `CredImap001` + a misnamed `Gmail IMAP (Luxe Wave)`) hide the overlap — compare `host`/`user`
  of the trigger credentials, never the credential names.
- Retiring the duplicate once the merge is trusted — **repoint first, delete second** (proven
  2026-09-10): PUT the workflow that still references the doomed record onto the keeper
  (`n8n_api.py update <id> <body.json>` → 200, stays inactive), **then**
  `DELETE /api/v1/credentials/{id}` → 200. Assert afterwards: credential count dropped by exactly
  one, exactly one `imap` record remains, every workflow's refs still resolve.
- **Refresh the watchdog secrets cache immediately after** — `~/.config/n8n/watchdog_secrets.json`
  stores decrypted `host/user/password` and **no credential ids**, so a stale cache goes on
  IMAP-LOGIN-testing a credential you just deleted while the watchdog keeps printing
  `all checks healthy`. Re-run `make_imap_cache.py`, assert the cache now holds exactly one `imap`
  entry, then re-run the watchdog. Same rule after rotating any IMAP/DeepSeek credential.
- Full runbook, plus how to prove two records are the *same mailbox* (decrypt on an **isolated DB
  snapshot**, compare `host`/`user` only, print booleans — never the passwords):
  `references/credential-hygiene-and-dr-hardening.md`.
- Merge pattern that works: **one IMAP trigger → fan-out to every branch start**, keep each
  branch's nodes verbatim and **rename colliding node names** (two `Telegram Alert` → `(Leads)` /
  `(Triage)`). Generate the JSON programmatically from the live DB
  (`~/work/n8n/build_merged_mailbox.py`) instead of hand-copying; leave the old workflows
  **deactivated, not deleted**, as rollback.
- Verify with real mail: send a test email, expect **exactly ONE execution**, and read per-node
  item counts from `execution_data`. That blob is `flatted`-encoded — plain `json.loads` raises
  `'list' object has no attribute 'get'`; decode with a reviver that resolves numeric *string*
  values as indices into the top-level array.

### Testing a workflow without side effects

- Clone it into a **test copy**: `Manual Trigger` + a Code node emitting items shaped like the
  real trigger payload (`date`, `from`, `subject`, `textPlain`, `text`, `messageId`);
  replace Telegram/MailerLite/SMTP nodes with `NoOp`; **remap hard-coded file paths inside Code
  nodes to `/tmp`** (e.g. `/home/ubuntu/ops/leads/support-triage.csv` → `/tmp/drill-triage.csv`)
  so the real node code runs without polluting production output.
- `N8N_USER_FOLDER=<sandbox> n8n execute --id=<testid>` gives isolated end-to-end proof — but
  while prod runs it dies with `n8n Task Broker's port 5679 is already in use`; set
  **`N8N_RUNNERS_BROKER_PORT=5699`** (plus `N8N_ENCRYPTION_KEY` for a restored DB) and
  `N8N_RUNNERS_ENABLED=false`. `N8N_USER_FOLDER` IS honoured by the CLI.
- **Cloning the test graph into a NEW row fails: `Failed to resolve owning project for workflow`.**
  A freshly inserted `workflow_entity` row has no project relation, so the CLI aborts before
  running. Cheaper than repairing relations: **clone the graph onto an existing (retired) workflow
  row** — the relation survives and the test runs under an id you already declared dead. Also set
  `versionId` when the source row has NULL (`rec['versionId'] = rec.get('versionId') or os.urandom(8).hex()`).
- **Re-assert the trigger wiring after copying.** In one test copy the `Inbox Poll → Synthetic Emails`
  edge had been popped (n8n drops a replaced trigger's connections), so the run exited "success" with
  nothing downstream executed. Check `connections[<trigger>].main[0][0].node == 'Synthetic Emails'`
  before trusting a green run.
- A green CLI run is not proof on its own: read the **per-node item counts** and the produced
  artifact afterwards (see `scripts/decode_execution_data.py`).

### Safe DR restore drill

- `~/ops/scripts/n8n_restore_drill.py` — extracts `./n8n/database.sqlite` from the newest
  encrypted archive into a sandbox and proves `integrity_check: ok`, row counts, and
  **credential decryption** (`export:credentials --all --decrypted` → 9 creds) → the archive
  rebuilds a *working* n8n, not just a readable file.
- Do the CLI proof **before** any `start`. If you must boot, neutralise first
  (`workflow_entity.active=0` **and** wipe `credentials_entity`) and use unique ports
  (`N8N_PORT=5788`, `N8N_RUNNERS_BROKER_PORT=5699` — prod holds 5678/5679).
- **Weekly / unattended:** Hermes cron `9ba302fe1c2b` (Sun 05:00) →
  `~/.hermes/scripts/n8n_restore_drill_weekly.sh` — silent on success, loud + non-zero on failure.
- **n8n is now in the restore path (2026-09-10):** `ops/restore.sh` restores `~/.n8n/database.sqlite`
  (keeping `database.sqlite.pre-restore-<ts>`) and `/etc/n8n/env` (encryption + API key); under
  `RESTORE_DRY_RUN=1` the env goes to `$HOME/n8n-env.restored` and `sudo` is never used.
  `ops/verify/restore_verify.sh` now checks n8n integrity + workflow count + env. Before this, a
  rebuilt VM came back with **no n8n at all**. Expect `RESULT: N passed, 0 failed`.
- `make_imap_cache.py` (watchdog secrets) must run against an **isolated DB snapshot** — the n8n CLI
  against the live user folder returns rc=1 with empty output. Cache: `~/.config/n8n/watchdog_secrets.json`.
  Make the generator **refuse to write an empty cache** (parse the export *file*, not stdout) — a
  silent empty cache blinds the watchdog, which is worse than a loud failure.
- **Cleanup after any archive extraction:** the extracted tree is **root-owned**, so a plain
  `rm -rf` leaves residue — use `sudo -n rm -rf <sandbox>` and confirm the path is gone. That tree
  carries `config` (**the encryption key**) plus decrypted credentials; never leave one in `/tmp`.
- **Doc drift is a real failure mode.** After the credential delete, `~/ops/kb/n8n-audit-and-plan.md`
  still read "both IMAP credentials still LOGIN" and "all 4 expected workflow IDs". The watchdog's
  `EXPECTED_IDS` is the source of truth — re-read it (and the live `active` flags) whenever the
  topology changes, then fix the doc in the same pass.

### Versioned workflow JSON export (diff-able DR layer, added 2026-09-10)

The encrypted archive's `database.sqlite` restores the whole instance but answers neither "what
changed since last week" nor "re-import just this one workflow". Add the cheap second layer:

- `~/ops/scripts/n8n_export_workflows.py` → `~/ops/backups/n8n-workflows/<YYYY-MM-DD>/`, one JSON per
  workflow + `summary.json`, keeps the **last 8** dumps, mirrors each dump to
  `gdrive:Hermes-Telegram-Backup/n8n-workflows/<date>/`.
- Cron: `n8n-workflow-export-weekly` (`30 5 * * 0`, `no_agent=True`) →
  `~/.hermes/scripts/n8n_workflow_export_weekly.sh`. Contract: **silent only when BOTH the local dump
  and the Drive mirror succeed**; a dead mirror exits non-zero with a one-line reason, so the job
  doubles as the offsite-health canary (the nightly backup's journal is read by nobody).
- Verified: rc=0 with 5 workflows, per-workflow files diff cleanly across dates. Design + failure
  semantics: `references/workflow-json-export-and-drive-mirror.md`.
- **Drive mirror ka token `cloud-vm-backup-dr` gotcha 17 ka territory hai:** re-auth ke baad mirror chup-chaap
  non-zero (401) de sakta hai, aur galat account me login hua to mirror khaali folder me "success" karta rahega.
  Ye cron hi offsite-health canary hai — isliye pehla check `rclone lsf gdrive:Hermes-Telegram-Backup/` me
  expected archives hona chahiye, na ke sirf rc=0. Recovery + wrong-account check: `cloud-vm-backup-dr` gotcha 17 + `references/rclone-wrong-account-recovery.md`.

### Zapier / Make: when NOT to add them (asked 2026-09-10)

Don't add a second automation SaaS on top of a working n8n unless one of these is true:

1. The target app has **no n8n path** (no connector AND no usable HTTP API) — then the SaaS's
   connector is the only route.
2. The **client** needs a no-code UI they will edit themselves (n8n's editor is fine for us, but it
   is not what a non-technical client should be handed).

Otherwise the honest arithmetic favours n8n here: it already runs 5 workflows + webhooks + ~28 Hermes
cron jobs at zero marginal cost and unlimited runs, whereas Zapier's free tier is 100 tasks/month on
2-step Zaps (a 4-step Zap at 1k runs/month lands in the ~$50–70/month tier; the entry paid plan is
$19.99 for 750 tasks) and Make's free tier is 1,000 credits/month with paid from ~$9. Report the
verdict with those numbers rather than a vague "n8n is enough".

## Verification

- After any tunnel change: curl no-auth 401 / with-auth 200 through the PUBLIC URL.
- After workflow import+restart: wait 40s, POST the webhook, expect the final JSON.
- Check `list:workflow` + DB `active` flag if the webhook 404s.
