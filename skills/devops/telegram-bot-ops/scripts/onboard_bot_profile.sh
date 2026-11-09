#!/usr/bin/env bash
# Onboard a NEW Telegram bot token as its own Hermes profile + systemd --user gateway.
#
#   onboard_bot_profile.sh <profile> <bot_token> [owner_tg_id]
#
# Mirrors the step-by-step sequence that was verified manually on this VM (2026-09-20,
# profile `azwork` / @FLworkAz_Bot, OCI aarch64). Every step below is individually verified;
# the script itself has not yet been run end-to-end as a unit — the first time you use it,
# read the output of each step and fall back to the manual runbook in
# references/new-bot-profile-onboarding.md if a step misbehaves.
#
# The token is never echoed: it is passed to python heredocs as $2/$argv and only the
# non-secret identifiers (bot id/username, env KEY NAMES) are printed.
set -euo pipefail

PROFILE="${1:?usage: onboard_bot_profile.sh <profile> <bot_token> [owner_tg_id]}"
TOKEN="${2:?bot token required}"
OWNER="${3:-}"
HOMEDIR="${HERMES_DIR:-$HOME/.hermes}"
PDIR="$HOMEDIR/profiles/$PROFILE"
UNIT="hermes-gateway-$PROFILE"

# --- resolve a python that can import hermes_cli -----------------------------
PY="${HERMES_PY:-}"
if [ -z "$PY" ]; then
  for cand in "$HOMEDIR/hermes-agent/venv/bin/python" "$(command -v python3 || true)"; do
    [ -n "$cand" ] || continue
    if "$cand" -c 'import hermes_cli' 2>/dev/null; then PY="$cand"; break; fi
  done
fi
[ -n "$PY" ] || { echo "FATAL: no python with hermes_cli — set HERMES_PY=/path/to/python" >&2; exit 1; }

echo "== 0. pre-flight (getMe / getWebhookInfo — prints no secrets)"
"$PY" - "$TOKEN" <<'PY'
import json, sys, urllib.request
t = sys.argv[1]
try:
    r = json.load(urllib.request.urlopen(f"https://api.telegram.org/bot{t}/getMe", timeout=30))
except Exception as e:                      # noqa: BLE001
    sys.exit(f"getMe FAILED: {e}")
res = r["result"]
print(f"  ok={r['ok']} id={res['id']} username=@{res.get('username')} name={res.get('first_name')!r}")
w = json.load(urllib.request.urlopen(f"https://api.telegram.org/bot{t}/getWebhookInfo", timeout=30))["result"]
print(f"  webhook={w.get('url')!r} pending={w.get('pending_update_count')}")
if w.get("url"):
    print("  WARN: a webhook is set — deleteWebhook it before long-polling, else 409.")
PY

echo "== 1. profile create (clones the ACTIVE profile — review SOUL.md afterwards!)"
"$PY" -m hermes_cli.main profile create "$PROFILE" --clone \
  --description "Telegram bot profile $PROFILE" </dev/null

echo "== 2. token swap + strip fleet-exclusive platform tokens (Slack etc.)"
"$PY" - "$PDIR/.env" "$TOKEN" "$OWNER" <<'PY'
import os, re, sys
path, token, owner = sys.argv[1], sys.argv[2], sys.argv[3]
drop = ("SLACK_BOT_TOKEN=", "SLACK_APP_TOKEN=", "SLACK_SIGNING_SECRET=", "SLACK_ALLOWED_USERS=")
out, seen = [], False
for line in open(path).read().splitlines():
    if line.startswith(drop):
        continue
    if line.startswith("TELEGRAM_BOT_TOKEN="):
        out.append(f"TELEGRAM_BOT_TOKEN={token}"); seen = True; continue
    if line.startswith(("TELEGRAM_ALLOWED_USERS=", "TELEGRAM_HOME_CHANNEL=")):
        continue
    out.append(line)
if not seen:
    out.append(f"TELEGRAM_BOT_TOKEN={token}")
if owner:
    out += [f"TELEGRAM_ALLOWED_USERS={owner}", f"TELEGRAM_HOME_CHANNEL={owner}"]
open(path, "w").write("\n".join(out) + "\n")
os.chmod(path, 0o600)
print("  env keys: " + ",".join(re.findall(r"^([A-Z0-9_]+)=", "\n".join(out), re.M)))
PY

echo "== 3. gateway install --start-now --start-on-login"
HERMES_HOME="$PDIR" "$PY" -m hermes_cli.main gateway install --start-now --start-on-login </dev/null

echo "== 4. guardrail drop-in (a fresh unit does NOT inherit the fleet's)"
SRC="$HOME/.config/systemd/user/hermes-gateway.service.d/99-guardrails.conf"
DST="$HOME/.config/systemd/user/$UNIT.service.d"
if [ -f "$SRC" ]; then
  mkdir -p "$DST"; cp "$SRC" "$DST/99-guardrails.conf"
  grep -q '^TimeoutStopSec=180' "$DST/99-guardrails.conf" || \
    printf '\n# state.db WAL safety (matches every other gateway unit)\nTimeoutStopSec=180\nKillMode=mixed\n' >> "$DST/99-guardrails.conf"
  systemctl --user daemon-reload
  echo "== 5. restart via the Hermes CLI (systemctl restart is guard-blocked from inside a gateway)"
  HERMES_HOME="$PDIR" "$PY" -m hermes_cli.main gateway restart </dev/null
else
  echo "  SKIP: $SRC not found — this box has no fleet guardrail baseline to copy."
fi

echo "== 6. verify"
sleep 20
systemctl --user is-active "$UNIT" || true
systemctl --user show "$UNIT" -p MemoryHigh -p MemoryMax -p MemorySwapMax -p TasksMax -p TimeoutStopUSec | sed 's/^/  /'
tail -4 "$PDIR/logs/gateway.log" | sed 's/^/  /'

cat <<EOF

NEXT (manual, needs the owner):
  • owner sends any message to the bot  -> proves inbound (bot->agent->reply); you cannot test this yourself
  • declare the new surface in ~/ops/observability/autonomy.json (surfaces + critical_services)
    then: python3 ~/ops/scripts/autonomy_audit.py   (expect 0 unclassified)
  • review $PDIR/SOUL.md  (clone may carry a CLIENT profile's brand voice)
EOF
