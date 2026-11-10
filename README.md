# ⚡ Enterprise Infrastructure Skills Mesh (`infra-skills-mesh`)

> **Autonomous 2-Tier Dynamic Skill Routing & Execution Engine for AI Coding Agents.**  
> Eliminates context-window token bloat by dynamically resolving and injecting only the exact skill spec required for any given engineering task.

[![Skills Count](https://img.shields.io/badge/skills-293%2B-blue.svg)](#)
[![Unified Triggers](https://img.shields.io/badge/unified__triggers-205-cyan.svg)](#)
[![CI Validation](https://img.shields.io/badge/enterprise__ci-passing-brightgreen.svg)](#)
[![Token Reduction](https://img.shields.io/badge/token__reduction->95%25-orange.svg)](#)

---

## 🎯 The Problem Solved

Injecting 293+ raw skill descriptions into every agent prompt wastes **15,000–35,000 tokens per roundtrip**, slows down inference, and causes LLMs to hallucinate between overlapping tools.

`infra-skills-mesh` solves this with a **2-Tier JIT Architecture**:
1. **Tier 0 (0 Tokens Overhead)**: High-speed local BM25 + taxonomy trie evaluates prompt intent in `< 1ms`.
2. **Tier 1 (Minimal Context Injection)**: Dynamically injects *only* the single matching `SKILL.md` into the agent's active memory.

---

## 🏗 Directory Architecture

```
infra-skills-mesh/
├── bin/
│   └── ghskill                # High-pitch CLI router & injection engine
├── registry/
│   ├── unified_index.json     # 205 unified trigger hubs & alias maps
│   └── canonical_index.json   # 293 full skill specs and use cases
├── skills/                    # 26 Enterprise categories
│   ├── devops/                # (70 skills)
│   ├── productivity/          # (36 skills)
│   ├── software development/  # (31 skills)
│   ├── creative/              # (23 skills)
│   ├── research/              # (18 skills)
│   ├── autonomous-ai-agents/  # (17 skills)
│   ├── mlops/                 # (15 skills)
│   └── ...                    # (19 more domain categories)
└── .github/workflows/
    └── ci.yml                 # Automated validation & integrity gate
```

---

## 🚀 CLI Usage (`ghskill`)

### 1. Route Intent to Matching Skill
```bash
ghskill route "audit my attack surface and crashproof daemon"
```
**Output:**
```
⚡ [GHSKILL ROUTER] Recommended Skills for Task: "audit my attack surface and crashproof daemon"
══════════════════════════════════════════════════════════════════════
1. Unified Suite: /audit (Confidence: 124)
   Prompt Action : Activate /audit for attack-surface-self-audit
   Subskills Included: attack-surface-self-audit, capability-gap-audit, project-state-audit
👉 Fast Trigger Token: /audit
```

### 2. Inject Targeted Skill Directly into Agent Prompt
```bash
# Pipes minimal SKILL.md directly into context (95% token savings)
ghskill inject "scrape web data"
```

### 3. List Hubs by Category
```bash
ghskill list --category DEVOPS
```

---

## 🛡 Quality & Compliance
- **EGM & REA Standardized**: Every skill includes falsifiable verification gates and single-line actionable use cases.
- **Enterprise Pre-Commit Validated**: Clean code, zero UI slop, zero credential leaks.
- **Integrated Cockpit**: Live telemetry rendered in [AeroFleet Terminal PWA](https://hermes-vnic.tail34b7f2.ts.net:8970/).

---

Part of [my always-on agent stack](https://github.com/Amz34) · [Awesome Agent Infrastructure](https://github.com/Amz34/awesome-agent-infrastructure) (135 live-checked building blocks).
