---
name: cloudflare-pages-workers-ops
description: Cloudflare Pages/Workers & wrangler login on headless VMs.
---

# Cloudflare Pages & Workers Ops (wrangler, remote VMs)

Deploying Pages sites (`X.pages.dev`), Workers (proxies/webhooks), and handling `wrangler login` when the box is a headless/remote VM and the user is chatting remotely (Telegram).

## Auth basics

- Wrangler reads auth ONLY from `~/.wrangler/config/default.toml`. Tokens copied to `~/.config/.wrangler/...` are NOT read — copy them over if valid.
- `npx wrangler whoami` FIRST. Account email shown decides what you can touch. For Aamir: the Cloudflare account registered to **aamir1zahran@gmail.com is the MAIN deploy account** — every site project lives there (sanad-io, sanadbot, avvs-triatek, az-ebook, topmate-aamir, estelar-demo, ai-business-kit, kwacha-deals, aone-chat-site, avvs-expert-pro, open-anatomy). Do NOT chase a mythical separate "business" CF account for these sites.
- OAuth tokens expire (~days). When `whoami` errors with expired auth, re-login (below). Never commit `.wrangler/` (add to `.gitignore`).

## Remote OAuth login — the working procedure

Wrangler's `login` opens `localhost:8976` callback and has a fixed ~141s internal timeout. On a remote VM the user must approve from their own device. Verified end-to-end flow:

1. Start login as a **background process, run PLAIN** — do NOT wrap in `rtk` (rtk buffers stdout; the OAuth URL never surfaces): `npx wrangler login` (background=true, notify_on_complete=true).
2. Wait for the listener: `ss -tlnp | grep 8976`.
3. Extract the URL from the **NEWEST** log: `ls -t ~/.wrangler/logs/*.log | head -1` then grep `https://dash.cloudflare.com/oauth2/auth[^ ]*`. Each attempt mints a fresh `state` + PKCE `code_challenge`.
4. **CRITICAL PITFALL — stale URL:** every login attempt invalidates the previous one (new state + new code_challenge/verifier pair held by the live process). Sending the user a URL from an earlier attempt's log means their Allow code can NEVER validate (PKCE verifier is gone with the dead process) — you get connection-refused on curl and must restart. Always confirm the URL's `state=` matches the CURRENT live attempt (compare with the process's own printed state / newest log) before sending.
5. Send the OAuth URL to the user in chat. They open it on their own device, log in (correct account + OTP), click **Allow**, and get redirected to `http://localhost:8976/oauth/callback?...` — a connection-refused/error page is EXPECTED and fine.
6. Ask them to copy the FULL address-bar URL (starts `http://localhost:8976/oauth/callback?code=...&state=...`) and paste it back in chat.
7. Complete it on the VM: `curl "http://localhost:8976/oauth/callback?code=<exact>&state=<exact>"` → HTTP 307 = code accepted. Then poll the process: "Successfully logged in" + exit 0. Config is written to `~/.wrangler/config/default.toml`.
8. If the ~141s timeout fires before the user pastes: restart login, re-extract from the newest log, and send the NEW URL (old one is dead).

## Pages deploy (production)

```bash
cd <site-dir>                                  # the dir you deploy (e.g. landing/)
npx wrangler pages project create <name> --production-branch main   # once; reserves <name>.pages.dev globally
npx wrangler pages deploy . --project-name <name>                    # direct-upload to production
```
- Deploy output shows a hash alias URL (`<hash>.<name>.pages.dev`) — that is per-deploy; the apex `https://<name>.pages.dev` serves the production deployment.
- Verify externally: `curl -s -o /dev/null -w '%{http_code} %{size_download}' https://<name>.pages.dev/` plus key assets (PDF etc.). Compare byte size against the local file to confirm the right artifact went live (e.g. whitened PDF 458,534B).

## Workers (proxies, lead capture)

- `wrangler.toml`: `name`, `main`, `compatibility_date`, `[vars]` for non-secrets, comment that secrets go via `npx wrangler secret put <NAME>` (pipe the value on stdin — never as an argv).
- Deploy: `npx wrangler deploy` in the worker dir.
- Landing-page → Worker → Notion lead capture pattern: see `references/lead-capture-notion-worker.md`.
- KV write budget — the 1,000-writes/day free tier is **account-wide**, so one noisy Worker/pageview
  tracker 429s every other Worker on the account. Attribute the top writer (local grep finds nothing:
  binding names live in the deployed bundle), fix write amplification (diff-before-write, capped
  counters, 1 put/pageview, drop write-only keys — deletes refund nothing), and stage client-facing
  changes for approval: see `references/kv-write-budget-attribution.md`. The alerting side of that
  guard (fossil alarms, slope projection) is skill `cron-watchdog`.
- Interactive 3D education app on Pages (Open Anatomy — cache-bust pitfall, fact-overlay UX, mobile credit-strip attribution, CDP mobile viewport testing, deploy+verify loop, gh private→public quirk): see `references/open-anatomy-pages-ops.md`.
- Open Anatomy product/market audit + competitor benchmark + 90-day roadmap (top-10 changes by impact×feasibility, positioning verdict, phases 1–4): see `references/open-anatomy-market-audit.md`.

## Git hygiene before public push

- `.gitignore` MUST exclude `.wrangler/` and any stale/superseded artifacts (keep them on disk, out of the repo).
- Secret-scan the repo before first push (`grep -rilE 'sk-|gho_|AKIA|api_key|secret|password|BEGIN .*PRIVATE'`).
- One clean initial commit, then `gh repo create <owner>/<name> --public --source=. --remote=origin --push --description "..."`; verify raw file URLs return 200.

## Client-site landing behavior (owner expectation — learned 2026-09-07)

Aamir's rule for ANY client site: **a pasted/shared link must open the FIRST
page (the landing/home experience)** — "link open pe first page ana chahiye".
Consequences for feature work:
- Do NOT ship self-initiated deep-nav features that skip the landing on fresh
  open (e.g. `?bone=ulna` auto-opening a detail card instead of home). Roadmap
  ideas are proposals; UX-changing behavior ships only with explicit sign-off.
- Address-bar URL sync (pushState/replaceState) turns every mid-session copy
  into a deep link — recipients no longer see the landing page. If shared links
  must land home, keep params out of the URL or make them landing-safe
  (language only: `?lang=ar` → localized FIRST page is fine).
- Pushback "fix karo or previous version kardo" = revert the BEHAVIOR to the
  prior experience (not necessarily git revert), then verify the landing
  matrix (root / each old param / lang variant → landing state, 0 console
  errors) before reporting done.

## Pitfalls recap

- Stale OAuth URL from an old attempt = wasted user action + timeout (the #1 time sink).
- rtk wrapper hides login stdout — run wrangler plain for interactive flows.
- Expired OAuth looks like empty whoami output — re-login, don't guess from old tokens.
- Pages project names are globally unique; if `create` errors "already in use", the name is owned by another account — reconcile with the user before deploying.
- Never put Cloudflare or Notion tokens inside committed files or client-side JS.
