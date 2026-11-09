# Chrome "Allow remote debugging?" popup — headless handling recipe

Session-verified recipe (2026-08, Chrome 151, Ubuntu headless VM, Xvfb :99).

## Why the popup exists
Chrome 136+ blocks `--remote-debugging-port` on the DEFAULT user-data-dir
(`~/.config/google-chrome`) unless the user has ticked the chrome://inspect
toggle. When the browser-use harness connects to a default-profile Chrome via
DevToolsActivePort, Chrome 147+ shows an "Allow remote debugging?" dialog —
**a fresh one for every new CDP connection**. The daemon's single held
connection is what makes Allow a one-time click; looping browser_exec retries
while the popup is up just spawns more dialogs.

## Preferred path: skip the popup entirely
Use a non-default user-data-dir + explicit port, then bind the daemon with
BU_CDP_URL (see main SKILL.md). No dialog ever appears.

## Fallback: click the popup on Xvfb
Packages needed: `xdotool`, `imagemagick` (import), `tesseract-ocr`.

1. Launch GUI Chrome on the virtual display:
   ```bash
   Xvfb :99 -screen 0 1920x1080x24 &
   export DISPLAY=:99
   google-chrome --no-sandbox --disable-gpu --user-data-dir=$HOME/.config/google-chrome about:blank
   ```
2. Enable the toggle so Chrome will accept the connection:
   ```bash
   python3 - <<'EOF'
   import json, os
   p = os.path.expanduser("~/.config/google-chrome/Local State")
   d = json.load(open(p))
   d.setdefault("devtools", {}).setdefault("remote_debugging", {})["user-enabled"] = True
   json.dump(d, open(p, "w"))
   EOF
   ```
   Then relaunch Chrome PLAIN (no port flag). It writes DevToolsActivePort (port 9222).
3. Trigger the connection (browser_exec call) → dialog appears.
4. Screenshot + OCR to locate the Allow button:
   ```bash
   DISPLAY=:99 import -window root /tmp/s.png
   tesseract /tmp/s.png stdout --psm 11 tsv | awk -F'\t' '$12!="" {print $7,$8,$9,$10,$12}'
   # Allow button ~ x=680-718, y=310-321 (varies with window size)
   ```
5. Click — but note: **synthetic mouse clicks are ignored by Chrome on this
   dialog** (security). Keyboard may work but focus order is unpredictable:
   - 1 Tab + Return can land on Cancel (dialog stays)
   - 2 Tabs + Return can land on the "Turn off in settings"/"Learn more" link
     (opens chrome://inspect instead of allowing)
   Retry with different Tab counts and re-screenshot each time.
6. chrome://inspect/#remote-debugging also has a "Allow remote debugging for
   this browser instance" checkbox — clicking it saves the toggle, but a
   Chrome restart is needed for it to take effect, and the popup still appears
   per new connection afterwards.

## Bottom line
If the popup route fights you more than ~2 retries, abandon it: custom
user-data-dir + BU_CDP_URL is deterministic and popup-free.
