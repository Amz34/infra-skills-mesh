# WebGL E2E QA on a headless VM — local Chrome + raw CDP (proven 2026-09-07)

Context that produced this: Open Anatomy (`open-anatomy.pages.dev`), a
Three.js bilingual 3D atlas with a new 3-layer build (Knowledge cards, Quiz
MCQ engine, `?embed=1` white-label mode). Every `browser_exec` attempt failed
with "app JS never loads data"; root cause was the remote harness Chrome
having NO WebGL (`gl2:false, gl1:false`) plus serving a stale file copy.
Valid QA = local Chrome with SwiftShader driven over raw CDP.

## 1. Launch the QA browser (one-time, background)

```bash
google-chrome --headless=new --no-sandbox --disable-gpu-sandbox \
  --use-angle=swiftshader --enable-unsafe-swiftshader \
  --remote-debugging-port=9223 --user-data-dir=/tmp/chrome-qa \
  --window-size=1400,900 about:blank
# log to /tmp/chrome-qa.log; verify:
curl -s http://127.0.0.1:9223/json/version   # -> {"Browser":"Chrome/152..."}
```
- `--enable-unsafe-swiftshader` mandatory (else software WebGL refused).
- Fresh `--user-data-dir` per project keeps profiles clean.
- Works headless on an Oracle/VPS VM with no GPU; renders via SwiftShader.

## 2. CDP driver skeleton (Python, `websockets` package)

```python
import asyncio, json, urllib.request, websockets

def targets():  # page tabs
    return json.load(urllib.request.urlopen('http://127.0.0.1:9223/json/list'))

async def evals(ws_url, expr, await_promise=True):
    async with websockets.connect(ws_url, max_size=2**28) as ws:
        await ws.send(json.dumps({'id':1,'method':'Runtime.enable'}))
        exceptions = []
        while True:  # drain pre-existing events (non-blocking)
            try: msg = json.loads(await asyncio.wait_for(ws.recv(), 0.05))
            except asyncio.TimeoutError: break
            if msg.get('method') == 'Runtime.exceptionThrown': exceptions.append(msg)
        await ws.send(json.dumps({'id':2,'method':'Runtime.evaluate',
            'params':{'expression':expr,'returnByValue':True,'awaitPromise':await_promise}}))
        while True:
            msg = json.loads(await ws.recv())
            if msg.get('id') == 2: return msg['result']['result'].get('value'), exceptions
```
- `awaitPromise:true` lets you evaluate async IIFEs for multi-step flows.
- Keep a running exception list per phase → "N console exceptions" evidence.
- Screenshot: `Page.captureScreenshot` `{format:'png'}` → base64-decode →
  save with distinct names (`qa-quiz.png`, `qa-embed.png`…) and sanity-check
  the `\x89PNG` magic bytes (empty/garbage captures happen on crashed tabs).

## 3. Wait discipline (3D apps are SLOW to init)

Module scripts + model fetch + WebGL compile take 5–15 s. Poll for a DOM
predicate instead of fixed sleeps:

```js
(async () => { const t0 = Date.now();
  while (!document.querySelector('#organList')?.children.length && Date.now()-t0 < 20000)
    await new Promise(r => setTimeout(r, 250));
  return { rows: document.querySelectorAll('#organList > *').length,
           canvas: !!document.querySelector('canvas') }; })()
```
Quiz flows: after each click, wait for the NEXT question's DOM marker before
asserting — rapid-fire evaluate returns the previous step's state.

## 4. Probe/assertion list that worked (reuse per app)

- Rows loaded: `#organList` children count (expected e.g. 1,460 structures).
- WebGL presence: canvas context probe + `gl.getParameter(gl.RENDERER)`.
- Quiz: open button → 8 questions × (click an option → feedback visible →
  advance) → final score text (`"1/8 (13%)"`) → Play again resets.
- AR/RTL labels: assert the rendered Arabic strings and `dir=rtl` attribute
  exactly as the UI shows them (`اختبار`, `١ من ٨`).
- Embed mode (`?embed=1`): assert chrome elements `display:none`/absent
  (topbar, side panels, footer) and canvas full-width.
- Overlay auto-dismiss: poll the overlay style after body-load event — verify
  it disappears on its own (long-wait check), don't just trust the code path.
- Zero console exceptions: `Runtime.exceptionThrown` event list empty across
  the whole phase.

## 5. Pitfalls

- `canvas.getContext('webgl2')` returns null if the app already took the
  context as `webgl` — the boolean probe is decisive only when run in a fresh
  tab or when checking `gl1 || gl2`; prefer driving the app and checking its
  own canvas/render state plus pixel content.
- `browser_exec` harness Chrome: remote daemon, possibly stale files, NO
  WebGL, stdout truncated mid-string. Never use it to QA a WebGL app or to
  prove "green" — it structurally cannot run the app.
- Record WHICH origin each driver tested: grep the `SITE =` constant in each
  `qa-drive*.py` before quoting results; a pass against `:8317` (a stale
  static server) is not evidence for `:8318`'s content. Byte-verify served
  files (`curl | sha256sum` vs disk) once per origin.
- Terminal output of long python drivers can vanish from transcripts — write
  phase results to a log file AND print; read the file back for the report.
- **Reuse KNOWN-GOOD selector strings from past passing drivers verbatim**
  (`#organList`), don't re-guess per script — a wrong-id probe (e.g. `#list`)
  returns 0 rows and looks like a regression until you diff the selectors
  against the actual HTML ids.
- **Learn the flow's state machine before asserting end-states**: in a timed
  mock exam, Finish/Submit is only enabled on the LAST question, so a driver
  that "finishes" early finds an empty results screen — that's a test-design
  error, not an app bug. Assert what the current step offers, then advance.

## 6. Post-deploy: point the SAME driver at the LIVE origin

After a preview/prod deploy, run the full driver against the real CDN URL
(`https://<name>.pages.dev/` or `https://preview-<branch>.<name>.pages.dev/`)
instead of a localhost server — same local Chrome + CDP code, swap the URL
constant. Proven: the full bilingual exam flow (open → answer 10 → results
with topic breakdown → review cards → CSV button) ran green against the live
CF Pages origin after prod push. This beats curl-only checks because it
exercises the served bytes + service worker + real network as a user sees
them, and it catches alias-propagation lag (the deployment preview URL
serves new content instantly while the alias may lag ~1 min).
Caveats: first load hits cache-miss latency — poll `#organList` children
with the 20 s budget instead of a fixed sleep; if the tab previously loaded
the same origin, clear caches first (`Network.clearBrowserCache` +
`Network.setCacheDisabled` for the nav) so the SW/HTTP cache can't mask a
stale build.
