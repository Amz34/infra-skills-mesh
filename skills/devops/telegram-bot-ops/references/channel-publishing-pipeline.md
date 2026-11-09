# Telegram channel publishing pipeline

Turning a Telegram channel into an automated content surface: verify the handle, hand off the one
action a bot cannot do, then feed and post on a schedule.

## 1. Handle check before any build ("activate this channel")

```bash
# Bot API answer, authoritative enough to act on
curl -s "https://api.telegram.org/bot$TOK/getChat?chat_id=@CorporateJobs"
# {"ok":false,"error_code":400,"description":"Bad Request: chat not found"}
```

- `chat not found` = the username resolves to nothing: a deleted/released channel, or never existed.
  A user account can usually claim it. Compare against a live handle (`@durov`, `getChat` ok=true)
  before believing the error.
- `t.me/<name>` rendering the generic "contact @name" stub corroborates, but HTML scraping alone
  cannot distinguish free vs reserved — always pair it with `getChat`.
- Only the user's client can prove assignability; do not promise the exact username. Have alternates
  ready (`…HQ`, `…KSA`, `…Official`) and check those with `getChat` too.

## 2. Channel creation is the user's step — plan around it, don't stall on it

No Bot API method exists to create a channel/group. Do not wait to build: finish the whole pipeline
first, then hand off two taps and say precisely what they unlock.

1. App → New Channel → title + username (give the exact spelling).
2. Channel → Administrators → add the bot → **Post messages** only.
3. Return the `t.me/…` link; resolve the numeric id with `getChat` or the first `sendMessage`.

## 3. Post format

- `sendMessage` with `parse_mode=HTML`, `disable_web_page_preview=true`, body ≤ 3900 chars.
- One item per post, fixed field order (title / org / location / pay / tags / apply link), then a
  one-line forward-CTA footer. Fixed order is what makes the channel look produced rather than dumped.
- Hashtags: 2 channel tags + one topical tag; skip tags for sources that supply vendor noise.

## 4. Cadence and dedupe

- Batch N per cron run (2 posts every 3h ≈ 6/day) inside the audience's waking hours, not per item.
- Alternate geographies/segments between posts — sorting purely by score turns the feed into one city
  or one country and readers churn. Track `last_geo` in `state/meta.json` and start the next run with
  the other bucket.
- Dedupe twice: URL minus query string, and normalized title prefix — aggregators re-list the same
  role under different ids. Keep a 30-day TTL in `state/posted.json` so a stale feed cannot repost.

## 5. Keyless job harvesting (LinkedIn guest endpoint is the workhorse)

```
https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search
   ?keywords=<role>&location=<city, country>&start=0
```

- Returns HTML cards from a server IP; parse with regex on `base-search-card__title`,
  `base-search-card__subtitle`, `job-search-card__location`, `base-card__full-link` href,
  `datetime="…"`. No key, no login.
- **The 429 wall is the design constraint, not an error to retry through.** Cache each
  (geo, keyword) result for ~6h and cap fresh fetches per run (~8) with ~3.5s spacing; on 429 fall
  back to the cached card set. Unbounded keyword × city loops burn the quota in one run and the next
  cron tick gets nothing.
- Supporting keyless feeds: `remotive.com/api/remote-jobs`, `jobicy.com/api/v2/remote-jobs`
  (`geo=apac` works, `geo=middle-east` returns 400), `himalayas.app/jobs/api`, `arbeitnow.com/api/job-board-api`
  (EU-heavy — drop `(m/w/d)` / `(m/f/d)` titles), WeWorkRemotely RSS (follow the 301).
- Drop unpaid/commission-only/equity-only rows and dedupe titles before scoring.

## 6. Score for the audience, not for freshness alone

Sort key = (target-geo weight, role-priority regex, recency). Geo weight first is what keeps a
"corporate jobs" channel relevant to an India/GCC audience instead of flooding it with US remote roles.

## 7. Growth is part of the deliverable

Pinned "how to apply" post with the invite link; channel link in the owner's LinkedIn/X posts; weekly
"top 10 this week" roundup (the shareable format); directory listings; post at commute/lunch hours.

## 8. Credential read gotcha

Hermes can redact secrets in tool output — a `.env` token can print as `8821683733:***` while the file
is intact. Judge by `len()` and shape regex, not by the printed value, and use the value in-process
(`urllib` inside `execute_code`) rather than echoing it into a shell command.

Reference implementation: `~/ops/corporatejobs/fetch.py` (harvest + format) and `publish.py`
(dedupe, geo mix, `--dry-run`), driven by cron.
