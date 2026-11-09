#!/usr/bin/env bash
# live_brief_sources.sh — one-shot map of a LIVE capture lane, for the
# "meeting brief do / abhi tak kya discuss hua" ping.
#
# Usage:  live_brief_sources.sh [RUN_DIR]
#         (default: $ZOOM_RUN, else ~/ops/zoom-attend/run)
#
# Prints: lane identity, ENDED flag, transcript chunk timeline, chunk in
# flight, latest transcribed chunk text, chat tail, newest screenshots.
# Read-only. Safe to run mid-meeting.
set -uo pipefail

RUN="${1:-${ZOOM_RUN:-$HOME/ops/zoom-attend/run}}"
if [ ! -d "$RUN" ]; then
  echo "RUN dir not found: $RUN"
  echo "hint: check ~/.config/zoom-attend/current.env for ZOOM_RUN, or pass the dir explicitly"
  exit 1
fi

echo "RUN=$RUN"
echo "NOW_UTC=$(date -u '+%F %T')  NOW_LOCAL=$(date '+%F %T %Z')"

echo "--- identity (authoritative: which lane is live) ---"
for f in label.txt lang.txt source-url.txt; do
  if [ -f "$RUN/$f" ]; then
    printf '%s: ' "$f"
    head -c 300 "$RUN/$f"
    echo
  else
    echo "$f: (missing)"
  fi
done

echo "--- state ---"
if [ -f "$RUN/ENDED" ]; then
  echo "ENDED flag PRESENT: $(cat "$RUN/ENDED")  (can be premature/wrong: cross-check the waveform before believing it)"
else
  echo "ENDED flag absent"
fi

echo "--- transcript chunk timeline (timeline anchors) ---"
if [ -f "$RUN/transcript.txt" ]; then
  grep -n '^=== live_' "$RUN/transcript.txt" | tail -60
  echo "transcript.txt: $(wc -l < "$RUN/transcript.txt") lines, $(wc -c < "$RUN/transcript.txt") bytes"
  LAST_HDR_LINE="$(grep -n '^=== live_' "$RUN/transcript.txt" | tail -1 | cut -d: -f1)"
  echo "--- LAST TRANSCRIBED CHUNK (coverage horizon) ---"
  if [ -n "${LAST_HDR_LINE:-}" ]; then
    tail -n +"$LAST_HDR_LINE" "$RUN/transcript.txt" | head -45
  else
    echo "(no chunk headers found — file may be from a stale/older lane)"
  fi
else
  echo "(no transcript.txt in $RUN)"
fi

echo "--- chunk in flight (transcriber.log tail) ---"
tail -3 "$RUN/transcriber.log" 2>/dev/null || echo "(no transcriber.log)"

echo "--- chat tail (NEAR-REAL-TIME: offers, links, audience questions) ---"
if [ -s "$RUN/chat.txt" ]; then
  tail -c 4000 "$RUN/chat.txt"
else
  echo "(chat.txt empty or missing — an empty file is NOT proof chat was unreadable; read the open panel's DOM over CDP)"
fi

echo "--- newest screenshots (slide evidence) ---"
ls -t "$RUN"/shots/*.png 2>/dev/null | head -3 || echo "(no shots/)"
