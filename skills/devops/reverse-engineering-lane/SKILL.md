---
name: reverse-engineering-lane
description: Use when triaging or decompiling a binary/APK/firmware.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [reverse-engineering, ghidra, mcp, malware, android, binary-analysis]
    related_skills: [mcp-tool-servers, agentic-tooling-research, untrusted-code-sandbox-lane]
---

# Reverse-Engineering Lane (rekit + Ghidra + REA MCP)

Offline RE lane on this aarch64 VM: static toolkit, Ghidra headless decompilation, and two MCP
surfaces (REA stdio, re-connector HTTP). Full detail: `~/brains/ops/knowledge/infra/reverse-engineering-lane.md`.

## When to Use
- Ek binary/ELF/PE/Mach-O, APK, firmware image, JS bundle, PCAP ya YARA/capa/floss scan karna hai.
- Decompilation chahiye (pseudo-C) — Ghidra headless.
- Agent (Hermes/Codex/Claude Code) ko RE tools MCP se dene hain.

## Env (har Ghidra/REA/apktool call se pehle)
```bash
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-arm64
export GHIDRA_INSTALL_DIR=/home/ubuntu/ops/vendor/re/ghidra_12.1.4_PUBLIC
```

## Fastest path — rekit (13 subcommands)
```bash
~/.venvs/re/bin/python ~/ops/re/rekit/rekit.py triage /bin/ls      # also: strings iocs disasm
~/.venvs/re/bin/python ~/ops/re/rekit/rekit.py apk    ~/ops/re/samples/fdroid.apk
~/.venvs/re/bin/python ~/ops/re/rekit/rekit.py firmware fw.bin      # js pcap yara capa floss ghidra health
~/ops/re/tests/run_rekit_suite.sh                                   # 12-test smoke suite
```

## Ghidra headless (native arm64 decompiler already built)
```bash
GH=$GHIDRA_INSTALL_DIR
$GH/support/analyzeHeadless /tmp/ghproj PROJ -import /bin/ls \
  -scriptPath ~/ops/re/rekit -postScript ListFunctions.java
$GH/support/analyzeHeadless /tmp/ghproj PROJ -process ls -noanalysis \
  -scriptPath ~/ops/re/rekit -postScript DecompileAll.java /tmp/ls.c
wc -l /tmp/ls.c     # /bin/ls => 412 funcs, ~18.7k lines
```
Scripts live in `~/ops/re/rekit/*.java`. If the decompiler binary is ever missing:
`Decompiler/os/linux_arm_64/decompile` (public Linux release ships x86_64 only). Rebuild from
`Decompiler/src/decompile/cpp` (`ghidra_opt`) and copy; Makefile needs `OSDIR=linux_arm_64`.

## MCP surfaces
- **re-connector (HTTP, always-on):** `http://127.0.0.1:8798/mcp` — 13 tools
  (`re_health`, `re_triage`, `re_strings`, `re_iocs`, `re_disasm`, `re_apk`, `re_firmware`, `re_js`,
  `re_pcap`, `re_yara`, `re_capa`, `re_floss`, `re_ghidra`). Unit: `systemctl --user status re-connector`.
- **REA (stdio, 125 tools):** wrapper `~/ops/re/rea-mcp.sh`. Flow: `open_binary` → `list_procedures`
  / `procedure_pseudo_code` / `batch_decompile` → `close_binary`.
- Probe pattern (real payload, not vendor errors):
  `~/.hermes/skills/devops/mcp-tool-servers/scripts/mcp_stdio_call.py <bin> <tool> '<json>'`.

## REA aarch64 gate — RESOLVED in rea-agents 6.4.0 (no patch needed)
6.4.0 maps Linux arm64 natively (`linux: {x64:"linux_x86_64", arm64:"linux_arm_64"}`) and verifies
`os/linux_arm_64/decompile` by its ELF header instead of assuming the host arch.
Verified 2026-10-12 on this A1 aarch64 box: `rea doctor` → `ghidra-native_decompiler: healthy`;
`rea decompile tiny --procedure main --provider ghidra` → rc=0 with real C; MCP tool count 125 → 170.
`~/ops/re/rea-arm64-patch.py` is **OBSOLETE — do not re-apply**. Rollback tarball:
`~/ops/re/rollback/rea-agents-4.1.0.tgz`. `hopper`/`ida` checks fail by design (not installed).

## Pitfalls
- **Never ripgrep all of `rea-agents/dist/`** — `generatedMcpToolCatalog.js` is 6.6 MB of generated
  JSON; grep only `dist/ghidra/*.js` or use `search_files`.
- **Big inline shell commands get blocked** (≥2 KB hardline, some quoting patterns). Write
  `~/ops/tmp/<name>.py` and run it; never inline a heredoc-of-doom.
- **Naam collision pitfall**: `procedure_pseudo_code` ka validator ek function naam accept nahi karta:
  `add` → `{"error":{"code":"invalid_request","category":"invalid_input","retryable":true}}` (address
  form `0x7d8`, `FUN_000007d8`, `tiny::add` bhi fail). Baaki sab names (`main`, `sub`, `mul`,
  `_start`, `call_weak_fn`, `FUN_*`) theek chalte hain — 10/11 internal functions decompile ho gaye.
  Workaround: us symbol ke liye Ghidra headless use karo
  (`analyzeHeadless /tmp/p P -import <bin> -scriptPath ~/ops/re/rekit -postScript DecompileAll.java out.c`).
- **Exact names** `list_procedures` ke `result[].value` se lo; `procedure.external==true` aur
  `thunk==true` skip karo (external = PERFECT, `__libc_start_main` type entries).
- **`keystone-engine` needs `pip`, not `uv`**: `uv pip install qiling` hangs/fails building it
  (py3.12/aarch64), while `~/.venvs/re/bin/python -m pip install qiling` builds 0.9.2 fine →
  qiling 1.4.6 OK.
- REA ka `java` probe false-negative de sakta hai: `rea analyze` ki provider-inspection mein
  `java,false,runtime_missing` dikh sakta hai jabki `rea doctor` healthy hai aur Ghidra run
  theek chalta hai (load ke waqt probe timeout). Blocker na samjho — `open_binary` →
  `procedure_pseudo_code` flow se verify karo.
- `/mcp` pe readiness GET-poll mat karo (endless SSE) — TCP port check, phir `initialize` POST.
- Decompiler output file me likho, terminal me 18k lines print na karo.
- Dynamic analysis: `gdb-multiarch`, `ltrace`, `strace`, `qemu-user` (`qemu-aarch64 -L /usr/aarch64-linux-gnu ./bin`),
  `afl-fuzz` (tested: afl++ 4.09c; smoke = `AFL_SKIP_CPUFREQ=1 AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1
  AFL_NO_UI=1 afl-fuzz -n -i in -o out -V 20 -- ./bin @@`), `qiling` (venv `~/.venvs/re`).
  Native samples direct chalti hain; x86-64 → `qemu-x86_64`.
- **REA Ghidra calls need free CPU.** On this 2-OCPU box a concurrent heavy load (load avg >20)
  pushes `list_procedures` past REA's internal cap (~426 s) and the tool returns error — it is a
  timeout, not a broken provider. Verify against a small binary and check the live runtime dir
  `/tmp/rea-ghidra-*/` (`ghidra.log`, `script.log`) before blaming the provider; the dir is deleted
  when the run finishes. Same load makes REA's `java` probe report `runtime_missing` on an
  otherwise healthy JDK.
- Probe scripts redirected to a file: run with `python -u`, warna stdout block-buffered rehta hai
  aur output sirf process exit pe dikhta hai.
- Android: `apktool` 3.0.3 user-level (`~/.local/bin`) shadows system 2.7.0.

## Verify
```bash
~/ops/re/tests/run_rekit_suite.sh
curl -s -o /dev/null -w '%{http_code}\n' --max-time 5 127.0.0.1:8798/mcp   # non-2xx/000 = up
python3 ~/ops/scripts/autonomy_audit.py                                   # 0 block
```
