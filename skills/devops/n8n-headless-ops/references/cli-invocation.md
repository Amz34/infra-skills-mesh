# n8n CLI Invocation on This VM (verified 2026-08-26)

## The one working command form

Run ANY n8n CLI command with the service's own node on PATH:

```bash
PATH=/home/ubuntu/.hermes/node/bin:$PATH /home/ubuntu/.local/bin/n8n <command>
```

e.g. `... n8n list:workflow` prints one `id|name` line per workflow.

## Pitfalls that cost time (both hit during verification)

1. **Wrong binary path:** `/usr/lib/node_modules/n8n/bin/n8n` does NOT exist here →
   `MODULE_NOT_FOUND`. The real binary is `/home/ubuntu/.local/bin/n8n` (npx-style install).
2. **Wrong node on PATH:** bare `node` is 20.20.2 → n8n refuses with
   "Your Node.js version ... is not supported by n8n" (needs >=22.22).
   The service (`ExecStart=/home/ubuntu/.local/bin/n8n start`, `EnvironmentFile=/etc/n8n/env`)
   relies on its own PATH; when calling the CLI manually you must prepend
   `/home/ubuntu/.hermes/node/bin` yourself.
3. `/etc/n8n/env` is root-readable only — non-sudo shell can't source it; the CLI
   commands above work without it for read ops (list/export) since n8n reads
   `~/.n8n/` config from the user's home.

## Current workflow inventory (as of 2026-08-26)

| id | name |
|----|------|
| tdZNdqTc16UqJ7MT | Sanas Lead Pipeline |
| carouselWorkflow001 | Carousel Gen: Webhook → Apify → DeepSeek |

- n8n runs as SYSTEM unit (`/etc/systemd/system/n8n.service`, active), port 5678,
  caddy basic-auth proxy on :5680 (no-auth → 401).
- A USER-level `n8n.service` also exists (`~/.config/systemd/user/n8n.service`) but is
  **disabled/inactive** — leftover duplicate; never start it (port 5678 conflict).
- Data dir: `~/.n8n/` (database.sqlite, storage/, nodes/).
