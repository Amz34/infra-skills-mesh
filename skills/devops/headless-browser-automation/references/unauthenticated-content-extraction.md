# Unauthenticated content extraction: app-shell pages, JSON APIs, guest views

For **public** content that `web_extract` or plain `curl` cannot render (JS-shell pages, guest-view
social pages, docs behind an app router). Complements the browser-harness path: when the harness
returns near-empty output, that is a signal to climb to the direct-HTTP/API rung — not a verdict
that the page is unavailable. Both cases below worked unauthenticated (2026-09).

## Triage ladder (stop at first success)
1. `web_extract <url>` — fine for static/SSR; a ~1–2 KB stub means climb, don't conclude.
2. `curl -sL -A "<desktop Chrome 140 UA>" <url> -o /tmp/p.html` → look for
   `<script type="application/ld+json">`, `__NEXT_DATA__`, `window.__*` blobs.
3. The app's own internal JSON API (sections below).
4. Browser harness / real browser (renders DOM, but slower and its output may elide).

## 1. Notion public page → `loadCachedPageChunkV2`

`https://app.notion.com/p/<Title>-<32hex>` is a JS shell: `curl` gives ~20 KB with
`<title>Notion</title>` and no body; `web_extract` a ~2 KB stub.

```bash
curl -s 'https://app.notion.com/api/v3/loadCachedPageChunkV2' \
  -H 'Content-Type: application/json' -A '<desktop Chrome UA>' \
  --data '{"page":{"id":"<dashed-uuid>"},"limit":100,
           "cursor":{"stack":[]},"chunkNumber":0,"verticalColumns":false}' \
  -o /tmp/notion_chunk.json
```

- 32-hex page id → dashed UUID (`3d2b9abc-be3f-807f-a46a-d5576b32f858`).
- Response `recordMap.block` (blockId → record). A ~10 KB doc returned as **105 blocks in one
  call**; `chunkNumber:1` gave 0 new blocks. **Paginate with the `cursor` from the previous
  response — bumping `chunkNumber` alone re-returns the same blocks.**
- Blocks are **doubly wrapped**: `{"spaceId":…,"value":{"value":{type, properties,…}}}` — unwrap
  before reading fields (classic `KeyError: 'type'`):

```python
v = rec
while isinstance(v, dict) and 'value' in v and 'type' not in v:
    v = v['value']
text = ''.join(run[0] for run in v.get('properties', {}).get('title', []) if run)
```

### Images inside a public Notion page
- Signed URLs sit **in the block JSON**: grep `https://prod-files-secure\.s3[^"]{0,400}`, dedupe
  hosts (`collections.Counter`), then `curl -o /tmp/img_NN.png <signed-url>` (14 images retrieved
  this way when the block-type walk returned 0).
- Signed URLs expire — download in-session, never store the URL as a durable asset path.
- Authenticated variant if needed: `POST /api/v3/getSignedFileUrls` with
  `{"urls":[{"permissionRecord":{"table":"block","id":"<blockid>"},"url":"<attachment:…>"}]}`.
- **Filename forensics:** captions/filenames in block text (`Capture_decran_2025-09-25`,
  `Screenshot_2026-05-29`) date the assets — decisive when auditing a doc's freshness claims.

## 2. LinkedIn guest view (post + comment thread)

- `https://www.linkedin.com/feed/update/urn:li:activity:<activityId>/` works with
  `curl -s -A "<desktop Chrome UA>"` (192 KB observed). `web_extract` on a URN-parameterised URL
  returned only a ~1.2 KB login stub — skip that rung.
- Deep link to a thread: append
  `?commentUrn=urn%3Ali%3Acomment%3A(urn%3Ali%3Aactivity%3A<activityId>,<commentId>)&replyUrn=...`
  (URL-encoded parenthesised URNs). This brings the highlighted thread into the page; the
  comment/reply IDs are usually **absent** from the plain post HTML.
- **Structured data comes from `<script type="application/ld+json">`** — interaction counts and a
  `comment` array (author/date/text). Prefer it over DOM scraping.
- Guest view exposes only ~10 comments even when `commentCount` is 537 — state that limit instead
  of implying you read the full thread. Reaction counts can differ between JSON-LD and rendered
  widgets; attribute every number to the field you read.
- Visible-text dump for a full read (~6 KB): strip `<script>/<style>`, strip tags,
  `html.unescape`, collapse whitespace.

### Snowflake ID → timestamp
`ts_ms = (id >> 22) + epoch`, calibrated against a known post timestamp (observed offset ≈ −26 ms
⇒ standard Unix-ms in practice). `delta_h_from_post` per comment is a cheap engagement signal —
the earliest repliers are the hottest, and a reply landing minutes before the user forwards the
link usually means that reply *is* the funnel step that delivered the next artifact.

## 3. Harness I/O pitfall: long output elides

Big multi-line prints come back truncated. What reads reliably: **one line per chunk**, ~1,200–1,500
chars, newlines → ` | `, prefixed (`N0|…`, `N1|…`) so gaps are visible; and prefer *targeted slices
around an anchor* (`t.find('<anchor phrase>')` ± 400 chars) over dumping whole files or raw API JSON.
