# Crashproof multi-site contact-value replacement (worked recipe)

Class of task: a contact value (phone/WhatsApp number, email) embedded across
several LIVE client sites must be replaced everywhere, with **zero other
changes** and no downtime. Verified 2026-09-03 on Sanad (`sanad-io.pages.dev`)
+ AVVS (`avvs-triatek.pages.dev`) — number swap `«OLD» → 0574268856`.

## Golden rules (learned the hard way)

1. **Backup before ANY write**: `cp -r <site-dir> ops/backups/<job>-<date>/`. Rollback is the only crashproof guarantee.
2. **Byte-exact replace, per file** — one Python pass over both trees, replacing every format variant of the old value:
   `966«OLD» | 966 «OLD» | 966-«OLD» | «OLD» | «OLD» | +966 «OLD» | 966«OLD»`
   (variant list = grep inventory first: `grep -oE '966 ?58 ?210 ?4381|...' tree/*.html`).
3. **Re-run the fix script = verification**: second run printing `TOTAL: 0 files, 0 occurrences replaced` is SUCCESS (nothing left), not failure. Do not misread it.
4. **Do NOT trust the live local folder == live site** — see stale-local trap below.
5. **Verify by old-count = 0 AND new-count > 0 on the LIVE domain after deploy** (not just locally).

## The stale-local trap (Sanad case)

`~/sanad-site` looked like the deploy source but was an OLD design: live had 5
extra sections (LIVE DEMO / REAL Q&A / CHANNELS / INDUSTRIES / FIRST WEEK),
`style.css?v=4` vs local `v=3`, and 4 JS files (script/i18n/booking/chat) vs
local 1. Deploying local would have REVERTED the live site to an old version.

Symptoms that local ≠ live:
- `curl -sL https://<site>.pages.dev/` has section markers absent locally
- asset version query strings differ (`?v=4` live vs `?v=3` local)
- local tree has dirs/files the live manifest lacks (and vice versa)

Fix: **build the deploy dir from the LIVE snapshot** — fetch the real file
list from the CF API, download each file from the live domain, apply ONLY the
intended byte-exact replace, deploy that dir.

## Getting the exact deployed file list (CF API)

```bash
# account id appears in the dashboard URL / `wrangler pages project list` output
curl -s -H "Authorization: Bearer <oauth_token from ~/.wrangler/config/default.toml>" \
  "https://api.cloudflare.com/client/v4/accounts/<ACCT>/pages/projects/<PROJECT>/deployments" \
  | jq -r '.result[0].files | keys[]'          # -> exact deployed paths
```
Then fetch each path from `https://<project>.pages.dev/<path>` (remember
`.html` URLs 308-redirect → follow redirects), replace old→new byte-exact, and
`wrangler pages deploy . --project-name <PROJECT> --branch <prod-branch>`.

Sanad live (i18n SPA design) = 14 files only: 7 root HTML pages +
`assets/css/style.css` + `assets/js/{script,i18n,booking,chat}.js` +
`package.json` + `wrangler.toml`. **No `ar/` folder** — Arabic is client-side
via i18n.js; `/ar/*` URLs 200 with index.html body (SPA fallback). A legacy
Netlify mirror (`sanad-io.netlify.app`) may run the same design separately.

## Production branch check (AVVS case)

`wrangler pages deployment list --project-name avvs-triatek` showed production
branch = `master`, NOT `main`. First deploy with `--branch main` went to a
PREVIEW URL (`main.avvs-triatek.pages.dev`) while the root domain kept the old
content. Redeploy with `--branch master` = production. Always confirm via
deployment list, then curl the ROOT domain.

## Deploy-source discovery for an unknown site

- `npx wrangler pages project list` → project name ⇒ live domain
- local source mapping: `grep -rl "<project>" ~/ops ~/.hermes/scripts` and read
  the rebuild/deploy script (e.g. `~/ops/scripts/rebuild-site.sh` may fetch
  from a Netlify mirror — check whether the CF deploy really uses the same
  source folder)
- SPA fallback: curl 200 on arbitrary paths (`/ar/`, `/_redirects`) means
  "no such file, served index.html" — do not treat as real files.

## Display-masking pitfall on this VM

Terminal output may display masked/compressed values (e.g. `tel:+966****4381`)
and collapse long outputs to "1 line". Ground truth ONLY from raw file reads:
`grep -c '\*\*\*\*' file` = 0 proves no literal asterisks in files; hexdump or
write verification results to `/tmp/*.txt` and read them back with read_file.

## Final verification checklist (per site, post-deploy)

```bash
for p in "" "ar/" "contact" "products" ...; do
  curl -sL "https://<site>.pages.dev/$p" | grep -cE '<old-variants>|<new-variants>'
done   # old = 0 everywhere; new > 0 where expected
curl -sL https://<site>.pages.dev/ | grep -c '<live-section-marker>'  # structure intact
```
Also curl each JS asset (4 files in Sanad's case) to confirm none were dropped.
