---
name: open-research-access
description: "Use when a paper is paywalled / you need a DOI's free copy."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [research, open-access, doi, unpaywall, openalex, doaj, crossref, bibtex, wayback]
---

# Open Research Access (keyless, legal only)

## When to Use

- "ye paper free me chahiye" / a DOI or paper title that sits behind a paywall
- literature review, evidence for a client deliverable ("cite peer-reviewed source")
- citation export (BibTeX), citation counts, TLDR of an unfamiliar paper
- any time you would otherwise paste a paywall link and shrug

## Tool (the single entry point)

`~/ops/scripts/oa_resolve.py` — keyless, no accounts, no Sci-Hub.

```bash
# 1) discovery by topic (title/keyword)
python3 ~/ops/scripts/oa_resolve.py "medical gas pipeline safety" --oa-only --limit 5

# 2) full chain for a known DOI (the real deliverable)
python3 ~/ops/scripts/oa_resolve.py 10.4103/joacp.joacp_274_16
python3 ~/ops/scripts/oa_resolve.py 10.4103/joacp.joacp_274_16 --bibtex   # + BibTeX
python3 ~/ops/scripts/oa_resolve.py 10.1038/nature12373 --json --save     # machine-readable + cache
```

Output of DOI mode: title, venue, authors, citation counts (+ S2 influential count,
reference count), OA status, DOAJ membership, TLDR, **VERDICT**, numbered free
mirrors, Wayback snapshot, Crossref license.

## Sources (all keyless, verified from this aarch64 VM on 2026-09-13)

| Source | Endpoint | Gives |
|---|---|---|
| OpenAlex | `api.openalex.org/works/doi:<doi>` and `/works?search=` | best OA PDF, all locations w/ version, cited_by, venue |
| Unpaywall | `api.unpaywall.org/v2/<doi>?email=` | independent OA verdict + repository mirrors |
| Semantic Scholar | `api.semanticscholar.org/graph/v1/paper/DOI:<doi>` | tldr, influentialCitationCount, openAccessPdf |
| Crossref | `api.crossref.org/works/<doi>` | publisher, license list, canonical URL |
| DOAJ | `doaj.org/api/search/journals/issn:<issn>` | is the venue a fully-OA journal |
| Wayback | `archive.org/wayback/available?url=` | frozen landing-page snapshot |
| DOI content negotiation | `doi.org/<doi>` with `Accept: application/x-bibtex` | free BibTeX (no client library) |

## Workflow

1. Reformat: title/DOI/query → run the script (never guess a mirror URL by hand).
2. Read the **VERDICT** line first. `FREE COPY FOUND (N mirrors)` → give the user
   mirror 1 and note the version (published / accepted / submitted).
   `NO OPEN COPY` → says so honestly; offer author-request email or interlibrary
   loan instead of a fake link.
3. For a deliverable, add `--bibtex` so the citation is copy-paste ready.
4. Prefer repository/PMC mirrors (`ncbi.nlm.nih.gov/pmc`, university repos) over
   publisher landing pages: they are stable and openly licensed.
5. Cite the *version* honestly — a submitted manuscript is not the published paper.

## Pitfalls (learned the hard way)

- **Semantic Scholar `/paper/search` 429s hard** from this shared VM IP. Use
  OpenAlex `/works?search=` for discovery (keyless, generous, no 429) and reserve
  S2 for its DOI endpoint. The script already respects this with `time.sleep(3)`.
- **Unpaywall requires `email=`** or it answers 422. The script sends
  `azengineeringapp@gmail.com`; keep a real address in any new call.
- Unpaywall's `url_for_pdf` **can be the DOI landing page** for diamond-OA records
  — mirror #1 is not guaranteed to be a PDF. Check the host before promising a file.
- `in DOAJ: False` does **not** mean paywalled (many OA venues are not DOAJ-listed).
- The Wayback availability endpoint is rate-limited: query it once per DOI
  (`--save` caches the whole result under `~/.cache/oa_resolve/`).
- Crossref/OpenAlex occasionally 5xx — the script retries 2x with backoff; a single
  blank field is not a failure of the whole resolution.
- **Legal line:** open access + author-deposited copies only. Never Sci-Hub /
  shadow libraries; if no legal copy exists, say so.

## Verification

- Script exits 0 and prints a VERDICT line; `--save` writes JSON to
  `~/.cache/oa_resolve/<doi>.json` — read it back if output looked truncated.
- A mirror is *confirmed* only after a `curl -sIL` (or the script's own fetch)
  returns 200. Never forward a link you have not resolved once.

## Related

- `research/arxiv` — arXiv-specific search (papers there are already open).
- `research/grounded-citations` — how to cite these findings in a deliverable.
- `research/free-knowledge-library` — books / textbooks (sibling capability).
