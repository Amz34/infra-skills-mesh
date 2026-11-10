---
name: rtk-token-killer
description: High-performance terminal output compression proxy and agent hook for devops workflows, cutting LLM context consumption by 60-90% on bash tool runs.
---

# rtk-token-killer

Deterministic Rust-based command-line output proxy (`rtk`) designed to filter and compress terminal and test execution output before feeding it into LLM agent context windows.

## When to Use
- Agentic test suite execution (`pytest`, `cargo test`, `npm test`) where passing test noise bloats context.
- Git operations (`git status`, `git diff`, `git log`) in repetitive agent turns.
- Large recursive directory walks or search queries (`find`, `grep`, `rg`).
- High-frequency CI/CD and terminal tool-use loops where context window consumption must be minimized.

## Core Capabilities
- **Sub-10ms Overhead:** Zero-dependency Rust binary compiled for Linux/Darwin.
- **Selective Retention:** Isolates error traces, failed assertions, and dirty state while collapsing hundreds of passing lines into single-line counters.
- **Multi-Agent PreToolUse Hooks:** Supports Google Antigravity, Claude Code, Cursor, Windsurf, Trae, Cline, and custom runners.
- **Cost Telemetry:** Live savings tracking via `rtk gain`.

## Execution Patterns
```bash
# 1. Install & path configuration
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/develop/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# 2. Configure agent PreToolUse hook
rtk init --agent antigravity
rtk init -g

# 3. Direct execution proxying
rtk git status
rtk cargo test
rtk npm test

# 4. Telemetry inspection
rtk gain
```
