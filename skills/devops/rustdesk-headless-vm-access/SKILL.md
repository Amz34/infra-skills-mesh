---
name: rustdesk-headless-vm-access
description: Use when giving a user RustDesk access to a headless VM.
version: 1.0.0
author: hermes
license: internal
metadata:
  hermes:
    tags: [rustdesk, remote-access, headless-vm, hbbs, tailscale, ocr]
    related_skills: [headless-browser-automation, hermes-cloud-vm-ops]
---

# RustDesk → Headless VM Access

## When to Use
- User needs to drive a GUI on a headless VM (Google sign-in, app setup) from their phone/PC.
- RustDesk connect fails: "ID doesn't exist", "Username missed", `/api/login` connection refused, or status not "Ready".
- You must hand the user a one-time RustDesk password without exposing real credentials.
- User ko VM ka **browser** chahiye (OAuth login, app sign-in) par RustDesk install nahi chahiye → noVNC quick tunnel: `references/novnc-quick-tunnel-desktop.md` (on-demand expose + teardown + post-login verification).

Recurring task: the user needs to drive a GUI app on a headless cloud VM (e.g. Google
sign-in in Chrome) from their phone/PC. The established channel is self-hosted
RustDesk (community `rustdesk-server` = hbbs + hbbr) running on the same VM's
Tailscale interface — the USER drives the GUI; the assistant never automates the
sensitive sign-in (CAPTCHA/lockout risk) and never sees the user's real passwords.

## Architecture (this deployment, 2026-09)
- hbbs (rendezvous, UDP/TCP 21116) + hbbr (relay, TCP 21117) run on the VM itself, bound to a Tailscale IP.
- Community server has **NO Pro web API on port 21114** — central to the login trap below.
- Target client: `/usr/bin/rustdesk --service` as **root**; configs `/root/.config/rustdesk/RustDesk.toml` and `RustDesk2.toml`.
- Server data/logs: `/var/lib/rustdesk-server/db_v2.sqlite3`, `/var/log/rustdesk-server/hbbs.log`.
- hbbs DB `peer` table columns: `guid, id, uuid, pk, created_at, user, status, note, info` — **no username column**; `SELECT id, status, info FROM peer;` lists registered clients.

## Repair: "ID doesn't exist" on the user's client
Root cause seen in the wild: the **VM's service** was still pointed at the public
server (`rs-ny.rustdesk.com`) while the user's phone app pointed at the private
server → the local hbbs DB has no row for the VM ID → clients report "ID doesn't exist".

Fix:
1. Back up first: `cp /root/.config/rustdesk/RustDesk.toml{,.bak}` (repeat for `RustDesk2.toml`).
2. In **BOTH** files set:
   - `rendezvous_server = '<tailscale-ip>:21116'`
   - `relay_server = '<tailscale-ip>:21117'`
   - `key = '<server-key>'` (value lives in the hbbs config; never write it into notes/chat logs)
3. Restart the client service, then relaunch the GUI on the Xvfb display.
4. Verify registration at the network level — logs/DB lag: `tcpdump -i any udp port 21116`
   shows periodic heartbeats from the VM client within ~30s (ground truth).
5. GUI status must OCR as **"Ready"** before telling the user to connect.

## Hand over a one-time password WITHOUT seeing real credentials
1. Kill the tray instance, launch GUI as root: `DISPLAY=:99 nohup /usr/bin/rustdesk &` (root GUI on the Xvfb display).
2. Capture only the RustDesk window: `wmctrl -l` / `xdotool search` for its id, then `import -window <id> /tmp/rd.png`.
3. OCR prep: `convert /tmp/rd.png -resize 300% -colorspace Gray -normalize /tmp/rd_big.png && tesseract /tmp/rd_big.png -`
4. One-time passwords rotate/expire: whenever the user reports failure, re-capture + re-OCR and confirm the value is still current before resending.
5. Send Remote ID + password in chat; tell the user it is one-time and to connect fast.

## RustDesk 1.4+ mobile "Login" (account-mode) trap
Newer phone/desktop apps show a **Login → Username/Password** section in the connect
sheet. Filling **Username** switches the app into *account-login mode*: it POSTs
`http://<id-server>:21114/api/login` (Pro-server API). Community hbbs has no 21114 →
**"Unknown Error: Failed to parse response … /api/login … Connection refused"**.
An empty-Username validation error ("Username missed") also signals the app is stuck
in account mode — NOT asking for the target peer's password.

Fix (user side, in order):
1. Phone app → Settings → ID/Relay Server config → **delete the "API Server" value** (keep only ID server + key). Save.
2. If no API Server field exists: Settings → Account → **Log out**, then retry.
3. Connect with Remote ID + the target's one-time/permanent password only — Username blank, Login section collapsed.
Corroboration: rustdesk/rustdesk issue #12875 (mobile connect breaks after self-hosted
account login; logging out restores normal connects).
Target-side username, if a login mode ever genuinely requires one, = the OS user
running the service (`root` here) — but with community hbbs the fix is disabling
account mode, never guessing usernames.

## Direction matters: who controls whom
- **Incoming (phone → VM)** — user's phone controls the VM GUI (Google sign-in etc.). The
  VM side needs nothing but status "Ready"; the session renders inside the RustDesk window.
- **Outgoing (VM → phone / Android host)** — needed when the PHONE's screen must appear on
  the VM (agent-driven phone storage/cache inspection). In the home window, type the phone's
  RustDesk ID into **Control Remote Desktop** and click the round Connect button right of the
  field. Android hosts with a password set → the VM's RustDesk pops an **"Authentication
  Required"** dialog (Password / Cancel / Authenticate) = client-side prompt for the REMOTE
  phone's RustDesk password. It is NOT the account-login `/api/login` trap and NOT an accept
  prompt — the session cannot start until that password is entered. Ask the user (phone app →
  Settings → Security → permanent password, or the temporary one on the phone's home screen);
  never guess.
- No live session is provable from screenshots alone — ground truth is connection lines in
  `/root/.local/share/logs/RustDesk/*/rustdesk_rCURRENT.log` (grep `conn|login|session|peer`).
- GUI relaunches (successive `/tmp/rd_guiN.log` attempts) kill active sessions and can leave a
  stale Settings page or auth dialog blocking the view. Reset before expecting a session:
  dismiss any dialog via its Cancel button (Escape does NOT dismiss it), then click top-nav
  **Home** (flutter 1.4 = single window; Home ≈ x66/y10, Settings ≈ x173/y10 window-relative).

## Reading user phone screenshots (OCR pipeline)
When the user forwards screenshots (RustDesk errors, phone UI) that cannot be viewed
directly, OCR them:
`convert <img> -resize 250% -colorspace Gray -normalize -sharpen 0x1 /tmp/u.png && tesseract /tmp/u.png -`
2.5x upscale + grayscale + normalize reliably pulls small phone UI text — error URLs
and field labels (the /api/login stack OCR'd fully this way). Read the full error
before theorizing about causes.

## Pitfalls (all hit in real sessions)
- `pkill -f "rustdesk --tray"` ALSO matches your own shell's command line → kills your own session (exit -15). Use the bracket trick: `pkill -f "[r]ustdesk --tray"`.
- Same trap while tearing down the noVNC stack (`x11vnc` / `websockify` / `cloudflared tunnel --url ...` patterns) — hit again 2026-09-10 and 2026-09-12. Teardown one-liners: `references/novnc-quick-tunnel-desktop.md`.
- **User ka noVNC session baar baar tootta/split hota hai?** Wajah = ek se zyada websockify instances us hi port (6080) pe. Count karne ka sahi tareeqa process **GROUPS** hai, PIDs nahi (websockify ek child fork karta hai) — `ps -eo pgid,args | awk '/[w]ebsockify/ {print $1}' | sort -u | wc -l` = exactly `1` hona chahiye. Self-heal + auto-reconnect detail: `references/novnc-quick-tunnel-desktop.md`; ready 2-min timer script: `scripts/novnc-chain-health.sh`.
- Patching only `RustDesk2.toml` does NOT work — the daemon reads `RustDesk.toml` too. Patch both or registration never happens.
- Don't trust "Ready"/log text alone for registration debugging — `tcpdump` UDP 21116 is the ground truth.
- GUI clicks DO work when done right: (1) `xdotool windowactivate <id>` (fallback windowraise+windowfocus) the target window FIRST — overlapping windows (Chrome ~1050x880 at 10,10) silently steal clicks; (2) locate buttons via `tesseract ... --psm 11 tsv` word boxes (cols 7-10 = left,top,w,h → click center = left+w/2, top+h/2); (3) add the window's screen offset to crop-relative coords. Escape does NOT dismiss dialogs — click their Cancel button. Full recipe: `references/gui-driving-ocr-xdotool.md`.

Session detail (exact error transcript + diagnosis trail): `references/mobile-account-login-21114.md`.
Driving/reading the headless GUI (screenshot+OCR+xdotool recipe), flutter 1.4 UI layout map, VM→phone (Android-host) connect flow: `references/gui-driving-ocr-xdotool.md`.
