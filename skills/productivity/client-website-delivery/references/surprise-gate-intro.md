# Surprise-gate intro overlay (gift-box splash before site reveal) — proven 2026-08-23

User request verbatim: "link open hone par first surprise gift box luring way
romantic me dekhe use clickkarne par website open ho.." — first show a luring
surprise gift box; tapping it opens the website. Built for the A.S Love 7.0
anniversary site. Reuse for any surprise/gift/teaser landing experience.

## Pattern

- Full-screen fixed overlay (`position:fixed; inset:0; z-index:9999`) sitting
  ABOVE all site content (heart/rose shower containers live at z-index ~6).
- The site loads and animates normally BEHIND the gate (petals fall, countdown
  runs) — the gate is pure presentation, so the reveal feels alive the instant
  it fades.
- Gate content stack: halo glow → kicker line → serif title → Urdu/RTL line →
  CSS-built gift box → pulsing "tap to open" hint.
- Body scroll-lock while gate is up: `body.gate-lock { overflow:hidden }`
  (class on `<body>` in HTML), removed on open.
- Click/tap ANYWHERE on the gate (whole gate is the tap target — huge for
  mobile): box lid flies up + rotates, box scales + glows, ~16–18 gold sparks
  burst (JS-spawned spans with CSS custom props `--dx/--dy`), gate fades
  (`opacity:0; visibility:hidden` transition), then gate element removed from
  DOM (~2.2s) so it can't block anything.
- Accessibility: `role="button" tabindex="0"` + Enter/Space keydown handler.

## Mobile-perfect essentials (user EXPLICITLY demanded: "make sure for
perfectly compatible for mobile view" — treat as mandatory for every build)

1. **Media query ≤420px:** scale the whole box down (190→158px), lid/body/
   ribbon/bow all proportional, title via `clamp()`, safe-area padding
   (`env(safe-area-inset-top/bottom)`), `-webkit-tap-highlight-color: transparent`.
2. **Landscape/short screens (`max-height:520px` and orientation:landscape):**
   compact every element so nothing clips or scrolls.
3. **Touch = click:** no hover dependency; whole gate clickable; keydown
   fallback for accessibility.
4. **Verify on an EXACT phone viewport before preview link** — headless
   `--window-size` lies; use CDP `Emulation.setDeviceMetricsOverride`
   (see headless-browser-automation skill,
   `references/mobile-viewport-cdp-verification.md`):
   - `matchMedia('(max-width:420px)').matches` true
   - box `getBoundingClientRect()` fully within viewport
   - `document.documentElement.scrollWidth <= innerWidth` (no horizontal scroll)
   - tap → gate removed → body unlocked → page scrollable again

## Key CSS pieces (pure CSS gift box, no images)

- `.gift-box` (relative, `filter: drop-shadow`), `.gift-lid` (absolute top,
  wider than body, `z-index:3`), `.gift-body`, `.gift-ribbon` (vertical gold
  band), `.gift-ribbon-h` (horizontal band), `.gift-bow` (`::before`/`::after`
  loops + knot span).
- **Float bob on a WRAPPER** (`.gift-bob` with translateY keyframes), NOT on
  `.gift-box` itself — otherwise the open-state scale transform on `.gift-box`
  conflicts with the bob animation (animation wins over transform).
- Open transitions under `.gift-gate.open`: lid `translate(-50%,-74px)
  rotate(-14deg)`, box `scale(1.24) brightness(2.1)`, gate `opacity:0` with
  `transition: opacity .9s ease .2s, visibility 0s 1.2s`.
- `.spark` spans: `@keyframes sparkFly` uses `translate(var(--dx), var(--dy))`
  set per-span in JS (random angle × distance).
- Respect `prefers-reduced-motion` (site-wide rule zeroes animation durations;
  gate still opens instantly — fine).

## JS shape (vanilla, no deps)

```js
(function () {
  var gate = document.querySelector(".gift-gate");
  if (!gate) return;
  var opened = false;
  function openGift() {
    if (opened) return; opened = true;
    gate.classList.add("open");
    document.body.classList.remove("gate-lock");
    for (var i = 0; i < 18; i++) { /* spawn .spark with --dx/--dy */ }
    setTimeout(function () { gate.classList.add("done"); }, 950);
    setTimeout(function () { gate.parentNode.removeChild(gate); }, 2200);
  }
  gate.addEventListener("click", openGift);
  gate.addEventListener("keydown", function (e) {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openGift(); }
  });
})();
```

## Pitfalls

- SW cache MUST be bumped (v1→v2→v3→v4...) after CSS/JS changes or returning
  visitors get the stale gate.
- Gate HTML goes right after `<body>` in index.html only (entry page) — other
  pages don't re-gate.
- If main.js loads at end of body, no DOMContentLoaded wrapper needed for the
  gate block; if loaded in `<head>`, wrap it.
- Verify with `node --check main.js` before the browser test.
