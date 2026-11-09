# noVNC / VNC over a Cloudflare quick tunnel (verified 2026-08-26)

End-to-end verified pattern (Oracle ARM VM, Munder Difflin harness): headless Electron app on Xvfb, viewed from ANY device via a plain browser URL — no SSH tunnel, no VNC client on the viewer side, no Termius port forwarding needed.

## Local stack (all bound 127.0.0.1)

- Xvfb virtual display: `Xvfb :99 -screen 0 1440x900x24 -nolisten tcp`
- x11vnc exporter: `x11vnc -display :99 -rfbport 5900 -localhost -rfbauth <passfile> -forever -shared -noxdamage`
- noVNC gateway: `websockify --web=/usr/share/novnc 127.0.0.1:6080 localhost:5900`
- NOTE: x11vnc passwd file is BINARY — read the real password from env/systemd unit, never `cat` the passfile into a guide.

## Tunnel

```bash
cloudflared tunnel --url http://127.0.0.1:6080 --no-autoupdate --logfile /tmp/cf-vnc-tunnel.log
```

User opens `<url>/vnc.html` → noVNC password prompt → VNC password → screen. websockify accepts the WS upgrade on any path (`/websockify` or root), so path is cosmetic.

## Verification — do BOTH (page 200 alone is NOT enough)

1. Page: `curl -s -o /dev/null -w "%{http_code}" <url>/vnc.html` → 200 (retry loop for DNS, 30–120s).
2. WebSocket path: NOT via curl — false negative through CF edge (returns 404/200 plain HTTP even when WS works; see SKILL.md pitfalls). Use the raw-socket probe:
   ```bash
   python3 scripts/ws_probe.py <host> /websockify
   ```
   → expect `HTTP/1.1 101 Switching Protocols` + `WEBSOCKET OK`.

## Persistence (survive VM reboots)

systemd user unit (e.g. `~/.config/systemd/user/munder-vnc-tunnel.service`):

```ini
[Unit]
Description=Cloudflare quick tunnel for noVNC (port 6080)
After=munder-novnc.service
[Service]
ExecStart=/usr/local/bin/cloudflared tunnel --url http://127.0.0.1:6080 --no-autoupdate --logfile /tmp/cf-vnc-tunnel.log
Restart=always
RestartSec=10
[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload && systemctl --user enable --now <unit>
```

URL-recovery helper (~/.hermes/scripts/munder-vnc-url.sh pattern): grep the logfile for `https://[a-z0-9-]+\.trycloudflare\.com` (sort -u | tail -1), print password from env, and `systemctl --user is-active` for all stack units. After any restart the user just asks "URL do" — one command, not a re-setup.

## Security notes

- Quick-tunnel URL is PUBLIC: anyone with it sees the noVNC login page (unauthenticated). The VNC password is the ONLY gate — keep it random, rotate via `vncpasswd <passfile>` + restart munder-vnc.
- Offer basic-auth in front (see `references/basic-auth-static-server.md`) as a second gate if the user wants it.
