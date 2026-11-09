#!/usr/bin/env python3
"""Verify a local web page's DOM in headless Chrome over CDP, text-first.

Why this exists: when the browser helper daemon is unusable for a localhost
target, drive google-chrome DIRECTLY over the DevTools protocol and assert on
evaluated JS instead of on screenshots. Stdlib only (no pip deps, masks its own
frames), so it runs from any interpreter on a headless VM.

Usage:
  python3 cdp_dom_probe.py http://127.0.0.1:8765/ \
      --js "(function(){return JSON.stringify({t:document.title, tabs:[...document.querySelectorAll('nav a')].map(a=>a.textContent)})})()" \
      --expect "Fleet" --expect "Ecosystem" --wait-ms 3000

  # console-error gate (exit 2 when the page logs an error)
  python3 cdp_dom_probe.py http://127.0.0.1:8765/ --js "1+1" --fail-on-console-error

Exit codes: 0 ok | 1 assertion/eval failure | 2 console error | 3 launch/CDP failure.
Stdout is one JSON object: {ws, title, result, console_errors, matches}.

Pitfalls this script encodes (all hit for real):
  * Chrome 111+ REJECTS the DevTools websocket unless the browser was started
    with --remote-allow-origins=*. Without it the handshake fails with a 403 and
    looks like "CDP is broken" rather than "one flag is missing".
  * An stale chrome still holding the debug port makes the new launch look
    broken. Kill by PORT OWNER, not by pattern: `pkill -f "<flag text>"` /
    `pgrep -f` can match the very shell command running them and kill it.
        fuser -k 9333/tcp
        ss -lptnH 'sport = :9333' | grep -o 'pid=[0-9]*'   # then kill that pid
  * Wait for the target to appear in /json/list instead of sleeping blindly;
    --headless=new is still starting up for a second or two after the port opens.
  * Use a throwaway --user-data-dir per run, else a running instance with that
    profile swallows the launch and your flags are ignored.
"""

import argparse
import base64
import json
import os
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from urllib.parse import urlparse

CHROME = os.environ.get("CHROME_BIN", "google-chrome")
PORT = int(os.environ.get("CDP_PORT", "9333"))


def http_json(path, timeout=5):
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=timeout) as r:
        return json.loads(r.read().decode())


def wait_for_target(match_url, deadline_s=30):
    end = time.time() + deadline_s
    last = None
    while time.time() < end:
        try:
            for t in http_json("/json/list"):
                if t.get("type") == "page" and match_url.rstrip("/") in (t.get("url") or ""):
                    return t
        except Exception as e:  # port not open yet
            last = e
        time.sleep(0.4)
    raise RuntimeError(f"no CDP page target for {match_url!r} within {deadline_s}s ({last})")


def ws_connect(ws_url, timeout=20):
    """Minimal RFC6455 client: text frames, masked, len 7/16/64-bit."""
    u = urlparse(ws_url)
    s = socket.create_connection((u.hostname, u.port), timeout=timeout)
    key = base64.b64encode(os.urandom(16)).decode()
    s.sendall(
        f"GET {u.path} HTTP/1.1\r\nHost: {u.hostname}:{u.port}\r\nUpgrade: websocket\r\n"
        f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n"
        f"Origin: http://{u.hostname}:{u.port}\r\n\r\n".encode()
    )
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = s.recv(4096)
        if not chunk:
            raise RuntimeError("CDP handshake: connection closed")
        buf += chunk
    head, rest = buf.split(b"\r\n\r\n", 1)
    status = head.split(b"\r\n", 1)[0].decode(errors="replace")
    if "101" not in status:
        raise RuntimeError(
            f"CDP handshake refused ({status}). Start chrome with --remote-allow-origins=*"
        )
    return s, rest


def ws_send(sock, text):
    payload = text.encode()
    n = len(payload)
    hdr = bytearray([0x81])
    if n < 126:
        hdr.append(0x80 | n)
    elif n < 65536:
        hdr.append(0x80 | 126)
        hdr += struct.pack(">H", n)
    else:
        hdr.append(0x80 | 127)
        hdr += struct.pack(">Q", n)
    mask = os.urandom(4)
    sock.sendall(bytes(hdr) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))


def ws_recv(sock, buf):
    def need(k):
        nonlocal buf
        while len(buf) < k:
            chunk = sock.recv(65536)
            if not chunk:
                raise RuntimeError("CDP socket closed")
            buf += chunk

    while True:
        need(2)
        opcode, ln, idx = buf[0] & 0x0F, buf[1] & 0x7F, 2
        if ln == 126:
            need(4)
            ln = struct.unpack(">H", buf[2:4])[0]
            idx = 4
        elif ln == 127:
            need(10)
            ln = struct.unpack(">Q", buf[2:10])[0]
            idx = 10
        need(idx + ln)
        data, buf = buf[idx:idx + ln], buf[idx + ln:]
        if opcode == 0x8:
            raise RuntimeError("CDP socket closed by browser")
        if opcode in (0x1, 0x2):
            return data.decode(errors="replace"), buf


def call(sock, buf, msg_id, method, params=None, timeout=20):
    sock.settimeout(timeout)
    ws_send(sock, json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    events = []
    while True:
        raw, buf = ws_recv(sock, buf)
        msg = json.loads(raw)
        if msg.get("id") == msg_id:
            if "error" in msg:
                raise RuntimeError(f"{method}: {msg['error']}")
            return msg.get("result", {}), events, buf
        if msg.get("method") in ("Runtime.consoleAPICalled", "Log.entryAdded"):
            events.append(msg)


def fmt_event(ev):
    m = ev["method"]
    p = ev.get("params", {})
    if m == "Runtime.consoleAPICalled":
        bits = [str(a.get("value", a.get("description", ""))) for a in p.get("args", [])]
        return f"console.{p.get('type')}: {' '.join(bits)}"
    e = p.get("entry", {})
    return f"log.{e.get('level')}: {e.get('text')}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--js", default="document.title")
    ap.add_argument("--expect", action="append", default=[],
                    help="substring that must appear in the JSON result (repeatable)")
    ap.add_argument("--reject", action="append", default=[],
                    help="substring that must NOT appear in the JSON result (repeatable)")
    ap.add_argument("--wait-ms", type=int, default=2500)
    ap.add_argument("--fail-on-console-error", action="store_true")
    a = ap.parse_args()

    profile = tempfile.mkdtemp(prefix="cdp-probe-")
    proc = subprocess.Popen(
        [CHROME, "--headless=new", f"--remote-debugging-port={PORT}",
         "--remote-allow-origins=*", f"--user-data-dir={profile}",
         "--no-first-run", "--no-default-browser-check", "--disable-gpu",
         "--window-size=1400,1000", a.url],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        target = wait_for_target(a.url)
        sock, buf = ws_connect(target["webSocketDebuggerUrl"])
        call(sock, buf, 1, "Runtime.enable")
        try:
            call(sock, buf, 2, "Log.enable")
        except RuntimeError:
            pass
        time.sleep(a.wait_ms / 1000)
        res, events, buf = call(sock, buf, 3, "Runtime.evaluate", {
            "expression": a.js, "returnByValue": True, "awaitPromise": True,
            "userGesture": True})
        value = res.get("result", {}).get("value")
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                pass
        text = json.dumps(value, ensure_ascii=False)
        errors = [fmt_event(e) for e in events
                  if fmt_event(e).startswith(("console.error", "log.error"))]
        matches = {e: (e in text) for e in a.expect}
        rejected = {r: (r in text) for r in a.reject}
        print(json.dumps({"ws": target["webSocketDebuggerUrl"], "title": target.get("title"),
                          "result": value, "matches": matches, "unexpected": rejected,
                          "console_errors": errors}, ensure_ascii=False, indent=2))
        if not all(matches.values()) or any(rejected.values()) or res.get("exceptionDetails"):
            return 1
        if a.fail_on_console_error and errors:
            return 2
        return 0
    except Exception as e:
        print(json.dumps({"error": str(e), "port": PORT, "chrome": CHROME}))
        return 3
    finally:
        proc.terminate()


if __name__ == "__main__":
    sys.exit(main())
