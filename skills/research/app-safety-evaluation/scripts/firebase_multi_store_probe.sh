#!/usr/bin/env bash
# Read-only Firebase exposure probe: Firestore + Realtime Database + Storage.
# GET / HEAD / LIST only. No account, no API key, no writes, no full file downloads.
# Prints one line per check plus field NAMES (never values, uids, emails or tokens).
# Usage: firebase_multi_store_probe.sh <firebase-project-id> [bucket]
#        OUTDIR=/tmp/fb_probe firebase_multi_store_probe.sh my-project
set -u

PID="${1:?usage: $0 <firebase-project-id> [bucket]}"
B="${2:-$PID.firebasestorage.app}"
OUT="${OUTDIR:-/tmp/fb_probe}"
mkdir -p "$OUT"
say() { printf '%s\n' "$*"; }

say "project=$PID bucket=$B out=$OUT"

# ---------- 1. Firestore (anonymous per-collection read) ----------
say "== Firestore =="
for c in users trees posts activity leaderboards notifications orders; do
  code=$(curl -s -m 20 -o "$OUT/fs_$c.json" -w '%{http_code}' \
    "https://firestore.googleapis.com/v1/projects/$PID/databases/(default)/documents/$c?pageSize=300")
  n=$(grep -o '"name":' "$OUT/fs_$c.json" 2>/dev/null | wc -l | tr -d ' ')
  say "firestore $c http=$code docs=$n"
done
code=$(curl -s -m 20 -o "$OUT/fs_listids.json" -w '%{http_code}' -X POST \
  -H 'Content-Type: application/json' -d '{"pageSize":100}' \
  "https://firestore.googleapis.com/v1/projects/$PID/databases/(default)/documents:listCollectionIds")
say "firestore listCollectionIds http=$code (403 means names cannot be enumerated anonymously: sweep guesses, do not claim a collection count)"

# ---------- 2. Realtime Database (the store audits usually forget) ----------
say "== Realtime Database =="
code=$(curl -s -m 20 -o "$OUT/rtdb_root.json" -w '%{http_code}' \
  "https://$PID-default-rtdb.firebaseio.com/.json?shallow=true")
keys=$(python3 - "$OUT/rtdb_root.json" <<'PY' 2>/dev/null
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    print('unparsed'); raise SystemExit
print(','.join(list(d)[:25]) if isinstance(d, dict) else type(d).__name__)
PY
)
say "rtdb root http=$code nodes=${keys:-none}"

for n in users activities trees global appConfig ads config settings; do
  code=$(curl -s -m 20 -o "$OUT/rtdb_$n.json" -w '%{http_code}' \
    "https://$PID-default-rtdb.firebaseio.com/$n.json")
  cnt=$(python3 - "$OUT/rtdb_$n.json" <<'PY' 2>/dev/null
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    print('-'); raise SystemExit
print(len(d) if isinstance(d, (dict, list)) else type(d).__name__)
PY
)
  say "rtdb /$n http=$code records=$cnt"
done

# Field names only for user-owned nodes: enough to prove what is exposed.
say "rtdb field names (names and counts only, no values):"
for f in "$OUT"/rtdb_users.json "$OUT"/rtdb_activities.json "$OUT"/rtdb_appConfig.json "$OUT"/rtdb_global.json; do
  [ -s "$f" ] || continue
  python3 - "$f" <<'PY' 2>/dev/null
import collections, json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    raise SystemExit
if not isinstance(d, dict) or not d:
    raise SystemExit
if isinstance(next(iter(d.values())), dict):
    c = collections.Counter(k for v in d.values() if isinstance(v, dict) for k in v)
    print('  %-12s %s' % (sys.argv[1].rsplit('/', 1)[-1], dict(c.most_common(15))))
else:
    print('  %-12s %s' % (sys.argv[1].rsplit('/', 1)[-1], ','.join(list(d)[:15])))
PY
done

# ---------- 3. Storage (anonymous list + header leak) ----------
say "== Storage =="
code=$(curl -s -m 25 -o "$OUT/objs.json" -w '%{http_code}' \
  "https://firebasestorage.googleapis.com/v0/b/$B/o?maxResults=1000&fields=items(name,size,contentType)")
say "list http=$code"
python3 - "$OUT/objs.json" <<'PY' 2>/dev/null
import collections, json, statistics, sys
try:
    it = (json.load(open(sys.argv[1])) or {}).get('items') or []
except Exception:
    print('  unparsed'); raise SystemExit
pre = collections.Counter(n.split('/', 1)[0] if '/' in n else '(root)' for n in (i.get('name', '') for i in it))
sz = sorted(i.get('size') or 0 for i in it)
print('  objects=%d prefixes=%s' % (len(it), dict(pre.most_common(10))))
if sz:
    print('  size median=%dB max=%dB total=%.1fMB' % (len(sz) and statistics.median(sz) or 0, sz[-1], sum(sz) / 1048576))
PY

FIRST=$(python3 - "$OUT/objs.json" <<'PY' 2>/dev/null
import json, sys
try:
    it = (json.load(open(sys.argv[1])) or {}).get('items') or []
except Exception:
    raise SystemExit
print(it[0]['name'] if it else '')
PY
)
if [ -n "${FIRST:-}" ]; then
  ENC=$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1], safe=""))' "$FIRST")
  curl -sI -m 20 "https://firebasestorage.googleapis.com/v0/b/$B/o/$ENC?alt=media" -o "$OUT/hdr.txt"
  hit=$(grep -ci 'x-goog-meta-firebasestoragedownloadtokens' "$OUT/hdr.txt" 2>/dev/null)
  say "media HEAD first object: token-header-present=$hit (presence only; the token value is never printed)"
fi
say "done: raw JSON in $OUT (fs_*.json, rtdb_*.json, objs.json, hdr.txt)"
