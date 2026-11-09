# Getting a genuinely different design variant from an external LLM (z.ai / GLM)

When the user says "use <AI site> for the UI/style so we compare both previews before
approval", the deliverable is TWO deployable variants, not a description. This pattern
produced the AZ Consultants V2 landing page (25 KB self-contained HTML, 6 sections, form
wired) to sit beside the hand-built V1 — client-approval-by-comparison instead of a
single-shot design argument.

## Endpoint / key

- z.ai (Zhipu GLM), OpenAI-compatible: `https://api.z.ai/api/paas/v4/chat/completions`
- Key: `ZAI_API_KEY` in `~/.hermes/.env` — read it in-process, never print it.
- Model ladder: try the strongest model once; on repeated HTTP 429 fall back to
  `glm-4.5-flash` (the one that answered) and keep the deliverable moving. A 429 usually
  means the key is shared across profiles (concurrency/rate cap), so a later retry can
  succeed — it is not a permanent denial and must not be reported as "the API is broken".
- `glm-4.5-flash` is a reasoning model: if `message.content` looks empty, inspect the
  response keys before assuming failure (it also returns `reasoning_content`).

## Generation mechanics

- Write the brief to a **file** (`<project>/zai_brief.txt`) and have a small script read it —
  long inline prompts in a tool argument get truncated and are painful to iterate.
- Contract: one complete self-contained HTML file, inline CSS + minimal vanilla JS, **no
  libraries/CDN**, one code block only; strip fences before writing `site_v2/index.html`.
- Use `stream: true`, accumulate `choices[0].delta.content`, `max_tokens` ~12000. A page
  this size takes **several minutes** — run it as a background process with
  notify-on-complete and do other work meanwhile (deploy prep, validator, screenshots).

## Brief structure that worked

1. Role + hard output contract (single file, no CDN, HTML only).
2. Brand/audience: who reads it, which disciplines/offerings exist.
3. **Style direction spelled out** — this is where "sleek, one-glance all details, easy to
   adopt, curiosity-driven" becomes an actual spec: light premium theme, bento tile grid,
   sticky slim nav, single accent colour, dense-but-calm type, key details above the fold,
   **no emoji, no stock photos, no human faces** (client hard rule).
4. **Exact copy strings to use** — H1 curiosity hook, subhead, metric tiles, capability chip
   labels, the 3 engagement names, CTA labels. Pinning copy keeps the variant on-brand and
   stops the model inventing claims or contact details.
5. The form contract verbatim: field names, `POST /api/lead`, honeypot `hp`, booking link.
   Never let it invent a phone number or an email address.
6. Responsive + "output only the HTML".

## Validate before deploy (mandatory for model-written HTML)

Run an `html.parser`-based checker that (a) asserts tag balance against a void-element list
and (b) asserts every required copy string, the endpoint path, the honeypot, and the booking
link are present, plus a `<section>` count. Flash-tier HTML is fine one day and broken the
next; this is the cheap gate before a preview URL reaches the client.

## Presenting the comparison

Deploy the variant on its own preview branch (see `cloudflare-pages-ops` →
`references/pages-previews-secrets-and-lead-endpoints.md`), screenshot both variants at
1440px and 390px, and present them as A / B — one line each on feel and on what the client
gains — plus a third "hybrid" option (A's hero + B's density) when the trade-off is obvious.
End with an explicit numbered choice so the client only has to reply "A", "B" or "C".
