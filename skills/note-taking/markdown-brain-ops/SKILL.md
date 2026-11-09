---
name: markdown-brain-ops
description: Build or sweep a markdown brain / kb repo.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
      - knowledge-management
      - markdown
      - decisions
      - cron
      - sweep
    related_skills:
      - hermes-memory-ops
      - obsidian
      - session-librarian
---

# Markdown Brain Ops

Build and maintain a *curated* markdown knowledge layer that an agent can route through
cheaply: an INDEX routing table, provenance-tagged claims, decision files with explicit
reversal conditions, and a deterministic sweep so rot gets caught without spending tokens.
Borrowed from `phuryn/pm-brain` (MIT) and hardened with local pitfalls.

**Live instance:** `~/brains/ops/` (Ops Brain). Legacy raw layer: `~/ops/kb/` (now frozen input).
Weekly cron: `ops-brain-sweep-weekly` (script-only) + `ops-brain-weekly-compression` (agentic).

## When to use

- User wants durable knowledge that survives sessions without filling `MEMORY.md`.
- Flat `kb/*.md` folders have grown past ~20 files and nothing is routed through an index.
- Decisions are buried in chat/session history with no "why" or "what would reverse this".
- Building a second brain for a new brand/client (see *Per-brain isolation*).
- Reviewing a sweep report, chasing decision debt, or promoting insights.

## Layout (copy this)

```
brains/<brain>/
  README.md          why this brain exists, what belongs here, cadence
  INDEX.md           ROUTING TABLE - read first, always. question -> file
  AGENTS.md          contract for any agent writing here
  rules/             provenance.md, writing.md, maintenance.md
  knowledge/         curated, durable, INDEX-listed (.md)
  decisions/         YYYY-MM-DD-<slug>.md + INDEX.md + _SCHEMA.md
  hypotheses/        open bets: statement, confidence, evidence, decision trigger
  ingestion/         per-artifact working notes (dated, disposable)
  source/            audit anchor (here: symlink to ~/ops/kb) - NEVER edit
  maintenance/       known-findings.json (suppressions w/ expiry) + log/sweep-*.md
  scripts/           sweep_structural.py, test_sweep.py
```

## Core rules

1. **INDEX-first.** Agents read `INDEX.md` and follow links; never bulk-load the tree.
   A file referenced by no INDEX is an orphan (the sweep flags it).
2. **Two layers, never merged.** `source/` = immutable raw history (do not move or rewrite
   legacy files - skills and crons reference their old paths). `knowledge/` = curated synthesis.
3. **Every claim carries provenance + confidence.** Path tag `[source/x.md]` when a real file
   exists; otherwise `(memory-rule, date)`, `(chat, no artifact, date)`, `(stakeholder-verbal, who, date)`,
   `(intuition, who, date)`, `(industry-knowledge)`, `(verified-external, url, date)`.
   Use the weaker tag when in doubt - never inflate a memory into a document.
4. **Claim types are a closed enum:** observation / interpretation / hypothesis / assumption /
   decision / spec / risk / question. Bullets read `- **observation:** ... confidence 0.6`.
5. **Decisions have an expiry pressure valve:** every decision file states *What would reverse
   this* in testable terms, plus a reversal-check date. `Status: pending` is an agent draft;
   only the user flips it to decided/killed/superseded.
6. **Promotion bar:** >=3 independent observations of the same pattern from the same
   brand/persona before it becomes knowledge. Never silently demote - cite the original
   premise by name and draft the change.
7. **Suppressions expire.** `maintenance/known-findings.json` entries need `reason` + `expires`;
   an expired suppression itself becomes a finding.
8. **Files in English; chat in the user's language.** Never put secrets in a brain.

## Ingest workflow

1. `read INDEX.md` of the target brain -> identify the affected 1-3 files.
2. Write `ingestion/YYYY-MM-DD-<slug>.md`: source, raw facts, open questions. Date-stamp rows.
3. Promote only what clears the bar into `knowledge/` (update the file + its INDEX row).
4. If the work settled a choice, draft `decisions/YYYY-MM-DD-<slug>.md` with `Status: pending`
   and a reversal condition; add it to `decisions/INDEX.md`.
5. Close with 2-4 bullets: resolved / drafted for confirmation / surfaced.
6. `git -C ~/brains/ops add -A && git -C ~/brains/ops commit -m "..."` (every brain is a repo).

## Sweep workflow

```bash
python3 ~/brains/ops/scripts/test_sweep.py        # prove the checks still fire
python3 ~/brains/ops/scripts/sweep_structural.py  # silent when clean, else findings
```

Cron runs the wrapper `~/.hermes/scripts/ops_brain_sweep.sh` as a `no_agent` job
(Friday 11:30 UTC = 17:00 IST): empty stdout = silent, so the sweep must print **only** findings.
Checks: stale-knowledge (42d), pending-decisions (14d), broken-links, untagged-evidence,
bad-claim-type, stale-evidence (30d), orphan-files, dead-source-refs, expired-suppression.

Then one agentic pass (Friday 12:00 UTC) for what grep cannot do: contradictions between
files, recurring patterns worth promotion, decision debt worth escalating, and 3-5 bullets
back to the user.

## Pitfalls (learned the hard way - keep them fixed)

- **`**bold**` vs nested bullet.** A nested-bullet unwrap test on `head[:1] in ("-", "*")`
  eats the first `*` of `**interpretation:**` and every claim row looks untagged.
  Guard with `and head[:2] != "**"`.
- **Claim-label regex must allow the colon inside the bold:** `^-\s+\*\*([A-Za-z][A-Za-z /-]*?):?\*\*`.
  The colon-outside form (`**observation**:`) never matches the written convention.
- **Do NOT flag every unknown bold label.** Structural labels (`**Last evidence:**`,
  `**In progress:**`, `**Pending:**`) are not claims. Use a DENY list of claim-ish words
  (fact/truth/hunch/guess/belief/opinion/...) instead of a whitelist of allowed labels.
- **Exclude `maintenance/` and `source/` from the md scan** or the sweep's own logs become
  findings and the report self-amplifies every week.
- **A clean sweep proves nothing.** `test_sweep.py` injects exactly one fault per check
  (plus negative cases for structural labels and tagged rows) in a temp copy. Run it after
  every edit to the sweep.
- **Backticks around a tag hide it** from naive detection - keep tags bare at bullet start.
- **Don't install a framework for this.** pm-brain's markdown+git+INDEX model is the whole
  value; a vector DB is unnecessary when the corpus is a few hundred routed files.
- **One brain per brand.** Single-PM brains assume 10-20 hypotheses and INDEX-first routing;
  merging brands collapses the routing and leaks context across clients.

## Verification before claiming done

- `scripts/test_sweep.py` -> all cases PASS, exit 0.
- Live sweep -> **empty stdout**, exit 0, log written under `maintenance/log/`.
- `git log --oneline` shows the commit; INDEX rows point at files that exist.
