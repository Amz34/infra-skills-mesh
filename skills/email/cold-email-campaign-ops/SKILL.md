---
name: cold-email-campaign-ops
description: "Use when running cold-email waves or triaging replies."
version: 0.1.0
metadata:
  hermes:
    tags: [Email, Outreach, Cold-Email, Campaign, Lead-Gen]
    related_skills: [b2b-outreach-email, himalaya, email-inbox-triage]
---

> **Claim-integrity gate (mandatory, 2026-09-15):** every claim in this output must be provable.
> Before ship run `python3 ~/ops/verify/claim_integrity.py <mode> <file|dir>` and clear all HIGH
> with `[src: ...]` evidence or `[claim-ok: reason]`. Rule: `~/brains/ops/rules/content-integrity.md`.
> Skill: `content-integrity-guardrail`.

# Cold-Email Campaign Ops

Operate the full lifecycle of B2B cold-email outreach campaigns (Invertio LEAP waves, AVVS, Sanad lead-gen): sending waves safely, keeping the prospect tracker honest, and expertly triaging everything that comes back — especially automated replies that look like human interest but are not.

## When to Use

- "Send the next wave" / "wave send karo"
- "Review this campaign reply and take action" (inbox response to an outbound pitch)
- A bounce, autoresponder, or gate-reply needs a judgment call
- Updating prospect CSVs (status/notes) after a send or a response
- Any deliverability / sender-reputation decision about a cold-email address
- "Campaign/gmail automation band karo" — temporary pause of everything tied to a sender account

## 1. Sending waves

- Script pattern (see `send_invertio_leap.py` in the client dir): smtplib + Gmail app password from `~/.hermes/.env` (`GMAIL_APP_PASSWORD`), multipart plain+html, CID-embedded images, PDF attachment, `{{Contact}}` slot personalization per recipient role.
- ALWAYS: test-send to the owner's address first (`python3 send_*.py test`), then dry-run the wave (`--dry`) to preview recipients, then real send.
- ~25s delay between sends (Gmail rate-limit safety). FROM name = genuine human sender name (spam-safe).
- Emails sent via smtplib through smtp.gmail.com DO land in Gmail `[Gmail]/Sent Mail` — the Sent folder is a reliable outbound record for verification.
- Waves go only to CSV rows with verified addresses (email_confidence=VERIFIED) and approved fit; never invent recipients.

## 1b. Scheduling a wave at genuine business hours (systemd user timer pattern)

A wave is not "sent" when it is written - it is sent when it fires at a **recipient-local
business hour**, paced, with a durable log. Do not run the jitter loop inline in the agent
session (24 sends x 75-165 s ≈ 45 min of runtime, and the session can end mid-wave).

- Convert to **recipient** time and schedule in UTC (this VM runs UTC): 10:00 IST email /
  10:45 IST SMS = `04:30` / `05:15 UTC`. A 2-3 AM send for the recipient reads as automation.
- Pattern that works: `~/.config/systemd/user/<campaign>-wave.service` (`Type=oneshot`,
  `ExecStart=/bin/bash .../wave_<ch>.sh` with `WorkingDirectory=` set) + a one-shot
  `OnCalendar=<date> <HH:MM>:00 UTC` timer, `Persistent=false`, `AccuracySec=30s`, then
  `systemctl --user daemon-reload && systemctl --user enable --now <name>.timer`.
- **Idempotency is mandatory**: the wrapper checks a marker file (`.email_wave_done`) and
  exits if present, so a re-fire or a reboot never double-sends a cold list.
- The sender script owns the loop: one recipient at a time, per-recipient jitter (email
  75-165 s, SMS 25-55 s), append each result to `sent_log.jsonl`, and print
  `WAVE DONE: sent N of M` into `wave_<ch>.out`. Support `--dry` so the same loop can be
  verified with zero sends before scheduling.
- Report with a **one-shot cron job** ~45-75 min after the wave that reads the `.out` logs
  and posts a short summary to the origin chat (`enabled_toolsets: [file, terminal]`).
  Cheaper and safer than keeping a long-running job alive.
- Volume/pacing: ≤25 emails/day per sending identity; one contact per firm per channel;
  don't email and SMS the same firm simultaneously (SMS lands after the email).

Full worked example (tender-advisory list, copy templates, QA gates, timer units, workbook):
`references/tender-advisory-outreach-campaign.md`.

### 1c. Wave N+1 (same campaign, newly-enriched prospects)

A second wave is legitimate and expected, but it must be built as its own campaign, not as
"run the same file again".

- **Source it from the firms wave 1 could NOT reach** (no published address) → enrich → contact-QA
  → schedule. Then **dedupe the new list against every previous wave's sent file**
  (`leads_send.json`, `sms_send.json`) so no firm is contacted twice for the same offer
  (`scripts/contact_qa.py` does the dedupe + gates in one pass).
- **Every wave gets its own marker, wrapper and timer pair** (`wave2_email.sh` → `.email_wave2_done`,
  `az-email-wave2.timer`, …, `<date> 04:30 UTC`). Never reuse wave 1's unit or marker: its
  `.email_wave_done` would silently suppress wave 2, and a wave-2 failure would be invisible.
  Give each wave its own one-shot report cron too.
- **Space the waves ≥1 business day apart** (Fri wave → Mon wave). Two waves in the same hour at one
  small firm list reads as a mail-merge campaign, not a person.
- Enrichment reality check (don't over-promise the user a big wave 2): harvesting contacts from a
  firm's own site yields a handful per dozen firms; directory/aggregator domains (IndiaMART,
  TradeIndia, Justdial, go4worldbusiness, exportersindia, tracxn, tendershark) hide addresses behind
  JS/forms and are not worth a fetch. The quality comes from QA gates (one per firm, domain must
  match the firm, no `firstname@` placeholders), not from scraping more. Recipe, yield numbers and
  the bulk-`web_search` helper pattern: `references/lead-enrichment-and-wave2.md`.

## 1d. When the site/domain in the copy changes or dies (link audit)

Campaign copy is baked in several layers — patch ONE and the wave still ships a dead link: the
shared template module (`tmpl.py`: `body()`, `sms()`), a **fallback renderer inside the sender
script** (used only if the template import fails), generated attachments (`*.xlsx` from
`mkxlsx2.py` — the file prospects get after replying), and the queue JSONs. This bit us when a
client site was deleted mid-campaign with 2 wave timers still pending.

- **Find occurrences by content, not filename**: regex over the tree for text, and **`zipfile`
  for xlsx/zip artifacts** (open the archive, regex the `.xml` members — `grep` is blind to them).
  Delete stale `__pycache__/*.pyc` too; they keep the old string and pollute later greps.
- **Establish which renderer is live** with a dry run — `python3 send_campaign.py --render`
  (prints sample email + SMS, sends nothing) and grep the output for the URL. Do not "fix" the
  in-script fallback and assume the template module agrees; the module wins when importable.
- **SMS: recompute length after ANY URL change, per lead (worst case).** A longer domain silently
  pushes a 1-SMS message to 2 SMS — double quota and it reads as bulk. Rule: worst case ≤160
  GSM-7 chars.
  ```python
  import importlib.util, json
  spec = importlib.util.spec_from_file_location('t', 'tmpl.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
  leads = json.load(open('sms_send2.json'))
  print(max(len(m.sms(l)) for l in leads))     # firm name varies per lead → max, not average
  ```
  Over budget: trim filler, keep the CTA — `"Reply BID or see <url>"` → `"Reply BID: <url>"` (−6 chars)
  restored 158 chars / 1 SMS for every lead.
- **Then prove the wave still fires**: its markers (`.email_wave2_done`, `.sms_wave2_done`) must be
  ABSENT (a present marker silently skips the wave) and the timers still scheduled:
  `systemctl --user list-timers 'az-*' --all`.
- Re-runnable check: `scripts/audit_campaign_links.py <campaign-dir> --old <old-domain> --new <new-domain>`
  scans text + zip artifacts, prints remaining dead refs, and exits 1 if any survive.
- Deleting the site itself (Pages project + local files) and the pre-delete dependent recon:
  skill `cloudflare-pages-ops` → "Decommissioning a project".

### 1e. After the link swap: the copy's CLAIMS must still be true

Repointing the URL is only half the fix. The replacement target is rarely the same *kind* of page
as the old one (a funnel page gets replaced by a brochure page), so sentences the copy has always
carried can become false the moment the link changes.

- **Grep the claims against the live target**: `curl -sL <new-url> | grep -ci -e 'tender map'
  -e 'buyer group' -e '14-point'` → 0 hits = the copy promises content that page does not host.
  Do this for every concrete noun the copy promises (map, groups, checklist, pricing, report).
- **Reframe so each promise rides the artifact you actually deliver**, and demote the site link to
  background: "*reply \"BID\" and I will send our Pan-India tender funnel file — 143 live channels
  …, the working tender map, the buyer groups … and the 14-point compliance pass … Background on the
  practice: <site>*". Honest, and it converts better: the promise now depends on a reply.
- **Same rule for generated attachments**: never keep a row like `Gated funnel document → <url>` when
  that URL opens the plain brochure (it 200s, so a status check will not catch the lie). Relabel to
  the real delivery channel: `Funnel file (on reply "BID") | emailed as attachment`.
- **Verify the fulfilment asset still exists** — anything the copy promises to send on reply is a
  money-path file. If it lived under the deleted tree it is gone from disk; restore it from the tar
  into the campaign dir, prove it is self-contained (0 refs to the dead domain) and that its own
  claims are inside it, then offer a PDF version for replying.
- **Numbers on a preview/handover must be computed in the same run, never typed.** Channel counts,
  link counts, max SMS length, upload counts — derive each one from the source data inside the
  verification script (`grep -c 'https\?://' <file>`, `max(len(sms(l)) for l in leads)`, zip-grep on
  the xlsx) and print it beside the artifact. A figure that came from memory earlier gets re-derived
  before the preview goes out.
- **Long copy lines break naive patching.** A very long single-line string (a full email paragraph)
  can arrive truncated in a shell/heredoc edit → partial match, exit 1. Patch a SHORT anchor inside
  the line, or bridge the tail with a regex in python
  (`re.sub(r'practice\..*?(https://<domain>[^\s]*)"', new, src)`), then prove it: count old/new
  occurrences (`old 0 | new 1`), re-render (`len(body())`, tail `repr`) — exit 0 alone proves nothing.

Worked case with exact commands (claim grep, xlsx row relabel, tar restore of the funnel file,
preview build): `references/copy-claim-integrity-checks.md`.

## 1f. India / same-trade advisory waves (2026-09-12, AZ Consultants India desk)

Wave built from `~/hmw_bid/HMW_Bid_Advisory_Leads_and_Tiers.xlsx` (37-firm PAN-India roster)
via `~/clients/invertio/prospects/outreach/{templates_india.py,india_wave.py}` + `india-lead-queue.csv`
(20 email) / `india-sms-list.csv` (11 mobile). Hook = the INCOIS case the leads came from.

- **Per-bid GeM permalinks are not verifiable from this VM** — `bidplus.gem.gov.in` refuses
  datacenter IPs (curl exit 7), but `web_extract` fetches it fine (title "GeM | All Bids on GeM").
  Never ship an unverified `/showbidDocument/<id>` link in cold copy; use the bid number in text plus
  `https://bidplus.gem.gov.in/all-bids` (bid search) and the owned tender board for the glance view.
- **Copy-integrity red line for same-trade leads**: the roster firms are the client's own competitors
  (Agni, Hydro Pnumatic, Universal Fire…). Share headline exposure/profit only
  (Rs 23.02L funds / Rs 16.02L net cash at risk / +Rs 20.8L 36-mo lean / yrs 4-5 Rs 4.7-18L).
  NEVER the floor price (Rs 92L) or rate build-up — that is the client's bid.
- **`%` inside copy breaks `%`-style templating**: "about 130% on the cash" → `ValueError: %o format`.
  Build copy with `.replace("{token}", value)` tokens, or escape `%%`.
- **`himalaya message send --save sent -a gmail` writes TWO copies into Gmail Sent** (Gmail SMTP
  auto-saves its own). The recipient still gets ONE; verify by count of `SENT` lines in the wave log,
  and don't report it as a double-send.
- User-ordered same-firm double-touch (email + SMS in the same hour) overrides the §1b "SMS lands
  after the email" rule — do it when asked, but say so in the report and expect it to read as bulk.
- testbee/textbee: the gateway SIM is a **Saudi** number sending to `+91` recipients; device accepts
  all, operator-side filtering is the residual risk. Always `test-sms --to <owner's Indian SIM>` first,
  and hold SMS at ≤160 GSM-7 (worst-case per lead, see §1d).

## 1g. Post-wave deliverability verification (never stop at "N/N SENT")

A wave log's `SENT` line means the SMTP server / SMS gateway **accepted** the message. That is not
delivery, and it is not what the user asked for ("make sure it doesn't land in spam"). 30-60 min
after the last send run three cheap read-only checks, then report only what was observed — never
"deliverability is fine", and never a claim you did not verify:

1. **Bounces** — `himalaya envelope list -a gmail -m INBOX -s 25`; look for `postmaster@`,
   `Undeliverable: <your subject>`, `Mail Delivery Subsystem`. Each hit = hard bounce → status
   BOUNCE, drop the address. If the bounce lands in a whole predicted-low-fit segment (IT firms on
   an HVAC roster, competitor-aggregator domains) cut that segment from wave N+1 instead of re-sending.
2. **Auto-reply = delivery proof** — an autoresponder from the target's OWN domain ("Thank You for
   Contacting", ticket ack) proves the mail cleared their inbound filters and reached the mailbox.
   Positive deliverability evidence, still NOT engagement (§2 triage).
3. **Spam folder** — `himalaya envelope list -a gmail -m "[Gmail]/Spam" -s 15`. Wave NDRs land there
   too; if your own inbound is being filtered, genuine prospect replies are at risk. Match dates —
   only bounces inside this wave's send window count.
4. **Links** — curl every URL the copy carried in the same pass
   (`curl -s -o /dev/null -w '%{http_code}' <url>`); a 404 or dead link in an already-sent wave is
   worse than a bounce, and the fix is a follow-up touch, not a resend.

- 1 bounce in 20 (5%) is a healthy cold-list rate. Name the firm in the report, don't bury it.
- Then OFFER (do not auto-arm) a **48h watch cron** (inbox + spam, silent unless something changes)
  plus the 7-day follow-up wave — the user decides which to arm.
- Exact commands, interpretation table and the India-wave sample evidence:
  `references/wave-deliverability-verification.md`.

## 1h. High-pitch variant ("luring + CTA") — real urgency only

When Aamir asks for a "high pitch email with luring and cta" (2026-09-12, India desk), raise the
persuasion, not the hype. Same verified numbers, same sender hygiene, tighter argument:

- **Money-first subject**, naming the firm: `Subject A) <Firm>, the Rs 16.02 lakh nobody budgets for`
  / `Subject B) Rs 16.02 lakh is decided before your bid goes in`.
- **Body order that converts**: the headline number → what it really costs to arrange → the return over
  the term → "Most tender losses are decided before the bid goes in, not after." → what we run
  (go/no-go, rate build-up, EMD, PBG, DSC, submission pack, AMC lifecycle) → sealed-room proof (one
  client per tender, NDA signed, costing never leaves the room, not even to the OEM) → tender-board link
  → CTA.
- **CTA = a 15-minute answer, not a meeting**: "Reply with the tender link and I will tell you in 15
  minutes whether it is winnable." Low-friction yes beats a calendar ask on a first touch.
- **Urgency must be a true policy statement**, never invented scarcity. The two honest levers:
  "one client per tender" and "if the deadline is inside 10 days, say so and we move you to the front".
  NO "2 seats left", no ALL-CAPS, no "act now / limited offer" — spam-filter words, and same-trade
  bidders check claims.
- Everything else from §2b/§2c still applies: plain text, no attachment/image/short-link, genuine
  From name, ≤200 words, `Reply STOP to opt out.` last line, one touch per firm. §1f floor-price red
  line holds: headline exposure + profit only, never the rate build-up.
- Working file: `~/clients/invertio/prospects/outreach/india_email_highpitch.txt` (subject A/B + body).

## 2. Triage: is this reply real or a gate?

Autoresponder / gated-inbox signatures — ALL mean "no human signal, no interest":

- Sender address contains `+noreply` / `noreply@` / `no-reply@` / `mailer-daemon` / `bounces@`
- Generic template wording: "Dear Sender", bilingual boilerplate (e.g. EN+AR), "please contact us at <support@...>"
- Arrives within minutes of the send, references none of your actual content
- "Contact us through X@..." = inbound-gate routing, NOT interest

Judgment playbook (the expert call):

- NEVER re-send the pitch to a support@ / help-desk address (Zendesk / help-center ticket queues). Cold sales pitches there = spam-complaint risk on the sending account + wrong funnel (support agents can't/won't sell). Expected value ≈ 0, risk > 0.
- NEVER reply to a `+noreply` address — it routes back into the same autoresponder or bounces.
- Hard bounce (550/5xx, "mailbox unavailable") → remove/fix the address, log status=BOUNCE.
- Genuine human reply → reply within thread, gauge interest, update tracker.

Route recovery for gated HIGH-fit leads (how to actually reach them):

- LinkedIn outreach to the named role (e.g. Head of Data / CTO) — cleanest route when no verified personal email exists.
- The company's official sales funnel: "Talk to sales" / request-a-demo / partner pages on their website.
- Do NOT guess personal emails from patterns (`firstname@company.com`) — deliverability/spam risk, low reply odds.

## 2b. Buyer-type outreach: verifying "genuine emails, never assumed"

Aamir's HARD rule for cold outreach to buyer-type targets (university faculty, company execs, founders): email ONLY addresses that are publicly published by the person or their institution. Pattern-guessing and paywalled aggregators are forbidden. Full ladder with working source types + curl/grep recipes: `references/genuine-email-verification.md`.

Verification-source hierarchy that WORKS (highest trust first):

1. Official university faculty/directory page — `curl -sL <page> | grep -oiE "[a-z0-9._%+-]+@<domain>" | sort -u` (Ajman directory pages carry staff emails in HTML; MBRU faculty pages too). KSA/Gulf discovery operator that works: `site:*.edu.sa anatomy "department of anatomy" email 2025` (and `site:*.ac.ae`, `site:*.edu.ae`) surfaces official directory pages; Taif (tu.edu.sa), Qassim (qu.edu.sa), Princess Nourah (pnu.edu.sa), Gulf Medical Univ (gmu.ac.ae) all publish head-of-department / dean-office emails in plain HTML on those pages.
   - Volume control: ONE email per organization per wave, even when several verified addresses surface (e.g. a verified dept coordinator alongside the head) — multiple institutional sends from one Gmail identity read as spammy and flag the whole wave.
2. The person's OWN published materials — their lecture slides/PDFs on the university domain (KAU histology slides carried `salsaggaf@kau.edu.sa`).
3. Journal corresponding-author / article emails (Wiley etc. list `ymezil@alfaisal.edu` on the paper).
4. Company official contact page / official licensing email (Kenhub's terms publish `contact@kenhub.com` for license inquiries; Neuronso's site publishes `info@neuronso.com`).
5. NOT verified: masked aggregator results (ZoomInfo shows `****@kau.edu.sa` — masked = unverified), RocketReach/Prospeo paywall previews, pattern guesses (`first.initial@uni.edu`).

When a target has NO genuinely published email → LinkedIn-only; hand the user a ready ≤300-char connection note instead of emailing an assumed address.

### Tone: punchy + dignified (Aamir's copy standard, 2026-09-07)

User correction on outreach copy: "Make it punchier and dignified respectable" + "if sent, don't send a second [time]". Embedded rules:

- Ultra-concise: value-led subject line, 2-3 sentence body carrying the link, ONE tailored line naming the recipient's institution/work, `Respectfully,` close with founder name + product. No emojis, no hype, no "I hope this finds you well" padding.
- **Never re-send the same pitch twice** once it has gone out ("dont second"). If copy feedback arrives after the send, save the revised template for the NEXT round / LinkedIn notes — do not resend to the same recipients.
- **Mandatory scheduling link** (user: "add the cal.com schedule in the link for very easy scheduling"): every email carries the account's booking link, e.g. `https://cal.com/<user>/15min`. Curl-check it first (`curl -sL -o /dev/null -w "%{http_code}" <url>` → 200). Sends that carried it performed better and read more genuine than bare pitches.
- **Structural spam-proofing per email**: verified sender identity in From, ONE email per organization, natural tailored subject that names the institution (never `[TEST]`, no CAPS/spam words), plain-text body only, minimal links (product URL + cal.com link only).
- Draft ALL wave copy in this style first; if the user has approved a send already, sending the approved copy beats waiting for a rewrite — but log the tone feedback into the template file for future rounds.

## 2c. himalaya v2 raw-send (overrides config display-name)

Installed himalaya is **v2.1** — `template send` does NOT exist (v1-era; errors `unrecognized subcommand 'template'`). The working send is a raw RFC822-style `.eml` file piped to `message send`:

```bash
himalaya message send --save sent -- /tmp/outreach.eml
```

- `.eml` must carry its own headers: `From: Human Name <account@gmail.com>` (display-name from the From header wins over the account's config `display-name` — needed when the account's configured name is client-branded, e.g. azengineeringapp displays "Triatek Venturi"), `To:`, `Subject:`, blank line, body.
- Self-test FIRST to the owner's testing account (aamir1zahran@gmail.com — testing only, never business targets) to confirm delivery + rendered display name, then send the real wave.
- Verify each real send by reading back the sent folder: `himalaya envelope list -m sent` (mailbox alias required; config at `~/.config/himalaya/config.toml`).
- Scripted sends can pipe the raw RFC5322 message on **stdin** instead of writing a temp
  `.eml`: `python3 -c '<build(recipient)>' | himalaya message send --save sent -a gmail`
  (same display-name override; `-a <account>` is required when the config holds several
  accounts, e.g. `gmail` + `aamir1zahran`).
- Confirm the override landed, don't assume: read the message back in the *receiving*
  account (`himalaya envelope list -a aamir1zahran -s 3`) and check the FROM column shows
  the genuine personal name rather than the account's configured brand.
- **Reply-To carries the branded address.** When sending from a shared Gmail identity but the reply
  should land on the product/offer domain, put an explicit `Reply-To: offers@<domain>` in the raw
  message (From stays a genuine human name). **Gate the whole wave on that mailbox really receiving**:
  enable forwarding (MX + SPF), verify the destination, then send a test from a second account and
  read it back. A cold email whose Reply-To bounces reads as a scam and burns the name you are selling.

## 2d. Permanent campaign log (Notion via ntn CLI)

Waves get logged to a permanent Notion page so status survives sessions (local /tmp logs are not enough). Proven recipe for the Open Anatomy campaign (see `references/notion-campaign-log.md` for exact commands, page IDs, and API quirks):

- Keep a local markdown master (`/tmp/<campaign>-log.md`) as source of truth — Round 1 + Round 2 tables, monetization routes, tone rules, next steps — then mirror it to a child page under the **AZ Master Leads** parent page (`3d06012e-e39a-81f8-96df-d1bf25faf8b5`).
- Env prefix before any `ntn` call: `export NOTION_API_TOKEN=$(cat ~/.config/notion/token); export NOTION_KEYRING=0` (never print the token).
- Create the child page from markdown, then verify read-back. When the log advances mid-campaign, PATCH the page's markdown — **but the documented API shapes fail**: raw `{"markdown": ...}` curl → 400 `body.type should be defined`; `ntn api … -X PATCH markdown="$(cat file)"` → multi-line parse failure. The WORKING full-replace body is `{"type":"replace_content","replace_content":{"new_str":"<entire markdown>"}}`, sent as a JSON file: build with `python3 -c` + `json.dumps`, then `-d @/tmp/body.json`.
- Verify the PATCH by reading the page markdown back and grepping for markers ("ROUND 2 — SENT") — never compare char counts (Notion's markdown renderer inflates them ~30% via link normalization).

## 3. Tracker hygiene

- Update the prospect CSV IMMEDIATELY when a response arrives: status + dated notes.
- Define one status vocabulary as the campaign grows (NEW → CONTACTED / AUTO-REPLY / BOUNCE / REPLIED / MEETING) the first time you deviate from NEW; reuse it consistently.
- Notes carry the evidence: date, sender address, what the auto-reply said, recommended route. Append, never delete prior notes.
- After editing a CSV with quotes/commas in notes, verify it still parses (python csv or similar) — broken quoting corrupts future waves.

## 4. Inspecting the campaign mailbox (himalaya v2)

See `references/himalaya-v2-cli.md` for exact working commands. Key facts:

- v2 requires mailbox aliases: `[mailbox.alias]` in `~/.config/himalaya/config.toml` (inbox/sent/drafts/trash/archive → `INBOX`, `[Gmail]/Sent Mail`, ...). Without it every list/search errors "Mailbox is required".
- Search DSL is SPACE-separated: `from foodics` works, `from:foodics.com` parse-errors.
- `himalaya message read <id>` shows full headers + body — ALWAYS check the FROM address and exact wording before judging a reply.
- Don't rely on `--output json` piped to python in this version — the table + message read is the reliable path.

## 5. Pausing / disabling campaign automation (account-wide)

When the user says "gmail/campaign automation band karo" (temporary disable, avoid token usage / account use / leaks):

- **"Tokens" ≠ only LLM-agent jobs.** no_agent script jobs consume 0 LLM tokens but still SEND or READ via the account — the user's underlying concern is the account being used at all. Pause script jobs too; do not leave them running just because they're free.
- Audit steps:
  1. `cronjob action=list` — enumerate every job (agent + script).
  2. Grep the actual scripts, not just job names/prompt previews (script jobs often have empty prompts): `grep -lE 'azengineeringapp|GMAIL_USER|FROM_ADDR|himalaya|@gmail' ~/.hermes/scripts/*.py` and the client dirs.
  3. **Follow wrapper chains**: thin cron wrappers `subprocess.run()` the real sender script in a client dir (e.g. `avvs_venturi_followup1.py` → `~/clients/AVVS-Triatek/outreach/send_venturi_followup.py`). Grepping only the wrapper misses the actual sender — read the wrapper, then grep its target.
  4. Pause, never remove — fully reversible in seconds; the user resumes on request.
  5. Report the full paused list, and separately flag any OTHER token-consuming agent jobs NOT tied to the account so the user decides on those independently.
- Account → automation map and audit commands: `references/campaign-accounts-and-cron.md`.

## Pitfalls

- **A dry run that prints `SENT` is not proof it sent — check the code path, then the Sent folder.** The KSA sender printed `SENT <company> -> <addr>` on a `--dry-run` scan because the label only tested the return code, which is `0` for the dry branch. Confirm with two things before alarming the user (or relaxing): (1) `if dry: return 0, "dry-run"` sits BEFORE the transport call in `send_email`/`send_sms`, and (2) `himalaya envelope list -m sent -a gmail` — a real send always lands there. Then fix the label to `DRY` so the next person is not misled.
- **A price-policy change must sweep every layer, and stale artifacts lie.** Live renderers are the templates (`templates_p1/p2/p3.py`, `templates_ar.py` `OFFER` + assembly), but the same numbers also hide in `build_report.py` (the attachment a warm reply receives) and in the previously generated pack md. After editing, re-render AND re-run the pack builder: the first pass left `az-advisory-emails-*.md` with 48 dead prices while the send path was already clean.
- Arabic SMS is UCS-2: 70 chars per segment, not 160 (the KSA SMS is 67 chars = 1 segment). Adding a lure sentence in Arabic to an SMS buys a second segment — keep Arabic SMS copy short and put the pitch in the email/LinkedIn instead.
- Sending the wave at the sender's clock instead of the recipient's: 10:00 IST is 04:30 UTC
  on this VM — schedule in UTC for recipient business hours, never "as soon as it is ready"
  (a 2-3 AM delivery reads as bulk automation).
- Running the jitter loop inline in the agent session — it is 30-60 min of runtime and the
  session can end mid-wave. Use the timer + idempotent wrapper pattern (§1b).
- Building the wave from the raw scrape without contact QA: multiple addresses at one firm,
  aggregator/broker domains, placeholder `firstname.lastname@` addresses, and addresses that
  do not match the firm all inflate the wave and burn sender reputation. ONE per firm (§2b).
- Piping himalaya through `| python3 -c` / `| head` masks the real exit code (pipeline reports tail's status). Run the command bare; treat a failed pipeline as failed.
- Confusing an autoresponder with a human reply = wasted sends + spam risk. Check FROM before drafting anything.
- **Never fake the greeting.** Deriving a name from the company field (`company.split()[0]`) produced
  "Hi Priamed," / "Hi Infinitus," — worse than no personalization. Use a neutral "Hi there," or
  "Hello <Company> team," and put the real personalization in ONE tailored line about their work.
  Non-ASCII/企业 names and bracket suffixes (`Priamed (trydock.ai)`) make token-slicing greetings
  obviously machine-made.
- A reply is not a lead. Track it, route it, but don't count a gate-reply as engagement.
- Don't create new status values per reply — the tracker becomes unreadable. One vocabulary, evidence in notes.
- Judging a cron job by its name/prompt preview alone during a disable audit — script jobs have empty prompts; only grepping the real script (and its subprocess target) reveals which account it touches.

## Verification

- [ ] Sent record exists in Sent Mail matching the CSV recipient list (wave sends)
- [ ] Every response logged: status updated, dated note appended
- [ ] No pitch sent to help-desk / support / noreply addresses
- [ ] CSV still parses after edits
