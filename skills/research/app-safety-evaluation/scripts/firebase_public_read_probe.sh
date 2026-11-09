#!/usr/bin/env bash
# Read-only Firebase backend probe for app-safety-evaluation.
# GET / list ONLY — no writes, no auth, no API key. A public rule answers 200; a correct
# rule answers 403 PERMISSION_DENIED. That difference IS the finding.
#
# Usage:  ./firebase_public_read_probe.sh <firebase-project-id> [bucket]
#   e.g.  ./firebase_public_read_probe.sh invertio-1702627006371
#
# Output is deliberately ONE LINE PER CHECK so it survives harnesses that collapse
# multi-line piped output. Full JSON bodies are kept in a temp dir for inspection.

set -u
P="${1:?usage: $0 <firebase-project-id> [bucket]}"
B="${2:-$P.firebasestorage.app}"
OUT="${TMPDIR:-/tmp}/fbprobe_$P"
mkdir -p "$OUT"

echo "== project=$P bucket=$B dir=$OUT"

# 1) Firestore: anonymous enumeration per collection
for c in users trees posts activity leaderboards notifications events reports; do
  code=$(curl -s -m 20 -o "$OUT/f_$c.json" -w '%{http_code}' \
    "https://firestore.googleapis.com/v1/projects/$P/databases/(default)/documents/$c?pageSize=300")
  docs=$(grep -o '"name":' "$OUT/f_$c.json" 2>/dev/null | wc -l | tr -d ' ')
  echo "firestore $c=$code docs=$docs"
done

# 2) Storage: anonymous object listing
code=$(curl -s -m 25 -o "$OUT/objs.json" -w '%{http_code}' \
  "https://firebasestorage.googleapis.com/v0/b/$B/o?maxResults=1000&fields=items(name,size,contentType)")
objs=$(grep -o '"name"' "$OUT/objs.json" 2>/dev/null | wc -l | tr -d ' ')
echo "storage list=$code objects~=$objs"

# 3) Storage: prefixes worth being curious about (feature surface + stray docs/policies)
for p in photos/ profileImages/ care/ docs/ placeholder/ users/ trees/; do
  code=$(curl -s -m 20 -o "$OUT/prefix.json" -w '%{http_code}' \
    "https://firebasestorage.googleapis.com/v0/b/$B/o?prefix=$p&maxResults=1000&fields=items(name,size)")
  n=$(grep -o '"name"' "$OUT/prefix.json" 2>/dev/null | wc -l | tr -d ' ')
  echo "storage prefix=$p code=$code objects~=$n"
done

# 4) Storage: prove unauthenticated download of the first listed object (bytes + status)
first=$(grep -o '"name": *"[^"]*"' "$OUT/objs.json" 2>/dev/null | head -n 1 | sed 's/.*: *"//; s/"$//')
if [ -n "${first:-}" ]; then
  enc=$(printf '%s' "$first" | sed 's|/|%2F|g')
  curl -s -m 30 -o /dev/null -w "storage unauth_download=$first code=%{http_code} bytes=%{size_download}\n" \
    "https://firebasestorage.googleapis.com/v0/b/$B/o/$enc?alt=media"
else
  echo "storage unauth_download=skipped (no object listed)"
fi

# 5) Landing-page context (not part of the security verdict)
pkg="${P##*-}"
curl -sL -m 30 -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' -o "$OUT/play.html" \
  "https://play.google.com/store/apps/details?id=$pkg" || true
echo "play_listing=$OUT/play.html bytes=$(wc -c < "$OUT/play.html" 2>/dev/null | tr -d ' ')"

echo "== read-only probe complete; nothing was written to the target."
echo "== next: inspect $OUT/f_*.json for field shapes (uid, lat/lng, image URLs)."
