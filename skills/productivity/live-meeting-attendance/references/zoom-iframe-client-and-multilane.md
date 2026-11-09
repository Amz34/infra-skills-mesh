# Zoom iframe client + multi-lane field notes (2026-09-17)

Context: two live Zoom sessions attended in parallel on the automation Chrome (CDP `:9333` /
`app.zoom.us/wc/…`) — "AGENTIC AI MASTERCLASS" (`89689313605`, joined from a `/meeting/register/`
link) and "ChatGPT-6 Astra Workshop" (`85420434468`, re-opened in a second tab because the user
asked for the other tab too). Everything below was verified live in that session.

## 1. Frame topology (registration-link join)
- `/meeting/register/<id>` → SPA form: `#question_first_name`, `#question_last_name`,
  `#question_email`, `#question_phone` (CDP `Input.insertText` after focusing; the SPA then
  navigates itself to the join URL).
- Result page: `https://app.zoom.us/wc/<mn>/join?ref_from=launch&tk=<JWT>`. Frames found:
  `parent (…/join?ref_from=launch&tk=…)` + `child (same URL)`; the toolbar / Join button /
  participants / captions all live in the child. Deepest matching frame = the client.
- The `/w/<mn>?tk=…&uuid=…` page renders "Join from browser" in the **main** frame; clicking it
  navigates to the wc client, which auto-joined (no separate Join click) when the `tk` was valid.
- Frame-aware probing (verified working): `Page.getFrameTree` → recurse `childFrames` → keep frames
  whose `url` contains the meeting number → take the last one → `Page.createIsolatedWorld(frameId,
  worldName)` → `Runtime.evaluate(expression, contextId, returnByValue=True)`. DOM queries and
  `el.click()` inside the isolated world are enough; no page helpers needed.
- Useful in-frame text markers (English account): preview = `Mute` / `Start Video` / `Join`;
  in meeting = `Leave` + `Participants (n)`. Match case-insensitively; a caption overlay node
  (`.lt-subtitle-wrap`) can exist while empty — empty means "nobody speaking", not "broken".

## 2. The audio-element drop (biggest pitfall found)
Evidence of the failure: frame text contains `leave` (so the session IS in the meeting),
`document.querySelectorAll('audio').length === 0`, `parec --device=auto_null.monitor` RMS `0.0`,
and the recorder's newest segment is digital silence. Live captions keep arriving — they ride the
data channel, **not** the audio stream — so captions are not proof that audio is playing.
Triggers observed: opening/joining the second meeting tab; creating a new null sink; `setSinkId` on
another tab's element; general tab churn. The client never restores playback by itself.
Recovery (verified, ~15 s): `Page.reload` the tab → it returns to the pre-join preview
(`Mute` / `Start Video` / `Join`) → click `^Join$` in the deepest frame → back in meeting, audio
element count `1`, sink RMS > 0. Note a `ref_from=launch` page does **not** auto-join on reload
(unlike a `/w/…` click-through, which did), so the Join click is mandatory.
Consequence for health checks: `in-meeting text AND audio count ≥ 1 AND sink RMS > 0` — never the
first alone.

## 3. Per-meeting audio isolation (setSinkId)
- `pactl load-module module-null-sink sink_name=AstraSink sink_properties=device.description=AstraSink`
  → capture with `parec --device=AstraSink.monitor`.
- Inside the meeting frame: `navigator.mediaDevices.enumerateDevices()` (Chrome lists the sinks as
  `audiooutput`, labels visible) → find `label === 'AstraSink'` → `el.setSinkId(entry.deviceId)` for
  every audio element of that tab. Verified: that tab's audio then showed on `AstraSink.monitor`
  (RMS ≈ 1900) while the other meeting stayed on `auto_null.monitor`.
- Caveat that decided the architecture: the move itself can blank the *other* tab's element, and
  both meetings were never simultaneously clean in one Chrome (each repair broke the other lane).
  Final shape: primary meeting = audio on the default sink (recorded); secondary meeting = attended,
  captions captured, its elements parked on the secondary sink so they cannot pollute the primary.
- Which stream is which: mute-test (`el.muted = true`) and/or transcribe ~8 s of the sink
  (`whisper_transcribe <wav> base en`) and listen to *who* is talking.

## 4. Multi-lane wiring
- `~/.config/zoom-attend/current2.env`:
  `ZOOM_RUN=/home/ubuntu/ops/zoom-attend/run-masterclass-0917`, `ZOOM_TAB_KEY=app.zoom.us/wc/89689313605`,
  `ZOOM_FRAME=89689313605`.
- `scrape.py` / `transcribe_chunks.py`: one-time patch to `RUN = os.environ.get("ZOOM_RUN", <default>)`;
  `scrape.py` binds `ZOOM_FRAME` (deepest match). Without `ZOOM_FRAME`, a frame-rendered client looks
  like "meeting UI gone" to the scraper → it writes a **false `ENDED`** every restart (observed in a
  loop). The old lane needed `ZOOM_FRAME=85420434468/join` added to its own `current.env` after its
  tab was reloaded into the iframe shape.
- Lane units `zoom2-recorder|scraper|transcriber.service`, `EnvironmentFile=-%h/.config/zoom-attend/current2.env`,
  recorder writing `-strftime 1` segments so a restart never overwrites `live_*.wav`.
- Per-lane workflow that worked: `wcui.py` / `wcui_frame.py` / `join_lane.py` (open tab → click
  "Join from browser" → `^Join$` in the deepest frame → report in-meeting + audio count).

## 5. Watchdog + wrap-up split (what actually ran)
- `~/ops/scripts/zoom_attend/lane2_watch.py`, invoked by `~/.hermes/scripts/zoom2_watch.sh`, cron
  every 5 min with `no_agent=True`: prints **nothing** while healthy (empty stdout ⇒ no message, no
  LLM). Checks: (a) `systemctl --user is-active` for the three lane units → restart; (b) CDP reachable
  and a tab with the lane's meeting number; (c) in-meeting text; (d) `document.querySelectorAll('audio').length`;
  (e) `parec` sink RMS with a 2-strike debounce. Heals with a throttled reload+rejoin; state in
  `run/health_state.json` (strikes, cooldowns: rejoin 600 s, alert 1800 s); announces `ENDED` once.
- `~/.hermes/scripts/zoom2_monitor.py` (separate agent cron, `monitor_script`) prints one stable line
  `LANE2_ENDED=yes|no` → the agent wakes exactly once, at the end, to transcribe leftovers, write the
  notes/learnings file and QA. Verified: the script stayed silent while healthy; the monitor's
  hash-suppression means no LLM cost until the flip.
- After any manual reload/rejoin/lane surgery: `rm -f <run>/ENDED`, otherwise the monitor and the
  wrap-up cron both finalize a meeting that is still running.

## 6. Reusable probes
- Level: `parec --device=<sink>.monitor --rate=16000 --channels=1 --format=s16le` →
  `struct.unpack('<%dh', buf)[::7]` → RMS/peak in plain Python (`audioop` is gone in 3.13).
- Interpreter that has `websocket-client` for CDP on this VM:
  `/home/ubuntu/.hermes/hermes-agent/venv/bin/python3`.
- Non-English clients: match toolbar controls case-insensitively and fall back to
  `aria-label`/`title` attributes when `innerText` differs by locale.
