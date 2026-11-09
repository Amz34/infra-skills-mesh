---
name: monetization-offer-gating
description: Use when pricing/selling a capability — gate each offer.
version: 1.0.0
author: Aamir Zameer — Hermes
license: MIT
metadata:
  hermes:
    tags: [monetization, offers, pricing, gate, verification, margin, capacity, lanes, autonomy]
    related_skills: [content-integrity-guardrail, agent-autonomy-governance, model-eval-ops, gpu-econ, competitor-landscape-research]
---

# Monetization offer gating — sell only what the infra can prove

## When to Use

- A capability looks sellable (a new course/framework/tool wave, "clients are asking for X") and the
  question is **what may we actually quote, at what price, with what delivery promise**.
- Adding/repricing an offer, opening a new capability lane, or quoting a tenant/slot count.
- Any request of the shape "how can our infra make money from <thing>" — the answer is a *gated
  portfolio*, not a narrative.

Companion classes: `content-integrity-guardrail` gates **claims in copy**; this skill gates
**capabilities and prices**. A capability that fails here must not be written into copy at all.

## The artifact set (all under `~/ops/monetize/`)

| File | Role |
|---|---|
| `offer_gate.py` | The gate: 10 rules, `--gate --spec <json>`, `--selftest`, `--rates`, `--frameworks` |
| `offers.json` | The real book — each offer carries `price`, `units`, `lane`, `autonomy`, `proof_check`, `framework`, `course_unit`/layer label |
| `rejected-offers.json` | Negative control — N offers, each designed to fail **exactly one distinct** rule, with an `expect` map |
| `frameworks.json` | Lane matrix: framework → course unit → **live import probe** command **and the reference-run requirement (R9a + R9b)** |
| `fw_probe_all.py`, `fw_measure.py` | Live probes: import ok, version, import time, RSS (evidence behind R9a + capacity) |
| `reference/ref_<framework>.py` | One **reference agent per lane** — the thing that actually runs (R9b evidence generator) |
| `reference/logs/<lane>.json` | Hash-bound run log: lane, framework, model, elapsed, output, `script_sha256`, `ran_at`, `local_only` |
| `reference/verify_reference.py` | R9b integrity check over those logs (sha match, real output, age) |
| `reference/unload_models.py` | Releases the resident ollama models (`keep_alive=0`) so the box returns to baseline after a run |
| `proof_binding_report.py` | R3 evidence table: every offer → a real check name in `verify/checks-*.json` |
| `coverage_check.py`, `label_units.py` | How much of the source syllabus/capability pyramid is priced, and each offer's layer label |
| `build_evidence.py` → `last_evidence.txt` | Section-labelled evidence file for the model-mode verifier |
| `run_all.sh` → `last_run.txt` | **One command** for the whole QA: probes → coverage → real gate → negative control → selftest → proof binding → **R9b reference runs** → **release local models (baseline)** |
| `~/ops/verify/checks-monetize.json` | The layer-3 manifest so the nightly silent-on-pass cron enforces all of it |

## Rules (why each exists — they came from real gaps, not theory)

- **R1 margin** ≥ `min_margin` (0.60) after allocated fixed cost.
- **R2 lane ToS** — the lane must be a declared lane; lanes are **imported** from
  `ops/scripts/gpu_econ.py` (`LANES` / `LANE_EXTRA`), never copied, so policy stays single-sourced.
- **R3 proof binding** — each offer's `proof_check` must resolve to a real check name in
  `verify/checks-*.json`. No proof → not sellable.
- **R4 SLA → watcher** — a promised SLA requires an **enabled** watcher/check to exist.
- **R5 plan-stable capacity** — Σ(RSS × units) must fit a **plan-based** cap:
  `CAPACITY_SHARE × (mem_total_mb() − SAFETY − RESERVED_LOCAL_MODELS_MB)`, i.e. derived from
  `MemTotal` (a stable property of the box) and a fixed reserve (`RESERVED_LOCAL_MODELS_MB = 2600`
  for the ollama models a reference run keeps resident), **never** from live free RAM. A verdict that
  moves when a background model happens to be resident is not a verdict. Live free RAM goes in a
  separate **R5b advisory** line ("live free X MB (LIVE PRESSURE)") = a deployment-timing fact, not a
  sellability fact. Selftest must prove the same book yields the same capacity verdict under different
  live free RAM.
- **R5b is advisory only** — may annotate the report, may never flip a pass/fail.
- **R6 external/money = L3 + gate** — anything external or money-touching carries autonomy level 3
  and `gate_required` (see `agent-autonomy-governance`).
- **R7 assumed numbers** — offers priced on assumed throughput/token counts need +15pp headroom and
  are flagged as warnings; assumed is allowed but must be *visible*.
- **R8 cost arithmetic** — recompute cost from the lane rate card (`in_per_mtok`) rather than trusting
  the hand-written number.
- **R9 framework readiness (two-sided — an import is not a delivery)** — an offer that names a
  framework needs **both**:
  - **R9a import probe** — that lane's live import probe passes **at gate time** (version + RSS from
    `fw_probe_all.py` / `fw_measure.py`). A declared-but-broken lane fails too.
  - **R9b hash-bound reference run** — a run log from `reference/logs/<lane>.json` showing an agent
    actually **executed** in that lane (`exit 0`, a real answer, `script_sha256` matching the script
    on disk, `local_only`, `role: reference agent`), checked by `reference/verify_reference.py`.
  Fail-closed: delete `frameworks.json` and every framework-named offer is blocked (proven by
  selftest). Rationale measured the hard way — `llama_index` imported cleanly and still died on its
  first `agent.run()`; an offer sold on "the library imports" would have shipped a broken deliverable.
- **R10 no phantom GPU** — `gpu_required` offers may only sit on a rented commercial GPU lane; a host
  with no GPU (`! command -v nvidia-smi`) can never host them locally.

## Method — self-prompting + self-QA loop (the ask "use cli, self-prompt, qa urself")

1. **Round loop, one artifact per round.** State the question in `SELF-PROMPT-LOG.md`, run a CLI
   probe, then let the **measurement contradict the plan** and fix the artifact. Log per round:
   question → measurement → decision. The log is a deliverable, not a diary.
2. **Six layers of QA, in this order:** real book (`--gate`) → negative control (`--gate` on
   `rejected-offers.json`) → `--selftest` (proves every rule can fire, positive control + tamper case)
   → layer-3 deterministic suite (`independent_check.py --mode deterministic --checks
   checks-monetize.json --label <x>`) → **R9b reference runs** (`reference/verify_reference.py`, then
   `reference/unload_models.py`) → independent model judge (`--evidence-file` rebuilt from the ledger)
   → `claim_integrity.py` on the write-up.
3. **Negative control is mandatory and must be one-distinct-rule-per-offer.** A gate that never
   fails proves nothing.
4. **Wire it to cron.** Add the new checks to `checks-monetize.json`; the nightly
   `daily_selfqa.sh` layer-3 run is silent-on-pass. Monetization then re-verifies itself every night.

## Pitfalls (measured, each one cost a real cycle)

- **Verifier evidence must be section-labelled.** `independent_check.py --mode model` needs
  `--evidence-file` (without it the verdict is "no evidence supplied"). An unlabelled dump gets
  misread: the selftest's ten `[ok ] rN` rule-firing lines looked like *ten passing offers* against a
  claim of "0 pass / 10 fail" — a correct rejection of my claim, not a tool failure. Fix: numbered
  sections with explicit headers ("REAL BOOK", "NEGATIVE CONTROL", "SELFTEST — rules firing, NOT offer
  verdicts") and a line per claim.
- **Every sub-claim needs its own evidence section.** "All offers pass" was accepted, but "every
  offer's proof_check resolves to a real check" was rejected until `proof_binding_report.py` produced
  a binding table. Assume the judge will decompose the claim and demand each clause.
- **Never lower a coverage floor to go green.** When the syllabus-coverage check failed, the honest
  fix was to label **all** offers by layer, not to relax the floor.
- **Don't sell a capability by name before its probe passes.** The named frameworks in the source
  syllabus were not installed anywhere on the box → the layer clients ask for by name was unsellable.
  Installing a real lane (and recording version + RSS) closed the hole.
- **`checks-*.json` shape varies** — some manifests are top-level lists, others objects with
  `checks`. Handle both, or the reader exits on a `TypeError`.
- **Don't trust inline one-liners for evidence**: heredocs and inline `for` loops over `checks-*.json`
  exited -1 and long commands are rejected over 600s. Write a `.py`/`.sh` file, run it, then read the
  produced artifact (`last_run.txt`, `last_evidence.txt`, `last_report_*.json`). Foreground timeout cap
  is 600s — use `background=true, notify_on_complete=true` for probes that install packages.
- **Never put the verifier's own past verdicts in the evidence file.** Rebuilding evidence from
  `run_all.sh` output *and* appending the earlier `verdict=fail` judge rows made the judge fail the
  claim twice — it read its own history as a contradiction. History belongs in the ledger
  (`verify-ledger.jsonl`), not in the evidence handed to the judge.
- **The evidence must literally contain the counts the claim asserts.** A claim saying "40/40 checks
  pass" was rejected while the evidence only had the gate/selftest numbers. Fix: `build_evidence.py`
  reads the newest deterministic suite row out of the ledger and emits **its own section** —
  `label / ts / verdict / passed / total` **plus one line per check with its pass flag**. State the
  number the claim names, in the same file, from the ledger (machine-written), not from memory.
- **Print a summary block FIRST in any checker.** Long record dumps get truncated in logs and hide
  *which* check failed; `independent_check.py` now emits a compact summary (`label/verdict/passed/
  total/failed names`) before the full JSON.
- **Selftest needs a positive control and a tamper case, not just failing inputs.** A rule only ever
  fed bad input proves nothing but its own paranoia. For R9b: a **real** reference script must pass,
  and a **tampered** log/hash (`selftest-ref-tampered.json`) must fail. (An earlier version used a
  synthetic log as the positive control — worthless.)
- **Resolve paths inside evidence against a fixed ROOT.** Run-log `script` fields were relative, so
  verification passed in the project cwd and failed from `/tmp` or through `~`. Fix: `ROOT` +
  `_resolve` in `verify_reference.py`, and abs-resolve + explicit "reference script missing on disk"
  handling in the gate.
- **When a lane only runs after a monkey-patch, the workaround is evidence.** Upstream
  `FunctionAgent` needed `__hash__` restored; the patch lives in the reference script and the
  workaround is **recorded in the run log's output** — surfaced as a fact, never hidden.
- **Leave the box at baseline after reference runs.** Real runs pin ~2.6 GB of local models; end
  `run_all.sh` with `unload_models.py` and verify `ollama ps` is empty. Add the reserve to the R5 cap
  so a run never silently changes a capacity verdict.
- **Write files in chunks and read them back.** Large `write_file`/`patch` payloads can be silently
  cut mid-content; a truncated script still looks plausible. Verify with a read-back, and prefer
  several small patches over one giant rewrite.
- **Flag what is still not claimed** in the write-up: a reference run ≠ a shipped client deliverable;
  assumed token counts remain assumed; a RAM figure for a RAG lane may be assumed. State these
  explicitly — the honesty section is what makes the rest credible.

## Verification

```bash
bash ~/ops/monetize/run_all.sh                     # rc=0, writes last_run.txt (all layers)
python3 ~/ops/monetize/offer_gate.py --selftest    # every rule must fire (incl. R9b + tamper cases)
python3 ~/ops/monetize/proof_binding_report.py     # N/N bound, 0 unbound
python3 ~/ops/monetize/reference/verify_reference.py   # 3/3 lanes: hash-bound run logs match
python3 ~/ops/monetize/reference/unload_models.py      # box back to baseline (ollama ps empty)
cd ~/ops/verify && python3 independent_check.py --mode deterministic \
  --checks checks-monetize.json --label monetize-pass2
cd ~/ops/verify && python3 independent_check.py --mode model --backend zai \
  --claim "<one sentence per clause>" --evidence-file ~/ops/monetize/last_evidence.txt
python3 ~/ops/verify/claim_integrity.py ~/brains/ops/knowledge/infra/<note>.md
```

Ledger rows land in `~/ops/observability/verify-ledger.jsonl`.

Session detail (source syllabus mapping, lane measurements, judge verdict history, file inventory):
`references/2026-09-18-hf-agents-course-monetization.md`.
Reference-agent lanes — how to build one per framework, the run-log schema, the two upstream traps
found by actually running agents, and the judge-failure post-mortem:
`references/reference-agent-lanes.md`.
