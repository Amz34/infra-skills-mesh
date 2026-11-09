---
name: verification-before-completion
description: Use before claiming work is done or fixed.
---

# Verification Before Completion

## Overview

**Core principle:** Evidence before claims, always.

**Violating the letter of this rule is violating the spirit of this rule.**

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in this message, you cannot claim it passes.

## The Gate Function

```
BEFORE claiming any status or expressing satisfaction:

1. IDENTIFY: What command proves this claim?
2. RUN: Execute the FULL command (fresh, complete)
3. READ: Full output, check exit code, count failures
4. VERIFY: Does output confirm the claim?
   - If NO: State actual status with evidence
   - If YES: State claim WITH evidence
5. ONLY THEN: Make the claim

Skip any step = lying, not verifying
```

## Verify the verifier

A green ad-hoc script proves nothing if the script itself is broken. Two failures
seen in practice (fire-lab Telegram wiring, 14-Sep-2026):

- **An assertion can be inverted and still look plausible.** `git diff --numstat`
  prints `added<TAB>deleted`; an assertion expecting `"0 1"` failed a correct
  `+1/-0` change. Re-read a FAIL before believing it, and re-read a PASS before
  trusting it.
- **Monkeypatching a module attribute leaks process-wide.** `urllib.request` (and
  any imported module) is a singleton: patching `mod.urllib.request.urlopen` to
  mock one section made *later live checks* silently read the fake payload
  (`KeyError: 'channels'`). Save the original and restore it the moment the mocked
  section ends, or the rest of the run is fiction.
- **A tool's SUCCESS REPORT is not proof the artifact is correct.** A large `write_file` /
  `patch` / `skill_manage` argument can arrive truncated while the tool still reports
  success; the giveaway is a literal `[truncated]` marker written into the file mid-sentence
  (hit 2026-09-15 in a SKILL.md, and repaired only after a scan caught it). Keep individual
  writes small (a few hundred chars; split big additions into several patches) and verify the
  artifact, not the report: `search_files(pattern='\[truncated\]', path=<dir>)` must return 0,
  then re-read the edited region before building on it.
- **A PASS can be served by the wrong process.** A readiness check returned
  `200` on a port that a *pre-existing, unrelated* service was already
  listening on — the app under test was never up, and the "verified" verdict
  was fiction. When a probe passes suspiciously fast, or a health check
  succeeds before the start step could have finished, confirm WHAT answered
  it (`ss -ltnp` / the probe's own identity string) and pin a port you
  verified is free before trusting the result.
- **A runner that bootstraps into the shared tool venv verifies a mutated
  environment.** Installing a project's requirements into the agent's own
  venv bumped `pydantic`/`fastapi`/`uvicorn` pins and left the *tool* broken
  — the green result described a state that no longer existed anywhere.
  Pin the project venv in the runner's manifest, and `pip check` the shared
  venv before and after any verify pass that installs anything.
- **A FAIL is not evidence about the product until your own assertion is ruled out.**
  Four consecutive FAILs in one pass (fire-lab, 19-Sep-2026) were *all* harness bugs;
  "fixing" the product first would have broken working code. The three shapes it took:
  - *Contradictory assertion* — demanded BOTH `"playwright"` AND `"Traceback"` in one
    output. A friendly message can never contain both, so the check could not pass.
  - *Self-defeating assertion* — `made.is_file() and not (Path.cwd() / rel).exists()`:
    cwd *was* the repo root, so it required the file's own parent to be absent.
  - *Stale hardcoded expectation* — expected 6300 anchors at 320px; truth is
    `sum((size // s) ** 2 for s in (8, 16, 32))` = 2100. The tool was right.
  Reproduce the failing step BY HAND first (one direct CLI call: read rc, full output,
  artifacts on disk) before editing a line of product code. Derive expected values in
  the script from the thing under test — a literal that passed by luck is a latent bug.

## Make Verification Canonical

A temp `hermes-verify-*` script is the right vehicle for ONE pass. If you are still
rewriting the same throwaway check every session, the real defect is that the repo has
no verifiable entrypoint — and the harness says so itself:
`No canonical test/lint/build command was detected`.

Fix it at the root, all three parts, in this order:

1. **Add the entrypoint.** Copy `templates/Makefile.verify` → `Makefile`.
   `make test` is detected as canonical; a bare `venv/bin/python -m pytest tests` is not.
   Recipes MUST be tab-indented — verify with `cat -A Makefile | grep -c "^\^I"`.
2. **Promote the ad-hoc check into the suite** so the temp script is never needed again,
   and make it cheap: pin the *ordering/contract*, not the expensive work. The permanent
   regression for "creates `--outdir` before exporting" runs the CLI with a MISSING
   checkpoint and asserts the directory now exists — it can only pass if the mkdir
   precedes the build, costing ~5s instead of a 40s real export.
3. **Mutation-test the new test** before trusting it: back the file up, remove the fix,
   run — it MUST fail — restore, then confirm no residue (`grep -c MUTATION <file>` → 0)
   and that `git diff --stat` shows only the intended change. A regression test that
   passes with the fix reverted is decoration.

**Run every gate the repo names, not just the test command.** A real workspace answers to more
than `make test`: the invertio lane has `make lint` (new-syntax diff), `make test` (golden cases),
`make check` (`init.sh` full path + harness gate score), `make vcr` (WIP=1 feature check) and
`make clean-check` (clean-state dimensions). Run each target the harness names, read each exit
code, and read the *messages* — `make vcr` legitimately answers "no feature in progress", which is
a green result, not a missing verification.

**Put the evidence where the repo wants it, or it counts as scratch.** The same workspace polices
its top levels (`clean-check`) and only records evidence for *tracked* features
(`evidence/<feature-id>-*.md`). So a verified non-feature change (a bug found while measuring, a new
QA script) must NOT be given an invented feature id or a stray file in `evidence/` — record the
command-by-command result in our own ops kb instead. Expect a harness to keep reporting
"unverified" while that change is uncommitted (WIP=1, no tracked feature) even with every gate
green: state that plainly and offer the commit/PR, rather than inventing a feature to silence it.

Related principle for the tools themselves: create output destinations up front and name
the missing path in one line (`[FAIL] no checkpoint at …`) rather than dying with a raw
traceback *after* expensive work. Session detail and reproductions:
`references/ad-hoc-verification-harness.md`.

## Common Failures

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Linter clean | Linter output: 0 errors | Partial check, extrapolation |
| Build succeeds | Build command: exit 0 | Linter passing, logs look good |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed |
| Regression test works | Red-green cycle verified | Test passes once |
| Agent completed | VCS diff shows changes | Agent reports "success" |
| File written/patched | Re-read the edited region (0 `[truncated]` markers) | Tool success report |
| Requirements met | Line-by-line checklist | Tests passing |

## Red Flags - STOP

- Using "should", "probably", "seems to"
- Expressing satisfaction before verification ("Great!", "Perfect!", "Done!", etc.)
- About to commit/push/PR without verification
- Trusting agent success reports
- Relying on partial verification
- Thinking "just this once"
- Tired and wanting work over
- **ANY wording implying success without having run verification**

## Rationalization Prevention

| Excuse | Reality |
|--------|---------|
| "Should work now" | RUN the verification |
| "I'm confident" | Confidence ≠ evidence |
| "Just this once" | No exceptions |
| "Linter passed" | Linter ≠ compiler |
| "Agent said success" | Verify independently |
| "I'm tired" | Exhaustion ≠ excuse |
| "Partial check is enough" | Partial proves nothing |
| "Different words so rule doesn't apply" | Spirit over letter |

## Key Patterns

**Tests:**
```
✅ [Run test command] [See: 34/34 pass] "All tests pass"
❌ "Should pass now" / "Looks correct"
```

**Regression tests (TDD Red-Green):**
```
✅ Write → Run (pass) → Revert fix → Run (MUST FAIL) → Restore → Run (pass)
❌ "I've written a regression test" (without red-green verification)
```

**Build:**
```
✅ [Run build] [See: exit 0] "Build passes"
❌ "Linter passed" (linter doesn't check compilation)
```

**Requirements:**
```
✅ Re-read plan → Create checklist → Verify each → Report gaps or completion
❌ "Tests pass, phase complete"
```

**Agent delegation:**
```
✅ Agent reports success → Check VCS diff → Verify changes → Report actual state
❌ Trust agent report
```

## When To Apply

**ALWAYS before:**
- ANY variation of success/completion claims
- ANY expression of satisfaction
- ANY positive statement about work state
- Committing, PR creation, task completion
- Moving to next task
- Delegating to agents

**Rule applies to:**
- Exact phrases
- Paraphrases and synonyms
- Implications of success
- ANY communication suggesting completion/correctness
