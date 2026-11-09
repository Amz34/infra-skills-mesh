# Credential hygiene + DR hardening (worked case, 2026-09-10)

Two jobs done back-to-back on the Sanad n8n instance: decommission a duplicate IMAP
credential, and put n8n inside the restore path. Both were green when they looked finished and
both had a trap that only showed up on the *next* check. Numbers below are real.

## 1. Retiring a duplicate credential (safe order)

Situation: two `imap` credential records, `CredImap001` and `Gmail IMAP (Luxe Wave)`
(`Ixnx9EJ8sR7S6KtR`), both pointing at the same mailbox. The second was referenced only by the
retired `Sanas Lead Pipeline` (`tdZNdqTc16UqJ7MT`), kept as a rollback artifact.

Order that works — **repoint before delete**:

1. **Prove "same mailbox" without leaking secrets.** The n8n CLI against the *live* user folder
   returned rc=1 with empty stdout. Running `export:credentials --all --decrypted --output=<tmp>`
   against an **isolated snapshot** worked:
   copy `~/.n8n/database.sqlite` (via `sqlite3` `.backup` / `Connection.backup`) + `~/.n8n/config`
   into `/tmp/n8n-credcheck/.n8n`, then `N8N_USER_FOLDER=/tmp/n8n-credcheck`.
   Compare `host` / `user` and print **booleans + a summary** (`host_equal=True user_equal=True
   pwd_equal=False`) — never print the passwords. Verdict: same mailbox, different stored
   password → the Luxe Wave copy was the **stale** one.
2. **Repoint the referencing workflow first.** `python3 ~/work/n8n/n8n_api.py update
   tdZNdqTc16UqJ7MT <body.json>` (PUT eats a full body: `{name, nodes, connections, settings}`)
   → 200, `active` stays false, node count unchanged. Now nothing references the doomed id.
3. **Then delete**: `DELETE /api/v1/credentials/{id}` → 200. Result: 8 credentials, exactly one
   `imap`, every workflow's refs still resolve, router healthy.
4. **Refresh the watchdog secrets cache — this is the trap.** `~/.config/n8n/watchdog_secrets.json`
   stores the decrypted `host/user/password` per credential **and no credential ids**, so after the
   delete the watchdog happily kept IMAP-LOGIN-testing a credential that no longer existed, and
   reported `all checks healthy`. Re-run `make_imap_cache.py`, then assert the cache now holds
   exactly one `imap` entry (and that the file is mode 600).
5. Afterwards `grep -rl "<deleted-id>"` over `~/ops/` and `~/.hermes/`: only historical docs may
   still mention it. If a *script or cache* still does, the cleanup is incomplete.
6. Keep the retired workflow **repointed, not deleted** — it stays a working rollback artifact.

### `make_imap_cache.py` shape (why it needs a snapshot)

Export to a **file** (`--output=<tmp>`), not stdout — parsing stdout produced rc=1 / empty output
and a `JSONDecodeError`. Run it against a DB copy with `N8N_USER_FOLDER=<snapshot>`, read the JSON
file, then `shutil.rmtree` the snapshot immediately (it holds the encryption key + decrypted
credentials). Refuse to write the cache if the export came back empty — a silent empty cache makes
the watchdog blind, which is worse than a loud failure. Refresh it **whenever any IMAP/DeepSeek
credential changes**.

## 2. DR: n8n was missing from the restore path entirely

`backup.sh` block 1g archived `n8n/database.sqlite` + `n8n/env`, but `ops/restore.sh` had **no n8n
block at all** — a rebuilt VM would come back with Hermes and **no n8n**: no workflows, no
credentials, no history. The weekly drill also never looked at n8n, so nothing would have caught it.

Fixes:

- `ops/restore.sh`: restore `~/.n8n/database.sqlite` (keeping
  `database.sqlite.pre-restore-<ts>` beside it) and `/etc/n8n/env` (encryption key + API key).
  Under `RESTORE_DRY_RUN=1` the env lands in `$HOME/n8n-env.restored` and `sudo` is never invoked.
- `ops/verify/restore_verify.sh`: +3 checks — n8n `pragma integrity_check`, `workflow_entity`
  count > 0, env extracted — so the drill fails loudly rather than "verifying" a VM with no n8n.
- `~/.hermes/scripts/n8n_restore_drill_weekly.sh` (thin shim, silent on success / loud + non-zero
  on failure) → Hermes cron `9ba302fe1c2b`, `0 5 * * 0`, `no_agent=true`.
- `TESTED`: shim rc=0 in 20 s with zero output; full drill rc=0 (archive
  `sanad-backup-20260910_062916.tar.gz.gpg`, 1348.9 MB → DB 11 MB, `integrity ok`, 4 workflows,
  9 credentials, credentials decrypted with the prod key); restore dry-run rc=0 followed by
  `restore_verify.sh` → `RESULT: 11 passed, 0 failed`.

### Cleanup traps found here

- Anything extracted from the backup archive comes out **root-owned**: `rm -rf /tmp/n8n-path-test`
  as the normal user leaves a residue behind. `sudo -n rm -rf` and then confirm the path is gone.
- Those temp trees carry `config` (**the encryption key**) and decrypted credentials — purge them
  before reporting the task done, and never leave one in `/tmp` overnight.
- A restore drill that only proves "the DB file exists" is worthless: decrypt the credentials
  (`export:credentials --all --decrypted`) as part of the proof.

## Doc/script edit habit that paid off

Long edits to the audit doc / SKILL.md were done in **small, separate** patches, and every write
was followed by a targeted re-read (`search_files` for the heading, `read_file` on the changed
range) plus `bash -n` / `py_compile` on edited scripts. Verify-after-write is what caught the
stale "all 4 expected workflow IDs" / "Both IMAP credentials still LOGIN" lines in
`~/ops/kb/n8n-audit-and-plan.md` after the credential delete — the doc had drifted from reality and
the watchdog's `EXPECTED_IDS` (3 active) was the source of truth.
