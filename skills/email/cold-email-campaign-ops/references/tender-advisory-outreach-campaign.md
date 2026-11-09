# Tender / Bid-Advisory Cold Outreach (AZ Consultants pattern)

Reusable recipe for Aamir's **Az. Consultants** brand (Pan-India tender & bid advisory):
build a demand-signal lead list of firms that need a tender specialist, then run a
genuine, non-spam email + SMS wave from `azengineeringapp@gmail.com`.

Brand isolation (HARD): Az. Consultants copy/workspace me HMW/AVVS/Sanad ka naam kabhi nahi.
Sender display name = personal genuine name (`Aamir Zameer`), never a client brand.

## 1. Lead list: demand signals first

Strongest hook = a firm that is **hiring a tender/bid executive right now** (they have more
bids than their team can review). Secondary = tender-active sectors (FM/MEP, fire & life
safety, HVAC/R, water/waste water, infra, defence-adjacent suppliers, drones/telecom).

Sources that worked:

- Tender/hiring demand signals: job posts mentioning "tender executive / bid manager /
  proposal engineer" + company name, then the firm's own site for contacts.
- Tender-active company discovery: sector scan + `site:` queries; company sites for
  `info@ / enquiries@ / sales@ / contact@` addresses; IndiaMART-type listings only as a
  last resort (many aggregated/placeholder addresses).

## 2. Contact QA (do this before ANY send)

- **ONE contact per firm per channel.** Multiple addresses at one firm in the same wave
  read as spam and can flag the whole wave. Rank preference:
  `info@ > enquir* > sales@ > contact@ > mail@ > account@ > first-person@`.
- Drop placeholder and broker noise: `firstname.lastname@`, aggregator/data-broker domains
  (tracxn, tendershark, zoominfo and similar), mismatched-domain hits (a Medicare address
  under a GMP firm), and anything you cannot tie back to the firm's own site.
- Cross-check every surviving address/phone against the firm record in the raw scrape file;
  an address that only appears in one source without a matching company record is dropped.
- Indian mobile validation (used for the SMS wave):
  strip non-digits → drop leading `91` / `0` → require 10 digits starting `6-9` →
  reject `62`–`65` leading pairs (landline STD codes: 641 Coimbatore, 631 Bhagalpur,
  652 Dhanbad, ...) → reject `0000/5555`-style tails. Dedupe to one mobile per firm.
- Keep the FULL original scrape (98 firms this run) in the workbook as the "lead bank"
  sheet; wave sheets only carry the contacted subset. Never throw away uncontacted firms —
  they are wave 2.

## 3. Copy pattern (curiosity-driven, no pitch)

Email subject: `<Firm> - hiring a tender executive: the annexure gap` (hiring firms) /
`<Firm> - tender submissions: the annexure that quietly kills bids` (others).

Body skeleton (plain text, ~200 words, no images/attachments/tracking):

1. One tailored line naming the firm + the signal seen.
2. The curiosity hook: "most bids are not lost on price - they are lost in the annexures
   (PQ document, expired validity, unflagged deviation sheet)".
3. What is offered, in one sentence each: eligibility/PQ mapping, BOQ & rate build-up,
   annexure-by-annexure rejection check, tech write-up vs every sub-criterion, deviation &
   risk register before the fee is paid.
4. 2-3 authoritative live channel links (GeM `bidplus.gem.gov.in/all-bids`, CPPP
   `eprocure.gov.in/cppp/`, State index `india.gov.in/tenders`) - real links raise
   legitimacy and deliverability.
5. Reply keyword hook: `reply "FUNNEL"` → the 150+ channel Pan-India tender funnel file.
   Curiosity + a small ask, no fee, no pitch.
6. Signature: name, "Contracts and Tender Advisory | Pan India", LinkedIn
   `https://www.linkedin.com/in/aamirzameer`, the gmail address.

SMS (single segment, ASCII only, firm name capped 22 chars):

```
<Firm>: bids die on annexures, not price. Free 48hr bid check, 1 live tender.
Reply FUNNEL for list. Aamir - AZ Consultants. STOP to opt out
```
(151 chars with a 22-char firm → 1 GSM-7 SMS. Assert `len(text) <= 160` in code, and never
let an em-dash/curly quote in - that flips to UCS-2 and burns 2-3x quota.)

## 4. Pacing, scheduling, and reporting

- Do NOT send inline in the agent session: 24 sends x 75-165 s jitter ≈ 45 min of runtime.
- Run the wave from a **systemd user timer** (oneshot service + one-shot `OnCalendar` in UTC,
  `Persistent=false`, `AccuracySec=30s`) so it survives the session ending.
- The wave script must be **idempotent**: check a marker file (`.email_wave_done`) and exit
  if already fired - a timer re-fire must never double-send a cold list.
- The sender script owns the loop: per-recipient jitter (email 75-165 s, SMS 25-55 s),
  append every result to `sent_log.jsonl`, and print a `WAVE DONE: sent N of M` summary to
  `wave_email.out` / `wave_sms.out`.
- Schedule at the **recipient's** genuine business hours: 10:00 IST email / 10:45 IST SMS
  = 04:30 / 05:15 UTC on this (UTC) VM. Night-time sends read as automation.
- Report back with a **one-shot cron job** set ~45-75 min after the wave that reads the
  `.out` logs and writes a short Hinglish summary to the origin chat
  (`enabled_toolsets: [file, terminal]`). Cheaper and safer than a long-running job.
- Volume: ≤25 emails/day per sending identity; the SMS wave is separate-channel, so keep
  one touch per firm per channel and let the SMS arrive after the email, not simultaneously.

## 5. Verification (before claiming success)

- Test email to the owner's testing account FIRST (`aamir1zahran@gmail.com`); confirm it is
  readable there and `From:` shows the personal name, not the account's configured brand
  (`himalaya envelope list -a aamir1zahran -s 3`).
- Dry-run the wave (`--email-limit 2 --dry`, `--sms-limit 2 --dry`) and confirm the loop
  prints per-recipient OK + a `WAVE DONE` line before scheduling.
- Live SMS test to the owner's own handset and get explicit arrival confirmation BEFORE
  wiring the SMS wave (see `sms-campaign-ops` for the international-A2P caveat).
- Workbook deliverable: sheets `Email wave (N)`, `SMS wave (N)`, `Full lead bank`, `Notes`
  (sender, schedule in IST, guardrails, reply hook, file names).

## 6. Files from the reference run (Aug/Sep 2026)

`/home/ubuntu/az_consultants/outreach/`: `leads_send.json` (email wave), `sms_send.json`
(SMS wave), `leads_clean.json` (QA'd scrape), `send_campaign.py` (modes: `--render`,
`--test-email`, `--test-sms`, `--email-limit`, `--sms-limit`, `--dry`), `tmpl.py` (copy +
sector/city maps + SMS renderer), `mkxlsx.py`, `wave_email.sh` / `wave_sms.sh` (idempotent
wrappers), `wave_email.out` / `wave_sms.out`, `sent_log.jsonl`.
Timer units: `~/.config/systemd/user/az-{email,sms}-wave.{service,timer}`.
