# Campaign accounts & automation inventory

## Sender account map

- **azengineeringapp@gmail.com** — SHARED sender/reader for ALL cold-email campaigns:
  - Invertio FM followups (agent jobs) + FM inbox monitor (IMAP read, every 6h)
  - Invertio LEAP followup #1 (Day 3) / #2 (post-LEAP wrap)
  - AVVS / Triatek Venturi outreach (sends with display name "Triatek Venturi" — same account, client identity)
  - Credentials: `GMAIL_USER` / `GMAIL_APP_PASSWORD` in `~/.hermes/.env`; himalaya config `~/.config/himalaya/config.toml` (aliases inbox/sent)
- **aamir1zahran@gmail.com** — personal account (AAMIR_GMAIL_USER / AAMIR_GMAIL_APP_PASSWORD). NOT used by campaign automations; used for personal/Vaibhav/client email checks.

## Automation set (hermes cron — `~/.hermes/cron/jobs.json`)

| Job | Schedule | Type | Account touch |
|---|---|---|---|
| Invertio FM inbox monitor | every 6h | no_agent script `invertio_fm_inbox_watch.py` | reads azengineeringapp (IMAP) |
| Invertio FM followup #1 / #2 / #3 | 27 Aug 06:00 / 30 Aug / 2 Sep | agent | sends azengineeringapp |
| AVVS Venturi followup #1 | 27 Aug 07:00 | no_agent wrapper → `~/clients/AVVS-Triatek/outreach/send_venturi_followup.py` (smtplib/himalaya) | sends azengineeringapp |
| Invertio LEAP followup #1 (Day 3) | 27 Aug 08:00 | no_agent script `send_invertio_leap_followup1.py`, workdir `~/clients/invertio/email-pitch` | sends azengineeringapp |
| Invertio LEAP followup #2 (post-LEAP) | 7 Sep 08:00 | no_agent script `send_invertio_leap_followup2.py` | sends azengineeringapp |

## Audit commands (disable/verify pass)

- `grep -lE 'azengineeringapp|GMAIL_USER|FROM_ADDR|himalaya|@gmail' ~/.hermes/scripts/*.py`
- Read each cron wrapper (may be <400 bytes) and grep any subprocess target in client dirs (`~/clients/*/outreach`, `~/clients/*/email-pitch`).
- Pause state is transient: always re-run `cronjob action=list` before assuming a job's current state or ID.

## Status note

All 7 azengineeringapp-touching jobs paused 2026-08-26 (user request: "gmail automation temporary disable... if tokens are used or get leaked"). Resume trigger phrase used: "gmail automation resume karo". Sanad LinkedIn video engine (Wed+Thu 4pm) is a separate agent job — posts to LinkedIn only, does NOT touch gmail; left running unless user asks.
