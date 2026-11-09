# Business One Service Layer connector

Working copy: `~/sap-connector/sap_b1/` (`config.py`, `client.py`, `tools.py`),
`mcp_server_b1.py` (11 tools), `mock_b1/server.py`, `tests/verify_b1.py` (16/16),
unit `sap-b1-mcp.service` (:8793), env `~/.config/sap-connector/env-b1`, doc `B1-CONNECTOR.md`.

## Endpoint + auth

Service Layer root `/b1s/v1` (default port 50000, HTTPS). Flow:
`POST /Login` `{CompanyDB, UserName, Password}` → JSON `{SessionId, Version, SessionTimeout}` +
`B1SESSION` cookie → all later calls carry the cookie → `POST /Logout`.
Client (httpx) keeps the cookie in its jar automatically; **session expiry** = HTTP 401 with
business code `301` → re-login **once** and retry the request. Re-login path ko mock me test
karne ka tareeqa: client ke jar se cookie delete karo, phir read — provider ko chhedne ki zarurat nahi.
Use a **dedicated B1 user** (no shared human login) with least-privilege authorisations.

## Entities used (all read + selective write)

`BusinessPartners` (CardCode, CardName, CardType `cCustomer`/`cSupplier`/`cLead`, Country,
Currency, GroupCode), `Items` (ItemCode, ItemName, ItemType, ItemsGroupCode, QuantityOnStock),
`Orders` (DocEntry, DocNum, CardCode, DocDate, DocTotal, DocumentStatus),
`Invoices`, `PurchaseOrders`.

## Query language subset the client implements

`$filter` with `eq|ne|gt|lt|ge|le`, `contains(Field,'x')`, `startswith(Field,'x')`, ` and `;
`$select`, `$orderby` (`Field [asc|desc]`), `$top`, `$skip`. Strings single-quoted — client
escapes embedded quotes by doubling.
**`$count`:** `GET /{collection}/$count` returns a bare integer; pass `$filter` through so a
filtered query's `count` = matched rows (else `row_count != count`). Page carries
`count_scope`: `filtered` / `collection` / `unavailable` (+ `count_error`), rather than lying.

## Writes

`POST /BusinessPartners` → 201 + created object; duplicate CardCode → 400 with code `-2028`
(real B1 duplicate code — mock reproduces it). `PATCH /BusinessPartners('C0001')` → 204 No
Content; changing the primary key → rejected. Same governance as the OData connector:
`SAP_B1_WRITE_ENABLED=0` default, `dry_run=True` default, field whitelist, **read-back after
write** (`read_back_ok`).

## Mock pitfalls (cost me a full run)

- **Route order:** Starlette first-match-wins — `GET /b1s/v1/{collection}` (catch-all) also
  swallows `/b1s/v1/BusinessPartners('C0001')` → single read 404s with a bogus
  "collection does not exist". Fix: in the catch-all, detect `(` and delegate to a
  `_read_single(collection, key, req)` helper (POST/PATCH are separate methods, so they were fine).
- **Be permissive like the real API:** PATCH/POST validation against the *current row's* keys
  rejects `City` on a record created without it. Allowed props = union of all rows' keys +
  known extras (`EXTRA_PROPS`).
- **Filtered counts:** mock `$count` must honour `$filter` too, otherwise the client's
  filtered `count` looks wrong (18 vs 15) and you chase a non-bug.

## Checks (16/16)

wrong-password login error code; unconfigured fail-closed; list + `$select`; filtered count +
`count_scope` + collection count; paging disjoint keys; single read + 404 envelope; write gate
OFF blocks + unchanged; dry-run writes nothing; real create 201 + read-back + duplicate `-2028`;
PATCH 204 + read-back + PK/disallowed-field rejection; cookie dropped → auto re-login;
agent-tool layer (dry-run + blocked message); MCP `tools/list` (11) + read + gated write with
`read_back_ok`. Harness recipe: `connector-verification-harness` reference in skill `mcp-tool-servers`.
