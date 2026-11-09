# Open Anatomy (anatomy-explorer-demo) — Pages ops runbook

Interactive 3D anatomy explorer for Aamir's client leverage: brand **Open Anatomy
/ التشريح المفتوح**, mobile-first, free CF Pages, PUBLIC GitHub source,
bilingual EN+AR. Deployed under the MAIN deploy account (project `open-anatomy`).

## Production facts

- URL: `https://open-anatomy.pages.dev` (prod-branch main; deploy from repo root:
  `npx wrangler pages deploy public --project-name open-anatomy`).
- `/index.html` = 308 root-redirect (pages.dev NORMAL — curl `/` for content).
- Repo: `github.com/Amz34/anatomy-explorer-demo` PUBLIC (user-approved so the
  footer "Source on GitHub" link works), homepage field = pages.dev URL.
- Project dir `/home/ubuntu/projects/anatomy-explorer-demo`; `public/` = site.
  Raw material gitignored (`.gitignore`: data/, raw/, glb_raw/, tools/node_modules/)
  → repo stays ~19 MB clean while ~874 MB stays local.

## Deploy + verify loop (do before claiming done)

1. `node --check public/app.js` after JS patches.
2. Dev server: `python3 -m http.server 8317` in project root.
3. browser_exec E2E against dev, then production with a unique query
   (`https://open-anatomy.pages.dev/?t=<uniq>`) to bypass cache.
4. Commit + push (`git push -q origin main`) → `npx wrangler pages deploy public
   --project-name open-anatomy` → curl assets 200 → browser verify → MEDIA shot.

## CACHE-BUST PITFALL (bug history #1)

Every static change (app.js/styles.css/facts.json/body.json) MUST bump query
versions: `?v=YYYYMMDD-N` in index.html asset URLs and `?v=N` for data JSON.
Stale versions served empty facts / old UI. Verify the exact `?v=` URL with curl.

## Deep-link episode — owner wants landing page first (2026-09-07)

Shipped self-initiated `?bone=<id|name>&lang=ar` deep links (URL-sync + boot
auto-jump straight to the bone card, full body hidden). User pushback (x2):
"Link open pe first page ana chahiye — fix karo or previous version kardo".
Root cause was TWO-fold: (1) boot auto-jump skipped the full-body home, (2)
syncUrl wrote `?bone=` into the address bar on every bone tap, so any link
copied mid-session opened straight to a card for recipients. Prod ROOT itself
was fine (first page loaded, 8 chips, 0 errors) — the complaint was always a
`?bone=` URL. Fix (commit `1de560e`, `app.js?v=20260907-3`, 7+/50-): boot
ALWAYS lands on first page — `showBody()` unconditional, DL.boneId branch
deleted; syncUrl writes language only; `?bone` silently ignored at boot; dead
code stripped (normKey/resolveParam/popstate handler). Kept: `?lang=ar` →
Arabic RTL FIRST page (still landing-safe, bilingual share value).
Landing matrix to verify (dev + fresh deployment `?cb=` + alias) after any
change: `root` / `?bone=BP9042` / `?bone=ulna&lang=ar` → ALL three must show
infoCard hidden, `#btnBody.active`, 8 `.chip`s, `window.__errs` empty; AR also
`documentElement.dir === 'rtl'`. Tap a bone row → card opens but address bar
stays clean (`/`); Body button → home. Chips selector pitfall: chips are
`.chip` elements WITHOUT a `#chips` wrapper — `document.querySelectorAll('.chip')`.

## Fact-card overlay UX (user request 2026-09-06)

`#infoCard` absolute overlay blocked OrbitControls rotation. Fix shipped:
✕ close button `#btnCloseInfo` (`.card-close`), click-anywhere-on-fact-block
hide, bilingual hint `.fact-hint` (EN `· tap to hide` / AR `· اضغط للإخفاء`),
re-select shows panel again (remove `.hidden`), hide on mode enter/exit.
Grep first: this app has NO AR mode — only the info overlay needed fixing.

## Mobile attribution — footer signatures on ≤880px (user ask 2026-09-07)

`.footer { display:none }` inside the mobile media query (stage = full-screen)
hid the credit/LinkedIn/GitHub signatures on phones. Fix shipped: mobile-only
`.m-credit` strip — a second row UNDER the topbar, in normal flow (flex,
center, wrap, gap 4px 10px, padding 4px 12px, font-size ~10.5px, `--muted`,
border-bottom), `display:none` on desktop, visible only ≤880px. Zero overlap BY
DESIGN: no absolute positioning, so stage top = strip bottom. Desktop `.footer`
untouched. Verify EN + AR modes; git commit/push may lag the deploy — do both.

## Mobile viewport testing (browser_exec + CDP)

- `window.resize()` is a no-op in headless Chrome; use CDP instead:
  `cdp('Emulation.setDeviceMetricsOverride', width=390, height=844, deviceScaleFactor=3, mobile=True)`.
- PITFALL: metrics do NOT stick if applied BEFORE `new_tab()` — navigation
  replaces the target. Order: navigate → apply override on the same tab →
  reload → verify `window.innerWidth`.
- `js()` strings must be single-line: multiline JS throws "unterminated string
  literal". Compact to one line or `(function(){...})()` without newlines.
- Verify overlap numerically (strip bottom px == stage top px), then screenshot.

## gh visibility quirk (private → public)

`gh repo edit --visibility public` exits 1 on a private repo — add
`--accept-visibility-change-consequences`. Verify: unauthenticated curl on
`https://github.com/OWNER/REPO` + raw README → 200. Cross-link loop: repo
homepage = pages.dev, site footer Source link, README "Live website" section.

## Content pipeline (regenerate via scripts only)

- `public/body.json`: 199 real bones / 7 regions (skull incl. hyoid, spine, rib
  cage, upper limb, hand, lower limb, foot) — `scripts/build_body_full.py`.
- `public/facts.json`: bilingual EN+AR (~213 facts) — `scripts/gen_facts*.py`.
- GLB ≈1.7 MB total (mobile-smooth), Blender-less (obj2gltf + @gltf-transform/cli).
- Benchmark Human Atlas (`human-atlas-seven.vercel.app`, repo `ahemag/human-atlas`):
  12 systems, Skeleton row 1, explode 0–100% slider, default = muscles écorché.
  Our 199-bone skeleton = their Skeleton system; explode-slider parity = optional
  offer only. Muscles/skin NOT in catalog — don't promise.

## CSS patch pitfall (bit us)

Replacing a partial CSS rule body can strand orphan lines (stray property +
extra `}`) when old_string ends mid-rule. Include the FULL rule (selector →
closing brace) in old_string; brace-count/re-grep after.

## Screenshots

`/tmp/anatomy_shots/` — skeleton_199_en.png, full_skeleton_v2.png,
prod_launch.png, fact_hide_prod.png, explode_state, body_mode(-ar).
