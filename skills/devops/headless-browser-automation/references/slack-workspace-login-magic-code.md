# Slack workspace login via magic code (headless VM, zero-password) — proven 2026-08-23

Session: Layer 3 — creating 4 Slack apps (per-client bots) from Hermes manifests on
the Oracle VM. Goal was to log into api.slack.com in Xvfb GUI Chrome to create the
apps. The login flow itself was fully worked out; app creation was pending the
user's magic-code handoff when the session paused.

## 1. Discover the workspace domain without asking the user

The Slack Web API `auth.test` with the existing bot token (from `~/.hermes/.env`,
never print the token) returns team name, team domain and bot user id:

```python
import os, json, urllib.request
env = {k: v for k, v in (l.strip().split('=', 1) for l in open('/home/ubuntu/.hermes/.env') if '=' in l and not l.startswith('#'))}
tok = env['SLACK_BOT_TOKEN']                       # xoxb-...
req = urllib.request.Request('https://slack.com/api/auth.test', data=b'')
req.add_header('Authorization', f'Bearer {tok}')
d = json.load(urllib.request.urlopen(req))
print(d['team'], d['url'], d['user_id'])           # e.g. Amz, https://amz-fgw7876.slack.com/, U0BS0CGEC69
```

## 2. Global signin vs workspace signin — the trap

- `https://slack.com/signin` with the member email → **"Sorry, but that email is
  invalid."** even for a valid workspace member (global lookup doesn't see
  workspace-only accounts).
- The workspace URL `https://<domain>.slack.com/` → redirects to the workspace's
  SSO page ("Sign in to <Team>") with working options. **Always use the workspace
  URL from `auth.test`, never the global signin.**

## 3. Choose the auth method (friction ranking, fresh Xvfb Chrome profile)

1. **Magic code (BEST)** — "Enter your email address" → Slack emails a 6-digit
   numeric code. The user reads it from phone Gmail and dictates it; the agent
   types it in. ~30s user step, no password, no QR, no Google.
2. Google SSO — on a FRESH Chrome profile this always lands on the password wall
   (new-device detection). Avoid unless the user can do OTP-only recovery.
3. QR sign-in — needs the user to scan with the Slack mobile app AND approve;
   works (Discord precedent) but is heavier than reading a code aloud.
4. Reading the login email yourself via Gmail IMAP — **do NOT plan around this**:
   the `.env` GMAIL_APP_PASSWORD was stale and IMAP auth failed for the member
   email. Design the flow so the user reads the code from their phone.

## 4. DOM specifics (workspace signin page)

- Email input: `#signup_email` (type=email).
- Submit button: matches /sign in with email/i; or `Sign In With Email`.
- After submit: "Check your email for a magic code" — a code was sent; no error
  means the email is a valid member.
- `fill_input` + native-setter + `input` event + real button click (NOT Enter
  dispatch) — same rule as React textareas elsewhere in this skill.

## 5. Session hygiene that bit this run

- Reused profile dir `/tmp/chrome-gui3` (from the earlier Discord session) →
  stale Discord QR-login tab surfaced as the ACTIVE tab mid-flow. Fresh
  `--user-data-dir=/tmp/chrome-<task>` per task.
- Chrome died once mid-flow; after restart the daemon reported
  `BU_CDP_URL ... unreachable after 30s` — kill stale daemons
  (`pkill -9 -f "[b]rowser_harness"`) and retry.
- Verify Chrome is alive with `curl -s localhost:9255/json/version` before every
  CDP step.

## Next steps (context for the continuation session)
- 4 app manifests ready at `~/slack-layer3/manifests/` (luxewave/sanad/avvs/ops,
  `channels:write` + `groups:write` added so bots can create/invite channels).
- Browser was mid-login waiting for the magic code from the user
  (aamir1zahran@gmail.com, workspace "Amz" amz-fgw7876.slack.com).
- After login: api.slack.com/apps → create-from-manifest per app → Install to
  workspace → copy bot token (xoxb) + app-level token (xapp) → wire per-profile
  gateways (whatsapp profile is the proven precedent).
