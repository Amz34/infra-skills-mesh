# Arabic ATS (Sabbar-style) Portal Apply — Field-Proven Playbook

Source: Zimam (hiring.zimam.sa, job "مدير مشروع" Mecca) full autonomous apply, 2026-09-03 — application SUBMITTED + dashboard-verified. Applies to Saudi/Arabic ATS builds (Sabbar, similar React Arabic portals) that are **not** SAP SuccessFactors.

## Route discovery
LinkedIn job "Apply" → off-site → company's own portal (e.g. `hiring.<company>.sa/jobs/<id>`). Jab role portal pe hai to portal ko directly automate karo (LinkedIn automation ban-risk policy wahan apply nahi hoti — company ka apna career portal safe hai). Job page Arabic hogi. Apply button → wizard modal: **step 1 بيانات التقديم (application data)** → التالي → **step 2 بيانات الحساب (email + password, no confirm) + إرسال الطلب**. Account creation + submit = ONE action.

## Form control inventory (Arabic RTL, 2-col grid)
Row order in DOM ≈ visual right-to-left. Labels (find label element by exact Arabic text, then its sibling/container control):
- الاسم الأول / الاسم الثاني / الاسم الثالث / **اسم العائلة** — text inputs. Family REQUIRED (validation on Next: "اسم العائلة مطلوب"). Aamir Zameer mapping: first=Aamir, second=Malik, third=(empty), family=Zameer. Don't duplicate third+family.
- رقم الهوية الوطنية (Iqama), رقم الجوال (native, prefix +966 is a SEPARATE text input), الجنس (native select: ذكر/أنثى), تاريخ الميلاد (date input, ISO yyyy-mm-dd), المؤهل التعليمي (native select: ثانوي/دبلوم/بكالوريوس/ماجستير/دكتوراه), سنوات الخبرة (number), آخر منصب (text), السيرة الذاتية (file), الشهادات والمستندات (optional files, skip).
- Custom comboboxes (buttons, NOT selects): الجنسية (nationality), دولة الإقامة (country), مدينة الإقامة (city), التخصص (specialty).

## Custom combobox playbook (the hard part — validated)
Widget = a `<button>` whose text = current value, plus a virtualized options portal (options are buttons; only ~8-12 rendered around scroll position; dataset can be 200+).

1. **Open:** synthetic `.click()` often fails. Use `scrollIntoView({block:'center'})` → fresh `getBoundingClientRect()` center → **real mouse click** (`click_at_xy`/CDP Input). Buttons below viewport silently never open (click lands nowhere).
2. **Filter:** on open, a search `<input>` takes focus (`document.activeElement.tagName == 'INPUT'`). THE reliable path: set its value via `HTMLInputElement.prototype` value setter + dispatch `input` (bubbles) → list filters to matches instantly (same tick). e.g. search 'هند' → الإقليم البريطاني…/الهند/هندوراس.
3. **Select:** plain `.click()` on the option does NOT register (virtual list re-renders between find and click → detached node; real mouse click on option also failed on this portal). Working formula: **full synthetic mouse sequence on the option AFTER filtering**: `mousedown` → `mouseup` → `click`, each `{bubbles:true}`. Selection commits (lib listens on mousedown). Filtered list is small+stable → no race.
4. **Verify:** read back the opener button's text (e.g. الجنسية button now shows الهند). Never trust the click — read the value.
5. **No filter input?** (some lists) → scroll loop: locate the scrollable options container (ancestor of a rendered option where `scrollHeight > clientHeight` and `clientHeight` roughly 150-400, NOT the form/HTML scroller), `scrollTop += ~200`, `time.sleep(0.25)` (virtual lib re-renders async), re-query rendered buttons for exact target text; repeat ≤15-20x, then real-click or mousedown-sequence the target. (Worked for country list: scroll to المملكة العربية السعودية.)
6. **Cascade:** مدينة الإقامة (city) combobox is **disabled until** دولة الإقامة (country) selected — don't fight it, set parent first.
7. Stuck dropdown → real click elsewhere or Escape; re-measure coordinates every attempt (layout shifts after selections re-render rows).

## Native fields
Value setter must match the element type: `HTMLInputElement.prototype.value` setter on a `<select>` THROWS — selects need their own descriptor/value assignment, then dispatch `change`. Inputs: setter + `input` event. Number/date inputs accept plain values.

## CV file upload (CDP)
`DOM.getDocument` → `DOM.querySelector(selector='input[type=file]')` → `DOM.setFileInputFiles` with the LOCAL path (browser runs on same host — real FS path works). Verify: the file name + size appear next to the label (e.g. `Aamir_Zameer_CV_Zimam_PM.pdf | 0.01 MB`).

## Submit + verification (never trust the click)
- التالي (Next): validation errors appear as Arabic inline text — read `document.body.innerText` slice around the form after clicking. Fix, retry. (Hit: "اسم العائلة مطلوب" = family name required.)
- إرسال الطلب (Send) → success = **dashboard read-back**: candidate view shows تقديماتي (My Applications), the job title, status **في الانتظار (Pending)**, and date. That read-back IS the proof (portal apply never appears on LinkedIn "My Jobs").
- تفاصيل الطلب (application details) expands the full job description — use it to confirm the right job was applied to (JD text should mirror the LinkedIn ad).
- Capture a screenshot after submit for the user's proof file.

## Account/creds conventions
- Portal account email = **monitored IMAP inbox** (azengineeringapp / aamir1zahran) — validation/reset mails must be readable; disclose the email used in the final message to the user.
- Password: `python3 -c "import secrets; print(secrets.token_urlsafe(18))"` → save `creds.env` (umask 177 / chmod 600) next to the pack.
- No OTP gate on this portal type (account+submit one shot) — but if an email-validation step appears, follow the SuccessFactors pattern (IMAP-fetch link, open in the SAME browser session).

## Aamir natural-application rule (explicit, recurring)
Submitted docs must look fully human/natural — NO AI mentions anywhere (no AI/full-stack profile line, no "AI-powered" bullets, no AI-generated footers/sections in the recruiter-facing PDF). Surgical edits only: strip the AI section, keep the rest of the real CV verbatim. Pre-delivery validation (exact terms only — plain 'ai' substring false-positives on normal words like "maintenance"):

```bash
pdftotext <cv.pdf> - | grep -in "llm\|full-stack\|intelligent automation\|AI-powered\|workflow optimization\|chat widget\|web scraping\|Hermes\|DeepSeek"
```
EXIT=1 → CLEAN. Exit 0 = a marker leaked — fix before submitting.
