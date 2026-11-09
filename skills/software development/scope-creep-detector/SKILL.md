---
name: scope-creep-detector
description: "Use when a diff outgrew its stated intent."
version: 1.0.0
author: Hermes Agent (rewrite of Shubhamsaboo/awesome-llm-apps agent_skills, Apache-2.0)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [code-review, diff, scope, pr-review, client-deliverable]
    related_skills: [github-code-review, requesting-code-review, simplify-code, project-state-audit]
---

# Scope Creep Detector

Compare what a change **claims** to do against what it actually **touches**, and
return a disposition per path: keep, split, or justify.

**Core principle:** the detector produces *review prompts*, never proof of intent.
A path with no token overlap may still be required; a path with overlap may still
be creep. The script is deterministic and offline; the judgement is yours.

**Why this exists:** most review pain is not bad code, it is a diff that mixes
two or three unrelated concerns, so nobody can review any of them properly.
Detecting that is mechanical. Deciding what to do about it is not.

## When to Use

- Before opening a PR or a merge request, to check the branch matches its title.
- Before sending a client deliverable (microsite, script, dashboard, ad lane) —
  confirm the work matches the agreed scope and nothing extra rode along.
- When a diff feels heavier than the task felt, or "just this fix" turned into
  ten files.
- When reviewing an agent's / subagent's output branch: agents over-deliver
  silently, and this catches it cheaply.
- When writing a PR description and you need the honest file list.
- Rejecting an oversized hunk during review: `oversized_hunk` points at hunks
  that mix separable concerns.

**Not for:** a single-file change that obviously matches its intent (the script
will say so; do not run a ceremony around it), or judging code quality — that is
`requesting-code-review` and `simplify-code`.

## Prerequisites

- `python3` (stdlib only, no packages, no network).
- A git repo with a diff: working tree, `--staged`, `--base <ref>`, or a patch
  piped in on stdin.

## How to Run

```bash
SC="$HOME/.hermes/skills/software-development/scope-creep-detector/scripts/scope_creep.py"

# working-tree changes vs one-paragraph intent
python3 "$SC" --repo . --intent "fix parser dropping empty tokens" --md

# JSON for programmatic use (stable key order, deterministic output)
python3 "$SC" --repo . --intent "..." --json

# staged only / against a branch / from a saved or piped patch
python3 "$SC" --repo . --staged --intent "..."
python3 "$SC" --repo . --base main --intent "..."
git diff main...HEAD | python3 "$SC" --diff - --intent "..."

# tighten or loosen the hunk-churn threshold (default 80 changed lines)
python3 "$SC" --repo . --intent "..." --hunk-threshold 150
```

Exit codes: `0` = ran fine (findings or not), `1` = bad usage / not a git repo /
empty intent. A clean diff is not an error.

JSON keys: `verdict`, `diff_source`, `intent`, `stats` (files, subsystems,
additions, deletions, oversized_hunks, formatting_only), `in_scope[]`,
`likely_creep[]` (with `reason`, `signals`, `suggested`), `new_deps[]`,
`api_renames[]`, `config_edits[]`, `caveat`.

## Signals (deterministic, cheap)

| Signal | Meaning | Default disposition |
|---|---|---|
| token overlap with intent | path shares a usable noun with the stated intent | Keep (still verify) |
| no overlap + separate subsystem | unrelated area touched | Split |
| `new_dep` | added package in requirements / pyproject / package.json (a same-name removal = constraint edit, not new) | Split |
| `api_rename` | removed `def`/`async def`/`class`/`function` with an added declaration of the same kind within 12 diff lines | Split |
| config / CI / build path edit (`.tf`, `.yml`, `.yaml`, `.toml`, `.github/`, Dockerfile, Makefile) | cross-cutting edit | Justify or split |
| `oversized_hunk` | > threshold added+removed lines inside one hunk | Keep or justify |
| `formatting_only` | equal removed/added lines, identical once all whitespace is removed | Split |
| subsystem count >= 3 | context, not a failure | Name it in the report |

## Procedure

1. **Write the intent as one paragraph in the requester's words** — the task,
   ticket, commit subject, or client ask. Do not paraphrase it into something
   broader. Vague intent is the main cause of false flags; if the intent is
   vague, say so in the report instead of trusting the labels.
2. **Run the script** in `--json` (parse it) and `--md` (human report).
3. **Verify every flagged path by hand before you claim anything.** Open the
   file, read the hunk, decide whether the change is *required* for the intent
   to work (then `justify`), *separable* (then `split`), or *unexplained*
   (then ask the author — do not guess a motive).
4. **Report as a table**: `path | disposition | evidence`. Evidence is the
   signal plus what you saw: "adds `flask`; nothing in the intent needs it".
5. **Nothing is edited by this skill.** A recommendation to split is a
   suggestion to the author; do not restructure their branch on your own
   initiative. If they ask you to split it, that is a new task.
6. **Client work:** run the same check, but the report goes to the private
   owner/dev channel only, with client identifiers minimised. Never paste
   client code, tokens, or paths into a public post or a lead-facing document;
   keep brands isolated (one client's material never appears in another's).

## Output contract

```
## Scope report
Intent: <verbatim>
Diff: N files, +A/-D, M subsystems

| path | disposition | evidence |
|---|---|---|
| src/parser.py | keep | overlaps intent: "parser"; single hunk |
| requirements.txt | split | adds dependency flask; not needed by intent |
| .github/workflows/ci.yml | justify | CI edit; needed for the new test job to run |

Caveat: <where the heuristic is weak on this diff>
```

## Pitfalls

- **Recall-biased on purpose.** Zero overlap is a prompt to look, not a verdict.
  Vague intents, test fixtures, migrations, and generated files routinely
  legitimately share no tokens with the intent line.
- **Rename detection is positional, not semantic.** A deleted function next to
  an unrelated new function reads as a rename. Confirm call sites before saying
  "API break".
- **Lockfiles are not parsed** — transitive churn hides direct additions. Read
  the manifest, not the lock.
- **Whitespace-only is narrow:** reordered imports or quote-style rewrites may
  not qualify as `formatting_only`.
- **A large hunk is not automatically bad.** One coherent algorithm can be 200
  lines. The signal points at *mixed* concerns, not size.
- **Never assert motivation.** Report the evidence; the author owns the "why".
- **Do not run this on an already-merged diff and treat it as blame.** It is a
  pre-review instrument.

## Verification

```bash
SC="$HOME/.hermes/skills/software-development/scope-creep-detector/scripts/scope_creep.py"
python3 -m py_compile "$SC"                                  # syntax
python3 "$SC" --repo . --intent "x" --json | md5sum          # run twice: identical hash = deterministic
grep -cE "socket|urllib|requests\.|http" "$SC"               # must be 0: offline, no egress
git -C . status --porcelain                                  # unchanged by the tool: read-only
```

Expected on a healthy run: `0` network refs, identical md5 across two runs, and
`git status` exactly as it was before you ran it.

## Provenance

Concept and signal set: `Shubhamsaboo/awesome-llm-apps` → `agent_skills/scope-creep-detector`
(Apache-2.0). Upstream material frozen read-only at
`~/ops/vendor/skills/Shubhamsaboo/scope-creep-detector/` with hashes; this file and
`scripts/scope_creep.py` are an independent Hermes-native implementation (single
file, stdlib only, no upstream imports), rewritten to the store's index and
safety conventions.
