# Tailored CV generation (verified 2026-08-26 — Carlsberg/WSP/Infya/Aker packs)

## Kya hai
ATS report + cover letter ke saath teeno artifact: **tailored CV** (headline + summary + competencies + experience bullets sab JD ke against reframed). LinkedIn Easy Apply me attach karne ke liye `.docx` chahiye.

## Core quirk: report.json ka `step2` (ATS rewrite) USUALLY EMPTY
`resume_ai.py --mode full` ka step2 (rewrite) DeepSeek prose call fail ho jata hai (empty LLM response) — carlsberg/wsp/infya teeno reports me `step2: []` mila. **Isko fix karne ki koshish mat karo** — tailored CV manually craft karo:
- Base CV markdown: `~/ops/jobhunt/cv/CV_Aamir_Zameer_PM_v2.md`
- report.md ka step1 analysis: missing keywords, quick wins, red flags, strengths
- Agar step2 present ho (jaise Infya report me) to uske rewritten bullets/headline reuse karo — warna khud reframe karo

## Format (Aker/Carlsberg/WSP/Infya pattern)
1. Header: name + **headline = job title matching** (e.g. "Facilities Manager – Critical Infrastructure..."), contact line me relocation note (country-specific)
2. **PROFESSIONAL SUMMARY** — role/company ke liye likha, 3-4 quantified achievements, relocation/sponsorship honest line
3. **CORE COMPETENCIES** — JD ke exact keywords (report ke missing keywords + step2 new-skills list), comma-separated
4. **PROFESSIONAL EXPERIENCE** — wahi facts, JD verbs se reframe (same numbers: SAR 50M+, 15% under budget, 98% uptime, 22% energy cut, 35% emergency-repair cut, 28% downtime cut, zero incidents). Kabhi naye numbers mat ghadna.
5. Education, certifications, toolkit (base CV se)
6. Footer: `*AI-tailored CV for <Company> — <Role>. Generated <date>. Tailored score: X/100 (+Y vs base).*`

## Guardrails (honesty — fabricate kabhi nahi)
- **Unverifiable claims user se confirm karo, placeholder mat likho**: Arabic fluency (Infya JD mandates fluent Arabic — user se pucha gaya, CV me bina confirm kiye NAHI likhna), UK right-to-work status, PMP certification
- UK roles: "UK work sponsorship required" sachai se likho (unless user confirm kare koi route hai); iqama line hatao; SCE de-emphasize karo
- Currency convert for local hiring managers: SAR→GBP ≈ ÷4.75, SAR→AED ≈ ×0.96 (e.g. SAR 50M+ ≈ £10.5M ≈ AED 48M)
- Country-specific registration line: UK → "Open to CEng assessment" (intent, claim nahi)

## docx conversion
```bash
pandoc <pack>/CV_Aamir_<Role>_tailored.md -o <pack>/CV_Aamir_<Role>_tailored.docx
```
(python-docx is not installed on VM; pandoc apt se install hua. LinkedIn Easy Apply .docx accept karta hai.)

## Delivery pattern
- Teeno artifacts MEDIA: bhejo (docx CV + cover letter)
- User ko 2 confirmation points do: (1) unverifiable claims jo aapne confirm karne ko kaha (Arabic, right-to-work), (2) score delta (83/100 +21 etc.) — honest probability framing ke saath (Infya 42/100 ~0.4% — batao, chhupao nahi)
