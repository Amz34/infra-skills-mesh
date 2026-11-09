---
name: ui-effect-libraries
description: Use when a UI needs beam/orb/gooey/metal/image FX.
version: 1.0.0
author: Hermes Agent, vendoring Jakubantalik/Libraries.dev (MIT)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [ui, effects, react, canvas, webgl, animation, client-work, vendor]
    related_skills: [frontend-design, svg-vector-visuals, client-website-delivery, headless-browser-automation, free-flux-image-api]
---

# UI effect libraries (Jakubantalik/Libraries.dev)

Five small, dependency-light React libraries that give a page *motion* without hand-rolling
WebGL/CSS tricks: glowing borders, "AI thinking" orbs, liquid/gooey navigation, brushed-metal
buttons and shader-driven image reveals. All MIT, all React >= 18, all verified working on this
VM (see §7).

## When to Use

- A page needs a **premium animated effect**: glow border on a card/CTA, "AI thinking" indicator,
  gooey pill nav, metal button, shader image reveal.
- An agent/chat UI needs a **state indicator** (working/searching/solving) → `thinking-orbs`.
- You are asked for "something like the Libraries.dev / Jakub Antalik effects".
- You need the **offline/pinned copy** of these packages (`~/ops/vendor/repos/Libraries.dev`) or the
  repo's LLM-parameter-tuning worker pattern (`services/studio-agent`, §8).
- Not for: static visuals where SVG/CSS suffices (`svg-vector-visuals`), page-level design work
  (`frontend-design`), or fake "AI" flourish on a client site that adds bundle weight for nothing.

## 1. The five libraries

| npm package | effect | reach for it when | tech |
|---|---|---|---|
| `thinking-orbs` | animated dot orb, 9 states | agent/chat "working / searching / solving" indicator | 2D canvas |
| `border-beam` | travelling glow border, 5 size presets | premium card, pricing tile, primary CTA | CSS (no canvas) |
| `liquid-gooey` | gooey morph/move/melt/bend nav | pill nav bar, segmented control, tab switcher | SVG filter |
| `metal-fx` | animated brushed-metal surface | button / circular badge that must feel "hardware premium" | WebGL2 |
| `img-fx` | generative shader backdrop + image reveal cycle | hero visual, product reveal, "generating…" image placeholder | WebGL2 + `three` |

## 2. Install

```bash
npm i border-beam liquid-gooey thinking-orbs metal-fx img-fx
# img-fx also needs:  npm i three
# react/react-dom >= 18 (19 fine)
```

Prefer the registry for `border-beam` **except** when you need the v1.4.0-only presets
(`pulse-outside`, `pulse-inner`, `metal`, `neon`) — npm lags at 1.3.0. Build from the vendored
source instead (`npm i file:~/ops/vendor/repos/Libraries.dev/packages/border-beam`). See §6.

## 3. Verified usage (copy-paste)

```tsx
import { ThinkingOrb } from 'thinking-orbs';
import { BorderBeam } from 'border-beam';
import { Liquid } from 'liquid-gooey';
import { MetalFx, isMetalFxSupported } from 'metal-fx';
import { ImageGeneration } from 'img-fx';

<ThinkingOrb state="searching" size={64} theme="dark" speed={1} />

<BorderBeam size="line" colorVariant="sunset" theme="dark" duration={6} active>
  <button>Get started</button>
</BorderBeam>

<Liquid blur={12} contrast={18} fill="#fff" waviness={0.6}>
  <Liquid.Item x={0}   y={0}><span className="pill">Overview</span></Liquid.Item>
  <Liquid.Item x={96}  y={0} transition="bouncy"><span className="pill">Pricing</span></Liquid.Item>
</Liquid>

{isMetalFxSupported() ? (
  <MetalFx variant="button" preset="chromatic" strength={1} glowGain={1.2}>
    <button>Upgrade to Pro</button>
  </MetalFx>
) : <button>Upgrade to Pro</button>}

<ImageGeneration preset="sweep-gradient" theme="dark" autoReveal images={['/a.jpg']}>
  <div style={{ width: 260, height: 160, borderRadius: 16 }} />
</ImageGeneration>
```

The liquid-gooey children must have **transparent** backgrounds (the gooey body is drawn by the
library); give them borders/radius, not `background: #fff`.

## 4. Props cheat sheet (extracted from the shipped `.d.ts`, not docs)

- **ThinkingOrb** — `state?: 'working'|'searching'|'solving'|'listening'|'connecting'|'weaving'|'composing'|'breathing'|'shaping'` (default `working`), `size?: 64|20` (**only these two tuned presets**), `theme?: 'auto'|'dark'|'light'`, `speed?: number`, `paused?: boolean`.
- **BorderBeam** — `size?: 'sm'|'md'|'line'|'pulse-outside'|'pulse-inner'`, `colorVariant?: 'colorful'|'mono'|'ocean'|'sunset'`, `theme?: 'dark'|'light'|'auto'`, `duration?`, `active?`, `staticColors?`, `borderRadius?`, `brightness?`, `saturation?`. Wraps `children`.
- **Liquid** — `blur`, `contrast`, `fill`, `shadow`, `waviness`, `wavinessFreq`, `filterPadding`, spring knobs (`massStiffness/Damping`, `sizeStiffness/Damping`, `radiusStiffness/Damping`), `roundness`, `corner*`, `anticipation`, `travel`, `stretch`, `tail`, `force`. **Liquid.Item** — `effect?: 'morph'|'move'|'melt'|'bend'`, `x`, `y`, `transition?: 'snappy'|'smooth'|'bouncy' | SpringConfig`, `dissolve?: boolean|number|DissolveOptions`, plus per-effect tuning objects (`morph`, `move`, `bend`, `melt`).
- **MetalFx** — `variant?: 'button'|'circle'`, `preset?: 'chromatic'|'silver'|'gold'`, `theme`, `strength`, `glowGain`, `paused`, `borderRadius`, `normalizeHostStyles`, `disableGlow`, `innerShadow`, `reflectionTargets`. Exports `isMetalFxSupported()`.
- **ImageGeneration** — `preset?: 'pixels-organic'|'pixels-mechanic'|'sweep-gradient'`, `theme`, `strength`, `pixelScale`, `cardBg`, `colors`, `images?: string|string[]`, `autoReveal`, `revealDelayRange`, `revealInitialDelay`, `revealHoldMs`, `revealFadeOutMs`, `borderRadius`, `paused`, `onCycle`. Ref handle: `element` + reveal/hide (`hold: 'auto'|'manual'`); reveal is a **no-op without `images`**.

## 5. Hard rules & pitfalls

1. **WebGL gate**: metal-fx and img-fx need WebGL2. Always branch on `isMetalFxSupported()` and render a plain child as fallback — headless/older clients get the fallback, not a blank box.
2. **`thinking-orbs` sizes are presets, not pixels** — `size={48}` will not give 48 px. Use 64 (avatar) or 20 (inline text).
3. **One GL context per page per library** — metal-fx/img-fx instances are shared/destroyed internally; do not mount dozens of them in a list, and don't unmount/remount in a loop.
4. **liquid-gooey**: transparent item backgrounds; don't combine `dissolve` with your own `mask-image`; `dissolve` only reads on `morph` items (ignored, with a dev warning, under `move`).
5. **Don't screenshot-verify with `browser_exec`** on this VM: its harness expects its own Chrome and fails `chrome-not-running`. Use the local SwiftShader Chrome + raw CDP recipe in §7; the `headless-browser-automation` skill carries the full WebGL QA method (its "WebGL E2E QA" reference).
6. **Snapshots at module scope read zeros** — if you add an evidence hook like `window.__fx`, make it a *function* that queries the DOM on call; a plain object literal is captured before React commits.
7. **Terminal guard**: `vite build` / `vite dev` in a foreground command can be refused as a long-lived server. Run it via `background=true` (or a wrapper script) and poll.
8. **SwiftShader is slow**: shader compile can stall the renderer main thread for a minute on this 2-core VM. After `Page.navigate`, sleep ~12 s and use CDP evaluate timeouts of 240 s before touching the page.
9. **Brand rule**: abstract FX only in client-facing work — no human faces/living beings (memory HARD RULE). These libraries are safely inanimate.
10. **Licensing**: MIT © Jakub Antalik — keep the license/attribution in the delivered repo. `metal-fx` bundles Paper Shaders' liquidMetal (Apache-2.0): ship `packages/metal-fx/NOTICE` with the deliverable.

## 6. Vendored source (offline, pinned)

`~/ops/vendor/repos/Libraries.dev` — shallow clone @ `422180dd7a5ac646c85deedc65500c4a74339127`
(2026-09-10), 44 MB tree. Carries what npm does **not**: the v1.4.0 `border-beam` source, the
iOS/Swift orb ports, and `services/studio-agent` (§8). `PROVENANCE.md` in that directory has the
per-package repo-vs-npm drift table, sha256 of every doc, and the update procedure
(`git fetch --depth 1 && git reset --hard FETCH_HEAD` — plain `git pull` is unsafe on a shallow clone).

Full upstream docs: `references/lib-docs/` (the five READMEs + metal-fx NOTICE).

## 7. Verification (proven green 2026-09-15)

Harness: `~/ops/evals/uifx-libs-verify/` — a Vite/React page mounting all five libraries, plus a
raw-CDP driver that reads back DOM state and per-panel pixels. Its `README.md` documents the file
map; `qa-fx.png` is the rendered proof.

```bash
cd ~/ops/evals/uifx-libs-verify
npm install                 # 76 pkgs, ~50 s
npm run verify              # tsc --noEmit + vite build (needs background=true)
python3 -m http.server 8123 --directory dist &
/opt/google/chrome/chrome --headless=new --no-sandbox --disable-gpu-sandbox \
  --use-angle=swiftshader --enable-unsafe-swiftshader --remote-debugging-port=9223 \
  --user-data-dir=/tmp/chrome-uifx --window-size=1500,1150 about:blank &
npm run qa                  # -> qa-report.json + qa-fx.png
```

Results on this VM: `tsc --noEmit` clean; bundle 909 kB (250 kB gzip incl. `three` + React);
render → **14 canvases, `webgl2: true`, `isMetalFxSupported(): true`, orbs 6 / beam wrappers 3 /
gooey SVG present / metal 4 / img-fx 4, 0 uncaught exceptions**. Every panel's screenshot crop is
non-uniform (grayscale stddev 0.037–0.388, 161–2370 distinct colours per panel) → pixels genuinely
drawn, not blank boxes. Installed: thinking-orbs 0.3.1, border-beam 1.3.0 (npm), liquid-gooey 0.2.1,
metal-fx 2.0.10, img-fx 0.5.1, three 0.180.0, React 18.

Re-run this after any library bump, before quoting §4 props to a client.

## 8. Bonus asset: `services/studio-agent` (LLM-tuned UI parameters)

Not on npm, and the most reusable *pattern* in the repo: a Cloudflare Worker that takes a natural
language request ("make it gold and calmer"), calls an LLM, and returns validated component props.
Structure worth copying: a JSON-schema parameter spec (`spec.ts`) is the single source of truth →
the same spec drives the LLM system prompt, response validation, and the preview controls the user
sees (`sites/home/src/studio/`). Reference: `~/ops/vendor/repos/Libraries.dev/services/studio-agent/`
(`README.md`, `spec.ts`, `handler.ts`); upstream README copied to
`references/lib-docs/studio-agent-upstream-readme.md`.

Use it when a client asks for "let me describe the change in words" parameter tuning on a
generated UI — pairs with `free-claude-code` / provider keys already on this VM.

## 9. Complements

`frontend-design` (page-level design), `svg-vector-visuals` (no-GL visuals), `client-website-delivery`
(intake → deploy), `free-flux-image-api` (content imagery the img-fx shader can reveal),
`headless-browser-automation` (the CDP QA recipe).
