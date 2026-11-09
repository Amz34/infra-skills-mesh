---
name: model-tier-selection
description: Use when selecting model/tier for a task — cost gate first.
---

# Model-Tier Selection (kaunsa model kis kaam pe)

Astra wave lessons #2/#7 (Fable vs Astra villa A/B; Astra Max vs Medium same task): benchmarks hype hain — REAL hamara kaam pe A/B karo, aur har task ke liye sahi price tier chuno. Frontier model ka matlab har cheez frontier se nahi.

## Trigger
- Naya model launch hua (GPT-6 Astra, Claude Fable X, ...) — "switch karein?" sawal.
- Ek task expensive lagna: long agentic run, pura repo build, client deliverable.
- Hybrid router me tier rules update (hybrid-compute-infra skill).

## Steps
1. **Task classify karo**:
   - Routine (extract, summarize, rewrite, simple Q) → cheapest tier / local (deepseek-v4-flash / qwen local) — Astra wave me bhi yehi pattern: "basic kaam ko frontier ki zaroorat nahi".
   - Mid (cron agents, delegation batches, medium coding) → mid tier.
   - High-value (complex one-shot build, client-facing doc/slide jo deal decide kare, 3D/site prototype) → frontier, aur wahan bhi subscription-included usage pehle.
2. **Cost gate**: frontier API ≈ $10/$50 per M tokens (Astra) = 20-50x routine. Total run cost estimate karo pehle (hermes-token-cost-ops): agar < value, tabhi frontier.
3. **Real-task A/B** kisi bhi switch se pehle: same client task dono models pe, output compare (coding-agent-ab-eval skill). Benchmarks/leaderboards cite mat karo — verify official docs pehle.
4. **Decision record karo** — roadmap doc me (e.g. `~/ops/kb/astra-ga-2026-09.md` style).
5. **Revert plan**: naya model fail ho to purane pe wapas — ek-line config change, system design me lock-in nahi.

## Local-first routing table (wired on this VM, 2026-09)

Ollama runs as a **system** service on `:11434` (the user unit is inactive — check `systemctl is-active ollama`, not the user one). Models installed: `qwen2.5:7b`, `qwen2.5:3b`, `llama3.2:3b`, `llava:7b`, `bge-m3` (embeddings).

| Alias | Model | Use for |
|---|---|---|
| `local` | qwen2.5:7b | bulk extract/rewrite/classify, cheap drafting, i18n string passes |
| `local-fast` | qwen2.5:3b | regex/label/normalize jobs, quick heuristics, embeddings-adjacent glue |
| `deepseek-v4-flash` (default) | — | agentic runs, tool-use, real coding |
| frontier | — | client-facing one-shot build / deal-deciding doc only |

- Aliases live in `~/.hermes/config.yaml` under `aliases:` with `provider: custom` + `base_url: http://localhost:11434/v1`.
- Reality check (30d, `state.db` sessions): 195 sessions on flash, **2** on a local model → the plumbing works but nothing routes local by itself. Route explicitly: pick `local`/`local-fast` for the classify/extract step BEFORE calling the frontier model.
- PII never leaves the box: send it through `~/.hermes/scripts/pii_gate.py` (hybrid-compute-infra skill).

## Pitfalls
- Hype posts ("AGI!", "free models on <new gateway>") — koi measurable nahi → ignore (tech-adoption-analysis skill).
- **"Free" / "official se 10× sasta" third-party relay = tier nahi, risk hai.** Price floor upstream cost se banta hai, isliye aisi offers farmed/carded/shared keys ya crypto-airdrop funnel hoti hain. Aise gateway ko default route ya client data pe kabhi nahi — sirf sandbox airlock (rate limiter + circuit breaker + quota ledger + kill switch, PII gate pehle). Recon ladder + verdict template: tech-adoption-analysis → `references/free-api-relay-due-diligence.md`.
- Third-party "GPT-6 status" trackers outdated hote hain — sirf official docs (openai.com, developers.openai.com) verify karo.
- Frontier models pe safety pauses/restrictions (Astra cyber tasks stopped) — sensitive tasks pe pehle test.
- Output token 128K + huge context = hidden cost; context sirf relevant rakho.

## Refs
- `~/ops/kb/astra-ga-2026-09.md` (Astra GA analysis + 20-build table)
- hybrid-compute-infra (local/frontier routing), hermes-token-cost-ops (cost), coding-agent-ab-eval (A/B)
