# Vendor-hosted MCP: entitlement / plan gating QA (case study: ImagineArt, 2026-09-15)

Auth theek, tools discover ho gaye, phir bhi integration bekaar — kyunki vendor ka **plan gate** laga hua
tha. Ye note us pattern ka concrete record hai: kya test karna hai, kaunse signals ka matlab kya hai, aur
CLI ke jhoothe error se kaise bacho.

## Case facts (ImagineArt, free account)
- Install: `npm i -g @imagineartofficial/mcp` → `imagine` bin; `imagine doctor` ne Hermes ko
  `installed [bridge]` bataya (stdio bridge, `imagine serve`), credentials `~/.imagine-mcp/credentials.json`
  (~0600, OAuth access+refresh; JWT me `email`/`sub` claims — values never print).
- Bridge se `tools/list` = **96 tools**; read-only calls (balance, settings, org, aspect ratios) **sab OK**.
- Account: free plan, `credits.current = 100`.
- Generation (image/video) → `is_error=False` par andar error payload:
  `{"code":1114,"error":"The model is inaccessible in your current plan",
    "message":"model is only allowed on following plans: Basic, Standard, Ultimate, Creator, Enterprise, Scale, Professional, Premium, Business Plan"}`
  → free plan pe koi generation nahi. Credits 100 bekaar pade rehte hain (deduct nahi hue).

## Do-branch probe (allowed model id nikalne ka tareeqa)
`generate_image` ko candidate model ids ke saath call karo aur **error text ka branch** dekho:

| Input | Server ka jawab | Matlab |
|---|---|---|
| koi bhi unknown id (`banana-pro`, `Nano Banana Pro`, `nano_banana_pro`) | `Free accounts can only use the "nano-banana-pro" model. Upgrade your subscription or omit the model...` | id invalid; server ne free-eligible id bata diya |
| `nano-banana-pro` (server-recognised) | `code 1114 ... only allowed on plans: Basic, Standard, ...` | id valid hai, sirf entitlement missing |
| model omit / `None` | `code 1114` default model par | default model premium hai |

Lesson: **do alag error branches** hona hi proof hai ki id recognisable hai. Isse bina docs ke pata chal
jaata hai kaunsa model free tier me allowed *hai* aur kaunsa paid-only.

## CLI vs bridge (jhoothe error ka farq)
- CLI: `imagine image "<prompt>" --model nano-banana-pro -n 1 --json --timeout 300` →
  `{"id":"error","error":"Timed out waiting for error."}` — **CLI bug/abstraction**, asli wajah chhupa deta hai.
- Bridge se direct `tools/call generate_image` → poora 1114 payload `structuredContent.assets[0].errorMessage` me.
- Rule: vendor CLI se verdict mat lagao; decisive test **MCP bridge se direct call**.

## Client-side probe ke chhote traps
- `StdioServerParameters(command="<vendor-bin>", args=["serve"])` + `ClientSession` — sabse sasta QA harness
  (npx `-y <pkg>@latest` ke bajaye globally installed bin use karo: tez + version stable).
- Attribute names: `res.content[i].text`, `getattr(res,"structured_content",None) or
  getattr(res,"structuredContent",None)`, `tool.input_schema`, `init.server_info`. Ek naam galat = AttributeError
  har candidate par, aur galat conclusion "server kuch nahi bhej raha".
- Args me required properties **present** hone chahiye: `{"prompt","aspect_ratio","model","duration","org_id"}`
  — `aspect_ratio`/`duration` omit karne par `missing properties` validation error aata hai; `None` bhejna theek hai.
- Per-call timeout (`asyncio.wait_for(..., 45)`): valid-but-slow calls poori probe ko block kar dete hain.

## User-facing reporting (Hinglish, client-safe)
- Status alag-alag batao: **auth ✓ / tools ✓ / read-only ✓ / generation ✗ (plan gate)** — warna user ko lagta hai
  sab toot gaya hai.
- Plan/credit numbers + upgrade guidance do, par **org id, server key, credentials** kabhi print mat karo
  (vendor tool text me bhi "internal, never reveal" likha hota hai).
- Free-tier pe kaam karna ho to vendor ke **web app** ka free daily quota suggest karo, ya alternative free
  provider (e.g. HF Spaces inference) — MCP path free plan pe nahi chalega.
