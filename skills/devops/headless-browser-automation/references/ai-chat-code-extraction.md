# z.ai (GLM) 3D-website generation & code extraction — session-verified recipe (2026-08)

User's trigger: a LinkedIn post showed GLM 5.3 building a 3D biking site for $0.14 vs
$2.21 for Anthropic's Fable 5. User: "Ye kaam ki cheez hai: Khud GLM 5.3?" — so we
drove z.ai headless to reproduce it. Everything below worked on the Ubuntu headless
VM via browser_exec (BU_CDP_URL custom-profile Chrome, Xvfb :99).

## Access facts
- `https://z.ai` chat works **without login** on the free tier. Title said "GLM-5.2";
  the post referenced 5.3 — treat the model name as whatever the site serves.
- Page offers template cards ("Prompt" / "Preview" pairs, incl. "3D Modeling").
  Clicking a card fills its starter prompt; we used our own prompt instead.
- Result: complete single-file site ("VELO | Precision Carbon Bicycles", 51.5 KB,
  1045 lines, 109 `THREE.` refs) from a one-line prompt. GLM really does produce
  finished, deployable HTML.

## Send a prompt (React textarea)
`fill_input('textarea', ...)` and plain `.value=` did NOT register (React state).
Working sequence:
```js
const ta = document.querySelector('textarea');
ta.focus();
const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
setter.call(ta, promptText);
ta.dispatchEvent(new Event('input', {bubbles: true}));
```
Then click the real send button — on z.ai it's `document.querySelector('.sendMessageButton')`
(or `button` index 18). Enter-key KeyboardEvent dispatch did NOT send reliably.
Confirm send by textarea length dropping to 0 and the message appearing in body text.

## Wait for streamed generation
The model streams the file into a CodeMirror editor over a LONG time (~2-4 min).
Doc length grows monotonically: observed 14,378 → 23,763 → 51,200 chars. Poll:
```js
const view = document.querySelector('.cm-content').cmView.view;
const doc = view.state.doc.toString();
// HTML: done when doc.includes('</html>')
```
Extracting before the completion marker yields truncated HTML (no `</html>`, no THREE
imports). Do NOT try to sweep `.cm-line` elements by scrolling — CodeMirror
virtualizes; you only ever get visible lines (~37 lines / 1.5K chars of a 51K doc).

## Save & test the result
- Save via browser_exec writing the returned doc to a workspace file, then copy to
  `~/projects/<name>/index.html`. Verify with `grep -c "</html>"` and `grep -c "THREE\."`.
- **ES modules + importmap → `file://` blocks the module scripts (CORS).** Serve:
  ```bash
  cd ~/projects/<name> && python3 -m http.server 8777   # background
  ```
  Then load `http://localhost:8777/index.html` in browser_exec.
- The landing layout renders fine without WebGL, but the canvas never appears if the
  test browser lacks WebGL. Check first:
  ```js
  const c = document.createElement('canvas');
  !!c.getContext('webgl2') || !!c.getContext('webgl');   // false on this headless VM
  ```
  When WebGL is absent, "canvas missing" is an environment artifact, NOT a code bug —
  verify imports (`import('three')` resolves, `typeof m.Scene === 'function'`) and
  syntax (`node --check`) instead, then hand off to the user's real browser.
- Cost sanity: one such generation ≈ $0.14 at GLM pricing. Local whisper/XTTS
  pipeline remains free; only LLM API calls cost.

## Reuse notes
- The saved file is a template for "client wants a 3D site" asks: generate via GLM
  prompt, extract with the CodeMirror API, serve locally, brand later.
- **GLM demo vs production build (proven 2026-08, AVVS):** when a client brand site
  is requested ("AVVS ka 3D style production site"), do NOT ship the GLM-generated
  page. Use it as concept proof only, then hand-build the production site: same 3D
  concept (Three.js model + particles) but with full brand control — real copy,
  bilingual EN/AR toggle (data-lang + .lang-en/.lang-ar classes, localStorage),
  WhatsApp lead form (form → wa.me with prefilled text), real logo assets, SEO meta.
  GLM's output is demo-grade (placeholder copy, wrong brand); hand-built wins for
  client deliverables. Deploy only after explicit user approval — preview first via
  cloudflared quick tunnel (see cloudflare-quick-tunnel skill).
- Related skill: `popular-web-designs` / `claude-design` for hand-built alternatives;
  this route is for when the user explicitly wants the AI-chat generation workflow.
