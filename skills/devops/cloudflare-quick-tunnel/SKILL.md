---
name: cloudflare-quick-tunnel
description: "Use when a local service needs a public HTTPS URL."
---

# Cloudflare Quick Tunnel — Public HTTPS for Local Webhook Receivers

Use when a local service (webhook handler, bot callback, dev server) needs a public HTTPS URL. Classic case: **Shopify webhooks require HTTPS** — a plain `http://VM_IP:port` endpoint gets rejected. Quick tunnels give `https://<random>.trycloudflare.com` with zero account setup.

**Also the standard answer to "preview link chahiye?"** for a locally-built site/staging page (proven 2026-08, AVVS 3D site): start a tunnel on the dev server port (`python3 -m http.server 8778`) and hand the user the URL. Works as a pre-deploy client demo — then deploy for real only after approval. Verify the tunnel serves the actual page (HTTP 200 + title in HTML), not just the port.

## Steps

1. **Start the tunnel** — ALWAYS with `--logfile`; without it the URL line is easy to lose in captured stdout:
   ```bash
   cloudflared tunnel --url http://127.0.0.1:8645 --no-autoupdate --logfile /tmp/cf-tunnel.log &
   ```
2. **Extract the URL** (appears ~10s after start, line `Your quick Tunnel has been created!`):
   ```bash
   grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" /tmp/cf-tunnel.log | tail -1
   ```
   The log has the URL banner; grep preserves log order (= chronological), so `tail -1` = newest.

   **PITFALLS (learned the hard way):**
   - **NEVER pipe through `sort -u` before picking the URL** — it reorders lexicographically. After a tunnel restart the NEW URL may sort first, so `sort -u | head -1` / `tail -1` can hand you the OLD, dead URL → Cloudflare 530 on every request (false "tunnel broken" alarm).
   - **HTTP 530 from the public URL ≠ service down.** It means the edge can't reach the tunnel — almost always you're testing a dead/old URL, or the restarted tunnel is still handshaking (~10s). Re-grep the log for the current banner; check the origin locally (`curl -s localhost:PORT/api/health`) to separate "app down" from "wrong URL".
   - **URL changes on EVERY restart** (trycloudflare assigns random names). Never hardcode/share an old URL after a restart; read it from the log. If a stable URL matters, use a named tunnel on a real zone instead.
   - **`cloudflared ... &` inside a shell exits with the shell** (Hermes terminal call ends → tunnel dies, exit -1). Run it via `terminal(background=true)` (persists across calls, logs to file) or, for crash-proofing, a systemd unit:
     ```
     [Service]
     ExecStart=/usr/local/bin/cloudflared tunnel --url http://127.0.0.1:PORT --no-autoupdate --logfile /home/ubuntu/logs/cf-TUNNEL.log
     Restart=always
     RestartSec=3
     OOMScoreAdjust=-500
     ```
     Verify: SIGKILL the tunnel process → systemd respawns it → new URL in log → public health 200.
   `tail -1` (NOT `sort -u | head -1`): grep preserves log order = chronological, so tail gives the NEWEST URL. `sort -u` reorders lexicographically — after a tunnel restart the alphabetically-first URL may be the OLD dead one (verified 2026-08: tested a dead URL → false 530 alarm).
3. **Health-check** the tunnel → local handler:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" https://<tunnel>.trycloudflare.com/healthz
   # 501/404 = tunnel reaching your server (GET on a POST-only route is fine); 000 = not reachable yet
   ```
4. Give the tunnel URL to the webhook provider (Shopify etc.).

## Live-refreshing pages behind a tunnel (pairing QR, status dashboards)

When the served content **regenerates on its own** (WhatsApp device-pairing QR emits a fresh code every ~20–60s, each valid ~60s), never render-and-send a one-shot image — the delivery round-trip loses the race and the user reports "code expired" repeatedly. Serve a page that auto-polls the freshest value instead (proven 2026-09: WhatsApp re-pair fixed this way):

1. **Run the backend with `terminal(background=true)` and redirect stdout to a log file INSIDE the command**: `node bridge.js … > /tmp/app.log 2>&1`. (`setsid nohup … &` wrappers get parser-blocked exit -1 before the redirect runs — then the log file never exists and the only copy of events sits in process-poll output.) With background=true + inner redirect, JSON event lines (`{"ts":<epoch_ms>,"qr":"https://wa.me/settings/linked_devices#…"}`) land in the file for any server/page to parse.
2. **Small poll server** (see `scripts/live-qr-page.py` — known-good 2026-09): reads the log's newest event, renders the QR PNG cached by ts (node `qrcode`), and serves HTML whose JS polls every ~4s, swapping `<img>` only when ts changes. Expose with `cloudflared tunnel --url http://127.0.0.1:PORT`.
3. **Page bugs that both manifest as UI stuck on "Connecting…" while curl works fine** (both hit in 2026-09):
   - **Relative asset URLs on a token route**: page served at `/TOKEN` (no trailing slash) makes `src="qr"` resolve to `/qr` (root), NOT `/TOKEN/qr` → 404 forever. Use absolute paths (`/TOKEN/qr`) in the HTML/JS.
   - **One endpoint, two content types**: an endpoint returning `{"ts":0}` JSON while idle but `image/png` once data exists breaks a JS poller that unconditionally calls `r.json()` (throws on PNG → catch → "Connecting…" loop). Split the roles: `/TOKEN/qr` → JSON poll only; `/TOKEN/qr.png?ts=N` → image only; `<img>` loads the PNG independently of the poll.
4. **QR = device-link grant**: the tunnel URL effectively lets anyone with it pair a device. Add an unguessable path token, don't post the URL in shared channels, and kill the tunnel + server once pairing completes.

## Closing a tunnel — and answering "koi use kar raha hai?"

Kill it properly: a tunnel started with `terminal(background=true)` must be stopped with
`process(action="kill", session_id=...)` — not `pkill` (see pitfalls). Then prove BOTH halves:

- `curl -s -o /dev/null -w "%{http_code}" https://<url>/path` → **530** (Cloudflare 1033 = tunnel gone).
  This is the one time 530 is the *desired* result, not an alarm.
- `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:PORT/path` → still **200** = you closed the
  exposure, not the app.
- No leftover tunnel on that port: run `pgrep -af cloudflared | grep <port>` and **read the match line** —
  the pipeline matches its own command line, so a bare count of `1` is usually the grep itself, not a
  live tunnel.

**Usage / attribution check — do this BEFORE claiming anything either way.** Quick tunnels at default
loglevel log the banner and connection registrations but **no per-request lines**, so if the origin
server keeps no access log there is zero attribution after the fact. The only counter is cloudflared's
own metrics endpoint; find its port in the logfile, then query it:

```bash
grep -aoE "Starting metrics server on [0-9.:]+" /tmp/cf-tunnel.log
curl -s http://127.0.0.1:<port>/metrics | grep -E "^cloudflared_tunnel_(total_requests|request_errors|response_by_code)"
```

That yields tunnel-wide totals (measured 2026-09: `240` requests, `229×200` + `11×404` favicon,
`0` errors) — but they include your OWN curl calls and a page's own auto-refresh polling, so they can
never prove "nobody else opened it". Report it honestly ("counts consistent with my own traffic; no
access log existed") instead of presenting a total as evidence of zero third-party access.

**If attribution may matter later** (a preview link handed to a client or opened on the user's phone),
add request logging at the ORIGIN server (timestamp, client IP, User-Agent, path) or start cloudflared
with `--loglevel debug`. Retrofitting after the fact is impossible.

**Exposure hygiene**: an unauthenticated tunnel serves whatever the port serves to anyone holding the
URL. Share it as a temporary link, close it as soon as the user is done, and prefer the copy-preview
pattern (a read-only copy of the page behind the tunnel) over exposing prod.

## Answering "link do" after the fact (URL recovery + safe handover)

The tunnel was started hours or days ago and the user now wants the URL. Recovery order:

1. **Find who owns it** — `systemctl --user list-units '*tunnel*' --all --no-pager`, then
   `systemctl --user cat <unit> | grep -E 'ExecStart|logfile'` gives both the **origin port** and the
   `--logfile` path. These are user-scope units: `systemctl status <name>` as root shows nothing and
   invites the false "service doesn't exist" conclusion.
2. **Read the CURRENT URL from that logfile** —
   `grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' <logfile> | tail -1`. `tail -1` is the newest
   (grep preserves log order); never `sort -u` first. The URL rotates on every restart, so re-read it
   every time instead of reusing a remembered one.
3. **Verify from outside before sending it** — `curl -s -o /dev/null -w '%{http_code}' <url>/<path>`.
   `530`/`000` = stale URL or still handshaking; check the origin locally
   (`curl -s http://127.0.0.1:PORT/health`) to separate "app down" from "wrong URL".
4. **If the app gates on an access code, put it in the URL fragment** — `https://host/#k=CODE`.
   A fragment never reaches the server, so the code stays out of access logs and referrer headers
   while the link stays one-click for the operator. Confirm both states (no code → 401, with code →
   200) instead of describing the auth as "should work"; a 200 without the code means the gate is off.
5. **Say what the link is.** A quick tunnel has no access control, so anything that leaves the
   building must be a named tunnel + Cloudflare Access. When a product has both a static public demo
   and a live operator console, hand over the demo for third parties and keep the console URL
   internal — never send the console URL to a reviewer just because it is the more impressive one.

## Pitfalls

- **DNS propagation delay**: trycloudflare subdomains take 30–120s to resolve. `curl` failing with `000` right after start is normal — wait and retry. NXDOMAIN from the LOCAL resolver (systemd-resolved) can persist after the public DNS already resolves (check: `dig @8.8.8.8 <url> +short` — if it returns Cloudflare IPs, the tunnel is fine, local cache is stale). Flush with `sudo resolvectl flush-caches`.
- **Local testing workaround** when the VM's own resolver is stale: pin the IP in `/etc/hosts`:
   ```bash
   echo "<cloudflare-ip> <tunnel-url>" | sudo tee -a /etc/hosts
   ```
   Only needed for testing FROM the same VM — external callers resolve normally.
- **Port conflict on restart**: old handler process may still hold the port with stale config. Check `ss -tlnp | grep <port>` and kill by PID (`kill <pid>`) before relaunching. Do NOT `pkill -f <scriptname>` from a heredoc shell — the pattern matches the shell command line itself and kills your own shell (exit -15). Use `pgrep -f <name> | xargs -r kill`.
- **Quick tunnels are ephemeral**: no uptime guarantee, URL changes on restart. Fine for demos/tests; production webhooks need a named tunnel or real domain.
- **Apps with hardcoded site URLs (WordPress) 301-loop behind the tunnel**: WP's `siteurl` fixed to `http://127.0.0.1:PORT` makes the tunnel URL redirect to `https://<tunnel>:PORT/` → loop/timeouts. Fix with dynamic `WP_HOME`/`WP_SITEURL` in wp-config from `$_SERVER['HTTP_HOST']`, stripping `:port` only for `trycloudflare.com` hosts — full recipe in the `wordpress-docker-staging` skill.
- `--dns-servers` curl flag is NOT supported by all libcurl builds — use the /etc/hosts or `--resolve` route instead.

## Verification

- Tunnel URL resolves publicly (from another machine or `dig @8.8.8.8`).
- Provider webhook → handler returns 200 with correct auth (e.g. HMAC header).
- 401 from handler = secret mismatch (handler env vs test secret), not a tunnel problem.

## Related

- `shopify-whatsapp-bot` — Shopify webhook → WhatsApp pipeline this tunnel serves.
- `hermes-cloud-vm-ops` — VM networking context.
