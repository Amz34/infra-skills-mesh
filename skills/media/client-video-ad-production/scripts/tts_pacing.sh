#!/bin/bash
# edge-tts pacing demo generator for client ad scripts (EN/AR).
# Proves a script fits the duration budget (e.g. 30s) BEFORE any paid render.
# edge-tts location: /home/ubuntu/.hermes/hermes-agent/venv/bin/edge-tts (7.x)
#
# Usage:
#   tts_pacing.sh "<english text>" "<arabic text>" [target_secs]
# Output: audio/demo-en30.mp3, audio/demo-ar30.mp3 + durations printed.
#
# Calibration (30s target, from AVVS case):
#   EN ~82 words: en-US-AndrewMultilingualNeural @ +2%  -> ~29.5s
#   AR same meaning: ar-SA-HamedNeural @ +18% (or trim)  -> ~29.8s
#   AR @ +14% -> 34.3s | +16% -> 32.1s | +18% -> 29.8s
set -e
cd "$(dirname "$0")/.."  # run from project root (venturi-ad/ etc.)
mkdir -p audio
EDGE=/home/ubuntu/.hermes/hermes-agent/venv/bin/edge-tts
EN_TEXT="$1"
AR_TEXT="$2"
TARGET="${3:-30}"

echo "EN demo..."
"$EDGE" --voice en-US-AndrewMultilingualNeural --rate=+2% --text "$EN_TEXT" \
  --write-media audio/demo-en30.mp3 2>/dev/null
EN_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 audio/demo-en30.mp3)
echo "EN = ${EN_DUR}s (target ${TARGET}s)"

echo "AR demo (start +18%, adjust if needed)..."
"$EDGE" --voice ar-SA-HamedNeural --rate=+18% --text "$AR_TEXT" \
  --write-media audio/demo-ar30.mp3 2>/dev/null
AR_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 audio/demo-ar30.mp3)
echo "AR = ${AR_DUR}s (target ${TARGET}s)"
echo
echo "AR overshoot? Trim text OR re-run with rate +20%..+25%."
echo "AR undershoot (< target-2s)? Lower rate toward +10%."
