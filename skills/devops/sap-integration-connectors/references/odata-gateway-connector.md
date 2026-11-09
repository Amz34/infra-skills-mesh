# OData gateway connector (SAP S/4HANA, ECC + Gateway)

Working copy: `~/sap-connector/` — `sap_odata/config.py`, `client.py`, `tools.py`,
`mcp_server.py` (9 tools), `mock_sap/server.py`, `tests/verify_stack.py` (12/12),
unit `sap-mcp.service` (:8791), env `~/.config/sap-connector/env`.

## Config contract (env-first, secret-safe)

`SAP_LABEL`, `SAP_BASE_URL`, `SAP_PATH` (e.g. `/sap/opu/odata/sap/API_BUSINESS_PARTNER`),
`SAP_APIKEY`, `SAP_USERNAME`/`SAP_PASSWORD` (basic) **or** `SAP_BEARER_TOKEN`,
`SAP_VERIFY_TLS`, `SAP_TIMEOUT`, `SAP_WRITE_ENABLED=0`.
Entity registry = whitelist + per-entity allowed fields; unknown entity/field → typed error,
never a raw KeyError. `health()` reports ok/False + missing-env list; tools **fail closed**
when unconfigured.

## Client behaviours that mattered

- **apikey gate:** sandbox/API-Hub endpoints want a header key (`APIKey`); client sends it only
  when configured. Missing key → provider's own fault envelope (`401 Failed to resolve API Key
  variable request.header.apikey`) — map it, don't swallow it.
- **CSRF for writes:** `GET <base>/?$metadata` (or any read) with `X-CSRF-Token: Fetch` and
  `x-csrf-token` response header capture, reuse the token + session cookie on POST/PATCH/DELETE.
  Copy the cookie jar into the write request or you get 403 "CSRF token validation failed".
- **V2 vs V4 shapes:** V2 `d.results` + `__count` via `$inlinecount=allpages`; V4 `value` array +
  `@odata.count` via `$count=true`. Client returns ONE normalised page dict
  (`ok/system/entity/items/row_count/next`) with a `shape` field telling the caller which flavour
  the endpoint spoke.
- **Paging:** `$top`/`$skip`, `next = {"skip": seen}` only when a total is known.
- **Duplicate create** → provider 409 with its own code; surface provider code + message verbatim.
- **Write gate:** `create_entity(..., dry_run=True)` default → returns the exact payload that
  *would* be sent (`executed: False`); real write only when `SAP_WRITE_ENABLED=1` **and**
  `dry_run=False`, followed by a client-side read-back (`read_back_ok`).

## Mock gateway (`mock_sap/server.py`) — what to fake

API-key gate → 401 fault JSON in the real shape; V2 + V4 envelopes; CSRF fetch endpoint;
`$top/$skip/$filter/$select`; single-key read + 404 envelope; POST 201 + duplicate 409;
PATCH with read-back. Deterministic in-memory data (customers/suppliers/items/orders) so the
verify script can assert exact counts.

## Checks that catch real bugs (12/12)

api-key gate; unconfigured fail-closed; V2 list + projection; V4 normalised shape; paging;
single read + 404; write gate OFF blocks; dry-run writes nothing (read-back); real write 201 +
read-back; duplicate 409; CSRF retry; MCP `tools/list` + `tools/call`. Harness recipe:
`connector-verification-harness` reference in skill `mcp-tool-servers`.
