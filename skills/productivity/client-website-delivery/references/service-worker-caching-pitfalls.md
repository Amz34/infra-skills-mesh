# Service Worker Caching Pitfalls (PWA site updates never reaching the user)

Debugged on A.S Love 7.0 (static site + trycloudflare tunnel, 2026-08).

## The cache-first SW trap: "refresh karke bhi no use"

Symptom: user reports a feature broken (here: Download buttons) across
MULTIPLE fix rounds. Server verified 200 + correct headers, JS handler added,
SW cache version bumped v8→v9→v10, user refreshed repeatedly. Still broken.

**Root cause:** the SW `fetch` handler was **cache-first for EVERYTHING**
(`caches.match(req).then(hit => hit || fetch(req))`). A returning visitor's
browser fetched `main.js` / `index.html` / `sw.js` **from the old SW cache**,
not the server. The user's phone ran the OLD main.js (no download handler)
and the OLD SW. Server-side curls proving the new code was live meant
nothing — the client never asked the server for it. Refreshing doesn't help
when the SW itself is stale: the old SW answers the refresh.

**Diagnostic lesson:** server-side 200 + fresh headers do NOT prove the
user's device receives them when a service worker controls the page. When a
user says "refresh karke bhi no use", suspect SW cache staleness FIRST —
grep the SW's fetch handler to see its strategy before re-fixing server code.
A version-bump alone is insufficient when the handler is cache-first.

## Fix (3 layers, applied together)

1. **Network-first strategy** for everything except immutable assets
   (photos/video): `fetch(req)` first, cache the response for offline
   fallback, hit cache only on network failure. Never cache-first for
   HTML/JS/CSS.

2. **Bypass SW entirely for downloads:**
   `if (req.url.includes("/assets/docs/")) return;` at the top of the fetch
   handler — no `respondWith`, browser talks straight to the server, so
   `Content-Disposition: attachment` headers are always fresh and no stale
   cached copy can intercept Download buttons.

3. **Force SW takeover:** `self.skipWaiting()` in install +
   `self.clients.claim()` in activate (plus old-cache deletion). Without
   these the new SW waits for the old one to die, so the stale SW keeps
   serving the user on their next visit.

## Related: stale server process vs stale SW cache — distinguish

- Old `private_server.py` PID still running with pre-fix code → kill,
  verify port free (`ss -tlnp | grep <port>`), restart background, curl-verify.
- SW cache staleness → user's device never re-fetched (see above). Check
  strategy + version reachability over tunnel:
  `curl -s <tunnel>/sw.js | grep -o "as-love-7.0-vN"`.
