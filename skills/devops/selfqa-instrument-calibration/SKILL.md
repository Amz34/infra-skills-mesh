---
name: selfqa-instrument-calibration
description: Use when auditing your own QA gates or graders.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [self-qa, verification, evals, instrumentation, guard, calibration]
    related_skills:
      - verification-before-completion
      - agent-autonomy-governance
      - content-integrity-guardrail
      - hermes-agent
---

# Self-QA instrument calibration

Every gate, grader, verifier or "self-QA" script is an **instrument**. An
instrument that cannot return the opposite answer carries no information. This
skill is the checklist for auditing instruments, born from a real audit on
hermes-vnic (2026-09-29) where four independent instruments were wrong.

## When to use

- You are writing/fixing a grader, verifier, cron gate, or eval check set.
- A gate has never failed (suspicious) or fails constantly (suspicious).
- You are about to trust a number an instrument produced ("credit +0.00",
  "0/220 measured", "all checks pass").
- A command was refused by a harness guard with an unrelated reason.

## The four bugs to look for (all four were real here)

1. **Type confusion in the record you read.** `skills-bench` writes
   `grading = {"passed": <COUNT:int>, "total": <n>, "pass": <bool>}`. Reading
   `passed` as a boolean makes `12/13` identical to `13/13` → every measured
   skill reported credit `+0.00` for weeks, and two genuinely load-bearing
   skills were labelled RENTAL. Read the count pair first, fall back to the
   bool, never coerce an int into a truth value.
2. **A check no correct answer can pass.** A regex expecting `^1\.` never
   matches models that write `**1.**`; a question-mark check anchored to a
   line-end never matches a trailing emoji. Result: `pass_rate = 0.0%` for
   *both* conditions and a meaningless headline. Enforce achievability: every
   check must be observed passing in at least one condition, else fix or drop it.
3. **Non-discriminating metrics.** A procedure score that puts all 220 skills in
   a 4–10 band, `thin = 0`, cannot rank anything. Always print the score bands
   and assert a minimum spread in the self-test.
4. **Fail-closed guards tripped by prose.** The Hermes terminal guard walks
   *referenced scripts transitively* and fails closed on referenced regular
   files >1 MiB. A docstring that merely mentions a big `.jsonl`/`.db` path
   locks out every command that references that script. See
   `~/brains/ops/knowledge/infra/hermes-lifecycle-guard-oversize.md`.

## Six failure modes found in the wild (layer-3 lane, 2026-10-04)

A whole verification lane sat dead for 4 days on one of these. Check them in order:

1. **Two roundings compared as if one.** `int(chars/4)` (floor) vs `round(chars/4)`
   (banker's) differ by 1 token on a 4,400-token index → a healthy store "failed".
   Never assert equality between two different arithmetic paths on a float boundary:
   compare within an explicit band (±1 token) **and** assert the raw input (char count)
   too, so real drift is still caught. Then re-run the gate and confirm the detail line
   shows both numbers.
2. **The verdict depends on a side channel.** The restore drill's PASS/FAIL was read back
   from its shared log, and an unchecked `>> $LOG` write made a *successful* restore report
   FAILED. Capture each run to a per-run file, compute the verdict from that, and give a
   bookkeeping fault its **own exit code** (e.g. 3 = "work passed, logging failed") that
   says so in words. A telemetry fault must never impersonate a functional failure.
3. **Whack-a-mole invariant.** "No heavy service has unbounded swap" scans a population
   one offender at a time: fixing warp-svc just revealed chrome-oauth. When an invariant
   quantifies over a set, ship a **sweep** that fixes the whole set in one pass
   (`~/ops/scripts/swap_ceiling_sweep.py --apply`) and schedule it, instead of patching the
   single unit the check happened to name. Apply such caps live (`systemctl set-property`)
   rather than restarting services that other lanes depend on.
4. **A referenced capability vanished, the check didn't.** `proof_check` pointed at a cron
   lane whose jobs were deleted → the offer became unsellable *and* the check name stopped
   resolving. Do not delete the check and do not rename it to whatever still exists. Make the
   invariant **"LIVE or ACCOUNTED FOR"** (lane exists OR a decision record in
   `~/brains/ops/decisions/` explains its absence) and repoint the dependent artifact. A
   capability must not be able to disappear silently.
5. **No lane-level watchdog.** Even a perfect instrument is useless if nobody notices it is
   switched off. `~/.hermes/scripts/lane_staleness_guard.py` (cron `*/30`) alerts on a lane
   that is dead, deliberately off, or stalled, with 24 h dedupe. Add a lane guard whenever
   you add a verification lane.
6. **Instrument noise calibrated to zero signal.** Flagging every `cost_status=None` row
   fired daily on genuinely free-tier calls. Recalibrate the *rule* to the actual risk
   ("spend recorded without a cost status", ≥3 calls or ≥$0.25), keep the benign row in a
   comment, and never let a monitoring lane cry wolf — that is how a 4-day outage is born.

Also: every gate needs a **negative control in the eval suite** (a fixture that must FAIL),
and the suite must be scored and run on a schedule — `~/ops/evals/capability/capability_eval.py`
is the working example (8 checks, `verdict: 8/8`, exit 1 on any miss).

## Procedure

1. **Make the instrument produce a distribution, not an opinion.**
   Print counts by class, score bands, and the median. If everything lands in
   one bucket, the metric has no resolution — fix it before using it.
2. **Write an independent verifier next to it** (`~/ops/verify/*_check.py`) with:
   - fixtures whose *expected* answer is true by construction (a dense procedure
     fixture must score high; a narrative habit fixture must score low),
   - a **negative control**: an assertion that must FAIL, proving the verifier is
     capable of reporting failure,
   - a **reproduction check**: recompute one headline number by a different code
     path (e.g. skill count via `find | wc -l`) and compare,
   - a **discrimination check**: bands non-degenerate / minimum gap between
     fixtures.
   Exit 0 pass, 1 fail, `--json` for cron. Never let the verifier import the
   audit's internals as truth — fixtures define truth.
3. **Wire it into `~/ops/verify/daily_selfqa.sh`** (silent on pass, prints on
   fail). New checks go in as: self-heal → instrument self-test → real assertion.
4. **Change instrument and verifier in the same commit.** A verifier that kept
   the old contract is how you find out you changed semantics — update its
   fixtures *with* an explicit comment saying what changed and why.
5. **Measure once for real before claiming a capability.** Inventory is not
   evidence. Run the benchmark on >=1 skill/case with `--with-baseline` and
   report the with-vs-without gap, per-check, plus the iteration count.

## Measure skill/harness credit (skills-bench)

```bash
cd ~/ops/evals/skills-bench
# 1. write evals.<skill>.json: prompt + deterministic checks (see evals.hyderabadi-urdu.json)
# 2. validate the harness wiring for free, then measure for real:
./run_bench.py --skill <skill> --evals evals.<skill>.json --runner stub  --iterations 1 --with-baseline --label smoke
./run_bench.py --skill <skill> --evals evals.<skill>.json --runner deepseek --iterations 3 --with-baseline --label <skill>-v1
# 3. audit the whole store (credit, index cost, thin skills):
~/ops/evals/harness-credit/harness_credit_audit.py --top 15
~/ops/verify/harness_credit_check.py        # 17 checks incl. int-grading regression
```

Credit numbers that matter: `credit_pass` (all checks) for headlines and
`credit_check` (mean fraction of checks passed) for the signal — the latter
survives one impossible check. A pair with no gap (`1.0 vs 1.0`) is a
**saturating eval**: it proves nothing about the skill, only about the eval.

**Re-grade stored outputs before you pay for a re-run.** When a bench result
looks like an instrument defect, `~/ops/evals/skills-bench/regrade.py <run-dir>`
re-applies a revised eval set to the outputs already in `benchmark.json` —
free, no API calls, and it tells you whether the loss was the skill or the
grader. Observed 2026-09-29 on `inbound-content-guardrails`: first pass
`with_skill 0-50%` vs `baseline 50-100%`; after recalibrating the checks and
re-grading the *same* outputs, `with_skill 100%` vs `baseline 75%` (then
confirmed with one fresh run for the ledger). Never delete a port, skill or
tool on a single uncalibrated bench loss.

## Pitfalls

- Do not put the literal three-token gateway-lifecycle invocation, or a
  `~/…/state.db` path, in any script you want to be runnable — the guard reads
  script contents, including docstrings and comments.
- Truncating a `.log` held open by a long-running unit does not shrink it
  (writer keeps its offset → sparse NUL padding). Rotate only per-run reopened
  `.jsonl`/`.ndjson` (`rotate_oversize_ledgers.py`), never live logs.
- Prefer the guard's own functions as the oracle over reimplementing its rules
  (`cron.lifecycle_guard._read_referenced_script`) so the audit cannot drift.
- A "verifier" that always exits 0 is decoration. Ship the negative control.
- **Three regex bugs that fabricate losses** (all three hit the same eval set):
  `[^.]{0,70}` between two clauses breaks the moment the model writes two
  sentences — use `(?is)` plus `[\s\S]{0,N}`; a `not_contains` check on a phrase
  from the payload punishes a model that *quotes the payload verbatim*, which is
  usually exactly what the skill instructs; and negation vocabulary that only
  covers `do not|won't` misses `did not`, `have not`, `nothing sent`,
  `no payment scheduled` — the baseline's phrasing wins and the graded skill
  loses. Write the vocabulary from the recorded outputs, not from imagination.
- Compare conditions on the same vocabulary: if the check patterns read like the
  *baseline's* prose, the instrument is biased toward the baseline by
  construction.

## Files

- `~/ops/evals/harness-credit/harness_credit_audit.py` — credit + procedure audit
- `~/ops/evals/skills-bench/regrade.py` — re-grade a stored run with a revised eval set (free)
- `~/ops/verify/harness_credit_check.py` — 17-check verifier (negative control incl.)
- `~/ops/verify/guard_trip_audit.py` — guard-fail-closed audited with the real oracle
- `~/ops/verify/rotate_oversize_ledgers.py` — keeps ledgers under the 1 MiB guard cap
- `~/ops/patches/reapply_hermes_patches.sh` — re-apply local Hermes patches post-upgrade
- `~/ops/verify/daily_selfqa.sh` — the daily gate all of the above hangs off
