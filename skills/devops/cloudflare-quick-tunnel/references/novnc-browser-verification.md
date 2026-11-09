# noVNC browser verification + link delivery gotchas (verified 2026-08-26)

Companion to `novnc-over-quick-tunnel.md`. Covers two things that file predates: the link-delivery pitfall that makes users report "link sahi se open nahi ho raha", and the full browser-based verification recipe for the noVNC 1.4+ UI.

## Pitfall: root URL is NOT the viewer — always hand out the full `/vnc.html` path

When the noVNC web root also serves the app it fronts (Munder's PHP app sits beside vnc.html on the same 6080 port), opening `<url>/` shows a **directory listing** (app/, core/, vendor/, vnc.html...), not the viewer — the user reads this as a broken link. ALWAYS give `<url>/vnc.html` explicitly, never the bare root URL.

## Browser-based end-to-end verification (noVNC 1.4+ UI, via browser-exec)

The "user says link is broken" debugging chain — page 200 via curl is NOT enough; prove the full flow in a real browser:

1. **WS through the tunnel from page JS** — `new WebSocket('wss://<url>/websockify')` → `onopen` fires = tunnel WS OK (curl gives false negatives through the CF edge).
2. **noVNC 1.4+ UI buttons are DIVs, not `<button>` elements** — `querySelectorAll('button')` returns `[]`; don't hunt for buttons. IDs:
   - Connect: `#noVNC_connect_button` (click → credentials dialog opens)
   - Credentials dialog: `#noVNC_credentials_dlg`; password input `#noVNC_password_input`; submit `#noVNC_credentials_button`
3. **Password input is React-controlled** — plain `.value =` may not register; use the native setter:
   ```js
   const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
   setter.call(document.getElementById('noVNC_password_input'), '<pass>');
   document.getElementById('noVNC_password_input').dispatchEvent(new Event('input', {bubbles:true}));
   document.getElementById('noVNC_credentials_button').click();
   ```
4. **Success proof**: `<canvas>` exists with real dimensions (e.g. 1440x900) AND `#noVNC_credentials_dlg` has LOST its `noVNC_open` class. Then `capture_screenshot()` the canvas and send it to the user as the "screen is live" proof image.

## Link delivery checklist (when handing a VNC link to Aamir)

1. Always the full `<url>/vnc.html` — never root.
2. Include the VNC password explicitly (it's the only gate; the quick-tunnel URL itself is public).
3. Warn that the URL changes on tunnel restart — re-run the URL-recovery helper each time.
4. If the user still says it won't open, run this browser verification before touching the tunnel — the tunnel is usually fine and the problem is the missing path.
