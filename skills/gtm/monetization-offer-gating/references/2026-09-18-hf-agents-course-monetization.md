# 2026-09-18 — HF Agents Course → machine-checked offer pyramid (pass 1 + pass 2)

Source artifact: a LinkedIn short link posted as "our infra should monetize this" — resolved by
content to the **free open-source Hugging Face Agents Course**. Course structure (from the post
text) drove the offer coverage map:

| Course layer | Priced offer added (pass 2) | Price | Margin | Proof binding |
|---|---|---|---|---|
| 01 Fundamentals | (existing) | — | — | check name in `checks-monetize.json` |
| 02.1 smolagents | `framework-agent-build` | $1,200 ×2 | 97.3% | R9 import probe + lane live |
| 02.2 LlamaIndex (agentic RAG) | `agentic-rag-agent` | $1,500 ×1 | 97.2% | local RAG lane live (ollama bge-m3) |
| 02.3 LangGraph | (part of framework build) | — | — | R9 probe |
| Bonus function calling | `functions-calling-finetune` | $900 ×1 | 98.6% | rented GPU lane (R10) |
| 03 Eval / traces | `agent-trace-observability-month` | $350/mo ×3 | 97.9% | watcher enabled (R4) |
| 04 Deploy | (existing) | — | — | — |

Book grew 8 → **12 offers**; 9 layers labelled. Coverage check floor = 6 layers, **all 12 offers
labelled** (never relax the floor to go green).

## The pass-2 finding (why R9 exists)

Unit 02 of the source names three frameworks. Probed the box: **none of smolagents / llama-index /
langgraph were installed anywhere** — the layer clients ask for *by name* was unsellable while we
still advertised "we build agents". Fix: real runtime lane `~/agentlab`.

Measured (live import probes, `fw_probe_all.py` / `fw_measure.py`):

| Framework | Course unit | Version | Result |
|---|---|---|---|
| smolagents | 2.1 | 1.26.0 | import OK |
| llama_index | 2.2 | 0.14.24 | import OK |
| langgraph | 2.3 | 1.2.11 | import OK |

All three imported in one interpreter: **52.2 MB RSS** → memory is not the constraint; delivery days
are. That is why those offers are priced on delivery hours, not tenants.

Capacity at pass time: used **1310 MB / cap 2310 MB** (headroom 4620 MB) → R5 PASS.
Host has **no GPU** → `gpu_required` offers may only sit on a rented commercial lane (R10).

## Gate results (pass 2)

| Layer | Result |
|---|---|
| Real book `--gate` | **12 pass / 0 fail** |
| Negative control (10 offers) | **0 pass / 10 fail** — one distinct rule each |
| `--selftest` | all 10 rules fire (R1–R10) + R9 probe path |
| Layer-3 deterministic suite | **35/35 pass** (31 + 4 new pass-2 checks) |
| `proof_binding_report.py` | **12/12 bound, 0 unbound** |
| Independent model judge (zai / GLM-4.5-flash) | **FAIL → FAIL → PASS** (`missing_evidence: []`) |
| `claim_integrity.py` on the note | PASS, 0 HIGH/MED/LOW |

## Judge history — the two rejections (the real lesson)

1. **Rejection 1 (ambiguity):** the evidence file mixed sections; the selftest's ten `[ok ] rN`
   rule-firing lines were read as *ten passing offers*, contradicting "0 pass / 10 fail". The judge
   was right — the evidence, not the verdict, was wrong.
2. **Rejection 2 (missing clause):** "every offer's `proof_check` resolves to a real check" had no
   evidence at all; the judge named exactly that clause.
3. **Pass** after: numbered sections with explicit labels (`[1] FRAMEWORK LANE PROBES`,
   `[3] REAL BOOK`, `[4] NEGATIVE CONTROL`, `[5] SELFTEST — rules firing, NOT offer verdicts`,
   `[6] PROOF BINDING`) and the new `proof_binding_report.py` output. `build_evidence.py` now
   assembles this file deterministically from `last_run.txt`.

Rule of thumb: treat a verifier rejection as **ground truth about the evidence artifact**, fix the
artifact, re-run. A verifier that cannot disagree is decoration.

## Still NOT claimed (honesty section, kept in the note)

- R9 proves *import*, not *delivery* — no reference agent shipped in any lane yet. Next step: one
  reference agent per lane (smolagents, LlamaIndex, LangGraph), documented and gate-passed, which
  upgrades R9 from "imports" to "shipped once".
- 5 offers are priced on **assumed** token counts (R7 warns); the RAG lane's 650 MB is assumed.
- Zero owned GPU.

## Fixed quirks found while wiring

- `checks-monetize.json` is a top-level **list** (not `{"checks": [...]}`) — readers must handle both
  shapes (`TypeError` on `['checks']`).
- Inline heredoc/`for` one-liners over the manifests exited -1; moving the same logic into
  `build_evidence.py` / `proof_binding_report.py` worked. Long package-install probes exceed the 600s
  foreground cap → `background=true, notify_on_complete=true`.
- `run_all.sh` gained step 6 (proof binding) so one command reproduces every layer.

## File inventory (pass 2 additions)

`offer_gate.py` (R1–R10) · `frameworks.json` · `offers.json` (12) · `rejected-offers.json` (10) ·
`fw_probe_all.py` · `fw_measure.py` · `coverage_check.py` · `label_units.py` ·
`proof_binding_report.py` · `build_evidence.py` · `append_checks.py` · `run_all.sh` · `last_run.txt` ·
`last_evidence.txt` · `SELF-PROMPT-LOG.md` · `~/ops/verify/checks-monetize.json` (35 checks).
Write-up: `~/brains/ops/knowledge/infra/monetize-architecture-boost-2026-09-18.md`.
