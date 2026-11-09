# SuccessFactors (SAP) careers portal — autonomous apply

Proven 2026-09-02 on Siemens careers (job 519392, full run: register → email
validation → login → draft resume → submit → verified "Application Received").

## URL anatomy (Siemens/SF)
- Job: `.../externaljobs/JobDetail/<jobId>?source=LinkedIn`
- Apply → `.../externaljobs/ApplicationMethods?folderId=<jobId>` → `Register?folderId=<jobId>` (upload-resume route)
- Login: `.../externaljobs/Login`  ·  Profile/apps: `.../externaljobs/ProfileJobApplications`
- Post-submit: `.../externaljobs/Success?folderId=<jobId>`

## Wizard (5 steps)
1 Login/Registration → 2 Profile → 3 Global questions → 4 Country questions →
5 Job-specific questions → Submit.
- **Server state lives in the session cookie.** Direct Register-URL navigation →
  form EMPTY (CV-parse prefill lost). Clean restart: job page → Apply → Upload
  CV → Continue. CV-parse prefills name/email/city/education/jobs.
- Partial completion saves a DRAFT: after login, My Applications shows
  "Application draft | Complete application" → resumes at the right step.
- Session expiry mid-wizard → wizard state lost; restart from job page.

## Registration gates
- **Email validation is REQUIRED before login works.** Account creation sends
  "Email address validation request" (from e.g. "Siemens P&O Talent Acquisition").
  Login error says: "If you've already created your account but haven't validated
  it, you can request a new validation email from the button below."
  → Read the email via IMAP (configured mailbox, app password) and click the
  `_portalVerifyEmail/<token>` link IN THE SAME BROWSER session. Then login works.
- **"There's an existing record with that email"** on Register = candidate record
  already exists for that email (real old account, OR a draft-record quirk where
  forgot-password mail never arrives because no real account exists). Don't burn
  time: register with another monitored email. Login form: `#username`,
  `#password`, "Log in".

## Widget mechanics (SF custom jQuery-UI/select2)
- **Field ids are digit-leading** (e.g. `id="42331"`) → `#42331` is an INVALID
  CSS selector. Use attribute selectors: `[id="42331"]`, `input[name="42331"]`.
- **select2 comboboxes** (citizenship, gender, some selects): native `<select>`
  holds only a placeholder option; the real options load via AJAX when you open
  the widget. Click the `.select2-selection--single` container → type in the
  `.select2-search__field` input → click the suggestion `<li>`. (Citizenship =
  remote AJAX search, e.g. type "India"; gender = local options.)
- Some "selects" are actually PLAIN TEXT inputs (state/region, salary currency) —
  just set the value (e.g. "SAR"). Salary = amount text + currency text.
- **Option VALUES are numeric codes** (663244 etc.), not "Yes"/"No". When setting
  a native select, loop options and match by option TEXT.
- **Checkbox groups share one name** (`42268-N[]`, one per question). Question
  order maps to field numbering, but DOM listing order ≠ visual order — read each
  option's own label text and the question stem container to disambiguate.
- **Controlled inputs** (React/JS) ignore `.value=`. Use the native prototype
  setter + `input`/`change`/`blur` events.
- **File inputs** (`input[type=file]` hidden): clicking opens a native chooser
  (invisible headless). Set files via CDP `DOM.setFileInputFiles` on the input's
  nodeId. Digit-leading ids again → locate via `DOM.querySelector` with an
  attribute selector.
- **SF clears passwords on EVERY failed submit** (security) and can desync
  select2 title fields / work-location selects. After any validation error:
  read back the affected fields, re-fill, retry. Before clicking Continue,
  press Escape to close any open select2 dropdown (open popups swallow clicks).
- Buttons: step button = `.saveButton` ("Continue >"); final = "Submit".

## Honesty + screening (non-negotiable)
- Wizard opens with an "all information is true" declaration checkbox.
- Grad-program roles screen with "Are you a fresh graduate?" and "Are you a
  <country> national?" — answer truthfully even when it auto-screens the
  candidate out (13+ yr experienced, non-national → No/No). Report the
  realistic outcome to the user, don't hide it.
- Work-history rows: keep only roles with verifiable dates; rows without dates
  get REMOVED (don't fabricate). Row ids persist after removal (harmless).

## Verification (before claiming success)
- URL becomes `/externaljobs/Success?folderId=` + "Thank you for applying…".
- My Applications shows status "Application Received" (not draft).
- Confirmation email may lag minutes — status page is authoritative.
