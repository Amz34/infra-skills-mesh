---
name: free-knowledge-library
description: "Use when you need a free legal book or textbook."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [books, textbooks, gutenberg, openlibrary, openstax, education, keyless]
---

# Free Knowledge Library (keyless, legal)

## When to Use

- "is there a free copy of this book?", classic literature, public-domain texts
- open textbooks for self-study / course material / content research
- building a local, offline reference library (low-bandwidth or cost-free delivery)
- any request where a paid book is assumed to be the only option

## Tool

`~/ops/scripts/free_library.py` — keyless, downloads to `~/library/books/`.

```bash
python3 ~/ops/scripts/free_library.py search "pride and prejudice" --limit 3
python3 ~/ops/scripts/free_library.py search "medical gas" --public-only
python3 ~/ops/scripts/free_library.py get 1342                 # plain text, header/footer stripped
python3 ~/ops/scripts/free_library.py get 1342 --format epub
python3 ~/ops/scripts/free_library.py textbooks "calculus"
python3 ~/ops/scripts/free_library.py textbooks --list         # all 129 OpenStax titles
```

## Sources (keyless, verified 2026-09-13)

| Source | Endpoint | Use |
|---|---|---|
| OpenLibrary | `openlibrary.org/search.json` (`fields=...,id_project_gutenberg,ia`) | metadata **plus the Gutenberg id** — the bridge that makes this fast |
| Project Gutenberg | `gutenberg.org/cache/epub/<id>/pg<id>.txt`, `files/<id>/<id>-0.txt`, `.epub.noimages` | 70k+ public-domain books, direct download |
| Internet Archive | `archive.org/details/<ia-id>` | in-copyright lending (needs a free account = a human step) |
| OpenStax | `openstax.org/apps/cms/api/v2/pages/?type=books.Book&search=` | 129 peer-reviewed open textbooks |

## Workflow

1. `search "<title>"` → read the `GUTENBERG id` block (that is the real answer).
2. `get <id>` → confirms the file on disk with a word count. Report the path, not a promise.
3. Textbooks: `textbooks "<subject>"` → give the OpenStax detail page.
   Tell the user the PDF/epub buttons are on that page (JS-rendered) — do not claim
   you downloaded a PDF.
4. For content work (carousel / lesson / summary) the downloaded `.txt` is the input:
   the Gutenberg header/footer is already stripped, so quoting and word counts are safe.

## Pitfalls

- **gutendex.com is no longer the right door** — it answers `301` with 0 bytes from
  this VM. Don't build on it; OpenLibrary + Gutenberg direct URLs are verified.
- `files/<id>/pg<id>.txt` 404s; the working shapes are
  `cache/epub/<id>/pg<id>.txt` and `files/<id>/<id>-0.txt` (both 200, tested).
- OpenStax has **no direct PDF URL in the page HTML** (JS-rendered). Only offer the
  detail page link; a "downloaded the textbook" claim would be false.
- `ebook_access: public` on OpenLibrary means a full-view scan exists — often an IA
  `bwb_*`/`librivox` item, not a downloadable file. Gutenberg ids are the reliably
  downloadable ones.
- Copyright: only public-domain (pre-1929 US / author +70y) or openly licensed works.
  Never route around a paywall for an in-copyright book.
- Keep the attribution/title line in place when reusing text in deliverables.

## Verification

- `get` prints `OK <path> (<words> words)` and exits 0; else exit 1. Re-check with
  `wc -w` on the file — a body under 2000 bytes is treated as a failure by the script.
- Downloaded files land in `~/library/books/`.

## Related

- `research/open-research-access` — papers/DOIs (sibling capability).
- `research/grounded-citations` — quoting these sources with citations.
