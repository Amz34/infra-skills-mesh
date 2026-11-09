# SanadGulf_bot — concrete setup & incident history

## Current host (since Aug 11 2026)
- **Oracle Always-Free VM "hermes-vnic" 158.101.229.133** (ARM Ampere A1, 2 OCPU / 12 GB, Ubuntu 24.04, ~46 GB free) — Hermes gateway + Sanad bot BOTH run here.
- Old hosts: AWS t3.micro `i-0619a0ba2cb462d30` (STOPPED, backup only) and Oracle `158.101.250.58` (disabled duplicate — terminate). Agent keypair on the active VM: `~/.ssh/oracle_hermes2` (comment `hermes-oracle-v2`), authorized on both Oracle hosts.
- **The agent's private key can vanish from `~/.ssh` across gateway restarts — after generating a keypair for a cloud VM, immediately append its PUBLIC key to the local `authorized_keys` too** (so the agent can re-enter the host from another box), and keep the instance's console-created keys as a second entry.

## Paths / env
- Bot dir: `/home/ubuntu/sanad-bot/` — `bot.py` (long-poll, urllib, IPv4-only override), `.env` (`SANAD_BOT_TOKEN`, `AAMIR_CHAT_ID=8843884232`), `logo.png` (640x640, brand colors), `bot.log`, `watchdog.log`, `watchdog.sh`.
- Bot runs with **system python3** (`/usr/bin/python3`, has `edge_tts` via `sudo python3 -m pip install --break-system-packages edge-tts`) — the hermes venv python does NOT have edge_tts. Voice notes also need `ffmpeg` (installed by the hermes installer).
- Bot: @Sanadgulfbot, bot id 8986728434, name "Sanad". Client-facing copy: pure English, no emojis, brand = one word "Sanad".
- Owner mirror chat: 8843884232 (Aamir). Owner's OWN messages are NOT mirrored (is_owner skip) — test the mirror with a second account.
- Watchdog: cron `*/5 * * * *` runs `watchdog.sh` → `pgrep -f "python3 bot.py"` (must match real cmdline) else `nohup python3 bot.py >> bot.log 2>&1 &`.
- Restart convention: `terminal(background=true, command="cd /home/ubuntu/sanad-bot && python3 bot.py >> bot.log 2>&1")` — durable log, tail-able from any session.

## Behavior (Tier 1, Aug 10 2026)
- **Menu:** Book a Free Call / See Pricing / Website Builds / Talk on WhatsApp / **Hear Pricing as Voice** (callback `voice`). Talk-to-Human was REMOVED per client (Aug 10) — a stale "human" button falls through to DEFAULT.
- **Language auto-detect:** any Arabic-script char (\u0600-\u06FF) → whole reply in Arabic (formal MSA, no emojis) + Arabic inline menu. `langs[chat_id]` persists so callback presses reply in the user's language. Arabic keyword sets named `*_KW_AR`. ⚠️ Never name an Arabic reply string the same as its keyword set — the tuple overwrites the string (hit this; 55/55 suite guards it).
- **General Q&A KB (A1):** `KB` list of (en_cues, ar_cues, en_answer, ar_answer), checked after intents, before DEFAULT. HOW_KW must NOT contain a "setup" cue and TERMS_KW cues are only "terms of service"/"terms and conditions" — otherwise they steal "support after setup" / "payment terms" from the KB.
- **Voice notes (A3):** `voice` intent/button → `make_voice_note(lang)` (edge-tts `en-US-GuyNeural` / `ar-SA-HamedNeural` → mp3 → ffmpeg → ogg opus 32k) → `send_voice()` multipart upload (urllib, 3× retry). `voice_pending[chat_id]` set by route(), `maybe_send_voice()` called after send in both callback and message paths; TTS fail falls back to text pricing. Numbers are spelled out in words for natural TTS.
- **Intent routing order:** greet → booking states (name→phone) → pricing → website → whatsapp → how → book → about → contact → reassurance → privacy → terms → KB → DEFAULT. Each intent = exact keywords + substring cues via `hit(low, exact, cues)`.

## Unit tests
- 55-case Tier 1 suite at `/tmp/test_bot_tier1.py` (regenerate from it): monkeypatch `bot.send`/`bot.answer_cb`/`bot.send_voice`; `reset()` clears states/names/langs/last_text/voice_pending/SENT per case; multi-turn booking calls `bot.route()` directly WITHOUT reset between turns; covers EN+AR intents, KB, lang persistence (Arabic user → callback replies Arabic), real voice file generation + cleanup, `client_kb()` t.me AND tg://user?id links.

## Incident history
- Aug 9–10 2026: DNS failure storms on the old host — getUpdates pends server-side (bot catches up) but failed sendMessage replies are lost forever → send-retry hardening.
- Aug 10: pro rebuild (intent routing → page links, WhatsApp CTA, tap-links, retry ×3, non-text handling) then Tier 1 (KB + Arabic + voice). 55/55 tests.
- Aug 11: **409 conflict** — two Oracle instances both running the bot (duplicate setup from a migration). Fix: kill the duplicate host's bot + remove its watchdog cron + disable its gateway service. Verify by checking the surviving bot.log stops growing (stale 409s look identical to live ones).

## Website integration (Sanad site)
- Live: **sanad-io.netlify.app**, bilingual (7 EN + 7 AR pages under `/ar/`, nav toggles, RTL + Tajawal, `$` pricing kept per client). Local source `/home/ubuntu/sanad-site/` (7 EN + 7 AR .html + assets).
- ⚠️ **Deploy with netlify-cli ONLY:** `npm i -g netlify-cli` then `netlify deploy --dir=/home/ubuntu/sanad-site --site=sanad-io --auth=$(cat /home/ubuntu/.netlify-token) --prod --json`. The raw urllib API script (`deploy-sanad.py`) fails on EVERY file upload with 422 `"no records matched"` even though `required` lists the exact sha256 digests and both path-key and digest-key uploads 422 (verified on 2 different sites). Do NOT re-debug the raw API — the CLI's internal flow works around it.
- Netlify account sites: sanad-io, luxewave-ksa, dancing-daffodil-2dbe29. Token file: `/home/ubuntu/.netlify-token` (was on the old host — re-auth via `netlify login` or a PAT if missing).
- **Version-conflict warning:** the user's laptop (Hermes One desktop) can deploy its own older site version — a laptop deploy that got "held" (Netlify limit) replaced the bilingual site with a button-toggle version lacking `/ar/` (404s). Re-deploy the canonical bilingual version from the VM after any laptop deploy attempt, and tell the user not to deploy from the laptop while the VM version is canonical.
