# QA'ing a "decision model" before monetizing it

Applies when a vendor (or a colleague) claims a specialised decision model beats a general
LLM and you are about to build an offer on that claim. The deliverable is a number you
produced yourself, not the vendor's number.

## Design rules that make the result decisive

* **Fix gold labels by construction, not by vibes.** Write the items so the correct answer
  is unambiguous from the text (give each item exactly one explicit signal: a role word, a
  timing word, a request verb). Rule-derived gold is objective; hand-waved gold is not.
* **Give the baseline the SAME rule text** the model's question text carries. If the model
  sees a precise definition and the baseline sees a loose one, you have measured the prompt,
  not the model.
* **Run N reps per system.** One run cannot distinguish determinism from luck. Report the
  share of items where all reps returned an identical label, and also compare token counts
  across reps -- identical token counts are a strong determinism signal.
* **Batch the model, don't batch the baseline.** Structured-decision models answer several
  typed questions in ONE call; an LLM baseline typically needs one call per question. The
  honest cost comparison is per judging-decision, e.g. 3 questions = 1 model call vs 3 LLM
  calls -- state it that way rather than comparing a single call to a single call.
* **Report what a scale metric means.** For an ordered field, give exact-match AND
  within-one-level accuracy; off-by-one on urgency is a different failure from a wrong side.

## Metrics to report

Per-field accuracy (categorical exact, ordered exact + within-1), JSON/parse validity rate
(a structured model needs no fencing or repair -- say so), mean latency, tokens in/out,
rep-identical rate, and errors by item with the model's own reasoning quoted.

## Measured example (2026-09-21, 30-item inbound triage, 3 reps each)

| | Jev (TypeSafe System One) | DeepSeek baseline |
|---|---|---|
| intent / dm / urgency accuracy | 1.000 / 1.000 / 0.967 | 1.000 / 1.000 / 0.967 |
| rep-identical | 30/30 | 30/30 |
| mean latency | 0.72 s | 1.71 s |
| tokens per 3 judgments | 604 in ONE call | ~1,110 across THREE calls |

**Conclusion drawn: accuracy PARITY on this task.** The real edge is latency (~7x wall
clock because one call replaces three), ~1.8x fewer tokens per judgment, byte-identical
repeat answers, and machine-parseable output with a confidence value. Do not sell accuracy
superiority the eval does not show. On an easy, well-specified task a frontier LLM matches
a decision model -- the differentiator appears in agentic loops and at volume, so evaluate
those before pricing an offer.

## Two traps that cost real time here

* **N x REPS futures + `zip(items, futures)` is silently wrong.** With 30 items x 3 reps
  the first 30 futures are three reps of item 1, then three of item 2: zipping them against
  the item list scores item 2 with item 1's answer and every accuracy collapses to ~0.27.
  Iterate the futures and derive the item:
  `for k, f in enumerate(futures): item, rep = items[k // REPS], k % REPS`
  Sanity check: item-count x rep-count must equal future-count before you read any metric.
* **When the model disagrees with your gold, re-read the gold first.** Here the model read
  "is the sender a decision maker" as *sender identifies themselves in the first person*,
  while the gold accepted any third-party role mention ("the director of operations wants
  ..."). The model was right and the rule was ambiguous -- tightening the rule changed five
  labels. An ambiguous gold turns a correct model into five apparent errors, and would have
  produced a false "the model is weaker" verdict.

## Frozen-set A/B: testing the VENDOR'S published claim with their real API

When the claim is a number ("wrong-skill 16.8% -> 7.3% with our cookbook"), do NOT build a
new set. Re-run the SAME items, the SAME candidate lists and the SAME design your earlier
run used, swapping ONLY the answerer (cheap-LLM lane -> vendor's real endpoint). Then the
vendor's number is directly testable instead of merely quotable.

Three things made the result decisive (2026-09-21, real Jev key vs the recorded
deepseek-flash run over our 214-skill roster):

1. **Assert the frozen set reproduced itself BEFORE reading any metric.** The earlier rows
   stored `task[:110]`; the candidate lists came from `rank_wide()` over a CACHED embedding
   index (`index_emb.json`) plus a seeded `random.Random(7).sample`. Load that cache
   directly -- do not let the helper rebuild it just because the live roster grew
   (210 -> 214) -- and check the reproduced items match the recorded rows 1:1 (here 60/60
   task prefixes). A rebuilt index or shifted roster silently changes the candidate lists
   and you end up measuring the retriever, not the answerer.
2. **Condition on the retriever ceiling.** `P(correct | gold in shortlist)` isolates the
   decision layer. Real Jev and the cheap LLM were EXACTLY equal (16/28 = 57.1%), so the
   17-vs-16 headline difference was retrieval noise; the ceiling itself (gold inside top-20
   only 46.7% of the time) is the real bottleneck. Always publish the ceiling next to the
   score, or the retriever's failures get charged to the model.
3. **Port their published cookbook DESIGN 1:1, not just their model.** Same two-stage shape
   (roster Choice + request Nouls, then top-3 fit Nouls), same thresholds, only the answerer
   swapped. Doing this produced the negative result that mattered: on our lanes the
   two-stage gate was WORSE with real Jev (81.8% wrong positives vs the cheap lane's 68.2%
   on the same 22-item set), and the gate scores barely separated should-use from
   should-not-use (mean 0.634 vs 0.500 against a 0.30 threshold). Their headline did not
   reproduce even with their real API.

| arm (identical items, only answerer swapped) | real Jev `jev-1.13.0` | cheap LLM lane |
|---|---|---|
| typed Choice over the same 20 candidates (n=60) | 26.7% hit, **0.75 s** | 28.3% hit, 17.15 s |
| conditioned on gold present in shortlist (n=28) | **57.1%** | **57.1%** (identical) |
| cookbook two-stage, 22 positives | 81.8% wrong | 68.2% wrong |
| cookbook two-stage, 22 negatives | 72.7% needless | 86.4% needless |
| output tokens for the same 60 decisions | **14,711** | 258,330 |

**Verdict pattern to reuse: buy the latency/token edge, not the accuracy story.** 22.8x
faster and 17.6x fewer output tokens on byte-identical decisions is real and worth wiring --
for narrow forks (cron/worker lanes, guardrail screens, queue triage). As a whole-roster
router it buys nothing our cheap lane did not already do.

### Operational notes from that run

* **Big option sets work but cost scales with option count.** A `Choice` over 214 options
  plus 3 request `Noul`s answered fine in one call (1.7-1.9 s, ~7.8k in / ~2.6k out tokens),
  and 13 batched questions cost ~0.77 s total. So the "batch the questions" rule holds far
  beyond a handful -- but cap the candidate count, it dominates the bill.
* **Key handling:** vendor key into the secrets vault, then run the harness through
  `vault exec <space> -- python3 script.py` so the script reads `os.environ` only. Never
  echo the key in a shell command (the command lands in the transcript) and never print it;
  record a `sha256[:12]` handle in the KB note if you need a provenance marker.
* **Pricing may simply not be published** (every `/pricing` path 404'd). Then report tokens
  and say cost is unknown pending the console's billing view -- do not invent a per-decision
  price to complete the table.
* **Re-derive in the harness's own verifier.** Append the new arm's numbers to the existing
  independent checker (`verify_results.py`: recompute from the raw JSONL, assert the report
  matches and the recorded baselines still re-derive). 11 passed / 0 failed is what makes the
  head-to-head quotable later.
* **Resumable by design:** multi-arm runs append one JSON row per item as each finishes and
  skip already-present keys, so a timeout costs nothing and a rerun is idempotent.

## Reporting rule for this user

He asks for honest value breakdowns, not advocacy. State where the baseline wins, name the
free alternative, and give the cost check. A flattering pitch that the measurements do not
support counts as a failed deliverable, and he will (correctly) distrust the next one.
