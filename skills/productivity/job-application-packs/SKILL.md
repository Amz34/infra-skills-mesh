---
name: job-application-packs
description: Use when generating Aamir job-application packs.
---

> **Claim-integrity gate (mandatory, 2026-09-15):** every claim in this output must be provable.
> Before ship run `python3 ~/ops/verify/claim_integrity.py <mode> <file|dir>` and clear all HIGH
> with `[src: ...]` evidence or `[claim-ok: reason]`. Rule: `~/brains/ops/rules/content-integrity.md`.
> Skill: `content-integrity-guardrail`.

# Job Application Packs (Aamir job hunt)

## When to use
- Aamir ko kisi job ke liye tailored pack chahiye: ATS report (scoring + rewrite + verification) + cover letter.
- CV ko kisi specific JD ke against optimize karna.
- Job-hunt advice deni ho (LinkedIn Open to Work, apply strategy).
- Scope/architecture sawal: "humari infra se jobs pe apply kaise karein", "apply automation banayein?", roadmap ya capability audit — pehle `references/apply-engine-architecture.md` + `~/ops/jobhunt/APPLY_ENGINE_ANALYSIS.md` padho, phir layer-by-layer status + gaps + phased plan ke saath jawab do (plain prose me mat likho).

## Pipeline
Scripts: `~/.hermes/scripts/resume_ai.py` + `cover_letter.py` (self-hosted DeepSeek; `DEEPSEEK_API_KEY` in `~/.hermes/.env`; model `deepseek-v4-flash`).

1. Clean CV text → `/tmp/cv_clean.txt` (typical ~6.2K chars)
2. `mkdir -p ~/ops/jobhunt/packs/<role_slug>/`
3. ATS pack:
   `python3 ~/.hermes/scripts/resume_ai.py --resume /tmp/cv_clean.txt --jd "<url|file>" --mode full --out ~/ops/jobhunt/packs/<slug>/<role>_report.json`
   → writes `<role>_report.json` + `<role>_report.md`
4. Cover letter:
   `python3 ~/.hermes/scripts/cover_letter.py --jd "<url|file>" --out ~/ops/jobhunt/packs/<slug>/<role>_cover.md`
5. Verify before delivery:
   - **Natural-application rule (Aamir explicit):** recruiter-facing docs me AI kahin nahi — no AI/full-stack section, no AI profile line, no AI-generated footers. Surgical edits only; baaki real CV verbatim. Exact-term grep se validate karo (command: references/arabic-ats-portal-apply.md).
   - report has `selection_probability_estimate` + `remaining_risks` — risk list is the honest story; share key items with user (don't bury them)
   - cover letter 150–190 words, opens with role+company, maps 3 exact-number achievements (SAR 50M+, 15% under budget, 98% uptime, 22% energy cut, zero-injury), SCE #317164 + transferable Iqama line, NO phone number, signed `Aamir Zameer — Project Management Engineer`

## Pitfalls
- **DeepSeek v4-flash = reasoning model**: emits hidden `reasoning_content` BEFORE `content`, and reasoning tokens count against `max_tokens`. With `max_tokens=600` the whole budget went to reasoning → EMPTY content, `finish_reason: length`. Any prose generation needs `max_tokens ≥ 2000–2500`. `cover_letter.py` already patched (2500 + empty-response guard) — preserve that when editing. Diagnosis recipe: references/deepseek-reasoning-token-pitfall.md
- **LinkedIn job URLs**: public `sa.linkedin.com/jobs/view/<slug>-<id>` URLs DO fetch fine with the script (verified 2026-09-10, 7.4K chars of JD text). Login-walled/blocked cases remain (`JD fetch failed (locked page?)`) → then save the JD text to a file and pass the file path. Transient `Temporary failure in name resolution` (DNS blip) → just retry once.
- **Years gap**: JDs often ask 15+ yrs, CV says 13+ → report flags ATS screen risk (~20% estimate). Don't hide it; cover letter reframes "13+ years" confidently, and suggest quantifying total FM/asset years if legitimately possible.
- Scripts log progress to stderr (use `2>`, `2>>`); stdout carries saved-file messages.
- **Discovery feed band mil sakta hai**: `Weekly AI Job Scout` cron (`0 6 * * 0` = Sun 09:00 Riyadh) `~/.hermes/cron/jobs.json` me `enabled:false` ho sakta hai → pipeline ka input hi ruk jata hai (scout data purana reh jata hai). Koi bhi apply/analysis se pehle cron state check karo aur user se poocho ke ON karna hai — khud enable mat karo (recurring Telegram digest hai).
- **Silent empty step (fixed 2026-09-10)**: reasoning-token truncation can make a step return `{}` → report.md me section 1 poora gayab / blank, aur ye "complete" lagta hai. `resume_ai.py` me ab `build_report()` ke andar `req()` validator hai: required keys na mile to step retry hota hai (3 tries) + stderr pe `step incomplete ... -> retry` warning. Agar report section blank dikhe, stderr check karo. `to_md()` me `### New summary` line pe missing `f` prefix bhi fix hua (placeholder verbatim print ho raha tha).
- **Apply-engine architecture + capability audit**: `~/ops/jobhunt/APPLY_ENGINE_ANALYSIS.md` (2026-09-10) — layer-by-layer status (discovery/materials/identity/submission/tracking), CDP substrate (`~/.hermes/scripts/cdp.py` + headless Chrome :9222), gaps + phased roadmap. Naya apply automation banane se pehle padho. Reusable part (layer table, verified baseline numbers, the `req()` retry-validator code, pipeline shape, honesty/routing rules): `references/apply-engine-architecture.md`.

## Portal application automation (autonomous apply on careers portals)
Jab Aamir bolta hai "khud completely apply kardo until final step done" aur role kisi careers portal pe hai — LinkedIn auto-apply mat karo (datacenter IP se ban risk; LinkedIn ka Apply external portal pe hi jata hai). Portal ko directly automate karo. DO portal flavors, alag-alag playbooks:
- **Western ATS (SAP SuccessFactors / Workday / Oracle)** → `references/successfactors-portal-apply.md`
- **Arabic/Sabbar-style ATS** (hiring.<company>.sa, RTL, custom comboboxes jo JS clicks resist karte hain; wizard: application data → account+submit ek saath) → `references/arabic-ats-portal-apply.md` — type-to-search + mousedown-sequence select + cascade country→city + CDP file upload, sab field-proven (Zimam, submitted 2026-09-03)
- **Flow:** job page → Apply → upload CV (server-side parse = profile prefill; direct Register URL se form EMPTY aata hai — hamesha job page se restart karo) → wizard steps (profile → global → country → job-specific Qs) → Submit → verify "Application Received" in My Applications + `/externaljobs/Success?folderId=` URL.
- **Email validation gate:** naya account login se pehle validation email chahiye ("Email address validation request" from P&O Talent Acquisition). Isliye portal account **hamesha us email se banao jiski inbox IMAP se padh sakte ho** (azengineeringapp / aamir1zahran — dono configured; shaikaamirmalik25 nahi). Validation link IMAP se nikal ke USI browser session me kholo, phir login.
- **"There's an existing record with that email"** = us email ka purana account/draft exists. Forgot-password kabhi nahi aa sakta (real account nahi bhi ho). Fight mat karo — doosra monitored email use karo. Final message me user ko email choice clearly disclose karo (CV header email ≠ portal account email ho sakta hai).
- **Honesty hard rules (portal pe bhi):** wizard "information is true" declaration deta hai → screening Qs ("Are you a fresh graduate?", "Are you a Saudi national?") truthfully answer karo, chahe auto-screen ho jaye. Work-history rows: sirf un roles ki jinke dates verified hain — dates na hon to row drop karo, fabricate mat karo. User ko batana ki submission honest hai + realistic outcome kya hai.

## LinkedIn Open to Work (job-hunt advice)
- Zaroori nahi, but recommended while actively applying: green banner + recruiter-search priority + role/location preferences.
- Privacy tip: choose **"Recruiters only"** mode so current employer never sees the banner.
- Flow: Edit profile → Add section → Open to Work.

## Output convention
`~/ops/jobhunt/packs/<role_slug>/` → `<role>_report.json|md` + `<role>_cover.md`. Existing: `parsons_srpm/`, `bigfish_assetops/`.
