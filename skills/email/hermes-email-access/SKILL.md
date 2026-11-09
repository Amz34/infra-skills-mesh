---
name: hermes-email-access
description: Use when reading Aamir's Gmail via himalaya CLI on this VM.
---

# Email access on this VM (himalaya CLI v2.1.0)

## Trigger
Aamir ke Gmail accounts se email dhoondhna/padhna/bhejna — subject search, attachment analysis, supplier extraction. Machine+user-specific facts jo bundled `himalaya` skill me nahi hain.

## Accounts
- `azengineeringapp` = azengineeringapp@gmail.com — BUSINESS (AVVS, client forms)
- `aamir1zahran` = aamir1zahran@gmail.com — **SIRF TESTING** (business me kabhi nahi)
- Config: `/home/ubuntu/.config/himalaya/config.toml`
- Passwords: per-account helper scripts `~/.local/bin/himalaya-<acct>-gmail-pass.sh` jo `~/.hermes/.env` se app-password read karti hain

## Golden invocation (cross-profile sessions — zaroori!)
Profile sessions (e.g. invertio group chat) ka $HOME profile home hota hai → himalaya config miss karta hai AUR password script (`~`-based) galat jagah read karti hai → auth fail. Fix:
```
env HOME=/home/ubuntu himalaya -c /home/ubuntu/.config/himalaya/config.toml -a <acct> <cmd>
```
- Auth success = config+script theek. Uske baad bhi errors aayen to = query/CLI syntax masla, credentials nahi.

## v2.1.0 CLI notes (generic himalaya help ke liye bundled `himalaya` skill dekho)
- **Search:** `envelope search "subject <val>"` — space-separated DSL, NO colons. `himalaya search` v2 me exist nahi karta. `envelope list` = folder listing only (no positional filters, no `--output json`).
- **Flag placement:** `-a/--account` top-level hai (`himalaya -a <acct> ...`), lekin `-m/--mailbox` subcommand ke BAAD (`... envelope search --mailbox 'X' "query"`). Subcommand se pehle `-m` lagao to error: "unexpected argument '-m' found".
- **Search scope = Inbox SIRF:** Gmail pe default sirf Inbox search hota hai. Inbox me zero hits = "email nahi hai" nahi — `--mailbox '[Gmail]/All Mail'` (poora account) aur `'[Gmail]/Sent Mail'` (bheje hue) pe dobara karo.
- **Read:** `message read <id>` — full MIME text (body + attachment filenames/sizes); ~32MiB emails bhi chalti hain.
- **Send:** `from X` bina colon; `-m/--mailbox` + `--save sent`; `--output json` nahi.

## Pitfalls
- **Vendor/product thread = reconstruct the LIFECYCLE, not just the one mail he named.** Read the whole thread oldest→newest before analysing:
  `envelope list --page-size 200 -m INBOX > /tmp/all.txt` then `grep -iE "<vendor>|<apex-domain>" /tmp/all.txt` (grep BOTH the brand name and its domain — transactional mail comes from `noreply@<domain>`, not the brand). Report it as a `UID | date | from | subject` timeline; the ACTIONABLE mails are the account-ready / sign-in one and the coverage is the newsletter at the end. Threshold mails expire: TypeSafe's sign-in code died in ~10 min (2026-09-21 case), so trigger → read → use without delay, and never `curl` the OTP link yourself — hand the login step to bhai.
- **Onboarding mail says what the vendor will NOT put on the pricing page.** "Account ready", "waitlist accepted", free-credit counts and expiry windows exist only in the inbox — read them before writing "pricing is not publicly comparable".
- **Bounce/DSN diagnosis (deliverability debug):** delivery failure ka `Delivery Status Notification` **sender** ke mailbox me aata hai (`Mail Delivery Subsystem` se) — destination me nahi. Bhai ko bheji test mail \"gayab\" lage to pehla step: sending account ka INBOX read karo (`-a <acct> message read <id> -m INBOX`), asli SMTP code wahin hai (`550 5.1.1`, `5.7.x`). Bade/inline output elide ho jate hain — `... > /tmp/dsn.txt` phir `read_file` + grep `550|5\\.1\\.1|diagnostic`.
- Online v1 examples (colon syntax `subject:x`) v2.1.0 me "invalid query" dete hain — auth pehle pass ho jata hai, is liye credentials ko blame mat karo.
- **User ka shorthand/typo ho sakta hai:** exact term pe zero hits = spelling galat hai (e.g. "fabke vs astr" → asli subject "fable vs astra"). Pehla step: OR se broaden karo across fields + sender nicknames (`subject fable or subject astra or from vaibhav`). Phir bhi zero → recent `envelope list` (page-size 15-25) eyeball karo — subject wahan dikh jata hai.
- **Ek edition do ESP se = EK email.** Newsletter/roundup ka same body do baar aata hai (Mailmodo `news.<domain>` + Beehiiv `mail.beehiiv.com`, IDs 8352/8354, byte-identical). Permalink (`newsletter.<domain>/p/<slug>`) + body pe dedupe karo aur report me "1 edition, 2 copies" likho — do emails mat ginno. Slug = asli headline; subject line sirf hook hai.
- **Lamba body (>14 KB) inline read me stub aata hai** — `message read <id> -m INBOX > /tmp/<tag>_<id>.txt`, phir python heredoc se char-offset slices print karo (pehle TOTAL_CHARS/LINES, phir first ~20 lines; body aksar line ~55 / char ~300 se shuru). Money/numbers ke liye regex sweep with context (`\$[0-9][0-9.,]*[^.]{0,60}`).
- **Newsletter ke price/number claims aksar embedded IMAGE me hote hain** (`media.beehiiv.com/.../*.png`) — CDN image curl karke `vision_analyze` se verbatim transcribe karao; sirf text body padhne se email ka sabse important number miss ho jata hai.
- Email body me embedded supplier/contact numbers AI-summarized ho sakte hain (Gemini share-link wali analysis bodies) → client ko dene se pehle web-verify karo (dekho `supplier-contact-verification` skill).
- Images attachments ko dekhne ke liye alag download chahiye; kaafi baar text/plain body me hi poora extraction hota hai.
