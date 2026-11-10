---
name: rust-disk-space-killer
description: High-performance enterprise disk space discovery and cleanup suite built on Rust binaries (dust and kondo) to reclaim tens of gigabytes from stale build caches, target directories, and node_modules across VM infra.
---

# rust-disk-space-killer

Enterprise-grade, compiled Rust toolchain for VM and CI/CD disk space optimization, auditing, and automated garbage collection.

## Core Capabilities
- **Real-Time Visual Profiling (`dust`):** Rust-based instant disk space visualization with hierarchical tree representations without waiting for unbounded `du -sh` runs.
- **Cross-Ecosystem Build Pruning (`kondo`):** Native Rust cleanup engine supporting 20+ project formats:
  - Rust: `target/` directories
  - Node.js: `node_modules`
  - Python: `.venv`, `__pycache__`, `.pytest_cache`
  - JVM: `.gradle`, `build/`, `target/`
  - C/C++: `build/`, CMake caches
- **Zero Runtime Dependencies:** Standalone compiled Rust binaries running with sub-second execution speed.

## Quick CLI Execution
```bash
# 1. Visual disk audit (Top 10 space consumers)
dust -d 1 -r -n 10 $HOME

# 2. Dry-run audit for stale project build artifacts older than 14 days
kondo -n -o 14d /home/ubuntu

# 3. Clean all build caches older than 14 days without prompt
kondo -a -o 14d /home/ubuntu

# 4. Immediate space recovery check
df -h /
```
