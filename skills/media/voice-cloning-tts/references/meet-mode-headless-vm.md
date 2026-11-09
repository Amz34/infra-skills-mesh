# Headless-VM Google Meet Presence (AI voice agent attends meetings)

Verified end-to-end 2026-08-22 on Oracle Cloud ARM64 Ubuntu (no GPU, no sound card, Xvfb :99).
Environment: Chrome 151.0.7922.137, PulseAudio 16.1, Python 3.11 venv `meetenv`.

## Architecture

```
User's phone/Meet  ⇄  Google Meet (browser, Xvfb :99)  ⇄  AI pipeline
                          ▲  speaker path                     │
                          │  Chrome output → aloop sink        │
   meet audio captured from aloop .monitor                    │
                          │                                    ▼
            Whisper STT → DeepSeek (Mozzaz) → XTTS (user voice)
                          │                                    │
              AI speech → ai_out sink (module-alsa-sink)  ─────┘
              Chrome mic = ai_out.monitor (PULSE_SOURCE env)
```

Key insight: **Chrome enumerates ALSA devices only** (via libasound + ~/.asoundrc pulse
plugin), NOT PulseAudio sinks directly. PulseAudio null-sinks (`module-null-sink`) are
invisible to Chrome — this is why `PULSE_SINK`/`PULSE_SOURCE` env vars alone did nothing.

## Setup steps (exact order)

1. **Virtual sound card (ALSA level):**
   ```bash
   sudo modprobe snd-aloop          # creates card 0, hw:0,0 + hw:0,1 (8 subdevices)
   ```
2. **Audio group / permissions** — user must access /dev/snd:
   ```bash
   sudo usermod -a -G audio ubuntu   # needs re-login to take effect
   sudo chmod 666 /dev/snd/*         # immediate fix for current session
   ```
3. **PulseAudio restart** so it detects the aloop card:
   ```bash
   pkill -9 pulseaudio; sleep 2
   pulseaudio --start --exit-idle-time=-1
   pactl list cards short   # expect alsa_card.platform-snd_aloop.0
   ```
4. **AI→Meet path (second sink):**
   ```bash
   pactl load-module module-alsa-sink device=hw:0,1 name=ai_out
   # Chrome mic = alsa_output.ai_out.monitor  (PULSE_SOURCE when launching Chrome)
   # AI speaks into  alsa_output.ai_out       (parec/pactl play target)
   ```
5. **ALSA default → PulseAudio plugin** (`~/.asoundrc`):
   ```
   pcm.!default { type pulse }
   ctl.!default { type pulse }
   ```
   Needs `libasound2-plugins` package. Verify: `aplay -D default file.wav` exit 0.
6. **Set defaults** so Chrome's ALSA stream lands where the agent can capture:
   ```bash
   pactl set-default-sink alsa_output.platform-snd_aloop.0.analog-stereo
   pactl set-default-source alsa_output.ai_out.monitor
   ```
7. **Launch Chrome (GUI on Xvfb, audio-sandbox OFF):**
   ```bash
   PULSE_SINK=alsa_output.platform-snd_aloop.0.analog-stereo \
   PULSE_SOURCE=alsa_output.ai_out.monitor \
   DISPLAY=:99 google-chrome --no-sandbox --disable-gpu --disable-audio-sandbox \
     --autoplay-policy=no-user-gesture-required \
     --remote-debugging-port=9242 --user-data-dir=/tmp/chrome-bu \
     "https://meet.google.com/CODE"
   ```
   `--disable-audio-sandbox` is MANDATORY — Chrome audio service can't open ALSA in sandbox.
8. **Connect automation daemon to this Chrome** (browser-harness scans default profiles,
   NOT custom ones — use BU_CDP_URL):
   ```bash
   timeout 30 /home/ubuntu/.hermes/bin/browser-use --reload
   export BU_CDP_URL="http://localhost:9242"
   browser-harness <<'PY'
   print(page_info())   # confirms daemon bound to custom Chrome
   PY
   ```
9. **Grant mic permission via CDP** (no UI click needed — headless VM has no dialog):
   ```python
   cdp('Browser.grantPermissions', permissions=['audioCapture','videoCapture'],
       origin='https://meet.google.com')
   ```
   After grant, Meet mic button reads "Default" instead of "Permission needed".
10. **Join:** fill `input[placeholder="Your name"]` → click button containing
    "Ask to join" → page shows "Please wait until a meeting host brings you into the call".
    Host (user) taps **Admit** on their own device.

## Verification probes

- `pactl list cards short` → aloop card present
- `curl -s localhost:9242/json/version` → Chrome responds on CDP
- In page JS: `navigator.mediaDevices.enumerateDevices()` → must show audioinput+audiooutput
  (was empty [] while stale Chrome instances were stacked — see pitfall)
- `parec --device=alsa_output.platform-snd_aloop.0.analog-stereo.monitor
  --format=s16le --rate=16000 --channels=1 --raw | head -c 32000` → ~1s of data = pipeline live
- **AI→Meet path probe:** `ffmpeg -f lavfi -i "sine=frequency=880:duration=5" -y /tmp/beep5.wav`;
  `(paplay --device=alsa_output.ai_out /tmp/beep5.wav &)` then record
  `alsa_output.ai_out.monitor` 4s → rms>1000 = AI speech reaches Chrome mic
- **Chrome output probe:** page JS `new AudioContext()` + 440Hz oscillator (0.5 gain) →
  record `platform-snd_aloop.0.analog-stereo.monitor` → rms≥1000 = Chrome audio pipeline live
- **Meet in-call probe:** `document.title` contains `Meet - <CODE>` AND body text contains
  mic button labels; Arabic homepage (`مكالمات جماعية`) = dropped out, must rejoin

## PITFALLS (each cost real debugging time)

- **`pkill -f "google-chrome"` does NOT match `/opt/google/chrome/chrome`** — the real
  binary's command line lacks the string "google-chrome". Stale instances stack up, the
  new launch just signals the old one, device enumeration silently returns `[]`.
  ALWAYS kill with `pkill -9 -f "/opt/google/chrome"` (or `pkill -9 chrome`).
- PulseAudio null-sinks are invisible to Chrome → ALSA loopback is the way.
- `audio` group membership only applies after re-login; `chmod 666 /dev/snd/*` is the
  immediate session fix.
- Headless mode (`--headless=new`) can't see audio devices; must run GUI Chrome on Xvfb.
- Camera will always read "Camera not found" — expected, turn it off before joining.
- Colab branch gotcha (unrelated but adjacent): Colab URLs pin `blob/main`; if repo default
  branch is `master`, Colab errors "No commit found for the ref main". Fix: rename branch
  and set default: `git branch -m master main && git push origin main && gh repo edit --default-branch main`.
- **`parec | ffmpeg` record pipe HANGS forever** — parec streams endlessly, ffmpeg waits for
  EOF that never comes; chunk.wav keeps growing (5s window → 9.9MB/5min file) and the agent
  NEVER transcribes/replies ("kuch nahi aya" symptom). Fix in `record_from_monitor`: direct
  `ffmpeg -f pulse -i <monitor> -t <seconds> -ar 16000 -ac 1 -y out.wav` with hard `-t`
  duration, wrapped in `subprocess.Popen(..., preexec_fn=os.setsid)` +
  `os.killpg(os.getpgid(proc.pid), SIGKILL)` on timeout. Verified: exact 5s → 158KB file.
- **Agent can run WITHOUT the cloned voice** — `main()` resolves the reference path via an
  `if/elif` chain; a wrong hardcoded default (`.../ref_voice.wav`) silently falls through to
  no reference and the agent logs `WARNING: reference voice nahi mila`. Fix: default
  `REF_AUDIO="/tmp/ref.wav"`, check `os.path.exists(REF_AUDIO) and os.path.getsize()>10000`
  FIRST, and always confirm the boot log shows `Using reference voice: /tmp/ref.wav` before
  telling the user to test.
- **User's Telegram voice note = clone reference**: Hermes stores incoming voice notes at
  `/home/ubuntu/.hermes/cache/audio/*.ogg` (same file may appear in multiple profile dirs —
  identical size = duplicates). Convert: `ffmpeg -y -i note.ogg -ar 22050 -ac 1 /tmp/ref.wav`.
  No need to ask the user for a fresh note if one already exists on disk.
- **Agent log appears empty while running** — `python3 -u` in the launch + `grep -vE` pipe
  buffers output, so `process log` shows 0 lines until buffer flushes. Don't kill/restart on
  empty logs; verify liveness via filesystem + Pulse instead: `ls -la /tmp/meet_*/chunk.wav`
  (fresh mtime = recording; ~160KB = correct 5s, multi-MB = record hang) and
  `pactl list source-outputs short` (a `1ch 16000Hz` protocol-native entry = agent's
  parec/ffmpeg stream is attached to the monitor).
- **Silence threshold too strict = "user talking but AI never replies"** — default VAD
  threshold (200) SKIPPED the user's real speech (measured rms≈108–174). Symptom: agent
  logs `silent (rms=NNN) — skip` with non-zero rms while user insists they're talking.
  Fix: threshold 30 (true silence ≈ 0–10, speech ≥ 50). Always eyeball the rms value in
  the skip log: if it's clearly non-zero, the user's voice IS arriving and the threshold
  is the bug, not the audio path.
- **NEVER click the Meet mic button to "enable" the mic** — the aria-label is the ACTION,
  not the state: when mic is ON the button reads `aria-label="Turn off microphone"` and
  clicking it DISABLES the mic (label flips to "Turn on microphone"). If a script earlier
  clicked it "to check", the mic is now OFF. Verify state by page text: mic ON ⇒ no
  "Your microphone is off" string; mic OFF ⇒ it's present. Re-enable by clicking the
  button whose aria-label contains "turn on microphone". This bit us mid-session: AI was
  replying into a muted mic, user heard nothing.
- **`pactl list source-outputs short` EMPTY for Chrome mic is NORMAL** — Chrome captures
  via ALSA (libasound → ~/.asoundrc pulse plugin), not as a PulseAudio source-output
  client, so an empty source-output list does NOT mean the mic is dead. The real route
  probe: play a tone on the AI sink, record the mic monitor:
  `ffmpeg -f lavfi -i "sine=frequency=880:duration=5" -y /tmp/beep5.wav` then
  `(paplay --device=alsa_output.ai_out /tmp/beep5.wav &)` + record
  `alsa_output.ai_out.monitor` → rms>1000 ⇒ AI→Meet path works. (A missing beep file
  makes paplay fail silently — always create/check the file first.)
- **Chrome silently drops to Meet HOMEPAGE** — after long idle or tab reloads the tab can
  end up on the Arabic join page (`مكالمات جماعية` / "Join with a code") while the agent
  keeps logging `Listening ... rms=0`. The AI is NOT in the call anymore. Always confirm
  in-call state from the page before declaring "AI is in the meeting": body text contains
  "Turn off microphone" / participant names / "has left the meeting" lines, and title is
  `Meet - CODE`. If on homepage: `goto_url(meet URL)` → name → join flow again
  (mic permission persists per-origin; re-grant with Browser.grantPermissions anyway).
- **WebAudio tone = fastest Chrome-output probe** — to prove Chrome's audio pipeline
  reaches the loopback monitor, synthesize in-page: `new AudioContext()` + oscillator at
  0.5 gain → record `platform-snd_aloop.0.analog-stereo.monitor` → rms≥1000 confirms
  Chrome→sink→monitor→record end-to-end. Zero-voice test that isolates the Chrome side
  from Meet's remote audio.
- **User reports \"only beep sound from Sanad\" → that beep is often YOUR test tone** —
  a `paplay --device=alsa_output.ai_out /tmp/beep5.wav` probe is AUDIBLE to meeting
  participants (it goes through Chrome mic into the call). If the user reports a beep
  shortly after you ran a tone probe, that confirms the AI→mic route is LIVE — the beep
  IS the proof, not a failure. Tell the user \"wo beep mera test tone tha — route kaam kar
  raha hai\". Don't re-run tone probes while the user is in the call without warning
  them first.
- **User drops a NEW meeting code mid-session → rejoin, don't assume same call** — when
  the user pastes a different `meet.google.com/CODE`, the AI must be re-joined: `goto_url`
  new code → `Browser.grantPermissions(audioCapture)` → name → join → lobby. The agent
  process does NOT need a restart for audio (same sinks/monitors), but DOES need a restart
  if you changed the greeting text. Detect \"user not actually in this call\" from page
  text: participant count shows only the AI (\"1\") and a line like
  `Aamir ... has left the meeting` — the user is in a different room; tell them to join
  THIS code (paste it back) before expecting replies.
- **AI speaks FIRST (startup greeting) — user preference** — the user wants the agent to
  greet proactively instead of only replying to speech (\"aap sanad se pehle bolne lagao
  woh baat karne do\"). Pattern: right after `tts_init()` in `main()`, synthesize and
  play a greeting (same TTS + `ai_out` path) BEFORE the listen loop starts:
  ```python
  greeting = ("Assalamu Alaikum wa Rahmatullah! Main Sanad AI hoon. "
              "Aap is meeting me kaise madad kar sakta hoon? Please bataiye.")
  log(f"Greeting: {greeting}")
  out = os.path.join(tempfile.mkdtemp(prefix="meet_"), "greeting.wav")
  tts_speak(tts, greeting, out)   # reuse the normal speak path
  log("Greeting spoken.")
  ```
  Watch for `Greeting spoken.` in the agent log to confirm. **Islamic greeting is the
  user's explicit persona choice** for Sanad (\"use islamic way sanad\") — keep
  Assalamu-Alaikum opening in meeting mode.
- **`python3 -u` + `grep -vE` pipe still buffers** — the watch-pattern notification fires
  (`Using reference` / `Greeting spoken` / `Heard:`) but `process log` stays empty until
  flush. Trust the watch notification + filesystem probes, not `log` output.

## ARM64 XTTS dependency fixes (aarch64 CPU, no GPU)

All verified; each resolves a distinct import/runtime error:

| Error | Fix |
|---|---|
| `torchaudio==2.11.0` binary mismatch with torch 2.13.0+cpu | Install a MATCHED pair: `pip install torch==2.11.0 torchaudio==2.11.0 --index-url https://download.pytorch.org/whl/cpu` |
| `weights_only=True` / unpickle error on model load | `export TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` (torch 2.6+ respects it) |
| `EOFError: EOF when reading a line` on first TTS init | License prompt needs `export COQUI_TOS_AGREED=1` |
| `BeamSearchScorer` removed from transformers | `pip install "transformers<4.50"` |
| torchaudio.load → torchcodec missing/import error on aarch64 | Patch `TTS/tts/models/xtts.py::load_audio` to fall back to soundfile (`sf.read(dtype="float32")` → torch tensor, mono mean, then `torchaudio.functional.resample`) |
| torchcodec pip wheel fails on aarch64 | Don't install it; use the soundfile patch instead |

Runtime env for everything: `source meetenv/bin/activate && export COQUI_TOS_AGREED=1 TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1`

Measured: model load 96s, synthesis 46s for ~9s speech (≈5x realtime) on 2-core ARM64.
First meeting reply takes 1.5–2.5 min (load + transcribe + think + speak) — tell the user
this upfront; it's "slow-live", not natural real-time.

## Meeting agent script

`/home/ubuntu/meetenv/meeting_agent.py` — complete pipeline (listen 5s window → silence
skip → whisper → DeepSeek Mozzaz → XTTS → play to ai_out sink). Modes:
`--listen-only` / `--speak "text"` / full (default). DeepSeek key auto-loads from
`~/.hermes/.env`. Launch pattern:
```bash
export DEEPSEEK_API_KEY=$(grep DEEPSEEK_API_KEY ~/.hermes/.env | cut -d= -f2)
python3 meeting_agent.py   # in meetenv, with the two TTS env vars set
```
