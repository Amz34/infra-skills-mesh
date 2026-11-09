# Zoom web-client capture — concrete details (verified 2026-09, Oracle ARM VM)

## Join flow (headless Chrome on CDP :9333, already running via chrome-automation.service)
1. `curl -s -A "<desktop Chrome UA>" -D /tmp/hdr.txt "<invite link>"` → response headers reveal the web-client redirect target (`app.zoom.us/wc/<meeting-id>/…`). Treat headers as sensitive.
2. Open the invite URL in a **new tab** of the existing automation Chrome (never touch the user's other tabs).
3. Click through the pre-join screen: "Join from your browser" → (name field is pre-filled from the token) → Join. `#wc-join-audio-by-computer` / "Join Audio by Computer" may need a click before audio flows.
4. Enable captions: open the caption/transcript control (`Caption Language`, live-transcription panel). Captions then render into the DOM.
5. If the meeting needs to be left alone, do not raise the window, do not take focus — CDP works in the background.

## Useful DOM selectors / probes
| Purpose | Probe |
|---|---|
| In-meeting check | presence of meeting toolbar / `#wc-container-right` |
| Live caption line | `.live-transcription-subtitle__item` (fallback `.live-transcription-subtitle__content`) |
| Chat panel | click the chat toolbar button, then read message nodes |
| Audio flowing | `pactl list sink-inputs` alone is NOT proof: it can show a Chrome sink-input, unmuted, volume 100%, RUNNING — and every recorded segment is still digital silence. Confirm signal in the file itself (see "Audio really flowing?" below) |

Caption polling loop pattern: read the node text every ~4s; if it changed and the old text is a prefix of the new one, log only the delta; otherwise log the whole line. Keep a `last_line` and skip identical repeats — without it the file grows with duplicates.

## Input events that actually count (trusted gestures)
- JS `element.click()` is an **untrusted** event: it grants no user activation, so it cannot unblock autoplay / a suspended AudioContext. Use a real CDP click (`Input.dispatchMouseEvent`, helper `t.click(x, y)`).
- Click coordinates are **viewport** coordinates. A control whose box reports `y=839` on a ~813-px-tall viewport is off-screen: the click silently lands nowhere and reports no error. The Zoom footer toolbar only renders on hover, so toolbar buttons are unreliable targets — hover first, or probe the DOM instead of blind-clicking.
- Never print `location.href` of a Zoom web-client tab: the live URL carries the join `tk=` bearer token (`app.zoom.us/wc/<id>/join?tk=…`) and it lands in tool output, logs and context. Print a redacted form only. (Upside: that href is also how a lost session is recoverable — a Chrome restart is not automatically fatal — but the value must never be echoed.)

## Audio really flowing? (verify, don't assume)
Growing segment files / `du -sh audio` climbing proves nothing — silence is still bytes. Two checks, ~30s, both in `scripts/zoom_audio_check.sh`:

1. Level of the newest segment: `ffmpeg -sseof -5 -i <newest>.wav -af volumedetect -f null - 2>&1 | grep max_volume` → **`max_volume: -91.0 dB` = digital silence**. A silent recording is useless even though the unit is `active` and the directory is megabytes.
2. Separate "capture chain broken" from "source is silent" with a tone round-trip: play a sine into the same sink while recording its monitor
   `(ffmpeg -f lavfi -i sine=frequency=440:duration=6 -f pulse auto_null >/dev/null 2>&1 &) ; sleep 1; timeout 30 ffmpeg -f pulse -i auto_null.monitor -t 4 -y /tmp/tone.wav; ffmpeg -i /tmp/tone.wav -af volumedetect -f null - 2>&1 | grep max_volume`
   Tone captured (≈ -18 dB) ⇒ plumbing is fine and **the browser is rendering silence**.

## When the browser renders silence
Observed 2026-09 (headless Chrome, Xvfb, meet joined as attendee with captions streaming): zero audio in every segment. Ruled out first — the Chrome unit has **no `--mute-audio`** flag on this VM, and the sink-input was unmuted. Root cause: the Zoom web client plays remote audio through WebAudio/WebRTC, so the page's `<audio>` element sits at **`paused=true, src=none`**; calling `.play()` on it does nothing and a trusted CDP click does not revive it.

Do NOT restart Chrome to chase this: with a token-bearing join link a restart can cost the whole attendance. Instead:
- Treat **live captions as the transcript** (they were complete and ~2s behind), keep slide shots + chat.
- **Stop the whisper transcriber** — whisper on digital silence invents text ("you you"), and a junk `transcript.txt` looks exactly like a real transcript. `systemctl --user stop zoom-attend-transcriber`, `mv transcript.txt transcript.silence.bak`, restart only after audio is verified.
- Say so plainly in the report (content still covered by captions) rather than implying a full audio recording exists.

## CDP helper (`~/ops/scripts/zoom_attend/cdp_lib.py`)
Minimal driver, no Selenium: `GET http://127.0.0.1:9333/json` → pick the tab by URL substring → open its `webSocketDebuggerUrl` with the `websocket` client → send `Runtime.evaluate` for JS reads and `Page.captureScreenshot` for shots. Requires an interpreter where `import websocket` works (Hermes venv python). Method name note: the helper's JS eval method is `t.js(expr)` — an older `t.eval(...)` spelling must not be used.

## Capture commands
- Audio: `ffmpeg -f pulse -i <sink>.monitor -ac 1 -ar 16000 -f segment -segment_time 300 -reset_timestamps 1 live_%03d.wav`
- Shots: CDP `Page.captureScreenshot` every 45s → `shots/*.png`
- Chunked transcript: for each closed wav (skip the newest, still-writing file), run the local whisper wrapper with the `base` model, low priority / one thread, append `[HH:MM] text` to `transcript.txt`, and keep a `transcribed.json` state map so segments are never processed twice.

## systemd --user unit skeleton
```ini
[Unit]
Description=Zoom attendee recorder
After=graphical-session.target
[Service]
Type=simple
ExecStart=/usr/bin/ffmpeg -f pulse -i auto_null.monitor ... live_%%03d.wav
Restart=on-failure
RestartSec=15
[Install]
WantedBy=default.target
```
Remember: escape `%` in ffmpeg patterns, and point Python services at the venv interpreter that has `websocket`.

## Cron watchdog prompt skeleton (monitor mode, every 5 min, deliver=origin)
- Monitor prints `STATE=LIVE|ENDED`, caption count, and deduped MENTION lines.
- Agent instructions: (1) if a `DONE` file exists and no new mentions → reply `[SILENT]`; (2) if `STATE=ENDED` and no `DONE` → stop the units, transcribe leftovers, write the English notes file, deliver the Hinglish summary, then `touch DONE`; (3) if new MENTION lines → short alert quoting them. Cap replies (~1200 chars) and never message when nothing changed.

## End state to hand the user
Notes file path, what was captured (audio/captions/shots/chat), what could NOT be verified (display name, anything before join time), and the explicit "listen-only" caveat.
