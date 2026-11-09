# Smallest AI — Cloud TTS/STT/Voice-Agent API (verified 2026-08-24)

API-first voice platform (Bengaluru, $21M funded): Lightning TTS, Pulse STT, Hydra
speech-to-speech, Electron LLM, plus hosted voice agents (phone/WhatsApp). One API key
works across models AND the voice-agent platform. Signup gives **$10 free credits**
(PAYG, no card required for the trial credit).

## Why use it (vs ElevenLabs / local XTTS)
- **$10 free credits + ~$0.01/min** — cheapest cloud voice path; fine for client-facing
  voice bots (Sanad voice-agent service line).
- Verified round-trip: TTS Hindi/Hinglish → wav (391KB, 8s, 24kHz), STT of that same
  audio → correct Devanagari transcription in 570ms (14x realtime).
- Also has an MCP server (`npx`) to control voice agents from an AI editor.

## Account / console
- Signup: `app.smallest.ai/login` → email → 6-char OTP → onboarding (name + "I want to
  build with APIs") → lands on API Keys page.
- **PITFALL: "Continue with Google" is the FIRST button on the login page.** Clicking it
  redirects to accounts.google.com. Use the email input + the *second* "Continue" button
  to get the OTP route.
- Console: `app.smallest.ai` — API Keys under **Developer → API Keys**
  (also at `/dashboard/api-keys`). Agents/Phone Numbers/Campaigns/WhatsApp under Create/Deploy.
- API key format: `sk_...`, **shown exactly once at creation** — copy it immediately and
  store in env (e.g. Hermes env file, 600 perms). Rotate/revoke from the console.

## Auth
`Authorization: Bearer $SMALLEST_API_KEY` on every request.

## TTS (verified working)
```bash
curl -X POST "https://api.smallest.ai/waves/v1/tts" \
  -H "Authorization: Bearer $SMALLEST_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: audio/wav" \
  -d '{"text": "Namaste! Main Sanad AI ki virtual assistant hoon.",
       "voice_id": "meher", "model": "lightning_v3.1_pro",
       "sample_rate": 24000, "output_format": "wav"}' \
  --output demo.wav
```
- Verified voice: `meher` (Hindi/Hinglish natural). Other voices via console Playground.
- Output: RIFF WAV, 16-bit PCM mono 24kHz.

## STT (verified working — TWO quirks)
```bash
ffmpeg -y -i demo.wav -codec:a libmp3lame -qscale:a 4 demo.mp3   # step 1: convert!
curl -X POST "https://api.smallest.ai/waves/v1/stt?model=pulse-pro" \
  -H "Authorization: Bearer $SMALLEST_API_KEY" \
  -F "file=@demo.mp3"
```
- **Quirk 1: `model` is a QUERY param, not a form field.** Missing/invalid →
  `{"status":"error","message":"Invalid model query parameter."}` with expected
  values `'pulse' | 'pulse-pro'`.
- **Quirk 2: raw WAV fails** (`AudioDecodeError: Failed to decode audio`) — convert to
  **mp3 first** (ffmpeg libmp3lame works; 48KB mp3 of 8s audio transcribed fine).
- Response: `{"status":"success","transcription":"...","language":"en","metadata":{...}}`.

## Endpoints that DON'T exist
- `GET /waves/v1/models` → 404 "Cannot GET" (console is the source of truth for voices).

## Telegram delivery of generated audio
`ffmpeg -y -i demo.wav -c:a libopus -b:a 32k demo.ogg` → send via `MEDIA:/path/demo.ogg`
= native voice bubble on Telegram (wav sends as playable file, ogg as voice message).

## Credential storage
`SMALLEST_API_KEY` in Hermes env file (~/.hermes/.env, 600 perms). Account:
aamir1zahran@gmail.com, org "Aamir1zahran's Organisation" (PAYG, $10 credit).
