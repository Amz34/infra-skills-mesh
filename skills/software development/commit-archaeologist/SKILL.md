---
name: commit-archaeologist
description: "Use when tracing why a line, function or file exists before changing it: introduction commit, full timeline, repeated co-changes, intent signals from commit messages. Offline git forensics, stdlib-only."

license: Apache-2.0 (script), MIT (this page)

metadata:
  category: software-development
  tags: [git, forensics, refactor, history, offline]
  source: "Adapted from Shubhamsaboo/awesome-llm-apps (agent_skills/commit-archaeologist, Apache-2.0); script vendored unmodified in scripts/."
metadata:
  version: 1.0.0
  platforms: [linux, macos]
---

# Commit Archaeologist

Read the history of a line before you touch it. Answers three questions git log alone
does not: who introduced this, what always changes together with it, and what the commit
messages say the intent was.

## When to use

- Before editing a line whose purpose is unclear ("why is this here?").
- Before deleting or rewriting a function: check whether history shows failed attempts.
- When a file keeps regressing and you need the pattern of past fixes.
- During review of legacy code inherited from a previous session or another author.

## When not to use

- On an untracked file, or a repository where history was squashed at import.
- As a substitute for reading the code. It gives you context, not correctness.
- For blame games: the output names commits, not people, on purpose.

## Prerequisites

- A real git repository (`git rev-parse --show-toplevel` must succeed).
- The file must be tracked (`git ls-files` match).
- Python 3.9+, no third-party packages, no network.

## How to run

```bash
# whole file
python3 $HERMES_SKILLS_DIR/software-development/commit-archaeologist/scripts/archaeologist.py <repo> <file>

# a specific current line range
python3 .../archaeologist.py <repo> <file> --lines 40-55

# machine-readable, for piping into further analysis
python3 .../archaeologist.py <repo> <file> --json
```

## How to read the output

| Block | Meaning |
| --- | --- |
| `COMMIT ARCHAEOLOGIST: <file>` + `Introduced by <hash> <subject>` | the commit that created the file, or the traced range |
| `TIMELINE` | every commit touching the file, newest first, with a coarse intent label (`feat`, `fix`, `other`) derived from the subject |
| `REPEATED CO-CHANGES` | files that changed in the same commits (`9x README.md`) — the coupling map |
| `INTENT SIGNALS` | phrases in commit subjects that state purpose; `none found` when the history is uninformative |

## Pitfalls

- `Introduced by` on a modern file often points at a bulk import commit; read `TIMELINE`
  instead and find the first semantic change.
- Renames are followed (`--follow`), so old paths appear in the timeline — expected.
- Co-change counts include mechanical commits (format sweeps, version bumps). Weigh the
  subjects, not the raw count.
- History argues intent; it does not prove the current code still does what the message said.

## Verification

Run it on a file you already understand and check the timeline reflects what you know.
A first run on `Makefile` in a known repository is a sufficient smoke test:

```bash
python3 .../archaeologist.py /path/to/repo Makefile
```

## Attribution

Script vendored unmodified from `Shubhamsaboo/awesome-llm-apps`
(`agent_skills/commit-archaeologist/scripts/archaeologist.py`, Apache-2.0). See
`scripts/ORIGIN.md` in this directory. This page is our own operational wrapper.
