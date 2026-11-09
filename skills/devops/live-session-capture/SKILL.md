---
name: live-session-capture
description: Use when joining/recording a live session (lc toolkit).
version: 1.0.0
author: Aamir's Hermes
license: MIT
metadata:
  hermes:
    tags: [live, recording, webinar, youtube, chrome, audio, pulse]
    related_skills: [headless-browser-automation, infra-hardening-crashproof, youtube-content]
---

# Live session capture (`lc` toolkit)

## When to Use

- The user drops a live URL and wants it attended/recorded ("join this masterclass").
- A session must be captured unattended for hours (webinar, YouTube live, product launch).
- You need audio + transcript + whiteboard frames + a written brief from a live event.
- Anything involving headless Chrome + pulse audio capture + long unattended runs.

Built 2026-09-17 out of the Liam Ottley/Kylon masterclass run; supersedes the ad-hoc scripts in
`~/ops/yt-attend/`. Covers the failure modes that silently killed hour-long captures.

## Quickstart

```bash
~/ops/bin/lc start "https://www.youtube.com/live/<ID>" --title "Masterclass X"
~/ops/bin/lc status                 # heartbeat: playback ct, chunks, dB, lane, guard-keep
~/ops/bin/lc stop                   # teardown + final transcribe + manifest + guard revert
~/ops/bin/lc verify                 # V1..V11 QA; exit 0 = pass
~/ops/bin/lc selftest               # offline end-to-end QA incl. player-crash self-heal
~/ops/bin/lc wait "<url>" --poll 60 # block until live, then start (scheduled streams)
```

Code: `~/ops/livecapture/{lcdrv.py,lc_sup.py,lc.py,lc_watch.py,tests/}`; README has full detail.
Runs: `~/ops/livecapture/runs/<date>-<slug>-<HHMMSS>/` (run.json, audio/, frames/,
transcript.txt, manifest.json, logs). Supervisor = systemd user unit `lc-<slug>-<HHMMSS>`.
Cron watchdog `d1e6eb2b3418` (no_agent, */15) stays silent while healthy and alerts on stale
heartbeat, silent audio, dead children, lane contamination, stream-ended-still-recording.

## Architecture (one durable unit per run)

`lc start` → run dir + private null-sink + guard-keep entries, then `systemd-run --user
--property=Restart=on-failure` for the supervisor (a clean exit means "intentional stop"; a
crash exits non-zero so systemd brings the capture straight back). The supervisor owns: persistent CDP websocket,
Chrome relaunch / tab presence / playback enforcement, audio-lane routing, ffmpeg recorder
child, whisper transcriber child, CDP frame captures, heartbeat into `run.json`.
Stop protocol = `run.json.stop_requested=true` (set by `lc stop`).

## Pitfalls that will bite again

1. **`chrome_tab_guard.py` R5 reaps a legitimately clientless Chrome** (no ESTAB CDP client for
   12 min, 2 strikes → SIGTERM). Symptom: capture dies every ~13-17 min with a clean exit.
   Two fixes, both needed: hold ONE persistent CDP websocket, and register the instance in
   `~/ops/chrome_tab_guard_keep_instances.txt` (`profile:<udd>` / `port:<n>`). `lc` does both;
   `lc stop` removes them. R3 (idle-tab close) is the second killer — keep the URL in
   `~/ops/chrome_tab_guard_keep.txt` too.
2. **Never `pactl move-sink-input` blind.** Move only streams whose owning PID (or an ancestor)
   carries your `--user-data-dir` (`Lane.is_ours`). Blind moves pull another lane's audio into
   your recording AND (the other direction) evict your own player, producing silent chunks.
   Verify with `pactl -f json list sink-inputs` + `/proc/<pid>/cmdline`.
3. **Recorder restarts must pass `-segment_start_number`**, else `-y chunk_%03d.wav` restarts at
   000 and overwrites earlier audio.
4. **One writer per run dir.** Use `lcdrv.RunLock` (flock). On 09-17 a wrap-up cron agent
   overwrote the notes file while the live agent was still writing.
5. **`pgrep -f 'user-data-dir=X'` matches your own shell** → phantom "leftover chrome" in
   teardown checks. Use `lcdrv.chrome_procs_for_profile()` (pure /proc scan).
6. **Silent audio is the failure you don't see**: check `mean_volume` of the newest finished
   chunk (`Lane.level_db`); < -60 dB means capture lost its audio. `lc verify` V2/V3 and
   `lc_watch.py` both enforce this.
7. **YouTube**: the page can be live while yt-dlp refuses ("Sign in to confirm you're not a
   bot") — use the signed-in Chrome profile
   (`--cookies-from-browser "chrome:<profile>"`). Liveness without Chrome: curl the watch page
   and grep `"isLive":true` / `"isLive":false` (CDP-free, so a capture outage cannot be misread
   as "stream ended"). A post-live VOD may not be available immediately — do not promise it.
8. **Headless audio**: Chrome needs a null-sink (`pactl load-module module-null-sink`), a running
   Xvfb display, and `PULSE_SINK` at launch; verify a sink-input actually appears on that sink.

9. **Driver liveness must be strict.** `ChromeDriver.up()` requires BOTH a non-empty CDP
   `/json/version` body and a real Chrome process on the profile. A truthy-but-empty check made
   a dead browser look alive: `launch()` never ran and the run recorded pure silence while every
   status field said "up" (caught by the 2026-09-17 Chrome E2E). `lc start` now launches Chrome
   eagerly so a broken browser aborts the start instead of silently capturing nothing.
10. **Don't send a child's stdout into the file it already logs to** (`lcdrv.log_line` prints as
   well) — every transcriber line appeared twice. Children log their own way; spawn with DEVNULL.
11. **`systemctl --user reset-failed lc-*` after a stop**, otherwise a `Restart=on-failure` unit
   with `--collect` lingers in `activating (auto-restart)` and the next run's unit name collides.

## Zoom lane vs lc toolkit — transcription pitfalls (2026-10-18, webinar 81066653879)

The older `~/ops/scripts/zoom_attend/*` lane (recorder + `transcribe_chunks.py` + `scrape.py`)
captures audio fine but its transcript can be **entirely hallucinated**: whisper.cpp `base` on
quiet Zoom segments emitted only `"you you you [BLANK_AUDIO]"` for all 58 chunks (≈4 h 47 m of
audio, zero usable words). Do not trust transcript.txt — check it before analysing.

1. **Verify signal before trusting a transcript.** `ffmpeg -i chunk.wav -af volumedetect -f null -`
   → mean −24…−30 dB, peak ≈0 dB means real audio; if the transcript is still filler, the STT is
   the problem, not the capture.
2. **Transcribe with Gemini when local STT underperforms.** `models/gemini-3.5-flash` /
   `3.6-flash` accept inline audio (`inline_data`, base64 WAV; ≤20 MB request) and did a 5-min
   segment in 4–15 s. `gemini-2.5-flash` is 404 for new keys — list models first
   (`/v1beta/models?key=`) and keep a fallback chain (3.6-flash → 3.5-flash → 3.8-flash).
3. **Gemini hallucinates on near-silence** (it invented an entire AWS/MuleSoft talk for quiet
   chunks). Sanity-check topic continuity across segments; discard segments whose text doesn't
   mention the session's subject, and rebuild that window from captured slides instead.
4. **faster-whisper small int8 on 2 vCPU ≈ 0.5× realtime** (158 s audio → 297 s) and
   whisper.cpp small is similar — both are too slow for 3 h of audio. Prefer the API path.
5. **Slides carry the content when audio fails**: `tesseract` on video-compressed 1600×1000 frames
   is noisy; sending 6 frames per Gemini vision call and asking for verbatim slide text gives
   clean, quotable copy. Sample every 60–120 s, then dedupe.

## Deliverable after the session

**Never ship the deck builder's smoke test.** `build_deck.py` run against `/tmp/testnotes.json`
produces a valid PDF full of placeholders ("Slide one / alpha / beta", "Audio 8/10 ok") — it looks
like a deliverable and is worthless. Always open the final PDF and read pages 1, a middle slide,
the QA table and the last slide before sending.

Also: `build_deck.py <run_dir> <notes.json>` — argument order matters (notes path first fails with
`JSONDecodeError: Expecting value: line 1 column 1`). Schema: `title, subtitle, meta, slides[{h,
points, img, note}], qa[{dim, score, comment}], takeaways[], actions[{what, who, when}]`, with `img`
relative to run_dir.

**Report measured numbers only.** In the 2026-10-18 run the first report claimed "37 segments,
6,719 words, 177 screenshots" — none of it measured, and all of it wrong (real: 58 segments,
~10.4 k words, 340 frames). Run `ls | wc -l` and `wc -w` before quoting metrics.

`run.json` + `frames/` + `transcript.txt` are enough for a written brief (delegate the
summarisation if the transcript is long). Keep audio until `manifest.json` exists, then prune.
Report coverage honestly: name the captured window and every real gap.

## Verification checklist before telling the user "done"

- `lc verify` → 0 FAIL; `manifest.json` present.
- `lc status` shows `cdp_ws_held: true`, lane ours ≥ 1, foreign/unknown 0.
- No stray processes, sink unloaded, guard keep entries reverted.
- Transcript covers every chunk but the last; frames show whiteboard/demo moments.
