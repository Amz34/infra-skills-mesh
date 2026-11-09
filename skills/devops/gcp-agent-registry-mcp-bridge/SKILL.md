---
name: gcp-agent-registry-mcp-bridge
description: Use when exposing a VM MCP server to GCP Agent Registry.
---

# GCP Agent Registry + Model Armor bridge for VM-hosted infra

Expose a VM-hosted MCP server as a discoverable Google Cloud Agent Registry
service, and screen untrusted text with Model Armor — both free, both
fail-open, without migrating the workload.

## Hard facts (verified 2026-10)

- **Agent Registry is $0.00** for register/store/update/discovery. Only optional
  *skill vulnerability scanning* costs $8 / 1M input tokens, and only from
  2027-01-01.
- **Model Armor standalone is free to 2M tokens/month**, then $0.10 / 1M tokens
  (4 characters = 1 token). Attaching SCC Premium/Enterprise instead changes the
  allocation to 3B/month included.
- **Agent Registry has no `global` location.** Use a region (`us-central1`).
- **Model Armor has no `global` endpoint** — `modelarmor.global.rep.googleapis.com`
  does not resolve. Use `modelarmor.us-central1.rep.googleapis.com`.
- A non-GCP VM **never appears as a Compute Engine instance** in the GCP console.
  It appears only as a registry *service* entry (catalog metadata + endpoint URL).

## Register an external MCP server

```bash
# 1. dump the real tool list, trim to fit the 10KB spec cap (name/description/inputSchema only)
curl -s -X POST $HUB/mcp -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' > /tmp/hub_tools.json

# 2. create the service (protocolBinding for MCP is JSONRPC, not "mcp")
gcloud agent-registry services create <name> \
  --project=$P --location=us-central1 --display-name="..." \
  --mcp-server-spec-type=tool-spec \
  --mcp-server-spec-content=/abs/path/toolspec.json \
  --interfaces="url=https://host/mcp,protocolBinding=JSONRPC"

# 3. verify: tools count lands under mcpServerSpec.content.tools (not .toolSpec)
gcloud agent-registry services describe <name> --project=$P --location=us-central1 --format=json
```

The console Studio panel's "Import tools" only works for publicly hosted
endpoints; for private/authenticated MCP servers upload the tool spec manually
(as above). The registry stores metadata — it does not proxy calls, so the
endpoint's own auth still governs access.

## Model Armor template + sanitize

```bash
POST https://modelarmor.us-central1.rep.googleapis.com/v1/projects/$P/locations/us-central1/templates?templateId=<id>
{"filterConfig":{
  "raiSettings":{"raiFilters":[{"filterType":"HATE_SPEECH","confidenceLevel":"MEDIUM_AND_ABOVE"},
                                 {"filterType":"DANGEROUS","confidenceLevel":"MEDIUM_AND_ABOVE"},
                                 {"filterType":"HARASSMENT","confidenceLevel":"MEDIUM_AND_ABOVE"},
                                 {"filterType":"SEXUALLY_EXPLICIT","confidenceLevel":"MEDIUM_AND_ABOVE"}]},
  "piAndJailbreakFilterSettings":{"filterEnforcement":"ENABLED","confidenceLevel":"MEDIUM_AND_ABOVE"},
  "maliciousUriFilterSettings":{"filterEnforcement":"ENABLED"}},
 "templateMetadata":{"logSanitizeOperations":true}}

POST .../templates/<id>:sanitizeUserPrompt   {"userPromptData":{"text":"..."}}
```

Parse `sanitizationResult.filterMatchState` (`MATCH_FOUND` = block) and
`filterResults` — it is a **dict keyed by filter name**, each value a dict whose
inner objects carry `matchState`/`confidenceLevel`; RAI subtypes arrive under
`raiFilterTypeResults`.

## Local guard pattern (this is the crash-proof bit)

Wrap the API in a tiny localhost service, never call Google inline from a
chat/bot path:

- fail-open: every exception path returns `allow=true` + `degraded=true`
- 2.5s upstream timeout, 6s token-fetch timeout
- circuit breaker: 3 fails -> open 60s
- LRU verdict cache (512 / 10 min) so repeats burn zero quota
- background token pre-warm thread (gcloud cold start ~4s blows the budget)
- user systemd: `Restart=always`, `RestartSec=3`, `MemoryMax=256M`, linger on
- prove it: `kill -9` -> auto-heal <6s; `systemctl --user stop` -> caller still exits 0

Reference implementation: `~/ops/modelarmor-guard/guard.py`, CLI `~/.local/bin/ma-guard`,
shadow hook `~/.hermes/hooks/ma-shadow/`.

## Giving Hermes the Argon model over Vertex (ADC, no static key)

Hermes can't hold a 1-hour gcloud token in config, so put a loopback proxy in
front of Vertex's OpenAI-compatible endpoint:

- upstream: `https://aiplatform.googleapis.com/v1/projects/$P/locations/global/endpoints/openapi`
- model id format is `google/gemini-4-argon`
- proxy mints the bearer from `gcloud auth print-access-token`, caches ~50 min,
  pre-warms in a thread, streams SSE through, returns **502** on auth failure so
  Hermes' fallback chain engages
- alias via `hermes config set model.aliases.argon.<field> <value>` (dotted keys;
  agent writes to `config.yaml` are blocked by design — use the CLI)
- Telegram in-chat switch is `/model argon` (shared CLI+gateway model_switch)

Two Vertex quirks that cost real debugging time:

1. Thinking models spend reasoning tokens from the same budget: `max_tokens: 16`
   → `finish_reason: length` with **empty content**. Use >= 400.
2. `reasoning_effort` accepts only `high|low|max|medium|minimal`; `"none"` (which
   Hermes sends on utility calls) is `INVALID_ARGUMENT`. Remap to `minimal` in
   the proxy or every session logs a stray 400.

Verify with a tool-using prompt, not just "reply OK" — a plain completion can
pass while function calling is broken.

## Pitfalls

- Gateway hooks load **at startup** — a new hook is inert until the gateway is
  restarted. Say so instead of claiming it is live.
- Gateway hooks are observe-only; blocking inbound user text needs a middleware
  plugin. Never sell shadow logging as enforcement.
- Do not restart the gateway just to activate a logging hook while a user is
  mid-conversation through that same gateway.
- `gcloud agent-registry` exists in gcloud 590+; if missing, run
  `gcloud components install agent-registry`.
