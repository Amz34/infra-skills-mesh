# Agentic Next-Levels — Research Bank (2026-08-25, verified)

Source: GitHub API (star counts verified 2026-08-25) + X articles (full web_extract reads).
Roadmap doc: `/home/ubuntu/ops/kb/agentic-next-levels.md` (four-plane audit tables included).

## GitHub repos (verified ⭐)

| Repo | ⭐ | Description | Use for our stack |
|---|---|---|---|
| obra/superpowers | 277,349 | Agentic skills framework & software development methodology | **Hermes supported** — spec→plan→subagent dev→review→verify chain; plugin install for Hermes+Claude Code+Codex (Tier 2) |
| affaan-m/ECC | 243,043 | Agent harness performance optimization: skills, instincts, memory, security | `.hermes` support built-in, MIT — harvest battle-tested configs (Tier 3) |
| msitarzewski/agency-agents | 147,935 | Complete AI agency: 230+ agent personas, 14 divisions | Harvest PM/sales/marketing personas for client agent profiles (Tier 2) |
| bytedance/deer-flow | 80,837 | Open-source long-horizon SuperAgent harness (researches, codes, creates) | Checkpointed multi-hour autonomy pattern (Tier 3) |
| mem0ai/mem0 | 64,002 | Universal memory layer for AI agents | Self-host on Oracle VM for client bots per-user memory (Tier 2); pattern: ADD-only + entity linking + temporal reasoning |
| raga-ai-hub/RagaAI-Catalyst | 16,151 | Python SDK: Agent AI Observability, Monitoring, Evaluation | Tracing + cost/latency/failure dashboard for cron/delegation runs (Tier 3) |

Also seen: punkpeye/awesome-mcp-servers 92.8K⭐ (MCP server collection — universal adapter layer), mlflow agent evaluation 27.7K⭐, zhayujie/CowAgent 46.7K⭐ (agent harness, plans tasks/runs tools).

## X articles (full read)

### 1. @yongkyun_lee — "The Architecture of Multi-Agent Systems" (Aug 2026)
URL: https://x.com/yongkyun_lee/article/2090202527732281596
- **4 planes**: Control (kaun act kare) / Communication (context kaun si boundary cross kare) / State (state kahan store ho) / Verification (output kaun accept kare).
- "Before adding another agent, identify which plane the current system cannot handle."
- "Agent count should follow **evidence diversity**, not process count — 2 diverse agents ≥ 16 homogeneous agents."
- Article me **Hermes Agent Kanban (NousResearch)** khud cited — hamara harness is edge pe hai.

### 2. @sairahul1 — "How To Build AI Agents in 2026 (That Actually Work)"
URL: https://x.com/sairahul1/article/2064988918630736353
- 5 building blocks: **Brain, Tools, Memory, Loops, Verification**.
- "Agents fail because they never check their own work — verification step: 60% → 90% reliability."
- **Progress-note habit**: har step pe 4 lines — STEP COMPLETED / KEY DECISIONS / CURRENT STATE / NEXT STEP.

### 3. Context snippets (search hits)
- @akshay_pachaar — subagents vs agent teams; large-scale agentic coding.
- @BrianRoemmele — plan-mode dev: codebase survey → structured approach → critique acceptance → clean diff.
- @ValaAfshar — IDC: 40% of G2000 roles AI agents ke saath collaborate by 2026.
- @rossmatican — agentic AI security: demo → product guardrails.

## Tiered plan (as delivered)

- **Tier 1 (done 2026-08-25)**: Verification gate (LinkedIn cron already had step 4; now standard) + progress-note embedded in LinkedIn cron prompt (verified in jobs.json) + four-plane audit doc (`~/ops/kb/agentic-next-levels.md`).
- **Tier 2 (0₹)**: superpowers plugin (Hermes+Claude+Codex), agency-agents personas harvest, mem0 self-host.
- **Tier 3 (~free)**: RagaAI observability, ECC configs harvest, deer-flow long-horizon pattern.

## Implementation notes (Tier 1 execution details)

- Long cron prompt edit: `~/.hermes/cron/jobs.json` → `d['jobs']` list, field `prompt` (job_id = `id` field, not `job_id`). `cronjob list` sirf preview deta hai. Exact copy → append section → `cronjob action=update` (full prompt pass karo) → jobs.json read-back verify (`PROGRESS-NOTE in prompt: True`).
- LinkedIn engine cron (id cf43d1de0d7a, `0 13 * * 3,4`, continuity=true): prompt ab 3994 chars — BUILD/UPLOAD/POST/Verify + PROGRESS-NOTE + DELIVERY sections.
