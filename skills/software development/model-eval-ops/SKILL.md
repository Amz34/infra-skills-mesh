---
name: model-eval-ops
description: Use when comparing LLM models or running task evals.
---

# Model Eval Ops — task-level LLM comparison baselines

## When to Use
- Comparing/choosing between LLM models or providers on real work ("konsa behtar hai?" needs evidence, not vibes).
- Regression check after a model or provider change — same golden set, compare scores.
- Building an eval harness from scratch (golden set + scorers + judges).
- Monthly model-eval report cadence (roadmap Track 3 L2).

Class-level skill for building and running **task evals that compare LLMs on real work** (DeepSeek vs Gemini routing, model upgrades, monthly eval cadence). Proof-by-build: golden sets come from real infra artifacts, never synthetic.

## Where the infra lives

- Harness: `~/ops/evals/eval_baseline.py` — urllib-only, zero external deps.
- Golden set: `~/ops/evals/golden.json`.
- Reports: `~/ops/kb/eval-reports/` — dated report MD + raw dump `eval_raw_latest.json` (overwritten every run).
- Rerun: `python3 ~/ops/evals/eval_baseline.py`; keys from `~/.hermes/.env` (DEEPSEEK_API_KEY, DEEPSEEK_MODEL, GOOGLE_API_KEY). Never print key values; probe quota with a 3-word call.
- Cron runner: `~/.hermes/scripts/eval_baseline_cron.sh` + cronjob `no_agent:true` — script stdout IS the delivered report.
- Current golden tasks (4): `wp-audit-json`, `client-summary`, `ar-hero`, `ar-pain` — full structure + observed results in `references/2026-09-avvs-wp-baseline.md`.

## Golden-set design rules

1. Real artifacts only — live wp-audit scans, client-approved bilingual content, real reports.
2. Deterministic scorers first (JSON validity, golden-item coverage, fabrication). LLM-as-judge only where deterministic is impossible (translation quality).
3. Matching hacks (proven):
   - Item candidates from slugs: raw slug + camelCase split (`twentytwentyfour` -> `twenty twenty four`) + hyphen-to-space.
   - Summaries: naive name-matching false-negatives good summaries — score via group aliases `{regex, count, group}` (e.g. `'(inactive|unused) themes'`). Golden items carry a per-item `group` field.
   - Fabrication detector: negation-aware (`no pending updates` is NOT a claim); keep matched snippet in the flag.
   - Arabic fixed-string checks: `ar_norm()` first — strip tashkeel/tatweel `[\u064B-\u0652\u0640\u0670]`, unify أإآ->ا, ى->ي, ة->ه — then contains-check.
4. LLM-as-judge: judge with BOTH models (cross-family, kills self-bias) and average. Strict JSON-output prompt, per-dimension 1-5 + winner. Parse-fail -> inconclusive, never fabricate a score.

## Frozen-set A/B (vendor claims and regressions)

When the claim is a number -- a vendor's "wrong-skill 16.8% -> 7.3% with our cookbook", or a
provider change you must regression-check -- do NOT build a new set. Re-run the **same items,
same candidate lists, same design**, swapping only the answerer, so the claim becomes testable
rather than quotable. Non-negotiables:

1. **Assert the frozen set reproduced itself before reading any metric.** Load the *cached*
   embedding index directly (a helper that rebuilds it because the live roster grew silently
   changes every candidate list) and verify the reproduced items match the recorded rows 1:1.
2. **Condition on the retriever ceiling:** report `P(correct | gold in shortlist)` and the
   ceiling itself (oracle-in-top-k) next to the headline, or the retriever's failures get
   charged to the model. On our 60-item lane this exposed a 17-vs-16 "difference" as pure
   retrieval noise (both lanes: 16/28 = 57.1% once gold was in the shortlist).
3. **Port the vendor's published design 1:1, not just their model** -- and report cost/latency
   deltas beside accuracy, since the buyable edge is usually speed and tokens, not accuracy.
4. **Re-run the recorded baseline arm FIRST as a control.** Point the *new* harness at the old
   arm and require it to reproduce the stored outputs item-for-item (same items wrong, same
   action mix). If the control drifts, you changed the pipeline as well as the answerer and the
   whole delta is unreadable. A control that reproduces is what licenses reading the other arm.
5. **Trust the response's `model` field, not your own flag.** Passing `--model deepseek-chat`
   still had every response echo `"model": "deepseek-flash"` — record the provider's reported id
   (and note the alias), or the write-up names a model that never ran.
6. **Give the label/calibration store an arm dimension before any A/B.** A store keyed on
   `(usecase, item, question)` silently overwrites one arm's labels with the other's, so the
   calibration table describes whichever arm ran last — and looks authoritative while doing it.

Second frozen-set lane, per-item (77 decisions, 6 use-cases, `real` vs `base` arms):
`~/ops/kb/jev-narrow-fork-ab-2026-09-21.md`; the runner + deterministic scorer are checked in as
`~/clients/invertio/jev/scripts/ab_run.sh` and `ab_score.py`, so the control re-run is one command.

Full recipe, the real-key numbers (Jev `jev-1.13.0`: 22.8x faster, 17.6x fewer output tokens,
zero accuracy gain), and the operational notes (vault-injected keys, unpublished pricing,
re-derivation in the harness verifier) live in `references/decision-model-qa-eval.md`.

## Pitfalls (learned the hard way)

- DeepSeek reasoning models (v4-flash): `reasoning_content` COUNTS against max_tokens (observed 10k-29k chars). JSON-typed gen calls need `max_tokens=16000` (8k truncates -> invalid JSON, finish=length); non-JSON 8000; summary 1600; judge calls 6000. Empty content: surface `__EMPTY__` marker with finish_reason + reasoning_len — never silently score.
- Gemini free-tier 429: backoff (tries=3, sleep 25s) fixes transient; persistent 429 = daily quota exhausted -> mark `inconclusive`, schedule rerun after ~07:00 UTC reset (Pacific midnight).
- One GOOGLE_API_KEY is shared across all 6 profiles on this VM — one heavy eval exhausts every profile at once. Probe with a 3-word call before full runs; long-term fix = per-profile keys.
- Never pipe a harness through `| tail` — exit code gets masked. Run bare or `> log 2>&1` + `echo exit=$?`.
- No inline `python3 -c` with shell-sensitive quoting — write a probe `.py` file instead.
- Runs outlive the 420s terminal timeout: launch, `pgrep -f eval_baseline.py` + poll; verify with `ps -o pid,etime,cmd` (pgrep can catch a dead wrapper).
- Winner logic: any-side error -> `winner=inconclusive` + note. Honest `[~]` + reason beats a fake `[x]`.
- Probe JSON structure before blind patches (dump actual keys) — key-guessing caused a KeyError.
- Latency 15-40s/call for reasoning models; report tokens+latency per model per task (cost signal).
- **Judge evidence packaging is the #1 cause of false FAILs** (observed twice in a row on a claim that
  was in fact fully verified). Before concluding the work is wrong, check the evidence file:
  - It must contain **exactly the counts/records the claim asserts** — if the claim says "40/40 checks",
    the file needs that row plus a per-item pass list, read from the ledger. A claim whose number is
    absent from the evidence will be failed for `missing_evidence` (`[]` = nothing missing).
  - **Never include the judge's own past verdicts or self-referential rows** in the evidence. Appending
    earlier `verdict=fail` rows made the judge doubt the claim it had just passed.
  - Give the judge the **reproduce command** alongside the result, so the row reads as re-runnable fact.
- **Print a summary BLOCK FIRST** in any checker whose full record goes to a log: a long JSON dump gets
  truncated and hides *which* item failed (a 40-check suite looked like a silent failure until the
  summary line was moved to the top).
- Relative paths inside evidence/log files must be resolved against a fixed ROOT — the same verifier
  that passed in its own directory failed when run from `/tmp`.
- A verifier that cannot disagree is decoration, but a verifier that fails **twice** is data: diff what
  it says is missing against what the evidence actually contains before changing the underlying work.

## Report and cadence

- Verdicts table (per-task winner + scores), judge tables, fenced model outputs for review, tokens+latency rows.
- After clean run: update `~/ops/kb/roadmap-progress.md` `[~]` -> `[x]` with date + proof path.
- Monthly rerun = roadmap Track 3 L2. Same golden set = regression signal on model/provider changes.

## Overlap note

`ai-eval-task-engineering` = exam tasks for coding-agent platforms (different class). Keep this one for harness design + API-model pitfalls.
