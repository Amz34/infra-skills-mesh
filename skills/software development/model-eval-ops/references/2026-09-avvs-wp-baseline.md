# 2026-09-09 — First baseline: DeepSeek v4-flash vs Gemini 3.7-flash

Reference for the FIRST built harness (still the live one). Reproduce from `~/ops/evals/` rather than re-inventing.

## Golden tasks (golden.json)

| task id | type | golden source | scorer |
|---|---|---|---|
| `wp-audit-json` | json | live wp-audit scan of avvs-wp sandbox (localhost:8080) — 5 real issues: 3 inactive plugins + 2 inactive themes | deterministic: per-item slug match (camelCase-split + hyphen variants), JSON validity |
| `client-summary` | summary | human audit summary of same scan | group-alias regex scoring + negation-aware fabrication detector |
| `ar-hero` | ar | AVVS-Triatek approved EN hero -> AR translation (CONTENT_EN.md / CONTENT_AR.md pairs) | must_include fixed AR strings via `ar_norm()` + LLM judge |
| `ar-pain` | ar | approved EN pain-point -> AR | same as ar-hero |

## golden.json task structure (verified by dump — no guessing)

```json
{
  "id": "...", "type": "json|summary|ar",
  "facts": { ... },                 // injected as RAW FACTS block in prompt
  "golden_items": [ {"human": "...", "group": "plugins"} ],
  "group_aliases": [ {"regex": "inactive plugins", "count": 3, "group": "plugins"} ],
  "must_include": ["..."]           // AR tasks only
}
```

## Harness anatomy (eval_baseline.py, ~12k chars, 15+ patches)

- stdlib only: json, re, os, sys, time, urllib.request, urllib.error.
- `call_model(env[key], model, sys_text, user, json_mode, max_tokens, temp)` — OpenAI-compatible JSON body; DeepSeek `deepseek-v4-flash` (reasoning), Gemini via `gemini-3.7-flash` alias.
- `retry_call(fn, tries=3, sleep_s=25)` -> `(txt, usage)` tuple (usage tracking must survive retries).
- Gen caps: `max_tokens=(16000 if type=="json" else 8000) if deepseek else (4500 if type!="summary" else 1600)`.
- Judge: both models judge, `temp=0.2, max_tokens=6000`, strict JSON output prompt; `retry_call(...)[0]` unpack.
- Per-task: `run_task` -> writes progress rows + raw outputs; final verdicts table -> stdout + report file.

## Observed results (partial run 2026-09-09)

- Gemini (before quota die): wp-audit JSON 5/5, summary 100%, no fabrication.
- DeepSeek: summary 40% (group-scored), JSON **truncated** at 8k cap -> fixed at 16k (probe confirmed valid JSON, finish=stop).
- Both models flagged the sandbox as HTTP/no-TLS — wp-audit.py itself did NOT have that check (tool gap candidate).
- DeepSeek summary also caught wp-audit's OWN fabricated detail once — useful cross-check property.

## Quota facts

- GOOGLE_API_KEY: single key shared by all 6 profiles (default, avvs, invertio, luxewave, ops, sanad, whatsapp) — verified hash-style without printing values. Exhausted 2026-09-09 ~22:00 UTC -> 429 -> full rerun postponed to cron 2026-09-10 08:00 UTC.
- Reset ~07:00 UTC (Pacific midnight). Persistent 429 = quota, not transient — don't burn retries.

## Probe-file pattern (shell-quoting safe)

Inline `python3 -c` with f-strings/newlines broke (`...n: command not found`). Fix used since:
write a small `.py` (e.g. `probe_ds16k.py`), run `python3 probe_ds16k.py`. Keeps quoting out of bash.

## Pitfall duplicates (also in SKILL.md — keep canonical list there)
- 420s terminal timeout vs 15-40s/call runs: background + pgrep/poll; verify with `ps -o pid,etime,cmd`.
- `| tail` masks exit code; use `> log 2>&1` + `echo exit=$?`.
