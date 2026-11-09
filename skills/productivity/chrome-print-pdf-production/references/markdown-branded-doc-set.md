# Markdown → branded client document set (render pipeline)

Working copy: `~/ops/sap-readiness/render/render_docs.py`, `render/brand.json`,
`render/README.md`; documents `~/ops/sap-readiness/*.md`; output `pdf/*.pdf`.
Built 2026-09-11 for the Az. Consultants SAP engagement pack (SOW, discovery
questionnaire, infra readiness analysis, boost runbook) — reusable for any brand.

## Layout

```
<project>/                 *.md  (source of truth; brand tokens as {{TOKENS}})
<project>/render/render_docs.py   pipeline
<project>/render/brand.json       colours, letterhead block, footer text, badges
<project>/pdf/*.pdf               rendered output (never hand-edited)
```

## Pipeline contract

1. Each markdown file starts with a small front-matter/meta block that the script reads:
   `title`, `classification` (`client-facing` | `internal`), `version`, `date`, `tagline`.
2. Substitution: `{{BRAND}}`, `{{CLIENT_FIELD}}`, `{{DATE}}`, `{{VERSION}}` etc. from a dict.
   **Any surviving `{{...}}` in the rendered HTML → abort that document with a non-zero
   exit** and name the file + missing tokens. Never render a partially-filled client doc.
3. `<!--internal--> … <!--/internal-->` blocks: DELETED when `classification: client-facing`,
   KEPT for internal docs. Authoring note ("note to sender") ek hi jagah likho — dono
   versions ek source se nikalte hain.
4. Markdown → HTML: `markdown.Markdown(extensions=["tables", "fenced_code", "attr_list"])`.
   Print CSS = the same verified block used in SKILL.md (`@page{size:A4;margin:16mm 14mm}` …).
5. Letterhead: brand name + document title + classification badge (visible!) at top of page 1;
   `position:fixed` footer for the repeating page footer (see SKILL.md).
6. Chrome: `google-chrome --headless=new --no-sandbox --disable-gpu --no-pdf-header-footer
   --print-to-pdf=<out> file://<abs html>`. Write HTML to a temp file, delete after render.

## Verification (every render, no exceptions)

```bash
pdftotext pdf/DOC.pdf - | grep -c '{{'                 # must be 0
pdftotext pdf/DOC.pdf - | grep -ci 'note to sender'    # 0 for client-facing docs
pdftotext pdf/DOC.pdf - | grep -c '<Brand Name>'       # > 0 (letterhead landed)
pdftoppm -png -r 70 -f 1 -l 1 pdf/DOC.pdf /tmp/cover   # cover spot-check (vision)
```
Also grep client-facing PDFs for any personal name the client must not see — the docs are
issued under the brand, not under a person.

## Edits that only show up after a re-render

- Cover meta lines collapse if separated by single newlines inside one paragraph → blank
  lines between them.
- Sentence-start capitalisation after a token substitution (`the Client` → `The Client`).
- Text-verify catches token/note leaks; ONLY the page-1 PNG catches layout (a stale PNG from
  an earlier render is a classic false alarm — regenerate it from the CURRENT pdf first).
