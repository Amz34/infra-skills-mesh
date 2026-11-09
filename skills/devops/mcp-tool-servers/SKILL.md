---
name: mcp-tool-servers
description: Use when wrapping integrations as MCP servers for agents.
---

# MCP Tool Servers (integrations → agent tools)

Astra wave lesson #15 (skirano: Ableton track end-to-end through MCP) + director pattern (#20): creative/pro apps ko MCP se agent-controlled banana. Hamare liye: jo integrations REST scripts me hain unhe MCP tools me wrap karo = koi bhi agent (Codex, Claude Code, Hermes subagents) directly call kar sake — naya glue code har baar nahi.

## Trigger
- Ek integration (Shopify/WhatsApp/Telegram/GSheets/Notion) ko agent workflow me use karna hai bina naye adapter ke.
- Agent ko "tool use" se multi-step task karwana hai (content post → measure → iterate).
- Existing skill scripts ko reusable tools me upgrade karna hai.
- **Kisi vendor ka hosted MCP connect karna hai** (ImagineArt jaisa SaaS, apna wrapper nahi) →
  uske official CLI se install karo; section "Vendor-hosted MCP server connect karna" dekho.

## Workflow
1. **Integration chuno** + uske existing scripts/tokens identify karo (~/.config me 600-permission files, .env).
2. **MCP server wrap karo**: Python `fastmcp`/`mcp` SDK — har operation ek tool (e.g. `shopify_create_product`, `whatsapp_send_message`). Tool schema precise (inputs, returns).
3. **Auth reuse**: tokens env vars se, kabhi code me hardcode nahi; existing token files (e.g. ~/linkedin_token.json, ~/.config/notion/token) reference karo.
4. **Least privilege**: sirf wo tools expose karo jo task ko chahiye — full API surface nahi.
5. **Register**: agent config me MCP server add (Codex/Claude Code MCP config; Hermes me tool-server pattern). Test karo real call se (verify: 201/URL/read-back).
6. **Rate limits + retries**: server me built-in retry/backoff; Shopify/WhatsApp quota respect karo.

## Pitfalls
- Tokens MCP config/logs me leak na hon (600 perms, .gitignore).
- Tool scope bada = risk bada — sirf zaroori tools.
- Har platform ka auth alag (OAuth refresh vs app password) — pichle skill setup (shopify-headless-ops, messaging-platform-integrations) se config reuse karo.
- MCP registry versioning — npx @modelcontextprotocol/server chala rahe ho to versions pin karo.
- **mcp SDK 2.x me `fastmcp` import purana hai**: `from mcp.server import MCPServer` use karo; `MCPServer(name=, version=, instructions=)`, `@mcp.tool()`, `mcp.run(transport="stdio")`, aur HTTP ke liye `asyncio.run(mcp.run_streamable_http_async(host=..., port=..., streamable_http_path="/mcp", json_response=True, stateless_http=True))`. Signature ke kwargs `inspect.signature()` se filter karo — SDK minor versions me badalte hain.
- **Readiness check**: streamable-HTTP endpoint pe GET se poll mat karo — woh SSE stream kholta hai jo band nahi hota (httpx timeout loop me phans jaoge). TCP connect se port check karo, phir `initialize` POST.
- **`hermes mcp add` interactive hai** (auth? → key → "Enable all N tools?"): non-interactive ke liye `printf 'n\nY\n' | hermes mcp add <name> --url http://127.0.0.1:<port>/mcp`. Galat input dene par ek stray `MCP_<NAME>_API_KEY` line `~/.hermes/.env` me likh di jaati hai (protected file — terminal se hatao).
- **Behtar scriptable rasta (verified)**: `hermes mcp add` piped input par `Cancelled.` de deta hai + `.env` me kachra chhodta hai. Iske bajaye nested config set use karo: `hermes config set mcp_servers.<name>.url http://127.0.0.1:<port>/mcp` aur `hermes config set mcp_servers.<name>.enabled true` — agent ke liye config.yaml direct likhna BLOCKED hai, lekin `hermes config set` chalta hai. Verify: `hermes mcp list` (row + "✓ enabled") aur `hermes mcp test <name>` (tools enumerate).
- **Naya MCP infra me dikhta hai automatically**: dashboard `eco.mcps` har profile ke `config.yaml` ke `mcp_servers` block se ban jaata hai — alag se register karne ki zaroorat nahi. Port-level up/down chahiye to collector ke `APP_CHECKS` me ek tuple add karo (`("latex_mcp","LaTeX / Overleaf MCP (8795)","Containers & AI","http",8795,"/mcp")`) aur connector inventory list me `(name, kind, note, config_path)` row — `/mcp` pe GET 406 deta hai jo "up" (<500) count hota hai.
- **Governance:** write tools ko default dry-run rakho aur ek explicit env gate (`<SYSTEM>_WRITE_ENABLED=1`) ke peeche; MCP clients (Claude Code/Codex/Hermes) acche-bure dono tarah call karte hain.

- **Session-cookie APIs (login-based REST, e.g. SAP B1 Service Layer `/Login`):** login response ka cookie httpx ke jar me khud chala jata hai; har request pe 401 / error `code 301` aaye to **ek baar** re-login karke retry karo (infinite loop nahi). Re-login path verify karne ka sasta tareeqa: client ke cookie jar se cookie delete karo, phir read karo — mock me koi special support nahi chahiye.
- **Filtered count semantics:** `count=True` ka matlab "kitne rows filter se match hue" hona chahiye, warna `row_count != count` par assert girta hai. `/{collection}/$count?$filter=...` bhejo aur page me `count_scope` ("filtered"/"collection"/"unavailable") rakho.
- **Mock me route order:** Starlette pehla match jeetta hai — `GET /{collection}` catch-all `/{collection}('KEY')` ko bhi nigal jaata hai (404 "collection does not exist" jaisa bhram). Catch-all handler me `(` dekh kar single-read helper ko delegate karo; POST/PATCH alag method hone se theek chalta hai.
- **Mock ko asli API ki tarah udaar rakho:** PATCH/POST par unknown-field validation current row ke keys se mat karo — collection ke saare rows ka union + known extra props (`EXTRA_PROPS`) lo, warna naya banaya gaya record PATCH par reject hota hai jabki asli API accept karta.
- **Multi-patch batches:** ek call me 4-6 patch bhejna theek hai, par `old_string` chhota (≤4 lines) rakho. Lamba block quote bhejne par tool output truncate hota hai aur literal `...[truncated]` file me likha ja sakta hai — phir `py_compile` pe SyntaxError. Har patch batch ke baad `python -m py_compile <files>` chalao, tabhi test.

## Vendor-hosted MCP server connect karna (third-party CLI + OAuth, headless VM)

Trigger: koi vendor apna **hosted MCP** deta hai (ImagineArt jaisa SaaS) → apna wrapper likhne se
pehle vendor ka official CLI try karo. Poore concrete commands: `references/vendor-mcp-oauth-headless.md`.

1. **Artifact identify:** docs page + npm package (`npm view <pkg> version description bin`), phir
   `npm i -g <pkg>`.
2. **Pehle dekho, phir likho:** `<bin> doctor` (vendor ka OAuth/client-discovery report — kis client
   ke liye bridge vs remote choose kar raha hai) aur `<bin> install <client> --dry-run --json`.
3. **`~/.hermes/config.yaml` ka backup** lo install se pehle — vendor installer file ko *directly* edit
   karta hai (kyunki `hermes mcp add` interactive hai).
4. **Install:** `<bin> install hermes` → Hermes me **bridge (stdio)** entry likhta hai:
   `mcp_servers: <Name>: {command: <hermes ka bundled npx>, args: [-y, "<pkg>@latest", serve]}`.
   Bridge kyun, remote kyun nahi: vendor spec me `supportsOAuth: true` par `ownLoginNeedsTerminal: true`
   hota hai (Hermes ka `hermes mcp login` non-interactive shell refuse karta hai, TUI terminal ka owner
   hai) → stdio bridge sasta padta hai; credentials vendor ki ek file me (~0600, auto-refresh) rehti hain
   aur Hermes ko apni OAuth nahi karni padti.
5. **Register verify:** `hermes mcp list` me entry dikhni chahiye; naye tools agle session me milte hain.
6. **Auth (headless VM ka loopback problem):** `<bin> login --no-browser --no-welcome` background process
   me chalao — wo authorize URL deta hai jiska `redirect_uri=http://127.0.0.1:<random-port>/callback`
   hota hai. User us URL ko apne device pe kholta hai, redirect uske device ke localhost pe jaata hai →
   page fail hota hai; us se **address-bar ka poora URL (`?code=...&state=...`) mangwa kar VM pe `curl`
   karo** — vendor ka loopback server usi request se code exchange complete karta hai. Login window
   aksar ~5 min (code me `LOGIN_TIMEOUT_MS`) → URL foran bhejo, expire ho to dobara chalao. (Ye flow
   design/code se confirm hai; ek baar user ke saath end-to-end verify karna baaki reh sakta hai — aise
   case me \"connected\" mat kehna, sirf \"auth step pending\" bolo.)
7. **QA khud karo:** `<bin> status` + `hermes mcp list`, phir ek **real sasta tool call** (ek generation
   ya ek read) — registration ≠ working integration. Read-only call akele proof nahi hai: free/limited plan
   par balance/settings/list tools chalte hain par **paid path** (generation) plan-gate deta hai — neeche
   "Entitlement / plan gating" section dekho aur wahi decisive call maano.

Extra pitfalls:
- Vendor installer `@latest` likhta hai. Pin karo to churn kam, par vendor ka update path toot sakta hai — trade-off likh kar rakho.
- Bundled/minified vendor JS (`dist/cli.js`) inspect karne ke liye inline `grep -o -E '<giant pattern>'` mat bhejo — lamba inline pattern hardline-block hota hai. `~/ops/tmp/` me chhota python probe script (`re.findall`) likho.
- Generative vendor tools me **human-face studios default hote hain** — hamare NO-human-faces rule se takraate hain; QA/report me inanimate product output chuno.

## Entitlement / plan gating — auth ho gaya ≠ integration kaam kar raha hai
Vendor MCP me OAuth pass hona sirf pehla step hai. Generation/paid tools aksar **plan-gated** hote hain:
read-only tools (balance, settings, `list_*`) chal jaate hain, par asli generation `code 1114 "The model is
inaccessible in your current plan"` deta hai. Isliye registration + `doctor` ke baad **ek real paid-path
call** karo aur uska error code capture karo — warna user ko bekaar ka upgrade/downgrade advice chala jaata hai.

- **Allowed-model discovery bina docs:** (a) tool ko **bogus model id** ke saath call karo — kai servers
  jawab me bata dete hain kaun free eligible hai (`Free accounts can only use the "<id>" model`);
  (b) us id ko dobara call kar ke **error branch compare karo**: unknown id → "only <id> allowed",
  known-but-gated id → plan list ("only allowed on plans: Basic, Standard, ..."). Do alag messages =
  id valid hai, sirf entitlement missing. Recipe + case study: `references/vendor-mcp-plan-gating.md`.
- **Vendor CLI ka error message jhootha ho sakta hai:** `imagine image --model <x>` ne `id error` +
  `"Timed out waiting for error."` dikhaya, jabki asli jawab 1114 plan-gate tha. Bridge se **direct
  `tools/call`** karo aur `text` + `structured_content` dono padho — wahi asli error laata hai.
  Reusable caller: `scripts/mcp_stdio_call.py`.
- **Client-side mcp SDK attributes version-dar-badalte hain:** `init.server_info` (`serverInfo`),
  `tool.input_schema` (`inputSchema`), `res.structured_content` (`structuredContent`). Har jagah
  `getattr(o, "structured_content", None) or getattr(o, "structuredContent", None)` fallback rakho —
  warna probe `AttributeError` pe marta hai aur lagta hai server ne kuch bheja hi nahi.
- **Tool args validation presence chahta hai, sirf null-allowed nahi:** `generate_image` ko
  `{"model": None}` dene par `missing properties [aspect_ratio, duration]` mila. Optional fields
  **explicit null** ke saath bhejo, omit mat karo.
- **Vendor tool text me "internal" markings hoti hain** (server key, org/user ids, "do not reveal").
  User-facing reply me plan/credits/error summary do — andar ke ids/keys print mat karo.


## Authoring a *new* server — four phases

Upstream `anthropics/skills` → `mcp-builder` (Apache-2.0) ka method, hamare lessons ke saath
merge kiya (frozen copy: `~/ops/vendor/skills/anthropics/mcp-builder/`):

1. **Research** — modern MCP design + framework docs padho, phir target API ko *apex tool*
   ke liye plan karo (kya agent ko sach me chahiye, na ki poori API surface).
2. **Implement** — ek shared API client (auth/retry/rate-limit ek jagah), har tool me
   `outputSchema` + `structuredContent`, aur annotations set karo: `readOnlyHint`,
   `destructiveHint`, `idempotentHint`, `openWorldHint`. Tool names prefixed
   (`shopify_create_product`, `sap_b1_list_orders`) — flat namespace me collision bachao.
3. **Review/test** — MCP Inspector se call karo, aur `references/connector-verification-harness.md`
   ke verify script se (client-level + `tools/list`/`tools/call`) assert karo.
4. **Eval** — 10 read-only, realistic, verifiable questions likho (independent, ek API
   sequence se answer ho, string-compare se grade ho sake), phir agent ko **answer-only**
   mode me chala kar tool output dekhne ke bajaye sirf final answer grade karo. Feedback
   loop: eval fail → tool description/schema fix karo. Har eval `<qa_pair>` me ek question,
   grading ke liye expected answer alag.

Tool-output discipline jo har eval fail karata hai: results **limited** rakho (default
`limit`, phir pagination), errors actionable (`"invalid customer_id: expected 6 digits"`,
poora traceback nahi), aur bade payloads paginate karo — warna agent context blow hota hai.

## Reference implementation
`~/sap-connector` (2026-09-11): SAP OData V2+V4 client + 9-tool MCP server + local mock gateway + `tests/verify_stack.py` (12/12 checks) + systemd user unit `sap-mcp.service` (port 8791). Doosra connector usi repo me: `sap_b1/` + `mcp_server_b1.py` + `mock_b1/` + `tests/verify_b1.py` (11 tools, 16/16 checks) + `sap-b1-mcp.service` (port 8793).
Teen more, same layout: `~/latex-connector` (12 `tex_*` tools, :8795), `~/rag-connector` (7 `rag_*` retrieval tools, :8797 — ChromaDB + local ollama, `tests/verify_rag.py` 20/20, `make test` canonical, plus `make profile` / `make chunker-ab` chunker A/B diagnostics), `~/ai-memory` (:49374 wiki tools).
**Mock the *model* too, not just the gateway.** `~/rag-connector/tests/mock_ollama.py` is a 60-line stdlib HTTP server
that answers `/api/embed`, `/api/chat`, `/api/tags` with deterministic hash bag-of-words vectors — point `OLLAMA_URL` at
it and a retrieval stack becomes fully offline, free and repeatable (20 checks in ~40s, no live store touched). Recipe:
set every env var the config reads *before* importing the package (config reads env at import time), run the real MCP
server as a subprocess on the verify port, and drive it over raw JSON-RPC.
**Ek connector = ek package + ek MCP entrypoint + ek mock + ek verify script + apna port + apna unit** (shared code copy karo, import nahi) — ek client ka change doosre ko na tode. Deliverable docs alag jagah: `~/ops/sap-readiness/` (readiness analysis, questionnaire, SOW, runbook + markdown→branded-PDF render pipeline). Naya connector banate waqt ye layout copy karo: client / tools / mcp_server / mock / verify_stack. Verification harness ka full recipe (JSON-RPC client, check list, real pitfalls): `references/connector-verification-harness.md`.

## Verification
- Har tool ka ek real call test: response + target pe read-back (external_state_verification pattern).
- Agent (Codex/Claude) MCP server list me tool dikh raha hai aur call kar raha hai.
- **Credentials ke bina verify (mock-gateway recipe):** external API ka chhota FastAPI mock banao jo asli gateway ki *shakal* de (API-key gate → 401 fault JSON, V2/V4 envelopes, CSRF fetch, 409 duplicate, `$top/$skip` paging, single-key read + 404), phir **ek hi script** me mock + MCP server boot karke client-level aur MCP-level (`tools/list`, `tools/call`) asserts chalao. Working template: `~/sap-connector/tests/verify_stack.py` (12 checks).
- **Real-endpoint proof bina creds:** asli endpoint ko bina key hit karo aur dekho ki uski *apni* error envelope map hoti hai (e.g. SAP sandbox → `401 Failed to resolve API Key variable request.header.apikey`, APIM fault shape). Ye network + auth + error-parsing plumbing prove karta hai — key ka intezaar nahi.
- **Verify port persistent service se alag rakho.** Warna test khamoshi se live service ko hit karta hai aur mock config ki jagah live config pe assert karta hai — 12 me se 9 checks fail dikhte hain jabki product code theek hai. Env var se override (`VERIFY_MCP_PORT`), default free port (8799).
- **Persistent deployment:** systemd **user** unit + `EnvironmentFile` (chmod 600) — `templates/mcp-http-service.service`, `templates/connector-env.example`. Verify chain: `systemctl --user daemon-reload && systemctl --user enable --now <unit>` → `is-active` → `ss -tlnp | grep <port>` → `hermes mcp list` → `hermes mcp test <name>`.
- Register karne ke baad naye MCP tools **agla session** me agent ko milte hain — usi turn me "tool available hai" mat kehna.
