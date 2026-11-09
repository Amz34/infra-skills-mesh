# Worked case: live workflow code edit — digest/CSV data loss (2026-09-10)

Prod router `zHwz2i9IW2nAQvwi` ("Inbox Router: Sanas Leads + Sanad Triage", 9 nodes, single IMAP
owner) on n8n v2.34.6, `/home/ubuntu/.n8n/database.sqlite`. Use as the reference implementation of
the "Editing a live workflow's code safely" runbook in SKILL.md.

## Symptom (why it hid)
- Telegram triage digest printed `From: undefined`.
- `~/ops/leads/support-triage.csv` rows had empty `email_date` / `from` / `subject` — the CSV is the
  human review trail, so the log was useless while *nothing* looked broken.
- Leads branch was unaffected (0 items) → SMTP/Telegram side effects fine, and n8n reported the
  execution as **success**. Execution status is not data validation.

## Root cause
`DeepSeek Classify` is an `httpRequest` node: it returns the API response **as the item**, replacing
everything `Normalize & Dedupe` had attached (`from`, `subject`, `date`, `messageId`, `text`).
Every downstream node read fields that no longer existed. Any HTTP node inserted mid-pipeline has
this effect.

## Fix
`Parse & Build Digest` re-attaches the source metadata **by index** against the upstream node, with
a bounds guard, and spreads it *after* `...item.json` so the real values win; it exports
`from`/`subject`/`date` explicitly (plus a `meta_paired` boolean) for the digest and CSV nodes.

```js
// shape of the fix — shipped node code: ~/work/n8n/merged/code/Parse_and_Build_Digest.js
const src  = $('Normalize & Dedupe').all().map(i => i.json);
const meta = src[i] || (src.length === 1 ? src[0] : {});   // degrade, never mis-pair
return { json: { ...item.json, from: meta.from, subject: meta.subject,
                 date: meta.date, meta_paired: !!meta.from } };
```

Index pairing is safe because the HTTP node runs once per item and n8n preserves order; on any count
mismatch the guard yields blanks instead of attributing one email's metadata to another.

## Proof chain (sandbox first, then one real email — both required)
- **Sandbox:** prod DB copied to a sandbox dir, graph cloned onto a **retired** workflow row, trigger
  rewired to `Manual Trigger` + synthetic emails, every outbound side effect replaced with `NoOp`,
  CSV path pointed at `/tmp`. `N8N_RUNNERS_ENABLED=false N8N_USER_FOLDER=<sandbox> n8n execute --id=<testid>`
  → 10/10 nodes green, `meta_paired=True` on both items, **real DeepSeek call**, CSV written to `/tmp` only.
- **Production:** one self-addressed test email → exec **202**, success in 3.5 s; digest *and* CSV row
  both carried `from='Sanad Ops <azengineeringapp@gmail.com>'`, `subject='Metadata check after fix'`,
  real `email_date`. Leads branch took 0 items (MailerLite untouched).
- **Apply:** PUT **200** of the full body (`{name, nodes, connections, settings}`), `active: true`,
  9 nodes, then `sudo systemctl restart n8n` → healthz 200 → DB re-read confirmed the new code.
- **Rollback:** `~/work/n8n/rollback/inbox-router-before-csv-fix.json` (same PUT + restart).

## Residue cleanup (part of the task, not an afterthought)
- CSV: filtered rewrite dropping only the 2 test rows → 0 data rows; kept `support-triage.csv.pre-testfix.bak`.
- Mailbox: imaplib `SEARCH`→`STORE +FLAGS \Deleted`→`EXPUNGE` removed the test mail (uid 483) and the
  earlier `[TEST]` self-mails; re-searched and reported 7 kept (real client mail + self-sent carousel packages).
- Sandbox dir removed — it held a full prod DB copy **including `config` (encryption key)** plus
  decrypted credentials; temp body/secret dumps deleted too.

## Non-obvious gotchas hit
- Inserting a **new** `workflow_entity` row → `Failed to resolve owning project for workflow`; clone
  onto an existing retired row instead.
- Source row had `versionId = NULL` → set a random hex for the copy.
- The copy's trigger edge `Inbox Poll → Synthetic Emails` was popped → the CLI run "succeeded" with
  nothing downstream executing. Assert the edge before trusting a green run.
- Editing the graph without restarting n8n changes nothing — the running process serves old code.

## Reusable artifacts
`~/work/n8n/`: `fix_digest_meta.py` (patched prod body + side-effect-free test copy), `run_sandbox_test.py`,
`e2e_check.py`, `e2e_readback.py` (newest execution + CSV readback), `cleanup_after_test.py`,
`n8n_api.py` (now carries the `update` PUT subcommand), `merged/code/*.js` node dumps.
