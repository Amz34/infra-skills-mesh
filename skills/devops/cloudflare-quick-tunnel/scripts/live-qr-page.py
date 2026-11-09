#!/usr/bin/env python3
"""Live-refreshing QR pairing page — reads a JSON-lines event log produced by a
pairing backend (e.g. baileys/whatsapp-bridge with --pair-json > log), serves the
FRESHEST QR so the phone can be scanned at any time (no 60s expiry race).

Known-good 2026-09 (WhatsApp device re-pair over a cloudflare quick tunnel).
Design rules baked in (each one was a real bug):
  * asset URLs are ABSOLUTE (/<TOKEN>/...) — a page at /<TOKEN> without trailing
    slash resolves relative 'qr' to /qr (root) -> 404 -> UI stuck "Connecting"
  * poll endpoint (/qr) returns JSON ONLY; image endpoint (/qr.png) returns PNG
    ONLY — never one endpoint serving two content types to a r.json() poller
  * QR = device-link grant: keep TOKEN unguessable, kill server+tunnel after pair

Usage: python3 live-qr-page.py <port> <token> [log_file]
Page:  http://127.0.0.1:<port>/<token>     (browser polls every 4s)
  /<token>/qr     -> JSON {"ts": <epoch_ms>} or {"ts": 0} while waiting
  /<token>/qr.png -> PNG of newest QR (cache by ts)
Log lines expected: {"ts": 1788813697109, "event": "qr", "qr": "https://wa.me/..."}
Backend launch pattern: terminal(background=true), command:
  node bridge.js --port <p> --session <dir> --mode bot --pair-only --pair-json > LOG 2>&1
(setsid/nohup wrappers are parser-blocked; the inner redirect is what creates the log.)
"""
import json, os, subprocess, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1])
TOKEN = sys.argv[2]
LOG = sys.argv[3] if len(sys.argv) > 3 else "/tmp/wa-pair.log"
BRIDGE_DIR = "/home/ubuntu/.hermes/hermes-agent/scripts/whatsapp-bridge"  # has node qrcode
CACHE = "/tmp/live-qr-cache"
os.makedirs(CACHE, exist_ok=True)

PAGE_TPL = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WhatsApp Link QR</title>
<style>body{background:#0b141a;color:#e9edef;font-family:system-ui;display:flex;flex-direction:column;align-items:center;padding:20px;margin:0}
h2{color:#00a884;margin:8px 0}img{width:min(92vw,420px);border-radius:12px;background:#fff;padding:10px;display:none}
p{color:#8696a0;font-size:14px;text-align:center}.ok{color:#00a884}.err{color:#ff7b7b}</style></head>
<body><h2>WhatsApp Link QR</h2>
<img id="q" alt="QR">
<p id="s">QR load ho raha hai…</p>
<script>
let last=0;
async function tick(){try{
  const r=await fetch('/__TOKEN__/qr?t='+Date.now()); if(!r.ok) throw 0;
  const j=await r.json();
  if(j.ts && j.ts!==last){last=j.ts; const im=document.getElementById('q');
    im.src='/__TOKEN__/qr.png?ts='+j.ts; im.style.display='block';
    document.getElementById('s').innerHTML='<span class=ok>QR fresh hai</span> &mdash; phone (WhatsApp → Linked Devices → Link a Device) se scan karo';
  } else if(!j.ts){
    document.getElementById('s').textContent='QR generate ho raha hai… 2-3 sec ruko';
  }
}catch(e){document.getElementById('s').innerHTML='<span class=err>Connecting…</span> page refresh karo agar 15s se zyada lage';}
setTimeout(tick,4000);}
tick();
</script></body></html>"""
PAGE = PAGE_TPL.replace("__TOKEN__", TOKEN)


def latest_qr():
    """(qr_string, ts_ms) of newest QR event, or (None, 0)."""
    if not os.path.exists(LOG):
        return None, 0
    try:
        with open(LOG) as f:
            for line in f:
                if '"qr"' not in line:
                    continue
                e = json.loads(line)
                qr, ts = e["qr"], int(e["ts"])
        return qr, ts
    except Exception:
        return None, 0


def render(qr, ts):
    out = os.path.join(CACHE, f"qr-{ts}.png")
    if not os.path.exists(out):
        subprocess.run(["node", "-e",
            "require('qrcode').toFile(process.argv[1], process.argv[2], {width:520,margin:2})",
            out, qr], cwd=BRIDGE_DIR, timeout=30, capture_output=True)
    return out


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == f"/{TOKEN}":
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body); return
        if path == f"/{TOKEN}/qr":
            qr, ts = latest_qr()
            body = json.dumps({"ts": ts if qr else 0}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body); return
        if path == f"/{TOKEN}/qr.png":
            qr, ts = latest_qr()
            if not qr:
                self.send_response(404); self.end_headers(); return
            out = render(qr, ts)
            with open(out, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body); return
        self.send_response(404); self.end_headers()


ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
