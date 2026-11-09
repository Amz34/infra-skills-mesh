# Connector verification harness (mock + MCP server in one script)

Working copies: `~/sap-connector/tests/verify_stack.py` (OData, 12 checks),
`~/sap-connector/tests/verify_b1.py` (Business One Service Layer, 16 checks).
Ye recipe dono se nikla hai — naya connector banate waqt copy karo.

## Why one script

Credentials nahi chahiye, network nahi chahiye, aur ek hi command poora stack prove
karta hai: connector (client) → agent tool layer → MCP server. Dashboard/demo se pehle
yahi script gate hai.

## Shape

```python
# 1. env for the CHILD MCP process (mock URL, dummy creds, write gate ON for write tests)
os.environ["SAP_B1_BASE_URL"] = f"http://127.0.0.1:{MOCK_PORT}/b1s/v1"
os.environ["SAP_B1_COMPANY_DB"], os.environ["SAP_B1_USERNAME"] = "SBODEMO", "manager"
os.environ["SAP_B1_PASSWORD"] = "mock-pass"
os.environ["SAP_B1_WRITE_ENABLED"] = "1"

# 2. boot mock: uvicorn subprocess  (mock_b1.server:app)
# 3. boot MCP:  subprocess <repo>/mcp_server.py --http --host 127.0.0.1 --port <MCP_PORT>
# 4. wait for readiness: TCP connect (NEVER an HTTP GET on /mcp — SSE stream never closes)
# 5. run checks as (name, callable) pairs; print PASS/FAIL + one-line detail
# 6. finally: terminate both, print "N/N checks passed", nonzero exit on any FAIL
```

MCP over streamable HTTP from the harness — keep it ~30 lines, no SDK dependency:

```python
class McpHttp:
    def __init__(self, url): self.url, self.sid = url, None
    def _rpc(self, method, params, _id):        # POST JSON-RPC 2.0
        h = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
        if self.sid: h["mcp-session-id"] = self.sid
        r = httpx.post(self.url, json={"jsonrpc": "2.0", "id": _id, "method": method,
                                       "params": params}, headers=h, timeout=30)
        if r.headers.get("mcp-session-id"): self.sid = r.headers["mcp-session-id"]
        return r.json()
    def initialize(self): ...           # then notifications/initialized
    def list_tools(self): return self._rpc("tools/list", {}, 2)["result"]["tools"]
    def call_tool(self, name, args):
        res = self._rpc("tools/call", {"name": name, "arguments": args}, 3)["result"]
        return res["structuredContent"] if "structuredContent" in res else json.loads(
            res["content"][0]["text"])
```

## Check list that catches real bugs

Read/plumbing: health; wrong-password login error code; unconfigured → fail-closed;
`$top/$select` projection; filter + `count_scope`; paging (`top`/`skip` disjoint keys);
single-key read vs 404 envelope.
Governance/write: gate OFF + `dry_run=False` → blocked AND target unchanged (read-back);
gate ON + `dry_run=True` → `executed: False` and nothing written; gate ON + real write →
201/204 **plus client-side read-back**; duplicate key → provider error code surfaced;
PATCH primary key rejected; disallowed field rejected.
Auth lifecycle: cookie jar se session delete → next read succeeds (auto re-login, once).
MCP layer: `tools/list` count == expected; one read call; one write call with
`read_back_ok` true.

## Pitfalls hit for real

- **Port isolation:** harness port must differ from the persistent systemd service port
  (8799 vs 8791) — warna test khamoshi se live service hit karta hai aur 12 me se 9 checks
  jhoote fail dikhte hain. Env override (`VERIFY_MCP_PORT`) + free default rakho.
- **`row_count == count` assert** sirf tab valid hai jab dono filtered hon; warna
  collection count aur matched rows compare karke galat fail milta hai.
- **Filtered rows assert karo, magic number nahi:** `all(r["Country"] == "SA")` +
  `count >= N`. Magic expected counts run ke andar banaye gaye records se badal jate hain.
- **`except` var ko return string me use mat karo** (`exc` except ke bahar undefined →
  UnboundLocalError test ke andar). Value ko except ke andar variable me le lo.
- **Har run ka output save karo:** `tests/last-verify-output.txt` /
  `tests/last-verify-b1-output.txt` — evidence ke liye, aur regression compare ke liye.
- **Fixture DDL ko asli DB se copy karo, retype mat karo.** Fixture `rates(id TEXT PRIMARY KEY)`
  likha tha jabki live DB `id INTEGER PRIMARY KEY` hai → `rates_fts.rowid = rates.id` join chup-chaap
  kuch match nahi karta (exception nahi, bas khaali result — aur \"retrieval kharab hai\" jaisa galat
  conclusion). Column *types* bhi mirror karo (`sqlite3 <live.db> .schema` se paste), aur ek check rakho
  jo known-good query pe non-empty rows assert kare.
- **Model-dependent stack me model bhi mock karo:** `~/rag-connector/tests/mock_ollama.py` (60 lines,
  stdlib HTTP) `/api/embed`, `/api/chat`, `/api/tags` pe deterministic hash bag-of-words vectors deta hai
  → poora suite offline, free aur repeatable (~20 checks/~40s, live store ko haath nahi lagta).
- **Env vars config ke *import* se pehle set karo** (`os.environ[...] = ...` imports se upar) — config
  import-time pe env padhta hai; warna harness chup-chaap live config/store pe test karta hai aur aapko
  lagta hai mock chala.
