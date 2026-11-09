#!/usr/bin/env bash
# zoom_audio_check.sh — is the meeting audio ACTUALLY being recorded?
#
# Usage: zoom_audio_check.sh [run_dir] [sink]
#   run_dir  default ~/ops/zoom-attend/run   (expects <run_dir>/audio/*.wav)
#   sink     default auto_null               (Pulse/PipeWire sink under test)
#
# Why: a recorder unit can be `active` and writing multi-MB segments that are
# entirely digital silence — file size and unit state prove nothing. Whisper on
# silence invents text, so verify BEFORE trusting transcript.txt.
#
# Reading the output:
#   tone ~-18 dB  => capture chain is fine; meeting file silent means the BROWSER
#                    is rendering silence (Zoom web client = WebAudio/WebRTC).
#                    Do NOT restart Chrome if joined via a token link — rely on
#                    live captions and stop the whisper transcriber.
#   tone -91 dB   => sink/monitor plumbing broken; fix that first.
#   both -91 dB   => no audio anywhere; stop the transcriber.
set -u

RUN_DIR="${1:-$HOME/ops/zoom-attend/run}"
SINK="${2:-auto_null}"
AUD="$RUN_DIR/audio"

level() { ffmpeg -sseof -5 -i "$1" -af volumedetect -f null - 2>&1 | grep -o 'max_volume: .*'; }

echo "== newest recorded segment =="
NEWEST=$(ls -t "$AUD"/*.wav 2>/dev/null | head -1)
if [ -z "${NEWEST:-}" ]; then
  echo "no .wav segments under $AUD"
else
  echo "$NEWEST"
  level "$NEWEST"
fi

echo "== tone round-trip through sink '$SINK' =="
(ffmpeg -f lavfi -i sine=frequency=440:duration=6 -f pulse "$SINK" >/dev/null 2>&1 &)
sleep 1
timeout 30 ffmpeg -f pulse -i "$SINK.monitor" -t 4 -y /tmp/zoom_tone_probe.wav >/dev/null 2>&1
if [ -f /tmp/zoom_tone_probe.wav ]; then level /tmp/zoom_tone_probe.wav; else echo "monitor '$SINK.monitor' not recordable"; fi

echo
echo "units: $(systemctl --user is-active zoom-attend-recorder zoom-attend-scraper zoom-attend-transcriber 2>/dev/null | tr '\n' ' ')"
