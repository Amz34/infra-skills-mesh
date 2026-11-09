---
name: telegram-job-channel-ops
description: Build a Telegram job channel + Mini App board.
---

# Telegram job channel ops

Stack that works (built for @CorporateJobsHub):

```
fetch.py      harvest + dedupe + geo-score  -> feeds/jobs.json
push_kv.py    slim payload                 -> Cloudflare KV key "jobs"
worker/       Mini App UI + /api/jobs (KV + edge cache)
publish.py    state/posted.json (30d)      -> channel posts
bot.py        long-poll: /start /latest /jobs, plain text = search
run_cycle.sh  cron: fetch -> kv -> publish (skips publish if no channel)
```

Run: `systemd <project>-bot` + crontab in UTC: `40 2` (daily worldwide sweep), `15 5` (digest),
`15 9,13,17` (regular cycles). Quote the schedule from `crontab -l` before telling the user
the update times — Riyadh is UTC+3, so convert both.

## Pitfalls that cost time

- **Bots cannot create channels or add themselves as admin.** Owner must add the bot with *Post messages*. `getChatMember` returning `member list is inaccessible` means the bot is not in the chat yet.
- **`web_app` buttons are invalid in channels** (`BUTTON_TYPE_INVALID`). Use a URL button to `https://t.me/<bot>?startapp=<param>`; keep `web_app` for the bot's menu button and private-chat keyboards.
- **Cloudflare Workers 403 Python `urllib`** (default UA `Python-urllib/3.x`). Always send a custom `User-Agent` on outbound calls to your own worker.
- **Worker cache key must include the query string.** Caching `url.origin + /api/jobs` serves the first query's result to every later query — looks like a broken filter. Use `new Request(url.toString())`.
- **LinkedIn job locations repeat the city**: `Riyadh, Riyadh, Saudi Arabia`. Collapse consecutive duplicate segments before posting (worker *and* publisher).
- **Jobicy geo enum** is `anywhere|emea|apac|americas`; `middle-east` returns HTTP 400.
- **Bot token source**: read `ops/<project>/.env` first, not `~/.hermes/.env` (gateway bot — wrong bot).
- **A hand-written `form_map_ai.json` breaks the funnel silently.** `Flow` filters `q["entry"]` and `FormClient` reads `data["title"]`; a map with only titles raises `KeyError('entry')` / `KeyError('title')` and `/apply ai` dies at open. Always regenerate with `python3 extract_form.py <viewform_url> form_map_ai.json` (live FB_PUBLIC_LOAD_DATA_, gives entry ids + option lists), then run `python3 qa_funnel.py` (43 checks, no form writes) before restarting the bot.
- **Silent send failures**: wrap `sendMessage` and print `description` when `ok` is false — Telegram HTML/`web_app` errors otherwise vanish into a dead chat.
- **A QA script that imports the live bot must put only that project dir on `sys.path`.** Prepending the analyzer/engine directory first (it often has its own `bot.py`) imports the wrong module and the failure surfaces as `ModuleNotFoundError: No module named 'telegram'` — a shadowing bug dressed as a missing dependency. Import the bot, let the bot lazily add its own helper paths.
- **LinkedIn group posting is not in the API** (only `w_member_social` personal posts). Groups are UI/browser only.
- `setChatDescription`, `setChatPhoto`, `pinChatMessage` work via Bot API once the bot is admin with `can_change_info`.

## Surfacing bot services on the Mini App page

Visitors who never open the bot should still see the free services. Add them to the page,
not only to `main_kb()`.

1. **Two placements**: a one-line `.tools` strip directly under the sticky header (two
   equal links, ~8px padding, green/blue tint) for visibility, and a `#services` section
   below the list with one card per service and the same actions. Repeat the CTA; do not
   rely on the strip alone.
2. **Static blocks go OUTSIDE `#list`.** `render()` overwrites the container's
   `innerHTML`, so a card placed inside it disappears on the first filter tap or
   load-more. Put the strip between `</header>` and `<main>`, the section between
   `</main>` and `<footer>`.
3. **Deep link, not a dead end**: `https://t.me/<bot>?start=<payload>` only works if the
   bot routes that payload. Add the branch next to the existing track args:
   `if arg in ("resume", "ats", "audit"): send(chat_id, RESUME_INTRO, main_kb()); return`.
   Without it the tap lands on the generic welcome and the page looks broken.
4. **Reuse the page's real CSS variables.** Check `:root` before using a token: `var(--fg)`
   where the file defines `--txt` silently falls back to the browser default colour.
5. **Do not fake an in-page version of a server-side tool.** The ATS score runs in Python
   (`resume_analyzer`), so a browser upload needs a token-gated API in front of it. Until
   that exists, the page links into the bot and says so — an in-page "audit" with no
   scoring behind it is worse than no button.
6. **Copy on the card stays honest**: what the tool does, what happens to the file
   (scored, not published), and the daily cap — matching what the bot actually enforces.

## Free resume audit → review ask (the growth loop)

Value first, ask second, zero friction to comply. Full mechanics: `references/review-request-mechanics.md`.

1. **Intake**: document upload (`extract_doc_text`, pypdf, 12-page cap, explicit encrypted/damaged `ValueError`) or pasted text gated by `looks_like_resume` (≥160 chars) so ordinary chat never burns a model call.
2. **Score**: Gemini via raw `urllib` (no SDK, so system python needs no new package), `maxOutputTokens 4096`, trim to the last newline on `MAX_TOKENS`, model verdict `NOT_A_RESUME` decides rejection — never the input text.
3. **Deliver**: `report_to_html` + `_chunks(≤3600)`; chunk below the 4096 hard limit so an escaping bug can never split a message.
4. **Ask**: link to `…/services/page/<id>/review/create/` (the plain service page does *not* open the review composer), a `<pre>` block holding a ready draft the reviewer taps to copy, plus a `🔄 Different draft` callback that regenerates. Never claim the review box is prefilled — LinkedIn accepts no prefill parameter; the copy block *is* the prefill.
5. **Draft variety**: slot pools (opener × middle × closer × optional emoji) mixed at random, no repeat inside the user's last 8 and the bot-wide last 80, persisted in `state/`. Same wording across two public profiles reads as astroturf.
6. **Honesty**: one line in the bubble asking the reviewer to swap a word so it sounds like them, and draft text that praises only what the product actually did (free, fast, specific) — no invented interview outcomes.

## What the audit costs (measured, not guessed)

- Billing is Gemini API tokens only, on the single `generateContent` call per audit. Telegram calls, PDF/DOCX parsing, job fetching and the review-draft generator are all local and free.
- `gemini-3.5-flash-lite` (primary): ~626 prompt + ~594 output ≈ **1,220 tokens, ~3s** per audit; `gemini-3.6-flash` fallback ≈ 2,684 tokens (thinking tokens included), ~11s. Read `usageMetadata` from a raw call when the user asks for real numbers — do not estimate.
- Paid-tier equivalent ≈ **$0.0003/audit** ($0.30 per 1,000). On the free tier it is $0 until the per-model daily cap (~500/day flash-lite, shared fleet-wide) runs out.
- `RESUME_DAILY_CAP = 4` per user per day bounds the worst case; the counter lives in `state/resume_audits.json`.
- Review drafts explicitly cost **0 tokens** — say so, because the obvious assumption is that every generated string is a model call.

## QA sweep before declaring done

1. `getChat` — title, username, description length, photo present.
2. `getChatMemberCount` + `getChat` `pinned_message` id.
3. Public proof: `curl -A 'Mozilla/5.0' https://t.me/s/<username>`, grep `og:description`, post count, pinned.
4. `/api/jobs?q=<term>` totals must equal a local count over `feeds/jobs.json` — mismatch = cache-key bug.
5. Bot handler dry test: import `bot.py` (it is `__main__`-guarded, so importing is safe),
   monkeypatch `send` **and** `funnels` — `handle()` reads `funnels().active` on entry and
   crashes on a stub otherwise. `bot.funnels = lambda: type("F", (), {"active": {}})()` then
   feed `{"chat":{"id":1},"from":{"username":"t"},"text":"/start <payload>"}` and assert
   the first line sent. This proves a new deep-link branch in seconds.
6. Worker change ships in this order: `node --check src/index.js` → `npx --yes wrangler@latest deploy`
   (wrangler lives behind npx; a bare `wrangler` is often not on PATH) → grep the live HTML for the
   new markup and every new `href` → run the existing `qa_worker.mjs` → 390px headless screenshot
   of both placements. A 200 from the root URL proves nothing about the block you added.
7. Keep a repeatable `qa_<feature>.py` next to the bot (compile changed files, assert routing strings, run the live model once, assert chunk sizes, call the sibling `qa_funnel.py`) and end with `RESULT n checks, m failed` + non-zero exit. One command to re-run after every edit beats ad-hoc transcripts.
