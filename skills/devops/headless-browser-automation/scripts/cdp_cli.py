#!/usr/bin/env python3
"""Reusable raw-CDP CLI for an ALREADY-RUNNING Chrome (any debug port).

Run with an interpreter that has `websockets`, e.g.
    /home/ubuntu/.venvs/gws/bin/python cdp_cli.py 9223 tabs

Commands (sel = substring of the tab's URL, or a numeric index from `tabs`):
    cdp_cli.py <port> tabs
    cdp_cli.py <port> text  <sel>                  # document.body.innerText
    cdp_cli.py <port> js    <sel> "<js-expr>"      # Runtime.evaluate, returnByValue
    cdp_cli.py <port> click <sel> "<js-finder>"    # real Input.dispatchMouseEvent at rect centre
    cdp_cli.py <port> type  <sel> "<text>"         # Input.insertText (use native-setter JS for React fields)
    cdp_cli.py <port> nav   <sel> <url>
    cdp_cli.py <port> key   <sel> "Enter"          # single key via Input.dispatchKeyEvent

Why this exists: when Chrome is already up on a debug port that the browser_exec
harness is not attached to, driving it over raw CDP (real input events + innerText
reads) is the reliable path — no OCR, no screenshot pipeline, no per-task driver.

Notes / gotchas:
- Use `with connect(...)` as a context manager (plain connect() warns/fails on new
  websockets releases).
- A click on a Google/React security control must be a REAL dispatchMouseEvent
  (synthetic .click() is often ignored); pass the element via a JS finder expression.
- Tab creation uses PUT /json/new (POST → 405). Prefer attaching to an existing tab.
- Results are printed to stdout; if your shell output looks compacted, redirect to a
  file ("> /tmp/out.txt") and read the file back.
"""
import base64
import json
import sys
import time
import urllib.parse as up
import urllib.request

from websockets.sync.client import connect


def http_json(port, path):
    return json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=20))


def tabs(port):
    return [t for t in http_json(port, "/json/list") if t.get("type") == "page"]


def pick(port, sel):
    tl = tabs(port)
    try:
        return tl[int(sel)]
    except (ValueError, IndexError):
        for t in tl:
            if sel and sel in t.get("url", ""):
                return t
        raise SystemExit(f"no tab matching {sel!r}; try `tabs` first")


def new_tab(port, url):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/json/new?{up.urlencode({'url': url})}", method="PUT")
    return json.load(urllib.request.urlopen(req, timeout=30))


class Tab:
    def __init__(self, ws_url):
        self.ws_url, self._id = ws_url, 0

    def call(self, method, **params):
        self._id += 1
        with connect(self.ws_url, max_size=None, open_timeout=30) as ws:
            ws.send(json.dumps({"id": self._id, "method": method, "params": params}))
            deadline = time.time() + 60
            while time.time() < deadline:
                msg = json.loads(ws.recv())
                if msg.get("id") == self._id:
                    if "error" in msg:
                        raise SystemExit(f"CDP error: {msg['error']}")
                    return msg.get("result", {})
        raise SystemExit(f"timeout waiting for {method}")

    def js(self, expr):
        res = self.call("Runtime.evaluate", expression=expr, returnByValue=True,
                        awaitPromise=True)
        return res.get("result", {}).get("value")

    def rect(self, finder):
        expr = (f"(() => {{ const e = {finder}; if (!e) return 'null'; "
                "const r = e.getBoundingClientRect(); "
                "return JSON.stringify({x: r.x + r.width / 2, y: r.y + r.height / 2}); })()")
        return json.loads(self.js(expr) or "null")

    def click(self, finder):
        r = self.rect(finder)
        if not r:
            raise SystemExit("click target not found")
        for kind in ("mousePressed", "mouseReleased"):
            self.call("Input.dispatchMouseEvent", type=kind, x=r["x"], y=r["y"],
                      button="left", clickCount=1)

    def type_text(self, text):
        self.call("Input.insertText", text=text)

    def key(self, name):
        self.call("Input.dispatchKeyEvent", type="keyDown", key=name,
                  code=name, windowsVirtualKeyCode=13 if name == "Enter" else 0)
        self.call("Input.dispatchKeyEvent", type="keyUp", key=name,
                  code=name, windowsVirtualKeyCode=13 if name == "Enter" else 0)

    def nav(self, url):
        self.call("Page.navigate", url=url)
        time.sleep(4)


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        raise SystemExit(__doc__)
    port, cmd = a[0], a[1]
    if cmd == "tabs":
        for i, t in enumerate(tabs(port)):
            print(i, t.get("url"))
        return
    sel = a[2]
    t = Tab(pick(port, sel)["webSocketDebuggerUrl"])
    if cmd == "text":
        print((t.js("document.body.innerText") or "")[:20000])
    elif cmd == "js":
        print(t.js(" ".join(a[3:])))
    elif cmd == "click":
        t.click(" ".join(a[3:]))
        print("clicked")
    elif cmd == "type":
        t.type_text(" ".join(a[3:]))
        print("typed")
    elif cmd == "key":
        t.key(a[3])
        print("key sent")
    elif cmd == "shot":
        r = t.call("Page.captureScreenshot", format="png")
        with open(a[3], "wb") as fh:
            fh.write(base64.b64decode(r["data"]))
        print("saved", a[3], len(r["data"]))
    elif cmd == "nav":
        t.nav(a[3])
        print(t.js("location.href"))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
