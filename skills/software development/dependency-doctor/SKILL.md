---
name: dependency-doctor
description: "Use when auditing a dependency manifest (requirements.txt, pyproject.toml, package.json) for stdlib shadowing, abandoned backports, unpinned ranges and intra-manifest conflicts. Offline static autopsy, no installs."


license: Apache-2.0
compatibility: Python 3 stdlib only. Offline by default.

metadata:
  hermes:
    tags: [dependencies, supply-chain, audit, python, node]
metadata:
  version: 1.0.0
  platforms: [linux, macos]
  author: Hermes + Aamir
---

# Dependency Doctor

## When to use

- Before shipping anything that has a manifest: a small service, a client script bundle,
  a CI lane, a container image.
- When a build fails with a weird import error that looks like the wrong package won.
- When inheriting a manifest you did not write and need a fast risk read.
- As the dependency layer of a pre-ship gate (pairs with `ci-lane`, `verification-first`).

## When not to use

- Do not use it as a CVE scanner. It does not query a vulnerability database.
- Do not use it to decide upgrades. It reports risk signals; the upgrade decision is yours.

## What it checks

| Class | Signal |
|---|---|
| Shadowing | A dependency whose name shadows a Python standard-library module (`json`, `email`, `typing`) - the import may resolve to the wrong package |
| Abandoned backports | Backport shims (`typing`, `dataclasses`, `enum34`) that pin old interpreters or are dead on modern ones |
| Unpinned | Bare names or open ranges (`requests`, `urllib3>=1.26`) - non-reproducible builds |
| Conflicts | Mutually exclusive ranges declared in the same manifest |

Findings carry a severity. Exit code is non-zero when findings exist, so it can be used
as a gate.

## Run it

```bash
python3 scripts/dep_doctor.py requirements.txt
python3 scripts/dep_doctor.py pyproject.toml --json
```

Absolute paths are safest in this environment; the script takes the manifest path as its
only positional argument and prints one block per finding plus a summary line.

## How to read the output

1. Fix shadowing first - it breaks runtime behaviour, not just reproducibility.
2. Then conflicts - they fail at install time and waste a build cycle.
3. Unpinned and backport findings are decision items: pin what you ship, drop what the
   interpreter already provides.
4. Re-run after editing; a clean run prints zero findings and exits 0.

## Pitfalls

- It inspects declared metadata only. A transitive dependency that is not in the manifest
  is invisible to it.
- Version ranges in `pyproject.toml` are read from the declared fields; a PEP 621 layout
  nested under a non-standard key will be reported as empty.
- It never installs anything and never calls the network in its default mode - safe to run
  against untrusted manifests.

## Verification

```bash
# negative control: a deliberately bad manifest must produce findings
printf 'json\nemail>=4\ntyping==3.7.4.3\nurllib3>=1.26,<1.20\n' > /tmp/bad-req.txt
python3 scripts/dep_doctor.py /tmp/bad-req.txt; echo "exit=$?"   # non-zero expected
```

A tool that reports clean on a bad manifest is broken - always run the negative control
after touching the script.

## Origin

Script vendored unmodified from `Shubhamsaboo/awesome-llm-apps`
(`agent_skills/dependency-doctor/scripts/dep_doctor.py`, Apache-2.0), adopted into this
skill library on 2026-10-16 and exercised against a real manifest and a negative control.
