# Himalaya v2.1.0 CLI — working commands (Gmail)

Verified 2026-08-24 on the Oracle VM during Invertio LEAP wave reply-triage.
Config: `~/.config/himalaya/config.toml`, account `gmail` (azengineeringapp@gmail.com),
password via `~/.local/bin/himalaya-gmail-pass.sh` reading `~/.hermes/.env`.

## Config fix: mailbox aliases (REQUIRED)

v2 errors `Mailbox is required: pass the mailbox name or alias...` on every
`envelope list` / `envelope search` until this section exists in the config:

```toml
[mailbox.alias]
inbox = "INBOX"
sent = "[Gmail]/Sent Mail"
drafts = "[Gmail]/Drafts"
trash = "[Gmail]/Trash"
archive = "[Gmail]/All Mail"
```

## Working commands

```bash
himalaya account list                                  # accounts + which is default
himalaya envelope list -s 10                           # recent inbox envelopes (needs alias)
himalaya envelope search "from foodics"                # inbox search — SPACE-separated DSL
himalaya envelope search -m sent "to foodics"          # sent-side search (mailbox required)
himalaya message read 360                              # full headers + body of envelope id
```

## Gotchas

- **Search DSL is space-separated**: `from foodics` ✓ ; `from:foodics.com` ✗
  (parse error `expected space after 'from'`). Same for `to`. The v1 `from:x@y` syntax is gone.
- `envelope search` also requires the mailbox (`-m sent`, `-m inbox`, ...).
- `--output json` did NOT emit parseable JSON on stdout in this version
  (`python3 -c json.load` failed on empty/other output). Use the table output +
  `himalaya message read <id>` instead of scripting against JSON.
- Messages sent via smtplib/sendmail through smtp.gmail.com DO appear in
  `[Gmail]/Sent Mail` — Gmail stores SMTP-sent mail server-side. The Sent folder
  is therefore a reliable outbound record (search it with `-m sent "to <domain>"`).
- Run himalaya BARE (no `| head`, no `| python3 -c` pipes): pipeline exit codes
  mask real failures (reported exit 0 while the actual command errored).
- Mailbox names are case-insensitive against the alias (`-m sent` == `-m Sent`).
- **No `-q` flag** on `envelope list` in this build — the search DSL is positional and
  space-separated (`himalaya envelope list -a gmail -m INBOX from postmaster`; `subject foo bar`).
- **No `folder list` subcommand** in this build. Read non-aliased folders directly with a quoted
  mailbox path: `himalaya envelope list -a gmail -m "[Gmail]/Spam" -s 15`,
  `-m "[Gmail]/All Mail"`, `-m "INBOX"`.
- Deliverability / bounce / spam-folder reading after an outbound wave:
  `references/wave-deliverability-verification.md` in this skill.
