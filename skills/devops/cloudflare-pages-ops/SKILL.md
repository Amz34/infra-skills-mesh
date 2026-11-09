---
name: cloudflare-pages-ops
description: "Deploy/manage Cloudflare Pages + Workers via wrangler CLI."
version: 1.0.0
author: hermes
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [cloudflare, pages, workers, wrangler, deploy, hosting]
---

# Cloudflare Pages & Workers Ops (wrangler)

## When to Use

Deploying a new site to CF Pages, re-deploying after edits, wrangler auth needed on a headless VM, adding a CF Worker with secrets, or answering "list all our live websites" — use this skill first.

Static client-site deploys on CF Pages (free tier) + small Workers (lead-capture beacons, redirects). Aamir's main deploy account: `aamir1zahran@gmail.com` (OAuth creds at `~/.wrangler/config/default.toml` — ALL client sites live here). Workers land on `*.sanad-io.workers.dev` (account Pages namespace). Project name → `https://<name>.pages.dev` (lowercase, dashes).

## Fresh deploy (already-authenticated)

```bash
cd <site-dir>                       # static files (index.html + assets) at root
npx wrangler pages project create <name> --production-branch main
npx wrangler pages deploy . --project-name <name>
curl -s -o /dev/null -w "%{http_code}\n" https://<name>.pages.dev/   # expect 200
```
- Re-deploy after edits: just `npx wrangler pages deploy . --project-name <name>`.
- **A read-only `CLOUDFLARE_API_TOKEN` in the environment SHADOWS the OAuth login** — wrangler
  prefers the env var over `~/.wrangler/config/default.toml`, so a fully logged-in account fails
  `pages project create` / `deploy` with an auth/`code: 10000` style error and it looks like the
  OAuth session died. Fix: run the command with the token unset (it is the vault `infra` token,
  account-read only):

  ```bash
  env | grep -o '^CLOUDFLARE[A-Z_]*'                      # see which vars are set (never echo values)
  env -u CLOUDFLARE_API_TOKEN npx --yes wrangler@3 whoami  # confirm the OAuth email
  env -u CLOUDFLARE_API_TOKEN npx --yes wrangler@3 pages project create <name> --production-branch main
  env -u CLOUDFLARE_API_TOKEN npx --yes wrangler@3 pages deploy . --project-name <name>
  ```

  Verify a fresh project is live with `curl https://<name>.pages.dev/` (deployment hash URL is
  authoritative instantly; the alias can lag — see TLS/alias notes below).
- Verify prod AFTER redeploy: curl the live root AND one asset (root may be cached; assets/ check catches stale deploys).
- **Alias domain lags the new deploy by up to ~a minute** (edge propagation) — a curl or headless-browser check run immediately after `deploy` can still get the OLD index.html while the deployment preview URL (`<hash>.<name>.pages.dev`) already serves the new one. When the first post-deploy check fails, do NOT assume the deploy broke: 1) curl the deployment preview URL (authoritative instantly), 2) re-fetch the alias with a cache-buster query (`curl 'https://<name>.pages.dev/?cb=NNNN'`), 3) retry after ~30–60s. Browser tests that load the old HTML also silently run the old JS — a feature "not working" on prod right after deploy is usually this race, not a code bug.

## Redeploy pitfalls (production vs preview)

- **Production branch may NOT be `main`** — an earlier `project create` may have set `--production-branch master` (e.g. AVVS `avvs-triatek` runs on `master`). Deploying with `--branch main` on such a project creates a PREVIEW deployment at `main.<name>.pages.dev` while the root domain keeps OLD content (a "deploy succeeded" message can still leave prod untouched!). ALWAYS check first: `npx wrangler pages deployment list --project-name <name>` → inspect the Environment column (Production vs Preview) + branch shown. Deploy with `--branch <actual-prod-branch>`, then curl the ROOT domain (never the hash/`main.` subdomain) to confirm the change is live.
- **Local folder may be STALE vs live** — the local source dir can hold an old design while live has newer sections, JS files, or `style.css?v=N` bumps. A naive `wrangler pages deploy .` would REVERT the live site. Before any edit-deploy: fetch live HTML (`curl -sL`) and compare section markers / asset version refs / JS file list against local. If they differ, build the deploy dir from the LIVE snapshot + apply only the intended edit (see `references/contact-number-swap-multisite.md`).
- **curl 200 ≠ file exists** — CF Pages projects can SPA-fallback: any missing path (`/ar/`, `/_redirects`, `/old-file.js`) returns 200 with the index.html body. Never infer the deployed file set from curl status codes — pull the real file manifest from the CF API deployment `files` dict instead.
- **Cache-bust static assets, NEVER the service-worker URL** — bump `?v=N` on html/js/css/json refs when content changes, but register the SW at a PLAIN path (`navigator.serviceWorker.register('sw.js')`): a versioned SW URL (`sw.js?v=N`) is treated as a DIFFERENT worker, so the old one keeps controlling the page and update checks break. Put the version in the SW's cache NAME (`open-anatomy-v<N>`) and let it prune the old cache — the plain path is re-checked by the browser on every navigation. Cache-first static + network-first HTML is the proven combo; post-deploy stale-JS reports right after a push are usually SW cache or alias-propagation lag, not a bad deploy — verify with `Network.clearBrowserCache` + fresh tab.
- **`.html` URLs 308-redirect** to clean URLs on CF Pages — python `urllib` fetches need an `HTTPRedirectHandler` subclass; curl needs `-L`.
- CF API deployment file hashes are an internal format, NOT md5/sha of served bytes — do not hash-assert downloaded content against the manifest.

## Preview-before-prod review gate (user must approve before prod)

Aamir rule: never push prod before the user reviews a working preview link.
Deliberate preview deploy (production branch UNTOUCHED):
```bash
npx wrangler pages deploy public --project-name <name> --branch preview-<tag>
# -> https://<hash>.<name>.pages.dev  (+ alias https://preview-<tag>.<name>.pages.dev)
```
- Verify the PREVIEW serves the intended bytes BEFORE handing over the link: `curl -sL <preview>/<file> | sha256sum` vs `sha256sum <local-file>` for EVERY asset (index.html, js, json, css). Sizes matching is NOT proof — same-size byte rewrites happen; hash-match all files is the pass bar. Preview `<hash>.<name>.pages.dev/<file>.html` 308-redirects to the clean URL (`/embed-demo.html` → `/embed-demo`) — curl needs `-L`; python `urllib` gets **403** on some projects without a browser UA (`urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})`).
- Prod-untouched evidence: capture prod's file sizes BEFORE and AFTER the preview deploy and state explicitly they didn't change.
- After user approves: deploy with the actual production branch (check `npx wrangler pages deployment list --project-name <name>` Environment column first — do not assume `main`).
- **Prod push on a `main`-production project = plain deploy, NO `--branch`**: `npx wrangler pages deploy public --project-name <name>` targets the production branch; `--branch` is only for preview deploys.
- **"Uploaded 0 files (N already uploaded)" is SUCCESS, not a no-op failure** — wrangler dedupes by content hash, and when prod content is byte-identical to what the preview deploy already pushed, the prod push uploads nothing yet still creates a NEW live deployment (grab the fresh deployment ID from output). Verify by fetching the origin, never by uploaded-file count.
- **Post-prod-push verification bar:** 1) curl live root → 200 AND contains the NEW cache-bust refs (`grep -o 'v=…'`); 2) served data JSONs parse with expected counts — inspect top-level keys first (a wrong key guess like `items` vs actual `organs` returns 0/0 and looks like a broken deploy); 3) run the app-level QA driver against the LIVE origin URL (not localhost) for the user flow that matters.

## Fresh project: the first deploy has a TLS provisioning gap

A hostname that has never been served before (`<hash>.<name>.pages.dev` AND its
`preview-<tag>.<name>.pages.dev` alias) can fail TLS for the first ~1–3 minutes after
`project create` + first `deploy`:

```
curl: (35) OpenSSL ... error:0A000410:SSL routines::sslv3 alert handshake failure   -> code=000
```

DNS resolves fine and an ESTABLISHED project (use one as a control host) returns 200 in the same
second — so this is edge cert/SNI provisioning for the new name, **not** a broken deploy, a bad
project, or a network fault. Do NOT re-deploy, re-create the project, or report failure; poll:

```bash
for i in $(seq 1 14); do
  C=$(curl -4 -s -o /tmp/p.html -w "%{http_code}" --max-time 25 "$URL" 2>/dev/null || echo 000)
  [ "$C" = "200" ] && break; sleep 30
done
```

Observed live on try 4 (~90s). `scripts/verify_pages_deploy.sh` wraps the poll + full verification.
Note on `-4`: it is worth forcing IPv4 for these probes — the v6 path returned 000 even after the
v4 path was serving 200.

A fresh project with **no production deployment yet returns 404 on the root** — when the preview
gate below is in play that 404 IS the "prod untouched" evidence. State it as proof, don't treat it
as an error or try to "fix" it.

## Verifying a static mirror after deploy (beyond hash-compare)

For a content/landing deliverable, hash parity is necessary but not sufficient — assert what the
RENDERED DOM says, and that forbidden strings are ABSENT (brand isolation, no leaked contacts):

```bash
google-chrome-stable --headless=new --disable-gpu --no-sandbox --virtual-time-budget=6000 \
  --dump-dom "$URL" > /tmp/dom.html
grep -c "<expected heading>" /tmp/dom.html                        # >= 1 for every section you claim
grep -ci -e 'HMW' -e '<other-brand>' -e '@gmail' -e '+91' /tmp/dom.html   # MUST be 0
```

Count embedded links in the SERVED bytes and cross-check against the source dataset — a mirror of
a Notion page must match it exactly (e.g. 154 `href` occurrences, 144 unique). Emojis/section icons
live inside the Notion build, so grep the DOM for `<b>36</b>`-style split markup rather than a
phrase like "36 states" — tag-split text legitimately returns 0 phrase hits.

**Preview screenshots for a non-technical reviewer:** the chrome CLI cannot scroll, but it DOES
honour URL fragments, so `--window-size=1400,1800 --screenshot=out.png "$URL#section-id"` captures
that section on load. Render hero + 2–3 `#anchor` shots instead of one 6000px-tall image (illegible
after chat compression). A full-page PNG of only ~35–40KB is a blank/error render — real content
comes out 300KB+.
**When `--screenshot` keeps producing a blank 5–16KB PNG** (seen on a tall Arabic/RTL page while the
same CLI rendered the LTR pages fine), stop retrying it and render to PDF instead — it paginates,
applies web fonts, and honours fragments:
`google-chrome --headless=new --no-pdf-header-footer --virtual-time-budget=8000 --print-to-pdf=/tmp/p.pdf "$URL"` then `pdftoppm -png -r 80 /tmp/p.pdf /tmp/pg`, and pick the page that shows the section you need.

## Hardening + redirect hygiene for a client Pages site (do this on every property)

Drop this in `public/_headers` next to the cache rules and redeploy (preview branch first, then `main`):

```
/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: SAMEORIGIN
  Strict-Transport-Security: max-age=31536000; includeSubDomains
  Permissions-Policy: accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()
  Content-Security-Policy: default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'self'; form-action 'self' <external-form-host>; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; media-src 'self'; manifest-src 'self'; worker-src 'none'; upgrade-insecure-requests
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Resource-Policy: same-origin
  X-Permitted-Cross-Domain-Policies: none
  X-XSS-Protection: 0
```

Adapt before shipping:
- Count `style=` attribute uses (`grep -c 'style=' *.html`). Any > 0 → CSP needs `style-src 'self' 'unsafe-inline'` (inline style attributes are blocked without it, page renders unstyled).
- Only keep `script-src 'self'` strict once `grep -n '\son[a-z]\+=' *.html *.js` returns nothing (no inline handlers) and every `<script>` has `src=`.
- `form-action` must list every external form host the pages POST to (`formsubmit.co`, etc.) or the enquiry form breaks silently.
- After deploy, confirm nothing got blocked: in a real browser check `document.styleSheets.length > 0` AND `document.fonts.size > 0`. Blocked CSS/webfonts = unstyled page.

Redirect hygiene — check every hop, not just the final URL:
- Probe the chain with redirects DISABLED and print each hop, for `/`, `/index.html`, `/ar.html`, `/ar/`, `/en`, and a junk path.
- **A `_redirects` rule whose target has no file on disk is a 301→404 for visitors.** Seen live: `/ar.html /ar 301` kept while `ar.html` was never deployed → every visit to the Arabic edition landed on the branded 404. Fix by shipping the target page or deleting the rule — never leave it.
- Trailing-slash + `.html` forms should each collapse to one canonical URL (`/ar.html` and `/ar/` → `/ar` 301), and `/index.html` → `/` 301.
- Every `<loc>` in `sitemap.xml` must return 200; hreflang alternates must be reciprocal and only on pages that genuinely exist in both languages. A sitemap listing a 404 is a Search Console error and reads as broken.

**Probe with a real browser User-Agent or you will misdiagnose a healthy site.** Cloudflare's bot rules return `403 Forbidden` (empty body) to `Python-urllib/3.x` on every path of a `*.pages.dev` host. Seen live: `403` on `/`, `/robots.txt`, everything — the site was perfectly fine in a browser. Always send a Mozilla UA (and `Accept`/`Accept-Language`) in verification scripts.

**The browser-use harness prepends a `🐴` marker to `document.title`** in its automation tab. It is NOT a site defect — confirm titles with a plain HTTP fetch before reporting an emoji/garble in the page title.

## Same-origin form endpoint (Pages Function) - kills the third-party form service

Replace `formsubmit.co`/Formspree/Netlify-style form actions with `functions/api/enquiry.js` so visitor data never leaves your own origin. Then CSP can be `form-action 'self'` (no external form host to allow, and the visitor never sees an activation/interstitial page). Pitfalls, all hit for real:

- **`functions/` is discovered from the CWD, not from the deploy directory.** `cd <site-dir> && wrangler pages deploy public --project-name=X` ships the Function; running the same command from the parent repo dir silently ships **no** functions and `POST /api/enquiry` answers **405** (looks like a method mismatch, isn't). Verify with `GET /api/enquiry` -> your Function's redirect, then `POST` -> expect `303` to the thanks page.
- **`wrangler pages secret put` only populates the production environment.** Preview deployments (`--branch=review`) do NOT get those secrets, so a form tested on a preview URL falls into the error path. Verify the real send on a production deployment.
- **Make failure loud.** Return an error redirect (`?err=1` back to the contact page) when secrets are missing OR the upstream API returns non-2xx - a missing secret must never look like a successful submission.
- **Surface the error client-side in a self-hosted `app.js`** (inline `<script>` is blocked by the hardened CSP): read `location.search`, insert a `role="alert"` notice before the form. Style with logical properties (`border-inline-start`) so RTL is correct.
- **Guard the redirect target**: only accept `next` values starting with `/` (open-redirect), and allowlist any `market`/`tag` field before echoing it into the alert message.
- `/ar.html` and other language forms need their own error page (`/ar.html?err=1`) - branch on the submitted `next` prefix.

## Generated sites: the build script owns `_headers` / `_redirects` / SEO files

If the site is produced by a generator (`build/sites.py` writing `public/*.html`, `build/extras.py`
writing `_headers`, `_redirects`, `sitemap.xml`, `robots.txt`, `404.html`), then hand-patched
infrastructure files are **not durable**: the next rebuild silently reverts every security header,
redirect rule and form action to whatever the generator still emits. Seen live: a fully hardened
`_headers` and a same-origin form endpoint were both stamped out by one `python3 sites.py` run,
because `sites.py` still held `FORM_ACTION = "https://formsubmit.co/..."` and `extras.py` still wrote
the old 4-header block. Any "the site regressed after a content edit" report is usually this.

Rule: **patch the generator, then prove it reproduces the shipped file byte-for-byte.**

**Generator source lines are escaping minefields — read the raw bytes before patching.** Copy strings
inside `_headers`/`_redirects`/CSS emitters are full of `\"`, `\n` and `\n  ` sequences, so a
patch target pasted from a rendered read tool either misses or matches the wrong region. Before a
targeted patch, print the exact lines:
```bash
python3 -c "print(repr(open('build/extras.py').read().splitlines()[N-1]))"
```
then use that repr'd string (backslashes intact) as the patch target; for multi-line refactors write
a small idempotent rewrite script instead of chaining patches. After ANY generator edit, re-run the
builder and diff `public/` against the pre-rebuild snapshot — a silent reversion is otherwise
invisible until a visitor hits the un-hardened page.

```bash
tar czf /tmp/pre_rebuild_snapshot.tgz <siteA>/public <siteB>/public   # snapshot BEFORE editing
cd <site-dir>/build && python3 sites.py                               # regenerate
cd <repo> && diff -rq /tmp/pre_<ts>/<siteA>/public <siteA>/public     # intended files only
diff /tmp/pre_<ts>/<siteA>/public/_headers <siteA>/public/_headers    # MUST be empty
grep -rc formsubmit <siteA>/public <siteB>/public | grep -v ':0' || echo clean
```
Then redeploy prod from the SITE dir (Functions are discovered from CWD) and re-run the live header /
hop-by-hop / form-post checks — generator output is what visitors now get.

Conditional infrastructure the generator must emit **per site**, not globally:
- Emit `/ar.html → /ar` redirects AND hreflang alternates only when `ar.html` is in the page set
  (`if name in ("index.html", "ar.html") and "ar.html" in names:`). A bilingual pair shipped on one
  market site but not the other otherwise produces a 301→404 and a false hreflang.
- Build the 404 page's nav from pages that exist on disk. Watch extension-less targets: `"/ar"` must be
  tested as `"ar.html" in names`, never `os.path.exists(out_dir + "/ar")` — that is False and the
  العربية link silently disappears.

**The generator usually owns the cached-asset headers too — that is what makes a fix look like it
failed.** `extras.py`-style writers default to `Cache-Control: max-age=604800` on `/*.css` and
`/*.js`. A re-deploy reuses the same filenames, so browsers (and headless checks) keep serving the
OLD stylesheet for a week while the HTML is brand new — seen live: a layout/nav polish fix appeared
not to apply on the live preview even after two successful deploys. Fix it in the generator: emit a
short TTL for CSS/JS (`max-age=600, must-revalidate`) or bump `?v=N` on every rebuild, and re-verify
with `Network.setCacheDisabled` (or a `?cb=<ts>` query) before declaring anything broken.

**Assert headers case-insensitively.** Served header names come back in differing case, so
`'Content-Security-Policy' in headers` reports a perfectly live CSP as missing while an
uppercase-checked HSTS passes — normalise with `{k.lower(): v for k, v in resp.headers.items()}` and
dump the whole dict before declaring any header absent.

Detail + the merge-two-market-sites-into-one-property playbook: `references/generator-owned-site-infra.md`;
merged single-property market-tab build (hero tabs, market-tabbed data board, verification
assertions): `references/merged-multi-market-property.md`.

## Decommissioning a project (delete a live site + its local files)

Trigger: "ye website undeploy + delete kardo", "project hata do". Irreversible, and usually has
live dependents — treat it as a 5-phase job, never one delete command.

1. **Confirm scope BEFORE deleting.** One batched clarify: just this Pages project? sibling
   projects too? local files? State explicitly what you will KEEP. Users say "delete the project"
   and mean only the project — never infer the rest, and never delete a dir wired to running
   automation on your own initiative.
2. **Recon for live dependents** — a production site is often the working dir of scheduled
   automation, and a project usually has siblings:
   ```bash
   npx wrangler pages project list                      # siblings exist! do not assume one project
   grep -rl "<project-dir>\|<domain>" ~/.config/systemd/user/ ~/.hermes/scripts/ ~/.hermes/cron/ 2>/dev/null
   systemctl --user list-timers --all | grep <campaign>
   ```
   Any hit = that automation survives the delete → flag it to the user, keep the files it needs
   (e.g. an `outreach/` dir with 2 pending waves inside the site's own folder).
3. **Backup, then delete.**
   ```bash
   tar czf ~/backups/<name>_$(date +%Y%m%d_%H%M).tar.gz -C /home/ubuntu <name>
   npx wrangler pages project delete <name>       # interactive confirm; check --help for -y/--yes
   ```
   Report backup size + file count so the restore path is real. Verify death from DNS, not the
   dashboard: `dig +short <name>.pages.dev` empty and `curl` → 000.
4. **Local cleanup — delete narrowly, report exactly.** Build an explicit keep-set
   (`outreach/`, `credentials/`, `.wrangler`), delete the rest, and print
   `DELETED n items, freed X MB, errors: none`.
5. **Repair references the delete just broke** — the step everyone forgets. Deleted URLs are
   hardcoded in campaign templates and generated attachments, and surviving scripts may read
   deleted data files. Grep the WHOLE tree (text, **inside xlsx via `zipfile`**, stale
   `__pycache__`), fix the source-of-truth template, rebuild generated artifacts, re-grep to 0 hits.
   Missing data file? Restore just that path:
   `tar xzf ~/backups/<ts>.tar.gz -C /home/ubuntu <name>/<file>`.
   Two things a 0-hit grep does NOT prove: **(a)** the replacement page actually contains what any
   surviving copy promises (a 200 on the new URL is not a content match — grep the claim words), and
   **(b)** every *fulfilment* asset the copy promises to send on request still exists on disk
   (often it lived under the deleted tree; restore it from the tar and prove it is self-contained).
   Campaign-side detail: skill `cold-email-campaign-ops` §1e.

Full worked case (what broke, exact commands, verification lines):
`references/site-decommission-and-reference-repair.md`.

## Remote OAuth login (headless VM — the hard part)

`wrangler login` needs a browser; on a headless VM run it in the BACKGROUND and hand the user the URL:

1. `terminal(background=true)`: `cd ~ && npx wrangler login` — prints a `https://dash.cloudflare.com/oauth2/auth?...state=...` URL, then waits ~2.5 min for the callback.
2. Send the user the FRESH URL (each attempt has its own state; an old attempt's URL is dead).
3. User opens it, clicks **Allow**, browser redirects to `localhost:8976/oauth/callback?code=...`. User pastes that full callback URL back into chat.
4. On the VM: `curl -v "<pasted-callback-url>"` → **HTTP 307 = success**; background login exits 0 and writes `~/.wrangler/config/default.toml`.
5. Verify: `npx wrangler whoami` → account email matches expected.

Pitfalls:
- **~2.5-minute window** — expired code gives HTTP 000 / curl exit 7. Never reuse an old URL: start a fresh attempt (new state) and resend.
- If whoami shows an email you think is a "testing" account: run `wrangler pages project list` and compare project names against known client sites before concluding — the main account hosts everything.

## Worker with secrets (lead-capture pattern)

```bash
# wrangler.toml has name + main entry; then:
printf '<secret-value>' | npx wrangler secret put MY_SECRET     # one line, no trailing newline
npx wrangler deploy                                              # -> https://<name>.<pages-project>.workers.dev
```
- Landing pages POST to the worker as a silent beacon — NEVER put the secret in client HTML; the worker holds it.

### Pages Functions with secrets (prefer this over a separate Worker)

A static site can carry its own API: put `functions/api/<name>.js` (exporting `onRequestPost`) inside
the deploy dir — it uploads with the site and serves at `/api/<name>`. No worker project needed.

- Secrets go on the PAGES project: `printf '<value>' | npx wrangler pages secret put TG_TOKEN --project-name <name>`.
  Pipe the value from wherever it lives (`python3 get_token.py | npx wrangler pages secret put ...`) and
  **never echo it** — the success line is the only output you need.
- **Pages secrets are PER-ENVIRONMENT.** `secret put` targets the production environment, so a
  preview-branch deployment does not see them: the same form can work on prod and silently
  no-op (`{ok:true, delivered:{telegram:false}}`) on `--branch preview-<tag>`. Test on the environment
  you are about to hand over, and promote with the real production branch before promising alerts.
- A Function returning 200/`ok:true` is NOT proof of delivery — assert the downstream flag from a real
  POST (`curl -X POST .../api/lead -d '{...}'` → `delivered.telegram true`).
- Worked example (landing page + lead form → Telegram, clean-URL gating, hero-canvas verification):
  `client-deliverable-patterns/references/monetizing-landing-page.md`.

## Custom domains, zones & Email Routing (mail for a site)

- **Creating a new zone is NOT scriptable with the CLI OAuth token.** A typical `wrangler whoami`
  scope set is `zone:read`, `email_routing:write`, `email_sending:write` — so `POST /v1/zones`
  returns 403 and an "Add a site" click in the dashboard (or a purpose-made token with `Zone:Edit`)
  is required. Read the real scope list with `npx wrangler whoami` BEFORE promising an end-to-end
  autonomous setup, and tell the user exactly which single step needs them.
- **Email Routing (free, forwarding-only) IS scriptable**: `npx wrangler email routing
  settings|addresses|rules` (plus the separate `email sending` product). Destination addresses must
  have their verification email clicked — if the agent can read that inbox, it can finish the setup
  alone. Forwarding gives no mailbox and no ability to send *as* the domain; say so before building.

  **Verified API path (2026-09, new domain wired end-to-end)** — the sequence is 3 API calls + 1 user
  click, and the two failure modes below are the whole reason this section exists:
  - `POST /zones/<zone>/email/routing/dns` (enable) **auto-creates MX + SPF** — confirm with
    `dig +short MX <d>` → `route1/2/3.mx.cloudflare.net` and `dig +short TXT <d>` →
    `v=spf1 include:_spf.mx.cloudflare.net ~all`. A freshly registered domain therefore *receives*
    mail before any mailbox exists.
  - `POST /accounts/<acct>/email/routing/addresses` (destination) → CF mails a tokenised verify link
    `https://dash.cloudflare.com/email_fwdr/verify?token=…`. That landing page sits behind
    **Cloudflare Turnstile**, which a headless browser cannot complete (verified: a JS click and a
    coordinate click both left the box unchecked, and the widget lives in a frame the page JS cannot
    enumerate). Extract the link from the inbox (`himalaya` raw read + regex for
    `email_fwdr/verify\?token=…`) and hand it to the user — **no login required, 5-second click**.
    The same link is one-time and belongs to the destination mailbox, so agent-side inbox access is
    what makes this finishable at all.
  - `POST /zones/<zone>/email/routing/rules` **before** the destination is verified → **error 2054**
    ("destination address must be verified"). Order: enable → add destination → user clicks → create rule.
  - **Receiving is proven only by a test message actually seen in the destination inbox, and the first
    test may bounce.** A brand-new domain's first send can fail `550 5.1.1 Address does not exist`
    purely from the sending MTA's cached no-MX state; the DSN lands in the *sender's* inbox, so
    "destination shows nothing" ≠ dead rule. Read the DSN, re-`dig` MX, re-send (full diagnosis:
    `references/pages-custom-domain-email-routing-api.md` §2b).
- **A Pages custom domain added via API does NOT create its DNS records.** `POST
  /accounts/<acct>/pages/projects/<proj>/domains {"name":"example.com"}` returns success, then the
  domain sits at `status: pending` indefinitely (polled 6 × 30 s) while `curl https://<domain>` returns
  `000`; the **dashboard** flow is the one that offers to add `CNAME @ → <proj>.pages.dev` for you.
  Auto-create needs a token with `Zone → DNS → Edit`; otherwise the user adds two proxied CNAMEs
  (`@` and `www` → `<proj>.pages.dev`) in the zone's DNS tab, or mints a DNS-Edit token. Because
  Email Routing's MX/SPF *do* get created automatically, "mail live / website 000" is a normal split
  state — check `dig` **and** `curl` separately instead of reporting the wiring as one thing.
- **Probe credential scopes before promising autonomy.** Two credentials usually exist and they are
  not interchangeable:

  | Credential | Pages edit | DNS write | Email Routing | Registrar |
  |---|---|---|---|---|
  | `vault`-stored API token (space `infra`) | ✅ | ❌ 403 | ❌ 403 | ❌ 403 code 10000 |
  | wrangler OAuth (`~/.wrangler/config/default.toml`) | ✅ | ❌ | ✅ | ❌ |

  Probe with small scripts (`printf … > p.sh; bash p.sh > /tmp/p.txt 2>&1; wc -c < /tmp/p.txt`, then
  read the file) — long inline command payloads get blocked or elided, and a probe that prints nothing
  looks identical to a probe that failed. Never echo the token value into the probe output.
- Exact endpoint sequence, error codes and the probe scripts:
  `references/pages-custom-domain-email-routing-api.md`.
- **Subdomain zones can hang forever** in "Pending Nameserver Update" because Cloudflare watches the
  **parent** domain's NS. If the parent is not in the account, do not build a site or mail setup that
  depends on that zone activating.
- Pointing a Pages project at a domain/subdomain whose DNS lives elsewhere: add the custom domain on
  the Pages project and let CF verify through the existing CNAME — no zone on our account needed.
- Full decision matrix (free subdomain hosts vs paid), record sets, and the mailbox recipes:
  skill `domain-email-provisioning` (`references/cloudflare-email-routing-cli.md`).

## Inventory / "all websites" checks

```bash
npx wrangler pages project list          # CF-hosted sites + their accounts
gh api user/repos --paginate | jq -r '.[].homepage'   # GitHub Pages sites
```
Surge.sh demo sites (client demos, `~/clients/invertio/`) are separate — probe `curl https://<domain>/`. A project's `LIVE_URL.txt` may hold a DEAD trycloudflare tunnel link — the real surge domain lives in the `CNAME` file or deploy script. Label preview-only branches (`https://<hash>.<name>.pages.dev`) vs production before reporting "live".
