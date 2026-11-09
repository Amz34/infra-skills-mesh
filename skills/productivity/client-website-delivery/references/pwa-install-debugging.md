# PWA Install Not Appearing — Root Causes & Fallback Pattern

Debugged on A.S Love 7.0 (static site + trycloudflare tunnel, 2026-08).
Site had manifest + SW + icons + install-button JS all correct and still
"app install nahi aa raha". Server-side was NOT the problem — browser-side
rules were. Verified live: sw.js 200 `application/javascript`, manifest 200
`application/manifest+json`, all 12 SW CORE files 200 over the tunnel.

## Why the install prompt does not appear (in order of likelihood)

1. **Chrome engagement criteria.** `beforeinstallprompt` fires only after the
   user has interacted with the page / spent meaningful time on it (typically
   2 visits with a gap, or ~30s dwell). A brand-new tunnel URL on first visit
   NEVER prompts. This alone explains most "install nahi aa raha" reports.
2. **In-app browsers (WhatsApp/Telegram/Instagram) never fire the event at
   all** — the install API is disabled there. User must open in Chrome/Safari.
3. **iOS Safari never fires `beforeinstallprompt`.** The only route is
   Share → "Add to Home Screen" (needs `apple-touch-icon` + the
   `apple-mobile-web-app-*` metas in `<head>` for a proper standalone icon).
4. **SW install silently failed.** If ANY file in the SW `CORE` list 404s,
   `caches.addAll()` rejects and the SW never activates → no prompt, and the
   `beforeinstallprompt` listener never runs. Always curl-verify every CORE
   file (disk AND tunnel) before debugging anything else.

## The 3-second fallback button (the fix)

Don't rely on the browser to show the prompt. Make the install button appear
regardless, then branch on whether a deferred prompt exists:

```js
(function () {
  var deferred = null;
  var isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  var isStandalone = window.matchMedia("(display-mode: standalone)").matches;

  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferred = e;
    document.getElementById("installApp").style.display = "inline-flex";
  });
  window.addEventListener("appinstalled", function () {
    document.getElementById("installApp").style.display = "none";
  });

  // Fallback: show the button even if the browser never prompted
  window.addEventListener("load", function () {
    setTimeout(function () {
      if (isStandalone) return;
      var btn = document.getElementById("installApp");
      if (btn && btn.style.display === "none") btn.style.display = "inline-flex";
    }, 3000);
  });

  document.addEventListener("click", function (e) {
    var t = e.target.closest ? e.target.closest("#installApp") : null;
    if (!t) return;
    if (deferred) {
      deferred.prompt();          // real Chrome install dialog
      deferred.userChoice.then(function (c) { if (c.outcome === "dismissed") t.style.display = "none"; });
      return;
    }
    var msg = isIOS
      ? 'Open in Safari, tap the Share icon, then choose "Add to Home Screen".'
      : 'Tap the browser menu (\u22ee) and choose "Add to Home screen" / "Install app". Make sure you are in Chrome (not WhatsApp/Telegram).';
    alert(msg);
    t.style.display = "none";
  });
})();
```

Button HTML: `style="display:none"` + a `.install-btn` class so it stays hidden
until JS shows it.

## Service worker cache version bump (making changes reach the user)

After ANY content change, bump `const CACHE = "as-love-7.0-vN"` → vN+1 in sw.js.
Old caches are deleted in `activate` (`caches.keys().filter(k => k !== CACHE)`),
so returning visitors get fresh content. Verify the new version is live over the
tunnel: `curl -s <tunnel>/sw.js | grep -o "as-love-7.0-v9"`. Tell the user to
refresh the page twice (first load updates SW, second loads new content).

## Stale server process serving old code

Symptom: local files fixed, but live/tunnel behavior unchanged (here: PDF
filename case + download headers). Root cause: an old `private_server.py`
PID was still running with pre-fix code. Fix pattern:
`ps aux | grep private_server` → `kill <PID>` → verify port free
(`ss -tlnp | grep <port>`) → restart in background
(`cd <site> && python3 private_server.py <port>` with terminal
background=true) → curl-verify headers on local AND tunnel.

## Asset dedupe before adding photos

When adding "new" photos from an email to an existing gallery, MD5-check them
against existing assets FIRST — 5 "new" photos turned out to be byte-identical
duplicates of already-present gallery files (same size was the giveaway:
2,131,223 == 2,131,223). `md5sum` both sets and compare; delete the dupes,
keep the real additions. Avoids silent duplicates in the gallery.
