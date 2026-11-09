---
name: live-webinar-attendance
description: Use when attending a live webinar for the user.
version: 1.0.0
author: Aamir's Hermes
license: MIT
metadata:
  hermes:
    tags: [webinar, zoom, live, recording, transcript, notes, deck, pulse, chrome]
    related_skills: [live-session-capture, headless-browser-automation, html-to-pdf-ebook-production]
---

# Live webinar attendance → recording → notes deck

## When to Use

- User drops a webinar/online-event link ("attend this, send me notes", "meeting hai, join karo").
- The event must be attended unattended (waiting room, 1-2h runtime) and turned into a written
  deliverable afterwards — not just a URL summary.
- Anything involving Zoom web client, pulse/ffmpeg capture, captions scraping, whisper
  transcription, or a slide-deck style notes PDF.

For YouTube lives + the general `lc` toolkit, use `live-session-capture`. This skill covers the
**Zoom web-client lane** (`~/ops/scripts/zoom_attend/`), which has a different join mechanic and
different failure modes.

## The Zoom lane (`~/ops/scripts/zoom_attend/`)

| File | Role |
|---|---|
| `start.sh <zoom_url> <tab_url_key> <label>` | launches Chrome on CDP `127.0.0.1:9333`, starts recorder/scraper/transcriber units, creates `~/ops/zoom-attend/run` |
| `open_join.py <zoom_url>` | opens the link and clicks "Join from browser" in the MAIN frame; extracts `mk` from the URL itself |
| `wcui_frame.py <id> '<id>/join' text` | inspect/act inside the Zoom web-client iframe (`text` dumps visible text) |
| `drain_on_end.sh` | waits for ENDED, stops recorder, drains transcript, writes notes skeleton |
| `chrome_sink_guard.py` + `chrome-sink-guard.timer` | keeps Chrome's audio stream on the virtual sink so the recorder hears it |
| `build_deck.py` | `notes.json` → 16:9 `deck.html` + `deck.pdf` (Chrome headless print-to-pdf) |
| `status.sh` | one-shot: date, unit `is-active`, run dir state |

Run dir convention: `~/ops/zoom-attend/run` (live), archive as
`run-YYYYMMDD-HHMMSS-<label>-ARCHIVED`.

### Registration links (`/w/<id>?tk=...`) need a TWO-STEP join

`start.sh <url> 'app.zoom.us/wc/<id>'` alone **fails** on a `us06web.zoom.us/w/<id>?tk=…&uuid=…`
link: the interstitial ("Join from browser") lives on the `us06web` host, so the tab URL never
matches the `app.zoom.us/wc/…` key and the scraper just logs `meeting tab not found` forever.
Working sequence:

```bash
# 1) join in the main frame (needs the tk link, not the wc URL)
python3 ~/ops/scripts/zoom_attend/open_join.py "https://us06web.zoom.us/w/<id>?tk=<REDACTED>&uuid=<uuid>"
# 2) start the capture lane against the SAME Chrome, without re-opening the tab
bash ~/ops/scripts/zoom_attend/start.sh "<same url>" 'us06web.zoom.us/w/<id>' "<topic-label>-<MMDD>" --no-open
```

Pass the host that actually ends up in the address bar as the tab key. Confirm with
`curl -s http://127.0.0.1:9333/json/list | jq -r '.[].url'` before starting units.
Treat `tk` as a credential: never echo it into chat/logs, redact as `[REDACTED]`.

### Pre-flight (run before every attendance — 3 of these have silently killed runs)

1. **`chrome-sink-guard.timer` must be enabled+active.** It ships disabled; without it Chrome
   streams to the wrong sink and the whole capture is silence.
   `systemctl --user enable --now chrome-sink-guard.timer` → verify `is-active`.
2. **Stop stale units and archive the old run dir.** Leftover recorder/scraper/transcriber from a
   previous meeting keep running (looping `meeting tab not found`, capturing silence) and
   `start.sh` will archive them under the *new* label, mixing two events.
3. **Tab guard keep-list.** Append BOTH `app.zoom.us/wc/<id>` and `zoom.us/w/<id>` to
   `~/ops/chrome_tab_guard_keep.txt`, else the guard closes your tab mid-event.
4. **End-to-end audio self-test with tone injection** (see `scripts/zoom_preflight.sh`). Do this
   *before* the host starts: it separates "capture chain broken" from "room is just quiet".
   Inject a 700 Hz tone into `auto_null`, then `volumedetect` the newest wav → expect ≈ **-18 dB**;
   ≈ -91 dB means the chain is not receiving. Empty `pactl list short sink-inputs` before the
   event starts is normal — don't read it as a failure.

## Monitoring & end-of-event

- Poll with `~/ops/scripts/zoom_attend/status.sh` + `date -u`; check `scraper.log` for
  `meeting tab not found`, and the newest chunk's `mean_volume` for silence.
- **Do not sleep-poll hour-long waits in the foreground** — a foreground `sleep` call times out
  around ~7 min regardless of the requested timeout. Run `drain_on_end.sh` as a *background*
  process with `notify_on_complete=true`: it blocks on ENDED, drains the transcript, and the
  completion notification re-enters the session so the agent wakes up to build the deliverable.
- Say "attended" only with evidence: chunk count growing, non-silent `mean_volume`, and a
  transcript with words in it.

## Deliverable: presentation-style notes

`python3 ~/ops/scripts/zoom_attend/build_deck.py <run_dir>` → `deck.html` + `deck.pdf`
(16:9, dark professional theme, optional per-slide images from captured frames).

- Read the top of `build_deck.py` for the exact `notes.json` schema before authoring content —
  don't guess keys.
- **Verify visually before sending**: render pages with PyMuPDF at dpi≈70
  (`page.get_pixmap(...).save()`), then look at the images — check for text overflow, empty
  image slots, and orphaned headings. A deck that parses is not a deck that reads.
- Include: agenda, per-topic sections with the speaker's actual claims, verbatim quotes worth
  keeping, Q&A, action items, and an honest coverage note (captured window + any gap).
- Screenshots/photos: use captured frames; where a visual is needed and none exists, generate it
  (see the visual rule in project context) — never leave an "image later" gap.

## Pitfalls

1. **Tab-key/host mismatch** (above) — the single most common reason a "joined" run records nothing.
2. **Guard timer disabled** → perfect silence for the whole event, all status fields green.
3. **Waiting-room silence is not a bug.** `mean_volume ≈ -91 dB` with 0 participants before the
   scheduled start is expected; keep the recorder running so entry is captured the second the host
   starts.
4. **`ffmpeg -f pulse -device=auto_null` is invalid** — the pulse muxer takes the sink as a
   *positional* argument: `ffmpeg -f lavfi -i "sine=frequency=700:duration=5" -f pulse auto_null`.
   `-device=` is an alsa/oss option and dies with `Unrecognized option 'device=auto_null'`.
5. **Two browsers, two truths.** `start.sh` owns Chrome on CDP 9333; attaching a separate
   desktop/browser automation to the same webinar creates a second tab that is not the one being
   recorded. Always drive the CDP-9333 tab (`/json/list`), or use `open_join.py`.
6. **`cua_browser_prepare` needs a real browser pid** (`browser_pid_required`) — get it from
   `list_windows`/`list_apps` first. The Zoom lane doesn't need it at all.
7. **Don't promise a VOD/replay.** Notes come from what you actually captured.

## Verification checklist before telling the user "done"

- [ ] Pre-flight 1-4 all confirmed (guard `is-active`, stale units stopped, keep-list updated, tone ≈ -18 dB).
- [ ] In-event evidence: chunk count rising, `mean_volume` > -60 dB, transcript words > 0.
- [ ] Transcript finalised for every chunk but the last; `notes.json` present.
- [ ] `deck.pdf` rendered and **visually** inspected page by page.
- [ ] Delivery states the captured window, participant count, and any real gap.

Detailed command transcript, error strings, and the notes/deck flow: `references/zoom-webinar-lane.md`.
Re-runnable pre-flight: `scripts/zoom_preflight.sh <webinar_id> <label>`.
