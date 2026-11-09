#!/bin/bash
# Ken Burns rough-cut builder — stills + b-roll -> 30s preview video w/ audio.
# Free visual proof BEFORE paid avatar render. Produces preview/<name>.mp4.
#
# Edit SCENES below: each line = "DURATION|IMAGE_PATH|ZOOM_START|ZOOM_END"
#   DURATION in secs (float ok)  ZOOM 1.0 = full frame, 1.15 = zoomed in
# AUDIO muxed on top; video length bounded by audio (-shortest).
#
# Pitfalls baked in (all hit in production):
#   - bash float math -> awk (bash $(( )) is integer-only)
#   - zoompan needs setsar=1 before concat (SAR mismatch otherwise)
#   - prescale to ~8000px avoids zoompan pixel-stepping jitter
#   - ffmpeg input indices are 0-based: images 0..N-1, audio = index N
#   - yuv420p for Telegram/WhatsApp playback
set -e
cd "$(dirname "$0")/.."
mkdir -p preview

W=1280; H=720; FPS=25
NAME="client-ad-roughcut"                       # output base name
AUDIO="audio/demo-en30.mp3"                     # approved pacing demo
IMG2="/home/ubuntu/.hermes/cache/images/img_54ff2ce4b9d4.jpg"
VENTURI="/home/ubuntu/clients/AVVS-Triatek/site/assets/img/ref-venturi-closeup.png"
SERVICE="/home/ubuntu/clients/AVVS-Triatek/site/assets/img/ref-service.png"
CONTROLLER="/home/ubuntu/clients/AVVS-Triatek/site/assets/img/ref-controller.png"

# DUR|IMAGE|ZS|ZE    (AVVS 30s example scene map — edit per project)
SCENES=(
  "5|${IMG2}|1.00|1.15"
  "8|${VENTURI}|1.10|1.00"
  "4.5|${SERVICE}|1.00|1.12"
  "4.5|${CONTROLLER}|1.12|1.00"
  "7.5|${IMG2}|1.00|1.08"
)

N=${#SCENES[@]}
inputs=()
zooms=""
for i in $(seq 0 $((N-1))); do
  IFS='|' read -r DUR IMG ZS ZE <<< "${SCENES[$i]}"
  [ -f "$IMG" ] || { echo "MISSING: $IMG"; exit 1; }
  F=$(awk -v d="$DUR" -v f="$FPS" 'BEGIN{printf "%d", d*f}')
  inputs+=(-loop 1 -t "$DUR" -i "$IMG")
  j=$((i+1))
  zooms="${zooms}[${i}:v]scale=8000:-1,zoompan=z='(${ZS})+(${ZE}-${ZS})*on/${F}':d=${F}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=${W}x${H}:fps=${FPS},setsar=1,format=yuv420p[v${j}];"
done

concat=""
for j in $(seq 1 $N); do concat="${concat}[v${j}]"; done
concat="${concat}concat=n=${N}:v=1:a=0,format=yuv420p[vout]"

ffmpeg -y -loglevel error \
  "${inputs[@]}" \
  -i "$AUDIO" \
  -filter_complex "${zooms}${concat}" \
  -map "[vout]" -map "$N:a" \
  -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 128k \
  -shortest -movflags +faststart \
  "preview/${NAME}.mp4"

DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "preview/${NAME}.mp4")
echo "DONE: preview/${NAME}.mp4 (${DUR}s)"
