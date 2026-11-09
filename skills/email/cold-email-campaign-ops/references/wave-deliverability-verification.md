# Post-wave deliverability verification (Gmail sender, himalaya v2)

Purpose: turn "N/N SENT" into evidence. A wave log proves the transport accepted the message;
these checks are what prove (or disprove) that it reached a mailbox.

## Exact command set (run after the last send, bare, no pipes)

```bash
# 1. Inbox: bounces + auto-replies (top 25 covers a wave that finished within the hour)
himalaya envelope list -a gmail -m INBOX -s 25

# 2. Spam folder: NDRs also land here; quoted mailbox path works even without an alias
himalaya envelope list -a gmail -m "[Gmail]/Spam" -s 15

# 3. Sent-side record of the wave (alias required: sent = "[Gmail]/Sent Mail")
himalaya envelope list -a gmail -m sent -s 25

# 4. Links the copy carried
curl -s -o /dev/null -w '%{http_code} ' https://<site>/<path>
```

Notes for this himalaya build (verified 2026-09-12):

- `envelope list` accepts `-a <account>` and `-m <mailbox>`; there is **no `-q` flag** — the search
  DSL is positional and space-separated (`himalaya envelope list -m INBOX from postmaster`).
- No `folder list` subcommand in this build — address `"[Gmail]/Spam"` / `"[Gmail]/All Mail"`
  directly with `-m`.
- Run bare: a `| tail` / `| python3 -c` pipeline masks the real exit code.

## Interpretation table

| Observation | Meaning | Action |
|---|---|---|
| `Undeliverable: <your subject>` from `postmaster@<their-domain>` | Hard bounce, mailbox/domain gone | status=BOUNCE, drop address, cut the segment from wave N+1 |
| Auto-reply from the target's own domain ("Thank You for Contacting", ticket ack) | Delivered — cleared their inbound filters | record as delivery proof, do NOT count as engagement |
| Zero bounces, zero auto-replies | Accepted but unproven | say exactly that; offer the 48h watch |
| Wave NDR sitting in `[Gmail]/Spam` | Your inbound is being filtered too → prospect replies may be invisible | watch Spam, not just INBOX |
| Link returns 404/000 after the send | Copy shipped dead | fix for the follow-up touch; never bulk-resend |

## India desk wave — observed evidence (2026-09-12, AZ Consultants India)

- 20/20 emails `SENT` (15:42-16:29 IST, 2-min gaps), 11/11 SMS accepted by the TextBee gateway.
- 1 hard bounce: Coretech India Solutions (`postmaster@thecoretech.com`) — IT firm on an HVAC
  roster, i.e. exactly the predicted-low-fit segment. 19/20 no NDR.
- 1 auto-reply: Creature Industry support ack → positive delivery evidence.
- Spam folder held only Aug KSA-wave bounces (burgerizzr, kalbepharma) — none from this wave.
- Both copy links 200 (pipeline + root).

## Reporting shape that satisfied the requirement

Sent count + first/last send timestamps + the named bounce + the auto-reply-as-proof + spam-folder
result + link status codes. Then the two OFFERS (48h watch cron, 7-day follow-up) as questions,
not as actions already taken.
