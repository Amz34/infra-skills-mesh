# External "poster" alerts from shared-token scripts (not Hermes)

Diagnosed Sep 2026. Aamir's DM (8843884232) received: "Telegram poster: send failed.
Telegram HTTP 400: {"ok":false,...,"description":"Bad Request: chat not found"}".
Nothing in Hermes code (`grep -rn poster ~/.hermes/hermes-agent`) or Hermes cron
jobs.json produced that string — the sender was an EXTERNAL autonomous script that
shares the main Zma1_bot token and DMs alerts to Aamir's chat id.

## The sender (Invertio client daily Telegram-group briefing)

- Script: `~/clients/invertio/multi-agent/tg-group/poster.py` — generates an AI
  briefing and posts it to a Telegram GROUP using the MAIN bot token from
  `~/.hermes/.env` (TELEGRAM_BOT_TOKEN). One-poll-per-token rule does NOT apply to
  posting via Bot API sendMessage — only getUpdates polling conflicts.
- Scheduler is **SYSTEM-level systemd**, not Hermes cron and not a user timer:
  `/etc/systemd/system/invertio-tg-poster.service` + `.timer` — daily
  `05:30:00 UTC` (= 08:30 Riyadh), `Persistent=true`, randomized delay 300s.
  ExecStart runs the crashproof venv:
  `~/clients/invertio/multi-agent/crashproof/.venv/bin/python .../tg-group/poster.py`.
- `config.json` (same dir) is the key state:
  - `group.chat_id` = target group (`-1004483240754` = "Enterprise AI | Data Intelligence")
  - `alerts.dm_chat_id` = `8843884232` (Aamir's main DM) → failure alerts land in the
    SAME chat Hermes uses, which is why they look like Hermes messages.
  - `pipeline.url` = `http://127.0.0.1:8088/run` (invertio-agent-pipeline.service upstream).
- `state.json` holds `last_error`, `last_post_date`, `posted_count`.
- `logs/poster-YYYYMM.jsonl` holds the full event history (`posted` / `post_failed`
  events with timestamps + error text + message_ids). Read the failure event here
  to see exactly when and why it died.

## Why "chat not found"

Telegram HTTP 400 `chat not found` = the bot cannot reach that chat: bot was removed
from the group, group was deleted, or the group was deleted+recreated (supergroups
get a NEW chat_id on recreation). Verify WITHOUT sending anything — read-only:

```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getChat?chat_id=-1004483240754"
# {"ok":false,"error_code":400,"description":"Bad Request: chat not found"} → group is dead
```

The timer keeps firing every day and re-alerts each time until fixed.

## Trace recipe for ANY mystery DM alert on this VM

1. Grep the exact label string in Hermes logs + cron jobs.json first:
   `grep -rn "poster\|send failed" ~/.hermes/logs/ ~/.hermes/profiles/*/logs/`
   and check both `~/.hermes/cron/jobs.json` AND `~/.hermes/profiles/*/cron/jobs.json`.
   Empty → NOT Hermes, look outside.
2. `grep -rln "<unique-word>" ~/clients/ --include="*.py"` → find the sender script.
3. Read its `config.json` (who it alerts + to which chat_id) and `state.json`
   (`last_error` often equals the exact DM text) + dated `.jsonl` event logs.
4. Find the scheduler BOTH places: user level (`systemctl --user list-timers`,
   `~/.config/systemd/user/`) AND system level (`systemctl list-timers`,
   `ls /etc/systemd/system/ | grep -i <name>`) — **user-level checks miss
   system-level timers**, which is exactly what happened here.
5. Verify the failing chat is dead with `getChat` (read-only) before proposing fixes.
   Note: system-level service files need `sudo cat` / sudo journalctl, but the
   working files (`config.json`, `state.json`, `logs/*.jsonl`) are user-readable.

## Fix options

- Group still wanted → re-add the bot to the group, then re-register the new chat:
  `python3 poster.py --register` (needs the bot to have seen one message in the new
  group first; error text when unregistered: "No group found. Add @Zma1_bot to your
  group, send one message there, then rerun."). Updates config.json `group.chat_id`.
- Group dead / no longer needed → stop the daily failure loop:
  `sudo systemctl disable --now invertio-tg-poster.timer`.
