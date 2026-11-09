# Third-party iframes + SPA shells in automation browsers (proven 2026-08)

Two traps that masquerade as "the site is broken" during browser_exec debugging
— both hit while diagnosing a "booking link opens but blank" report on a
Cal.com embedded calendar.

## Trap 1: automation Chromium loads NO third-party iframes

Headless/automation Chromium (browser-use harness) does not create child
frames for ANY cross-origin iframe — not even a plain `<iframe
src="https://example.com">` injected by JS.

Tell-tale: `cdp('Page.getFrameTree')` shows only the top frame, no children,
for an iframe whose element exists with a correct `src` and whose network
panel shows no request.

**Control test before accusing the target site:** inject
`document.createElement('iframe')` with `src='https://example.com'`, wait a
few seconds, re-run `Page.getFrameTree`. If the control also produces no
child frame, the browser policy is the blocker → NOT a real bug in your page.

**Real proof that a site blocks framing:** response headers, not the frame
tree. `curl -sI "<iframe-url>" | grep -iE "x-frame|frame-ancestors"` — an
`X-Frame-Options: DENY` / `frame-ancestors 'self'` header is a real block;
empty output means framable. Sites with official embed modes (Cal.com
`?embed=true`) typically send no such headers and work in real browsers.

## Trap 2: HTTP 200 + big HTML ≠ page rendered

JS-heavy SPA shells (Next.js/React booking pages, etc.) return a large
generic HTML shell — e.g. Cal.com returned 562KB with ZERO event-specific
data (`eventType`, title, slug all absent). curl size/grep cannot distinguish
a live page from a broken one because the real content loads client-side
after mount.

**Decisive check:** render in a real browser, wait ~6s for the client-side
fetch, then read `document.body.innerText` + `page_info()` title. A live
event shows its real title and content; a broken one shows an empty/error
body.

## User-side "blank page" causes (after the code is proven fine)
- Browser cache of a pre-setup empty shell → hard refresh / incognito.
- In-app webviews (Telegram etc.) render JS-heavy SPAs blank → tell the user
  to open in the external browser (3-dot menu).
- Adblocker / privacy extensions blocking the frame → keep a visible direct
  CTA link next to any embedded iframe so there is always a working path.
