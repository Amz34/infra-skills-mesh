# Worked Examples (2026-09-04, same session)

Both were LinkedIn posts by Akshay Pachaar with "analyze/beneficial to our infra?"
requests. They show the full shape: resolve -> extract -> verify -> infra map ->
3-bucket verdict -> one next action. Final outputs landed in Hinglish, concise.

## Case 1: JIT-Agent (lnkd.in/p/deqWZ3SD)

**Post claim:** "Self-evolving agent harnesses are here (100% open-source)."
JIT-Agent-27B (Qwen3.6-27B base) writes a per-task harness — 4 Python modules
(memory / planning / tool_policy / action) + prompt config — BEFORE the task;
a fixed execution model then runs inside it step by step. Claims: harnesses
matched/beat hand-built runtimes (OpenCode, Claude Code) at ~half the tokens;
DeepSeek-V4-Flash + JIT harnesses > GPT-5.6 on DeepSearchQA/OdysseyBench.
Archive keeps winning harnesses; own weights never change.

**Verification hits:** HF org `JIT-Agent/jit-27b` = 27.36B BF16 (≈55–60GB VRAM),
explicit "initial research release"; repo `bingreeky/JIT` benchmark-runner grade,
serve with TP=4 (4 GPUs). Meta-cost hidden in the post: 3 candidate harnesses
generated per task (best-of-N) — sits outside the quoted per-case savings.

**Verdict: ❌ not now — watchlist.**
- Hardware ceiling: cannot run 27B BF16 on the box (Ollama qwen 7b/3b).
- Overhead math wrong at his task sizes: most tasks are short (lead capture,
  WhatsApp replies) — generation cost would eat the savings.
- Concepts already present in stack: hybrid_router+pii_gate = his tool policy;
  Hermes skills = curated per-task-type harness; cron no_agent scripts +
  monitor hash-suppression = "keep computation out of the model" (paper's core).
- Watch trigger set: ≤14b distilled/quantized variant or public API of jit-27b
  → deployed silent monthly no_agent cron "JIT-Agent monthly watch"
  (schedule `0 9 1 * *`, script `~/.hermes/scripts/monthly_jit_agent_watch.py`,
  job id 45b13b2fd0dd; polls HF org/search + OpenRouter; baseline first run
  found only `JIT-Agent/jit-27b`; next check 1st of month 09:00).

## Case 2: TrueForge (lnkd.in/p/dinFtkKq)

**Post claim:** Sam Altman made the case for open-source harnesses in July; a
month later TrueFoundry shipped TrueForge. Core diagnosis: "Much of your agent's
token bill is the model re-reading what it already read" — harness design fault.
Two controls: (1) cut context — tool returns short preview + file path instead
of full result every turn; delegate to subagents (30 tool calls in their own
context, summary comes back); run toolchains in code (1 script joins 3 tools
into 1 table); (2) cut call count — skip planning/verification/reflection when
fewer steps suffice. GH: github.com/truefoundry/trueforge.

**Verification hit:** GitHub API — 5.2k stars, MIT, TypeScript, created
2026-07-23, pushed 2026-09-04 (same-day activity = alive, but weeks old).

**Verdict: ❌ no action — pure validation of the existing stack.** Every control
the post prescribes maps 1:1 to Hermes behavior already in daily use:
- preview + file path -> web_extract / read_file (head+tail, full text on disk)
- subagent delegation -> delegate_task (isolated context, summary return)
- toolchains in code -> execute_code (hermes_tools)
- skip model when fewer steps do -> cron no_agent scripts + monitor hash-suppression
Meta-note for future posts: JIT-Agent (per-task generated harness) and TrueForge
(fixed harness + good defaults) attack the SAME problem from two ends; Aamir's
stack sits in the middle (fixed runtime + per-task skills + silent scripts) —
a useful framing for the next "which harness should we run?" question.

## Case 3: Stas Bekman "10 local AI repos" listicle (lnkd.in/p/d8zKKZNc, 2026-09-09)

Different shape: not a single-product post but a 10-repo listicle ("run powerful
AI locally, cut API bills to $0"). Full list recovered ONLY from the
`og:description` meta tag (curl raw HTML) — visible body extraction truncated
mid-list. Repos: Ollama, ComfyUI, llama.cpp, GPT4All, whisper.cpp, LocalAI,
text-gen-webui, exo, Jan, mlx-lm.

**Mapping verdict (9/10 no-op):** Ollama = already running (post validates the
stack); llama.cpp = inside Ollama; LocalAI = redundant (router already gives
OpenAI-compat API); ComfyUI/GPT4All/Jan/text-gen-webui = desktop/GUI, headless
VM useless; mlx-lm = Apple Silicon only. exo (47.3k stars, Apache-2.0, active)
= watchlist with explicit trigger: only if a client job needs privacy +
large-model AND ARM devices become available (cluster ops burden).

**The 1 that mattered — whisper.cpp** (org-move catch: API on old owner
`ggerganov/whisper.cpp` = None; real owner `ggml-org/whisper.cpp`, 53.5k stars,
MIT, pushed previous day). Local speech-to-text = genuinely NEW capability
(Telegram voice notes → text, $0, audio never leaves box). User approved a
spike → verdict on THIS box (aarch64 2-core ARM, 11GB):
- Build: needs cmake; `make -j2` → `build/bin/whisper-cli`. Models via
  `huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-{base,small}.bin`
  (141MB / 465MB). .ogg → 16kHz mono wav via ffmpeg first.
- Measured: base ~1.3x realtime, small ~0.45x realtime (12s clip → 9s / 26s).
- Quality (TTS test clips): **English small ≈ verbatim-perfect → prod-grade
  for client bots**; Hinglish small = gist-level only (mixed-code Hindi mis-
  hears, drops sentence tails; base worse) → NOT client-facing verbatim;
  Arabic untested.
- State: spike complete, NOT formalized — files lived in /tmp, user decision
  pending. If formalizing: proper install + wrapper script + feature in client
  bots (English voice notes), Hinglish only for rough internal notes.

## Case 4: Willow Jarvis — GPT-6 Astra + Butterbase "Astra Parts" (lnkd.in/p/dhNR-4kZ, 2026-09-09)

Not a listicle — a product demo. Post claim: GPT-6 Astra live on the Butterbase AI
Gateway; "Astra Parts" demo = 1 sentence describing a mechanical part → Astra
writes parametric CAD → browser compiles to a watertight 3D solid → stored +
quoted, ~$0.07/part. Whole app = 1 table + 1 Durable Object + 1 function + 1
HTML file on Butterbase; out-of-quota page hands over the prompt to rebuild the
app on your own account with any AI agent.

**Verification hits:** OpenAI `gpt-6-astra` (+`-pro`, batch variants) live on
OpenRouter @ $10/M in, $50/M out. BenchCAD is real (arxiv 2605.10865, 17,900
execution-verified CadQuery programs, ISO/DIN/ASME families) but "Astra tops
BenchCAD" = post's word, no independent leaderboard found. Butterbase =
`butterbase-ai/butterbase`, Apache-2.0, TypeScript, 3.4k stars, created
2026-05-20, pushed same-day = alive, but only ~4 months old; "BaaS: Postgres,
auth, storage, functions, AI gateway, MCP" ≈ what Aamir does with
Notion+Forms+Workers, split across pieces.

**Verdict: ❌ CAD not now (irrelevant to lead-gen/bot infra); 👀 Butterbase
watchlist (trigger: 10k stars OR stable v1 release OR repo dead); 💡 borrow
"hand over the rebuild prompt" handoff pattern for client deliverables
(no lock-in feel).**

Watch deployed: silent no_agent cron "Butterbase maturity watch" (schedule
`0 9 1 * *`, script `~/.hermes/scripts/monthly_butterbase_watch.py`, job id
7e2ea04ccc37). Script = delta_watch_noagent template adapted to GitHub API:
fixed markers STARS_CROSSED_10K / STABLE_V1_RELEASE / REPO_LOOKS_DEAD
(>90d no push). Star counts NOT embedded in markers (changing ints would alert
every month). Baseline 1st run silent, state
`~/.hermes/scripts/butterbase_watch_state.json`.

## Case 5: turbovec / bit-width vector quantization (lnkd.in/p/dsPGmAJe, 2026-09-13)

Post claim (Ayesha Shafique): "10M vectors eat 30GB+ RAM — turbovec does it in
4GB"; 4-bit scalar quantization turns 1536-dim vectors from 6,144 bytes to 384
bytes = 16x compression, "zero training", "search speeds past FAISS", prebuilt
AVX-512 VNNI assembly, MIT, 17k+ stars.

**Verification hits:** `RyanCodrai/turbovec` = MIT, Rust+Python, 17,014 stars,
created 2026-03-26, pushed 2026-08-18, v1.0.0. Algorithm real: Google Research
TurboQuant, arXiv **2504.19874** (Zandieh/Daliri/Hadian/Mirrokni, 2025-04-28).
PyPI ships a **manylinux_2_28_aarch64 wheel** → installs on this VM with no Rust
toolchain (verified: turbovec 1.0.0, numpy only).

**Post's error (reusable catch):** 384 bytes is the **2-bit** figure (16x);
4-bit = 768 bytes = 8x. The "3.4x faster" number is from the **4-bit** config
(2-bit averages only +23%) — the post bundles two different configs into one
sentence. Post also omits the recall trade-off (its own README shows TQ+ 0.7pp
BEHIND FAISS at R@1, d=1536 4-bit) and buries the real wins: O(1) remove
(0.44–1.22µs vs FAISS remove_ids 0.19–1.02 **seconds**) and crash-safe
incremental `sync()`.

**On-box benchmark** (50k×1536 clustered unit-norm, 1000 queries, aarch64
2-core): numpy exact float32 18.26 ms/q; 2-bit 0.75 ms/q, 15.2x compression,
recall@10 **0.42**; 4-bit 1.20 ms/q, 7.6x, recall@10 **0.76**; calibrate() gave
+0.003 recall and slowed 2-bit (1.82 ms/q) → skip it. 2-bit recall is unusable
for RAG; 4-bit is the only viable config. Reusable harness:
`~/.hermes/tmp/turbovec_bench.py` + venv `~/.hermes/tmp/tv_venv` (sandbox only,
ai-stack untouched — user said keep).

**Verdict: ❌ not now / 👀 watchlist.** The post's pain (30GB vector RAM) is not
Aamir's: ai-stack = ChromaDB + bge-m3 1024-dim via Ollama, **548 embeddings
across 7 collections** (chroma.sqlite3 = 9.3MB; ~2.2MB of float32 vectors) on an
11GB box. His real bottlenecks are LLM **generation** (hosted), 2 cores / no GPU
(load avg 2.2), disk 52%. Swapping out Chroma means losing HNSW + metadata
filtering for ~2MB. Genuine fit only at: (1) ZeroEgress-style air-gapped RAG,
(2) a client corpus >~500k–1M chunks (1M×1024 float32 = 4GB), (3) kernel-level
per-tenant ACL allowlist filtering. Re-check trigger: vector count >~500k or an
air-gapped RAG requirement. Offered a silent no_agent monthly watch; user has
not taken it up.

**Note for next post of this class:** vendor posts of the form "Nx compression
AND faster" almost always mix quant levels — check bytes-per-vector arithmetic
against dim×bits/8 FIRST, before reading benchmarks. And check the arch: this
box has `asimd`+`asimddp`(SDOT) but **no i8mm/SMMLA**, so AVX-512/i8mm kernel
claims are structurally unreproducible here.

## Response-shape takeaways that worked
- Start with "Post kya hai (verified)" one-liner, then repo/maturity reality
  check with real numbers, then infra mapping by NAME, then verdict, then
  "abhi kya kare" with either a concrete action or explicit "kuch nahi —
  ye hamare setup ka validation hai". Short is fine; correctness is not skippable.

## Case: affaan-m/ECC (2026-09-29) — "248k stars, one plugin, all in context"
**Verdict: ❌ full install / ✅ four skills ported by hand.** 269,155★ in 8.3 months is real
(top-30 repo) but shallow — 1,352 watchers = 199:1 vs freeCodeCamp 53:1, so the star count
carries no information about quality. 68 agents / 94 commands exact; "286 skills" was 292.
"Installs as one plugin" is Claude-Code-only: ECC's own Hermes target is marked
`availability: advanced`, `guidedReady: false`, hooks `not-configured` — a directory dump.
The import bill was NOT the tokens (+6.1k/turn, 2.36x index, ~$2/month) but description shape:
287/292 descriptions lack a `Use when` trigger, so our 57-char truncation turns them into
fragments and routing degrades. Our lint over all 292: 0 passes, 292 warn-only, 8 hard fails
(7 fixture false positives, 1 `rm -rf /` inside a teaching example). Upstream hygiene was fine
(MIT, `npm install --ignore-scripts`). Ported 4 mechanisms, rewritten, 4x PASS 0 warns; nothing
installed; upstream frozen at `~/ops/vendor/skills/affaan-m/<skill>/`.

**Note for next post of this class:** for a large skill pack, run the lint over the WHOLE pack
before deciding — description-trigger shape is the gate, not licence or token cost. Popularity
claims ("N stars in M months") should be recomputed from `created_at`; watch the short link
redirect — `lnkd.in` still does not resolve with curl, use `web_extract`.

**Follow-through lesson (same day, worth repeating):** judging the vendor on the index axis exposes
your OWN store to the same judgment. Running `skill_lint.py --tree ~/.hermes/skills` here found
131/225 descriptions index-clean (40% had no `Use when` trigger, 32% truncated mid-phrase) → 94
rewritten under a validated contract (trigger-first, sentence 1 inside 57 chars, context read from
each skill's own `## When to Use`, never invented) → 225/225. Ports then had to clear a *calibrated*
bench: the first pass showed the port losing to the no-skill baseline, and re-grading the SAME
recorded outputs (free, `regrade.py`) proved the grader was wrong, not the skill (brittle
`[^.]{0,70}` gaps, `not_contains` punishing verbatim quoting, baseline-flavoured vocabulary). Final:
93.8% vs 50.0%. **Never act on a single uncalibrated bench loss.**
