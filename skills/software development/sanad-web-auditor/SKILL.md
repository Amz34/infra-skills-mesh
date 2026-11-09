---
name: sanad-web-auditor
description: "Use to audit performance and extract visual design systems."
version: 1.0.0
author: Aamir Zahran (Amz34 / Sanad)
license: MIT
platforms: [linux, macOS, windows]
metadata:
  hermes:
    tags: [audit, performance, lighthouse, design-system, visual-dna, claude-md, branding, ai-agents]
    related_skills: [web-site-qa-lane, design-intelligence, frontend-design, github-pr-workflow]
---

# Sanad Web Auditor & Design Extractor

Enterprise-level performance and design extraction toolbox branded under **Sanad (سند)**. It combines PageSpeed-to-CLAUDE.md auditing and VisualDNA design system extraction to empower AI coding agents with instant, highly accurate visual and performance instructions.

## When to Use

1. **Before any AI coding run**: Run a PageSpeed audit, generate a `CLAUDE.md` fix plan, and feed it straight to Claude Code or Hermes.
2. **Reverse-engineering elegant websites**: Extract design systems (colors, typography, spacing, shadows, and tech stack) using VisualDNA to build high-performance, non-slop UIs.
3. **Continuous Integration & Auto-Push**: Automatically audit client sites on every GitHub push/release and maintain performance baselines.

## Direct Product & Download Links

| Use Case | Tool Name | Direct Link (Mobile / Laptop) |
|---|---|---|
| **Performance to AI Fix** | **Lighthouse-MD** | [lighthouse-md.com](https://lighthouse-md.com/) |
| **Lighthouse Extension** | **Lighthouse-MD Chrome Extension** | [Lighthouse-MD Chrome Web Store](https://chromewebstore.google.com/detail/lighthouse-md-pagespeed-a/cphchklbbkhglppapokhdbhnkhghhhnk) |
| **Design System Extractor** | **VisualDNA Web App** | [visual-dna.live](https://visual-dna.live/) |
| **VisualDNA Extension** | **VisualDNA Chrome Extension** | [VisualDNA Chrome Web Store](https://chromewebstore.google.com/detail/visualdna-%E2%80%93-design-system/ljilnejdgkedledpbhncgfdojfmnnaib) |

## Quick Commands & Scripts

### 1. Run Performance Audit to CLAUDE.md
```bash
# Audits the website and writes a CLAUDE.md in current directory
npx lighthouse-md https://example.com

# For desktop audits and direct stdout printing
npx lighthouse-md https://example.com --strategy desktop --stdout
```

### 2. Auto-generate Design System Prompt
Use VisualDNA on your browser (Mobile or Laptop) to extract a website's palette and typography, then export it as a Tailwind CSS config or custom CSS and save it directly to `MASTER.md`.

## GitHub Actions Cron & Push Automation

To make this legendary and part of our brand, we set up an automated GitHub Workflow (`.github/workflows/sanad-audit.yml`) inside our repositories. This automatically runs on weekly cron or on every git push to generate/update the `CLAUDE.md` file.

```yaml
name: Sanad Performance & QA Audit

on:
  push:
    branches: [ main ]
  schedule:
    - cron: '0 0 * * 0' # Weekly on Sundays

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Run Sanad Web Auditor
        # Audits our deployed production URL (e.g. imaa-kiosk.pages.dev)
        run: npx lighthouse-md https://imaa-kiosk.pages.dev

      - name: Commit and Push Audit Plan
        run: |
          git config --global user.name "Sanad Auditor"
          git config --global user.email "auditor@sanad.io"
          git add CLAUDE.md
          git diff-index --quiet HEAD || git commit -m "chore(audit): auto-update CLAUDE.md performance fix plan [skip ci]"
          git push
```

## Brand Gates & Verification

- **Never Commit Credentials**: Never let the PageSpeed API Key leak into public repos. Run anonymously (free quota is generous).
- **Verify before Delivery**: Always run the audit on the preview build (e.g., Cloudflare Pages preview branch) before deploying to production.
