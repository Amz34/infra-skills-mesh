---
name: voice-cloning-tts
description: Use when building AI voice assistants with cloned voices.
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [tts, voice-cloning, xtts, colab, whisper, deepseek]
    related_skills: [hermes-agent]
---

# Voice Cloning & TTS Assistant Pipelines

Build AI voice assistants that speak in the user's own voice: mic → STT → LLM reasoning → cloned-voice TTS. Covers option selection, XTTS-v2 usage, Colab notebook delivery, and mandatory ethics.

## When to use
- User wants AI to speak in their voice (voice cloning, meeting presence, voice notes, "AI ko meri awaz se bolwana")
- Interactive voice assistant: hear → think → speak in any language
- Choosing between cloud / local / Colab routes for TTS
- Real-time "live" voice agent (camera vision, live form-filling, tool calls mid-call) → use the realtime
  bidi section below, not the turn-based loop: `references/realtime-live-voice-agent.md`

## Decision table (validated 2026-08)
| Option | Cost | Quality | Latency | Privacy | Best for |
|---|---|---|---|---|---|
| ElevenLabs cloud | Free ~10 min/mo, $5/mo Starter | Best (70-85% natural) | <1s realtime | Voice on their server | Real-time meeting presence |
| Local XTTS-v2 (CPU VM) | $0 | Good | ~5x realtime measured on ARM64 2-core (46s for 9s audio) | Fully private | Pre-recorded content + SLOW-paced meeting replies |
| **Google Colab free T4 GPU** | $0 | Good | ~1 min clone | Via Google servers | Fast cloning, interactive test, zero install — recommended start |

## Pipeline architecture
1. **STT:** faster-whisper (90+ langs) — `WhisperModel("base", device=..., compute_type="float16" if cuda else "int8")`
2. **Reasoning:** DeepSeek API (or Hermes) with personality system prompt; answer in user's language, concise, speakable
3. **TTS:** XTTS-v2 — `tts_models/multilingual/multi-dataset/xtts_v2`; `tts.tts_to_file(text, speaker_wav="sample.wav", language=..., file_path=..., speed=...)`
4. Real-time meeting presence needs virtual audio. PROVEN recipe on headless Linux VM (no GPU, no sound card): **snd-aloop kernel module + PulseAudio + ~/.asoundrc + Chrome flags** — NOT pipewire. Full step-by-step in `references/meet-mode-headless-vm.md`.

## XTTS-v2 specifics
- 6-sec sample enough; 30-60 sec clean recording ideal (quiet room, phone ok)
- Languages: XTTS-v2 official = 17 (en/es/fr/de/it/pt/pl/tr/ru/nl/cs/ar/zh-CN/ja/hu/ko/hi). **Urdu NOT in the list** (verified via app dropdown 2026-08; older "Urdu ✅" claim was wrong) — best-effort via hi code + Roman script only; tell user honestly. Arabic ✅. **Kashmiri not officially supported** — best-effort via closest code (hi/ar); tell user honestly
- Model ~1.8 GB + torch ~2 GB; disk 4-5 GB total; RAM ~4-6 GB inference
- CPU-only (esp. ARM64 2-core): ~5x realtime measured — usable for slow meeting replies (1-2 min per response) and pre-recorded content, NOT natural real-time conversation
- ARM64 CPU install pitfall set (all verified 2026-08): see `references/meet-mode-headless-vm.md` — torch/torchaudio must be a matched pair (2.11.0+2.11.0 from `--index-url .../whl/cpu`; 2.13.0 has no torchaudio), `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` + `COQUI_TOS_AGREED=1` envs, `transformers<4.50` for BeamSearchScorer, and a soundfile fallback patch in `TTS/tts/models/xtts.py::load_audio` (torchaudio→torchcodec missing on aarch64)
- `pip install TTS==0.22.0` (pin version)

## Colab 1-click delivery workflow (proven)
1. **Build notebook programmatically** via Python builder script (json.dump of nbformat dict) — never hand-write notebook JSON
2. **PITFALL:** inside builder, cell source strings are triple-quoted — never put `"""` docstrings inside cells (they terminate the outer string). Use `#` comments in cell code; use `'''` for JS templates inside cells
3. GitHub: `gh repo create Amz34/<english-name> --public --source . --push` (repo names always English)
4. Colab link: `https://colab.research.google.com/github/USER/REPO/blob/main/NB.ipynb`
5. User steps: **Runtime → Change runtime type → T4 GPU**; DeepSeek key via left key icon → `userdata.get("DEEPSEEK_API_KEY")`
6. Colab mic recording: `google.colab.output.eval_js` + MediaRecorder → webm → `!ffmpeg -y -i mic.webm -ar 16000 -ac 1 mic.wav` (works headless/browser, needs hardware acceleration permission)
7. Notebook structure: install → load model → upload sample → clone test (EN/HI/UR/AR) → personality setup → text chat → mic voice chat → save/download

## Personality modes pattern (multi-persona, same voice)
One cloned voice, per-persona system prompt + speed tweak: `speed` 1.0 / 1.1 / 0.95. Example trio (user-specified): Kashish (charming/warm), Hasmukh (cheerful/humorous), Mozzaz (dignified/professional). System prompt: define tone + "answer in user's language, concise, speakable (max 3-4 sentences)".

## Meeting Mode (AI attends Google Meet with user's voice) — proven 2026-08
Full pipeline: Meet audio → `snd-aloop` monitor → Whisper STT → DeepSeek (Mozzaz) → XTTS (user's voice) → `ai_out` sink → Chrome mic → Meet.
1. **Virtual audio:** `sudo modprobe snd-aloop` (NOT pulseaudio null-sinks — Chrome enumerates ALSA only), PulseAudio restart, `module-alsa-sink device=hw:0,1 name=ai_out` for the AI→Meet path, set ALSA defaults
2. **User must be in `audio` group** or `chmod 666 /dev/snd/*` (group change needs re-login)
3. **Chrome launch flags:** `DISPLAY=:99 google-chrome --no-sandbox --disable-gpu --disable-audio-sandbox --autoplay-policy=no-user-gesture-required --remote-debugging-port=9242 --user-data-dir=...` — `--disable-audio-sandbox` is critical (ALSA blocked in sandbox otherwise)
4. **Mic permission via CDP:** `Browser.grantPermissions(permissions=['audioCapture','videoCapture'], origin='https://meet.google.com')` — no UI click needed
5. **Join flow:** name → "Ask to join" → host admits from their own device
6. **Meeting agent script** lives at `/home/ubuntu/meetenv/meeting_agent.py` (listen-only / speak / full modes) — reuse, don't rewrite. Launch with `python3 -u` (grep pipe buffers logs otherwise)
7. **PITFALL:** `pkill -f "google-chrome"` does NOT match `/opt/google/chrome/chrome` binaries — stale instances stack up and break device enumeration; use `pkill -9 -f "/opt/google/chrome"`
8. **PITFALL ("kuch nahi aya"):** `parec | ffmpeg` record pipe hangs forever → agent records but never replies. Record with direct `ffmpeg -f pulse -i <monitor> -t <sec>` + setsid/killpg timeout. Also verify boot log shows `Using reference voice` (wrong hardcoded ref path runs the agent without the clone). Full debug recipe in `references/meet-mode-headless-vm.md`
9. **LIVE-TEST CHECKLIST before telling user "say hello":** (a) page still in-call — body text has mic/participant strings, title `Meet - CODE` (Chrome silently drops to homepage on idle); (b) mic is ON — button reads "Turn off microphone" (that label is the ACTION: clicking it mutes!); (c) agent booted with `Using reference voice`; (d) chunk files ~160KB fresh. Each has cost real sessions. Detail in `references/meet-mode-headless-vm.md`.
10. **AI speaks FIRST — user preference** — user wants the agent to greet proactively, not just reply ("aap sanad se pehle bolne lagao"). After `tts_init()`, synthesize+play a startup greeting before the listen loop; confirm via `Greeting spoken.` log. **Sanad's persona greeting is ISLAMIC** ("Assalamu Alaikum wa Rahmatullah! Main Sanad AI hoon...") — user explicitly chose this ("use islamic way sanad"). Watch pattern `Greeting spoken`.
11. **New meeting code mid-session** — user pasting a different Meet code means REJOIN via browser (goto_url → grantPermissions → name → join). Agent audio needs no restart (same sinks); restart only if greeting text changed. User "not in this call" = participant count shows only AI + `has left the meeting` line — paste the code back so they join THIS room.
12. **User says "sirf beep sound" → that beep is likely YOUR OWN tone probe** — `paplay` on `ai_out` is audible through Chrome mic to all participants; it proves the AI→Meet route is live, not a failure. Don't re-probe while user is in-call without warning.
13. **PITFALL ("beep output" root cause): VERIFY the reference voice is actual speech before cloning** — a Telegram voice note can land as a pure tone (user's `audio_86942c460450.ogg` → `/tmp/ref.wav` was 62s of tone: zcps≈1971, rms≈4219, no silence gaps). XTTS clones the reference faithfully, so a tone reference ⇒ every synthesized reply is a beep. Check: convert to 16k mono, compute zero-crossing rate + RMS + pitch (autocorrelation) per segment — real speech has silence gaps, varying segment RMS, and a pitch histogram clustered at the speaker's fundamental (male ~120-240Hz); a tone has flat zcps (~2× its frequency, e.g. 1760 for 880Hz), uniform RMS, one dominant pitch. **zcps ALONE is not decisive** — clean speech with sibilants/noise measured zcps≈1592 this session and was correctly verified as speech by pitch clustering at 180-240Hz. If reference is a tone: re-capture, don't debug the TTS/model.
14. **BEST FIX for tone reference: capture the user's voice LIVE from the meeting** instead of asking for another Telegram note (Telegram delivery is what corrupts). Record 5s windows from the Chrome speaker sink monitor (`alsa_output.platform-snd_aloop.0.analog-stereo.monitor` — the same sink the agent listens on), keep chunks with rms > 60, collect ~8 chunks (~40s), concat to 22.05kHz mono. Works end-to-end: 6 chunks / 32s captured with pitch-verified speech. Ready-to-run: `scripts/capture_voice.py`; run it, tell user to talk 40-60s, then `meeting_agent.py --ref /tmp/ref_voice.wav`. Reference path is a CLI arg (`--ref`) — never rely on the hardcoded default.
15. **PITFALL: silence threshold too high silences real users** — agent's rms threshold was 200; the user's speech arrived at rms≈120-174 and got skipped as "silent". Speech rms is typically 500-4000, real silence <10; a threshold of 30-60 is safe. Symptom: agent logs endless `silent (rms=NNN) — skip` with NNN well above 10 while the user insists they're talking.
16. **PITFALL: don't click Meet mic button to "check" it** — the label is the ACTION: "Turn off microphone" means the mic is ON (clicking mutes it). Toggling during a session silently breaks the AI's voice for everyone until re-enabled. Verify state by reading the label; only click when you intend to change it.

## Local Voice Agent (gradio app, zero API) — proven 2026-08
Extend the voice-cloner gradio app with a 2nd tab: voice note → faster-whisper STT → local LLM → XTTS reply in the cloned voice. Client-demo ready (lead-qualifier: name → need → phone → "team will call back").
- **LLM: Ollama, fully local** — `curl -fsSL https://ollama.com/install.sh | sh` (works on ARM64; "No NVIDIA/AMD GPU detected, CPU-only" warning is normal) → `ollama pull qwen2.5:3b` (~2GB Q4) → chat via `requests.post("http://127.0.0.1:11434/api/chat", json={"model":"qwen2.5:3b","stream":False,"options":{"num_ctx":2048,"temperature":0.4},"messages":[...]})`. ~3-5s CPU reply. RAM headroom: server 3GB + ollama ~2GB + XTTS gen transient ~3GB ≈ tight-but-OK on an 11GB box; drop to qwen2.5:1.5b if the OOM killer bites.
- **Shared voice state:** module-global `CURRENT_LATENTS`; `clone()` sets it; agent tab falls back to a default reference wav (`aamir_voice.wav`) if unset. Pre-compute latents in a **daemon thread started BEFORE `demo.launch()`** → agent has a voice ready ~1 min after boot without blocking startup (log marker `[agent] default voice ready`).
- **TTS language auto-detect from reply text:** Devanagari → `hi`; Arabic script → `ar`; else `en` (Roman/Hinglish reads fine as English).
- **Demo speed:** force LLM to max 2 sentences + `speed=1.05` → ~30-90s CPU generation per turn. Call `model.inference(...)` directly (skip the eval step — similarity+whisper on output costs 20-40s/turn for no demo value).
- **System prompt:** "REPLY IN THE SAME LANGUAGE the user speaks, short + speakable (max 2 sentences)" + the lead-qualifier flow.

PITFALLS (each cost real test cycles):
- **gradio 5 Chatbot accepts dict format ONLY.** `gr.Chatbot` default `type="messages"` validates the OUTPUT in postprocess: returning legacy `[[user, bot]]` pairs raises `AppError: Data incompatible with messages format. Each message should be a dictionary with 'role' and 'content'...` — the fn already ran (STT/LLM/TTS done!) but the response dies at serialization, and the error LOOKS like input validation. Return `[{"role":"user","content":...},{"role":"assistant","content":...}]`. Input `None`/`[]` preprocesses fine; only the output shape fails.
- **gradio_client session state:** endpoints whose fn consumes gr.State (e.g. /generate's latents) need the state populated first: /validate → /clone → /generate in the SAME Client instance (state persists across predict calls). Cold /generate → "Pehle voice validate + clone karo".
- **Don't guess file paths from truncated logs:** gradio_client result paths print truncated (`/tmp/gradio/<hash>/tmp…`); `ls` the actual dir for the real filename before `handle_file()` — guessing costs a full re-run.
- **E2E loop test:** /generate a question in the cloned voice → `handle_file()` it back as the agent input → verify STT heard it, LLM replied, audio returned. Full detail in `references/local-voice-agent-gradio.md`.

## Realtime Live Voice Agent (bidirectional streaming) — proven 2026-09
For "live voice agent" demos (caller talks → agent answers in <1s, watches the camera, fills a form live,
calls tools mid-conversation, hands off to a human) use a **single bidirectional streaming session**, NOT the
turn-based STT→LLM→TTS loop above (that CPU pipeline is ~5x realtime and cannot hold a conversation).
Built + self-QA'd on this VM at `~/ops/liveagent/` (`server.py` + `index.html`, `gemini-3.8-live` Live API):
measured setup 0.48s / first audio 0.70s, 6 live tool calls, camera frame described in speech, notebook
filled live, route stamp — verified from a headless Chrome over a cloudflared HTTPS tunnel.
- Wire + bridge + QA recipe: **`references/realtime-live-voice-agent.md`** — endpoint + setup frame, the
  `toolCall`-arrives-at-TOP-LEVEL pitfall, 16 kHz in / 24 kHz out PCM, AudioWorklet capture + back-to-back
  buffer scheduling, `window.__…` page test hooks, CDP headless driver, HTTPS-tunnel requirement for mic/camera.
- **Avatar = orb, never a human face** (house rule for client-facing work) — disclose that difference from the
  source demo instead of faking a face.

## Voice sample script authoring
- Provide script in native script (e.g. Perso-Arabic Kashmiri) **plus Roman transliteration side by side** — user reads whichever is easier
- Sections: numbers 1-10, intro, a question, emotional/thank-you (~45-60 sec total)
- Tell user: dialect differences don't matter — voice is cloned, not the words; read naturally with pauses

## Ethics (MANDATORY — state explicitly every time)
- Clone only the user's OWN voice for their own content/meetings
- Disclose AI voice in client/professional calls (best practice)
- Never clone anyone else's voice — illegal + unethical
- Privacy honesty: local = fully private; Colab/cloud = voice passes through their servers

## Output style (this user)
- Hinglish, concise, decision tables, honest limitations FIRST (speed, language gaps, privacy)
- Recommend one option; ask before big installs (disk/RAM check first: `df -h /`, `free -h`)
- Offer Colab link + next action (voice note upload) explicitly

## Support files
- `references/colab-voice-notebook.md` — notebook builder pattern, JS mic snippet, DeepSeek call, personality dict
- `references/local-voice-agent-gradio.md` — zero-API voice agent as a gradio 2nd tab: agent_turn fn shape, Ollama wiring, pre-clone thread, dict-format fix, E2E test recipe
- `references/realtime-live-voice-agent.md` — realtime bidirectional voice agent (Gemini Live API): wire protocol, server bridge, orb-avatar rule, headless-Chrome + HTTPS-tunnel QA recipe, restart pitfalls
- `references/meet-mode-headless-vm.md` — FULL headless-VM audio setup (snd-aloop, PulseAudio, Chrome flags, CDP grant, join flow) + ARM64 XTTS dependency fixes, error-by-error
- `scripts/capture_voice.py` — capture user's voice LIVE from the Meet audio path to build a clean XTTS reference (bypasses corrupted Telegram voice notes); verify with rms-variation + pitch clustering, then `meeting_agent.py --ref /tmp/ref_voice.wav`
