---
name: agent-skill-adoption-gate
description: Use when vetting or adopting a third-party agent skill.
version: 1.0.0
author: Aamir Zameer (Hermes Agent)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [skills, supply-chain, evaluation, governance]
    related_skills: [tech-adoption-analysis, mcp-tool-servers]
---

# Agent-skill adoption gate

## When to Use

- Someone shares a skill from `skills.sh`, a GitHub repo, or a marketplace and asks to install it.
- A published or trending skill looks useful for client work (design, MCP, evaluations).
- You are about to run `npx skills add`, copy a `SKILL.md` into `~/.hermes/skills`, or alias any
  third-party instruction file into the agent's context.

A skill is an **instruction-injection channel that runs with the agent's full credentials** (Gmail,
LinkedIn posting, Cloudflare token, SMS gateway, SAP connector). Popularity is not a safety signal:
the marketplace's own audit page has flagged vendor-owned repos Critical/High.

## The three steps (never skip 1 or 3)

1. **Inspect without installing**
   `~/ops/scripts/skills-review.sh <owner/repo>` → lists skills;
   `… <owner/repo> <skill> [skill …]` → extracts each SKILL.md + runs a static risk pass into
   `~/ops/skills-review/<source>_<ts>/SUMMARY.md`.
   **Why not a fake HOME:** the `skills` CLI writes to the real passwd home (`~/.hermes/skills`) and
   ignores an overridden `$HOME` — a stray install into the curated store has been observed and
   reverted. Never bulk `add -g`.
   Read the **extracted text**, never the listing: top-ranked "guidelines" skills turned out to be
   empty wrappers that fetch `raw.githubusercontent.com/...` at run time (audited artifact ≠ executed
   artifact).
   Since 2026-09-29 the script also unwraps each extracted file into `<out>/tree/<skill>/SKILL.md`
   and runs the real gate on it (`skill_lint.py --tree … --no-dirname`, check ids + supply-chain
   section), appending a `## Gate: skill_lint.py` block to `SUMMARY.md`, writing `gate.json`, and
   **exiting 2 when a hard fail is found** (`SC-01` credential-shaped, `SC-02` fetch-and-exec).
   A `SC-03` `curl|sh` install one-liner is a warn only: check the domain is the vendor's own.
   The old grep pass is prose; the exit code is the gate.
2. **Rewrite, don't copy** — put the idea into a Hermes-native skill under our conventions
   (`Use when …` description, `## When to Use`, brand isolation, no-faces imagery rule, pure-English
   client copy). Freeze the upstream material read-only at `~/ops/vendor/skills/<owner>/<skill>/`
   with a `PROVENANCE.md` (repo, license, pinned commit, SKILL.md hashes — append hashes at vendoring
   time, do not trust a later diff).
3. **Measure before trusting**
   ```bash
   ~/ops/evals/skills-bench/skill_lint.py <skill-dir>              # static gate, no hard fail
   ~/ops/evals/skills-bench/skill_lint.py --tree ~/.hermes/skills   # whole-store audit
   ~/ops/evals/skills-bench/run_bench.py --skill <name> --evals <evals.json> \
       --runner deepseek --iterations 3 --with-baseline --max-tokens 24000 --ledger
   ```
   `--tree` grades every `SKILL.md` under a root and prints `verdicts`, `index-clean descriptions:
   N/M` and a `supply-chain (SC-*)` section; findings are tagged with stable ids (`STRUCT-*`, `IDX-*`,
   `SC-*`) so a store audit can be aggregated by check instead of read as prose. Exit: 0 pass, 1
   warn-only, 2 hard fail. Use `--no-dirname` when linting extracted review trees (the dir is the
   npx alias, not the skill name) and `--json` for the artifact a decision file cites.
   `--ledger` writes the verdict to the layer-3 verifier (`verify-ledger.jsonl`). A skill enters the
   store as a **pending** decision (`~/brains/ops/decisions/`) until it beats baseline.

   **The token budget is a *reasoning* budget — check it before believing a with-skill loss.**
   `--max-tokens` is shared by the model's `reasoning_content` and the visible answer, and
   `run_bench.py` falls back to grading `reasoning_content` when `content` is empty. A reasoning
   model (`deepseek-v4-flash`) can burn the entire budget thinking and emit **no answer at all** —
   the grader then scores the deliberation stream as if it were the artifact, and "stays a page, not
   an essay" / missing-token checks fail for a reason the skill did not cause. Symptom: `usage.
   completion_tokens_details.reasoning_tokens == max_tokens`, `content` empty, artifact a few hundred
   chars. Read `reasoning_tokens` first, and re-run at ≥32k before writing a skill off
   (2026-09-29, `frontend-design`: 16k cap ⇒ 0–33 % vs 67 % baseline on `landing-page-tokens`;
   a *longer* skill deliberation is what flipped it, not the artifact).

   **A red check can be the instrument's fault, not the skill's.** The checks are regex proxies:
   `critique-pass / gives concrete fixes, not vibes` was `(replace|change to|instead|use a)`, so a
   *more* concrete `property: value` fix (`padding: 12px → 24px`) scored red while a vague sentence
   merely containing "replace" scored green. Before tuning a skill to satisfy a red check, read the
   pattern and ask what answer it rewards; repair it in `evals.example.json` and log the change in
   `~/ops/evals/skills-bench/evals-CHANGELOG.md` — verdicts recorded before a repair are not
   comparable with later ones.

   **The gate scores the *average*, so saturated evals cap your reachable lift.** With 3 evals where
   baseline already sits at 100 % on two of them, the maximum possible lift is +0.333 against a bar
   of +0.30 (`assert_delta.py` `min-delta`). Clearing it therefore needs: perfect with-skill scores
   everywhere, a decisive win somewhere, and **no run that hit the cap and failed a check** — that
   clause counts baseline runs too, so raise the budget until nothing truncates rather than arguing
   with the gate. If a lift is real but sub-threshold, harden the saturated evals and record that
   in the decision file; never lower the bar.

## Index shape is a gate, not cosmetics

A skill's routing value lives in the ~57 chars the index shows. Audit on the same axis we judge
vendors on: `skill_lint.py --tree ~/.hermes/skills` prints `index-clean descriptions: N/M`, where
clean = opens with `Use when/for` **and** finishes its first sentence inside the 57-char window
(`desc_trigger_ok`, `desc_len` ≤ 150 in `--json`).

Measured 2026-09-29: our own store was **131/225 clean (40% of descriptions had no `Use when`
trigger at all, 32% were cut mid-phrase)** — the same defect we had just rejected a 269k-star pack
for. 94 descriptions were rewritten to `Use when <trigger>. <detail>.` → **225/225 clean**.
Backup before any such sweep: `tar czf ~/ops/backups/skills-store-<date>.tar.gz -C ~ .hermes/skills`.

## Watch and overlap tooling

- `~/ops/scripts/vendor_drift_check.py` — re-hashes every vendored pin against the sha256 recorded
  at intake, asks GitHub whether the upstream blob moved since the pinned commit, and re-checks the
  pack's shape against the curated-subset trigger. Silent when clean; cron `vendor-drift-watch`
  (monthly, `no_agent`, wrapper in `~/.hermes/scripts/`) delivers stdout only as an alert.
- `~/ops/scripts/skill_overlap_report.py` — local bge-m3 embeddings over all descriptions, reports
  pairs above ~0.86 with a `referenced by` column (cron / other skills). Merge **as an alias** when
  a reference exists; never delete a skill a cron job names. Report only, changes nothing.
- Decision records for the ECC intake: `~/brains/ops/decisions/2026-09-29-skill-intake-affaan-m_ECC.md`.

## Pitfalls (all observed, not theoretical)

- **Budget is a confound.** `frontend-design` scored 0% vs a 33–67% baseline on the artifact eval at
  `--max-tokens 9000` and 100% vs 0% at 24000: the model planned until the cap. Before believing a
  negative verdict, re-run one eval at double the budget and eyeball the raw output.
- **Hybrid reasoning models bill reasoning against the completion cap** — a cap hit is only evidence
  of truncation when that run also failed a check.
- Grade the **raw answer**, not a single fenced block: answers arrive as many small blocks, and a
  "longest fence" heuristic mis-scores them.
- A process-heavy skill makes a chat-only model monologue; any skill that prescribes passes needs an
  explicit **output contract** (artifact only, complete, no `...`, nothing after the block) and its
  detail in `references/` rather than the top-level SKILL.md.
- `skills update` silently re-pulls content and the CLI marks third-party skills `Trust=local` with
  no provenance distinction — installing globally dilutes a curated store.
- Telemetry is on by default in the CLI: `DISABLE_TELEMETRY=1` on every call.

- **A pack can be technically clean and still be un-routable.** In `affaan-m/ECC` 287/292
  descriptions had no `Use when/for` opener and averaged 304 chars (ours: 62) — the trigger lands
  after the 57-char index window, so the agent never sees why to load the skill. Judge a pack on
  index shape, not on skill count.
- **Bulk description edits need a contract, a backup and central application.** Validate every new
  description (opener, first sentence ≤57 chars, ≤150 total, ASCII, grounded in that skill's own
  `## When to Use`) and write it as a quoted YAML scalar; never hand-edit 90 files, and keep a
  tarball of the store from before the sweep.

## Reference

- Policy + reversal test: `~/brains/ops/decisions/2026-09-14-agent-skill-adoption-gate.md`
- Evidence: `~/ops/skills-review/FINDINGS-skills-sh.md` (supply chain),
  `~/ops/skills-review/FINDINGS-skills-adoption-20260914.md` (adoption + measurements)
- Harness: `~/ops/evals/skills-bench/README.md`
