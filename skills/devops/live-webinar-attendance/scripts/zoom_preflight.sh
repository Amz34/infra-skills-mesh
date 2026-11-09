#!/usr/bin/env bash
# Pre-flight for the Zoom webinar lane (~/ops/scripts/zoom_attend).
# Usage: zoom_preflight.sh <webinar_id> [label]
# Idempotent. Stops stale units, archives the old run dir, fixes guard state,
# extends the tab keep-list, and proves the audio chain with a tone injection.
set -uo pipefail

ID="${1:?usage: zoom_preflight.sh <webinar_id> [label]}"
LABEL="${2:-webinar-$ID-$(date +%m%d)}"
BASE="$HOME/ops/zoom-attend"
RUN="$BASE/run"
cdr=0
ok()   { printf '  OK   %s\n' "$*"; }
warn() { printf '  WARN %s\n' "$*"; cdr=1; }

echo "== 1. stop stale capture units =="
systemctl --user stop zoom-attend-recorder.service zoom-attend-scraper.service \
                     zoom-attend-transcriber.service 2>/dev/null
for u in recorder scraper transcriber; do
  state=$(systemctl --user is-active "zoom-attend-$u.service" 2>/dev/null)
  [ "$state" = "active" ] && warn "zoom-attend-$u still active" || ok "zoom-attend-$u stopped"
done

echo "== 2. archive previous run dir =="
if [ -d "$RUN" ]; then
  dest="$BASE/run-$(date +%Y%m%d-%H%M%S)-${LABEL}-ARCHIVED"
  if mv "$RUN" "$dest"; then ok "archived -> $(basename "$dest")"; else warn "could not archive $RUN"; fi
else
  ok "no previous run dir"
fi

echo "== 3. chrome sink guard =="
systemctl --user enable --now chrome-sink-guard.timer 2>/dev/null
state=$(systemctl --user is-active chrome-sink-guard.timer 2>/dev/null)
[ "$state" = "active" ] && ok "chrome-sink-guard.timer active" || warn "chrome-sink-guard.timer is '$state'"
sink=$(pactl info 2>/dev/null | awk -F': ' '/Default Sink/{print $2}')
echo "     default sink: ${sink:-unknown}"

echo "== 4. tab guard keep-list =="
KEEP="$HOME/ops/chrome_tab_guard_keep.txt"
touch "$KEEP"
for pat in "app.zoom.us/wc/$ID" "zoom.us/w/$ID"; do
  if grep -qF "$pat" "$KEEP"; then ok "keep-list has $pat"
  else printf '%s\n' "$pat" >> "$KEEP"; ok "keep-list += $pat"; fi
done

echo "== 5. audio self-test (700Hz tone into default sink) =="
mkdir -p "$RUN/audio"
ffmpeg -loglevel error -y -f lavfi -i "sine=frequency=700:duration=5" -f pulse "${sink:-auto_null}" \
  && ok "tone injected" || warn "tone injection failed (check sink name / pulse)"
sleep 6
newest=$(ls -t "$RUN"/audio/*.wav 2>/dev/null | head -1)
if [ -z "$newest" ]; then
  warn "no wav chunks yet — recorder not running (expected if units start after pre-flight)"
else
  mean=$(ffmpeg -hide_banner -i "$newest" -af volumedetect -f null - 2>&1 \
         | awk -F': ' '/mean_volume/{print $2}')
  echo "     newest chunk: $(basename "$newest") mean_volume=${mean:-n/a}"
  case "$mean" in
    -1[0-9]*|-2[0-9]*) ok "audio chain alive" ;;
    *) warn "weak/absent signal — recorder may not be hearing $sink" ;;
  esac
fi

echo
[ "$cdr" -eq 0 ] && echo "PRE-FLIGHT PASS" || echo "PRE-FLIGHT HAS WARNINGS (review above)"
exit "$cdr"
