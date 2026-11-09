# Seminar/masterclass → our-stack upgrade audit

Trigger: Aamir attended (or we captured, via `live-meeting-attendance`) a seminar/webinar and asks
**"is seminar se hamari infra me kya upgrade karna chahiye / capability boost kaise karein?"**.
The reference artifact is a **captured transcript** (`~/ops/zoom-attend/run/transcript.txt` +
`chat.txt`), not a landing page — same deliverable as `references/infra-gap-audit.md`, different
evidence source.

Core rule: the speaker's own taxonomy becomes the **audit axes**; every line of the audit's
evidence must come off THIS host. Never restate the seminar as the answer, never adopt a vendor's
demo architecture as our plan, and never let the host's marketing claims into a status column.

## 1. Extract the taxonomy from the transcript, not the sales page
Worked case — DDS "Master Agentic AI" (Mohammad Arshad, Founder DDS Dubai, 2026-09-20) taught an
explicit ladder, which is what made the audit sharp:

1. prompt engineering → 2. context engineering → 3. harness engineering → 4. **loop engineering**
   ("sabse powerful; sab kuch connect karta hai").

Supporting frames, all reusable as audit axes:
- **6 stages of an agentic app** (demo: HALA, an HR agent for "ACME Global"), stage 1 = *Clarity &
  the Real Document* — "define the problem before touching a model"; where "web coders" fail.
- **ReAct loop** (reason → act → observe → stop) and the need for an explicit stop condition.
- **RAG = a technique that turns documents into a file-search tool** — not a package, not an agent
  (called out by the host as the #1 industry misconception).
- **4 chunking strategies** — fixed-size / recursive / semantic / table-aware; fixed-size "cuts
  sentences and table rows", table-aware keeps each table whole.
- **Agent = LLM + tool**; deterministic lookups (SQL/HRMS) vs generative paths (policy text).

**Verify before quoting a seminar claim.** A live capture gives three sources that disagree:
audio transcript, chat log, and the slides. Cross-check all three (OCR the screenshots —
`tesseract` over `shots/*.png`) and cite which one said it. Run `scripts/verify_capture_claims.py
<run_dir> --claims "…" "…"` for this instead of ad-hoc greps: it classifies every claim per source
(VERBATIM / PARTIAL <ratio> / NOT FOUND) and hands back the `[src: …]` tag plus a verdict line
(`slide-only` ⇒ never attribute it to the speaker). Real example (2026-09-20): the demo app
was HALA per the slides but "Decobot" in the audience chat; "fixed-size will break your system" was
never said — the slide reads "cuts sentences and table rows"; "who owns the data" was our own
addition to stage 1, not the host's words. Same rule for the speaker's identity: the host's name
and role are ASR-mangled too (host = **Mohammad Arshad, data scientist**, DDS Dubai) — a wrong
attribution invalidates the entire write-up.

Reading recipe: locate the chunk via the `^=== live_` headers, then window it with a script file
(`python3 /tmp/<script>.py`) — never pull a 100K+ char transcript into context.

## 2. Inventory FIRST, in one pass, off the box
Never answer from remembered architecture. Verified probe set (2026-09-20):
- **MCP / tool surface:** `awk '/^mcp_servers:/{f=1;next} f&&/^[^ ]/{f=0} f' ~/.hermes/config.yaml | grep -E '^  [a-z0-9_-]+:'`
- **RAG truth (store + chunking, not the README):**
  `~/ai-stack/venv/bin/python3 -c "…chromadb…list_collections()…count()"` and
  `grep -nE 'RAG_CHUNK|CHUNK *=' ~/ai-stack/rag.py ~/ai-stack/ingest.py`
- **Skill/harness surface:** skills count + `ls ~/ops/bin` (which CLIs are actually callable).
- **Loop-side surface:** cron jobs, verify ledger, `~/ops/evals`, `~/ops/observability/`.
Pitfall: long multi-part recon one-liners come back **elided/truncated** in this harness ("1 lines
output"). Split into 2–4 small commands, or write the probe to a file and run it — an empty tail is
an elision, not a finding.

## 3. Scorecard: level | status | PROOF (each row carries a measured artifact)
Worked output: prompt ✅ / context 🟡 / harness ✅ / **loop 🔴 = weakest layer**. "We have skills" is
not evidence; "205 skills, 4 local MCP servers, 0 loop-trace records" is. The 🔴 must be the row with
the largest *measured* absence, not the row that sounds most impressive.

## 4. Findings that recur on our box (re-check, then reuse)
- **RAG was CLI-only, not a tool** → **CLOSED 2026-09-20**: it is now 8 MCP tools on
  `127.0.0.1:8797` (`rag_search` / `rag_answer` / `rag_collections` / `rag_stats` / `rag_index` /
  …), with the deterministic rate lane fused into search. When re-running the audit, VERIFY the
  surface (`mcp_servers:` in `~/.hermes/config.yaml`) instead of re-reporting this finding — a
  stale finding column is the fastest way to lose the user's trust in the whole scorecard.
- **Chunking is fixed-window** → table corpora split mid-row (detail: `chromadb-rag-ops` pitfall 10).
  **Verdict measured 2026-09-20**: the structure-aware chunker fixes table integrity (99% of rows
  keep their header vs 22%) but *lowers* recall → **not promoted**; the recall fix that WAS promoted
  is the lexical (FTS5/BM25) lane + rank fusion (hit@1 0.409→0.591, hit@5 0.818→0.909). Method +
  numbers: `chromadb-rag-ops` → `references/retrieval-change-eval.md`.
- **Deterministic vs generative boundary unenforced** → numbers can come from the model instead of
  a tool; the place to enforce it is the existing content gate
  (`~/ops/verify/claim_integrity.py`): a figure needs `[src:tool|file]`.
- **Loop telemetry absent** → we score task OUTPUT (ops/evals, ops/decision) but not the loop
  (turns, tool calls, retries, tokens, stop reason). Cheap version: one JSONL row per loop run →
  silent weekly digest.
- **Model tiering matches the host's own advice** ("a very simple model was enough"): cheap model on
  grounded tool turns, strong model only for planning.

## 5. Deliverable shape (what Aamir accepts, verified 2026-09-20)
- Hinglish, bullets, no hype; **P0 / P1 / P2** where every P0 item names a real file, port or
  command — and P0 is genuinely cheap (no new spend).
- A **"jaan-boojh ke nahi kar rahe"** section: the deliberate non-upgrades (e.g. no paid vector DB or
  managed RAG licence — local Chroma + bge-m3 suffices).
- 1–2 "we are already ahead here" rows (cron no_agent watchdogs, MCP system-of-record connectors,
  verify ledger + autonomy registry) so the box isn't read as uniformly behind.
- Separate **host claims** (community size, "most powerful model as of today", participant counts)
  from engineering facts; label the unverified ones.
- Bonus read: when the vendor's demo decomposes into components we already own (an HR policy bot =
  deterministic DB lookup + policy retrieval), the opportunity is **packaging, not building** — say
  so in one line.
- Write the plan to `~/ops/kb/<TOPIC>-upgrade-<date>.md` and attach the file; the chat reply carries
  the scorecard summary. Close with a single offer to implement P0 (not a question list).
