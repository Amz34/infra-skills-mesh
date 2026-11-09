# Driving the headless RustDesk GUI (screenshot + OCR + xdotool)

Validated on the Oracle VM (Xvfb :99), Sep 2026, while trying to inspect a phone's
storage (WhatsApp/media cache scan) through a VM→phone RustDesk session. Works for
reading UI state and clicking reliably when the stack discipline below is followed.

## Environment facts (this VM)
- GUI runs as root on Xvfb `:99` (1440x900): `sudo -u root env DISPLAY=:99 rustdesk`
  (stdout goes to `/tmp/rd_guiN.log` — N increments on every relaunch).
- Service: `rustdesk --service` (root). Real logs (NOT ~/.local/share/rustdesk/log):
  `/root/.local/share/logs/RustDesk/rustdesk_rCURRENT.log` plus `service/` and
  `check-hwcodec-config/` subdirs.
- VM RustDesk ID: 385 948 621 (shown on Home). Phone host ID used: 112 617 3543.
- Other windows on :99 overlap RustDesk: e.g. Chrome (~1050x880 at 10,10) sits over the
  RustDesk window (~800x600 at 320,150) and silently swallows clicks meant for it.

## State checks before acting
1. `ps aux | grep -i rustdesk` → GUI process + `--service` both present.
2. Window inventory: loop `xdotool search --name ".*"` → `getwindowname` +
   `getwindowgeometry` per id (also `xdotool search --name RustDesk`). Note sizes +
   positions so you know what overlaps what.
3. Session ground truth is in the LOGS, not the screen: `sudo grep -iE
   "incoming|outgoing|connected|login|session|peer" <log>` — no matching lines means no
   live session, whatever the UI suggests.

## Screenshot + OCR pipeline
- Full capture: `DISPLAY=:99 import -window root /tmp/rd.png`
- State reading: `tesseract /tmp/rd.png /tmp/o --psm 11` (psm 11 = sparse text, best for
  UI). psm 6 only when the region is a clean paragraph/line.
- Click targets (word boxes): `tesseract /tmp/rd.png /tmp/o --psm 11 tsv`, then parse:
  TSV columns 7,8 = left,top; 9,10 = width,height; 12 = word text. Click center =
  `left+w/2, top+h/2`. Filter: `awk -F'\t' 'NF>=12 && $12!="" {print $7","$8" "$12}'`.
- Region OCR: `convert /tmp/rd.png -crop WxH+X+Y +repage -resize 200% /tmp/c.png` then
  tesseract. **Crop offsets are relative to the crop origin** — when cropping from a
  window screenshot, add the window's screen offset to get absolute coords; when
  cropping the full root capture at 0,0 the coords ARE absolute already.

## Click discipline (the part that makes it work)
1. **Raise/focus the target window FIRST**: `xdotool windowactivate <winid>`
   (fallback: `windowraise` + `windowfocus`). Without this, clicks land on whichever
   window is actually on top in the X stack — screenshots don't reveal stacking.
2. `xdotool mousemove <absX> <absY> click 1` with ROOT-absolute coordinates.
3. After every click: re-screenshot + re-OCR and verify the state actually changed
   before issuing the next action. Coordinate guesses are cheap to correct this way;
   blind sequences drift.
4. Dialogs: `Escape` does NOT dismiss the RustDesk "Authentication Required" dialog —
   you must click Cancel (or Authenticate). OCR-TSV the dialog buttons and click.

## RustDesk 1.4 (flutter) UI map — 800x600 window at screen (320,150)
- Top bar (window-relative): Home ≈ (66,10), Settings ≈ (173,10).
- Home page: left card "Your Desktop / ID and password" (VM ID ~y162); right side
  "Control Remote Desktop": an ID input (~y117-128) + round green Connect button,
  center ≈ window (430,163) ≈ absolute (750,313).
- Settings page: left sidebar General / Network / Security / Display / Account / About.
  Accidentally landing here is the classic misclick symptom.
- "Authentication Required" dialog: ~400x287 at screen (0,0), Password field +
  Cancel/Authenticate. Cancel ≈ (101,248). This dialog is the CLIENT asking for the
  REMOTE peer's RustDesk password — it reappears on EVERY connect attempt to a
  password-protected host until the right password is entered. It is NOT the
  account-login /api/login trap (see references/mobile-account-login-21114.md).

## VM→phone (Android host) connect flow
1. Make sure the GUI is on the Home page (click top-nav Home if a stale Settings page
   or dialog is showing — GUI relaunches leave stale state).
2. Ensure the phone's RustDesk ID is in the "Control Remote Desktop" field, click the
   green Connect button (≈750,313).
3. Within ~2-4s the "Authentication Required" dialog appears → type the phone's
   RustDesk password → Authenticate. The phone screen then renders inside the main
   window (verify by re-OCR: look for the phone's UI text, e.g. app labels).
4. Wrong password → dialog just re-prompts; ask the user again rather than guessing.

## Pitfalls hit
- Raw whole-screen clicks from a single OCR pass drift into the wrong page (Connect →
  Settings). Fix: verify page state by OCR before and after, and raise the window.
- GUI relaunches (`rd_guiN.log` counter) silently kill active sessions; always re-check
  Home/Ready state and logs after any restart.
- Old assumed log paths (`~/.local/share/rustdesk/log`) are wrong on this VM — the real
  hierarchy is `/root/.local/share/logs/RustDesk/`.
