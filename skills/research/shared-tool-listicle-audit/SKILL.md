---
name: shared-tool-listicle-audit
description: Use when a shared tool/repo listicle needs auditing.
version: 1.0.0
author: aamir-agent
license: internal
metadata:
  hermes:
    tags: [research, adoption, qa, governance]
    related_skills: [tech-adoption-analysis, link-safety-triage, agent-skill-adoption-gate, app-safety-evaluation]
    created: "2026-09-20"
---

# Shared tool listicle audit (decode -> verify -> fit -> gate)

## When to Use

A user drops a LinkedIn / X / lnkd.in post that is a *tool or repo listicle* ("10 repos that..."),
or a single short link to one, and asks to "analyze/audit/implement" it. Also load
`tech-adoption-analysis` (the reporting contract) — this skill is the executable pipeline for the
"tool/repo listicle" sub-class it lists.

## Procedure

1. **Never trust the post.** Resolve every short link first. `lnkd.in` and LinkedIn posts are JS
   interstitials: the destination is inside the HTML body, not a `Location` header. Plain `curl -I`
   returns headers only and often 1 line of noise — always fetch the BODY.
2. Decode all embedded targets:
   ```bash
   python3 ~/ops/scripts/repo_intel_audit.py --url "<shared-url>" --repos <owner/repo>... \
     --title "<label>" --claims claims.json --append-ledger
   ```
   `--claims` is a `{owner/repo: claimed_stars}` JSON: the tool diffs claim vs live API.
3. The tool does the four real steps: RESOLVE -> VERIFY (authenticated `gh api`, 5000/hr) -> SCORE
   against `FINGERPRINT` in the tool -> REPORT (`~/ops/kb/repo-intel/<date>-<slug>.md` + `.json`),
   then runs `~/ops/verify/claim_integrity.py` over the report.
4. Read the verdict column and act only on **ADOPT-CANDIDATE** rows. **REFUSE** rows stay refused
   (offensive tooling / banned domains) — state the reason, do not silently drop them.
5. For an adopted candidate, measure it ON THIS BOX before claiming value — install into a
   throwaway venv (`~/.venvs/intel-audit`) and record the real result. "It has 83k stars" is not
   evidence; "5/16 channels live from this IP" is.
6. Run the negative controls before trusting the gate: `--selftest` must return 0 with all controls
   PASS, including the ones that MUST fail (bogus repo, inflated star claim).

## Turning a document into a skill (the doc->skill lane)

`book-to-skill` only extracts text + metadata and expects an agent to synthesise the skill; it has no
Hermes output mode. Bridge it and gate it:

```bash
python3 ~/ops/scripts/doc_to_skill.py <doc.pdf|docx|md> --slug my-skill --category doc-derived   # preview
python3 ~/ops/scripts/doc_to_skill.py <doc.pdf> --slug my-skill --category doc-derived --apply    # install
python3 ~/ops/scripts/doc_to_skill.py --selftest                                                  # gate controls
```
Then replace the `TODO(agent)` markers from `references/source-extract.md` and re-run
`skill_lint.py` on the skill dir until rc=0.

## Measured baseline (2026-09-20, this VM, Jeddah datacenter IP)

- `agent-reach doctor` from `~/.venvs/intel-audit`: **5/16 channels usable** (YouTube, RSS/Atom,
  V2EX, Jina Reader, GitHub-with-our-gh-auth). **X / Reddit / LinkedIn / Instagram / xiaohongshu
  are all locked** behind extra login/cookie backends — the exact platforms the listicles hype.
  Chinese-first CLI output.
- "Read any web page" in that tool = r.jina.ai, which is already our default and which LinkedIn
  still blocks (empty body). Free-tier Jina is not a LinkedIn reader.
- LinkedIn post bodies are NOT retrievable from here (bot-blocked, proxy-blocked). Get the repo list
  from the user or from the post's visible text; do not pad the gap with guesses.

## Pitfalls

- Unauthenticated `urllib` GitHub calls rate-limit at 60/hr and silently return nothing — use `gh`.
- A repo can be "mature" (stars, pushed today) and still be a bad fit: `HKUDS/nanobot` (48k stars,
  787 open issues) is the same product as our own agent runtime = OVERLAP, not adoption.
- Star counts in listicles are usually accurate (this one: max drift 0.37%). The risk is not the
  numbers, it is the missing part: what the tool does NOT do, and what it needs (cookies, logins,
  paid API keys) — read the doctor/install output, not the README badges.
- Install docs lie about availability: neither `agent-reach` nor `book-to-skill` is on PyPI; both
  need `pip install "git+https://github.com/..."`.

## Verification

```bash
python3 ~/ops/scripts/repo_intel_audit.py --selftest      # 7/7 controls
python3 ~/ops/scripts/doc_to_skill.py --selftest          # 5/5 controls
```
Both must exit 0, and both suites contain must-FAIL controls — a gate that only ever passes is
not a gate.
