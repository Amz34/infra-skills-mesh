# Media (Audio/Video) Integration into a SW-Managed Static Site

Proven on A.S Love 7.0 ("Our Song" dedicated player, 2026-08) — static site
served by `private_server.py` (custom Python `SimpleHTTPRequestHandler`
subclass) behind a trycloudflare tunnel, with a service worker.

## 1. Pitfall: custom server MIME map missing the new extension

`private_server.py` overrides `guess_type()` with an `EXT_MAP` dict; any
extension NOT in the map falls back to `application/octet-stream`:

```
".mp3": "audio/mpeg",   # missing → curl shows application/octet-stream
```

Adding `assets/audio/song.mp3` without updating `EXT_MAP` serves the file
(200, full size) but with the WRONG content type — `<audio>` may still play
in some browsers, but the type is wrong and anything stricter (fetch, some
mobile WebViews, strict MIME sniffing) breaks.

**Fix:** add `.mp3`: `"audio/mpeg"` (and `.ogg`, `.wav`, `.m4a`, etc. as
needed) to `EXT_MAP`, then RESTART the server (old PID keeps serving the
pre-fix map — see SW-pitfalls reference for the stale-process distinction).

**Verify content type, not just status:**
```bash
curl -s -o /dev/null -w "%{http_code} type=%{content_type} size=%{size_download}\n" \
  http://localhost:8077/assets/audio/our-dedicated-song.mp3
# expect: 200 type=audio/mpeg size=<full bytes>
```
Repeat the same curl against the TUNNEL URL — localhost green does not
prove the tunnel serves the updated map.

## 2. SW precache for media + cache version bump

To make the song playable offline (or first-tap instant), add the audio file
to the SW `CORE` precache list AND bump the `CACHE` version — otherwise
existing visitors keep the old SW that never precaches it:

```js
"./assets/audio/our-dedicated-song.mp3"   // in CORE array
const CACHE = "aslove-v13";                // bumped from v12
```

`skipWaiting()` + `clients.claim()` already in place → new SW takes over on
next load. Verify over tunnel: `curl -s <tunnel>/sw.js | grep -o "aslove-vN"`
and `grep -c "our-dedicated-song"` (expect 1).

## 3. Themed player pattern (HTML + JS, no framework)

Theme-matched "Our Song" section — glass card reusing site design tokens
(`--gold-soft`, `.eyebrow`, `.serif`, `.btn-glow`, `.glass`, `.reveal`),
inline styles only for layout deltas so no CSS file change is needed:

```html
<button id="song-play" class="btn btn-glow" aria-label="Play our song">
  <span id="song-btn-label">▶ &nbsp;Play our song</span>
</button>
<audio id="our-song" src="assets/audio/our-dedicated-song.mp3" preload="none"></audio>
<p id="song-status"></p>
```

JS in `main.js` (inside existing IIFE):

```js
var song = document.getElementById("our-song");
var songBtn = document.getElementById("song-play");
var songLabel = document.getElementById("song-btn-label");
if (song && songBtn) {
  songBtn.addEventListener("click", function () {
    if (song.paused) {
      var p = song.play();
      if (p && p.catch) p.catch(function(){});   // autoplay-policy rejections
      songLabel.innerHTML = "❚❚ &nbsp;Pause";
    } else { song.pause(); songLabel.innerHTML = "▶ &nbsp;Play our song"; }
  });
  song.addEventListener("ended", function () {
    songLabel.innerHTML = "▶ &nbsp;Play our song";
  });
}
```

Notes:
- `preload="none"` keeps a 1.4MB file from slowing first paint; audio starts
  on tap.
- `song.play()` returns a Promise — always `.catch()` it (browser autoplay
  policy rejects programmatic play without user gesture in some contexts).
- Button toggles label (▶/❚❚) + optional status text; reset on `ended`.

## 4. Full verification checklist (all layers)

1. `node -c assets/js/main.js && node -c sw.js` — syntax (note: main.js is
   at `assets/js/main.js`, NOT repo root).
2. `grep -c "Our Song\|our-dedicated-song" index.html` — section present.
3. localhost curl: page 200, audio 200 + `type=audio/mpeg` + full size.
4. tunnel curl: same checks against `https://<tunnel>/...`.
5. `curl -s <tunnel>/ | grep -o "Our Song\|our-dedicated-song" | uniq -c`
   — served HTML actually contains the section.
6. `curl -s <tunnel>/sw.js | grep -o "aslove-vN"` — new SW version live.

## Scope discipline

User rule on this site: "no other changes should be done" — when adding a
feature, touch ONLY the files the feature needs (index.html section,
main.js handler, sw.js CORE + version, server EXT_MAP). Do not refactor,
restyle, or "improve" adjacent code; report what was touched.
