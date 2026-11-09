# Smallest AI Atoms — Voice Agents & Telephony Calling (verified 2026-08-24)

Atoms = Smallest's agent platform with **built-in phone calling — no Twilio needed**.
Same `SMALLEST_API_KEY` unlocks it. One API runs the full conversational loop:
**Pulse** (STT) → **Electron** (conversational small LLM) → **Lightning** (TTS).

Use case in play: Sanad receptionist/IVR service line (~$0.08/min voice agents).
**Sanad receptionist voice = MALE `blake`** (user correction 2026-08-24: "Make it male voice").

## Python SDK — package name is `smallestai`
```bash
pip install smallestai          # NOT smallest-ai, NOT smallest (those silently fail/404)
```
Client: `from smallestai import SmallestAI; c = SmallestAI()` (reads `SMALLEST_API_KEY` env).
Surface: `c.atoms.agents`, `c.atoms.agent_versioning_branches` (+ `_drafts`/`_revisions`/`_versions`),
`c.atoms.calls`, `c.atoms.phone_numbers`, `c.atoms.billing`.

## Agent CRUD (REST, verified live)
```bash
curl -sS -H "Authorization: Bearer $SMALLEST_API_KEY" "https://api.smallest.ai/atoms/v1/agent"   # list
curl -sS -X POST "https://api.smallest.ai/atoms/v1/agent" \
  -H "Authorization: Bearer $SMALLEST_API_KEY" -H "Content-Type: application/json" \
  -d '{"name":"Sanad Receptionist Test"}'          # → {"status":true,"data":"<24-hex agent_id>"}
```
First test agent on this org: "Sanad Receptionist Test" id `6a8c70cbc06de79ef0e79f5e`,
main branch id `6a8c70cbc06de79ef0e79f72`.

## ⚠️ Versioning is the v2 BRANCH model — old drafts API is dead
`POST /atoms/v1/agent/{id}/drafts` → **404** (SDK docs: "Deprecated on the v2 branch model.
Migrate to `PUT /agent/{id}/branches/{branchId}/draft`"). Use `agent_versioning_branches`.

## PROVEN live flow: configure prompt/voice → fire real outbound call
```python
from smallestai import SmallestAI
AGENT, BRANCH, TO = "6a8c70cbc06de79ef0e79f5e", "6a8c70cbc06de79ef0e79f72", "+966574268856"
c = SmallestAI()

# 1) branches.list → find the default branch (is_default=True, name 'main')
branches = c.atoms.agent_versioning_branches.list(id=AGENT)   # branch.id from BranchSummary.branch

# 2) update_draft = UPSERT of the open draft (auto-creates one if none open).
#    Body is an agent-config partial in the same camelCase shape as GET /agent/{id}.
c.atoms.agent_versioning_branches.update_draft(
    id=AGENT, branch_id=BRANCH,
    global_prompt="You are the receptionist for Sanad... "
                  "Speak your opening message word for word, then close: 'Thank you for calling Sanad. Goodbye!' "
                  "After that remain silent and wait for the call to end.",
    first_message="Hello! You've reached Sanad, your AI receptionist... How can I help you today?",
    slm_model="electron",                       # fastest; default gpt-4.1
    synthesizer={"voice_config": {"model": "waves_lightning_v3_1_pro",
                                  "voice_id": "blake", "gender": "male"},   # blake=male default; meher=female (verified)
                 "speed": 1.0, "sample_rate": 24000},
    mute_user_until_first_bot_response=True,    # intro plays uninterrupted on pickup
    wait_for_user_to_speak_first=False,
    allow_interruptions=False,
    llm_idle_timeout_config={"telephony_timeout_time_in_secs": 8},  # silence → auto-end short test call
)
# → Revision(status='draft', draft_id=...)

# 3) test_call with the DRAFT (include_draft=True) — real outbound ring
call = c.atoms.agent_versioning_branches.test_call(
    id=AGENT, branch_id=BRANCH, include_draft=True,
    mode="telephony", to_phone=TO,
)
# → TestCallResult(conversation_id='...', call_id='CALL-1787589560726-05dab7')
```
- To change ONLY the voice (user: "make it male voice"): re-run `update_draft` with a new
  `synthesizer` dict, then `test_call` again — new draft revision, new call.
- `end_call` TOOL is NOT available in the v2 single_prompt config (no `tools` key in
  `GET /agent/{id}`; tools live in the workflow graph). Short calls = idle-timeout trick above.
- New-agent defaults (read from `GET /agent/{id}`): slm `gpt-4.1`, transcriber `pulse`,
  workflow `single_prompt`, session timeout 900s, telephony idle timeout 20s, voice blake male.
- `slm_model` options: electron, electron-kogta, electron-kogta-v2, gpt-4o, gpt-4.1, gpt-5.2,
  gpt-realtime, gpt-realtime-mini.

## Other calling route (documented, not live-verified this session)
```python
c.atoms.calls.start_outbound_call(agent_id="...", phone_number="+9665XXXXXXXX", test_call=...)
```
- Number must be E.164 (country code, no +0 or spaces).
- Wait 5-10s between calls (rate limit).
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

## Supersedes
This file carries the corrected, live-verified calling workflow. The older
`references/smallest-ai-atoms.md` in this skill still says `pip install smallest-ai`
(wrong) and lacks the v2 branch model — prefer THIS file for anything calling-related.
