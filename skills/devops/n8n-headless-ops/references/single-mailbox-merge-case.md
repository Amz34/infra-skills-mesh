# Worked case: two same-mailbox pollers → one merged "Inbox Router" (2026-09-10)

Session-specific record of the merge + cutover + DR drill on this VM. Read with the
"One mailbox = one poller" and "Activation authority in n8n 2.x" sections of SKILL.md.

## The bug (confirmed from the DB, not guessed)

Two ACTIVE workflows each owned an IMAP trigger on the **same mailbox**
`azengineeringapp@gmail.com`, every 5 min, `postProcessAction: read`,
`trackLastMessageId: true`, `forceReconnect: 5`:

| Workflow | Node | Credential record | Credential id |
|---|---|---|---|
| `Sanas Lead Pipeline` (`tdZNdqTc16UqJ7MT`) | Email Trigger (IMAP) | `IMAP Gmail Outreach (azengineeringapp)` | `CredImap001` |
| `Support Triage Desk` (`SupportTriageV1`) | Email Trigger (IMAP) | `Gmail IMAP (Luxe Wave)` ← misnamed | `Ixnx9EJ8sR7S6KtR` |

Two *different* credential records, same `host`/`user` → the overlap was invisible to anyone
reading credential **names**. Whichever trigger polled first consumed the UNSEEN set and marked
it read; the other saw nothing. Result: **random silent loss of leads or support mail**, plus the
loser flapping with `read ECONNRESET` (visible in the journal right up to the restart).

**Diagnosis recipe:** for every workflow whose node `type` contains `imap`, print
`nodes[].credentials.imap.id` + `parameters`, then
`n8n export:credentials --all --decrypted` and group by `host`/`user` — never by name.
More than one active workflow per `user` = this bug.

## The fix

Merged into **`Inbox Router: Sanas Leads + Sanad Triage`**, id `zHwz2i9IW2nAQvwi`, 9 nodes:

```
Email Trigger (IMAP)  [CredImap001, */5, postProcessAction: read, forceReconnect: 5]
├── Filter & Enrich → MailerLite Add Subscriber, Telegram Alert (Leads)
└── Normalize & Dedupe → DeepSeek Classify → Parse & Build Digest
                        → Telegram Alert (Triage), Log to CSV
```

Both branches sit downstream of the SAME trigger -> one poll, one owner, no race. Built
programmatically from the live DB (`~/work/n8n/build_merged_mailbox.py`) rather than hand-copied:
it reads both source workflows, hoists one trigger, rewires the second branch's `connections`
entry, and **renames colliding node names** — two nodes were both called `Telegram Alert`
(plus two `Filter...`/`Log to CSV`), so the merged JSON must suffix them `(Leads)` / `(Triage)`
and the merge must rewrite `connections` keys to the new names.

Old workflows were left **deactivated, not deleted**, as the rollback path.

## Cutover runbook (what was actually run)

1. Build the merged JSON + a synthetic **test copy** (see SKILL.md "Testing a workflow without
   side effects"), `n8n execute --id=<testid>` with `N8N_RUNNERS_BROKER_PORT=5699` → all nodes
   green, real CSV written through `require('fs')` (proving the earlier
   `Module 'fs' is disallowed` era is over).
2. `python3 ~/work/n8n/n8n_api.py list` → capture current ids/active states.
3. `n8n_api.py activate <merged>` , `n8n_api.py deactivate <old1> <old2>`.
4. **`sudo systemctl restart n8n`** — mandatory, see below.
5. Verify: journal `Activated workflow "…"` lines list only the intended set;
   `n8n_api.py list`; then send a real email and confirm exactly ONE execution.

## The trap that made restart mandatory (timeline, prod)

| time | event |
|---|---|
| 08:24:15 | API `deactivate SupportTriageV1` → HTTP 200, `active:false` |
| 08:25:35 | test email #1 arrives |
| 08:25:44 | **two** executions: `zHwz2i9…` (199, success) **and** `SupportTriageV1` (200) → duplicate processing, CSV got 2 rows for 1 email |
| 08:32 | `systemctl restart n8n` → journal activates only Carousel + Invertio + Inbox Router |
| 08:33:18 | test email #2 arrives → **exactly one** execution (201), retired workflows silent, CSV +1 row |

Conclusion: `POST /workflows/{id}/deactivate` returning 200 does **not** unregister the poller in
the running process. Restart, then re-prove with real mail. Cleaned the test rows out of the
production CSV afterwards.

## DR drill trap (same root cause)

The restored sandbox (`N8N_USER_FOLDER=/tmp/n8n-restore-drill`) booted with **4/4 workflows
ACTIVE even though every `workflow_entity.active` was 0** — the restored instance started polling
the LIVE mailbox. No executions were created and no mail was consumed (verified: drill 26 execs =
prod 26 execs), but only by luck. Drill instances must neutralise `active` **and** wipe
`credentials_entity` before `start`, and use unique ports (prod holds 5678/5679).
`~/ops/scripts/n8n_restore_drill.py` therefore does the CLI-only proof and never starts a server:
archive → DB extract → `pragma integrity_check` → counts → `export:credentials --all
--decrypted` (9 creds decrypt) → sandbox removed. Verified output: `DRILL PASS`.

## Leftovers left deliberately unfixed (offer them, don't sneak them in)

1. Triage CSV rows log empty `email_date`/`from`/`subject`: the DeepSeek HTTP node replaces the
   item payload, so `Parse & Build Digest` must re-attach them from `$('Normalize & Dedupe').all()`.
2. `Error while saving insights metadata and raw data` every ~30 s — pre-existing, unrelated to
   this work, insights feature broken.
3. Unused duplicate IMAP credential `Gmail IMAP (Luxe Wave)` — only the retired workflow
   references it; delete once the rollback window closes.
4. Watchdog now enforces the contract: exactly ONE active IMAP poller, and the retired pair must
   stay inactive (`RETIRED_IDS` in `~/ops/scripts/n8n_watchdog.py`) → a re-activation alert fires.
