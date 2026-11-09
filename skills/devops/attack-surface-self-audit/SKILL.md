---
name: attack-surface-self-audit
description: Use when auditing or hardening a VM's real attack surface.
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [security, hardening, audit, recon, verification]
    related_skills: [agent-autonomy-governance, infra-hardening-crashproof, secrets-vault-ops]
---

# Attack-Surface Self-Audit (measured, fix-first, falsifiable)

## When to use
- "audit/QA our infra", "kya exposed hai", "harden the box", or analyzing someone else's breach writeup and mapping it to OUR box.

## Core rules
1. **Measured, not narrated** — every claim = command output.
2. **Fix-first** — live exposure milte hi remediate karo (stop/mask/rebind) BEFORE writing the report.
3. **Falsifiable artifact** — the audit must be able to FAIL: `--selftest` injects a real defect (e.g. a 0644 secret) and must fail closed. Always-green audit = untrustworthy.
4. **Honest FAIL** — never downgrade FAIL to PASS for a green run; use explicit ACCEPTED entries with written rationale, excluded from the exit-code gate.
5. **No secrets in output** — key NAMES only, values `[REDACTED]`; collectors must never print values.
6. Idempotent + re-runnable; exit code = gate (0 = no FAIL, non-zero = FAILs found).

## Steps
1. **Recon (scripted; append everything to one evidence file)**
   - `ss -ltnp` listeners — wildcard `0.0.0.0` / `*` / `[::]` = candidate exposure
   - firewall ground truth: `nft list ruleset`, `iptables -S INPUT`
   - tunnels/proxies: `ps -eo pid,args | grep -E 'cloudflared|ngrok|ssh -R'` → note each TARGET `host:port` (loopback targets = backends safe to rebind)
   - external view: probe the public hostnames from OUTSIDE the box, not from the box
   - identity/privilege: `sudo -n -l`, sshd config, `stat -c '%a %n'` on secret files
2. **Classify** each surface: EXPOSED (public, no auth) → EXPOSED-AUTHED → LOOPBACK-ONLY → INTERNAL-WILDCARD (defense-in-depth gap) → NOT-PRESENT
3. **Remediate now** (backup → change → verify → rollback on failure):
   - proxy tunnels: `systemctl stop` + move unit to `<name>.disabled-<YYYYMMDD>` + `ln -sf /dev/null <unit>` (plain `mask` fails when the unit file exists)
   - wildcard binds: rebind to loopback — first check dependents (`grep -rn <port>` in configs/connectors), then systemd drop-in `Environment=OLLAMA_HOST=127.0.0.1:11434` / unit `ExecStart ... --host 127.0.0.1`
   - parsers/web servers: prefer DENYLIST coder policy when the engine silently ignores allowlist form (ImageMagick 6 ignores allowlist → denylist works)
4. **Write the audit** (`~/ops/verify/attack_chain_audit.py`): checks `AC-01..N` via `add(id, title, status, evidence, fix)`; statuses PASS/FAIL/WARN/ACCEPTED; `--selftest` flag; exit 0 only when no FAIL.
5. **Prove the delta** — run selftest, then real run, then re-run after each fix; keep before/after evidence files.

## Pitfalls (learned the hard way)
- **Blind I/O**: long stdout can come back truncated/empty → scripts write evidence to FILES and report the verdict via **distinct exit codes** (bitmask = one bit per check). Keep stdout ≤3 lines.
- `grep -c` / `wc -l` output sometimes doesn't render → write to `/tmp/x.txt` then `read_file`.
- Large shell heredocs / `base64` echoes truncate → use the file-write tool instead.
- Broad `grep -rn` across many dirs times out (124) → narrow per-file greps with `timeout 60`.
- Root-owned systemd drop-ins need `sudo install -m 644 /tmp/x.conf <path>`; the patch tool only writes user-writable files.
- Do NOT rebind a bind hard-coded inside a client's source file (`server.py`) without owner input — do the clean drop-ins first.
- A check added after the baseline shows as REGRESSION noise → record the baseline row whenever a gap is knowingly accepted.
- Multi-worker apps need ~20s to boot: verify with a delayed `curl` before declaring the rebind broken.

## Verification
- `python3 ~/ops/verify/attack_chain_audit.py --selftest` → exit 0
- real run → FAILs only for items explicitly accepted-with-rationale
- after rebind: `ss -ltn` shows `127.0.0.1:PORT`, unit `is-active`, and `curl 127.0.0.1:PORT/...` returns 200
