# Cloudflare Pages Deploy on Headless VM — Full Recipe

Validated on AVVS Triatek (Aug 2026): bilingual static site at site root,
Pages Function `functions/api/lead.js` → Telegram, production
`https://<project>.pages.dev`.

## 1. Auth: use `wrangler login --device` (NOT token, NOT callback flow)

- `CLOUDFLARE_API_TOKEN` from the dashboard often verifies as **401 Invalid
  API Token** (paste corruption; CF tokens are 40 chars, `cfat_`-prefixed
  variants can be longer). Don't burn time re-pasting — switch to OAuth.
- `npx wrangler login` (localhost callback flow) FAILS on a headless VM:
  the CLI prints `http://localhost:8976/oauth/callback?...`, the user opens
  it on their phone, authorizes, and the redirect lands on THEIR device's
  localhost — not the VM. The CLI times out after ~3 min. The user can
  paste the callback URL back, but the process usually dies first.
- **Correct flow — Device Authorization Grant:**
  ```bash
  npx wrangler login --device   # run in background terminal
  ```
  CLI prints: visit `https://dash.cloudflare.com/oauth2/device/verify`
  and enter code `XXXXXXXX` (5-min window). Send the user the
  `?user_code=XXXX` prefilled URL — they open it, hit Allow, done.
  `wrangler whoami` confirms; credentials persist in
  `~/.config/.wrangler/` for future deploys — no token file needed.

## 2. Project create + deploy (site files at repo root)

```bash
npx wrangler pages project create <project> --production-branch master
npx wrangler pages deploy . --project-name <project> --branch master --commit-dirty=true
```
- Output dir is `.` when the site root == repo root (no `public/`).
- `--commit-dirty=true` silences the "uncommitted changes" warning.
- `functions/` auto-detected and bundled (no wrangler config needed for it).
- Keep `spec/`, `*.py`, `.dev.vars` out of production: append to `.gitignore`
  before deploy (wrangler respects it).

## 3. Secrets: printf, then REDEPLOY

```bash
TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' ~/.hermes/.env | head -1 | cut -d= -f2-)
printf '%s' "$TOKEN" | npx wrangler pages secret put TELEGRAM_BOT_TOKEN --project-name <project>
printf '%s' "8843884232" | npx wrangler pages secret put TELEGRAM_CHAT_ID --project-name <project>
```
- **`echo` adds a trailing newline → corrupts the secret** (or at least risks
  it). Always `printf '%s'`.
- **After setting secrets, `wrangler pages deploy` AGAIN.** The first
  post-secret lead test may fail with `{"ok":false,"error":"Telegram send
  failed: Not Found"}` even with a valid token — that's deploy propagation
  delay, not a bad token. Verify the token independently first:
  `curl -s "https://api.telegram.org/bot${TOKEN}/getMe"` → `{"ok":true,...}`
  then redeploy and re-test the function.

## 4. Debugging secrets on production (masked echo)

Temporary Pages Function to see what Cloudflare actually holds (masks values,
deploy, curl, then DELETE + redeploy):

```js
// functions/api/dbg.js
export async function onRequest({ env }) {
  const mask = (s) => s ? `len=${s.length} head=${s.slice(0,6)} tail=${s.slice(-4)}` : "UNDEFINED";
  return new Response(JSON.stringify({ bot: mask(env.TELEGRAM_BOT_TOKEN), chat: mask(env.TELEGRAM_CHAT_ID) }));
}
```
`curl https://<project>.pages.dev/api/dbg` → compare head/tail against the
local `.env` value. Remove the file and redeploy when done.

## 5. Lead form test

```bash
curl -s -X POST https://<project>.pages.dev/api/lead \
  -H "Content-Type: application/json" \
  -d '{"name":"T","email":"t@t.com","phone":"123","country":"PK","interest":"FMS-1650","message":"test"}'
```
Field names must match `functions/api/lead.js` exactly — it's `interest`,
NOT `product` (`{"ok":false,"error":"Required fields missing"}`).
Success = `{"ok":true}` (Telegram message sent to chat 8843884232).

## 6. git sync after deploy

`git add -A && git commit -m ... && git push origin master` — keeps the
GitHub-connected Pages project in sync if the user also wired the GitHub
App (auto-deploy on push).

## 7. `--branch` mismatch = silent PREVIEW deploy (root domain stays stale)

Symptom: after `wrangler pages deploy --branch main` (or any branch ≠ the
project's production branch), the **root domain `https://<project>.pages.dev/`
keeps serving the OLD content** while the branch alias
(`https://main.<project>.pages.dev/`, `https://production.<project>.pages.dev/`)
serves the NEW content. It looks like CDN cache — it is NOT. Don't chase
cache purges (Pages purge_cache endpoint returns 405; there's no CLI purge).

Diagnosis:
```bash
npx wrangler pages deployment list --project-name <project>
```
The `Environment` column shows **Production** vs **Preview** per deployment.
The root domain ONLY serves the deployment whose environment is Production.
The project's production branch was fixed at create time
(`--production-branch master`); the git repo's branch name is what matters.

Fix: deploy with the project's actual production branch:
```bash
npx wrangler pages deploy . --project-name <project> --branch master
```
then verify on the **root domain** (not the alias): the new marker must appear
at `https://<project>.pages.dev/`. Branch aliases can show new content while
root is stale — root-domain curl is the only reliable verification.
