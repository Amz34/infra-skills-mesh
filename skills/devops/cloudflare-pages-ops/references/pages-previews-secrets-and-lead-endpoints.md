# Pages preview branches, env secrets, and lead endpoints

Verified on the `az-consultants` project (AZ Consultants tender-advisory site, Sep 2026).

## 1. Branch → URL mapping (this is the approval mechanism)

```bash
wrangler pages deploy . --project-name <proj> --branch main        # -> https://<proj>.pages.dev  (PRODUCTION)
wrangler pages deploy . --project-name <proj> --branch preview-zai # -> https://preview-zai.<proj>.pages.dev
```

Any non-`main` branch name produces its own preview host `<branch>.<proj>.pages.dev`.
So a design A/B comparison needs no extra infra: build each variant in its own
directory (`site/`, `site_v2/`), deploy each on a distinct `preview-*` branch, and
send the user the two URLs + screenshots. Production is only touched on `--branch main`.

Approval flow used (respects "no prod deploy without approval"):
1. Variant A deployed on `main` (or kept as-is on `main`), variant B on `preview-<name>`.
2. Screenshot both (`chrome --headless=new --screenshot=... --window-size=1440,1150 --virtual-time-budget=9000`).
3. User picks; winner re-deployed with `--branch main`; rollback = redeploy the previous directory on `main`.

`site_vN/` directories and the "keep the old page as `funnel.html`" trick give an instant
second preview without touching the live page.

## 2. Each branch deploy is a FULL snapshot

A deployment only serves the files present in the directory you deployed. Assets or
secondary pages that live on another branch are NOT inherited. Before deploying a
variant directory, copy in everything it needs:

```bash
cp -r site/functions site_v2/        # so /api/* works on the preview host
cp site/funnel.html site_v2/funnel.html
```

## 3. Secrets: production vs preview, and the redeploy gotcha

```bash
echo "$VALUE" | npx wrangler pages secret put KEY --project-name <proj>                  # production env
echo "$VALUE" | npx wrangler pages secret put KEY --project-name <proj> --env preview    # preview env
```

**Preview-env secrets bind only to NEW deployments.** Symptom seen: the preview host's
function kept returning `{"ok":true,"delivered":{}}` (i.e. env var undefined) after
`secret put ... --env preview`; a fresh `wrangler pages deploy . --branch preview-zai`
made Telegram delivery work immediately. Always redeploy the branch after setting a secret.

Never let a secret value reach stdout/chat — pipe it straight from its source file:

```python
# get_tg_token.py  (reads ~/.hermes/.env, prints ONLY to the pipe)
for line in open('/home/ubuntu/.hermes/.env'):
    if line.startswith('TELEGRAM_BOT_TOKEN'):
        print(line.split('=', 1)[1].strip().strip('"').strip("'"))
```
```bash
python3 get_tg_token.py | npx wrangler pages secret put TG_TOKEN --project-name <proj>
```

## 4. Lead-capture endpoint (monetization pattern, no backend server)

`functions/api/<name>.js` inside the deployed directory becomes `POST /api/<name>`.
Shape used for a lead form that alerts the owner on Telegram:

- `export async function onRequestPost({ request, env })`, `await request.json()`.
- Drop bots silently: if the honeypot field (`hp`) is non-empty, return `{ok:true}` without sending.
- Send: `https://api.telegram.org/bot${env.TG_TOKEN}/sendMessage` with `chat_id: env.TG_CHAT`, plain-text body of name/firm/email/phone/discipline/tender.
- Always return JSON `{ok:true, delivered:{telegram:true|false}}` so the caller can verify the path end-to-end.
- Smoke-test after every deploy (a real test message lands in the owner's Telegram — that IS the proof):
  `curl -s -X POST https://<host>/api/lead -H 'Content-Type: application/json' -d '{"name":"QA","firm":"QA","email":"qa@example.com","scope":"FM","tender":"smoke test"}'`
  `{"ok":true,"delivered":{"telegram":true}}` = wired correctly.

## 5. Other Pages behaviours worth remembering

- **`.html` 308-redirects to the extensionless path** (default `html_handling`): link
  `/funnel`, not `/funnel.html`. `curl -o /dev/null -w "%{http_code}"` on `/funnel.html`
  returns 308, on `/funnel` returns 200 — not an error, but don't put the `.html` form in copy.
- Post-deploy check in one line: index, sub-page, and assets, e.g.
  `for p in / /funnel /assets/site.css; do curl -s -o /dev/null -w "$p %{http_code}\n" https://<host>$p; done`
- Mobile sanity check without a vision model: same headless `--screenshot` with `--window-size=390,1500`
  (a non-trivial file size means the layout rendered, no horizontal-scroll blowout proof needed).
