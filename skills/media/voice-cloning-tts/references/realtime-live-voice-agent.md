# Realtime ("live") voice agent — bidirectional streaming on our own infra

Verified 26-Sep-2026 by building **Sanad Live Claim Intake** at `~/ops/liveagent/` (`server.py` +
`index.html`), self-QA'd from a locally-launched headless Chrome through a cloudflared HTTPS tunnel.

## When this is the right architecture
A demo/post shows a *live* voice agent: caller speaks → agent answers in under a second, **watches the
camera**, fills a form/notebook live, calls tools mid-conversation, hands off to a human. That is one
**bidirectional streaming session**, NOT the turn-based STT → LLM → TTS loop in the parent skill
(that loop's CPU pipeline is ~5x realtime and cannot hold a conversation).

## Wire protocol (what actually worked)
- WS: `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key=$KEY`
- First frame MUST be `setup`:
```json
{"setup":{"model":"models/gemini-3.8-live",
  "generationConfig":{"responseModalities":["AUDIO"]},
  "systemInstruction":{"parts":[{"text":"<agent persona + rules>"}]},
  "tools":[{"functionDeclarations":[...]}],
  "inputAudioTranscription":{},"outputAudioTranscription":{}}}
```
- Input: mic = 16 kHz PCM16 mono; camera = base64 JPEG/WEBP via `realtimeInput.mediaChunks`; typed text =
  `clientContent.turns[]`. Output audio = **24 kHz** PCM16 mono.
- **PITFALL (cost ~an hour): tool calls do not always arrive nested in `serverContent`.** Here they came at
  the TOP level of the message. Read both:
  `tc = msg.get("toolCall") or (msg.get("serverContent") or {}).get("toolCall")` — same for
  `toolCallCancellation`. Reply at once with
  `{"toolResponse":{"functionResponses":[{"id":<id>,"name":...,"response":{...}}]}}` or the agent stalls.
- Turn boundary = `serverContent.turnComplete:true` (there is no separate "you may speak" flag).
- Keep `input/outputAudioTranscription` ON: it yields text for BOTH sides, which is what makes the harness
  assertable without any ASR step.
- Measured on this VM: setup complete ≈ **0.48 s**, first agent audio ≈ **0.70 s** → feels real-time.
- Dump raw output to `.pcm`, then `ffmpeg -f s16le -ar 24000 -ac 1 -i turn.pcm turn.wav` to review.

## Server bridge pattern
Browser ⇄ WS (JSON) ⇄ our asyncio server ⇄ Live API WS.
- browser→server: `{"type":"audio","pcm":b64_16k}`, `{"type":"video","jpeg":b64}`, `{"type":"text",...}`.
- server→browser: `agent_text`, `caller_text`, `tool`, `notebook` (full state after every tool),
  `turn_complete`, `audio` (b64 24k).
- Capture at 16 kHz (AudioContext + ScriptProcessor/AudioWorklet) → Int16 → base64. Play agent audio by
  scheduling `AudioBufferSourceNode`s back-to-back; do **not** `new Audio()` per chunk (clicks/gaps).
- The AudioContext stays suspended until a user gesture — a "Start call" button that resumes it is mandatory,
  otherwise the demo is silent with no error.
- Log BOTH directions with a flush-on-write `log(where, *a)`. A silent bridge failure is invisible: a closed
  live session just looks like a quiet caller.

## Tools + visuals that make the demo believable
`verify_policy`, `set_notebook_field`, `classify_claim`, `pin_frame` (evidence stays visible with its
caption), `draw_sketch` (server-side SVG pen path), `route_claim` (human-handoff stamp, e.g. `NEEDS DOCS`).
- **Avatar = orb, never a human face.** The source demo used a talking head; the house rule bans human faces
  in client-facing work. Render an orb and *state the difference honestly* instead of faking a face.

## QA without a phone
1. `python3 server.py --port 8100 --host 127.0.0.1`
2. Public HTTPS URL for the user's phone — **`getUserMedia` (mic/camera) refuses a plain-http non-localhost
   origin**, so tunnel it: `cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8100`, then grep the
   `https://*.trycloudflare.com` line out of its log.
3. Drive it headless (own CDP driver, e.g. `~/ops/liveagent/qa_drive.py` with nav/state/say/frame/shot/eval):
   `chrome --headless=new --no-sandbox --disable-gpu --enable-unsafe-swiftshader --remote-debugging-port=9223
   --remote-allow-origins=* --user-data-dir=/tmp/chrome-liveagent about:blank`, then `curl :9223/json/version`.
4. Expose page test hooks (`window.__sanad = {start, sendText, sendFrame}`) so `say "<line>"` / `frame <img>`
   can be injected and state read back — every UI claim then has a screenshot + JSON behind it.
5. Vision-QA the screenshot before showing the user: streaming delta text must **merge into the open line**
   per speaker (otherwise the panel fills with one-word lines); nothing hidden behind the control bar; no
   stray black boxes (an un-started `<video>` needs `display:none` until the camera starts).

## Pitfalls
- **Restarting the app server:** `pkill -f "server.py --port 8100"` matched its own invoking shell → exit
  `-15` (SIGTERM), killing the terminal command itself. Resolve the PID by port
  (`ss -ltnp | grep ':8100'`) and kill that PID.
- Long `write_file`/`patch` payloads get silently truncated on this VM — write in chunks and read back; a
  truncated patch leaves broken JS/CSS that only surfaces in the browser.
- An idle QA Chrome tab holds an open Live session and burns per-key daily quota — navigate it to
  `about:blank` when finished (keep exactly one session live).
- Cost: the prototype ran at **$0** (always-free VM + existing key). For a REAL phone call, bridge to the
  telephony lane instead — see `references/atoms-outbound-calling.md`.

## Independent QA of what came back (don't grade your own homework)
- Grade on the **server-side state JSON** (notebook fields, pinned-frame captions, the `route_claim` stamp)
  and then transcribe the returned 24 kHz audio with local whisper — the Live API transcript is a claim,
  the `.wav` on disk is evidence. A demo that "sounds right" can still have skipped every tool call.
- Exercise the vision path with a **synthetic** frame: generate a damaged-room image with `fluxgen`, crop any
  watermark band (`ffmpeg -vf "crop=iw:ih-80:0:80"`), push it through `sendFrame(b64)` — no customer footage
  needed and it keeps the demo face-free.
