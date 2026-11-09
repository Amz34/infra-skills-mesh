# React + Vite Premium Build (pazi.ai-class demo)

When Aamir says "expert pro demo" / "premium stack" / "pazi.ai jaisi site",
this is the recipe. Verified 2026-08 on AVVS Expert Pro demo
(avvs-expert-pro.pages.dev), built and deployed in ~1 session.

## Why this stack
pazi.ai fingerprint (from headers + bundle analysis): nginx static server +
hashed Vite assets (`/assets/index-<hash>.js`) + React + Tailwind (CSS
custom-property layers) + GSAP (ScrollTrigger/ScrollSmoother/Flip) +
Three.js + PostHog analytics + Sentry error tracking. All FREE tooling —
the premium feel is animation + design taste, not paid software.

## Scaffold (files written directly, faster than create-vite rewrite)
```
package.json        # react, react-dom, gsap, three; dev: vite, @vitejs/plugin-react, tailwindcss, postcss, autoprefixer
vite.config.js      # plugins: [react()], build.outDir 'dist'
postcss.config.js   # tailwindcss + autoprefixer
tailwind.config.js  # content ['./index.html','./src/**/*.{js,jsx}'], extend colors (navy/teal/gold per client)
index.html          # meta + OG + favicon data-URI SVG + Google Fonts preconnect
src/index.css       # @tailwind directives + base layer (bg-navy-deep, selection, scroll-smooth)
src/main.jsx        # createRoot render; PostHog/Sentry init GUARDED by import.meta.env.VITE_* keys
src/App.jsx         # Navbar + Hero + Products + Features + SimulatorCTA + Contact + Footer
src/components/*.jsx
```
Install: `npm install --no-audit --no-fund` (~35s, ~150 packages).
Build: `npm run build` → `dist/`. Chunk >500kB warning is expected (three.js);
gzip ~214kB for the whole app — fine for a demo.

## Debug recipe: silent blank page (root empty, NO console error)
This is the #1 trap. Symptom: page loads, `curl` 200s, script tag present,
`document.getElementById('root')` is empty, and every console hook you
installed sees nothing.

Root cause found: an uncaught exception during module execution / mount —
here `Error creating WebGL context` thrown by `new THREE.WebGLRenderer()`
inside Hero's `useEffect` — crashes the whole React tree. Post-load
`window.addEventListener('error')` hooks MISS it because they're installed
after the module already ran (or run in an isolated world).

The trap that catches it (CDP preload script, runs BEFORE page scripts):
```python
cdp('Page.addScriptToEvaluateOnNewDocument', source='''
window.__errs = [];
window.addEventListener('error', e => window.__errs.push('ERR: ' + e.message + ' @' + (e.filename||'').split('/').pop() + ':' + (e.lineno||0)));
window.addEventListener('unhandledrejection', e => window.__errs.push('REJ: ' + String(e.reason).slice(0,200)));
''')
js("location.reload()")
# then read: js("JSON.stringify(window.__errs)")
```
Critical: re-register per target and reload in the SAME tab — a new tab does
NOT inherit the preload script. This trap also proved React itself worked
(plain React UMD test page rendered fine → isolate bundle vs. harness).

Other checks that led nowhere (don't repeat): console.error override hooks,
window error listeners post-load, `performance.getEntriesByType('resource')`
(only proves the JS downloaded, not executed), manual `import()` of the
bundle (resolves OK because module evaluates — the crash is in the React
commit, not module eval). Go straight to the CDP preload trap.

## WebGL fallback pattern (must-have for any Three.js component)
```jsx
useEffect(() => {
  const mount = mountRef.current
  let renderer = null, raf = 0, clock = null, points = null, ring = null, ring2 = null, geo = null, mat = null
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(mount.clientWidth, mount.clientHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    mount.appendChild(renderer.domElement)
  } catch (e) {
    console.warn('WebGL unavailable, falling back to static hero:', e.message)
    return   // graceful — app must NOT crash
  }
  // ... build scene with geo/mat/etc ASSIGNED to outer lets (no const re-declare)
  return () => {
    cancelAnimationFrame(raf)
    window.removeEventListener('resize', onResize)
    if (renderer) { renderer.dispose(); geo?.dispose(); mat?.dispose(); if (renderer.domElement.parentNode) mount.removeChild(renderer.domElement) }
  }
}, [])
```
Pitfalls hit while refactoring to this:
- Hoist ALL `const` scene objects to outer `let` BEFORE the try — if you
  declare `const geo` inside the body while `let geo` is in scope, esbuild
  fails: `The symbol "geo" has already been declared` (7 errors, one per
  symbol). Rename inline consts (`const geo2 = ...; geo = geo2`) or drop the
  inner const.
- Cleanup must guard on `if (renderer)` — after the early return, `geo`/
  `mat`/`renderer` are null and unguarded `.dispose()` throws.
- The `ref={ref}` MUST be on the actual `<section>` the effect queries —
  a missing `ref` prop while the effect calls `ref.current.querySelectorAll`
  throws `Cannot read properties of null` and blanks the page the same way.

## Deploy (Cloudflare Pages, new project)
```bash
npx wrangler pages project create avvs-expert-pro --production-branch master  # WITHOUT --production-branch it silently fails
npx wrangler pages deploy dist --project-name avvs-expert-pro --branch master
curl -sL https://avvs-expert-pro.pages.dev/ | grep -c "assets/index"   # verify live
```
Then browser-verify live: zero errors, sections rendered, screenshot for the
user. Git: `git init -q; git add -A; git -c user.name=Amz34 -c user.email=... commit -q -m "..."`.

## Reuse for other clients
Swap `tailwind.config.js` colors + copy in components + brand name in
index.html → any client gets a pazi.ai-class landing in ~1 session. The
SimulatorCTA section can embed/link the client's existing interactive
artifact (AVVS linked its live canvas simulator).

## Sticky scroll-stack pitfalls (GSAP ScrollTrigger) — "gaps + text blurred on scroll-up"

Symptom (user, phone photos): "gaps between sections; when scrolling up, text
on that section is blurred and unreadable." Verified + fixed on estelar-demo
v3, 2026-09-02 (dark-luxury EN/AR real-estate demo).

Root-cause chain — check in this order:
1. **Sticky tracks too tall**: 300vh per card in a 3-card stack = giant
   near-empty scroll region. A pinned card inside such a track leaves the
   viewport mostly empty for a full screen-height of scrolling → screenshots
   mid-scroll read as "gaps" (pinned card + dark void above/below).
2. **Text reveal scrubbed over a narrow window** (opacity 0.42→0.9 of track
   progress): while pinned, text is invisible/partial for most of the track
   → unreadable.
3. **Reverse stagger on scroll-up**: reveal animations reverse-stagger so
   text lingers at ghost opacity (0.4–0.6) and re-blurs as you scroll back
   → the "blurred when scrolling up" complaint is a ghosted opacity state,
   NOT CSS blur.

Truth-tests (do NOT call pixel darkness a "gap" — dark dusk imagery is real
content; see references/text-only-visual-qa.md):
- DOM gap test: during the scroll, count element-free viewport rows — real
  gaps = viewport slices with NO intersecting element, not dark pixels.
- Computed opacity at rest AND mid-track (ghost = <1.0 while visible).

Fix parameters (validated live):
- Tracks: 300vh → `h-[175vh]` (mobile) / `lg:h-[240vh]` (desktop). Section
  total height dropped 8,315px → 5,150px at 844px viewport (−38%).
- Reveal: start EARLY (progress ~0.06) and HOLD (complete by ~0.16) so text
  is fully legible for most of the track — never scrub 0.42→0.9.
- Stagger 0.06–0.16 (tight); zoom scale [0.86, 1.08] (subtle, no full-bleed).
- After fix: opacity 1.0 at rest, element-free viewport rows = 0.

General rule: sticky-scrub wow needs SHORT tracks + early-and-held reveals.
The longer the invisible pinned phase, the more "gap"/"blur" complaints you
will get from real users.
