# Google v3 sign-in, passwordless push route (fresh CDP profile, no saved session)

Proven 2026-09-09 on Oracle Cloud VM (Xvfb :99, Chrome 152 via raw CDP port 9223,
fresh profile dir `~/.config/chrome-forms`), signing `aamir1zahran@gmail.com` back in
after a cookie wipe. Goal: reach a state where the USER's one phone tap completes
sign-in — the agent never types or sees the Google password.

## Context / prerequisites
- Chrome 136+ refuses `--remote-debugging-port` on the DEFAULT user-data-dir
  (`~/.config/google-chrome`): use a fresh non-default dir → but a fresh dir has NO
  session, so a full Google sign-in is required. (If the login already lives in the
  default profile, use the Local State `devtools.remote_debugging.user-enabled: true`
  toggle route instead — see SKILL.md.)
- Launch: `google-chrome --remote-debugging-port=9223 --user-data-dir=<fresh-dir>` on
  `DISPLAY=:99` (GUI mode; needed for real X11 fallback clicks).
- **Before relaunching Chrome on any login-bearing profile: snapshot the cookie DB
  first** — see cookie-WAL trap below. The wipe that forced this whole sign-in
  happened on relaunch.

## Flow (all real CDP input events; page verifies after each step)

1. Navigate tab to `accounts.google.com/signin` (CDP `Page.navigate` or `location.href`
   — `/json/new?url=` may land on newtab).
2. Identifier page `/v3/signin/identifier?flowName=GlifWebSignIn…`:
   - field `#identifierId` (type=text, standard). Focus + `Input.insertText` with the
     email, or native value setter + input event.
   - Next = `#identifierNext` — DOM `.click()` WORKED here (Google's own button),
     navigated to the password challenge.
3. Password page `/v3/signin/challenge/pwd?TL=…` ("Hi <First>", email shown,
   "Enter your password"). **We do not know the password and never ask for it.**
   - Click "Try another way" (link at bottom of the password card) with a REAL CDP
     click. Synthetic `.click()` AND synthetic `MouseEvent` dispatch on this link were
     silently ignored. Real recipe:
     ```python
     # rect center via Runtime.evaluate:
     # [...document.querySelectorAll('div[role=button],li,[role=listitem],a')]
     #   .find(x => x.textContent.trim().startsWith('Try another way'))
     # then Input.dispatchMouseEvent mousePressed + mouseReleased at (cx, cy)
     ```
   - ⚠️ Re-read the rect IMMEDIATELY before clicking. A stale rect click landed on the
     footer "English (United States)" language selector → page-language menu opened
     (body text: "Afrikaans, azərbaycan…"). Tell: body text becomes a language list.
   - This opens the recovery-options list (NOT a password reset): rows such as
     "Tap Yes on your phone or tablet" / "Get a verification code at ••• ••• ••56" /
     "Try another way to sign in". Rows are `LI` elements (seen: `LI.aZvCDf`);
     label text is split across child nodes → leaf-text search fails; use
     textContent prefix match on role/listitem elements.
4. Click "Tap Yes on your phone or tablet" (real click) → confirmation page
   "Do you have your phone? — Google will send a notification to your phone" with
   [Yes] [Try another way]. Click Yes (real click) → "Check your phone — Google sent
   a notification to your phone. Tap Yes on the notification to verify it's you."
5. Google now pushes to the user's phone (any device where the account is signed in
   with notifications). **Hand off here**: message the user to tap "Yes, it's me".
   Poll `location.href`/body text until it advances. If no notification arrives
   (account not on their phone), fall back to the SMS row matching a known SIM
   (masked endings map to known devices) or the email-code row read via IMAP.

## Element-finding + input rules on Google security pages
- Match container roles with textContent PREFIX (`startsWith`), never exact leaf text.
- DOM `.click()` works on some Google buttons (`#identifierNext`) but NOT on the
  security-sensitive links — go straight to real CDP input for anything that
  advances recovery; verify URL + body text after every click.
- Window coords on Xvfb: X window may sit at Position (10,10); for xdotool fallback
  add the window offset to viewport rect centers (`import -window <id>` screenshots
  are window-relative; `import -window root` is screen-relative).
- Direct URL navigation into `challenge/pwd` (even with the TL token) → HTTP 400.
  Always restart from `accounts.google.com/signin` and click through.

## Cookie DB traps that made this necessary (2026-09-09)
- Live Chrome `Cookies` DB read (sqlite3 on the file while Chrome runs) showed valid
  SID/HSID/`__Secure-1PSID`. After `cp`-copying the file to /tmp, the COPY showed the
  same rows but ALL values length 0 — the real values live in `Cookies-wal` (WAL
  mode) and `cp` misses it. Backup correctly:
  ```bash
  sqlite3 ~/.config/google-chrome/Default/Cookies ".backup '/tmp/cookies_snapshot.db'"
  # or: cp Cookies Cookies-wal Cookies-shm together; verify VALUES not row count
  ```
- Relaunching Chrome on the profile (same `--user-data-dir`, new port) silently wiped
  every Google session cookie (values → length 0). Order matters: snapshot + verify
  BEFORE any relaunch of a login-bearing profile; never relaunch-then-discover.
- Runtime check (CDP `Network.getCookies` / `Storage.getCookies`) vs DB check can
  disagree when the WRONG Chrome instance holds the port — always confirm which
  Chrome answers (`curl :<port>/json/version` UA + `/proc/<pid>/cmdline` profile dir)
  before trusting cookie state.
