---
name: typesafe-decisions
description: Use when a task needs typed, calibrated decisions.
version: 1.0.0
author: Aamir Zameer (Hermes Agent)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [typesafe, jev, routing, classification, confidence, cost-optimization]
    related_skills: [system-one-decision-gate, model-tier-selection, billable-api-integration]
---

# TypeSafe / Jev — typed, calibrated decisions

Covers TypeSafe System One (the "Jev" decision model): schema-first questions answered with
numbers and labels plus calibrated confidence, instead of generated text you then have to parse.

## When to Use

- A pipeline needs **one snap judgment per question** (is this about billing? how urgent? does this
  lead match the ICP?) rather than free-form prose that must then be parsed.
- You are gating on a **probability**: route to a human, escalate a model tier, or auto-answer only
  when `confidence` clears a threshold (thresholds scale with the cost of being wrong).
- A prompt currently asks a chat model N separate questions — batching them into **one** TypeSafe
  call is the cost/latency win (upstream cookbook measures 11.5x cheaper, 9.6x faster over a
  13-question pass with unchanged answers).
- You need **stable** answers run-to-run where an LLM's sampled text varies (self-consistency
  cookbook: LLM answers vary run to run; Jev returns stable noul probabilities).

Not for: drafting copy, summarising, extracting long spans, tool-calling loops, or anything where
you want text back. Jev returns **numbers and labels**, never prose.

## Verified facts (2026-09-21, live call from this VM)

| Fact | Value |
|---|---|
| Endpoint | `POST https://api.typesafe.ai/v1/systemone` |
| Auth | header `Authorization: Bearer <key>` |
| Model id | request `"model": "jev-latest"`; response reports `jev-1.13.0` |
| Latency, 3-question call | **0.76 s** |
| Usage from that call | `input_tokens 369`, `output_tokens 75` |
| Console | `https://console.typesafe.ai` (workspace: Aamir Zahran / Az Consultants) |
| Errors | `401` bad key · `422` body validation (offending field in body) · `429`/`529` retry with exponential backoff (SDKs do it automatically) |
| Choice limit | max 255 options per Choice |

## Credentials (never print, never commit)

- Key lives at `~/ops/typesafe/api_key.txt` (mode `0600`, prefix `apikey`, 108 chars) and in
  `vault` under `typesafe/TYPESAFE_API_KEY`.
- Read it at use time: `K=$(cat ~/ops/typesafe/api_key.txt)` — do **not** paste the value into a
  command that gets logged, and never into a client deliverable.
- SDK/CLI consumers read `TYPESAFE_API_KEY` from the environment.
- Console sign-in is **email-code** (no Google OAuth needed): `/login` → email → "Email me a code
  instead" → 6-digit code arrives in the mailbox → `himalaya` reads it → Verify. See the
  `headless-browser-automation` skill for the CDP recipe used.

## Wire format (raw REST — this is what differs from the SDK docs)

The Python SDK example shows class-based questions (`Noul(...)`, `Choice(...)`, `Score(...)`) and
reads `response.nouls["x"].noul`. On the **raw endpoint** every question needs an explicit
`"type"`, and everything comes back under a single `answers` map:

```bash
curl -s -X POST https://api.typesafe.ai/v1/systemone \
  -H "Authorization: Bearer $(cat ~/ops/typesafe/api_key.txt)" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "jev-latest",
    "state": {"document": "<the text/message/record to judge>"},
    "questions": {
      "billing":  {"type": "noul",   "instructions": "Is this ticket about billing?"},
      "tone":     {"type": "choice", "instructions": "What is the tone?",
                   "criteria": {"calm": null, "frustrated": null, "angry": null}},
      "urgency":  {"type": "score",  "instructions": "How urgent is this?",
                   "criteria": ["can wait", "this week", "today"]}
    }
  }'
```

Response shape (real, trimmed):

```json
{"model":"jev-1.13.0",
 "answers":{
   "billing":{"type":"noul","noul":0.98},
   "tone":{"type":"choice","choice":"frustrated","confidence":0.87,
           "probabilities":{"calm":0.06,"frustrated":0.92,"angry":0.02}},
   "urgency":{"type":"score","score":2.0,"confidence":1.0,
              "legend":{"0":"can wait","1":"this week","2":"today"},
              "probabilities":{"0":0.0,"1":0.0,"2":1.0}}},
 "usage":{"input_tokens":369,"output_tokens":75}}
```

- `state` is free-form JSON — feed the raw record; don't pre-summarise it (the whole point is the
  judgment happens on the source).
- `criteria` is an **object** for `choice` (option → rubric description, `null` for no extra
  detail) and an **array** for `score` (ordered, becomes `legend`).

## Choosing a primitive

| Primitive | Ask | Returns | Use for |
|---|---|---|---|
| **Noul** | yes/no proposition ("Is X about Y?") | `noul` probability 0–1 | gates, inclusion filters, binary flags |
| **Choice** | one label from a closed set | `choice` + per-option probabilities | classification, routing, intent |
| **Score** | position on an ordered scale | `score` + `legend` + probabilities | urgency, fit, quality tiers |

Rules that hold up in practice:
- **One snap judgment per question.** Splitting a complex judgment into several questions beats one
  fuzzy question; each answer carries its own confidence.
- Prefer `noul` for a decision you will threshold, `choice` when you need the label itself.
- Ask speculative questions freely — they cost the same and the probability is the output.

## Using confidence (the part that makes it worth money)

- Confidence is derived from the probabilities, not hand-waved. **"I don't know" is a signal, not
  a failure** — a low-confidence answer is the system telling you to route elsewhere.
- Three paths: (1) **act** above threshold, (2) **escalate** to a bigger/reasoning model or a human
  in the uncertain band, (3) **refuse/ask** below the floor.
- **Thresholds scale with the cost of being wrong.** Money or safety → high threshold (0.95+);
  a tag on a dashboard → 0.7 is fine.
- Escalation pattern that pays for itself: Jev answers every item cheaply, only the uncertain band
  goes to a premium model. Most volume never reaches the expensive tier.

## Grounded verdict loops (measured on this VM)

Jev judges best when a script has already proven what is provable. Pattern measured on this VM
(`~/ops/typesafe/qa/` — 13 probes against a live storefront, 36 calls, 80 s wall clock):

1. **CHOICE** call — which executable probe runs next, given the current observation.
2. **VERDICT** call — every requirement judged in the *same* call (9 questions, one call).
3. **AUDIT** call — only when violations were claimed: Jev must point at the evidence proving each
   claim; unproven claims are downgraded to `not_observable`.

Grounding contract that made it work:

- Compute deterministic checks in Python and pass them in `state` as `check_*` booleans, named so
  **TRUE always means the requirement is MET**. Any other polarity and the model reads the check
  backwards — that bug produced a real false positive here.
- Pass raw observations under `evidence_*` for whatever only interpretation can settle.
- **Never let a model verdict override a deterministic check** in either direction: force the
  verdict from the check and keep the model's differing opinion recorded next to it.

Measured value of the audit pass: 18 claims → **2 real defects**, 15 downgraded as unproven. A probe
loop without grounding + audit reports mostly noise, and a wrong deterministic check is worse than
no check because it becomes authoritative and un-auditable — write the check text next to the
requirement it settles and re-read it before trusting the gate.

## Site sweep product (`~/ops/typesafe/sweep/`, 2026-09-21)

The probe loop above, generalised into a config-driven product that runs on any website and emits a
client-facing report:

- `sweep_core.py --target targets/<name>.json [--pack generic] [--lane jev|deepseek]` — preflight →
  probe order → per-requirement verdicts → self-audit → authority gate → `results.json`,
  `report.md`, `report.html`.
- `packs/generic.py` (10 site-agnostic probes: crawl status, console errors, titles, single h1,
  image alts, internal links, mixed content, soft-404, mobile overflow, form validation) with the
  requirement set in `requirements/generic.json`, which binds each requirement to its `check_*`
  names and a copy-pasteable repro command.
- `render_pdf.py --run runs/<dir> --out docs` — client-facing PDF via Chrome print-to-pdf: cover
  block, then per defect **What we found / Proof (exact command) / Impact / Fix**, plus a
  "what we did not test" section, brand-only authorship, ASCII-only text. Run the deliverable
  skill's AI-tell scan before sending.
- `selftest.py` — 97 offline invariants, wired into `~/ops/verify/checks-monetize.json` so the offer
  carries a real proof binding.
- `offer-candidate.json` — gated offer spec (see below).

Three guards are the actual product value, each earned by a real failure:

1. **Render preflight** (`classify_render`). sanad.io answers a plain GET with 200 but hands headless
   Chrome an "Access Denied" wall; without the guard the sweep reported the *wall's* defects as the
   site's (403 console errors, 17px overflow, soft-404) — all false. When the browser is not looking
   at the real page the run **refuses** and reports no findings at all.
2. **Deterministic checks decide; the model only interprets** (`apply_authority`, polarity: `check_*`
   TRUE = requirement met).
3. **`requires_manual_confirmation` + `flag_when`** — a requirement the harness cannot prove (would
   an empty form really submit?) is reported as "flag for a human check", never as a defect. The
   probe never submits a form the browser considers valid, so it can never send a client a message.

Independently checked: the az-ebook soft-404 finding (a nonexistent path returns HTTP 200) was
reproduced by both lanes.

**Priceability forced a second lane.** The Jev API publishes no rate card, so an offer priced on Jev
fails R8 in the offer gate. `lanes.py` adds `DeepSeekLane` behind the same
`ask(state, questions)` contract. Measured on az-ebook: 25 calls, 34,586 in / 17,618 out tokens,
139.5 s, **$0.004809** at the api_deepseek_flash rate card. DeepSeek over-claims more than Jev (one
run: 9 claims, 9 downgraded by the audit) — the authority gate is what keeps the output honest, not
the model.

## Pitfalls (all hit for real on this VM)

- **A helper that swallows exceptions hides a broken probe.** `js()` returning `None` after a JS
  syntax error looked exactly like "the site has no internal links". Record JS errors and let a probe
  assert that it measured *something* (`check_*_links_checked_at_least_one` is what caught it).
- **Count a defect once.** A requirement proven broken stays violated for the rest of the run; only
  the step where it first flips is a finding, otherwise a 1-defect site reports "8 findings".
- **An offer-gate spec must be `{"offers": [...]}`.** A bare offer object makes the gate print
  "0 pass / 0 fail" and look clean.
- **`\b` does not protect a URL regex.** `/payment\b` matches `/payment-terms`; use
  `/payment(?:[/?#]|$)` or the sweep refuses pages it should sweep.


- **`"type"` is mandatory on raw REST.** Omitting it (copying the SDK's class-based shape) returns
  `422` with the offending field named — read the error body, it tells you which key is wrong.
- **Response is `answers`, not `nouls`/`choices`/`scores`.** SDK docs split them into typed
  collections; the raw endpoint merges them and tags each with `"type"`.
- **`model` must be sent as `jev-latest`** — pinning an invented version string gets a `422`.
- Don't compose a mini-prompt per question. `instructions` is the question; `state` carries the
  material. Putting the document inside `instructions` destroys the token win.
- Batching is where the savings are, but **all questions in one call share one `state`** — if two
  questions need different documents, that's two calls.
- Never put the API key in a client deliverable, a cron prompt, or a git-tracked file.
- **Do not test the cart/checkout contract through the storefront UI.** On the Shopify theme probed
  here the UI add-to-cart silently did nothing in headless Chrome (cart stayed at 0), so every UI
  verdict came back `not_observable`. The public cart API (`/cart/add.js`, `/cart/change.js`,
  `/cart.js`, `/discount/<code>`) through same-origin `fetch` is the reliable lane — and it is where
  quantity validation actually lives.
- **`before`/`after` observations must not straddle a mutation the probe itself performs.** A probe
  that clears the cart and then reads totals makes any "total unchanged" check meaningless; capture
  the comparison values *inside* the probe and return them.
- Probe functions that share a signature must be called uniformly — a set of "needs handle" probes
  calling `f(s)` while every function takes `(s, h)` fails instantly with 0.0 s steps.

## Reference material on this box

- Vendored upstream, read-only, pinned: `~/ops/vendor/skills/typesafe-ai/typesafe-ai/SKILL.md`
  (+ `PROVENANCE.md` — commit `65a39f39`, MIT, sha256 `71ea90d7…`).
- Upstream docs mirror: `~/ops/typesafe/docs/` (`api.md`, `primitives.md`, `primitives/choice.md`,
  `primitives/noul.md`, `primitives/score.md`, `confidence.md`, `concepts/state.md`,
  `concepts/how-to-build-with-system-one.md`).
- Cookbooks worth mining: `docs.typesafe.ai/cookbooks/parallel_questions`,
  `/sde_cascade`, `/consistency_noul_cookbook`, `/function_calling`.
- Claude Code plugin (this VM, scope user, v0.5.7):
  `~/.claude/plugins/cache/typesafe-ai/typesafe/0.5.7/skills/typesafe-ai/SKILL.md`.
- Monetization lanes + measured numbers: `~/ops/typesafe/MONETIZATION.md`.
- Grounded probe-loop demo (runnable): `~/ops/typesafe/qa/` — `jev.py` (client), `browser_ops.py`
  (Playwright probes), `probe_loop.py` (choice → verdict → audit, writes `results.json`,
  `report.md`, `report.html`; `--report-only` re-renders without re-probing).
