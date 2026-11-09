# Infra Baseline — for post→infra verdicts

Purpose: stop re-deriving "what is our box / what is our stack" on every shared post. Verified Sep-2026 on this VM. If a verdict hinges on one of these numbers, re-verify it cheaply rather than trusting the copy.

## Box
- arch **aarch64** (Oracle Cloud ARM, Neoverse-N1), 2 cores, ~11 GB RAM (~6 GB free idle), **no GPU**.
- `/proc/cpuinfo` features: `asimd`, `asimddp` present; **`i8mm` absent** → vector libs fall back to the SDOT kernel. x86-only flags (`avx2`, `avx512*`, `vnni`) are irrelevant here: never credit an AVX-512 speedup claim in a verdict.
- Disk ~193 GB total (~100 GB used at check), load avg ~2.2 on 2 cores — the box is already busy.

## RAG / vector stack
- `~/ai-stack`: ChromaDB + Ollama, 100% localhost, zero API cost.
- Embeddings = **bge-m3 via Ollama (1024-dim)** — NOT Chroma's default MiniLM (384-dim). OpenAI 1536/3072 dims never apply.
- Store: `~/ai-stack/chroma/chroma.sqlite3` — 9.3 MB, 7 collections, **548 embeddings** total.
- Float32 RAM cost of those vectors: 548 × 1024 × 4 ≈ **2.2 MB**. That is the number a compression pitch must beat.
- Real bottlenecks in order: **LLM generation** (hosted API; local 7B OOMs, 3B ≈ 3.4 tok/s), 2 cores / no GPU, then disk. Vector RAM is not a constraint.

## Measure-on-hardware worked case (turbovec, Sep-2026)
Post claimed: "10M vectors eat 30GB+ RAM → turbovec 4GB … 16× compression, 4-bit, faster than FAISS."
1. Verified source: GitHub API — `RyanCodrai/turbovec`, 17,014 stars, MIT, Rust + Python bindings, ~7 contributors, v1.0.0. PyPI JSON — prebuilt `manylinux_2_28_aarch64` wheel, sole dep numpy → no Rust toolchain needed. arXiv abs page — TurboQuant, **2504.19874** (real paper, not a pitch).
2. Throwaway venv `~/.hermes/tmp/tv_venv` (py3.11) + install turbovec 1.0.0 → imports clean on aarch64.
3. Bench, clustered unit-norm data (200 centroids, N=50k, D=1536, NQ=1000), 1000 queries:
   - 2-bit: **0.75 ms/query**, 15.2× compression, recall@10 0.42
   - 4-bit: **1.20 ms/query**, 7.6× compression, recall@10 0.76
   - exact numpy brute force: **18.3 ms/query**
   - Synthetic-data recall is a **lower bound** — never quote it as real-embedding recall.
   - The bench that ran exit 0 still lives at `~/.hermes/tmp/turbovec_bench.py`: **copy and parameterize it; do not re-derive the turbovec API from memory.**
4. Verdict: our 2.2 MB of vectors vs the post's 30 GB problem → ❌ adopt now, 👀 watchlist with trigger "**corpus > ~500k chunks, or an air-gapped / per-tenant RAG requirement**". Genuine fit = ZeroEgress-style local-only deliverables + SIMD-kernel tenancy allowlists (isolation without recall loss) + O(1) delete.
5. Swap cost counted: adopting it means dropping Chroma's HNSW + metadata filtering and rebuilding the retriever — not worth it for ~2 MB.

## Post-audit findings worth reusing
- The post's own sentence mixes configs: "4-bit … 6,144 → 384 bytes, 16×" — 384 B is **2-bit**; 4-bit is 768 B = 8×. Its "3.4× faster than FAISS" is the **4-bit** figure; 2-bit averages only **+23%**. Best-compression and best-speed numbers from different configs, bundled as one claim.
- Omitted trade-off: recall parity is not free (README's own charts: 4-bit trailed FAISS by ~0.7pp R@1 at d=1536). Omitted wins: **O(1) remove** (0.44–1.22 µs vs FAISS `remove_ids` 0.19–1.02 **seconds**) and crash-safe incremental `sync()`.
- "Zero training" is true for the default data-oblivious path, but an optional one-shot `calibrate(sample)` buys ~+2pp recall — so the claim is accurate-but-incomplete, not false.

## Harness / orchestration / cost baseline (Sep-2026)

For concept posts ("how do we get from agent → orchestration?", "our agents are slow/dumb/expensive"),
these are the numbers to quote instead of adjectives. Re-measure before quoting them in a verdict.

- **Harness:** Hermes default profile — 189 curator skills in `~/.hermes/skills/`, 786 `SKILL.md`
  across 6 profiles (the index itself is a standing prompt cost). RTK + compression wrappers in use.
  Local model aliases exist (`local`, `local-fast` → Ollama qwen2.5 3b/7b) = free tier for cheap tasks.
- **Orchestration:** 22 enabled cron jobs, 6 gateway profiles, ~448 cron runs / 7 d.
  `delegate_task` allows 10 concurrent children **but `max_spawn_depth = 1`** → fan-out only, no
  hierarchy (this is the honest ceiling when someone pitches "multi-agent orchestration").
  Reference CLI-agent harness deployment = Munder Difflin floor (Electron, CDP 9223, aarch64).
- **Cost (the lever that dominates):** `~/.hermes/cron/usage_audit.jsonl` — 19 logged runs =
  **4.13 M tokens, avg 217 k prompt tokens per run, max 1.01 M in a single run**; balance was $4.82.
  Prompt/token budget per job beats any concurrency work for savings.
- **Governance:** registry `~/ops/observability/autonomy.json` (139 surfaces, 116 classified,
  L4=97), auditor `~/ops/scripts/autonomy_audit.py`, gate coverage **18.2 %** after the layer-3
  wiring (14.3 % before), 4 P4 (verification-debt) report findings.
- **Verification:** `~/ops/verify/independent_check.py` — deterministic mode **0.0 s / $0**,
  9/9 on real state; cross-vendor model mode (worker DeepSeek → judge GLM) 23–29 s per verdict.
  Local Ollama is **not** usable for synchronous gates on this box (cold load ~25 s, ~12 tok/s).
- **Pipeline rule:** a "boost our infra" verdict = one measured gap per missing layer + a ranked
  leverage list (effort × value) + monetization readiness per play + the cheapest item built and
  independently verified in the same session. Detail: `agent-autonomy-governance` →
  `references/layer3-independent-verification.md`.
