# Telegram Mini App on a Worker + KV

Pattern: a bot whose real product is a searchable board (jobs, catalogue, listings). The Worker
serves the UI and a JSON API from KV; the VM cron owns harvesting and pushes the snapshot. Cheap
(free tier), no server, no redeploy per data refresh.

## Architecture that works

```
VM cron  fetch.py ──► feeds/jobs.json ──► push_kv.py ──► KV key "jobs"
                                                          │
Telegram ── menu button / web_app button ──► Worker ────────┘  GET / (UI)  GET /api/jobs (JSON)
```

- One Worker, two GETs: `/` (inline HTML, inline CSS/JS — no build step, no asset upload) and
  `/api/jobs` (filters + `limit` applied server-side). Add `/health` returning `{ok,count,fetched_at}`
  so cron/liveness checks are one curl.
- Data refresh = `PUT /accounts/<acc>/storage/kv/namespaces/<ns>/values/<key>` with the whole JSON.
  Redeploying the Worker per refresh wastes deploys and is slower than a KV write.
- Slim the payload at push time (title, company, location, url, source, posted). Internal scoring
  fields (`_geo`, `_prio`) stay on the VM.

## Headers the webview needs

```
content-type: text/html; charset=utf-8
x-frame-options: ALLOWALL
content-security-policy: frame-ancestors 'self' https://web.telegram.org https://*.telegram.org
```

Load `https://telegram.org/js/telegram-web-app.js`, then on boot `tg.ready(); tg.expand();` — without
`expand()` the app opens as a half-height sheet. `tg.HapticFeedback.selectionChanged()` on filter
changes is the cheap native feel. Guard every `tg.*` call: the same URL must render fine in a plain
browser (that is how you QA it).

## Wiring it to the bot

```python
api("setChatMenuButton", menu_button=json.dumps({
    "type": "web_app", "text": "Browse jobs",
    "web_app": {"url": "https://<worker>.<account-subdomain>.workers.dev/"}}))

# inline keyboard on /start and every reply
{"inline_keyboard": [
    [{"text": "🔎 Open board", "web_app": {"url": MINIAPP}}],
    [{"text": "📢 Join the channel", "url": CHANNEL},
     {"text": "❓ Help", "callback_data": "help"}]]}
```

The URL must be HTTPS; `*.workers.dev` is fine. `web_app` (not `url`) is what opens in-app — a plain
`url` button kicks the user out to a browser and loses the Mini App context.

## Bot command surface for the same data

Keep the bot useful without the Mini App: `/latest` (top N) and `/jobs <keyword>` (search over the
same API, `parse_mode=HTML`, `<a href>` per item). Bot and app read the same `/api/jobs`, so one
harvest update refreshes both.

## QA loop (before telling the user it is live)

1. `curl -s .../health` → `{ok:true,count:N,fetched_at}` with N matching the harvest log.
2. `curl` the API with each filter (`?geo=ksa`, `?q=accountant`) and assert the counts move.
3. `browser_exec` with `cdp('Emulation.setDeviceMetricsOverride', width=390, height=844, mobile=True)`
   + `capture_screenshot()` — inspect the screenshot yourself for overflow, sticky-footer overlap,
   and duplicate location text. **Re-apply the metrics override after every navigation** (a `goto_url`
   or reload clears it and you end up screenshotting a 1280px desktop layout).
4. Interaction, not just render: set `#q` value + `dispatchEvent(new Event('input'))`, click a filter
   chip, then count `.card` nodes — proves the search/filter path, not only the first paint.

## Pitfalls

- **Location strings arrive duplicated** from aggregators (`Riyadh, Riyadh, Saudi Arabia`). Collapse
  consecutive duplicate segments server-side in the API response, not in the UI, so the bot and the app
  both get clean text.
- **The join/CTA button points at a channel that may not exist yet.** `getChat` → `chat not found`
  means that CTA is a dead link; either ship the channel first or state plainly that the button goes
  live when the channel does.
- **Don't render untrusted job text with raw `innerHTML`.** Escape `& < > "` in every interpolated
  field before building card HTML — feed data is third-party input.
- **Edge cache masks KV updates**: `caches.default` + `max-age=300` means a push can take up to 5 min
  to appear. Fine for a job board; know it before declaring a push "not working".
