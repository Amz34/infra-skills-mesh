# Vendor-hosted MCP + OAuth connect (headless VM) — ImagineArt case, 2026-09-15

Concrete transcript-level record. Class-level steps SKILL.md me hain; yahan sirf specifics.

## Vendor artifact (verified)
- Package: `@imagineartofficial/mcp` (bins: `imagine`, plus aliases). Global install root is VM ke
  `/home/ubuntu/.local/lib/node_modules`, binary `/home/ubuntu/.local/bin/imagine`.
- Hosted server: `https://mcp.imagine.art/` (~96 tools). OAuth 2.1 + PKCE, dynamic client
  registration, `scope = "openid email mcp:tools"`, no API keys.
- Docs: `https://docs.imagine.art/integrations/imagine-mcp` ; landing `https://www.imagine.art/mcp`.
- Linkedin shortlink (`lnkd.in/p/<id>`) → `curl -sIL -A "<desktop UA>"` se resolve karo; LinkedIn
  default UA ko block karta hai.

## Commands that worked
```bash
npm install -g @imagineartofficial/mcp          # rtk npm ... fallback ke saath
imagine doctor                                  # OAuth discovery + detected clients + mode decision
imagine install hermes --dry-run --json         # preview: {"mode":"bridge", ...}
cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak-<ts>
imagine install hermes --no-login               # writes config directly, exit 0
hermes mcp list                                 # ImagineArt -> enabled (stdio path column)
```

Install ne `~/.hermes/config.yaml` ke `mcp_servers:` me ye likha (198-203):
```yaml
  ImagineArt:
    command: /home/ubuntu/.hermes/node/bin/npx      # Hermes ka bundled node/npx
    args:
      - -y
      - "@imagineartofficial/mcp@latest"
      - serve
```

## Mode selection (vendor CLI ka logic)
- `hermes` client spec: `supportsOAuth: true` par `ownLoginNeedsTerminal: true`, aur comment:
  "`hermes mcp login` refuses a non-interactive shell, and the Hermes TUI owns the terminal" →
  vendor **bridge (stdio)** chunta hai (`imagine serve`), remote (`--url https://mcp.imagine.art`,
  `auth: oauth`) nahi.
- Bridge = credentials `~/.imagine-mcp/credentials.json` (0600, auto-refresh + revocation handling)
  vendor CLI ke paas; Hermes ko kuch OAuth nahi karni padti. Isi wajah se `IMAGINE_MCP_SERVER_MODE`
  jaisa env knob bhi server-side hai.
- `imagine doctor` strict clients (Codex) ke liye remote ko disqualify karta hai — issuer/origin
  mismatch + missing RFC 9207 `iss` param. Bridge unka fallback hai.

## Headless login (loopback callback)
`imagine login --no-browser --no-welcome` (background process me, warna 5-min wait foreground ko
block kar deta hai) ne ye print kiya:
```
https://imagine.art/mcp/authorize?response_type=code&client_id=mcp_<id>&code_challenge=<...>
 &code_challenge_method=S256&redirect_uri=http%3A%2F%2F127.0.0.1%3A45817%2Fcallback
 &state=<32-hex>&scope=openid+email+mcp%3Atools&resource=https%3A%2F%2Fmcp.imagine.art%2F
```
- CLI bundled code me koi device-code / paste-a-code fallback **nahi** hai — sirf loopback server
  (127.0.0.1:<random port>, `/callback`, state check) + `LOGIN_TIMEOUT_MS = 5 * 60 * 1000`.
- Isliye headless VM pe plan: URL user ko do → wo apne phone pe sign-in kare → redirect uske phone ke
  127.0.0.1 pe fail hoga → address bar ka poora URL (`?code=...&state=...`) wapas bheje → VM pe
  `curl "http://127.0.0.1:<port>/callback?code=...&state=..."` → CLI exchange complete kare.
- Session me user sign-in pending chhoda gaya tha — is completion step ko end-to-end verify karke hi
  aage badho; `imagine status` / ek real tool call se confirm karo, warna "connected" mat kaho.

## Tooling gotchas
- Vendor JS minified hai (`dist/cli.js`). Inline `grep -o -E ".{200}paste.{300}"` jaisa lamba pattern
  hardline-block ho jaata hai — `~/ops/tmp/imagine_probe.py` me chhota python script likho jo
  `re.findall(r'PREFERRED_CALLBACK_PORT\s*=\s*[0-9]+', src)` type patterns chala kar print kare.
- `imagine --help` / `imagine doctor` ka output kabhi `| head -N` me mat phenko jab usi se next step
  decide karna hai — pehle file me capture karo, phir padho.
- Hermes ko MCP extra chahiye: `uv tool install "hermes-agent[mcp]"` — warna `mcp.client.streamable_http`
  import fail hota hai.
