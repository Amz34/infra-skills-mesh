---
name: searxng-search-lane
description: Use when a task needs unmetered web search here.
version: 1.0.0
author: Hermes (invertio ops)
license: MIT
metadata:
  hermes:
    tags: [search, searxng, infra, free-lane]
    related_skills: [blocked-page-recovery, grounded-citations, hermes-agent]
---

# SearXNG search lane (free, unmetered)

## When to Use
- A task needs many web lookups and you want to avoid vendor search quota.
- A cron/script job needs search results without an API key.
- The keyless vendor ring is rate-limiting or returning thin results.

Local meta-search instance: `http://127.0.0.1:8888` (container `vane-searxng`,
part of the vane-lab stack `~/vane-lab`). No API key, no quota. Wired into
Hermes: `SEARXNG_URL` in `~/.hermes/.env` + `web.search_backend=searxng`
(config) — the built-in `web_search` tool answers from this lane first and
falls back to the keyless vendor ring if it fails.

## Use it
- Agent sessions: call `web_search` normally.
- Scripts / cron jobs: `python3 ~/.hermes/scripts/sxng.py "query" -n 10`
  (flags: `--recent day|week|month|year`, `--news`, `--json`; exit 1 = no
  results, 2 = lane unreachable).
- Raw JSON: `curl -s -G http://127.0.0.1:8888/search --data-urlencode "q=terms" --data-urlencode format=json`.

## Pitfalls (measured 2026-09-15)
- `limit=` is not honoured by this instance — slice results yourself.
- DuckDuckGo returns CAPTCHA from datacenter IPs; Bing news throws a parsing
  error, so `categories=news` yields nothing. Use general search with
  `time_range` for freshness instead.
- Only pass `engines=` with names you verified: re-probe with
  `curl -s -G http://127.0.0.1:8888/search --data-urlencode "q=test"
  --data-urlencode format=json --data-urlencode "engines=<name>"`.
- **2026-10-07 outage + fix.** Every default general engine was throttled from this
  datacenter IP at once — brave HTTP 429 (`suspended_time=180`), google cse
  "unusual traffic", duckduckgo CAPTCHA, yep 403 — so aggregate results silently
  fell to **0** (watchdog alerted, nothing was done). `yahoo` still answered with
  relevant hits but ships `disabled: true` in the image defaults. Fix, in
  `~/vane-lab/searxng/settings.yml`:
  ```yaml
  engines:
    - name: yahoo
      disabled: false
  ```
  then `docker restart vane-searxng`, then confirm `/config` reports
  `yahoo enabled=True` and `sxng.py "python static analysis tools"` returns real hits.
- Keep total lane outages out of research paths: a 0-result response is
  indistinguishable from "no such topic". When a lane run needs findings, assert
  `len(results) > 0` and fail loudly instead of writing an empty pool.
- General queries give 30-40 results in ~1s, but quality is mixed: forum
  threads and content farms appear alongside primary sources. Verify claims.

## Health
Silent watchdog cron `SearXNG Lane Watchdog` (every 30m) alerts on Telegram if
the lane is down, broken, or returns fewer than 3 results. Manual check:
`bash ~/.hermes/scripts/searxng_health.sh` (no output = healthy).
Restart: `docker restart vane-searxng`. Detail:
`~/brains/ops/knowledge/infra/vane-answer-engine-eval-2026-09-15.md`.

## Structured-output consumers (measured 2026-09-15)

Pipelines that ask a model for a JSON schema and then parse it must not assume
compliance: cheap providers may return fenced or prose answers, and a hard
JSON.parse then crashes the request, which **hangs** instead of erroring. Put an
enforcement boundary in front: repair fences, re-ask, and return a fast 5xx on
failure. Working example: `json-shim.py` in the console kit
`~/clients/sanad/private-search-console/` (OpenAI-compatible, internal-only,
keeps the provider key in its own env).
Measured before/after on the same host: 1 usable run in 6 attempts -> gate PASS
in 111 s, 9 domains.
