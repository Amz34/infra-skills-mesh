---
name: web-site-qa-lane
description: "Use when auditing a live site: a11y, layout, SEO."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [qa, web, accessibility, axe, playwright, seo, visual-regression]
    related_skills: [dogfood, android-mobile-qa-artemis, client-website-delivery]
---

# Web Site QA Lane (deployed-site audit)

Deterministic, re-runnable quality gate for a **live URL** — our Cloudflare Pages
sites and client sites alike. Complements `dogfood` (hands-on exploratory QA with
browser tools): this lane is the CLI gate an agent or cron runs unattended.

## When to use

- A site/preview is ready → automated pass before hand-off (Sanad, AVVS, client sites).
- After a content/theme/font change → regression check that nothing a11y or layout broke.
- A client asks "site theek hai / accessible hai?" → run it first, quote the JSON.

## Command

```bash
~/.venvs/playwright/bin/python ~/ops/qa/site_qa.py https://example.com
~/.venvs/playwright/bin/python ~/ops/qa/site_qa.py https://example.com --strict
```

Use the **playwright venv interpreter**; a bare `python3` has neither playwright nor
axe. Reports land in `~/ops/qa/reports/<host>-<YYYYMMDD>/` (`report.json`, `report.md`,
screenshots).

## Exit-code contract (what makes it usable in CI/cron)

| Code | Meaning |
|------|---------|
| 0 | pass |
| 1 | fail — at least one finding |
| 2 | error — the run itself couldn't happen (DNS/TLS/timeout/redirect loop) |

`--strict` promotes notes to findings, so a hygiene run can gate a release; the
non-strict run is the everyday "what should we fix?" view.

## What it checks

- **axe-core 4.10.2, vendored** at `~/ops/qa/vendor/axe.min.js` — no CDN, so the lane
  cannot be broken by a remote outage and needs no network beyond the target.
- **Three viewports**: desktop 1440 / tablet 834 / mobile 390 — separate a11y node counts
  per viewport (responsive defects only show in the narrow one).
- **Horizontal overflow** (`scrollWidth > clientWidth`) — the real mobile bug signal.
- **Console errors + failed requests** — silent JS errors are high-value findings.
- **SEO/meta**: title, description, canonical, `og:image` presence.
- **Visual baseline** PNG diff — first run seeds the baseline, `--update-baseline`
  accepts an intended design change (say so when you use it).

## Noise policy (keeps the finding set trustworthy)

- **favicon 404 → note, never a finding** (otherwise every site without a favicon "fails").
  Same for `alt=""` on decorative images and third-party script warnings.
- axe **nodes ≠ distinct bugs**: colour-contrast can produce dozens of nodes from one rule.
  Report node counts in the summary; keep findings actionable and de-duplicated.

## Editing the lane

1. Change `~/ops/qa/site_qa.py`.
2. Run `~/ops/qa/selftest.sh` — it proves **both** exit branches against
   `~/ops/qa/fixtures/index.html` (pass ⇒ 0, strict ⇒ 1, favicon ⇒ note). A lane whose
   own contract is untested is decoration; extend the selftest in the same change.
3. Keep `vendor/axe.min.js` pinned; bump it deliberately and re-run the selftest.
4. Client-facing report text: **pure English, no emojis, no images** (Aamir's client rule);
   findings go to the owner only, never to a public post.

## Worked example (sanad-io.pages.dev, 2026-09-21)

40 a11y nodes desktop / 38 tablet / 37 mobile — `color-contrast`, `heading-order`,
`landmark-one-main`, `region`; **`og:image` missing**; overflow 0; console errors 0.
Useful shape: layout was clean, so the deliverable to the client was a short
accessibility list plus the social-preview image, not a redesign.

## Pitfalls

- Don't audit a localhost dev server and label the report as the deployed site — the
  report dir name must match the host you actually loaded.
- A stale baseline produces false visual diffs; refresh deliberately and record it.
- Mobile-only overflow = bug; desktop-only overflow is usually a benign wide element.
- When the deliverable is an **app**, pair this with `android-mobile-qa-artemis` (device
  lane); for hands-on flows, `dogfood`.
