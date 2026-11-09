#!/bin/bash
# TEMPLATE — copy and edit the four CONFIG lines. Applies a candidate prod file
# with backup + verify + automatic rollback. Repo has no git, so the backup IS
# the version history (backups/<file>.<label>-<ts>).
#
# Usage: bash apply-with-rollback.sh <patched-file> <label>
#   e.g. bash apply-with-rollback.sh /tmp/server_accesslog.py accesslog
set -u

TARGET_FILE="server.py"                              # CONFIG: prod file to replace
SERVICE="infra-dash.service"                         # CONFIG: systemd unit (system or --user)
PROBE_URL="http://127.0.0.1:8765/data.json"          # CONFIG: cheap liveness probe
GATE_CMD="DASH_URL=http://127.0.0.1:8765 /usr/bin/python3 verify/drive.py"   # CONFIG: real gate (may be "")
SYSCTL="sudo -n systemctl"                           # CONFIG: on this VM infra-dash.service is a SYSTEM unit (/etc/systemd/system) — "systemctl --user" DOES NOT see it and aborts with "Unit not found", which this script then treats as a failed deploy and rolls back. Verified 2026-09-13; sudo is passwordless.
PYBIN="/usr/bin/python3"                             # CONFIG: the interpreter the unit actually runs

PROD="/home/ubuntu/clients/invertio/infra-dashboard"
NEW="${1:?need patched file path}"
LABEL="${2:-change}"
TS=$(date +%Y%m%d-%H%M%S)
BAK="$PROD/backups/$TARGET_FILE.$LABEL-$TS"

rollback() {
  echo "!! FAILURE -> ROLLING BACK"
  cp "$BAK" "$PROD/$TARGET_FILE" || { echo "!! backup restore failed: $BAK"; exit 2; }
  $SYSCTL restart "$SERVICE"
  sleep 2
  echo "rolled back; active=$($SYSCTL is-active $SERVICE) probe=$(curl -s -o /dev/null -w '%{http_code}' "$PROBE_URL")"
  exit 1
}

cd "$PROD" || exit 2

echo "=== 1. backup ==="
cp "$PROD/$TARGET_FILE" "$BAK" || exit 2
ls -l "$BAK"

echo "=== 2. install + compile (prod interpreter) ==="
cp "$NEW" "$PROD/$TARGET_FILE" || rollback
$PYBIN -m py_compile "$PROD/$TARGET_FILE" || rollback
echo "compile OK"

echo "=== 3. restart ==="
$SYSCTL restart "$SERVICE" || rollback
sleep 3
echo "active=$($SYSCTL is-active $SERVICE)"

echo "=== 4. liveness + endpoint parity ==="
for u in / /data.json "/history.json?hours=24" /fleet.json; do
  echo "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:8765$u")  $u"
done
echo "public host: $(curl -s -o /dev/null -w '%{http_code}' -H 'Host: aslove7.ddns.net' http://127.0.0.1:8765/)"

echo "=== 5. gate (post-change) ==="
if [ -n "$GATE_CMD" ]; then
  eval "$GATE_CMD" || rollback
fi
echo "=== DONE — change live, backup at $BAK ==="
