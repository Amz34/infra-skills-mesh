# Memory containment on a small box (2 vCPU / 11–12 GB) — verified 2026-09-21

Real incident: RAM available fell to **29%**, swap **7.7 GB used** (zram 5.9 GB + disk 1.7 GB),
load 1.15, top5 RSS 2805 MB — the box was thrashing although nothing had crashed yet. The cause
was **not a leak**: unbounded swap ceilings plus one *idle* model left resident.

## What actually consumed it

| Culprit | Detail |
|---|---|
| `llama-server` 1433 MB | an **idle** ollama runner — the RAG embedding model, loaded 1.5 h earlier (keep-alive still counting). Unloading it alone returned ~1.4 GB. |
| `omniroute.service`, `n8n.service` | `MemorySwapMax=infinity` |
| `user@1001.service` | the Hermes gateway user manager had **no swap ceiling at all** — the single largest swap source (2.6 GB) |
| `llava:7b` | ≈4.4 GB of weights installed but unused → `ollama rm` took the models dir 9.5 GB → 5.1 GB |

## Fixes (all persistent)

```bash
sudo systemctl set-property omniroute.service  MemorySwapMax=256M
sudo systemctl set-property n8n.service        MemorySwapMax=256M
sudo systemctl set-property user@1001.service  MemorySwapMax=4G    # cap the whole user slice
sudo systemctl set-property infra-dash.service MemorySwapMax=128M  # found BY the checker below
echo -e '[Service]\nEnvironment="OLLAMA_KEEP_ALIVE=5m"' \
  | sudo tee /etc/systemd/system/ollama.service.d/keepalive.conf
sudo systemctl daemon-reload && sudo systemctl restart ollama
ollama rm llava:7b
```

`systemctl set-property` **without** `--runtime` writes `/etc/systemd/system.control/*.conf`, so it
survives reboot — always confirm with `systemctl show <unit> -p MemorySwapMax --value` (`infinity`
means the cap did not land).

Result: RAM available **29% → 43%**, top5 RSS **2805 → 1678 MB**, no crash.

## Keep-alive is a policy choice, and it must match the box

`OLLAMA_KEEP_ALIVE=30m` (latency-first) is right only when RAM is not shared with a gateway. On this
box the gateway + RAG stack share the same 11 GB, so the containment value is **5m** (idle unload);
the cost is a ~31 s cold load on the next local call. Do not "fix" a RAM alert by raising keep-alive
back to 30m — that recreates the resident-model pressure; lower it and accept the cold load.

## Rule: contain, don't measure

A watchdog that prints "RAM 29%" every 15 min changes nothing. Every memory-heavy unit needs a
**swap ceiling**, and the invariant is *"the ceiling still exists"*, not *"usage is low"*. Encode it
so it cannot silently regress: `~/ops/scripts/mem_containment_check.py` (5 invariants — ollama slice
swap ceiling, no memory-heavy service (RSS > ~150 MB) with unbounded swap, user-manager ceiling,
keep-alive ceiling, no oversize local model). It stays green on a busy box and fails only when a
containment guarantee disappears.

Two traps this checker taught:

1. **A ceiling may live on an ancestor slice.** ollama's cap sits on `ollama.slice`, not on the
   service — walk parent slices (`eff_cap()`), never judge the unit alone.
2. **Check scripts run with a bare env** (the Layer-3 verifier calls them that way): resolve
   binaries absolutely / normalize `PATH`, and pass the CLI its own `HOME` (`HOME=/usr/share/ollama
   ollama list`) or the model check silently degrades to "absent".

Companion watchdog rules and the QA-side philosophy: `infra-dashboard-ops` →
`references/qa-invariant-lessons.md`.
