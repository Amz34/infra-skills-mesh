# Reading login-walled social posts (LinkedIn / X / IG)

Companion to the research skill `blocked-page-recovery` (bundled — that one's ladder is the
general method; this file is the social-platform case as measured Sep 2026).

## Expected results, in order

| Attempt | What you get |
|---|---|
| `web_extract <url>` | ~700 chars of nav chrome / "Sign in to continue" |
| headless browser + `document.body.innerText` | ~600 chars of the same login chrome |
| `curl -s --max-time 45 "https://r.jina.ai/<url>"` | **the full post text** |

So do not burn rounds on the browser for a social URL — go straight to the reader proxy.
Anonymous `r.jina.ai` worked for a LinkedIn post link in Sep 2026 (no `JINA_API_KEY` set);
try anonymous first, then `-H "Authorization: Bearer $JINA_API_KEY"` if it 401s.

## Citing it

A reader render is `live` provenance (server-side render of the live page), not a snapshot —
cite normally, and keep the habit of marking claims fetched this way with `[src: …]`.

## Gotchas seen in practice

- `lnkd.in/<slug>` shortlinks: a `curl -sIL … | grep -iE '^(HTTP|location)' | head -30` probe
  returned only ONE matching line — the redirect chain did not print. Don't conclude the link
  is dead from that; fetch the reader URL directly, or use `-w '%{url_effective}'`.
- A post *about* a project is not the project. After reading the post, still check the primary
  sources (repo, paper, model card / HF API) before repeating the post's numbers — the claims in
  the post ("real time", "20 ms/frame") are marketing until measured.
- Engagement counts (reactions/comments) are visible with the post text via the reader; record
  them only if the audit needs reach evidence, and never as a quality signal.

## Pairs with

- `link-safety-triage` — when the link itself is unknown/suspicious (domain, redirects, who
  shared it) rather than merely gated.
- `tech-adoption-analysis` — the verdict workflow once the source text is in hand.
