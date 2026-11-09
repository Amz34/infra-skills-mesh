# Notion Public Page Extraction (proven 2026-08-26)

Notion public pages resist normal extraction: `web_extract`/curl get
Cloudflare-blocked or render only a ~600-char outline; the page's internal
API (`POST /api/v3/loadCachedPageChunk` with the page UUID) returns HTTP 200
but **0 blocks** — don't chase it. The working recipe uses the browser:

> ⚠️ **CORRECTION (verified 2026-09-19): that "0 blocks / don't chase it" note is
> endpoint-specific, not a property of Notion.** On an `https://app.notion.com/p/<slug>-<32hex>`
> public page, **`POST /api/v3/loadCachedPageChunkV2` (the V2 suffix) returned the whole
> document unauthenticated — 105 blocks / ~10 KB of text in ONE call, no cookies, no browser.**
> Always try the API route below BEFORE the browser recipe; fall through to the browser only
> if the page is `workspace.notion.site`-style or V2 returns empty.

## API route — try FIRST (proven 2026-09-19, app.notion.com/p/…)

```bash
curl -s 'https://app.notion.com/api/v3/loadCachedPageChunkV2' \
  -H 'Content-Type: application/json' -A '<desktop Chrome UA>' \
  --data '{"page":{"id":"<dashed-uuid>"},"limit":100,
           "cursor":{"stack":[]},"chunkNumber":0,"verticalColumns":false}' \
  -o /tmp/notion_chunk.json
```

- 32-hex id from the URL → dashed UUID (`3d2b9abc-be3f-807f-a46a-d5576b32f858`).
- Response `recordMap.block`. **Paginate with the `cursor` returned by the previous call** —
  bumping `chunkNumber` alone re-returns the same blocks (chunk 1 gave 0 new blocks on a
  105-block page, which is a per-page cap, not an error).
- Records are **doubly wrapped**: `{"spaceId":…,"value":{"value":{type, properties,…}}}`.
  Unwrap before reading fields, or you get `KeyError: 'type'`:
  ```python
  v = rec
  while isinstance(v, dict) and 'value' in v and 'type' not in v:
      v = v['value']
  text = ''.join(run[0] for run in v.get('properties', {}).get('title', []) if run)
  ```
- **Embedded images**: grep the raw chunk JSON for `https://prod-files-secure\.s3[^"]{0,400}` →
  those signed URLs `curl -o /tmp/img_NN.png` directly (14 images recovered this way after a
  block-type walk returned 0). They expire — download in-session, never store the URL.
  Authenticated alternative: `POST /api/v3/getSignedFileUrls` with
  `{"urls":[{"permissionRecord":{"table":"block","id":"<blockid>"},"url":"<attachment:…>"}]}`.
- **Asset filenames are evidence**: `Capture_decran_2025-09-25`, `Screenshot_2026-05-29` date the
  screenshots in a doc — decisive when auditing whether its claims are fresh.

Generalisation of this ladder (LinkedIn guest post/comment pages via curl + `ld+json` + snowflake
ID→timestamp, and the single-line chunked reads that survive harness output elision):
`references/unauthenticated-content-extraction.md`.

## Why it fails with plain tools
- `curl` with a Googlebot UA → Cloudflare 403 on notion.site.
- `web_extract` → 3.9K chars of outline only (lazy-rendered blocks).
- Browser `document.body.innerText` after load → outline only; scrolling
  does NOT trigger block render (contrary to normal lazy-load SPAs).

## Working recipe (browser_exec)
1. **Open the page, then extract ALL links** — Notion docs are often HUB
   pages: section headings ("The exact prompts...") are anchor links to
   SIBLING SUB-PAGES with their own UUIDs:
   ```js
   js(`(() => JSON.stringify([...document.querySelectorAll('a')].map(a => a.getAttribute('href')).filter(Boolean)))()`)
   ```
   Sub-page hrefs look like `/Sub-page-title-<32-hex-uuid>`.
2. **Navigate to each sub-page directly** (`goto_url("https://<workspace>.notion.site" + href)`),
   wait ~5s, read `document.body.innerText`.
3. **If the sub-page text is still collapsed, extract from the raw HTML** at
   heading markers — block content IS present in `innerHTML` even when
   `innerText` omits it (code blocks/callouts render as zero-width chars):
   ```python
   import re
   html = js("document.documentElement.innerHTML")
   for name in ["Prompt 1", "Prompt 2"]:
       i = html.find(name)
       seg = re.sub(r"<[^>]+>", " ", html[i:i+3000])
       print(re.sub(r"\s+", " ", seg).strip())
   ```
4. Full-text recovery: dump the whole `innerHTML` and strip tags with regex;
   content beyond each heading marker lives in the following ~2-3K chars.

## js() helper traps that bit during this flow
- `js("() => JSON.stringify({...})")` — bare arrow = UNcalled function →
  returns `{}`. Must be `js("(() => JSON.stringify({...}))()")`.
- `js()` cannot return raw objects (serializes to `{}`); always return
  strings (JSON.stringify / innerText).
- An async fetch inside `js()` also needs `(async () => {...})()` wrapping.

## When to use
- Notion public share links (workspace.notion.site) that other tools can't read.
- Same pattern likely works for other lazy SPAs whose content lives in the
  rendered DOM rather than a JSON API: hub-page links → direct navigation →
  innerHTML marker extraction.
