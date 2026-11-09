# Carousel Webhook Workflow (reference implementation)

Built 2026-08-26 for the "YouTube → LinkedIn carousel" pipeline (Josue AI video flow).
Live-tested end-to-end: webhook POST → Apify transcript → DeepSeek slides → JSON response
(HTTP 200, ~37s, ~4KB).

## Node Chain (6 nodes)

| # | Node | Type (typeVersion) | Notes |
|---|------|--------------------|-------|
| 1 | Webhook | n8n-nodes-base.webhook (2.1) | POST, path `carousel`, `responseMode: "responseNode"`, custom `webhookId` |
| 2 | Apify Transcript | n8n-nodes-base.httpRequest (4.5) | POST run-sync-get-dataset-items, `jsonBody: ={{ JSON.stringify({ videoUrl: $json.body.url }) }}`, httpHeaderAuth cred |
| 3 | Flatten Transcript | n8n-nodes-base.code (2) | item has `data: [{start,dur,text}]` array → join `seg.text` into one string |
| 4 | DeepSeek | n8n-nodes-base.httpRequest (4.5) | chat/completions, model deepseek-v4-flash, max_tokens 8000, response_format json_object |
| 5 | Parse Slides | n8n-nodes-base.code (2) | `JSON.parse(choices[0].message.content)` → {title, slides, caption} |
| 6 | Respond to Webhook | n8n-nodes-base.respondToWebhook (1.5) | respondWith allIncomingItems |

Connections: linear 1→2→3→4→5→6.

## E2E Test Recipe (post-import)

```bash
# after restarting n8n, WAIT ~40s for async webhook registration
curl -s --max-time 280 -u "sanas:$PASS" -X POST \
  "https://<tunnel>/webhook/carousel" \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://www.youtube.com/watch?v=<VIDEO_ID>"}'
# expect: [{"title": "...", "slides": [...10], "caption": "..."}]
```

Auth via caddy proxy (basic auth user `sanas`). Without auth: 401.

## Apify specifics (from live session)

- Token: `APIFY_API_TOKEN` in `~/.hermes/.env` (600 perms). FREE plan: $5/mo usage credits,
  ~6 compute units/mo, ~0.2-0.5 CU per transcript video (~15-25 videos/mo free).
- Account check: `GET https://api.apify.com/v2/users/me?token=...`.
- Actor discovery: `GET https://api.apify.com/v2/store?search=youtube%20transcript` — the
  popular one is `pintostudio~youtube-transcript-scraper` (5.1M+ runs). Input: `{"videoUrl": "..."}`
  (NOT startUrls). Output items: `[{"data": [{"start": "...", "text": "..."}]}]` — text nested
  under `data`.
- API path uses tilde: `/acts/<username>~<actorName>/run-sync-get-dataset-items` — slash form
  returns page-not-found. `?timeout=240` caps sync wait.
- YouTube/yt-dlp/youtube-transcript-api are BLOCKED from the Oracle VM IP — Apify is the main
  transcript route (scrapes from its own servers).

## Hermes CLI twin (same pipeline, scripts)

`~/.hermes/scripts/carousel/` — the reference implementation the n8n workflow mirrors:
- `transcript_apify.py <url> [--out file]` — Apify sync fetch, loads token from ~/.hermes/.env.
- `generate_carousel.py <transcript.txt> --voice english|personal|bilingual --brand "<line>"`
  — DeepSeek → slides.json; system prompt pins tool stack (Apify + DeepSeek + auto PNG,
  NEVER GPT/Canva) and brand line (anti-hallucination: model invented "Alex Rivera" once).
- `render_slides.py slides.json --out dir --brand "..."` — 1080×1350 PNGs (Pillow), inanimate
  visuals only.
- `post_linkedin_carousel.py <png_dir> --caption "..." --dry-run` — LinkedIn v2 multi-image
  carousel post (review-first).

Brand line for Aamir's personal carousels: `Aamir Zameer | PME Consultant | aamir1zahran@gmail.com`.
