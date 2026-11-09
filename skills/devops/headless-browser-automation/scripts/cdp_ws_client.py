#!/usr/bin/env python3
"""Minimal raw-CDP WebSocket client for driving an already-running headless Chrome.

Use when browser_exec can't attach (custom-port Chrome): GET /json/list ->
webSocketDebuggerUrl, then send CDP commands. Stdlib only.

Target Chrome must run with --remote-debugging-port=<port> and
--remote-allow-origins=* (Chrome 136+).

Usage:
    python3 cdp_ws_client.py [port] [js-expression]
    # e.g. python3 cdp_ws_client.py 9242 "document.body.innerText.slice(0,8000)"
"""
import base64, json, os, socket, struct, time, urllib.request


def find_page_ws(port=9242, url_fragment=None):
    tabs = json.load(urllib.request.urlopen(f"http://localhost:{port}/json/list"))
    for t in tabs:
        if t["type"] == "page" and (url_fragment is None or url_fragment in t["url"]):
            return t["webSocketDebuggerUrl"]
    raise RuntimeError(f"no page tab on port {port}")


class CDP:
    """Minimal CDP-over-WebSocket client (stdlib only).

    Frame-parsing gotchas handled here (each one caused a real stall/timeout):
    - client->server frames are MASKED (4-byte mask); mask must be XORed off
    - extended length codes: 126 -> 16-bit length, 127 -> 64-bit length
    - payloads arrive in chunks -> buffer and reassemble
    - server PING frames (opcode 0x9) MUST be answered with a PONG (0x8A)
      or the connection stalls mid-message (classic silent timeout)
    - close frame (0x8) -> connection over
    """

    def __init__(self, url):
        host_port, path = url.split("://")[1].split("/", 1)
        host, port = host_port.split(":")
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock = socket.create_connection((host, int(port)), timeout=60)
        req = (f"GET /{path} HTTP/1.1\r\nHost: {host_port}\r\nUpgrade: websocket\r\n"
               f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
               f"Sec-WebSocket-Version: 13\r\n\r\n")
        self.sock.sendall(req.encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            resp += self.sock.recv(4096)
        assert b"101" in resp.split(b"\r\n")[0], resp[:300]
        self.buf = b""
        self._id = 0

    def send(self, obj):
        payload = json.dumps(obj).encode()
        mask = os.urandom(4)
        n = len(payload)
        hdr = bytearray([0x81])  # FIN + text opcode
        if n < 126:
            hdr.append(0x80 | n)
        elif n < 65536:
            hdr.append(0x80 | 126)
            hdr += struct.pack(">H", n)
        else:
            hdr.append(0x80 | 127)
            hdr += struct.pack(">Q", n)
        self.sock.sendall(bytes(hdr) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def _read_frame(self):
        while len(self.buf) < 2:
            self.buf += self.sock.recv(65536)
        b1, b2 = self.buf[0], self.buf[1]
        opcode = b1 & 0x0F
        n = b2 & 0x7F
        off = 2
        if n == 126:
            while len(self.buf) < 4:
                self.buf += self.sock.recv(65536)
            n = struct.unpack(">H", self.buf[2:4])[0]
            off = 4
        elif n == 127:
            while len(self.buf) < 10:
                self.buf += self.sock.recv(65536)
            n = struct.unpack(">Q", self.buf[2:10])[0]
            off = 10
        masked = b2 & 0x80
        mask = b""
        if masked:
            while len(self.buf) < off + 4:
                self.buf += self.sock.recv(65536)
            mask = self.buf[off:off + 4]
            off += 4
        while len(self.buf) < off + n:
            self.buf += self.sock.recv(65536)
        payload = self.buf[off:off + n]
        self.buf = self.buf[off + n:]
        if masked:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        return opcode, payload

    def recv(self, timeout=60):
        self.sock.settimeout(timeout)
        frames = []
        while True:
            op, payload = self._read_frame()
            if op == 0x1:  # text message (may be fragmented across frames)
                frames.append(payload)
                return json.loads(b"".join(frames).decode("utf-8", "replace"))
            if op == 0x9:  # ping -> MUST pong or the connection stalls
                self.sock.sendall(bytes([0x8A, 0x80]) + os.urandom(4))
            if op == 0x8:  # close
                return None

    def call(self, method, params=None, timeout=60):
        self._id += 1
        self.send({"id": self._id, "method": method, "params": params or {}})
        while True:
            m = self.recv(timeout)
            if m is None:
                raise RuntimeError("ws closed")
            if m.get("id") == self._id:
                return m

    def evaluate(self, expr, timeout=60):
        r = self.call("Runtime.evaluate",
                      {"expression": expr, "returnByValue": True}, timeout=timeout)
        return r.get("result", {}).get("result", {}).get("value")


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9242
    expr = sys.argv[2] if len(sys.argv) > 2 else "document.title"
    cdp = CDP(find_page_ws(port))
    cdp.call("Runtime.enable")
    val = cdp.evaluate(expr)
    print(val if val is not None else "NO RESULT")
