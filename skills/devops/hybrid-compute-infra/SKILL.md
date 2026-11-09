---
name: hybrid-compute-infra
description: "Use when setting up hybrid compute (Ollama, PII routing)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [hybrid, compute, ollama, pii, privacy, routing, local, cost, watchdog]
---

# Hybrid Compute Infra (Local + Cloud Routing)

Perplexity hybrid-compute pattern (Aravind Srinivas LinkedIn post, 2026-09) applied
to Aamir's Oracle ARM VM: **sensitive steps run local, heavy reasoning runs cloud —
decide where a workload runs BEFORE any cloud LLM call.**

## When to Use

- Setting up hybrid local/cloud routing on a fresh VM (reproduce this kit)
- Wiring a new pipeline (form intake, lead scoring, email triage) that must
  route sensitive data locally
- Debugging: watchdog alerts, PII gate wrong verdicts, cold-model latency,
  cost report not showing local traffic
- RAM pressure / swap thrash / "box got slow" (idle model resident, unbounded swap ceilings)
  → `references/memory-containment-small-box.md` (containment rules + the ceiling checker)
- Explaining the architecture / selling "client data never leaves the box" to clients

## Architecture

```
input ──> pii_gate.py (deterministic-first: regex → Luhn → keywords → local LLM confirm)
              │
              ▼
         hybrid_router.py ──decide()──►  PII high  → LOCAL (privacy, never leaves box)
                                         classify/extract/summarize/score/normalize
                                         + short text → LOCAL (cost: free tokens)
                                         everything else → CLOUD (frontier reasoning)
```

- **PII Gate** = privacy wall. **Router** = cost optimizer. **Watchdog** = crash-proof layer.
- Fail-closed philosophy: if local LLM is unavailable, keyword-flagged text is
  treated as sensitive → routed local. Data never leaks cloud-ward on a miss.

## Components (all in `~/.hermes/scripts/`, copies in this skill's `scripts/`)

| File | Role | Key flags |
|---|---|---|
| `pii_gate.py` | Classify/redact PII, deterministic-first | `--stdin --mode check\|redact\|classify --no-llm` |
| `hybrid_router.py` | Local/cloud decision + execution | `--task classify\|extract\|summarize\|score\|normalize\|generic --run --model` |
| `hybrid_watchdog.sh` | Ollama restart + gateway alert + PII smoke test | silent when healthy (no_agent cron) |
| `hybrid_cost_report.py` | Weekly cloud $ + local/cloud split signal | cron `0 8 * * 1` |
| `lead_pipeline.py` | Full lead chain: PII gate → local score → sanitized cloud summary | `--stdin --payload --cloud-summary --rubric --threshold --lang` |

Config aliases (set via `hermes config set`, NEVER hand-edit config.yaml):

- `local` → `qwen2.5:7b` (quality local tasks)
- `local-fast` → `qwen2.5:3b` (fast/cheap local tasks, PII LLM-confirm model)
- Use in any Hermes session: `hermes chat -q "..." -m local` or `/model local`

## Setup (fresh VM, ~15 min)

### 1. Ollama as a systemd service with warm models

```bash
# install ollama (Linux), then:
sudo systemctl enable --now ollama
sudo mkdir -p /etc/systemd/system/ollama.service.d
# keep-alive = RAM-vs-latency POLICY. 30m is latency-first and only correct when ollama
# owns its RAM; on a box where the gateway/RAG stack shares 11GB, 5m unloads an idle
# model (verified 2026-09-21: an idle runner held 1.4GB until keep-alive dropped to 5m).
# Cold load ~31s, warm 4s. Containment: references/memory-containment-small-box.md
echo -e '[Service]\nEnvironment="OLLAMA_KEEP_ALIVE=5m"' \
  | sudo tee /etc/systemd/system/ollama.service.d/keepalive.conf
sudo systemctl daemon-reload && sudo systemctl restart ollama

# pull models (ARM box: 2 vCPU/11GB → 3B for speed, 7B for quality)
ollama pull qwen2.5:3b && ollama pull qwen2.5:7b
# preload once so the warm window starts immediately
curl -s http://localhost:11434/api/generate -d '{"model":"qwen2.5:3b","prompt":"hi","keep_alive":"30m"}' >/dev/null
```

Verify: `curl -s http://localhost:11434/api/tags` and the OpenAI-compat endpoint
`curl -s http://localhost:11434/v1/models` (Hermes custom provider + scripts use `/v1`).

### 2. Deploy scripts (this skill is the source of truth)

```bash
SKILL_DIR=~/.hermes/skills/devops/hybrid-compute-infra
cp "$SKILL_DIR"/scripts/{pii_gate.py,hybrid_router.py,hybrid_watchdog.sh,hybrid_cost_report.py,lead_pipeline.py} ~/.hermes/scripts/
chmod +x ~/.hermes/scripts/*.py ~/.hermes/scripts/hybrid_watchdog.sh
```

### 3. Hermes model aliases (config set only)

```bash
hermes config set model.aliases '[{"name":"local","model":"qwen2.5:7b","provider":"custom","base_url":"http://localhost:11434/v1"},{"name":"local-fast","model":"qwen2.5:3b","provider":"custom","base_url":"http://localhost:11434/v1"}]'
hermes config get model.aliases   # confirm
```

(Ollama's `/v1` endpoint is OpenAI-compatible → the built-in `custom` provider
plugin handles it; no per-vendor plugin needed. Verify plugin exists:
`~/.hermes/hermes-agent/plugins/model-providers/custom/`.)

### 4. Cron wiring (cronjob tool; script field = FILENAME only, not full path)

- `hybrid-infra-watchdog` — `*/15 * * * *`, `no_agent=true`, script=`hybrid_watchdog.sh`, deliver=origin
- `hybrid-cost-report` — `0 8 * * 1` (Mon 8am), `no_agent=true`, script=`hybrid_cost_report.py`, deliver=origin

## Usage Examples

```bash
# Route a decision (no LLM call): PII → local, clean short classify → local, else cloud
echo "Client phone +966 50 123 4567 wants a quote" | python3 ~/.hermes/scripts/hybrid_router.py --stdin --task classify

# Execute the routed step (local model does it; cloud = passthrough note)
echo "..." | python3 ~/.hermes/scripts/hybrid_router.py --stdin --task score --run

# Redact before anything (overlapping spans merged → no [REDACTED:a]b] corruption)
echo "Call +966 50 123 4567, ID 1098765432" | python3 ~/.hermes/scripts/pii_gate.py --stdin --mode redact --no-llm

# Pipeline pattern: gate → route → only non-PII text may touch the cloud LLM
verdict=$(echo "$text" | python3 ~/.hermes/scripts/pii_gate.py --stdin --no-llm)
# if '"level":"high"' → local route; else cloud
```

## Lead Scoring Pipeline (`lead_pipeline.py`)

The Perplexity pattern end-to-end on real client value: a raw lead (form payload
or free text) is **gated, scored locally, and only a PII-free summary may touch
the cloud**. Selling point for clients: *lead data never leaves your box*.

```bash
# raw text (Arabic supported: summary in Arabic)
echo "نحتاج صيانة مكيفات لمستشفى في جدة" | python3 ~/.hermes/scripts/lead_pipeline.py --stdin --lang ar

# form payload with client rubric (same shape as ai-lead-qualifier answers)
python3 ~/.hermes/scripts/lead_pipeline.py --payload '{"company_type":"fm","need":"chiller","budget":"approved"}' \
  --rubric "Ideal: FM companies with approved budget. 60+ qualified." --threshold 60

# cloud-refined summary — ONLY fires when zero PII remains (fail-safe: else auto-skipped)
echo "Elevator maintenance, 3 units, Jeddah building" | python3 ~/.hermes/scripts/lead_pipeline.py --stdin --cloud-summary
```

Design invariants: raw lead text is **never persisted** — storage
(`~/.hermes/leads/scored.jsonl`) keeps only the redacted text + score; with PII
present the cloud step is impossible by construction (fail-closed).

| Test | Input | Expect |
|---|---|---|
| T-L1 PII privacy | "AC repair, call +966501234567, email facilities@clinic.sa" | route local, reason `privacy:PII level high`, cloud skipped |
| T-L2 fail-closed | "HVAC hospital, maintenance contract expiring" | keyword sensitivity → `--cloud-summary` auto-skipped |
| T-L3 payload | `--payload` + `--rubric` | local score + qualified bool from rubric |
| T-L4 Arabic | Arabic text `--lang ar` | score + summary in Arabic |
| T-L5 cloud path | clean text + `--cloud-summary` | `cloud_summary.used: true` (DeepSeek, only PII-free) |

Integrates with `~/projects/ai-lead-qualifier` (scorer.py) — same rubric/JSON
shape, so a config's `scoring_mode: llm-local` can later swap DeepSeek for
qwen2.5:7b without changing the schema. Default scoring mode stays `llm`.

**Pitfalls (lead pipeline):**
- 2 vCPU CPU-only: 7B inference 30-90s warm (longer cold). ALWAYS use `response_format: json_object` + `max_tokens <= 200`; per-call timeout >= 420s. Short outputs keep it fast.
- `classify()` already returns `redacted_text` — do NOT call `pii_gate.redact()` separately (it needs `spans_by_type`).
- Truncated model JSON must never crash: `_extract_json` fallback `{}` + exception-safe `main()` → stdout ALWAYS has JSON (never empty).
- Raw lead text is NEVER persisted — only `redacted_text` goes to `~/.hermes/leads/scored.jsonl`.

## Verification Suite (run after any change)

| Test | Command | Expect |
|---|---|---|
| T1 phone/email | `echo "Call +966 50 123 4567, a@b.com" \| pii_gate.py --stdin --no-llm` | `"level":"high"`, categories phone+email |
| T2 SA ID | `echo "ID 1098765432" \| pii_gate.py --stdin --no-llm` | `"level":"high"`, `"sa_id"` |
| T3 overlap redact | `echo "Call +966 50 123 4567 or write to a@b.com, ID 1098765432" \| pii_gate.py --stdin --mode redact --no-llm` | each span → own `[REDACTED:x]`, no nesting |
| T4 keyword-only | `echo "My salary bank statement and payslip" \| pii_gate.py --stdin --no-llm` | `"level":"medium"` (LLM-confirm skip) |
| T5 clean text | `echo "Quote for AC maintenance" \| pii_gate.py --stdin --no-llm` | `"pii": false, "level":"low"` |
| T6 credit card | `echo "Card 4532015112830366" \| pii_gate.py --stdin --no-llm` | Luhn-valid → `"credit_card"` |
| T7/T8 LLM path | keyword text with LLM confirm (warm) / cold | warm ~4s, cold ~30s (first load) |
| T9 watchdog | `~/.hermes/scripts/hybrid_watchdog.sh` | exit 0, silent (healthy) |
| T10 cost | `python3 ~/.hermes/scripts/hybrid_cost_report.py` | $ + model usage |
| E2E | `time hermes chat -q "Reply with exactly one word: OK" -m local-fast` | response from local model, ~30-45s |

Baseline (2026-09-01): cloud $4.85/week, 393M cache-read tokens; local calls
`estimated_cost_usd = 0/None` → rising `api_call_count` with near-zero cost =
local doing the heavy lifting.

## Pitfalls

- **Cold load is 31s, warm is 4s.** Keep-alive 30m + preload; never benchmark
  cold. Warmup trick: one tiny `/api/generate` call with `keep_alive:"30m"`.
- **Overlapping PII spans corrupt redaction** (`[REDACTED:sa_id]phone]`) — fixed
  by merge-first logic in `redact()`. If you touch it, re-run T3.
- **Gateway restart from inside the gateway is impossible** — watchdog is
  alert-only for hermes-gateway (systemd auto-restarts it); only Ollama gets
  restarted by the watchdog.
- **Cron `script` field takes a filename** (`hybrid_watchdog.sh`), not a path —
  full path causes creation failure.
- **Never hand-edit `~/.hermes/config.yaml`** — `hermes config set` only; a stray
  indent breaks the live gateway. The file holds API keys → never print it raw.
- **`hermes config get` may show `***` for some values** — verify via the alias
  list, not the value.
- **Custom provider needs the exact key name** (`key_env`) from the plugin
  source; Ollama needs no key at all (local).
- **2 vCPU/11GB ARM ceiling:** 7B-class smooth, 3B fast; local quality << frontier
  — right for classify/extract/summarize/score/normalize, wrong for hard code or
  deep reasoning (route those cloud).
- **qwen itself masks PII partially** (e.g. phone) on top of the gate — double
  protection, expected.
- **A loaded model is real RAM, not free capacity.** An idle embedding runner held
  **1433 MB** for 1.5 h (RAM 29%, swap 7.7 GB) while the keep-alive kept it warm; unloading it
  returned ~1.4 GB. Never "fix" a RAM alert by *raising* keep-alive back to 30m — lower it and
  accept the cold load, or the resident-model pressure comes straight back.
- **Every memory-heavy unit needs a swap ceiling** (`MemorySwapMax`), not just a memory cap:
  `omniroute`/`n8n` 256M, `infra-dash` 128M, and the **gateway user manager
  (`user@1001.service`) 4G** — that unbounded slice was the largest single swap source (2.6 GB).
  `systemctl set-property <unit> MemorySwapMax=…` persists via
  `/etc/systemd/system.control/` (no `--runtime`); confirm with
  `systemctl show <unit> -p MemorySwapMax --value` — `infinity` means it did not land.
  A ceiling may sit on an **ancestor slice** (ollama's is on `ollama.slice`), so walk parents
  before calling a unit unbounded.
- **Prune models you no longer use** (`ollama rm llava:7b` → models dir 9.5 GB → 5.1 GB) and pull
  on demand instead of keeping a vision model resident "just in case".
- **Any script/check that drives ollama must not assume a login shell.** Checks run under a bare
  env: resolve the binary absolutely (or normalize `PATH`) and pass `HOME=/usr/share/ollama` when
  the CLI must read the model manifest — otherwise the check silently degrades to "absent".

## Extending (expert path)

- New local task → add prompt in `hybrid_router.py` `PROMPTS` + name in
  `LOCAL_TASKS`; re-run T-routes.
- New PII type → add regex to `pii_gate.py` `PATTERNS` (Luhn if card-like); re-run T1–T6.
- Alert channel → watchdog reads `TELEGRAM_BOT_TOKEN` from `~/.hermes/.env`,
  chat `HYBRID_ALERT_CHAT` (default 8843884232).
- Local vision/embeddings: `ollama pull bge-m3` (embeddings for the RAG stack).
  Pull a vision model **only while you need it** — `llava:7b` was removed 2026-09-21
  (≈4.4 GB disk + 1.4 GB RAM when resident). Route those tasks local the same way.
