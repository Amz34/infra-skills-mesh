# Vanilla Single-File 3D Bilingual Site (Three.js) — proven 2026-08 (AVVS Triatek)

Fast "3D style" client deliverable WITHOUT React/Vite: one `index.html` + `assets/` folder.
Used for AVVS Triatek 3D production site (`~/projects/avvs-3d/`). Good when client wants
"3D style production site" and the build must be cheap, static, and CF-Pages/Netlify-ready.

## Architecture
- **Fixed full-screen `<canvas id="scene">` at z-index 0** + `#vignette` overlay (radial gradient,
  z-1, pointer-events:none) + `.content` wrapper (z-2). Three.js scene is the page background;
  HTML sections scroll over it. No scroll-linked 3D needed.
- **Three.js via importmap** (ES modules — MUST test over http://, `file://` blocks modules):
  ```html
  <script type="importmap">
  {"imports":{"three":"https://unpkg.com/three@0.160.0/build/three.module.js",
  "three/addons/":"https://unpkg.com/three@0.160.0/examples/jsm/"}}
  </script>
  ```
- **Scene recipe that reads "3D" instantly:** venturi-valve-style body (open CylinderGeometry +
  inner throat cone + torus flanges + actuator box) OR any product-shaped primitive stack;
  300-400 additive-blending particles flowing through the throat (loop: advance Y, wrap at ±1.9,
  jitter X/Z); glow torus pulsing opacity; 3-4 floating wire rings rotating on Z; GridHelper floor
  at y=-2.15 with low opacity; fog `FogExp2(bg, 0.028)`. Lights: ambient + 2 colored directionals
  + one point light. Animation: valve slow Y-rotate + mouse-parallax (`valve.rotation.y = t*0.22 +
  mouseX*0.15`), gentle bob `sin(t*0.7)*0.12`.
- **Bilingual EN/AR via `data-lang` attr, NOT separate `ar/` folder** (works when the site is one
  file): every translatable element gets `.lang-en` AND `.lang-ar` classes; CSS shows one set:
  ```css
  html[data-lang="ar"] .lang-en{display:none}
  html[data-lang="en"] .lang-ar{display:none}
  ```
  Toggle button flips `document.documentElement.dataset.lang`, persists in localStorage, `dir="rtl"`
  handled per-element (Arabic copy reads RTL naturally inside its own text). Language switch is
  instant (no page reload) — better UX than the `ar/` folder for single-pagers.
- **Lead form → WhatsApp prefilled message** (zero backend, no Cloudflare Function needed):
  on submit, build `https://wa.me/<number>?text=` + encodeURIComponent of a key:value lead summary
  (name/company/email/phone/facility/message), `window.open`, reset. Same pattern works for the
  floating WhatsApp button. For Telegram-DM leads see `lead-form-telegram.md` instead.
- **Colors:** pull the client's brand hex from the existing site (`grep '#[0-9a-fA-F]{6}'`), use it
  as the accent + glow; dark navy bg (`#050B14`-ish) makes teal/cyan glow pop.

## Verification on headless VM (no display, no GPU)
- Serve: `python3 -m http.server 8778` in the project dir.
- Plain headless/browser-exec Chrome has NO WebGL → canvas never appears. Use the swiftshader
  verification Chrome (see headless-browser-automation skill): launch with `--use-gl=angle
  --use-angle=swiftshader --enable-unsafe-swiftshader --remote-debugging-port=9244
  --remote-allow-origins=* --user-data-dir=/tmp/chrome-test`, then CDP `Page.navigate` →
  `Runtime.evaluate` (`!!document.querySelector('canvas#scene')` + webgl context) →
  `Page.captureScreenshot` → pixel histogram: teal/bright pixel share ~3-5% = scene drew.
- Cheap pixel check (PIL): sample every 3rd pixel; count `g>90 && b>90 && r<90` (teal-ish) and
  `r+g+b>350` (bright). Live glowing scene ≈ 3-4% teal + 4-5% bright on dark bg; blank canvas ≈ 0%.
- Deploy: same CF Pages flow as any static site (see SKILL.md step 3); get approval before deploy.

## Pitfalls
- Canvas element must exist BEFORE the module script runs (script at end of body, canvas in head area).
- `grid.material.transparent = true` needed or grid opacity silently ignored.
- Do not add OrbitControls on a background scene unless you want user interaction — auto-rotate +
  mouse parallax is enough and avoids scroll-jacking.
- Favicon/logo: copy from client's existing site assets; missing favicon shows a horse emoji in
  browser-exec titles (harmless, not in page content).
