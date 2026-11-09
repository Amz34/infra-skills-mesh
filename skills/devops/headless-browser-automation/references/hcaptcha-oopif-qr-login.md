# CAPTCHA iframes (hCaptcha) + QR login + Chrome restart after gateway shutdown (proven 2026-08-23)

Session: connecting Discord (Developer Portal) to Hermes on the Oracle VM.
Validated techniques for hCaptcha OOPIFs, QR-code logins, and recovering the
GUI Chrome after a gateway interruption.

## 1. hCaptcha inside cross-origin OOPIFs — raw websocket, not JS clicks

Discord's "Are you human?" check is hCaptcha in **out-of-process iframes**
(OOPIFs). Parent-page JS cannot reach them (cross-origin), and
`Input.dispatchMouseEvent` at viewport coords works for the checkbox but you
cannot *inspect* the challenge without a sessionId.

### Discover the OOPIF sessions (Target.getTargets does NOT list them)

`Target.getTargets` returns only top-level targets. OOPIFs arrive as
`attachedToTarget` events. cdp_drive's `CDP.call()` lacks sessionId support
(sending a `sessionId` param raises `KeyError: 'result'`), so use **raw
websocket send with a manual msg_id** and collect events:

```python
import cdp_drive, json, time
tab = cdp_drive.get_tab()
c = cdp_drive.CDP(tab['webSocketDebuggerUrl'])   # c.sock is the raw ws
def send(method, params=None, _id=None):
    c.msg_id += 1
    c.sock.send(json.dumps({'id': c.msg_id, 'method': method, 'params': params or {}}))
    return c.msg_id
send('Target.setAutoAttach', {'autoAttach': True, 'waitForDebugger': False, 'flatten': True})
time.sleep(2)
# read pending events off the socket
c.sock.settimeout(2)
try:
    while True:
        evt = json.loads(c.sock.recv(1 << 16))
        if evt.get('method') == 'Target.attachedToTarget':
            print(evt['params']['sessionId'], evt['params']['targetInfo'].get('url'))
except Exception:
    pass
```

Then probe each session by sending a `Runtime.evaluate` **with its sessionId**
in the same raw-send manner; the reply comes back keyed by your msg_id with
`result.result.value` = iframe body text (e.g. checkbox iframe h=76
"I am human / Privacy - Terms"; challenge iframe h=570).

### Checkbox click needs `mouseMoved` BEFORE the press/release

A plain `mousePressed`/`mouseReleased` at the checkbox coords had **no visible
effect**. Adding `mouseMoved` first made the challenge open (iframe height
150→570):

```python
for x, y in [(585, 519), (590, 519), (580, 519)]:
    c.call('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': x, 'y': y})
c.call('Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': 585, 'y': 519, 'button': 'left', 'clickCount': 1})
c.call('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': 585, 'y': 519, 'button': 'left', 'clickCount': 1})
```

### Challenge failure → click "Skip" to reload a fresh challenge

A wrong answer leaves the challenge iframe showing only
`Please try again. ⚠️ / Skip / EN` — no image grid. Clicking **Skip** resets
to a brand-new task (proven: fresh "click on the TWO icons that are similar
to each other" rendered afterward). The image selection itself is a
**human-only step** — screenshot the challenge, send it to the user with
exact instructions ("pick the 2 similar icons, press Verify"), never attempt
to auto-solve it.

## 2. Discord QR-code login flow (user approves on phone)

`discord.com/login?redirect_to=%2Fdevelopers%2Fapplications` shows a QR
alternative to email/password.

1. Screenshot the login page, decode with `zbarimg /tmp/s.png` → prints
   `QR-Code:https://discord.com/ra/<token>`.
2. **QRs expire in ~60 s.** Send BOTH the decoded link and the QR image
   (user asked for the link alongside the screenshot) with an explicit
   "scan immediately" instruction.
3. User flow: Discord mobile app → Settings (gear) → **Scan QR Code** →
   Confirm/Approve. No email/OTP involved.
4. After approval the page jumps to the hCaptcha step (§1) — and the login
   session is then cookie-bound to the Chrome profile.

## 3. Login-session persistence check (after Chrome restarts)

After a gateway shutdown/restart, relaunch Chrome with the SAME
`--user-data-dir` profile. To verify the login actually survived:

- Page title alone lies: `My Applications | Discord Developer Portal` renders
  even when logged OUT (body shows "Create Account / Log In" buttons).
- Check cookies: `Network.getAllCookies` filtered to discord.com domains.
  Analytics + Cloudflare cookies (`__dcfduid`, `cf_clearance`, `_ga`…) exist
  logged-out. A **real session needs the auth token cookie** — if only the
  analytics/cf set is present, the session is gone: redo the QR login (§2).
- On this VM the Discord session did NOT survive the gateway shutdown; expect
  a fresh QR scan after any Chrome kill.

## 4. Chrome restart recipe after gateway shutdown

- Xvfb often survives (it's a separate background process); only Chrome gets
  SIGKILLed (exit code -9). Check with `process(action='poll')`.
- **Restart via `terminal(background=true)` — the tool REFUSES nohup/disown/
  setsid wrappers** ("use background=true so Hermes tracks the process").
- **pgrep self-match trap:** `pgrep -af "chrome.*9255"` matches the very
  shell command running the pgrep (the pattern string appears in its own
  cmdline). Use `ps aux | grep -E "Xvfb|chrome" | grep -v grep` instead.
- Restart order: Xvfb first (if dead), then Chrome on the same profile +
  port 9255. Verify with `curl -s http://localhost:9255/json/version`.
- Chrome exited -9 once at ~108 s uptime with only benign GCM/extension
  errors in the log — a plain relaunch (adding `--disable-gpu --no-sandbox`)
  came up clean. If the port is still bound, kill stale Chrome first.

## Related

- `oauth-login-flows-headless.md` — cross-origin GSI iframe clicks (same raw
  CDP `Input.dispatchMouseEvent` family) + CLI OAuth callback gotchas.
- `/tmp/cdp_drive.py` — CDP driver: `get_tab()/js()/screenshot()` module fns +
  `CDP(ws_url)` class with `.call(method, params)` (params dict, **not**
  kwargs — `CDP.call(url=...)` raises TypeError) and `.sock` raw ws.
- Main SKILL.md — GUI Chrome launch recipe (Xvfb :99, profile, port 9255).
