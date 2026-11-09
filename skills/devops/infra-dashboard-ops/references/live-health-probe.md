# "Is the dashboard healthy right now?" — one-pass probe + preview teardown

Two jobs live here: (1) a copy-paste health probe over the live endpoint, and
(2) the checklist for sharing a preview/tunnel and shutting it down cleanly.

## Health probe (never read source to answer "prod theek hai?")

```bash
D=/home/ubuntu/clients/invertio/infra-dashboard
systemctl is-active infra-dash.service            # prod runs at SYSTEM scope
systemctl list-timers --all | grep infra          # collector one-shot, ~2 min
stat -c '%n %y' $D/status.db                      # freshness (mtime)
curl -s http://127.0.0.1:8765/data.json > /tmp/d.json
```

Top-level keys are the FIXED list
`api, avail, eco, fixes, groups, host, iso, now, ok, ts, updated_age_s`.

**The only correct "anything down?" traversal** (write it to a file, don't inline it):

```python
import json
d = json.load(open("/tmp/d.json"))
items = [it for g in d["groups"] for it in (g.get("items") or [])]
bad   = [it for it in items if it.get("st") != "up"]
print("items:", len(items), "| not-up:", len(bad))
for it in bad:
    print("!", it.get("label"), "->", it.get("detail"), "|", it.get("st"))
```

- Items carry **`st`** (`up|warn|down|off`) — there is **no** `status`/`level`/`ok`
  per item, and a group's entries live under **`items`**, not `checks`. A probe
  written against the wrong keys finds nothing, prints "0 down", and you report
  ALL-CLEAR while an item is `warn`. Dump the shape first:
  `json.dumps(d["groups"][0], ensure_ascii=False)[:400]`.
- Healthy baseline: **58 items, 57 up, 0 down, 1 warn** — the standing warn is
  the agent memory store (`MEMORY n/4000 · USER n/2000`), i.e. the box warning
  you that Aamir's Hermes memory is near-full. Report it as an action item, not
  as a downed service.
- `cached.json` can sit ~23 h old by design (TTL cache); freshness truth is
  `status.db` mtime + the payload's own `updated_age_s` (~15-35 s).
- Never trust a probe run inline in a chained shell one-liner: it came back
  `lines 42 malformed 42` (false) and once with empty output. `write_file` the
  checker to `/tmp/…py` and run **that**.

## Sharing a preview, then closing it

Pattern used for the OpenUI pilot (see `generative-ui-panel-layer.md`):

1. Build the **copy** preview (`make_preview.py`), serve it locally, verify with
   `stat -c '%n %y'` that prod files are older than the spike.
2. Expose with `cloudflared tunnel --url http://127.0.0.1:<port>` (quick tunnel).
   Keep the log (`/tmp/cf-*-preview.log`) — its metrics endpoint
   (`Starting metrics server on 127.0.0.1:<p>`, then `/metrics`) is the only usage
   evidence you get.
3. **Attribution limit — say it out loud**: the spike server keeps no access log,
   so cloudflared's counters are all you have. Observed 240 requests
   (229×200, 11×404 favicon, **0 errors**) — every one attributable to your own
   verification + the page's 20 s auto-refresh, i.e. **no proof any outsider
   viewed it**. Do not claim a human saw the link.
4. Meanwhile the copy's preview layer issues **0 LLM calls** (public view:
   `tool calls 19 | LLM calls 0`) — safe to show.
5. Close on request: kill the cloudflared session (not `pkill` blindly), then
   prove it — public URL → **530**, loopback → **200**,
   `pgrep -af cloudflared | grep <port>` → **0**. Prod files still 2026-09-10.

## OpenUI rollout verdict (keep until a revisit trigger fires)

- **Into prod now: no** panel layer. Reasons: prod already renders 58 live checks
  with zero LLM calls; generation on this box is ~193 s/panel (ARM, no GPU); OUI-1
  model is absent (llama.cpp PRs open, Ollama manifest 404); and it would add a
  generated-text→UI path to a private dashboard for no gain.
- **The two cheap wins that survived the spike** — do these instead:
  1. **Request logging at the origin server** (the repo had none; it is why the
     preview could not be attributed to anyone). Staged 2026-09-13 — design +
     verification + apply plan in `prod-server-change-protocol.md`.
  2. **Written tunnel hygiene**: the private dashboard never goes on a naked quick
     tunnel (Caddy password + firewall stay); share a *copy-preview* instead.
- **Revisit triggers**: OUI-1 (or any small model) running locally + fast; a real
  ad-hoc "generate me a view" ask from Aamir; a GPU/offload path appearing.
