# Genuine-email verification ladder (buyer-type cold outreach)

Rule from Aamir (2026-09-07, Open Anatomy outreach): "genuine email not assumed" —
only send to addresses the person/institution publicly published. No pattern
guessing, no paywalled-aggregator outputs. Worked example below is the Open
Anatomy (open-anatomy.pages.dev) university/company outreach wave.

## Verification sources, highest trust first

1. **Official university faculty/directory page HTML.** Directory pages often
   carry a `mailto:` or a raw address even when the rendered page hides it.
   Grep the raw HTML:
   ```bash
   curl -sL "https://www.ajman.ac.ae/en/directory/staff/<slug>" \
     | grep -oiE "[a-z0-9._%+-]+@<domain>\.ac\.ae" | sort -u
   ```
   - Ajman University directory → `a.spaska@ajman.ac.ae`, `z.hein@ajman.ac.ae`
     (both confirmed this way).
   - MBRU (Dubai) faculty page → `nerissa.naidoo@dubaihealth.ae` (their domain is
     dubaihealth.ae, NOT mbru.ac.ae — check the page, don't assume the domain).

2. **The person's own published materials** (lecture slides/PDFs on the
   university domain or slideshare). KAU prof's own histology slides carried
   `salsaggaf@kau.edu.sa` — a first-party source, high trust.

3. **Journal corresponding-author / article emails.** PubMed/journal article
   pages list author emails. `ymezil@alfaisal.edu` (Alfaisal, Riyadh) came from
   a Wiley article's author contact block.

4. **Company official channels** — the address the company itself publishes for
   the relevant purpose:
   - Kenhub GmbH: `contact@kenhub.com` is their published licensing/inquiries
     address (their license terms page) — right channel for a licensing pitch.
   - Neuronso (Naim Messai, Dubai): `info@neuronso.com` on their official site.

## NOT verification

- Masked aggregator output — ZoomInfo returns `****@kau.edu.sa`: masked means
  UNVERIFIED, treat as no email.
- RocketReach / Prospeo / Hunter paywall previews — not first-party, skip.
- Pattern guesses (`first.initial@university.edu`, `name@company.com`) — hard
  no. If no published email exists, the target is LinkedIn-only.

## Send mechanics (himalaya v2.1 — `template send` does not exist)

Raw RFC822-style file piped to `message send`:

```bash
himalaya message send --save sent -- /tmp/outreach_<slug>.eml
```

.eml shape — From display-name in the file WINS over the account's configured
display-name (config for azengineeringapp says "Triatek Venturi"; file says
"Aamir Zameer", recipient sees "Aamir Zameer"):

```
From: Aamir Zameer <azengineeringapp@gmail.com>
To: <verified-address>
Subject: Free bilingual (EN/AR) 3D anatomy atlas — for <institution>?

Dear Dr. <Surname>,

We built Open Anatomy — a free, interactive 3D human-anatomy atlas that runs in
the browser, fully bilingual English/Arabic:
https://open-anatomy.pages.dev

<ONE tailored line: their institution / teaching focus / licensing angle>

Best regards,
Aamir Zameer
Founder, Open Anatomy
```

Workflow that ran cleanly on 2026-09-07 (8/8 sends verified in Sent folder):

1. Verify every recipient address via ladder above (never assume).
2. Compose one .eml per recipient (unique tailored line).
3. Self-test FIRST to aamir1zahran@gmail.com (testing account — never a real
   target) → confirm delivery AND rendered From display-name.
4. Send real wave: `for f in ...; do himalaya message send --save sent -- /tmp/$f.eml; done`
5. Read back to verify: `himalaya envelope list -m sent` (mailbox alias
   required; config `~/.config/himalaya/config.toml`).

## Tone standard (user correction 2026-09-07)

"Make it punchier and dignified respectable; if sent, don't send a second."
→ Ultra-concise body, respectful address ("Dear Dr."), no emojis/hype, one
tailored line per recipient, `Respectfully`/`Best regards` close. After a wave
is sent, do NOT resend revised copy to the same recipients — save the revision
for LinkedIn notes / the next round.

## Post-wave state

Wave 1 (7 targets + Kenhub) sent 2026-09-07. Remaining LinkedIn-only (no
published email found): Andrew Bowditch (ex-Visible Body CEO), Dimitrios
Mytilinaios (Kenhub content head), Niels Hapke (Kenhub). Revised punchier
template saved at `~/projects/anatomy-explorer-demo/outreach-copy-v2.md`.
