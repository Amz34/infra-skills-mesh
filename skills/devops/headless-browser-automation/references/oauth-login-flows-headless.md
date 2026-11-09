# OAuth login flows + cross-origin iframes on headless VMs (proven 2026-08-23)

Session: connecting X (Twitter) via `xurl auth oauth2` on the Oracle VM for a
Product Hunt launch boost. Two reusable techniques emerged.

## 1. Cross-origin login iframes (Google GSI) — raw CDP clicks, not JS .click()

developer.x.com's "Continue with Google" button lives inside a cross-origin
iframe (`accounts.google.com/gsi`). All JS-through-parent approaches fail:

- `iframe.contentDocument` → `SecurityError: cross-origin` — cannot reach in.
- `el.click()` on the `<iframe>` element → nothing happens (the real button's
  listener lives inside the iframe document).

**Fix: raw CDP `Input.dispatchMouseEvent` at the iframe's viewport coords.**
OS-level input lands inside the iframe regardless of origin:

```python
import cdp_drive  # /tmp/cdp_drive.py — has NO click helper, only js/navigate/screenshot + CDP class

tab = cdp_drive.get_tab()
box = cdp_drive.js('''(() => {
  const f = [...document.querySelectorAll('iframe')]
    .find(x => (x.src||'').includes('accounts.google.com/gsi'));
  if (!f) return null;
  const r = f.getBoundingClientRect();
  return [r.x, r.y, r.width, r.height];
})()''', tab)                       # e.g. [539.5, 348.5, 360, 40]
cx, cy = int(box[0]+box[2]/2), int(box[1]+box[3]/2)
c = cdp_drive.CDP(tab['webSocketDebuggerUrl'])
c.call('Input.dispatchMouseEvent', {'type':'mousePressed','x':cx,'y':cy,'button':'left','clickCount':1})
c.call('Input.dispatchMouseEvent', {'type':'mouseReleased','x':cx,'y':cy,'button':'left','clickCount':1})
c.sock.close()
```

- cdp_drive's `CDP.call(method, params)` is the raw channel — no `websocket`
  module needed in the interpreter (cdp_drive bundles its own).
- The OAuth popup opens in a **NEW tab/window 3-5s later** — enumerate
  `GET http://localhost:9255/json` and look for the new page target; don't
  assume it replaced the current tab.
- If no popup appears: suspect popup blocking (rare on Xvfb GUI Chrome) or the
  click coordinates being off after layout shifts (`--disable-infobars`
  prevents the yellow banner shift).

## 2. CLI OAuth callback flows on a headless server (xurl pattern)

`xurl auth oauth2 --app my-app` prints "opening browser…", spawns xdg-open
(defunct without a display), and runs a local callback listener. Three server
gotchas:

1. **Callback port must be free.** xurl binds `localhost:8080`. A docker
   container (e.g. `wp-sandbox`) or dev server on 8080 breaks the listener.
   ```bash
   docker stop wp-sandbox
   (echo >/dev/tcp/127.0.0.1/8080) 2>/dev/null && echo busy || echo free
   ```
2. **Registered redirect URI must resolve.** This VM's `my-app` was registered
   with `https://<random>.trycloudflare.com/callback`; when that quick tunnel
   died, the listener failed with a DNS/lookup error. Fix without touching
   secrets:
   ```bash
   xurl auth apps redirect-uri set my-app http://localhost:8080/callback
   xurl auth status   # shows current registered URI per app
   ```
   The X dashboard whitelist must match too (App → User authentication
   settings → Redirect URI). Generic lesson: before debugging any OAuth CLI,
   check `auth status` for a dead/foreign redirect URI.
3. **No browser → run the auth CLI in the background and drive GUI Chrome
   yourself.** `terminal(background=true)` keeps the callback listener alive
   while you complete login in Xvfb Chrome (port 9255, profile
   `/tmp/chrome-gui2`, `--remote-debugging-port` + `--disable-infobars`).
   The agent drives the browser; the **user still does the Google/OTP step**
   — that handoff is the fallback, never automated credentials.

## Related
- `/tmp/cdp_drive.py` — small CDP driver (get_tab/js/navigate/screenshot + CDP.call).
- GUI Chrome launch recipe in the main SKILL.md (Xvfb :99, non-default profile,
  `--remote-debugging-port=9255`).
- X app naming: `my-app` (client id registered), redirect URI now
  `http://localhost:8080/callback` — dashboard whitelist pending user login.
