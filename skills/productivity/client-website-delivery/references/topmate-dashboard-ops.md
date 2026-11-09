# Topmate Dashboard Ops — Digital Products, Pricing, Profile Photo

Managing the REAL topmate.io account (not the replica). Proven 2026-08-31 on
Aamir's account: 10 products created in one session (4 free + 6 paid),
all went LIVE. Admin dashboard = `https://topmate.io/dashboard` (login via
user's browser), public profile = `https://topmate.io/<username>`.

## Digital product creation flow (VALIDATED — 10x success)

1. `/dashboard/services` → **"+ Add New"** → choose **Digital Product**.
2. Fill title + amount: **$0 for free lead magnets**, real price for paid.
   Paid product amounts go through the same form — no special flag.
3. **"Next: Customize"** — NOTE: this is a React (Next.js) form; synthetic
   `el.click()` on the button is IGNORED. Use a REAL CDP coordinate click:
   ```python
   r = js("(() => {const b=[...document.querySelectorAll('button')].find(e=>(e.textContent||'').includes('Next: Customize')&&e.offsetParent!==null); const x=b.getBoundingClientRect(); return JSON.stringify({x:x.x+x.width/2,y:x.y+x.height/2})})()")
   click_at_xy(cx, cy)   # browser_exec helper
   ```
4. **Form fields on customize page:**
   - `input[name=short_custom_description]` (or the first text input) —
     fill via **native value setter** (`Object.getOwnPropertyDescriptor(
     HTMLInputElement.prototype,'value').set.call(el, text)` + `input`
     event) or `fill_input`; plain `.value=` doesn't register with React.
   - Long description = Quill rich-text editor (`[contenteditable=true]`) —
     `fill_input` works there.
   - **Pricing anchor:** Topmate has NO original-price/strikethrough field
     (checked the customize form). Do the anchor in the description text:
     "Worth $32 → aaj $9" style.
5. **Content ("Add file or link"):** an antd `ant-btn` → click opens a
   dropdown (`ant-dropdown-open` class appears). Item **"Link to external
   page"** opens a modal with URL + Name fields. THIS IS THE KEY BYPASS:
   direct file upload opens a NATIVE file chooser that is INVISIBLE in
   headless and never appears in the DOM — attaching a URL via the dropdown
   works 100% headless. Use it for everything (freebie HTML pages hosted on
   a tunnel, etc.).
6. **Visibility:** dropdown "Hidden from profile" → set to **"Visible on
   profile"** before Save, or the product won't show publicly.
7. Save → product LIVE. Verify: `curl -s https://topmate.io/<username> |
   grep -oE "<product title>"` — titles appear in the public HTML.

## 1:1 Call service creation flow (VALIDATED 2026-08-31 — 10 services batched)

Same dashboard, different card: "+ Add New" → **"1:1 Call"** (NOT Digital
Product). Flow: Add New → dialog card → basic-details form → "Next:
Customize" → short desc + Quill → Save → verify on public page.

Reusable helper pattern: put `create_service(title, duration, amount,
short_desc, desc)` in the session's `agent_helpers.py` (auto-imported by
the browser harness). CRITICAL: harness helpers (`js`, `cdp`, `click_at_xy`)
live in the exec globals, NOT importable — pass them as explicit arguments:
`create_service(js, cdp, click_at_xy, title, ...)`.

Steps + selectors (state-dependent — re-locate on each run):
1. `js("location.href='/dashboard/services'")`, wait ~3s.
2. "+ Add New" — MUST match an exact BUTTON with an anchored regex:
   `[...document.querySelectorAll('button')].find(e=>/^\s*\+ Add New\s*$/.test((e.textContent||'').trim())&&e.offsetParent!==null)`
   — naive `includes('Add New')` over `button,div` matches parent DIVs and
   never opens the dialog.
3. "1:1 Call" card — scope the search INSIDE `[role=dialog]`. The sidebar
   tab "1:1 Call" (same text) navigates to `/dashboard/services/video`
   instead of opening the modal — clicking the wrong one lands on a page
   with no form fields.
4. basic-details form: title = `input[placeholder="Name of Service"]`
   (≤50 chars — hidden chars from fill_input push it over and block Next
   with a validation error; shorten the title). duration/amount = the two
   `.ant-input-number-input` fields, sorted by y (duration ≈610, amount
   ≈699 in one viewport; find by bounding rect each run).
5. "Next: Customize" — real CDP coordinate click (React ignores synthetic
   `.click()`). Validation errors silently block this.
6. Customize: short desc = first text `input` sorted by y (NOT by x —
   viewport width changes x; a `x>400` filter failed at ~900px width where
   fields sit at x≈288). Long desc = Quill `.ql-editor` (contenteditable)
   — click exact position, then insert text. Anchor price in Quill text:
   "Worth $X → today only $Y" (no strikethrough field exists).
7. Save (bottom-right). Verify: `/dashboard/services` then
   `document.body.innerText.slice(0,2000)` (cards lazy-render; innerText
   works), or the public profile page.

### Duplicate/orphan drafts — delete flow

A failed run mid-flow leaves the draft PUBLIC with basic details saved (the
basic-details step auto-saves). Result: duplicate service cards on the
public page. Delete: open the orphan's Edit page
(`/dashboard/services/edit/basic-details?id=<draft_id>&type=1`), scroll to
bottom, "Delete Service" button → ant popconfirm → click "Yes, Delete"
(DOM click works on the popconfirm button). Then re-verify the public list.

### Pricing/positioning rules (Aamir's standing preferences)

- USD only; medium/nominal prices until leads arrive (2026-08-31 batch:
  $7–$39 range).
- Punchy neuro-marketing copy + anchor in description ("Worth $30 → today
  only $9").
- New services are low-ticket entry offers with upsell to 1:1 calls;
  every freebie carries a "book a call" CTA.

## React gotchas on the Topmate dashboard (summary)

- Synthetic `.click()` ignored on: Next: Customize, ant-btn "Add file or
  link", dropdown items, Save. → ALWAYS real CDP coordinate clicks
  (`click_at_xy` with rect center from JS).
- Inputs: native value setter + input event (React controlled inputs).
- Full technique detail → `headless-browser-automation` skill section
  "React/antd forms & click-landing verification".

## Account settings (checked /dashboard/settings)

- **Currency**: set to USD there (matters for international clients).
- **Commission**: Topmate takes 10% of product/service revenue.
- Payout setup (UPI/bank) = USER step — guide manually, never automate
  entering bank details.

## Profile photo upload — automation FAILED, manual fallback (honest)

9+ headless attempts on the customize editor (click avatar in preview
iframe, hover-reveal, double-click, MutationObserver on both main + iframe
documents, Page.setInterceptFileChooserDialog) — the avatar click never
opened a chooser or created an `input[type=file]` in either document, while
the SAME CDP click mechanism demonstrably worked on other elements (Mobile
tab switched viewports). **Do not burn time re-attempting this.** Hand off
to the user with exact steps (30 seconds, phone or laptop):
1. topmate.io/dashboard → sidebar "Edit Public Profile" → "Customize
   public profile"
2. Click the avatar (blank/default) → "Upload Photo"
3. Also edit the headline there (profile editor is an iframe visual
   editor — headline is click-to-edit "Start your page" placeholder).

## Related

- Replica page build + verification → `references/topmate-style-profile-page.md`
- Freebie delivery pages hosted on a cloudflare tunnel → `cloudflare-quick-tunnel` skill
