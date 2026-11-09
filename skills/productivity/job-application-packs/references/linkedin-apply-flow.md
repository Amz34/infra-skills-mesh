# LinkedIn application submission — agent vs user division of labor (verified 2026-08-26)

## When user says "khud se apply kardo" (auto-apply karna)
Yeh deliberate workflow hai — decline karo with reasons, not as "nahi ho sakta" laziness:
1. **Login wall**: Apply button dabate hi LinkedIn "Sign in" maangta hai. Agent kabhi passwords type nahi karta (security rule), aur user headless VM browser me khud login nahi kar sakta (koi screen nahi hai; OTP/Google login user-side hai).
2. **Account ban risk (strongest reason)**: Oracle VM datacenter IP se LinkedIn automation → anti-bot captcha walls + account flag/ban ka risk. User ka LinkedIn account job-hunt ka sabse bada asset hai — ban = career damage. LinkedIn automation se isko risk mat lagao.
3. **External portal redirects**: Bade companies (Carlsberg, WSP, Type One jaise) ka "Apply" Easy Apply nahi hota — company ke apne career portal (Workday-style) pe le jata hai → naya account + forms. Automation wahan aur phas jata hai.
4. **Time math**: Manual apply = 2-3 min/job vs automation setup 30+ min jo phir bhi login pe atka.

## Browser check bina login (safe)
LinkedIn job page view hoti hai bina login (title + Apply button state) — job abhi live hai confirm karne ke liye useful. Apply button click mat karo (login wall pe le jayega). `browser_exec` + `new_tab(<job url>)` + page_info() se confirm karo.

## Delivery pattern (kya dena hai jab pack bana chuke ho)
- Cover letter + tailored CV as MEDIA: files
- Direct job link — FULL URL (report.json me truncated hota hai, neeche quirk dekho)
- Exact 2-min apply path: link kholo → Easy Apply/Apply → CV attach → cover letter paste → submit
- Verification steps (neeche)

## LinkedIn application status check (user-facing easy steps)
1. LinkedIn → Jobs icon (briefcase) → **My Jobs** → **Applied** tab → status: **Applied / In Review / Rejected**.
2. Ya usi job ki post dobara kholo — green **"Applied"** button (click nahi hota) = submit ho chuka; "Easy Apply"/"Apply" dikhe to abhi nahi hua.
3. Confirmation email: *"You applied to [Company] at [Job Title]"* — yeh bhi proof hai.
⚠️ External portal (Easy Apply nahi) pe apply kiya ho to LinkedIn My Jobs me nahi dikhega — wahan confirmation email hi proof hai.

## Quirk: report.json me truncated JD URLs
`resume_ai.py` report.json me JD URL short form me store karta hai (`https://uk.linkedin.com/jobs/view/facilities-manager-at-c...`). Full LinkedIn URLs yahan se lo:
- `~/ops/jobhunt/scout/*.json` — grep `https://[^"]*jobs/view/`
- Ya session history (job scout wale sessions me full links milte hain)
User ko apply link dete waqt hamesha full URL do.
