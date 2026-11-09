# Apply-Engine Architecture & Capability Audit

Full write-up: `~/ops/jobhunt/APPLY_ENGINE_ANALYSIS.md` (2026-09-10, ~11 KB).
This file = the reusable part: layer audit, the failure modes found, and the build shape.

## Layer audit (what exists vs what's missing)

| Layer | Status | Where it lives |
|---|---|---|
| 1. Discovery | works, **cron often OFF** | `~/.hermes/scripts/linkedin_job_scout.py` → `~/ops/jobhunt/scout/jobs.json`; cron `0 6 * * 0` (Sun 09:00 Riyadh), `enabled:false` by default |
| 2. JD acquisition | works for public URLs | script fetches `sa.linkedin.com/jobs/view/<slug>-<id>` (~7.4K chars) or a local file path |
| 3. Score | works (~55 s/job) | `resume_ai.py --mode score` |
| 4. Rewrite + cover | works (full pack ~2 min) | `resume_ai.py --mode full` → `<role>_report.json|md`; `cover_letter.py` → `<role>_cover.md` (~6.5 s) |
| 5. Identity / email gate | works | `himalaya` IMAP on `azengineeringapp` + `aamir1zahran` (NOT `shaikaamirmalik25`) |
| 6. Submission | proven manually, not automated | `~/.hermes/scripts/cdp.py` + headless Chrome CDP `:9222`; playbooks in this skill's references |
| 7. Ledger / dedupe | **missing** | propose `~/ops/jobhunt/ledger.csv` (date, company, role, url, score, pack path, status, confirmation) |
| 8. Cadence (auto-apply) | **missing** | nothing runs "shortlist top N → apply" today |

Verdict shape for the user: the gap is **orchestration, not capability** — RTL comboboxes, CDP file upload, validation-email gate and honest screening answers are already field-proven.

## Verified baseline numbers (2026-09-10, use as sanity reference for new runs)

- Full pack on a live Jeddah PM job: `report.json` 24,191 chars, `report.md` 12,372 chars; final **86/100, +54, selection probability ~1 in 5 (20%)**, 136 keywords covered, 8 remaining risks, 8 next actions.
- Cover letter: 176 words, opens role+company, 3 exact-number achievements, SCE #317164 + transferable Iqama, no phone.
- Live re-score with the new validator: 53.5 s → **56/100** (ATS 48 / impact 78 / relevance 48 / format 62), top-5 missing keywords: Primavera P6 / MS Project; BOQ, shop drawings, RFIs, material submittals, method statements; fit-out / snagging / handover; PMP; AutoCAD / Revit / BIM.
- Prior pack for comparison: Siemens Tamayuz (Sep 2) `step1.overall_score = 45`.
- Marginal cost per pack ≈ 3 LLM calls (~50–70K tokens incl. prompts, estimate) — cents, not dollars. Time and supervision are the real constraints.

## Failure mode #1 — silent empty step (highest-value finding)

Reasoning-model truncation (reasoning tokens counting against `max_tokens`) can make a step return `{}`
after the internal retries in `deepseek_json`. The report then renders *without Section 1* and still looks
"complete" — the ATS score, missing keywords and red flags all vanish with no error.

Evidence: the 2026-09-10 full run wrote `step1: {}` into `report.json`, while the same pack still showed
`final_score_after: 86, improvement +54` (so step3 was fine and the loss was invisible).

**Fix now in `resume_ai.py` → `build_report()`:** a local `req(user, keys, max_tokens, tries=3)` wrapper that
retries until every required key is present, printing `step incomplete (missing [...]) attempt n/3 -> retry`
to stderr, and a final `WARNING: step still empty/partial` if it never validates.
Required-key sets: step1 `['overall_score','score_breakdown','top_5_missing_keywords']`,
step2 `['rewritten_headline','rewritten_summary','ats_issues','rewritten_bullets']`,
step3 `['final_score_after','selection_probability_estimate','remaining_risks']`.

Pattern to reuse in any JSON-returning LLM step (same shape as `cover_letter.py`'s empty-response guard):

```python
def req(user, keys, max_tokens=4000, tries=3):
    d = {}
    for i in range(tries):
        d = deepseek_json(SYSTEM, user, max_tokens=max_tokens, tries=1)
        if isinstance(d, dict) and all(k in d for k in keys):
            return d
        print(f'    step incomplete (missing {[k for k in keys if k not in (d or {})]}) '
              f'attempt {i+1}/{tries} -> retry', file=sys.stderr)
    print('    WARNING: step still empty/partial after retries - report section will be blank',
          file=sys.stderr)
```

**Verification recipe (no LLM spend):** import the module, monkeypatch `deepseek_json` to return `{}` on the
first call then a valid dict, and assert `build_report('R'*100,'J'*100,'score')` ends with populated keys and
2 API calls. For a real check, re-run `--mode score` (~55 s) and confirm `step1` is non-empty.
**Health check on any existing pack:** `step1 == {}` in the JSON means that pack shipped with a blank score
section — regenerate the score step before quoting it to the user.

## Failure mode #2 — template placeholder leaked into the report

`to_md()` printed the literal `{s2.get('rewritten_summary')}` for months because that list element was missing
its `f` prefix. Fixed 2026-09-10; verify by re-rendering an existing `report.json` through `to_md()` (no LLM
call needed) and checking that the "### New summary" line contains prose, not `{s2.get(...)}`.

Lesson: when a `.md` renderer is built from a list of f-strings, one missing `f` is silent — grep the renderer
for `{'` / `{s` / `{x.get` patterns after any edit.

## Target pipeline shape (build order)

```
cron (weekly) → scout → score (fast filter, threshold) → shortlist minus ledger
   → full pack + cover letter (no human) → route by URL domain
   → adapter: successfactors | arabic_ats | workday | unsupported
   → CDP apply → HARD GATE: 1-line approval before final Submit
   → verify confirmation text / ?folderId= URL → ledger row
```

Routing/honesty rules that must survive into any automation:
- Never automate LinkedIn Easy Apply from the VM (datacenter IP → ban risk on Aamir's professional identity).
  External ATS portals only; Easy Apply stays manual on his phone.
- Portal account email must be IMAP-readable so the validation link can be opened in the same CDP session.
- Always restart from the job page (CV upload → profile prefill); the direct Register URL gives an empty form.
- Truth on screening questions; only verified work-history dates; never claim unheld tools (PMP/Primavera/AutoCAD).
- Ledger + dedupe from run one, otherwise the engine re-applies to the same company and reads as spam.

## Honest-expectation framing (Aamir responds well to this)

Applying ≠ interviewing: 86/100 with ~20% selection probability means ~2–4 first calls per 20 applications —
volume is the lever, quality the multiplier. Budget ~1 adapter failure per 3–4 applications (Workday/CAPTCHA/OTP),
each new company needs a supervised first run. Fixing the report's own risk items (missing Primavera/PMP/AutoCAD
claims, AI language in the summary, single-column ATS layout) is worth more per application than any automation.
