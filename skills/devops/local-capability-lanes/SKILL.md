---
name: local-capability-lanes
description: Use when running local doc/search/ML/decision lanes.
version: 1.0.0
author: Aamir's infra (Hermes agent)
license: MIT
metadata:
  hermes:
    tags: [local-first, search, documents, tabular-ml, decisions, cpu-governor]
    related_skills: [sqlite-fts5-multilingual-search, docx, xlsx, powerpoint, chromadb-rag-ops]
---

# Local capability lanes (sfs / docgen / tabpredict / decide / heavy)

Five lanes built on this VM (2026-10-12, from the "solo devs clone big tech software" gap audit).
All are **local, zero-cost, offline**; none call a paid API. All live under `~/ops/` with a
`README.md` next to them, and every one has a `selftest`.

| Lane | Path | Entry point | What it gives us |
|---|---|---|---|
| `sfs` | `~/ops/filesearch` | `sfs` (`~/.local/bin/sfs`) | hybrid file search: SQLite **FTS5** + ONNX **semantic** over ~11.7k files / ~71k chunks |
| `docgen` | `~/ops/docgen` | `docgen` (`~/.local/bin/docgen`) | read/write real DOCX/XLSX/PPTX + headless LibreOffice → **PDF** |
| `tabpredict` | `~/ops/tabular` | `tabpredict` (`~/.local/bin/tabpredict`) | tabular prediction: sklearn (live) + TabPFN (installed, licence pending) |
| `decide` | `~/ops/decisions` | `~/ops/decisions/decide.py` | calibrated YES/NO gate from local ollama logprobs → ACCEPT/REJECT/**ESCALATE** |
| `heavy` | `~/ops/infra` | `~/ops/infra/heavy.sh`, `~/ops/infra/load_report.sh` | CPU-quota + memory-pressure governor for bulk lanes |

## When to use which

- "file/docs kahan likha tha" / meaning-based recall → **`sfs search`** (`--mode sem|lex|auto`).
- Anything producing a client document, invoice, deck, bilingual PDF → **`docgen`**.
- Score leads, churn, prices — any CSV with a target column → **`tabpredict`**.
- A go/no-go that must be defensible, cheap and logged → **`decide.py`** (never in a hot UI path).
- Any bulk CPU/RAM job (embedding, pip, whisper, Ghidra, du scans) → wrap in **`heavy.sh`**.

## Commands

```bash
# --- sfs: local hybrid file search -------------------------------------------------
sfs stats                                     # chunks, vectors, db size
sfs search "the server dies when memory runs out"            # hybrid (auto)
sfs search "textbee sms gateway" --mode lex -k 5             # keyword only
sfs search "gateway oom score" --mode sem --path ~/ops -k 5  # semantic only, scoped
sfs index                                     # incremental lexical reindex (safe, ~25s warm)
sfs index --semantic --budget 6000            # embed N pending chunks (priority order)
sfs prune                                     # drop chunks of deleted files
sfs nightly                                   # exactly what the 03:30 cron runs

# --- docgen: documents ------------------------------------------------------------
docgen selftest                               # writes+renders docx/xlsx/pptx, asserts page counts
docgen md2docx in.md out.docx                 # markdown -> real OOXML
docgen csv2xlsx in.csv out.xlsx
docgen md2pptx in.md out.pptx
docgen office2pdf in.docx                     # any OOXML/ODF -> PDF (headless soffice)
docgen md2pdf in.md out.pdf
docgen pdfinfo out.pdf                        # pages, encrypted?, metadata
docgen pdftext out.pdf                        # text layer

# --- tabpredict: tabular ML -------------------------------------------------------
tabpredict selftest
tabpredict data.csv --target label            # auto: task detect + model compare + CV
tabpredict data.csv --target price --model tabpfn
tabpredict --apply model.joblib new_rows.csv  # score new rows with a saved model

# --- decide: calibrated local gate ------------------------------------------------
python3 ~/ops/decisions/decide.py "Is the box memory-pressured right now?"
python3 ~/ops/decisions/decide.py --json --context "<facts>" "Should we deploy now?"
python3 ~/ops/decisions/decide.py selftest

# --- heavy: governor ---------------------------------------------------------------
heavy.sh --label embed -- sfs index --semantic --budget 2000
heavy.sh --strict --mem-wait 600 --min-mem 1500 -- <bulk-cmd>   # skip (exit 3) if pressured
heavy.sh --status
~/ops/infra/load_report.sh                    # load, top CPU/mem hogs, slots, ollama probe
```

## Verify before trusting (all cheap)

```bash
docgen selftest | tail -3                     # expect PASS + 1/1/3 page PDFs
sfs stats                                     # expect ~71k chunks, vectors growing nightly
tabpredict selftest | tail -5                 # expect PASS, accuracy/ROC-AUC + timing
python3 ~/ops/decisions/decide.py --json "Is 17 a prime number?"   # expect ACCEPT with p_yes
heavy.sh --label t -- bash -c 'cat /sys/fs/cgroup$(cut -d: -f3 /proc/self/cgroup)/cpu.max'  # 50000 100000
```

Report the selftest output as evidence — never claim a lane works without it.

## Pitfalls (all hit for real on 2026-10-12)

- **ollama is NOT a bulk embedder on this box.** Measured `bge-m3` and `nomic-embed-text` at
  **0.3–0.6 chunks/s** (a single 1-token `llama3.2:3b` call took **5m01s** under load 46). Use ollama
  only for small quality jobs / re-ranking; bulk goes through **fastembed (ONNX)**.
- **fastembed's default cache is `/tmp/fastembed_cache`** → wiped on reboot, and a cold fetch can hang
  for minutes. `sfs` pins `cache_dir=~/ops/filesearch/models`. If a semantic run shows 0 vectors for
  minutes, check the cache dir before blaming the model.
- **Contention, not the model, is the throttle**: the same ONNX pass measured **4.7 chunks/s idle vs
  ~0.35 chunks/s while other lanes run (13×)**. Run bulk via `heavy.sh`, ideally off-peak.
- **Memory pressure is the real killer**: with swap 2 GB **full**, ONNX re-reads its model pages from
  disk and crawls (`rchar` ~900 MB per run). `heavy.sh` waits/skips on `MemAvailable < 1200 MB` or
  swap > 70% (env: `HEAVY_MIN_MEM_MB`, `HEAVY_MAX_SWAP_PCT`, `HEAVY_MEM_WAIT`; `--strict` → exit 3).
- **LibreOffice**: installed with `--no-install-recommends` (no distro fonts) — Arabic still renders
  because `~/.fonts` carries Noto; the font actually used was **DejaVu** (verified by eye, not by text
  extraction). Always pass `-env:UserInstallation=file://<tmp>` (docgen does) or concurrent soffice
  runs collide on one profile lock.
- **Arabic/mixed-direction PDF text extraction is unreliable** (bidi reorder scrambles substrings);
  verify RTL deliverables by rendering PNG (`pdftoppm -png`) and looking at it.
- **TabPFN needs a one-time licence acceptance** (browser login → `TABPFN_TOKEN` env var, or
  `~/.cache/tabpfn/auth_token`). That is a consent action on Aamir's account — ask him, never accept
  silently. The sklearn models in the same lane work without it.
- **TabPFN pulls the CUDA torch build on ARM** (`torch 2.14.1+cu130`, ~5.6 GB). Works on CPU; swap for
  a `+cpu` wheel if disk is tight.
- **Use `uv pip install`, not `pip`,** for large wheels: pip burned 40+ min on torch (11 GB IO churn)
  before being killed; uv finished in minutes.
- **`decide.py` fails safe**: any backend timeout returns `ESCALATE` with an error, never auto-yes.
  Cold model load ~4 min, warm ~25 s — batch it, never put it in a request path.
- **Never `pkill -f`** (it kills the harness itself). Kill explicit PIDs: `pgrep -P <parent>` then
  `kill <pid>`; note children survive a parent kill.
- **Long `write_file`/`patch` payloads can get truncated** — after any big write run
  `grep -rn "\[truncated\]" <files>` and read the region back.

## Maintenance / cost

- Cron: `30 3 * * * /home/ubuntu/ops/filesearch/nightly.sh` → incremental lexical + up to 6,000
  embedded chunks + prune, all under `heavy.sh`; silent on success, log at
  `~/ops/filesearch/logs/nightly.log`.
- Full semantic coverage (~71k chunks) takes ~2 quiet weeks at that budget; priority order is
  skills → brains → ops → projects → clients → sanad.
- Everything is free/local; only external dependencies are the HF model fetch (cached) and `soffice`.
- Background: `~/ops/infra/reports/2026-10-12-solo-devs-clone-big-tech-gap-audit.md`.
