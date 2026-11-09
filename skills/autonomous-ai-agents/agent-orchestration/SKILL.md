---
name: agent-orchestration
description: Dispatch to Hermes sub-agent profiles; fleet monitoring.
---

# Agent Orchestration — Architect Playbook (Aug-2026)

Aamir's solo-entrepreneur AI team: Hermes (default profile) = COO/architect; per-client profiles = sub-agents; cron = workers. Main agent DISPATCHES, never does client work inline.

## Fleet
| Profile | Domain | cwd | Source-of-truth |
|---|---|---|---|
| luxewave | Shopify store, media, marketing | ~/clients/luxewave | ~/clients/luxewave/MEMORY.md |
| sanad | Sanad biz: bots, hosting, WP audit | ~/sanad-site | ~/sanad-site/MEMORY.md |
| avvs | AVVS Triatek site, lead-gen | ~/clients/AVVS-Triatek | ~/clients/AVVS-Triatek/MEMORY.md |
| ops | Infra, backup, marketing, products | ~/ops | ~/ops/MEMORY.md |
| whatsapp | WhatsApp bridge (gateway running) | — | — |

Har profile: apna SOUL.md (role), memories/ (MEMORY.md + USER.md), scripts/, cron/, config.yaml (terminal.cwd = client dir). Same DeepSeek model, cloned from default.

## Dispatch (request aane pe)
```bash
# one-shot (recommended — fire & report)
hermes -p luxewave chat -q "task brief — self-contained, background context de do"
# interactive (long sessions)
tmux new -s luxewave "hermes -p luxewave chat"
```
- Task brief SELF-CONTAINED likho: subagent ko conversation history nahi milti. Client facts wahi hai jo MEMORY.md me.
- 'Karo/khud karlo' = full autonomous; sirf OTP/Google-login steps user ko bhejo.
- Background dispatch: `hermes -p <name> chat -q "..." > /tmp/dispatch-<name>.log 2>&1 &` + notify on complete.

## Monitoring (architect role)
- `hermes -p <name> cron list` — profile ke cron status
- /tmp/luxewave-watch.log — watchdog heartbeat (<15 min fresh = OK)
- :8645 handler 501 = up; tunnel URL vs /tmp/luxewave-webhook-url
- fleet-health-monitor cron (default, 30 min, silent-watchdog) — alerts sirf anomaly pe
- Disk: `df -h /`; gateway: `pgrep -f "hermes.*gateway"`

## Rules
- Client kaam kabhi inline mat karo — dispatch karo (memory/context isolation hi is architecture ka point hai).
- Client facts update hote hi source-of-truth file + profile memory DONO update karo (main memory me nahi — woh sirf global index).
- Naya client: `hermes profile create <name> --clone` + SOUL + MEMORY.md seed + terminal.cwd. Backup pehle: `cp -r ~/.hermes/memories ~/.hermes/config.yaml ~/.hermes/cron ~/backups/`.
- Slack bots per profile (Layer 3): pending — user ke Slack app banwane pe.

## Pitfalls
- `pkill -f "script_name"` apni hi command line ko match karke kill kar deta hai — exact PID ya `[.]` regex use karo.
- Watchdog hangs: background children inherit flock fd → flock kabhi release nahi hota. Pid-file lock + `timeout 100` subshell use karo (luxewave_watch_webhook.sh pattern).
- Cron script relative paths profile me resolve: ~/.hermes/profiles/<name>/scripts/.
