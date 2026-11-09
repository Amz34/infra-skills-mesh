#!/usr/bin/env bash
# Probe per-model Gemini free-tier quota BEFORE a long agent run.
#
#   probe_gemini_quota.sh [model ...]
#
# Free tier is capped per MODEL per project (quotaValue is often 20/day), so one
# spent model is not a dead key: this prints the HTTP code per model plus the
# error status, e.g.
#   gemini-3.8-flash    429 Too Many Requests
#   gemini-3.7-flash    200
# Exit 0 always; read the table. The key is NEVER printed.
set -uo pipefail

PROJECT_ENV="${PROJECT_ENV:-$HOME/projects/artemis/.env}"
KEY="${GOOGLE_API_KEY:-}"
if [ -z "$KEY" ] && [ -f "$PROJECT_ENV" ]; then
  KEY=$(grep -m1 '^GOOGLE_API_KEY=' "$PROJECT_ENV" | cut -d= -f2- | tr -d '"'"'"' ')
fi
[ -n "$KEY" ] || { echo "probe_gemini_quota: no GOOGLE_API_KEY in env or $PROJECT_ENV"; exit 2; }

MODELS=("$@")
[ "${#MODELS[@]}" -eq 0 ] && MODELS=(
  gemini-3.8-flash gemini-3.7-flash gemini-3.5-flash
  gemini-3.1-flash-lite gemini-2.5-flash-lite gemini-robotics-er-2-preview
)

BODY='{"contents":[{"parts":[{"text":"ok"}]}],"generationConfig":{"maxOutputTokens":1}}'
TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT

printf '%-32s %-4s %s\n' MODEL CODE STATUS
for m in "${MODELS[@]}"; do
  code=$(curl -s -m 30 -o "$TMP" -w '%{http_code}' -X POST \
    -H 'Content-Type: application/json' -d "$BODY" \
    "https://generativelanguage.googleapis.com/v1beta/models/${m}:generateContent?key=${KEY}")
  status=$(python3 - "$TMP" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    print("-"); raise SystemExit
e = d.get("error", {})
det = str(e.get("details", ""))
quota = ""
if "PerModel" in det:
    quota = " [per-model daily quota]"
print((e.get("status") or "OK") + quota)
PY
)
  printf '%-32s %-4s %s\n' "$m" "$code" "$status"
done
