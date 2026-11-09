---
name: system-one-decision-gate
description: Use for typed cheap decision gates (routing, triage).
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [routing, decisions, calibration, jev, typesafe, eval]
    related_skills: [tech-adoption-analysis, agentic-tooling-research, model-tier-selection]
---

# System One decision gate (Jev contract, our lanes)

Turn a bounded fork ("which skill / which agent / which tool / escalate to human?") into ONE
typed request that returns **labels + calibrated probabilities + confidence**, instead of
generating prose that code has to parse back into an `if`.

## When to use

- Agent skill/route selection, intent routing, queue triage, lead scoring, guardrail screens.
- Any place you currently prompt an LLM and regex/JSON-repair its answer.
- **Not** for math, counting, long-form writing, or irreversible execution (Jev's own docs
  say the same: "code computes, LLMs create, Jev decides, fresh state proves the result").

## The recipe (measured design, not a guess)

TypeSafe publish this design in `docs.typesafe.ai/cookbooks/skill_suggestion.md` after
benchmarking it on **our own Hermes roster** (182 skills, 488 requests): wrong-skill loads
16.8% → 7.3%, needless loads 9.8% → 4.0%, with the "agent handed the right answer" floor at
2.5%/1.2%. Two requests, two thresholds:

1. **Rank wide (1 request):** one `Choice` over the *whole* roster (label → short description),
   plus 3 `Noul`s about the *request*: `acts_on_user_system`,
   `would_follow_documented_procedure`, `prose_suffices` (inverted). Mean of the three
   **< 0.30 → suggest nothing**. Choice accepts up to **255 options** — a 209-skill roster fits.
2. **Read narrow (1 request):** `Choice` over the top 3 with ~700-char body excerpts +
   one `fits` `Noul` per candidate. `max(fits) < 0.30` → nothing.
3. **Inject one line**, never rewrite the roster (keeps prefix caching):
   `<skill_relevance>Relevant to the current request: <slug>. Ignore this if it does not fit
   what the user actually asked for.</skill_relevance>`

## Running it WITHOUT a TypeSafe key

`pip install 'system-one-adapter[openai]'` (MIT, `typesafe-ai/system-one-adapter-python`) is a
drop-in `TypeSafeClient` replacement backed by any OpenAI-compatible endpoint. Point it at our
lanes — no waitlist, no key:

```python
from system_one_adapter import SystemOneAdapterClient, Choice, Noul
from system_one_adapter.providers.openai import OpenAIProvider

cli = SystemOneAdapterClient(structured_outputs=False, llm_answer_mode="probabilities",
                             normalize_probabilities=True)
prov = OpenAIProvider("deepseek-flash", base_url="https://api.deepseek.com/v1", api_key=KEY)
r = cli.system_one(state="<user request>", questions={"which": Choice(
        instructions="Which skill should be loaded?", criteria={"slug": "desc", ...})},
    model=prov)
probs = r.answers["which"].probabilities      # ranking
conf  = r.answers["which"].confidence         # peak prob rescaled from uniform
```

Ready-made in this repo: `~/ops/decision/gate.py` (single-stage), `~/ops/decision/gate2stage.py`
(exact two-stage port incl. thresholds, shortlist, excerpts).

## Pitfalls (all hit here, 2026-09-19)

1. **DeepSeek thinking mode is ON by default** (effort=high) and destroys the economics:
   one 20-option Choice cost **~4.3k output tokens and 17 s**. Disable it —
   `extra_body={"thinking": {"type": "disabled"}}` (the adapter does not expose it; inject it
   into `provider._client.chat.completions.create`). Measured: 17.1 s → 1.9 s, $0.0027 →
   $0.0003 per decision — **but accuracy falls with it**, so measure both arms.
2. **The local free lane is not a synchronous gate.** Ollama `qwen2.5:3b` on this 2-core box:
   ~80 s for one typed Choice (cold load dominates). Async/batch lanes only.
3. **Use `structured_outputs=False`** for DeepSeek/Ollama; strict JSON-schema mode is the
   OpenAI/Responses path. DeepSeek json mode works; malformed output is retried by the adapter.
4. `system_one_adapter` exposes `probabilities`/`confidence`; read `usage` with **attribute**
   access (`usage.input_tokens_total`) — it is a pydantic model, not a dict.
5. Confidence and probability are different axes: choice confidence = peak probability rescaled
   from uniform (adapter `_utils/confidence_metrics.py`). Use **probability** for ranking,
   **confidence** to decide act-vs-escalate.
6. **Their benchmark package is now published** (since 2026-09-21): `cooksafe` 0.1.0 on PyPI
   ("Shared helpers for the TypeSafe cookbooks") + `pypi.typesafe.ai` wheels 0.1.0/0.1.1/0.1.2 —
   so the old "not independently reproducible" blocker is gone; replay it before trusting tables.
7. **Pricing is published nowhere** (`docs.typesafe.ai/pricing`, `/v1/pricing` → 404). Only hard
   cost numbers are token counts from the live response `usage`.

## With a real TypeSafe key (2026-09-21, measured on this box)

Key lives in vault space `infra` as `TYPESAFE_API_KEY`; inject, never echo:

```bash
vault exec infra -- python3 ~/ops/decision/eval_jev.py --workers 4      # real-Jev A/B, resumable
```

Native REST lane (no adapter shim, the adapter only emulates the contract with another model):

```python
POST https://api.typesafe.ai/v1/systemone   # Authorization: Bearer $TYPESAFE_API_KEY
{"state": "<context>", "model": "jev-latest",
 "questions": {"which": {"type": "choice", "instructions": "...", "criteria": {"opt": "desc"}},
               "q1":    {"type": "noul",  "instructions": "..."}}}
# -> {"answers": {"which": {"choice": "opt", "confidence": 0.97,
#                           "probabilities": {"opt": 0.98, ...}},
#                "q1": {"type": "noul", "noul": 0.87}}, "usage": {...}}
```

Response shapes verified: `Choice` → `probabilities` (+`confidence`), `Noul` → `noul`.
A 214-option Choice works fine (their documented ceiling is 255). Batching holds up for real:
13 Nouls in ONE call = **0.77 s** (469 in / 238 out tok, ~310 tok/s out).

**Measured verdict — real Jev vs our deepseek-flash lane, identical items and candidate sets:**

| | real Jev (jev-1.13.0) | deepseek-flash |
|---|---|---|
| one typed Choice over embedding top-20 (n=60) | 26.7% hit@1, **0.75 s** | 28.3% hit@1, 17.15 s |
| same, conditioned on gold ∈ shortlist (n=28) | 57.1% | 57.1% (identical) |
| cookbook two-stage over whole roster (22 pos/22 neg) | **81.8%** wrong / 72.7% needless | 68.2% wrong / 86.4% needless |
| output tokens, 60 decisions | **14,711** | 258,330 |

So: **no accuracy gain over a cheap LLM, a 22.8× latency win and 17.6× fewer output tokens** —
value is in narrow, latency-bound forks (cron/worker lanes, guardrails, queue triage), NOT in
whole-roster routing. The 16.8% → 7.3% claim did **not** reproduce on our traffic; our ceiling is
the retriever (gold in top-20 only 46.7% of the time), not the decision layer. Full detail:
`~/ops/kb/jev-real-key-headtohead-2026-09-21.md`.

## Real Jev on a real narrow-fork lane (2026-09-21, second measurement)

The stack already has a five-use-case typed-decision lane at `~/clients/invertio/jev`
(lead-qualify, queue-gate, reply-triage, tender-screen, guardrail, support-route) with
risk-tiered gates, a label/calibration store and a real-token runlog. It was built against
an **emulated** Jev (`backend=openai` -> DeepSeek). Flipping to `--backend typesafe` needs the
vault key and no code change; same 77 decisions, only the answerer differs
(`jev/scripts/ab_run.sh real|base`, deterministic scorer `jev/scripts/ab_score.py`).

- **Cheaper wire, not a better brain:** ~2.7x faster per decision (733-763 ms vs 1,928-2,404 ms)
  and ~2.0x fewer output tokens. (Two-stage batching is where the 22.8x came from, not per-item calls.)
- **Schema conformance is the real win:** 77/77 calls returned validator-clean *full* probability
  distributions; the DeepSeek proxy needed its lenient path on 77/77 (every row warned
  "partial probability distributions accepted").
- **Guardrail got WORSE, not better:** 4/10 vs 7/10 on the lane's own labelled fixture. Real Jev
  **never emits `allow`** — it over-flags all 4 benign items as `answer_only`/`ask_human` — and it
  under-escalated one attack (`g09` delete-table -> `block`, not `block_and_alert`). Attack recall
  4/5 vs 5/5. Do not put Jev in the security seat as-is.
- **reply-triage: 8/8 on gold, identical to baseline, 2.6x faster** — that one is a clean win.
- **Gates move when the answerer moves:** Jev's probabilities are sharper, so the *same* policy
  produced `act 7 / review 19` on lead-qualify where DeepSeek produced 0 `act`, and flipped the
  lead wave 8/8 (Jev `P1` vs DeepSeek `P2`). Thresholds fitted on one model are not valid for
  another — recalibrate before letting a gate `act`. `labels.py` keys on
  `(usecase,item_id,question)` with **no arm dimension**, so an A/B silently overwrites the other
  arm's labels; add a run tag first.
- Bug found by the same run: `cli.py` referenced `Decision.errors` (the dataclass carries
  `warnings`) -> `live-check` crashed *after* a successful real call, and `ask` would too.
  Fixed; `python3 -m jev.cli selftest` = 46 tests OK.

Full detail: `~/ops/kb/jev-narrow-fork-ab-2026-09-21.md`.

## Verification (do this, don't trust the gate)

```bash
cd ~/ops/decision && python3 build_evalset.py && python3 build_negatives.py   # real pairs from state.db
~/.hermes/tmp/soa/venv/bin/python eval_gate2.py      # wrong-skill + needless-skill rates
python3 verify_results.py                            # deterministic re-derivation, no LLM
```

Ground truth = the skill Hermes **actually loaded** in that turn (`skill_view` call in
`~/.hermes/state.db`), not a label invented by the eval. Report "agreement with the agent's own
choice", not "correctness". Full write-up: `~/ops/kb/jev-typesafe-audit-2026-09-19.md`.
