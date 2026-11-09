# Local Voice Agent as a gradio 2nd tab (zero API) — session detail 2026-08-31

Proven on the `/home/ubuntu/voiceclone` app (XTTS-v2 + faster-whisper base int8, ARM64 2-core, 11GB RAM, served via trycloudflare tunnel). Goal: client-demo voice agent — user sends a voice note, bot replies with text + audio in the CLONED voice, everything local (no API key).

## Architecture
```
voice note (mic/upload)
  → studio.to_wav16() → studio.transcribe()  [faster-whisper base int8]
  → Ollama qwen2.5:3b (127.0.0.1:11434)      [local LLM, ~3-5s CPU]
  → language auto-detect on reply text
  → XTTS inference() with CURRENT_LATENTS     [cloned voice]
  → wav out + transcript history (dict format)
```

## Key code shapes
- **Global voice state** (module level, shared across tabs):
  ```python
  CURRENT_LATENTS = None            # set by clone(), read by agent
  DEFAULT_REF = "/home/ubuntu/voiceclone/aamir_voice.wav"
  ```
- **Pre-clone thread** — starts before `demo.launch()` so the agent has a voice ~1 min after boot, without blocking startup:
  ```python
  def _preclone():
      global CURRENT_LATENTS
      if CURRENT_LATENTS is None:
          CURRENT_LATENTS = studio.speaker_emb(DEFAULT_REF)
          print("[agent] default voice ready", flush=True)
  threading.Thread(target=_preclone, daemon=True).start()
  ```
- **Ollama call**:
  ```python
  requests.post("http://127.0.0.1:11434/api/chat",
      json={"model": "qwen2.5:3b", "stream": False,
            "options": {"num_ctx": 2048, "temperature": 0.4},
            "messages": [{"role": "system", "content": sys_prompt}] + msgs},
      timeout=240)["message"]["content"]
  ```
- **TTS lang detection**:
  ```python
  def detect_tts_lang(text):
      if any('\u0900' <= ch <= '\u097F' for ch in text): return "hi"
      if any('\u0600' <= ch <= '\u06FF' for ch in text): return "ar"
      return "en"   # Roman/Hinglish reads fine as English
  ```
- **Fast generation, no eval** (skip similarity/whisper on output — saves 20-40s/turn):
  ```python
  model = studio.tts.synthesizer.tts_model
  result = model.inference(text=reply, language=tts_lang,
      gpt_cond_latent=gpt_cond, speaker_embedding=spk_emb,
      speed=1.05, enable_text_splitting=True,
      temperature=0.6, top_k=30, top_p=0.8, repetition_penalty=2.0)
  # result["wav"] (tensor) → numpy → soundfile.write(tmpfile)
  ```
- **Default agent system prompt** (client demo / lead-qualifier):
  "REPLY IN THE SAME LANGUAGE the user speaks. Keep answers SHORT and speakable: maximum 2 sentences. Greet, ask the caller's name and need, collect a phone number, then say the team will call back soon."

## PITFALL: gradio 5 Chatbot output format (3 test cycles lost)
`gr.Chatbot` defaults to `type="messages"` in gradio 5. The fn's return value is validated in **postprocess** — returning legacy pairs `[[user_text, reply]]` raises:
```
AppError: Data incompatible with messages format. Each message should be a
dictionary with 'role' and 'content' keys or a ChatMessage object.
```
The function had ALREADY completed (STT + LLM + TTS all ran — visible in the server journal: chatbot.py `_check_format` in postprocess) but the response died at serialization. Fix — return dicts:
```python
return history + [
    {"role": "user", "content": user_text},
    {"role": "assistant", "content": reply},
], out_wav, status
```
Input side accepts `None`/`[]` fine — only the OUTPUT shape fails. When this error appears, check the SERVER journal first (journalctl --user -u <svc>) — the traceback shows postprocess vs preprocess immediately.

## PITFALL: gradio_client session state
Endpoints whose fn consumes a `gr.State` (e.g. /generate's latents) return "Pehle voice validate + clone karo" when called cold, because the state is per-session. Run the flow in ONE Client instance (state persists across predict calls):
```python
v  = c.predict(handle_file(wav), api_name="/validate")
cl = c.predict(v[1], api_name="/clone")
g  = c.predict("Question text?", "en", 1.0, api_name="/generate")   # now works
```

## PITFALL: truncated paths in gradio_client output
Result paths print truncated (`/tmp/gradio/<hash>/tmp`) — never guess the tail filename for `handle_file()`; `ls` the hash dir for the real `.wav`.

## E2E loop test (through the tunnel)
1. `/generate` a question in the cloned voice (e.g. "Hello, what services does your company offer?") → get wav path.
2. Feed it back: `c.predict(handle_file(q), None, "", api_name="/agent_turn")` — pass `""` (empty) sys prompt so the default kicks in.
3. Assert: transcript contains the heard question, status contains the reply, audio path returned, total turn < ~3 min.

## Memory profile (11GB box)
At rest: server ~3.0GB + ollama ~2GB + others ~2.7GB → ~3.9GB free. XTTS generation transient +2-3GB → tight but OK. If OOM killer bites during agent turns, switch `qwen2.5:3b` → `qwen2.5:1.5b`.
