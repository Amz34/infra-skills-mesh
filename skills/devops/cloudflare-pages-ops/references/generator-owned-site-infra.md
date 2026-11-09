# Generator-owned site infrastructure (headers, redirects, SEO, forms)

## Symptom
Hand-patched `public/_headers` (8 hardening headers), a cleaned `public/_redirects`, same-origin form
actions and an error-notice `app.js` were live and verified (22/22 scorecard) — then one routine
`python3 build/sites.py` rebuild reverted them, because the generator still emitted
`FORM_ACTION = "https://formsubmit.co/<email>"` and the old 4-header block. Deploy succeeded, so
nothing looked broken until the live checks ran.

## Who owns what (Az. Consultants case, `~/clients/invertio`)
| File | Owns |
|---|---|
| `advisory-site/build/sites.py` | every `public/*.html` (head, nav, hero, form block, footer), `FORM_ACTION`, per-market dicts (`market`, `thanks`) |
| `advisory-site/build/ar_copy.py` | Arabic `ar.html` copy, hidden form fields, AR form note |
| `advisory-site/build/extras.py` | `_headers`, `_redirects`, `sitemap.xml` (+hreflang), `robots.txt`, `404.html` |
| `advisory-site/build/qa_sites.py`, `qa_mobile_fit.py` | the gates |
| `<site>/functions/api/enquiry.js` | the Pages Function (NOT generated — copy it into each site) |

## Fix sequence (verified 2026-09-12)
1. Snapshot built output first: `tar czf /tmp/pre_rebuild_snapshot.tgz advisory-site/public india-site/public`.
2. Patch the generator, not the output: `FORM_ACTION="/api/enquiry"`; per-market dict keys `market` +
   `thanks`; hidden fields `market` / `next` / `page`; form-note text; `extras.py` header block restored
   to the full 8-header set; conditional `_redirects` + hreflang; disk-driven 404 nav.
3. Regenerate, then **diff-prove**: `diff -rq /tmp/pre/<site>/public <site>/public` → only intended
   files change, and `diff .../_headers public/_headers` → **EMPTY (byte-identical)** is the pass bar.
4. Redeploy prod from the site dir, re-run live header / hop-by-hop / form-post checks.
5. Note any *intended* diff and why (e.g. the form-note text), so the diff is evidence, not noise.

## Small-file patch discipline for big generators
- Large reads / `sed` dumps get elided — read in chunks:
  `sed -n '58,100p' extras.py | cat -n | cut -c1-92`.
- When a line is truncated in your view, pull its exact bytes before writing a patch `old_string`:
  `python3 -c "L=open('extras.py').readlines(); print(repr(''.join(L[129:134])))"`.
- For a multi-line block you cannot quote safely, script the edit with `re.sub` over the file
  (a 20-line `/tmp/fix_nav.py`) and assert `found: True` + `ast.parse(ok)` after.

## Conditional-infra snippets that fixed real bugs
- sitemap hreflang: `if name in ("index.html", "ar.html") and "ar.html" in names:`
- `_redirects`: prepend `/ar.html /ar 301` + `/ar/ /ar 301` **only** when `"ar.html" in names`
- 404 nav: build from pages present on disk; `/ar` must be tested as `"ar.html" in names`
  (naive `os.path.exists(out_dir + "/ar")` is False → the العربية link silently vanished)

## Merge two market sites into one property (hero tabs)
- `wrangler pages project create az-consultants-group --production-branch=main` — an empty project
  returns 404 on the root until the first deploy (that 404 doubles as "prod untouched" evidence).
- **Secrets are per project**: set the Telegram token/chat-id on the NEW project too, or its form
  falls into the error path while the old projects work fine.
- New generator `group-site/build/group.py` imports `sites.py` (components + market copy dicts) and
  composes pages; do not rewrite approved copy — add only the new hero / tabs / markets sections.
- Market routing on a merged site: visible `<select name="market">` (IN | KSA) on the EN edition,
  hidden `market=KSA-AR` on `/ar`; the Function allowlists values and falls back to a default —
  an unknown tag is a silent mis-route.
- Cutover: attach the purchased domain (apex + www), SSL, then 301 both legacy `*.pages.dev`
  properties to the canonical domain, and switch sitemap/canonical/hreflang to the new domain **in the
  generator**. Leaving two live copies ranking is the failure mode.
