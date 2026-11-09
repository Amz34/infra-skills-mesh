# Cleanup vs Speed — worked case (2026-09-15, hermes-vnic)

## The user's question
"Phir bhi infra slow hai — irrelevant files ya cache delete karenge?"
(slowness complaint **bundled with** a cleanup request — the trap is answering only the cleanup half.)

## What was actually reclaimed (~4.9GB)
| Target | Before | After |
|---|---|---|
| journald | 284M | 76M (`journalctl --vacuum-size`) |
| /var/log | 941M | 443M (rotated `syslog.1` alone = **438M**, produced by a crash-looping gateway) |
| /tmp | 3.5G | ~0 (mtime >2d: old chrome test profiles, OCR temp, devtunnel binary) |
| apt cache | 127M | 1.3M |
| npm cache | 841M | 530M (`npm cache clean --force`; `~/.npm/_npx` kept) |

Result: `/` went from ~84G free to **89G free (55% used)** — i.e. disk pressure was never the problem.

## Deliberately NOT touched (say so in the report)
- Backups: ~9.5G local + Drive copies (data, never "trash")
- Docker images in use by running containers
- `__pycache__` — deleting it is a one-off stall; the next import pays the rebuild
- venvs / `.local/share/uv` / global node_modules backing live services
- No service was stopped or killed as part of "cleanup"

## The honest verdict (this is the deliverable)
Disk cleanup here gave **~0 speed improvement** — it is hygiene. Measured 07:35 UTC the same day:

- RAM: 5.7G resident + **3.5G in swap/zram**; kernel continuously swapping (≈38 in / 54 out per sec)
- `vmstat`: **wa (iowait) 42–46%** while `us` (user CPU) only 4–12%
- load **1.5–2.0 on 2 vCPU**, constant `b=1`, one D-state kernel worker
- ⇒ CPU idle + waiting on memory IO = the felt "slowness". ~30 long-running services (6 hermes gateways, omniroute, chrome automation, n8n, open-webui, 2×mysql, 2×wordpress, postgres, rsshub) on 2 vCPU / 12GB.

## Framing rules that worked
1. Answer the cleanup question with numbers, then immediately separate it from the speed question.
2. Never let a cleanup report imply it fixed slowness — the user tests it and feels nothing, which burns trust.
3. Give the real cause (memory pressure) + the free remedy (OCI Always Free ARM = 4 OCPU / 24GB; box ran at half) + the trim option (stop un-used heavy services), and ask which lever to pull.
4. Credential/secret rule still applies throughout: Slack `.env` token values never printed — masked/`md5sum`-compared only.

## Related
- `saas-performance-diagnosis` → host triage step + `references/disk-vs-memory-host-triage.md`
- `infra-hardening-crashproof` → Gateway Crash-Loop (fix the emitter *before* vacuuming its logs)
- `oci-cloud-vm-ops` → free shape headroom + resize path
