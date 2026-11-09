# AZ Engineering Field Guide — worked personalization pipeline (2026-09)

26-page A4 eBook (Red Hat "agentic AI" replica) + 5-page free teaser + poster. All verified exit-0.

## File layout used
- `src/part_a.html` (head + CSS + cover + TOC …), `src/part_b.html` (body chapters … + `</div><!-- /sheet -->` comment before close)
- `src/frag_css.html` — personalization CSS (`.pgfoot`, `figure.diag`)
- `src/frag_fig_a|b|c.html` — three inline SVG figures (940-unit viewBox)
- `src/frag_lastpage.html` — author/CTA page section with class `page brk`
- `src/update_ebook.py` — splice script; `src/toc_sync.py`; `src/poster.html`

## Splice script anchors (exact, from the real file)
- CSS insert: before `</head>` → `A = re.sub(r'</head>', frag_css + '</head>', A, count=1)`
- Figures/lastpage insert: split B at `re.search(r'</div><!-- /sheet -->', B)` — NOT a blind `</body>` regex (file had a comment there).
- Idempotency: `if 'frag personalization CSS' not in A:` guard per branch.
- Assemble: `cat src/part_a.html src/part_b.html > AZ-Engineering-Agentic-AI-Field-Guide.html`

## Verification results (what "done" looked like)
- Footer: letterspaced regex `Z\s*A\s*M\s*E\s*E\s*R` found on pages 1–26; naive `'Aamir Zameer'` only matched cover/bio (p1, p26) → false coverage report.
- Figure pages: scan `'Figure 1' in page.extract_text()` → Fig1 p4, Fig2 p6, Fig3 p9.
- Section start pages via keyword scan: Ch2=11, Ch3=18, AppA=16, Glossary=24 → TOC spans updated 03/06/11/18/16/24.
- Teaser: pages[0:4] + separately rendered poster → 5 pages; poster is A4 margin-0 with URL text + QR PNG.

## QR / image deps on uv venv
```bash
uv pip install --python /tmp/pdfvenv/bin/python qrcode pillow   # only working form
qrcode.make('https://example.com').save('/tmp/qr.png')          # img src="file:///tmp/qr.png" in poster HTML
```

## Sensitive/AI-copy scans (client-facing artifacts)
```bash
grep -inE 'sk-[A-Za-z0-9]{8}|api[_-]?key|password|BEGIN (RSA|OPENSSH|PRIVATE)|token[=:]' <html> <pdf-text-dump>
```
Brand rules for this client: green palette (#0B3B2E/#0E7A46/#DDF3E4), footer "AAMIR ZAMEER · AZ ENGINEERING · FIELD GUIDE 2026" letterspaced, no "AI" word in marketing copy (title keeps "Agentic AI"), no human faces, no naked emails in public HTML (FormSubmit alias instead).
