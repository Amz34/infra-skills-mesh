# DeepSeek reasoning-model token pitfall (empty LLM responses)

## Symptom
`call_deepseek()` returns `""` (empty string) with NO exception. Script writes the output file anyway → 0-byte file. Exit code still 0 (until guard added).

## Root cause
`deepseek-v4-flash` is a **reasoning model**. It emits hidden `reasoning_content` BEFORE visible `content`, and reasoning tokens count against `max_tokens`. When the prompt is complex (long JD + constraints), reasoning eats the entire budget:

```json
{"choices": [{"message": {"content": "", "reasoning_content": "..."},
              "finish_reason": "length"}],
 "usage": {"completion_tokens": 600,
           "completion_tokens_details": {"reasoning_tokens": 600}}}
```

`finish_reason: "length"` + `reasoning_tokens == max_tokens` + empty `content` = the signature. Simple prompts work fine (short reasoning); complex ones don't — non-deterministic, so it can pass once then fail.

## Diagnosis recipe (repro)
1. Sanity check: call API directly with a trivial prompt ("Reply with exactly: TEST_OK") → works, `content` non-empty, reasoning short.
2. Reproduce: call with the real system prompt + JD → `content` len 0, `finish_reason: length`, `completion_tokens_details.reasoning_tokens == max_tokens`.
3. Conclusion: token budget, not auth/network/model outage.

## Fix (applied to ~/.hermes/scripts/cover_letter.py, 2026-08-26)
- `max_tokens=600` → `max_tokens=2500` for prose generation.
- Guard: `if not letter: print('ERROR: empty LLM response...'); sys.exit(1)` — never write an empty output file silently.
- Rule of thumb: reasoning models need max_tokens ≈ desired content tokens × 4–6 (reasoning can be 3–5× the visible output).

## Scope
Applies to ANY OpenAI-compatible API where the model has a hidden reasoning pass (deepseek v4-flash/reasoner, o1-style, etc.) — check `completion_tokens_details` when a "working" call returns empty.
