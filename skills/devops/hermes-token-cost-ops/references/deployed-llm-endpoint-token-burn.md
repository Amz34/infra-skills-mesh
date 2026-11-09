# Deployed LLM-proxy endpoint — token burn audit & fixes

Proven 2026-08-27 on `aone-chat-site.pages.dev` (Aone demo chat). Pattern:
static Pages site + `functions/api/chat.js` proxying to
`https://api.deepseek.com/chat/completions` with `env.DEEPSEEK_API_KEY`.

## Why it burns tokens

- Every visitor chat message = 1 DeepSeek API call (system KB + up to 20
  history msgs + ≤1024 output tokens). Fractions of a cent each — fine for
  normal use, but the endpoint is **public, unauthenticated, CORS `*`**:
  anyone can script `POST /api/chat` directly and spam it.
- Key often comes from `~/.hermes/.env` (e.g. `dev-server.sh` does
  `grep '^DEEPSEEK_API_KEY=' ~/.hermes/.env`) → **same balance Hermes uses**.

## Audit (read-only, zero cost)

```bash
cd ~/projects/<site>
npx wrangler pages secret list --project-name <name>   # key present?
# read functions/api/chat.js — which upstream + env vars it uses
cat wrangler.toml                                       # [vars], bindings
grep -oE '^[A-Z_]+=' ~/.hermes/.env | sort -u          # shared keys
```

## Fix 1 — KV-backed per-IP rate limit

1. Create namespaces (prod + preview — Pages `pages dev` needs preview):
   ```bash
   npx wrangler kv namespace create <name>-ratelimit          # → id
   npx wrangler kv namespace create <name>-ratelimit-preview --preview  # → preview_id
   ```
2. `wrangler.toml`:
   ```toml
   [[kv_namespaces]]
   binding = "RATE_LIMIT_KV"
   id = "<prod-id>"
   preview_id = "<preview-id>"
   ```
3. In the function, **before** parsing the request body (so garbage/spam
   requests count too):
   ```js
   const RATE_LIMIT_PER_MIN = 10;
   async function rateLimited(env, ip) {
     if (!env.RATE_LIMIT_KV || !ip) return false;
     const key = "rl:" + ip;
     const raw = await env.RATE_LIMIT_KV.get(key);
     const count = raw ? parseInt(raw, 10) : 0;
     if (count >= RATE_LIMIT_PER_MIN) return true;
     await env.RATE_LIMIT_KV.put(key, String(count + 1), { expirationTtl: 60 });
     return false;
   }
   // ip = request.headers.get("CF-Connecting-IP") || "unknown"
   // 429 JSON response with the same CORS headers
   ```
4. Deploy: `npx wrangler pages deploy dist --project-name <name>`

## Zero-cost verification (no LLM calls)

- **Rate-limit test:** send 12 POSTs with body `garbage-not-json` → first 10
  HTTP 200 ("Something went wrong"), 11th/12th HTTP 429. Garbage bodies
  throw at `request.json()` *after* the counter increments → no upstream
  call, no tokens.
- **End-to-end test:** counter has 60s TTL — `sleep 65` first, then ONE real
  message to confirm a real reply (cost: fractions of a cent).
- `for i in $(seq 1 12); do curl -s -o /dev/null -w "%{http_code}" -X POST ...; done`

## Fix 2 — scheduled kill switch (option 3 pattern)

Disable the chat after a demo window without taking the site down:

```bash
printf 'y\n' | npx wrangler pages secret delete DEEPSEEK_API_KEY --project-name <name>
```

- `wrangler pages secret delete` has **no `--yes`/force flag** — it prompts;
  pipe the answer.
- After deletion the function replies `Server not configured — missing API
  key.` (because of the `if (!apiKey)` guard) → site up, zero token burn.
- Schedule via `cronjob` with `no_agent=true` + a bash script in
  `~/.hermes/scripts/` (delete → sleep 8 → curl real message → grep for
  "not configured" → report). One-shot ISO schedule, e.g.
  `2026-08-29T09:00:00` for "2 din baad".
- KV rate-limit namespace can stay — harmless without the key.

## Pitfalls

- Cloudflare KV is eventually consistent — the counter is "close enough"
  for a 10/min abuse cap, not a hard sliding window. Fine for demo/client
  sites; use Durable Objects if you need exact limits.
- `wrangler pages deploy` output gives a preview URL
  (`https://<hash>.<name>.pages.dev`) — the real domain stays live.
- `web_extract` on the deployed JS returns rendered HTML, not source — read
  the local `functions/` and `dist/` files instead.
