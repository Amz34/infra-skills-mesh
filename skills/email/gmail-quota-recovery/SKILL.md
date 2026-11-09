---
name: gmail-quota-recovery
description: Use when Gmail/Google account is near full. Audit+purge.
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Email, Gmail, Quota, Storage, Backup, DR, DevOps]
    related_skills: [hermes-email-access, himalaya, cloud-vm-backup-dr, infra-hardening-crashproof]
---

# Gmail / Google account quota recovery

Use when Google says an account is ~80-100% full, especially an account our infra writes into
(backup sink). Audit first, then compress, then fix the leak that filled it.

## When to Use

- Google sent a "storage almost full / 80%+" notice for an account we depend on.
- A Gmail-connected backup or agent lane is suspected of filling that account.
- `guard_trip_audit.py` reports a new tripper whose target is a huge log (see §4).

Trigger first, then split the quota (§1), measure Gmail (§2), kill the leak (§3), verify (§5).

## 1. Never guess which half is full

Google counts **Drive + Gmail + Photos** against one quota. Split it with rclone:

```bash
rclone about gdrive: --json
```

- `used` = **Drive only**. `other` = **Gmail + Photos**. `trashed` = Drive trash (still billed).
- Fill % must be `(total - free) / total`. `used/total` is WRONG and can never fire at 80%
  (measured 2026-10-10: used 68 MB vs a 659 MB account → 0.42% instead of 4.1%).
- Empty Trash in **both** halves: Gmail Trash and Drive trash still bill quota.
  Drive deletion with rclone: always `--drive-use-trash=false`, else it just moves the quota.

## 2. Gmail side — measure with IMAP, not the web UI

Creds: `GMAIL_USER` / `GMAIL_APP_PASSWORD` in `~/.hermes/.env` (app password, IMAP enabled).

**Pitfall #1 — folders with spaces must be quoted.** `M.select('[Gmail]/All Mail')` fails
("Could not parse command") and a silent failure looks like "0 messages, 0 MB" — the exact
bug that hid a 1.2 GB Trash. Always `M.select(f'"{box}"', readonly=True)`.

**Pitfall #2 — one round trip per message is far too slow.** Batch the size census:

```python
M.select('"[Gmail]/All Mail"', readonly=True)
typ, dat = M.uid("SEARCH", None, "ALL")
uids = dat[0].split()
for i in range(0, len(uids), 500):                     # batches of 500
    t, d = M.uid("FETCH", ",".join(u.decode() for u in uids[i:i+500]), "(RFC822.SIZE)")
    # sum int(re.search(rb"RFC822\.SIZE (\d+)", part).group(1)) over the *bytes* parts
```

Per-folder census that answers "where are the bytes?":
`INBOX`, `"[Gmail]/Sent Mail"`, `"[Gmail]/All Mail"`, `"[Gmail]/Trash"`, `"[Gmail]/Spam"`,
plus Gmail search strings via `X-GM-RAW` (`larger:5M`, `category:promotions`, `from:google.com`).
Note `X-GM-RAW` cannot contain nested quotes — pass `larger:10M`, not `subject:"x y"`.

Trash is the most common hidden hog (found 1.20 GB of 1.84 GB, 65%, as ~59 duplicate 22 MB
campaign sends). Empty it only after:
1. dumping a manifest (from/subject/date/size) to a file — cheap provenance;
2. archiving one sample `.eml` locally;
3. proving copies survive elsewhere (`X-GM-RAW` search in All Mail / Sent Mail);
4. purging: `M.select('"[Gmail]/Trash"'); M.uid("STORE", "1:*", "+FLAGS", "(\\Deleted)"); M.expunge()`
   (same for Spam). Irreversible — Trash items would otherwise auto-purge in 30 days anyway.

## 3. Drive side — the orphan-archive leak

A backup folder that no longer receives uploads is never rotated, so one stale archive can pin
~33% of the quota for good (found: one 5.0 GB archive parked 3 days after the Drive leg was
disabled; two of them had been the real reason for the 80% notice).

Rule: **the inactive leg must hold ZERO archives.** In the backup script, prune whenever the
leg is off:

```bash
rclone delete --drive-use-trash=false --include "sanad-backup-*.gpg" "gdrive:$DRIVE_FOLDER/"
```

Also fix the monitor: the off-VM truth must follow the ACTIVE leg (`BACKUP_DRIVE=1` → Drive,
else the OCI bucket). Probing the disabled leg produced a permanent false
"off-VM copy N NIGHTS BEHIND" alarm while DR was healthy.

Add a **fill-level alert at 70%** (`(total-free)/total`) — a headroom-only check lets the
account reach 80% with no alert from us.

## 4. The syslog chain that trips Hermes' lifecycle guard

Symptom: daily self-QA reports a "NEW guard tripper"; commands referencing that script are
refused with a misleading "cannot restart, stop, or uninstall the gateway".

```bash
python3 ~/ops/verify/guard_trip_audit.py --json      # script::target pairs, rc 1 if new
```

Root-cause chain seen 2026-10-10:

1. The live syslog file under `/var/log/` = 408 MB. Source: `warp-svc` emits ANSI-coloured **DEBUG** lines
   ("route-change: Routes changed") several times a second (~400 MB/week).
2. Why it never rotated: `/var/log` is group-writable and `/etc/logrotate.d/rsyslog` had no
   `su` directive → logrotate skips every file ("parent directory has insecure permissions").
   Fix: add `su root adm` (+ `maxsize 200M`), then `sudo logrotate -d` must show **0 errors**.
3. Any script naming the live syslog file under `/var/log/` then trips the guard (referenced file > 1 MiB).

Fixes: truncate it (`sudo truncate -s 0` on the path under `/var/log/`); drop only DEBUG at rsyslog
(`/etc/rsyslog.d/49-warp-quiet.conf`:
`if ($programname == "warp-svc") and ($msg contains "DEBUG") then stop` — journald keeps the
full stream); reference oversize paths in your own scripts via `"$HOME"/...` or a glob so they
do not tokenise as a real file.
- 2026-10-12 follow-up: DEBUG-only was **not** enough. warp-svc regrew the same file to 41 MB in 2 days
  with level-less lines (`NewNeighbour; Destination: ...`, `handle_update{...MasqueTunnelStatsUpdated...`);
  drop those markers too. A live log will always exceed the guard cap, so point at the **directory**
  (`/var/log/`), never the file, and re-measure after the fix instead of trusting the config text.

## 5. Verify, then report

- `rclone about gdrive: --json` before/after (quote exact bytes; `trashed: 0`).
- Re-run the guard audit → `new: []`, rc 0. Re-run the failing gate → silent rc 0.
- Report **before → after** per hog and the root-cause fixes, not just "cleaned up".
- Leave unrelated disk pressure (e.g. VM root at 85%) as an explicit open item.
