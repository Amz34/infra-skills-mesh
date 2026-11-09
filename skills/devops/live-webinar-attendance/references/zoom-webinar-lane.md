# Zoom webinar lane — worked record (2026-10-17, webinar 81066653879)

Session: user dropped a Zoom registration link ~1h before start and asked to attend, capture,
QA and deliver presentation-style notes. Host never started during the observed window; the
capture lane itself was validated end-to-end (waiting room reached, audio chain proven with a
tone, recording + transcription live).

## Link shape

```
https://us06web.zoom.us/w/81066653879?tk=<credential>&uuid=WN_xxxxxxxxxxxxxxxxxxxx
```

- `/w/<id>` (not `/j/<id>`): the *webinar registration* landing page.
- `tk` is a per-attendee access token — treat as a credential, redact in chat and logs.
- The landing page has a main-frame **"Join from browser"** control; the actual meeting UI then
  lives in an iframe under `app.zoom.us/wc/<id>`.

## What failed and why

| Attempt | Result |
|---|---|
| `start.sh <tk-url> 'app.zoom.us/wc/<id>' <label>` | run dir created, units start, but `scraper.log` repeats `meeting tab not found` — tab URL is `us06web.zoom.us/w/...`, key is `app.zoom.us/wc/...`, no match |
| Playwright ad-hoc scripts | brittle (headless profile, no persistent CDP client); abandoned in favour of the `zoom_attend` lane |
| `cua_browser_prepare profile_mode=isolated_new` | refused: `browser_prepare requires a positive pid` — needs a pid from `list_windows`/`list_apps` first |

## What worked

```bash
# inspect what Chrome actually has open
curl -s http://127.0.0.1:9333/json/version
curl -s http://127.0.0.1:9333/json/list | jq -r '.[] | "\(.type) \(.url)"'

# main-frame join (tk link, not the wc URL)
python3 ~/ops/scripts/zoom_attend/open_join.py "https://us06web.zoom.us/w/<id>?tk=…&uuid=…"

# verify the tab is now in the waiting room
python3 ~/ops/scripts/zoom_attend/wcui_frame.py <id> '<id>/join' text

# start capture against that same Chrome
bash ~/ops/scripts/zoom_attend/start.sh "<tk-url>" 'us06web.zoom.us/w/<id>' 'webinar-<id>-1017' --no-open
```

Evidence the waiting room was reached: `wcui_frame.py … text` returned waiting-room copy and
participant count `0`, and the recorder's newest chunk measured `mean_volume: -91.0 dB` (silence
from an empty room, not a broken chain).

## Audio chain proof (tone injection)

```bash
# default sink was auto_null; no sink-inputs until Chrome actually plays
pactl info | grep 'Default Sink'
pactl list short sink-inputs           # empty before playback — normal

# inject a known tone straight into the sink the recorder monitors
ffmpeg -loglevel error -f lavfi -i "sine=frequency=700:duration=5" -f pulse auto_null

# measure the newest recorded chunk
newest=$(ls -t ~/ops/zoom-attend/run/audio/*.wav | head -1)
ffmpeg -hide_banner -i "$newest" -af volumedetect -f null - 2>&1 | grep -E 'mean_volume|max_volume'
```

Observed: `mean_volume: -18.1 dB` on the tone (chain OK), `-91.0 dB` on waiting-room audio.
`-f pulse -device=auto_null` is NOT valid — the pulse muxer takes the sink positionally.

The sink guard keeps Chrome's stream on `auto_null`; it ships **disabled**:

```bash
systemctl --user enable --now chrome-sink-guard.timer
systemctl --user is-active chrome-sink-guard.timer
```

## Stale-run hygiene

Before a new event, old services from a previous meeting were still running and spamming
`meeting tab not found`; `start.sh` had also archived the stale run dir under the *new* label.
Correct order:

```bash
systemctl --user stop zoom-attend-recorder.service zoom-attend-scraper.service \
                     zoom-attend-transcriber.service
mv ~/ops/zoom-attend/run ~/ops/zoom-attend/run-$(date +%Y%m%d-%H%M%S)-<old-label>-ARCHIVED
grep -q 'zoom.us/w/<id>' ~/ops/chrome_tab_guard_keep.txt || printf '%s\n%s\n' \
  "app.zoom.us/wc/<id>" "zoom.us/w/<id>" >> ~/ops/chrome_tab_guard_keep.txt
```

## End-of-event drain

`drain_on_end.sh` blocks until the scraper writes ENDED, stops the recorder, runs the transcriber
over the backlog and writes a notes skeleton into the run dir. It must run as a background process
with completion notification — a foreground `sleep` poll dies at ~7 min, and `nohup … &` from the
terminal tool also did not survive:

```
terminal(background=true, notify_on_complete=true) → bash ~/ops/scripts/zoom_attend/drain_on_end.sh
```

## Notes → deck

`build_deck.py <run_dir>` reads `notes.json` from the run dir and emits `deck.html` + `deck.pdf`
(16:9, `@page { size: 1280px 720px }`, dark theme `#2b4260` accent, `.body.noimg` variant centred
for text-only slides). Verify by rasterising pages:

```python
import pymupdf
doc = pymupdf.open("deck.pdf")
for i, page in enumerate(doc):
    page.get_pixmap(dpi=70).save(f"/tmp/deck_p{i}.png")
```

then inspect the PNGs for overflow / empty image slots before delivering.

## Delivery shape the user expects

Comprehensive, presentation-like: agenda → per-topic sections with the speaker's actual claims →
verbatim quotes → Q&A → action items → honest coverage note (captured window, participants, gaps).
Copied into chat as text **and** the PDF attached. No excuses framing if something external
(host no-show) blocks content — state what was captured and what it proves.
