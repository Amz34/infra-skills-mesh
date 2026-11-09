# Capability loops: discover → gate → measure

How this box *learns* new capabilities without hand-holding, as wired Sep 2026. Three loops,
deliberately separated, each with a stated boundary. Lives here (not in the gate skill) because
the gate skill `agent-skill-adoption-gate` is **user-owned** — autonomous curation may not write
to it; its policy is unchanged and remains the governing rule.

## Loop 1 — Discover (what's new out there)

- `~/ops/scripts/tool_scout.py` — deterministic GitHub topic/name search for agent-skill and
  agent-tooling repos. Prints identity-only lines (no stars/dates) so the cron monitor hash is
  stable; authenticated via `gh auth token`; re-prints a cached last-good list when every query
  fails, so a rate-limit can never masquerade as "everything changed".
- Cron `tool-scout (capability discovery)` — `0 4 * * *`, deliver telegram,
  `monitor_script` = `~/.hermes/scripts/tool_scout.sh` (a ~6-line `exec` shim to the real script,
  because `monitor_script` must live under `~/.hermes/scripts/`). The agent only runs on a real
  delta. Triage prompt is bounded: **no installs, no vendoring** — candidates become pending
  decisions.
- Monitor-payload rules and the stability proof (run twice, compare `md5sum`): the
  "monitor-gated discovery scout" variant in this skill's SKILL.md.

## Loop 2 — Gate (is it safe to hand the agent this instruction set?)

- `~/ops/scripts/skill-intake.sh <owner/repo> [skill …]` — one command: runs the static review
  (`skills-review.sh`) and writes a **pending decision draft** into `~/brains/ops/decisions/`
  (schema `_SCHEMA.md`; add the row to `INDEX.md`). Inspect-only by construction: never installs,
  never vendors, never touches the skill store.
- Policy, why popularity is not a safety signal, and the pitfalls: skill
  `agent-skill-adoption-gate` (user-owned — read it, don't rewrite it).
- Manual by design and staying that way: the rewrite into Hermes-native form (needs judgement)
  and the per-skill bench run.

## Loop 3 — Measure (prove it beats baseline before trusting it)

- `~/ops/evals/skills-bench/skill_lint.py <skill-dir>` then
  `run_bench.py --skill <name> --evals <evals.json> --runner deepseek --iterations 3
  --with-baseline --max-tokens 24000 --ledger`.
- `--ledger` → `verify-ledger.jsonl` (layer-3 verifier). A skill stays **pending** until it beats
  baseline; token budget is a known confound (re-run at double budget before believing a negative
  verdict).

## What the agent already has, and where to look

- `~/ops/scripts/capability_index.py [--grep X]` → `~/ops/kb/CAPABILITIES.md`: every skill in the
  store plus which curated CLIs are actually on `PATH` (Sep 2026: 205 skills / 15 categories,
  33 of 46 CLIs present). Absent CLIs are listed too — the point is that scope claims stay honest
  and "use a CLI if required" needs no guessing.
- Governance still applies: `~/ops/observability/autonomy.json` + `autonomy_audit.py` /
  `infra_sentinel.py`; L4 + external is banned (external/money = L3 + gate_required). A new
  automated surface must declare its level.

## Open items (pending — do not start without the user's go-ahead)

- A weekly cron that takes pending skill-intake decisions through steps 2–3 (rewrite + bench)
  automatically — it spends tokens, so it needs an explicit yes.
- A `capabilities` pane in the registry (`~/clients/invertio/infra-dashboard`) — a client-code
  change, so it needs approval + a dash-build bump.

Written up as: `~/brains/ops/decisions/2026-09-17-capability-intake-loops.md` (companion:
`2026-09-17-firelab-relation-layer-shelved.md`).
