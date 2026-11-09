# Smallest AI Atoms — Voice Agents & Telephony (verified 2026-08-24)

Atoms = Smallest's agent platform with **built-in phone calling — no Twilio needed**.
Same `SMALLEST_API_KEY` unlocks it. One API runs the full conversational loop:
**Pulse** (STT) → **Electron** (conversational small LLM) → **Lightning** (TTS).

Use case in play: Sanad receptionist/IVR service line (~$0.08/min voice agents).

## Agent CRUD (REST, verified live)
```bash
# List agents
curl -sS -H "Authorization: Bearer $SMALLEST_API_KEY" \
  "https://api.smallest.ai/atoms/v1/agent"
# → {"status":true,"data":{"agents":[...],"totalCount":N}}   (0 agents = fresh key/org)

# Create agent — minimal payload works, returns agent_id directly
curl -sS -X POST "https://api.smallest.ai/atoms/v1/agent" \
  -H "Authorization: Bearer $SMALLEST_API_KEY" -H "Content-Type: application/json" \
  -d '{"name":"Sanad Receptionist Test"}'
# → {"status":true,"data":"6a8c70cbc06de79ef0e79f5e"}   (24-char hex id)
```
New agents start as `single_prompt` workflow, default voice/language. Prompt & voice are
set later via version/update endpoints or the Atoms dashboard (atoms.smallest.ai).
First test agent on this org: "Sanad Receptionist Test" id `6a8c70cbc06de79ef0e79f5e`.

## Outbound call
```python
# Python SDK: pip install smallest-ai
client.atoms.calls.start_outbound_call(agent_id="...", phone_number="+9665XXXXXXXX")
```
- Number must be E.164 (country code, no +0 or spaces).
- **Wait 5-10s between calls** (rate limit).
- Caller ID: rent a number from Smallest inventory (~$10/number/month) or import an
  existing one via SIP (Twilio/Telnyx/Vonage).

## Pricing (2026-08)
- Atoms voice agent: ~$0.08/min entry ($0.09-0.21 depending on model stack), 2-3x
  cheaper at volume; free tier to start building.
- TTS Lightning V3.1 Pro ~$0.195/10K chars; Pulse realtime STT ~$0.004/min.
- No public balance endpoint (`/balance`, `/account` → empty/404); check credits at
  `app.smallest.ai` console.

## Related TTS pitfall (hit live same session)
`POST /waves/v1/tts` param MUST be `voice_id` — the old name `voice` returns HTTP 400
`{"error":[{"code":"invalid_type","path":["voice_id"],"message":"Required"}]}` and the
error body comes back as JSON where audio was expected. Check the param name first on
any 400. (Full TTS/STT quirks in `references/smallest-ai-api.md`.)
