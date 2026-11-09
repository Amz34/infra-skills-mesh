---
name: vm-infra-map
description: Use when asked what infra/agents/services are connected or running on this Oracle VM. Gives the real inventory and the exact check commands.
version: 1.0.0
author: Hermes (agent)
license: MIT
metadata:
  hermes:
    tags: [infra, ops, gateway, mcp, ports]
---

# This VM's infrastructure (hermes-vnic, Oracle free tier)

Answer infra questions from live state — never from the `manage_connections`
registry. That registry is for *hosted connector* authorization and is empty by
design; it does NOT describe this machine.

## Hermes surfaces (all tailnet-only over TLS)

| Surface | Local | Tailnet URL |
|---|---|---|
| Hermes Account dashboard | 127.0.0.1:9120 | https://hermes-vnic.tail34b7f2.ts.net:9443/ |
| Hermes Chat (WebUI) | 127.0.0.1:8788 | https://hermes-vnic.tail34b7f2.ts.net:9445/ |
| Infra Dash (Invertio app) | 127.0.0.1:8765 | https://hermes-vnic.tail34b7f2.ts.net:9446/ |
| Headless desktop backend | 127.0.0.1:9119 | — (no SPA) |

## Gateways (systemd --user)

`hermes-gateway.service` (default profile) plus per-profile units:
`-avvs -az1trade -azwork -indaz -invertio -ksaaz -luxewave -ops -whatsapp`.
Check: `systemctl --user list-units 'hermes-*' --no-pager`

## Other services

- `signal-cli-daemon.service` → 8091 (Signal bridge)
- `hermes-serve.service` → 9119
- `caveman-proxy` → 8787 (`~/.caveman/bin/`)
- `ttyd` → 7681 under https://…ts.net/term
- `invertio-hub.service` → 8130 (MCP hub, behind Funnel 8443)
- Fire & Smoke Watch → 8512 (behind Funnel 10000)
- `hermes-dashboard`, `hermes-dashboard-infra`, `hermes-webui`, `hermes-webui-revwatch.timer`

## MCP servers (tools the agent actually gets)

`hermes mcp list` →
ai-memory (`127.0.0.1:49374/mcp`), sap-odata (8791), sap-b1 (8793),
latex (8795), rag (8797); ImagineArt disabled (stdio).

## Ports exposed publicly (Funnel — treat as internet-facing)

8443 → 8130, 10000 → 8512. Everything else is tailnet-only.

## How to answer "which infra is connected?" correctly

```bash
systemctl --user is-active hermes-gateway.service        # core gateway
hermes gateway status | head -20                          # platforms + state
hermes mcp list                                           # MCP servers
hermes cron list | head -20                               # scheduled jobs
ss -ltn | grep -E ':(8788|9120|8765|9119) '               # local surfaces
tailscale serve status                                    # public/tailnet map
```

## Known traps

- `hermes update` without restarting gateways leaves them on stale modules —
  `hermes gateway restart` (or the updater's fleet restart) is required.
- The WebUI caches the agent git revision; after an update it refuses turns
  until its process restarts (`hermes-webui-revwatch.timer` does this).
- Dashboard `basic_auth` is read at boot only; a config write needs a restart.
- `TWILIO_ACCOUNT_SID` force-enables SMS in any profile that has it; without
  `SMS_WEBHOOK_URL` that platform fails fatally (luxewave was in this state).
