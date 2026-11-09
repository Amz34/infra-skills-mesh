#!/usr/bin/env python3
"""WebSocket handshake probe through a TLS proxy (Cloudflare quick tunnel, etc.).

Why: curl gives FALSE NEGATIVES for WS endpoints behind CF edge (plain HTTP
404/200 even when WS works for real browsers). This does what a browser does:
raw TCP + TLS + HTTP/1.1 Upgrade headers. Expect 101 Switching Protocols.

Usage: ws_probe.py <host> [path] [port]
  host  = tunnel hostname, e.g. economy-peas-saint-brand.trycloudflare.com
  path  = WS endpoint path, default "/"
  port  = default 443
Exit 0 on 101, 1 otherwise.
"""
import socket, ssl, sys, base64, os

host = sys.argv[1]
path = sys.argv[2] if len(sys.argv) > 2 else "/"
port = int(sys.argv[3]) if len(sys.argv) > 3 else 443

key = base64.b64encode(os.urandom(16)).decode()
ctx = ssl.create_default_context()
raw = socket.create_connection((host, port), timeout=15)
s = ctx.wrap_socket(raw, server_hostname=host)
req = (f"GET {path} HTTP/1.1\r\nHost: {host}\r\n"
       "Upgrade: websocket\r\nConnection: Upgrade\r\n"
       f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
s.send(req.encode())
resp = s.recv(4096).decode(errors="replace")
status = resp.split("\r\n")[0]
print(status)
print("WEBSOCKET OK" if "101" in status else "WS FAILED")
s.close()
sys.exit(0 if "101" in status else 1)
