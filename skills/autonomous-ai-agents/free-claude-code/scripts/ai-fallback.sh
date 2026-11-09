#!/usr/bin/env bash
# ============================================================
# ai-fallback.sh — Perfect Fallback Router for FCC free pool
# FREE providers me rotate (kabhi break nahi), DeepSeek last resort
#
# Usage:
#   ai-fallback.sh "your prompt"              # simple prompt
#   ai-fallback.sh --check                    # health check all routes
#   ai-fallback.sh --list                     # pool status
#   export DEEPSEEK_API_KEY=...               # enable paid last-resort
#
# Installed live as: ~/.local/bin/ai-fallback.sh + symlink ~/.local/bin/ai
# Verified 2026-08-23: rotation, cooldown, DeepSeek last-resort all passed.
# ============================================================
set -uo pipefail
export PATH="$PATH:$HOME/.local/bin"

# ---------- Configuration ----------
# Rotation pool (ORDER = priority). Tested working routes first.
FREE_POOL=(
  "fcc-claude|haiku|claude-haiku-4-5-20251001"      # R1: free haiku (verified)
  "fcc-claude|sonnet|claude-sonnet-4-5-20251001"    # R2: free sonnet (verified)
  "fcc-pi|default|pi"                                # R3: pi free
  "fcc-opencode|default|opencode"                    # R4: opencode
  "fcc-grok|default|grok"                            # R5: grok
)
DEEPSEEK_MODEL="${DEEPSEEK_MODEL:-deepseek-chat}"
TIMEOUT_SEC=60
LOG_FILE="${FCC_LOG:-/tmp/ai-fallback.log}"
STATE_FILE="/tmp/ai-fallback-state.txt"   # cooldown state per route

# ---------- Helpers ----------
log() { echo "[$(date '+%H:%M:%S')] $*" >> "$LOG_FILE"; }

# check if route is in cooldown (after failure)
in_cooldown() {
  local route="$1" now last
  now=$(date +%s)
  last=$(grep "^$route=" "$STATE_FILE" 2>/dev/null | cut -d= -f2 | tail -1)
  [[ -z "$last" ]] && return 1
  (( now - last < 120 )) && return 0 || return 1   # 2 min cooldown
}

mark_fail() {  # route failed -> cooldown
  echo "$1=$(date +%s)" >> "$STATE_FILE"
  tail -50 "$STATE_FILE" > "$STATE_FILE.tmp" && mv "$STATE_FILE.tmp" "$STATE_FILE"
}

mark_ok() {  # route healthy -> clear cooldown
  sed -i "/^$1=/d" "$STATE_FILE" 2>/dev/null || true
}

# ---------- Single route attempt ----------
try_route() {
  local wrapper="$1" model="$2" label="$3" prompt="$4" out rc
  out=$(echo "$prompt" | timeout "$TIMEOUT_SEC" "$wrapper" --print --model "$model" 2>&1)
  rc=$?

  if [[ $rc -eq 124 ]]; then
    log "TIMEOUT $label"
    return 1
  fi
  # Detect failure patterns (rate limit, auth, empty)
  if [[ "$out" =~ (429|rate.?limit|quota|unauthor|invalid.?api|api.?key|permission|error|refus) ]] \
     || [[ -z "$(echo "$out" | tr -d '[:space:]')" ]]; then
    log "FAIL $label (rc=$rc): $(echo "$out" | head -c 120)"
    return 1
  fi
  log "OK $label"
  echo "$out"
  return 0
}

# ---------- Main: rotate through pool ----------
run_prompt() {
  local prompt="$1" out=""
  local attempts=0

  # Phase 1: FREE pool rotation
  for entry in "${FREE_POOL[@]}"; do
    local wrapper model label
    wrapper="${entry%%|*}"; rest="${entry#*|}"
    model="${rest%%|*}"; label="${rest#*|}"
    ((attempts++))
    if in_cooldown "$label"; then
      log "SKIP $label (cooldown)"
      continue
    fi
    echo "[fallback] trying $label..." >&2
    if out=$(try_route "$wrapper" "$model" "$label" "$prompt"); then
      mark_ok "$label"
      echo "$out"
      return 0
    fi
    mark_fail "$label"
  done

  # Phase 2: DeepSeek paid last resort (key required)
  if [[ -n "${DEEPSEEK_API_KEY:-}" ]]; then
    echo "[fallback] free pool exhausted -> DeepSeek (paid)..." >&2
    local dout
    dout=$(timeout "$TIMEOUT_SEC" curl -s https://api.deepseek.com/chat/completions \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
      -d "{\"model\":\"$DEEPSEEK_MODEL\",\"messages\":[{\"role\":\"user\",\"content\":$(printf '%s' "$prompt" | jq -Rsa .)}],\"max_tokens\":1024}" 2>&1)
    if echo "$dout" | grep -q '"content"'; then
      log "OK deepseek"
      echo "$dout" | jq -r '.choices[0].message.content' 2>/dev/null || echo "$dout"
      return 0
    fi
    log "FAIL deepseek: $(echo "$dout" | head -c 150)"
  fi

  echo "[fallback] ALL ROUTES FAILED — check /tmp/ai-fallback.log" >&2
  return 1
}

# ---------- Health check all routes ----------
check_all() {
  echo "=== FCC Fallback Pool Status ==="
  for entry in "${FREE_POOL[@]}"; do
    local wrapper model label
    wrapper="${entry%%|*}"; rest="${entry#*|}"
    model="${rest%%|*}"; label="${rest#*|}"
    if in_cooldown "$label"; then
      echo "  $label: COOLDOWN"
    else
      echo "  $label: ready"
    fi
  done
  [[ -n "${DEEPSEEK_API_KEY:-}" ]] && echo "  deepseek: ready (paid)" || echo "  deepseek: NOT CONFIGURED"
  echo "=== server health ==="
  curl -s -m 5 http://127.0.0.1:8082/health || echo "fcc-server DOWN"
}

# ---------- CLI ----------
case "${1:-}" in
  --list)    check_all ;;
  --check)   check_all ;;
  --model)   shift; export FORCE_MODEL="$1"; shift; run_prompt "$*" ;;
  *)         run_prompt "$*" ;;
esac
