---
name: telegram-bot-ops
description: "Use when running Telegram long-poll bots on servers."
version: 2.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [telegram, bot, devops, polling, watchdog]
---

# Telegram Bot Operations

Use when deploying, restarting, migrating, or debugging a Telegram long-polling bot on a server (VM/VPS). Covers the patterns that keep a bot alive 24/7, the token-conflict rule, and client-bot mirror setups.

## Core rules

1. **ONE poller per bot token.** Two processes calling getUpdates with the same token → `HTTP 409 Conflict` on one of them. Telegram only serves the poller that holds the current offset. When migrating or duplicating a bot across hosts, verify only ONE instance runs — check EVERY host (this bites hardest after multi-VM setups; a duplicate bot on a second instance 409s silently in the log).
2. **Watchdog pattern:** cron `*/5 * * * *` running a `watchdog.sh` that does `pgrep -f "python3 bot.py" || nohup python3 bot.py >> bot.log 2>&1 &`. The pgrep pattern MUST match the real process cmdline. Before stopping a bot for migration, REMOVE its watchdog cron first — otherwise it resurrects and conflicts with the new host.
3. **Retry-hardened sends:** a `send()` wrapper with 3× retry + backoff, because transient DNS/network errors lose replies permanently (getUpdates pends server-side, but failed sendMessage is gone).
4. **Owner mirror with tap-to-DM button:** mirror every client message to the owner with an inline URL button `{"text": "Message Client", "url": link}` where link = `https://t.me/<username>` or `tg://user?id=<chat_id>` (works username-less; NEVER `t.me/<firstname>` — may hit a stranger).
5. **Durable run:** `terminal(background=true, command="cd <botdir> && python3 bot.py >> bot.log 2>&1")` or systemd user service. bot.log mtime is NOT liveness — a Hermes-background instance writes to its pipe, not the file. Verify with `ps aux | grep "[b]ot.py"`.

## Telegram API limits — channels & forum topics

- **Bots CANNOT create channels or groups via Bot API** — no such method exists. If the user wants a dedicated channel for bot/cron content, they must create it manually and add the bot as admin (channels require bot-admin to post). **Check the handle before building anything:** `getChat?chat_id=@Name` returning `chat not found` means the username is free/released (a deleted channel can be reclaimed) — then build the full posting pipeline first and hand the owner only the two taps (create channel, add bot as admin with *Post messages*). Full flow: `references/channel-publishing-pipeline.md`.
- **Automated channel posting** (feed → score → dedupe → scheduled posts, plus the keyless LinkedIn guest jobs endpoint and its 429/caching rule): `references/channel-publishing-pipeline.md`.
- **A BotFather “Done! Congratulations on your new bot” paste is NOT the channel.** Asked to “activate” a channel, users routinely go create a bot instead (`/newbot`) and report it as done. Say it in one line — bot and channel are separate objects — then repeat the create-channel taps; do not build on the assumption the channel exists (re-run `getChat` to prove it). Reassure with the namespace rule so they stop trying alternate spellings: **bot usernames must end in `bot`, so `@CorporateJobs` stays free for the channel even while `@CorporateJobs_Bot` exists.**
- **Telegram Mini App = the public, searchable surface for a feed** (job board, catalogue, booking) when a channel alone is the wrong UX. Serve an HTTPS page from a Worker and hang it off the bot with `setChatMenuButton` (`{"type":"web_app","text":"Browse","web_app":{"url":…}}`) plus an inline `web_app` button; full recipe, headers and QA loop: `references/mini-app-webapp.md`.
- **Forum topics:** `createForumTopic` works ONLY in groups with topics enabled — otherwise HTTP 400 `"the chat is not a forum"`. Detect capability first: `getChat` → `result.is_forum` (true/absent).
- **Workaround for "separate channel" requests:** deliver into the existing group with strong per-message branding (🎓 headers, numbering), or redirect delivery to a user-made channel via cron `deliver=platform:chat_id`.

## Pitfalls

- **Remote poller hunt:** when a gateway logs 409 conflicts continuously but `ss -tnp | grep -E '149\.154\.|91\.108\.'` shows ONLY ONE local process connected to Telegram → the second poller is on ANOTHER HOST (laptop desktop app with the same token, second VM). Check `/proc/<pid>/environ` for `TELEGRAM_BOT_TOKEN` per process to map pollers; blank the token in non-owner profiles' `.env` so a config flip can never re-enable polling. Desktop app on laptop = UI client ONLY if paired to the server gateway; a standalone local install with the same token polls independently and 409s the server. **Check the webhook first:** `getWebhookInfo` → if `url` is non-empty, `deleteWebhook` instantly fixes long-poll 409s (seen on Sanad bot Aug 2026 — conflict was a stale webhook, NOT a duplicate poller). Only after confirming webhook is empty, hunt for duplicate instances (`ps aux | grep "[b]ot.py"` on ALL hosts), then kill the duplicate and remove its watchdog cron. Log lines showing 409 are often stale — check if the log still GROWS before concluding the conflict persists (`stat -c%s log`, sleep, re-stat).
- **409 storm vs resource problem — the cliff rule (expert insight).** A 409 storm looks like a resource issue, and under real load you DO get genuine 409s — the logs aren't fully lying. **The discriminator is timing pattern, not volume:** resource degradation climbs/falls *proportionally* with load (no single time bucket dominates); a stale-webhook storm *cliffs* — continuous 409s from the moment the webhook was set, so ONE minute bucket carries the majority of errors. Diagnose: (1) `getWebhookInfo` first — one-call root cause; (2) if clean, bucket the 409 log lines by `YYYY-MM-DD HH:MM`; top bucket > 50% of errors → config event (webhook/deploy/duplicate instance), else resource issue (rate limits, memory, connection pool). A ready classifier: `Amz34/selfhosted-agent-stack` → `scripts/telegram_409_diagnose.py`.
- **Ship the poller before you hand over the link.** A brand-new bot with no running process silently swallows `/start` and “Hi” — the owner reads that as a broken bot. Start the poller (systemd `Restart=always`) first; a first `getUpdates` at `offset=0` replays the backlog, so early messages still get answered, just late.
- **Non-text updates** (photo/sticker/voice) must be handled explicitly: polite nudge + menu, and mirror the media type to the owner. `edited_message`, `my_chat_member`, `channel_post` should be skipped silently.
- **Rate limits during startup:** rapid `setMyName`/`setMyDescription`/`setMyCommands` calls can 429; the profile setup is best-effort, polling starts anyway.
- **Language auto-detect:** if a bot replies in the user's language, store `langs[chat_id]` so callback-button presses reply in the same language (callbacks are ASCII, they don't carry language).
- **Never name a reply string the same as its keyword set** — the tuple definition overwrites the string (real bug; guard with a route() test suite).

## Verification

- Route-level test suite: monkeypatch `send`/`answer_cb`/`send_voice` to no-ops, `reset()` state dicts per case, multi-turn booking flows call `route()` directly WITHOUT reset between turns (reset kills the state machine). Assert reply copy contains the page link it promises.
- After any restart: check startup line in bot.log, `ps` for the process, and send a real message (or have the owner test with a second account).

## Sanad bot specifics

⚠️ **STATUS (Aug 18 2026): @SanadGulfbot DELETED** — testing bot tha, ab koi live client bot nahi. Files removed from VM, watchdog cron removed, webhook cleared (conflict root cause), backup at `~/ops/backups/sanad-bot-final-20260818.tar.gz`. Remaining sections = historical record + reusable pattern for future client bots.

## Hermes gateway bots (this VM)

When the bot runs as a **Hermes profile gateway** (not a standalone bot.py), see `references/hermes-multi-profile-gateway.md` for: bot→profile token mapping (Zma1_bot shared across 6 profiles) and the DeepSeek model block.

### Bringing a NEW token live as its own profile ("<link> — is bot ko on karo")

Full verified flow (Sep 2026): `references/new-bot-profile-onboarding.md` — pre-flight `getMe`/`getWebhookInfo` without ever printing the token → `profile create --clone` → token swap in the profile's own `.env` → `gateway install --start-now --start-on-login` → guardrail drop-in → restart → `autonomy.json` surface declaration → verification ladder; one-command helper: `scripts/onboard_bot_profile.sh <profile> <bot_token> [owner_tg_id]` (runs steps 0–6, never echoes the token). The non-obvious parts:

- **`profile create --clone` copies the ACTIVE profile** — verified: a new bot inherited a *client* profile's `SOUL.md` (its brand voice) and every secret in its `.env`. Review SOUL.md and strip what the new bot must not carry.
- **A freshly installed unit does NOT inherit the fleet guardrails.** Copy `hermes-gateway.service.d/99-guardrails.conf` into `hermes-gateway-<profile>.service.d/`, append `TimeoutStopSec=180` + `KillMode=mixed` (state.db WAL safety), then `systemctl --user daemon-reload` (limits only change on restart). Match the fleet — every gateway here shows `CPUQuotaPerSecUSec=infinity`.
- **Platforms auto-enable from token presence, not config** (`config get platforms.<x>.enabled` → `not set` on every profile). So cloned `SLACK_*` keys make the new gateway fight the other profile over the app token: `Slack app token already in use by <profile>` + infinite reconnect. Strip `SLACK_*` from the new profile's `.env` and restart.
- **Restart path when the guard bites:** `systemctl --user restart hermes-gateway*` is refused from inside a gateway (`blocked: restarting a hermes gateway`), but the Hermes CLI passes — `HERMES_HOME=~/.hermes/profiles/<p> <venv>/bin/python -m hermes_cli.main gateway restart` (prints the new PID). Prefer it over the older Python-subprocess workaround; `daemon-reload` / `is-active` / `show` are always allowed.
- **Verification stops at outbound unless the owner tests inbound:** gateway.log `Connected to Telegram (polling mode)` + `Sent home-channel startup notification to telegram:<chat_id>` proves delivery, and `getWebhookInfo` draining to `pending=0` proves the poller took over — but bot→agent→reply needs the owner to message the bot. Say exactly that instead of claiming the loop is verified.

### Phase 2 — "expertly QA the bot": metadata, avatar, and the delivery surface

A green gateway is not a finished bot. Second pass (verified 2026-09-21, @KsaAzConsults_Bot):

- **Metadata set + read back, never assume:** `setMyName` / `setMyShortDescription` / `setMyDescription` / `setMyCommands` (JSON array), each proven by `getMyName` / `getMyShortDescription` / `getMyDescription` / `getMyCommands`. Space rapid calls (~1s) — the profile set can 429 while polling is fine.
- **Bot avatar:** `setMyProfilePhoto` takes a JSON *object*, not a file field — the naive multipart upload fails with `"Bad Request: photo isn't specified"`. Exact working shape, avatar-matching recipe, and read-back proof: `references/botfather-metadata-and-avatar.md`; reusable token-from-file client: `scripts/tg_bot_api.py`.
- **The client's site form is part of the bot's delivery surface.** Pages/Netlify Functions read `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` from project env **at deploy time** — a site deployed before the bot existed still delivers leads into the OLD bot's chat (real brand leak: KSA site enquiries landed in the India bot's DM). Compare the project's latest deployment date against the bot's go-live, then re-point secrets + redeploy. **Production redeploy = ask the user first** (offer a preview deploy as the alternative).
- **Language register belongs in SOUL.md, scoped by audience — not left to USER.md.** A cloned profile inherits the sibling's `memories/USER.md`, whose "reply in Hinglish" rule silently outranks SOUL.md's English-for-clients instruction; the client-facing bot answered a client intro in Hinglish. State the split explicitly in SOUL.md: owner chat = owner's language, anything a client could read = professional English, no emoji, no AI mention.
- **Strip the cloned `webhook` platform** when the bot only needs Telegram: two profile gateways on the default 8644 log `EADDRINUSE` every minute (drowns real errors). Remove it from the clone's `config.yaml`; it applies on the next restart.
- **Prove token exclusivity before claiming "no 409 risk":** sha256 each candidate token and compare it against every profile `.env` — one bot token, one profile, one 24/7 poller.
- **Grep the new profile for the sibling brand** (`India|GeM|CPPP` etc.) across `SOUL.md`, `memories/`, `config.yaml` before declaring it clean; a clone is riddled with the source brand until you sweep it.


See `references/sanad-bot.md` — full setup, Tier 1 features (QA KB, Arabic auto-detect, voice notes), test suite, incident history, and the Netlify deploy lesson.

## Other platform integrations

WhatsApp Cloud API, X/Twitter, Instagram, and Mostaql lead-monitoring setups live in the `client-platform-integrations` skill (one reference per platform). Same one-brain rule applies: integrations run ONLY on the 24/7 Oracle server — the laptop desktop app is a UI client, never a second polling host.
