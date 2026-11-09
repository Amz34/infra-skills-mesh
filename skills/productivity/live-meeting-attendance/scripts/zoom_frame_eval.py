#!/usr/bin/env python3
"""Frame-aware CDP eval / click for iframe-rendered web clients (Zoom web client).

A Zoom `/wc/<mn>/join?ref_from=launch&tk=...` page keeps the whole meeting UI inside an
iframe, so top-document queries answer "no buttons / empty list" while the tab title and
URL look perfectly fine. This tool walks the frame tree, picks the DEEPEST frame whose
url matches the given substring, opens an isolated world in it, and evaluates / clicks
there. In-frame `el.click()` DOES work for Join / Show Captions / audio controls.

Needs a python with `websocket-client` (on this VM:
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3).

  frames --tab 89689313605                          # list frames: depth, id, url
  text   --tab 89689313605 [--frame 89689313605]    # that frame's innerText
  js     --tab 89689313605 [--frame SUB] 'document.querySelectorAll("audio").length'
  click  --tab 89689313605 [--frame SUB] '^Join$'   # innerText/aria-label regex -> el.click()

`--frame` defaults to the tab substring. `frames` selections are printed deepest-last so
`pick_frame` (deepest match wins) is easy to eyeball.

Every primitive here (frame tree -> deepest match -> isolated world -> in-frame
evaluate/click) was exercised against a live Zoom web client on 2026-09-17, but this
helper is a condensation of those one-off scripts: run `frames` once against the target
tab to confirm the URL substring/pick before trusting `click`, and read `disabled` from
its JSON result rather than assuming the click landed.
"""
import argparse
import json
import sys
import urllib.request

try:
    import websocket  # websocket-client
except Exception:  # pragma: no cover
    sys.exit("run me with a python that has websocket-client "
             "(e.g. /home/ubuntu/.hermes/hermes-agent/venv/bin/python3)")

CLICK_JS = """(()=>{const p=new RegExp(%s,'i');
const sel='button,a,[role=button],[role=menuitem],div[aria-label],span[aria-label]';
const els=[...document.querySelectorAll(sel)];
const lab=e=>((e.innerText||'')+' '+(e.getAttribute('aria-label')||'')).trim();
const hit=els.find(e=>p.test(lab(e)));
if(!hit)return {ok:false,seen:els.map(lab).filter(Boolean).slice(0,40)};
hit.click();
return {ok:true,matched:lab(hit),disabled:!!hit.disabled,
        cls:(hit.className||'').toString().slice(0,80)};})()"""


class Conn:
    """Minimal synchronous CDP connection (one message in flight at a time)."""

    def __init__(self, url, timeout=25):
        self.ws = websocket.create_connection(url, timeout=timeout)
        self.i = 0

    def send(self, method, **params):
        self.i += 1
        self.ws.send(json.dumps({"id": self.i, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.i:
                if "error" in msg:
                    raise RuntimeError("%s -> %s" % (method, msg["error"].get("message")))
                return msg.get("result", {})

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def list_tabs(port):
    url = "http://127.0.0.1:%d/json/list" % port
    with urllib.request.urlopen(url, timeout=8) as fh:
        return json.loads(fh.read().decode())


def pick_tab(sub, port):
    pages = [t for t in list_tabs(port)
             if t.get("type") == "page" and sub in (t.get("url") or "")]
    if not pages:
        raise SystemExit("no tab matching %r" % sub)
    return pages[0]


def frame_list(c):
    tree = c.send("Page.getFrameTree")["frameTree"]
    out = []

    def walk(node, depth):
        f = node["frame"]
        out.append({"id": f["id"], "url": f.get("url", ""), "depth": depth})
        for child in node.get("childFrames") or []:
            walk(child, depth + 1)

    walk(tree, 0)
    return out


def pick_frame(frames, sub):
    hits = [f for f in frames if sub in f["url"]] or frames
    return sorted(hits, key=lambda f: f["depth"])[-1]


def make_world(c, frame_id, name="zoomz"):
    return c.send("Page.createIsolatedWorld", frameId=frame_id,
                  worldName=name)["executionContextId"]


def evaluate(c, frame_id, expr):
    ctx = make_world(c, frame_id)
    res = c.send("Runtime.evaluate", expression=expr, contextId=ctx,
                 returnByValue=True, awaitPromise=False)
    if "exceptionDetails" in res:
        return {"error": res["exceptionDetails"].get("text", "exception")}
    return res.get("result", {}).get("value")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["frames", "text", "js", "click"])
    ap.add_argument("arg", nargs="?", help="JS expression (js) or regex (click)")
    ap.add_argument("--tab", required=True, help="URL substring of the meeting tab")
    ap.add_argument("--frame", default=None, help="URL substring of the target frame "
                                                 "(default: same as --tab)")
    ap.add_argument("--port", type=int, default=9333)
    ap.add_argument("--chars", type=int, default=4000, help="text: max chars to print")
    a = ap.parse_args()

    tab = pick_tab(a.tab, a.port)
    c = Conn(tab["webSocketDebuggerUrl"])
    try:
        c.send("Page.enable")
        c.send("Runtime.enable")
        frames = frame_list(c)
        if a.cmd == "frames":
            for f in frames:
                print("%d  %-8s %s" % (f["depth"], f["id"][:8], f["url"][:160]))
            print("PICKED %d %s" % (pick_frame(frames, a.frame or a.tab)["depth"],
                                    pick_frame(frames, a.frame or a.tab)["id"][:8]))
            return 0
        fid = pick_frame(frames, a.frame or a.tab)["id"]
        if a.cmd == "text":
            v = evaluate(c, fid, "document.body ? document.body.innerText : ''")
            print((v or "")[:a.chars])
            print("--- len=%s" % len(v or ""))
        elif a.cmd == "js":
            if not a.arg:
                raise SystemExit("js needs an expression")
            print(json.dumps(evaluate(c, fid, a.arg))[:a.chars])
        else:
            if not a.arg:
                raise SystemExit("click needs a regex")
            out = evaluate(c, fid, CLICK_JS % json.dumps(a.arg))
            print(json.dumps(out)[:a.chars])
    finally:
        c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
