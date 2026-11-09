# Executable-model upgrade pass ("data + auditor" → a tool)

Framing that generalises: a published **model** — a roster, an org chart, a policy file, a config
registry — that ships only as JSON plus an auditor is *inert*. A stranger cannot use it, predict it,
or test it. The upgrade that makes such a repo genuinely strong is to make every declaration
executable, then prove it on more than one OS. The line that sells it: *"You must be able to
predict, grep and unit-test which seat picks up a task — otherwise the org chart is fiction."*

## The five moves (in the order that keeps CI green)

1. **A deterministic CLI over the declarations.** `governance/router.py`: text in → the responsible
   entry out (owner, plane, autonomy level, cost tier, confidence), the contracts that bind it, and
   whether a human approval gate applies. Deterministic and stdlib-only — if the router needs a
   model call, the repo can no longer demonstrate the property in CI.
2. **Cost/limit envelopes as enforceable promises.** `governance/budget.py`: every tier must declare
   a ceiling; a missing ceiling is a finding (`E_NO_CEILING`), spending past it is a finding
   (`E_OVER_BUDGET`). "No tier is unbounded spend" is checkable; "we watch spend" is not.
3. **An append-only telemetry ledger.** `telemetry/ledger.py`: one JSONL line per sample,
   `rollup()` for max/avg/window, threshold alerts, `--json` output. Answers "has it been getting
   worse" with data — and is the natural consumer of the cross-platform null-handling
   (`references/cross-platform-ci-matrix.md`).
4. **Packaging + docs so it installs and explains itself.** `pyproject.toml` (bump version, dev
   extras `pytest/pytest-cov/ruff`), `CHANGELOG.md`, `docs/design.md` (the *why*, one page), and a
   hand-coded SVG diagram with `role="img" aria-label` (no image generation needed).
5. **Breadth proof.** Widen CI to the OS × Python matrix, raise the auditor's rule-code count as new
   invariants land, and re-measure every number in the README.

## Verification discipline that makes it credible

- `ruff check .` + `pytest` + `pytest --cov` locally, using the *same* commands as the repo's
  `.hermes/environment.json` recipes so `hermes verify` reproduces them (build + test + start).
- New invariants arrive WITH tests; an invariant without a test is a README claim.
- Re-measure after the suite grows: adding one regression test moved this suite 32→33 tests and
  coverage 96%→94%. Badge, numbers table and the rendered "tests-pass" screenshot must all move in
  the same commit — a screenshot reading `32 passed` next to a badge saying 33 costs more
  credibility than the badge ever bought.
- Regenerate every asset from a fresh capture of the *current* code; a screenshot of old output is
  the visual version of a stale badge.

## Where the same pass lands on the operator's own infra

Publish from the private source through a scrub filter, then add a drift watchdog so the public copy
cannot rot silently: skill `agent-autonomy-governance`,
`references/derived-artifact-drift-watchdog.md`. That watchdog immediately paid for itself — the
published roster carried 6 of up to 22 routing signals per entry because the generator had capped
the list, and both the repo's own audit and the CI were green while it was wrong.
