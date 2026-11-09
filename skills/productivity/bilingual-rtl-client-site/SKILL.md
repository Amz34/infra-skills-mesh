---
name: bilingual-rtl-client-site
description: Add a genuine RTL Arabic edition/tab to a client site.
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [rtl, arabic, i18n, cloudflare-pages, client-site, seo]
    related_skills: [cloudflare-pages-ops, client-website-delivery, arabic-text-search]
---

# Bilingual / RTL client site edition (EN + AR)

## When to Use
- Client asks for a "KSA / Arabic version", an Arabic tab, or any RTL-language edition of an existing static site.
- You must add a second-language edition without disturbing the live home-market pages.

Goal: a genuinely-written second-language edition (never machine output), correctly mirrored RTL layout, safe SEO wiring, and a byte-verified deploy.

## 0. Recon before writing
- Find the real prod source: `md5sum site/index.html` vs live file (`curl -sL <prod-url> | md5sum`) — the dir whose bytes match prod is the source of truth. Do NOT rebuild from a stale parallel dir.
- Read the established deploy script (`deploy_*.sh`) — reuse its project name, account id, and verify block. Prod branch is usually `main`: confirm with `npx wrangler pages deployment list --project-name <p> | grep -i production | awk -F'│' '{print $4}' | sort -u`.
- Deploy a NEW preview branch (e.g. `--branch ksa-arabic`) so an older review branch is not clobbered. Prod only after explicit user approval.

## 1. URL structure
- `<site>/ksa.html` = English regional edition; `<site>/ar/ksa.html` = Arabic RTL. Asset paths must be absolute (`/assets/...`) from nested dirs.
- Language tab in the shared nav: `<span class="langswitch"><a class="on" href="/ksa.html">EN</a><a href="/ar/ksa.html" hreflang="ar" lang="ar">العربية</a></span>`; hide on small screens via a class and always keep a footer link as fallback.
- `hreflang` alternates only between true equivalents (EN<->AR pair of the same regional page) + `x-default`. Do not cross-link the pan-region home.
- `sitemap.xml` (with `xmlns:xhtml` alternates) + `robots.txt` pointing at it.

## 2. Arabic copy = genuine, not translated
Write MSA business register yourself. For procurement/tender work: منصة اعتماد، نظام المنافسات والمشتريات الحكومية، كراسة الشروط والمواصفات، التأهيل المسبق، جدول الكميات، العرض الفني/المالي، لجنة فحص العروض، فتح المظروف المالي، الضمان الابتدائي/النهائي، المحتوى المحلي، شهادات الزكاة والضريبة والتأمينات، تصنيف المقاولين، التشغيل والصيانة، إدارة المرافق.
Keep Western digits (0-9) and Latin brand names Latin. Rebuild stat/CTA labels as truthful regional numbers instead of copying the home-market ones.

## 3. RTL engineering (what looks broken if skipped)
- `<html lang="ar" dir="rtl">`; load an Arabic webfont (IBM Plex Sans Arabic pairs with Inter) and set it in a `[dir="rtl"] body` rule.
- **Kill letter-spacing on Arabic** — connected script breaks: `[dir="rtl"] h1,[dir="rtl"] h2,[dir="rtl"] h3,[dir="rtl"] .brand,[dir="rtl"] .eyebrow{letter-spacing:0;text-transform:none}`.
- Mirror list bullets and absolute badges: `[dir="rtl"] ul.clean li{padding-left:0;padding-right:20px}` + `:before{left:auto;right:0}`; `[dir="rtl"] .badge{left:auto;right:24px}`.
- Email/phone inputs stay LTR: `<input type="email" dir="ltr">`.
- Line-height up a notch for Arabic (1.85-1.9).
- Put these rules in the shared stylesheet scoped to `[dir="rtl"]` — zero effect on LTR pages.

## 3b. Mobile fit — the RTL pinch-out bug (check this FIRST when a user says "zoom out manually")
Symptom: on a phone the Arabic page needs pinch-out / pans sideways; the LTR pages are fine.
Measure it, never guess: emulate 390/360/320px and read `document.documentElement.scrollWidth` vs `clientWidth`, then list every element whose rect extends past the viewport (sort by rect width — the offender is often a container whose *child's* min-content is huge).
Two root causes seen in the wild, both one-line fixes:
- **Off-screen hiding hacks.** `left:-9999px` / `text-indent:-9999px` (honeypot inputs, skip links, visually-hidden labels) is a landmine: in `dir=rtl` that negative-inline overflow becomes *scrollable*, so the document balloons (measured 10389px = 9999 + 390) while LTR pages are untouched. Hide the safe way instead: `position:absolute;width:1px;height:1px;margin:-1px;border:0;padding:0;overflow:hidden;clip-path:inset(50%);white-space:nowrap;opacity:0`.
- **Non-shrinkable grid tracks.** A mobile rule like `grid-template-columns: 1fr` keeps `min-width:auto`, so ONE long `<select>` option (Arabic budget bands are long) drags the whole track to its min-content and past the viewport. Use `minmax(0, 1fr)` for every responsive single/double-column rule.
Belt-and-braces in the shared sheet (clip, not hidden, so sticky headers keep working):
```css
html, body { max-width: 100%; overflow-x: clip; }
body { overflow-wrap: break-word; }
.wrap, .panel, .card, .split > *, .lanes > *, .form-grid > * { min-width: 0; }
select, input, textarea { max-width: 100%; }
```
Then prove it with the gate: `python3 build/qa_mobile_fit.py` (see `scripts/qa_mobile_fit.py` — headless Chrome, iframes at 390/360/320, element-level detection). `overflow-x: clip` alone masks this class of bug, so the gate must flag *elements past the viewport*, not just `scrollWidth` — and re-test the gate by planting a 1200px div: a gate that cannot fail is worthless.

## 4. Form wiring
- Arabic labels/options in the same field order; translate select options.
- Add `<input type="hidden" name="market" value="KSA-AR">` (other pages `IN`/etc.) and echo it in the lead handler (`'Market: ' + clean(d.market || 'unspecified', 40)`) so alerts show the lead's market.

## 5. Deploy + verify (never ship unverified)
```
npx --yes wrangler pages deploy site --project-name <p> --branch <preview-branch> --commit-dirty=true
```
Verify md5 equality local vs live for every new path. A first-attempt mismatch on `/` is usually the previous deployment's cache — retry with a `?cb=N` query before believing it. After approval deploy `--branch main` and re-verify the same way.

## Pitfalls
- **A near-blank headless screenshot is diagnostic, not a tooling glitch.** An Arabic page shot 20x smaller than its siblings (16.7KB vs ~350KB) was the first hint the document was absurdly wide; run the mobile-fit gate before blaming the screenshot tool.
- **A shared `style.css`/`extra.css` is copied into every output dir** by the build (`sites.py` copies CSS + fonts to the other market's `public/`): edit the source sheet once, then re-run the builder so the copies — and the gates — see it.
- Tool output here gets elided when large: verify with SHORT python prints (`print('MARK', a, b, c)`) instead of big greps/read dumps.
- A JSON-LD line containing `https://schema.org","@type"` may display as `***` (output redactor) while the file on disk is fine — confirm with `json.loads` on that line before "fixing" it.
- Don't reuse the home-market funnel/PDF link on the regional edition — it leaks the wrong country's content; share the regional file on request instead.
