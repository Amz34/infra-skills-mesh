# Corporate-level rebuild of an EXISTING client site (parts-assembly method)

Trigger (verbatim style): *"<client-url> isko bhi shopify high-pitch type me replicate
corporate level website banao, qa urself"* — i.e. an existing (often thin) live client
marketing site must come back as a corporate-grade property, self-verified, no scope Q&A.

Proven 2026-09-21 on `luxewave-ksa.netlify.app` (hotel-supply client) — thin one-pager
rebuilt into a full corporate site with video hero, 13 generated photos, corporate
sections, and a working chat/form widget, all QA'd before any deploy.

Golden rule: **the live page is the source of truth for approved copy + behaviour JS;
you are re-skinning and re-sectioning, not inventing a new business.** Harvest first,
then rebuild.

## 1. Harvest from a GIT SNAPSHOT (never from your own output)

```bash
cd <repo>
git status --porcelain                     # confirm the source page is still unmodified
git show HEAD:index.html > /tmp/old_index.html   # <= the pristine source
```
Extract from `/tmp/old_index.html`:
- approved visible copy (strip `<script>/<style>`), section inventory, byte/line counts
- the inline behaviour `<script>` (nav toggle, counters, chat widget, form handler)
- the chat/contact widget markup + its CSS
- exact form/chat endpoints (grep `fetch(` and `XMLHttpRequest`/`.open(`)

Never point the extractor at the file your builder writes — see §3 pitfall.

## 2. Chunked authoring + single builder

Author the new page as ordered chunks under `/tmp/lw_build/`:
`00_head.html`, `10_css_core.html`, `11_css_nav.html`, `12_css_hero.html`, … `18_css_responsive.html`
(styles), `19_body_open_nav.html`, `20_hero.html` … `29_footer.html`, `30_chat.html`, `31_extra_js.html`.

`build_site.py` concatenates them in a FIXED list and re-appends the harvested behaviour
script verbatim, so the client's existing widget/nav/form keep working untouched:

```python
CHUNKS = ["00_head.html", "10_css_core.html", ..., "31_extra_js.html"]
page = "\n".join(open(D / c, encoding="utf-8").read() for c in CHUNKS)

old = open('/tmp/old_index.html', encoding='utf-8').read()          # snapshot, NOT the repo file
blocks = re.findall(r'<script(?![^>]*src=)[^>]*>.*?</script>', old, re.S)
script = max(blocks, key=len)                                       # behaviour script = biggest inline block
assert 'getElementById' in script and len(script) > 5000, 'main script extraction failed'
page = page.replace('</body>', script + '\n</body>')
open(R / 'index.html', 'w', encoding='utf-8').write(page)
```

Then assert the result (fail loudly, do not eyeball):

```python
h = open(R/'index.html').read()
assert h.count('getElementById') >= 20      # widget/nav/form JS is really present
assert h.count('<script') == 3              # JSON-LD + behaviour + your extra JS
assert h.count('</body>') == 1 and h.count('BEFORE-NUMBER-STRING') == 0
```

## 3. The self-clobber bug (this cost the whole site's JS, silently)

The first builder read the "old" page from the SAME path it wrote (`R/index.html`).
Run 2 therefore harvested… its own output: the biggest inline `<script>` of the NEW page
was the JSON-LD block, so the site was rebuilt **with the behaviour script replaced by a
duplicate JSON-LD** — chat, form, nav toggle, counters and scroll-reveal all dead, with no
error anywhere. Detection: `grep -c getElementById index.html` collapsed 24 → 3 and the
page had two `application/ld+json` blocks. Same class of bug applies to any
"read → transform → write same file" pipeline: **snapshot the source out of band
(git) and assert markers after every run.**

## 4. Class-drift gate (mandatory after assembling hand-written HTML+CSS)

`python3 scripts/check_class_drift.py index.html` — exit 1 = a used class has no rule.
Real hits on this build: markup `class="foot"` vs CSS `footer.site-foot` (footer rendered
unstyled), `class="form"` vs `.form-card` (contact form unstyled), `.foot-brand img` vs
markup `.foot-logo`, plus dead CSS for `.pillar`, `.step::before` (double numbering with the
markup counter `.step-n`). Fixing these is what "corporate" actually looks like — a
half-styled section is the single most common "looks cheap / fake" cause.

## 5. Imagery — generate, then LOOK at it before it ships

`fluxbatch prompts.txt --outdir art --preset carousel` (cards) / `--preset hero` (bands),
then build one contact sheet and review it with vision (`sheet.jpg`), regenerate any tile
that came back with garbled objects/text. Inanimate only for client work (no faces /
crowds). Keep the CLI usage note: `fluxgen --usage` for remaining quota.

## 6. Copy truth pass

Replace any claim you cannot evidence with a request-based phrasing — e.g. a
"Batch Traceability" cert card became **"Documentation On Request — copies of licences,
conformity certificates and product specifications are shared for your procurement file."**
Then run the standing gate:
`python3 ~/ops/verify/claim_integrity.py <file> --json` (expect `pass`, 0 high/med).
Also unify the contact number across the WHOLE deliverable — page AND the chat function's
system prompt (`netlify/functions/chat.js` had the old number) — and flag the change in the
handover message.

## 7. Self-QA (Playwright over CDP, 3 breakpoints)

Use the persistent Chrome, not a fresh launch:
`p.chromium.connect_over_cdp('http://127.0.0.1:9333')` (Chrome on `DISPLAY=:99`).
- Desktop 1440×900, tablet 820×1180, mobile 390×844; screenshot `desktop_top`, `mobile_top`,
  `desktop_full`, `mobile_full` + per-section shots.
- **Reveal-animation trap:** elements with `.reveal{opacity:0}` are invisible in a full-page
  capture, so the shot shows big BLANK bands and looks broken. Inject
  `pg.add_style_tag(content='.reveal{opacity:1 !important;transform:none !important}')`
  before the full-page capture, and ship a real fallback in the page
  (`<noscript><style>.reveal{opacity:1;transform:none}</style></noscript>` +
  `@media (prefers-reduced-motion:reduce)`).
- Assert, don't eyeball — one dict per viewport:
  `video.paused == False`, `video.error == None`, `readyState >= 2`, `console errors == 0`,
  `broken_images == 0`, every `a[href^="#"]` resolves to an existing element,
  WhatsApp/store link counts, and no duplicate `<script>` JSON-LD.
- Then review the key screenshots with native vision (hero legibility, footer contrast,
  section continuity on the full-page shot) and fix what it flags — e.g. the "Sound on"
  pill had to move inline under the trust row, and the mobile hero scrim had to be
  tightened to `rgba(9,22,50,.90/.86)` so text stayed readable over the video.
- Video: a 404×720 portrait source upscaled to full-width desktop = visible blur. Correct
  pattern: sharp 16:9 image as the desktop background + a portrait 9:16 video card
  (`height:min(68vh,600px)`, gold border); full-bleed video + scrim on mobile.

## 8. Deploy when the canonical host's credentials are missing

The client's canonical URL often belongs to a host you have no token for (Netlify here).
Do NOT silently migrate the client's URL. Instead:
1. Commit + push the repo (the work is preserved; a repo without auto-deploy changes nothing live).
2. Ship a **review build to a NEW Cloudflare Pages project** so the user can see it today:
   copy the repo to a deploy dir, inject `<meta name="robots" content="noindex,nofollow">`
   (never compete with the client's canonical URL) and a `Disallow: /` robots.txt in the
   deploy copy only, keep `canonical`/`sitemap` pointing at the official URL.
   `env -u CLOUDFLARE_API_TOKEN npx wrangler@3 pages project create <name> --production-branch main`
   then `... pages deploy . --project-name <name>`.
3. Verify the deployed URL live (curl markers + Playwright again on the public URL).
4. Hand over the link and ask for the ONE missing credential in the same message
   ("Netlify token bhejein ya login link chahiye?") — that is the only blocked step.

Chat/form on a host without its backend degrade to the client's own fallback (the widget
posts to `/api/contact` then opens WhatsApp) — say that explicitly instead of calling it done.

## 9. Pitfalls quick table

| Symptom | Cause | Fix |
|---|---|---|
| Chat/form/nav/counters dead, no console error | builder read its own output | snapshot source via `git show HEAD:file`, assert `getElementById` count |
| One section unstyled / "looks cheap" | markup class vs CSS selector drift | `scripts/check_class_drift.py` |
| Blank bands in full-page screenshots | `.reveal` opacity-0 | inject override in QA + `<noscript>` fallback in page |
| Stat block shows "4 ! 5" or empty | `data-target` numeric counter fed a range | static `<div class="num-static">4–5</div>` |
| `wrangler` auth error on a logged-in account | read-only `CLOUDFLARE_API_TOKEN` in env shadows OAuth | `env -u CLOUDFLARE_API_TOKEN npx wrangler@3 …` |
| Old phone number still reachable | widget system prompt inside the site's function file | grep the whole tree, not just the HTML |
