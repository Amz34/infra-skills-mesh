# Media Update via Email → Staging → Review-File → Deploy (review-gated)

Proven 2026-08 on A.S Love 7.0 anniversary site (user: "Strictly no other
changes … give the review file prior deploy"). Applies to ANY existing static
site when the user emails new media (audio/images/videos) and wants a gated
deploy. User's hard rule: **never touch production until approval**.

## Trigger
- "In my email inbox there are some files … add/replace … strictly no other changes"
- User sends WhatsApp-recorded audio (PTT opus), phone photos, phone videos via Gmail

## Steps

1. **Fetch attachments from Gmail** (creds in `~/.hermes/.env`, GMAIL_USER +
   GMAIL_APP_PASSWORD). Find the email by subject keyword, list attachments,
   download all to `/tmp/<task>_files/` (e.g. aslove_files). See
   gmail-imap-access / email-imap-extraction skills.

2. **Inspect + prep media** (before touching any HTML):
   - `ffprobe` duration/format of each file
   - **opus (WhatsApp PTT) → mp3** for browser compatibility (opus not
     universal in `<audio>`): `ffmpeg -y -loglevel error -i f.opus -c:a libmp3lame -b:a 128k f.mp3`
   - Images: PIL resize/optimize (~900px wide, quality ~82 → ~100KB each) into
     the site's existing naming scheme
   - Video: keep mp4, copy under site's video dir; `ffprobe` for report

3. **Staging copy — NEVER edit production directly:**
   `cp -r /home/ubuntu/<site> /tmp/<site>_staging && cd /tmp/<site>_staging`
   Apply ALL edits only in staging. Production stays untouched until approval.

4. **Apply the exact requested changes** (nothing else):
   - Song/audio section: keep 1st song, ADD 2nd (`<button id=…-2>` + second
     `<audio>` + JS player block mirroring the first; punchier button label
     per user taste). Section title "Our Song" → "Our Songs".
   - Memories: numbered-asset gallery — bump `var total = N`, and **extension
     logic when mixing formats**: existing assets `.png`, new ones `.jpg` →
     `var ext = (i <= <oldTotal>) ? "png" : "jpg";` then use `"." + ext` in
     src/href. (Hardcoded `.png` in the loop will 404 new jpgs silently.)
   - Videos: add second `.video-frame` block in the SAME section, matching
     style/caption pattern.

5. **Serve staging locally + verify:**
   - `python3 -m http.server <port>` in background (8931 works), then
     `curl -s -o /dev/null -w "%{http_code} %{size_download}B"` each new asset
   - Browser (browser_exec): per page assert DOM — button text present,
     gallery item count (`querySelectorAll('a').length`; expected =
     total − skips), video count + source srcs
   - Screenshots: `capture_screenshot()` **overwrites the same file** every
     call — `shutil.copy(p, "/tmp/<task>_review/<name>.png")` immediately
     after each capture, or you lose prior shots.

6. **Diff proof — only intended files changed:**
   `diff -rq --exclude=<server-file> <prod> /tmp/<site>_staging`
   Expect: only the edited html/js + new assets. Report this to the user as
   the "no other changes" proof.

7. **Review file** (`/tmp/<task>_review/REVIEW.md`): before/after table per
   change, new-files list, verified checklist (browser-rendered), privacy
   note ("sab staging me hai, production pe zero change"), and an explicit
   approval gate ("Approve karo to deploy"). Attach the screenshots as
   MEDIA: lines.

8. **STOP.** Send review file + screenshots. Deploy ONLY after explicit
   approval ("deploy karo"/"approve"). Never auto-deploy — including to a
   live quick-tunnel preview — before that.

## Pitfalls
- Don't convert the new mp3 into the old filename unless the user said
  "replace" — "2nd song add karo, 1st wala rehne do" = NEW file, both players.
- WhatsApp voice-note opus in an email is often THE intended song — confirm
  with the user ("confirm wahi hai") before converting; don't assume it's
  scrap.
- `python3 -m http.server` in a foreground terminal call gets blocked as a
  long-lived process — start with background=true, then curl in a separate
  call.
- Keep captions/style identical to existing blocks for new videos/images —
  "no other changes" includes visual consistency.
