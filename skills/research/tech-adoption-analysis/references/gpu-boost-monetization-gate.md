# GPU boost + monetization gate (reference for "how do we boost/monetize our GPU" asks)

Use this when Aamir (or a client) asks how to *boost* the infra's GPU or *monetize* GPU-shaped work,
or forwards a concept post about GPU performance. Verified 2026-09-13 on the Always-Free VM.

## 1. The standing fact: this VM has no GPU

`nvidia-smi` is absent; `lspci` shows a Virtio display device only. Any answer that starts with
"optimise the GPU" is wrong before it starts. The honest framing is **lanes**, not tuning:

| Lane | Rate | Commercial? | Use |
|---|---|---|---|
| local CPU | $0 | yes | ≤3B Q4 only |
| Kaggle free | $0 (30 GPU-h + 20 TPU-h per week) | **no** (ToS: internal, personal, non-commercial) | R&D, benchmarks, eval |
| HF ZeroGPU | $0 (A100 40 GB, Gradio Spaces) | **no** | demos |
| Vast.ai 4090 | $0.13–0.59/h, per-second | yes | default for sold work (spot) |
| RunPod 4090 | $0.34–0.74/h, per-second | yes | default for sold work (on-demand) |
| RunPod A100 80 GB | from $1.39/h | yes | only when >24 GB VRAM is needed |
| OCI A10 / A100 / H100 | $1.50 / $2.95 / $10.00 per GPU-h | yes | residency/compliance only |

Ownership break-even (4090-class, ~$2,300 capex, 350 W at $0.048/kWh ⇒ ~$0.104/h): **192 h/month**
vs Vast typical, 564 h/month vs Vast spot. Below that, renting wins - do not buy hardware.

## 2. Reusable tooling (already built)

- `~/ops/scripts/gpu_econ.py` — rate card + 5-rule margin gate.
  `--gate` (exit 0 pass / 1 fail), `--selftest` (proves each rule fires), `--breakeven`,
  `--quota-watch` (silent unless free hours are about to expire unused), `--rates`.
- `~/ops/gpu-econ/plays.json` — live play list. `rejected.json` — negative control (must exit 1).
- `~/ops/gpu-econ/bench_baseline.py` — re-measures the local ceiling (BLAS GFLOP/s, copy bandwidth,
  ollama tok/s). Run this before quoting any local-inference throughput.
- `~/ops/verify/checks-gpu-econ.json` — 17 deterministic layer-3 checks.

**Gate rules to reuse for any new monetization idea:** R1 margin floor, R2 lane terms vs
customer-facing exposure, R3 assumed throughput needs +15 pp headroom, R4 free-lane weekly capacity,
R5 price ≥ floor. Adding a play = append to `plays.json` and re-run `--gate`; the R3 rule is what
stops an assumed throughput figure from becoming a quoted price.

## 3. Measured local baseline (2026-09-13, re-run to refresh)

72.9 GFLOP/s fp32 BLAS · 22.8 GB/s aggregate copy bandwidth · 11.6 GiB RAM (2.8 GiB available with
two models resident) · qwen2.5:3b: cold load 21.1 s, 10–15 tok/s generation, 31 s for a 36-token
exchange · qwen2.5:7b: 0.03 tok/s generation, 3 m 34 s for the same exchange (unusable -
residency-bound, not compute-bound).

## 4. Analytical frame that worked

Take the post's closing question - *what is limiting useful progress right now?* - and answer it with
our numbers instead of summarising the post. Then add the two things concept posts usually omit and
that decide this case: (a) utilisation is invisible to the invoice (wall-clock/per-second billing
makes load and prefill the paid cost), and (b) capability ≠ permission (the free lanes may not be
sold). Deliverable shape that satisfied the ask: measured baseline table + lane ladder + ranked
monetization plays with unit economics + a built gate + independent verification.

## 5. 2026-09-18 evolution — the ask became "can our infra systematically monetize THIS wave"

Same class, one level up: instead of GPU plays, the link was a **capability syllabus** (the free
open-source HF Agents Course: unit 1 fundamentals → unit 2 three agent frameworks → unit 4 eval) and
the question was what the infra may *sell* against it. Full recipe now lives in the class-level skill
`monetization-offer-gating`; the transferable lessons measured here:

- **A course unit is a pricing layer, not a topic.** Tag every offer with its syllabus layer and run a
  coverage check — the honest fix for an unmet coverage floor is to **label all offers**, never to
  lower the floor.
- **Don't sell a capability by NAME before its probe passes.** Unit 2 names three frameworks
  (smolagents / LlamaIndex / LangGraph) and **none were installed on the box** → the one layer clients
  ask about by name was unsellable. Fix = install a real lane and measure it (all three together:
  **52.2 MB RSS**, so cost was never the blocker — delivery time was, hence delivery-day pricing).
- **Rule set grew 4 → 10** when the artifact became an offer portfolio: added proof binding
  (offer → a real `verify/checks-*.json` check), SLA → enabled watcher, live capacity tied to
  `/proc/meminfo`, external/money = autonomy L3 + gate, cost recomputed from the lane rate card,
  framework readiness (live import probe at gate time), and no-phantom-GPU (`gpu_required` only on a
  rented commercial lane — this host has no GPU, so unit-1-bonus fine-tuning must be rented).
- **The independent judge rejected the claim twice — both times about the EVIDENCE, not the claim.**
  `independent_check.py --mode model` needs `--evidence-file`; an unlabelled dump let the selftest's
  ten `[ok ] rN` rule-firing lines read as *ten passing offers*, and the sub-claim "every offer's
  proof_check resolves to a real check" had no artifact until a binding report existed. Two rejections
  before a pass is the healthy signal that the verifier can actually disagree.
