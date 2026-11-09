# Mobile viewport verification via Node raw-CDP (no puppeteer) — proven 2026-08-23

Context: verifying a mobile-perfect responsive site (surprise gift-gate overlay,
anniversary site) on a headless Oracle VM. `browser_exec` harness was unavailable
(`fatal: chrome-not-running`), puppeteer/playwright not installed. Node 22+ has
global `WebSocket` + `fetch` — a raw CDP test needs ZERO npm deps.

## The script skeleton

```js
const { spawn } = require("child_process");
const PORT = 9333;
const chrome = spawn("/usr/bin/google-chrome-stable", [
  "--headless=new", "--no-sandbox", "--disable-gpu",
  "--window-size=375,667", `--remote-debugging-port=${PORT}`, "about:blank"
], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  // 1. Find the PAGE target — NOT /json/version (browser-level endpoint)
  let page = null;
  for (let i = 0; i < 30; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      page = list.find((t) => t.type === "page");
      if (page) break;
    } catch { await sleep(300); }
  }
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0; const pending = new Map();
  const send = (method, params = {}) => new Promise((res) => {
    const mid = ++id; pending.set(mid, res);
    ws.send(JSON.stringify({ id: mid, method, params }));
  });
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); }
  };
  await new Promise((r) => ws.onopen = r);
  await send("Page.enable"); await send("Runtime.enable");

  // 2. CRITICAL: force the exact phone viewport BEFORE navigate.
  //    --window-size=375,667 does NOT reliably set it (headless=new gave 500x524).
  await send("Emulation.setDeviceMetricsOverride", {
    width: 390, height: 844, deviceScaleFactor: 3, mobile: true,
    screenWidth: 390, screenHeight: 844
  });
  await send("Page.navigate", { url: "http://localhost:8077/" });
  await sleep(3500);

  const evalJs = async (expr) =>
    (await send("Runtime.evaluate", { expression: expr, returnByValue: true }))?.result?.value;
  // ... assertions, then ws.close(); chrome.kill();
}
```

## The assertions that matter (each one caught real bugs)

- Viewport actually applied: `[window.innerWidth, window.innerHeight]` → expect [390, 844].
- Intended media-query branch active:
  `matchMedia('(max-width: 420px)').matches` → true for small-phone CSS.
- Element fits the phone (gift box fully visible, no clipping):
  `getBoundingClientRect()` top>0 && bottom<innerHeight && left>=0 && right<=innerWidth.
- No horizontal overflow: `document.documentElement.scrollWidth <= innerWidth`.
- Interaction (tap simulation): `element.click()` (bubbles) → assert class changes
  (`.open`/`.done`), element removal from DOM, body scroll-lock released,
  page scrollable after: `document.documentElement.scrollHeight > innerHeight`.

## Visual proof without eyes

CLI screenshot (`--screenshot=/tmp/gate_mobile.png --window-size=390,844`) then PIL
pixel sampling to confirm the intended composition actually rendered:

```python
from PIL import Image
img = Image.open("/tmp/gate_mobile.png").convert("RGB")
w, h = img.size
center = img.crop((w//4, h//3, 3*w//4, 2*h//3))
px = list(center.getdata())
reds   = sum(1 for r,g,b in px if r > 120 and g < 80 and b < 80)    # gift box
golds  = sum(1 for r,g,b in px if r > 160 and g > 120 and b < 110)  # ribbon/bow
darks  = sum(1 for r,g,b in px if r+g+b < 120)                       # background
print(f"red {reds/total:.1%} gold {golds/total:.1%} dark {darks/total:.1%}")
```

A healthy dark-themed gate reads ~13% red + ~7% gold + ~67% dark — confirms the
box, ribbon and bg are all present at the right proportions, no blank render.

## Pitfalls

- `/json/version` gives the BROWSER target — `Runtime.evaluate` on it returns
  `undefined` for everything. Always `/json/list` → pick `type:"page"`.
- If every evalJs result is `undefined`, you attached to the wrong target (see above).
- `--window-size` alone lies; `Emulation.setDeviceMetricsOverride` with
  `mobile:true` is the ground truth for phone layout tests.
- Node `--check` on the main.js catches syntax errors before the CDP run —
  cheap pre-flight.
- Kill the chrome child (`chrome.kill()`) or ports pile up; use a fresh port
  per run (9333, 9334, ...).
