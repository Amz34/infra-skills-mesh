---
name: repo2prompt-local
description: Reverse a repo/site into a build brief privately, offline.
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [reverse-engineering, prompts, privacy, github, offline]
    related_skills: [github-repo-management, codebase-inspection, client-website-delivery]
---

# repo2prompt — local reverse-prompt generator

Private, self-hosted replacement for gitreverse.com. Reads a GitHub repo (public **or private**)
or a live website and writes a **reconstructed build prompt + grounded engineering brief** (real
file map, mechanisms, gaps, rebuild plan).

## When to use
- Client-confidential repos/sites: gitreverse.com publishes every reverse to its public `/library` → never submit client work there.
- Competitor or OSS architecture teardown in <1 min, grounded in real files.
- Turning an existing site/repo into a starting brief for Claude Code / Codex / Hermes builds.
- Client-website work: `--url` mode gives a page-structure + stack brief before rebuilding.

## Location / install
- Tool: `/home/ubuntu/tools/repo2prompt/repo2prompt.py` (stdlib only, no deps)
- Command: `~/.local/bin/repo2prompt` (symlink; add `~/.local/bin` to PATH if missing)
- Docs: `/home/ubuntu/tools/repo2prompt/README.md`
- Cache of raw evidence: `~/.cache/repo2prompt/*.json`

## Core commands
```bash
repo2prompt owner/repo                       # quick (metadata + tree + README)
repo2prompt owner/repo --include-files       # deep: reads real source files (best quality)
repo2prompt owner/repo --include-files --out ~/prompts/x.md
repo2prompt ~/local/checkout --include-files # local dir
repo2prompt --url https://site.com           # website mode
repo2prompt owner/repo --backend ollama      # fully offline generation
```
Flags: `--backend auto|ollama|deepseek|gemini|openai`, `--model`, `--max-file-chars` (90k),
`--max-tree`, `--max-tokens` (2600), `--temperature`, `--out`, `--no-cache`, `--print-evidence`.
Env: `R2P_BACKEND`, `R2P_OLLAMA_MODEL`, `OLLAMA_HOST`, `DEEPSEEK_API_KEY`, `GOOGLE_API_KEY`
(read from process env and `~/.hermes/.env`; never echoed).

## Backends / cost
- `auto` (default): deepseek → gemini → ollama. Deepseek run = ~100k chars input ≈ fractions of a cent, 9–40 s.
- `ollama` = true offline (no bytes leave the VM) — use for anything client-confidential.
- Private repos fetch through the local `gh` CLI session, so no token handling in the script.

## Pitfalls (learned on this VM)
- **Ollama dies under memory pressure.** With ~2 GB available, `qwen2.5:7b-64k` never loads and the
  request hangs. The script preflights `/api/tags` and fails fast with a clear message; free RAM
  (headless chrome ~1.7 GB, hermes ~1.4 GB are the top hogs) or use `--backend deepseek`.
- Private repos often have **no README** (404) → brief is thin unless `--include-files`.
- Website mode sees rendered HTML only: JS-heavy sites yield weak evidence; a repo run is stronger.
- Output is a **plausible new brief**, not the author's original prompt — always verify against code.
- For private repos, decide deliberately: `--include-files` with a cloud backend sends code off-box.

## Verify it still works (cheap, ~10 s)
```bash
repo2prompt Amz34/anatomy-explorer-demo            # private repo path
repo2prompt --url https://gitreverse.com           # website path
```
Expect: `[i] evidence: N chars | backend=auto` then a `## Reconstructed build prompt` section and a
`## Grounded engineering brief` with a real file map.
