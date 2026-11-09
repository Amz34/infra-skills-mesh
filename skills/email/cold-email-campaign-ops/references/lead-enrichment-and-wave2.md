# Lead enrichment + wave 2 (worked recipe)

Session: AZ Consultants tender-advisory campaign, Sep 2026. Channel-agnostic — reuse for any
"we have a firm list, most have no contact details" situation.

Shape: **bank → wave 1 → enrich the remainder → wave 2**, each wave a separate scheduled campaign
with its own marker/timer, both reported.

## 0. Counting first (never guess wave size)

```
bank (all firms found)        98
wave 1: published email       24
wave 1: SMS-able mobiles      25
hiring-signal firms (job ad)   7
remainder with no contact     74   <- enrichment target
wave 2 after enrichment: 24 emails / 14 mobiles
```
Report these four numbers to the user every time the list changes. A wave of "24" means 24 firms
that survived QA — not 24 rows in a file.

## 1. Bulk enrichment loop (this is where the volume comes from)

Bulk search must run inside `execute_code` (only place `web_search` exists), and long inline
payloads get blocked by the command parser → **put the firm list + the loop in a
`.py` module on disk, then import it from a 3-line `execute_code` snippet**:

```python
# enrich_module.py on disk:  FIRMS = [...]
def run_batch(lo, hi):
    ...
# execute_code:
import sys; sys.path.insert(0, '/home/ubuntu/az_consultants/outreach')
import enrich_module as e
print(e.run_batch(0, 25))
```
Batch ~25 firms per `execute_code` call and append results to a JSONL file after each batch, so a
timeout loses one batch, not the run.

Query shape that worked per firm: `<firm name> <city> email contact`, then
`"<firm>" tender OR bids`, plus a site-scoped pass (`site:<their-domain>`) when a domain is known.

## 2. Harvest rules (yield is low — accept it)

- Best signal: `mailto:` and `tel:` inside the firm's OWN site (curl the contact page; don't render).
- Aggregator/directory domains: **skip entirely** (IndiaMART, TradeIndia, ExportersIndia,
  go4worldbusiness, Justdial, tracxn, tendershark, eworldtradefair, zaubacorp, Tofler, LinkedIn,
  Facebook) — addresses are hidden behind JS/forms and the hits are broker inboxes.
- Substring token matching beats equality: firm "Integra FM" → domain `integrafm.com` matches only
  with a substring/prefix test. But substring matching also produces unrelated-domain false
  positives (e.g. a preschool domain for an unrelated query) → keep a per-campaign
  `BAD_DOMAINS` blacklist and log every rejection with its reason.
- Placeholder locals (`firstname@`, `your.email@`), `+` tags and mismatched domains = reject.
- Prefer ONE address per firm (first surviving), then mark the firm done for that wave.

## 3. Wave-2 build + scheduling

```bash
# per wave: builder -> send file -> wrapper -> timer pair
python3 wave2.py          # -> wave2_send.json  (+ prints "emails N | max sms LEN")
python3 bs2.py            # phone normalizer (strip \D, drop 91, reject 62-65 STD)
```
- `wave2.py` writes its own send files; the sender picks them up via env override
  (`LEADS_FILE=wave2_send.json`, `SMS_FILE=wave2_send.json`) so the wave-1 files stay frozen as the
  dedupe baseline.
- Alarm the length check across the WHOLE list (`max sms 159`), not one sample — the longest firm
  name is what decides 1 SMS vs 2.
- Timer units: `az-email-wave2.service/.timer`, `az-sms-wave2.service/.timer`, one-shot
  `OnCalendar=2026-09-14 04:30:00 UTC` (= 10:00 IST), `Persistent=false`, every wrapper guarded by
  its own `.email_wave2_done` marker writing `wave2_*.out`.
- `systemctl --user daemon-reload && systemctl --user enable --now az-email-wave2.timer` then
  `systemctl --user list-timers 'az-*'` — all four units (wave1 email/SMS + wave2 email/SMS) must
  appear; report the table to the user.
- Separate one-shot report cron per wave (11:30 IST) reading `wave_*.out` + the send status files.

## 4. Deliverable refresh

Rebuild the campaign workbook (not a new file): sheets `Wave 1 emails / Wave 2 emails / SMS 1 /
SMS 2 / bank / site links`, from the same JSON the sender uses, so counts can't drift. Print
`saved <path> w1 N w2 N s1 N s2 N` as the machine-checkable summary.

## 5. Verification bar before telling the user "wave armed"

1. `python3 send_campaign.py --render` exits 0 (renders every lead).
2. Send-file counts printed and non-zero; zero-length SMS list is a silent failure — assert it.
3. `systemctl --user list-timers` shows the next fire time for each unit.
4. One live test message to the owner's own handset/address earlier in the campaign (arrival
   confirmed by the user) is what licenses the real wave.
5. Report honestly: which wave produced how many contacts, and anything held back (e.g. a firm kept
   out because the only address was an aggregator inbox).

## Pitfalls

- Long inline shell/python payloads are refused or mangled → write the step to a file and run it.
- Truncated tool output ("exit 0, 1 lines") hides the real numbers: redirect to `/tmp/x.txt` and
  read back a slice (`head -c`), or have the script print one compact summary line.
- Reusing wave 1's marker file or unit suppresses wave 2 with no error.
- A `patch` that fails with "could not find match" means the old_string was guessed, not read —
  grep the exact string first (`grep -o ".\{20\}funnel.\{20\}"`).
