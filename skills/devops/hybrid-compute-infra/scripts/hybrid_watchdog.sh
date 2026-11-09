#!/usr/bin/env bash
# Hybrid infra watchdog — crash-proof layer.
# Silent when healthy (no_agent cron pattern); prints only when action taken.
# Checks: Ollama API, Hermes gateway, PII gate smoke test.
set -u
LOG=~/logs/hybrid-watchdog.log
mkdir -p ~/logs
ts() { date '+%Y-%m-%d %H:%M:%S'; }
alert() { # alert <message>
  local msg="$1"
  echo "$(ts) ALERT: $msg" >> "$LOG"
  local token chat
  token=$(grep -oP '^TELEGRAM_BOT_TOKEN=\K.*' ~/.hermes/.env 2>/dev/null | head -1)
  chat="${HYBRID_ALERT_CHAT:-8843884232}"
  if [ -n "$token" ]; then
    curl -s --max-time 10 "https://api.telegram.org/bot${token}/sendMessage" \
      -d chat_id="$chat" -d text="⚠️ Hybrid watchdog: ${msg}" >/dev/null 2>&1 || true
  fi
  echo "$msg"
}
ACTION=""
# 1. Ollama API
if ! curl -s --max-time 5 http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "$(ts) Ollama down -> restarting" >> "$LOG"
  sudo systemctl restart ollama
  sleep 8
  if curl -s --max-time 5 http://localhost:11434/api/tags >/dev/null 2>&1; then
    ACTION+="ollama restarted; "
  else
    ACTION+="OLLAMA DOWN (restart failed); "
  fi
fi
# 2. Hermes gateway (user service) — systemd auto-restarts it; watchdog only alerts
if ! systemctl --user is-active --quiet hermes-gateway 2>/dev/null; then
  ACTION+="GATEWAY DOWN (systemd restart loop active?); "
fi
# 3. PII gate smoke test (expect pii:true on sample)
SAMPLE="Client phone +966 50 123 4567 email client@example.com"
if ! OUT=$(echo "$SAMPLE" | python3 ~/.hermes/scripts/pii_gate.py --stdin --no-llm 2>/dev/null); then
  ACTION+="pii_gate script error; "
elif ! echo "$OUT" | grep -q '"pii": true'; then
  ACTION+="pii_gate wrong verdict; "
fi
if [ -n "$ACTION" ]; then
  alert "infra actions: ${ACTION}"
else
  echo "$(ts) healthy" >> "$LOG"
  exit 0
fi
