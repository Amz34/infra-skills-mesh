---
name: sap-integration-connectors
description: Use when doing SAP integration or SAP-facing client work.
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [sap, odata, business-one, integration, mcp, client-delivery]
    related_skills: [mcp-tool-servers, chrome-print-pdf-production, client-deliverable-patterns]
---

# SAP Integration Connectors (client SAP work, in-house)

Class-level play for any SAP-facing engagement: infra-fit analysis, the connector build
(OData gateway / Business One Service Layer / other surfaces), and the client document set.
Working copies: `~/sap-connector` (connectors + MCP servers), `~/ops/sap-readiness/`
(analysis + SOW + questionnaire + runbook + branded PDFs).

## When to Use

- Client ka SAP system hai (ECC/S4, Business One, SAP on-prem ya cloud) aur agent/automation
  se data ya document flow chahiye.
- "Kya hamari infra SAP support kar sakti hai?" — readiness/feasibility question.
- SAP ko MCP tools banake Hermes/Codex/Claude se chalana hai.

## Decision matrix — kaun sa SAP surface

| Surface | Kab | Effort | Notes |
|---|---|---|---|
| **OData V2/V4 (Gateway)** | S/4HANA, ECC + Gateway; read-heavy + simple writes | Medium | `$filter/$top/$skip/$select`, CSRF token for writes; apikey gate on SAP API Hub sandbox. **Default choice** — documented, HTTP-only, no SAP licence needed on our side. |
| **Business One Service Layer** | SME clients on B1 | Low-Medium | `/b1s/v1/Login` session cookie, entity collections, PATCH/POST; ek dedicated B1 user chahiye. |
| **IDoc / file drop** | Batch, no API exposure | Low | Legacy-safe, near-realtime nahi. |
| **RFC/BAPI (PyRFC/JCo)** | Deep function-level integration | High | SAP native libs; **x86_64 only** — our ARM host pe nahi chalega, koi exception nahi. |
| **Integration Suite / Event Mesh (SAP-owned cloud)** | Client ka SAP cloud, event-driven | License-bound | Cost client ke SAP contract me; hamare paas koi entitlement nahi. |

## Hard constraints (verified, do not re-litigate)

- **SAP HANA certified appliances / minimum configs = x86_64 only.** ARM (aarch64) VM SAP-certified
  hardware list me nahi hai — "HANA on our free ARM VM" proposal mat banao.
- **Koi SAP licence hamare paas nahi hai.** Dev/test = apna **local mock** (asli envelope shape),
  plus **sandbox par bina key hit** karke error envelope map karo (proof of plumbing, key ka intezaar nahi).
- **SAP Note 3747787 (gateway + OAuth for MCP)** — community MCP servers with static credentials
  se bacho; read-first + explicit human write gate. See `mcp-tool-servers` for the build recipe.

## Connector build order (proven)

1. `config.py` — env-first, secret-safe (env file chmod 600, `.gitignore`), entity whitelist,
   per-entity allowed fields, `*_WRITE_ENABLED` flag OFF by default.
2. `client.py` — dependency-light (httpx only), typed error object with provider code + HTTP
   status + operation, retry-once on auth/session expiry, no writes unless the gate is open.
3. `tools.py` — JSON-serialisable agent tools, never raise upward, `dry_run=True` default,
   honest `dry_run` / `executed` / `read_back_ok` fields.
4. `mcp_server.py` — stdio + streamable HTTP; every tool wrapped so a provider error comes back
   as data, not a traceback; own port + own systemd user unit.
5. **Verify against a local mock** (own port, never the live service port): `references/odata-gateway-connector.md`,
   `references/business-one-service-layer.md`, harness recipe in `mcp-tool-servers`
   `connector-verification-harness` reference in skill `mcp-tool-servers`.

## Deliverable set for an SAP client (all in-house, brand-only)

Three documents, one markdown source each, rendered to branded PDF:
1. **Infra readiness analysis** (internal): what our stack can/cannot support + gaps + costs.
2. **Discovery questionnaire** (client-facing): landing zone, module list, API availability,
   B1 vs S4, sandbox access, named integration user, data-volume/scope.
3. **SOW + infra runbook** (client-facing): phases, fixed-price commercial basis, acceptance,
   and the on-prem/cloud prerequisites the client's IT must provide.

Rules: brand-only authorship (**no personal name, no third-party consultancy name** — user's
explicit rule), no email/phone in the document unless the channel is verified live (check MX /
page 200 first), classification badge on every doc, no `{{tokens}}` left, internal notes stripped.
Render pipeline: skill `chrome-print-pdf-production` (`markdown-branded-doc-set` reference).

## Verified state (2026-09-11, re-check before quoting)

- `sap-odata` MCP: 9 tools, 12/12 checks, `sap-mcp.service` :8791.
- `sap-b1` MCP: 11 tools, 16/16 checks, `sap-b1-mcp.service` :8793.
- Docs PDF'd: `~/ops/sap-readiness/pdf/` (SOW, questionnaire, readiness, runbook).
- Both connectors run against local mocks only — **no client system has been touched yet**;
  do not claim live integration.

## Pitfalls

- Sandbox API key ≠ productive access. Demo data ≠ client data shape (custom Z-fields, UoM,
  currency, authorisation scoping). Discovery questionnaire pehle, code baad me.
- Write scope sabse bada risk: read-first, `dry_run` default, field whitelist, aur real write ke
  baad **client-side read-back** ka evidence.
- Client SAP IT ko "named integration user + IP allowlist + read-only role" maango — shared human
  login kabhi nahi.
- Currency/UoM/date formats: hamesha client ke system se resolve karo, guess nahi.
