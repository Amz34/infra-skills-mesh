# Generative-UI panel layer — OpenUI Lang (SPIKE BUILT + MEASURED, prod untouched)

STATUS (Sep 2026): the analysis below was **executed as a spike**, not just evaluated. Everything
lives in `~/clients/invertio/infra-dashboard/spike-openui/` (spike server :8799, static +
`/dash/*` proxy to the real :8765). Production `web/index.html`, `server.py`, `collector.py` and
`infra-dash.service` were **not** modified — re-check with `stat` after any spike work.
Verdict stands: **adopt OpenUI Lang + runtime now; keep the OUI-1 model on watchlist; never send
client data through Thesys' free tier.** Re-verify versions/limits before starting (they move).

## Spike results — measured, not claimed

- **Runtime, no build step, no CDN**: vendored `@openuidev/browser-bundle@0.1.1` (prebuilt IIFE,
  ~650KB gzip) + `@openuidev/lang-core@0.2.18` (parser / prompt-gen / validation) into
  `spike-openui/vendor/`. Library exposes **57 components**, root type is `Card`.
- **Reference panels render live data with 0 LLM calls** (`tools 13 | llm 0` in one page load):
  `panels/ref_host_health.oui` (9 statements), `ref_ops_failures.oui` (15), `ref_fleet_filter.oui`
  (11 — dropdown `$var` re-queries `fleet_tasks` on Apply with the model counter still at 0).
  "Generate once, execute forever" is proven on this box: LLM only ever runs at **generation**.
- **Encoding win (same UI, one tokenizer)**: `ref_ops_failures` = **461 openui-lang tokens /
  1,364 chars** vs **1,678 JSON-tree tokens / 6,052 chars → 72.5% saving** (`encode_measure.py`,
  counted with the running model's real tokenizer via Ollama `prompt_eval_count`).
- **Generation**: `qwen2.5:3b` @ ctx 12288 → decode **~3.1–3.4 tok/s**, prefill ~9–15 tok/s on
  2 vCPU. Task-only prompt → the model rambled/repeated to the `num_predict` cap and produced an
  **invalid** program (2 resolvable statements, unresolved refs). With a **few-shot template**
  (a COMPLETE valid panel passed in the prompt) → **valid on attempt 1**: 9 statements, 356 output
  tokens, 193s; the panel it wrote is 982 bytes = **384 openui-lang tokens** (`out/gen-metrics.json`). `qwen2.5:7b-64k` @ 32768 ctx **OOMs** on this 11.9GB box (never loads).
  → Generation belongs off-box (hosted model / GPU); the runtime belongs on-box.

## Pitfalls found (all reproduced, all fixed in the spike)

1. **Thundering herd on the real dashboard.** Four `Query(...)` bindings fired in parallel each hit
   `/data.json` at once → upstream **502** → empty panels. Fix: TTL cache + single-flight coalescing
   in the spike proxy; assert with the `X-Spike-Cache: miss → hit` header. Any real integration needs
   this guard before panels point at an endpoint.
2. **Small local model needs a template.** Raise `num_predict` never fixes it; passing a complete
   valid panel as a template does. Also cap the ask ("at most 22 statements") and cap
   `num_predict` (1100–1400) because CPU decode dominates wall time.
3. **Task-only generation is not a valid slow path — it's a failing path.** Keep it as the negative
   control in `out/gen-metrics.json`, don't ship it.
4. **Verifier must be location-independent**: `SP = os.environ.get("SPIKE_ROOT") or
   os.path.dirname(os.path.abspath(__file__))`, otherwise a copy run from `/tmp` can't find the
   spike. (Cost me one failed verification run.)
5. **Generated UI is still code-shaped output** → the runtime's component allow-list is the sandbox;
   never let a generated spec fetch arbitrary URLs, and validate server-side with the official
   parser before storing.

## Writing the verifiers (no canonical test command exists in this repo)

Both layers are checked by **ad-hoc scripts** — `verify.py` for the spike, plus a throwaway one for
whatever changed in the current turn. They only earn the word "verified" if written defensively:

- **Normalize numbers before comparing doc-cited values.** Docs print `1,364` / `72.5%`, JSON holds
  `1364` / `72.5`. Strip separators on both sides (`re.sub(r"(?<=\d),(?=\d)", "", s)`) or the check
  fails on formatting instead of substance.
- **Never hardcode the check total** (`total = 30`): count dynamically and print
  `len(checks) - len(fails)` of `len(checks)` — a hardcoded total silently mis-reports the moment
  you add a check, and a monkey-patched tail line breaks the script outright.
- **Assert against the artefact's real shape.** `tools.json` is a *list of dicts*; `encoding.json`
  nests panels under `["panels"]`; `measure.json` carries an `interaction` block. Read what the file
  actually returned, don't re-derive it from the earlier prose.
- **Re-parse rather than re-quote.** The preview verifier re-runs `node validate.js panels/<f>.oui`
  and compares the parser's count to the recorded `out/preview-measure.json` (9 / 15 / 11) — recorded
  numbers must stay reproducible from the artefacts themselves.
- **Bytes ≠ characters**: `len(html)` counts characters (multibyte `·`, `—`, emoji in the dashboard)
  while `curl -w '%{size_download}'` counts bytes — 99,444 vs 99,654 for the same file. Compare with
  `os.path.getsize()`.
- **If a verifier run gets called stale, re-run it, don't re-narrate it.** Recreate the same checks
  and execute; re-asserting from memory is exactly what the verification gate is there to catch.

## Files / reproduce + verify

`server.py` (:8799, static + coalesced cached proxy) · `tools.json` (7 tool specs = 7 provider fns) ·
`genprompt.js` (library+tools → system prompt) · `validate.js` (official-parser verdict) ·
`gen.py` (local generation; env `SPIKE_MODEL`/`SPIKE_CTX`/`SPIKE_NUM_PREDICT`) ·
`encode_measure.py` · `report.py` (→ `REPORT.md`, measured values only) · `web/panel.html`
(render harness, `?panels=`, `window.__spike` counters) · `make_preview.py` (prod copy →
`preview/index.html`, the pilot) · `verify.py` (**37/37 ad-hoc checks, exit 0**).

```sh
cd ~/clients/invertio/infra-dashboard/spike-openui
python3 server.py &                                  # :8799
node genprompt.js > prompts/system-prompt.txt        # offline
python3 gen.py host_health_fewshot                   # local gen (slow; few-shot)
python3 encode_measure.py ref_ops_failures           # token cost, both encodings
python3 make_preview.py                              # prod copy + generated region
python3 report.py && python3 verify.py               # REPORT.md + checks
open "http://127.0.0.1:8799/web/panel.html?panels=host_health_fewshot,ref_ops_failures,ref_fleet_filter"
open "http://127.0.0.1:8799/preview/index.html"      # the pilot preview
```

## Pilot preview — embedding into the REAL dashboard without touching prod (BUILT + MEASURED)

`make_preview.py` (idempotent) reads `../web/index.html` **read-only** and writes
`preview/index.html`; the spike server serves it at `http://127.0.0.1:8799/preview/index.html`.
It injects exactly three anchors into the copy:

1. `<head>`: vendored `openui-styles.css` + the region CSS + a **fetch shim** that rewrites the
   dashboard's OWN `/data.json|/history.json|/fleet.json` calls to `/dash/*` (the real dashboard
   sends no CORS headers, so the preview must be same-origin with the proxy).
2. Before `<div id="tilesSec">`: the `Generated panels` section (chips: parse / tool calls / LLM
   calls + re-run button).
3. Before `</body>`: `openui-bundle.min.js` + the mount script (toolProvider bound to the same
   endpoints). Also **comment out the service-worker registration** — a preview must never install
   a SW. Measured live: 3 panels, 3/3 parsed, 7 tool calls, **0 LLM calls**, dashboard's own tiles
   still live, prod mtimes unchanged.

Pitfalls that cost real time here (all now handled in the generator):

- **An undefined tool map dies silently.** Leaving `dash`/`toolProvider` out of the injected script
  throws only *inside* React's render, so React unmounts the tree with **no thrown error, no DOM** —
  the section header renders and the grid stays empty. If the region is blank, do not assume CSS:
  test `createRoot(el).render(<Renderer response=... />)` and watch for a ReferenceError.
- **The library ships a LIGHT theme by default** (its palette is `--openui-*` vars switched by
  `@media (prefers-color-scheme: dark)`). Embedded in a dark dashboard that looks broken. Fix
  without hand-copying colours: regex the dark block out of `vendor/openui-styles.css` and re-emit
  it scoped to the region (`#genSec{...}`) at build time. Portals (dropdowns/modals) mount on
  `document.body`, outside the scope — they stay light.
- **Keep the report reproducible.** Appending the preview section to `REPORT.md` from a separate
  script broke the verifier's reproducibility check (regenerating the report dropped it). Emit it
  from inside `report.py`, fed by `out/preview-measure.json` (values read back out of the live page).
- Panel tables are wider than a 2-column grid cell → they scroll horizontally inside the card. If
  that bothers the pilot, give wide panels `grid-column: span 2`.

**Verified state (Sep 2026)**: preview verifier **21/21 exit 0** (byte-identical idempotent rebuild;
three injections in place; tool-map binding present; shim rewrites `/data.json|/history.json` →
`/dash/*`; dark values taken from the library's own dark block, upstream light value untouched; no
CDN; SW off; prod mtimes older than the spike; `REPORT.md` reproducible + measured-only), spike
verifier **37/37 exit 0**, `curl` on `/preview/index.html` → **HTTP 200**. Screenshot evidence kept
at `out/screenshot-preview-pilot.png` and delivered to Aamir with a `MEDIA:` line — same convention
as the QA loop in `SKILL.md`.

**Reusable pattern beyond this dashboard**: to preview a change to any no-build single-file page,
serve a *copy* generated by a script that reads the original read-only, injects the new layer, and
disables the service worker; prove prod is untouched with `stat -c '%n %y'` on the original files
before and after. Cheap, and it keeps "approval before prod" honest instead of aspirational.

## Next step if green-lit (prod deploy needs Aamir's approval, preview first)

1. Embed the vendored IIFE in the real `index.html` + a `panels` table in `status.db` (panel text =
   data), keep the existing 20s refresh; rollback = one file.
2. Generate off-box (hosted model) → validate with `lang-core` → store; version panels in the repo.
3. Add endpoint coalescing/caching so panel queries can't stampede `/data.json`; then pilot the two
   panels already written here (host health, ops failures) and compare for a week.

## Original analysis (still the why)

- **The cost being attacked**: every panel today = hand-written HTML block + a `draw*()` function
  (card / chip / row / donut / gauge / ribbon), plus collector field + server passthrough + SW cache
  bump. **Panels are code, not data.** Baseline: `infra-dash.service` → `server.py` :8765 +
  single-file `web/index.html` (~78KB vanilla JS, no framework, no build) + `sw.js`; client polls
  `/data.json` every 20s; `collector.py` timer (2 min) → `status.db` (~113MB). Co-resident surfaces
  that would benefit: AI-DS :8001, lead-qualifier :8110, Streamlit :8500/:8000, Open WebUI :3002,
  Telegram bots (text-only today).
- **OpenUI Lang** (`thesysdev/openui`, MIT): line-based DSL an LLM emits; runtime parses + renders
  with a component library; official renderer is React, `lang-core` is framework-agnostic. Load-bearing
  idea: the LLM generates the UI **once**, then `Query("…")` bindings call *our* tools on every
  refresh/filter at **zero LLM calls** — maps 1:1 onto `/data.json`, `/fleet.json`, `/api/*` via a
  `toolProvider` function map (MCP servers also work; sap-odata/sap-b1/ai-memory already run here).
- **Reliability (their doc)**: 92.9% completion, 2 blank screens in 1,104 runs, best pairing 99.5% →
  never assume valid output; keep server-side validate + repair (our errors-as-data, exit-0 pattern).
  Gateway "Autofix" is free-tier 3,000 calls/mo BYO LLM key — but free *models* may train on data →
  **never send client data**.
- **OUI-1 model is a separate question** (26B-A4B block-diffusion): not required for any of this and
  **cannot run on this box** — no GPU, 11.9GB RAM vs 13.3GB smallest community quant, llama.cpp
  block-diffusion support still OPEN, Ollama manifest 404. Details:
  `research/tech-adoption-analysis/references/model-local-runnability-ladder.md`.
