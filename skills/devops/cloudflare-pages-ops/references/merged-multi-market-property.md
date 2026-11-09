# Merging regional editions into ONE Pages property (market tabs)

Proven 2026-09-12 on AZ Consultants: two market sites (`azconsultants-india.pages.dev`,
`azconsultants-ksa.pages.dev`) merged into one group property `az-consultants-group`
(production branch `main`), preview `--branch review` →
`https://review.az-consultants-group.pages.dev/`. Generator +
verification script were the only things edited; the merged `public/` is throwaway output.

## Shape of the merged property

- One Pages project, one generator (`group-site/build/group.py`) importing the per-site sources
  (`sites.py`, `ar_copy.py`, `extras.py`) as modules — never copy their output by hand.
- **Hero tabs, not section tabs**: two pills (`India | Saudi Arabia`) above the hero swap the whole
  market narrative (eyebrow, H1, trust strip, CTA, stats).
- **Market-tabbed data board**: the tenders page reuses the same pattern over per-market row sets
  (KSA Etimad rows / India CPPP-GeM rows) fed by separate captured data files. Keep the feeds
  separate; do not merge them into one list.
- Arabic edition stays a full RTL one-pager pair (`ar.html` + `ar-thanks.html`) with `dir="rtl"`,
  `hreflang` EN↔AR and canonical already pointing at the future group domain.
- Form gets a VISIBLE `select name="market"` whose option values must match the Function's
  allowlist exactly (`IN`, `KSA`, `KSA-AR`) — a hidden-only market input makes the lead's market
  invisible in the Telegram alert.

## CSP-safe tab pattern

- Markup: `role="tablist"` + `role="tab"`/`aria-selected` + `role="tabpanel"`; all behaviour in the
  self-hosted `app.js`; all styling in the sheet. No inline `onclick`, no inline `<script>`
  (the hardened CSP kills both).
- CSS hides only the inactive panel, so with JS disabled BOTH panels remain readable.
- Deep-link the state (`?tab=ksa`) read on load — this is what makes a review screenshot possible
  without clicking, and what lets a shared link land straight on the Saudi panel.
- **Verify by assertion, never by eye:** after clicking the KSA pill, read `aria-selected` for both
  pills (expect `India:false | Saudi Arabia:true`) and confirm the panel text changed. A screenshot
  cannot distinguish a swapped panel from a re-styled one.

## Nav polish belongs in the generator

Market names + a language switcher make nav labels wrap mid-phrase ("Track / record", Arabic
"اتصل بنا"). Fix with `.nav{flex-wrap:wrap;row-gap:6px}` + `.nav a{white-space:nowrap}` emitted by
the build script and appended to the generated `style.css` — a hand-patched stylesheet is destroyed
by the next regeneration. Prove it: single nav row / expected nav height, and
`document.documentElement.scrollWidth === clientWidth`.

## Verification bar before handing the preview link over

Keep ONE script per property that gates both rebuild and deploy. All of these passed as one clean
run (43/43 checks) on the merged site:

1. **Page inventory** — exactly the expected file set (11 pages here, EN + AR + 404 + robots +
   sitemap + `_headers` + `_redirects`).
2. **Regeneration is byte-identical** — rebuild, then diff against the pre-rebuild snapshot; only
   intentionally changed files may differ. This is the proof that the generator is source of truth.
3. **Forbidden-string absences** — 0 `formsubmit`, 0 currency/price tokens (`SAR`, `ريال`, `INR`,
   `₹`), 0 emoji, 0 leftover `{placeholder}`/TODO. Grep the whole `public/` tree, not just HTML.
4. **0 broken links** — internal `href`/`src` targets must exist on disk.
5. **Hardening headers sourced from the generator** — inspect the emitted `_headers`, then confirm
   the live edge serves them (lowercase-normalised dict; see SKILL.md).
6. **Live checks** — ratio of `scrollWidth/clientWidth` at 320/360/390 (EN + AR), tab
   `aria-selected` toggle, market select options, data-board row counts per market.

## Screenshots for the approval gate

Harness CDP screenshots timed out repeatedly on this review; the headless Chrome CLI produced every
shot reliably, including deep-linked tab state:

```bash
CH=$(ls /usr/bin/google-chrome* /usr/bin/chromium* ~/.cache/puppeteer/chrome/*/chrome-linux64/chrome 2>/dev/null | head -1)
mkdir -p /tmp/az_group_shots && cd /tmp/az_group_shots
for spec in "01_index_en|1440,980|$URL" "02_index_ksa_tab|1440,980|$URL/?tab=ksa" \
            "03_ar_hero|1440,980|$URL/ar.html" "05_mobile390|390,844|$URL" ; do
  IFS='|' read -r name size u <<<"$spec"
  "$CH" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
        --window-size="$size" --screenshot="/tmp/az_group_shots/$name.png" "$u"
done
md5sum /tmp/az_group_shots/*.png | sort    # distinct hashes = genuinely distinct captures
```

Then eyeball the one that decides the approval (tab active + nav single row) with `vision_analyze` —
`--screenshot` silently writes nothing on some runs, so `ls -la` the directory before reporting.

## Gotchas hit for real

- `Page.captureScreenshot timed out after 60s` on a healthy page → CLI fallback above.
- Stale CSS from the generator's 7-day `max-age` made the nav polish look unfixed → short TTL.
- First live header check reported CSP "missing": header-name case sensitivity, not a defect.
- Preview deployments carry NO project secrets (`wrangler pages secret put` = production only), so
  form/Telegram E2E must be run against the production deployment, not the preview link.
