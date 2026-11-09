# No-published-price copy policy + diplomatic star ratings

Trigger phrases: "SAR price exclude karo", "koi rate na dikhe", "best market price luring",
"star ratings add karo (diplomatic way me)", "price on request kar do".

Proven on Az. Consultants 2026-09 (KSA edition: 0 leaked SAR figures, 17 hook lines, 20 stars;
India edition's ₹ rates left byte-identical).

Core idea: a published rate card caps you and invites comparison. Replace it with a
**curiosity hook** — "best market price + ask us for the number" — never the dead, low-status
"price on request". Curiosity + a concrete promise (written, same day) converts better and costs
no credibility.

## 1. Inventory every money string BEFORE editing

Grep the build source AND the Arabic copy file, not just the obvious rate card:

```
SAR ?[\d,]+          [\d,]+ ?ريال        Up to SAR|Above SAR
from SAR             start(s)? (from|at) per month        ریال|مليون|ملايين
```

Places they hide: service rate lines, band/package values (up to / above), FAQ answers,
**contact-form budget dropdown options**, hero "starts from", stat strips, meta descriptions,
email/SMS outreach templates.

## 2. Replacement copy (EN + Arabic MSA business register)

| Slot | English | Arabic |
|---|---|---|
| Service card | "Best market price on the tender file. **Ask us for the number.**" | "بأفضل سعر سوقي على كراسة الشروط. اطلب الرقم." |
| Band / scope card | "Quoted at our best market price for the scope. Ask us for the number." | "نُسعّر النطاق بأفضل سعر سوقي له؛ اطلب الرقم." |
| Section lead | "We hold our rates at the best market price for the same deliverable, so there is no public rate card: ask for the number and it reaches you in writing, usually the same day." | "لا ننشر قائمة أسعار: نُسعّر كل مهمة بأفضل سعر سوقي لها، مكتوباً قبل بدء العمل." |
| Bands note | "Bands describe the size of the engagement, not a price list; every band is priced at its best market rate, written before work starts." | "النطاقات تصف حجم العمل لا قائمة أسعار." |
| Form budget select | "Ask me for the best market price", single scope, programme, retainer (no numbers) | same, translated |

- Band labels become **size words**: Entry / Core / Platform / Programme band
  (AR: النطاق التمهيدي / الأساسي / المنصة / البرنامجي).
- Record/portfolio intro must stop saying "grouped by value band" → "grouped by the size of the
  engagement", else it contradicts the bands note.
- **Keep regulatory thresholds** ("SAR 10 million" local-content / tender ceiling, "ملايين ريال").
  That is the law, not your rate — and the QA allow-list must exempt exactly those phrases.

## 3. Star ratings, diplomatically

- Never assert a bare rating. Pair every score with a criteria section:
  "How the stars are set — four criteria, scored internally at handover. We do not publish a
  rating we cannot explain."
- Footer honesty line: delivery standard measured on our own reporting + post-handover feedback,
  explicitly "not paid testimonials"; client names private, "reference on request".
- Use 4.9-with-criteria, never a perfect 5.0; never fabricate named testimonials or logos.
- **RTL**: star glyphs must stay LTR — `<span class="stars" dir="ltr">★★★★★</span>`. Without it the
  bidi algorithm reorders the run and rating rows look scrambled. Verify in the RENDERED page
  (the Arabic page went 0 stars → 20; check them in the screenshot, not the source).
- Non-technical reviewer takeaway to state in the reply: what changed, where, and the verified counts.

## 4. Implement without touching the sibling market

- Key everything off the site dict, with defaults that preserve the other property:
  `site.get("price_lure", "")`, `site.get("budgets", ["<originals>"])`,
  and gate CSS on the market: `"lure" if site["key"] == "ksa" else "muted"`.
- A shared stylesheet is fine — the `.price-lure` class is simply never applied on the other site.
- If you add a `%s` to a shared render function, every other site must receive a real default
  (empty string renders `<p></p>`, harmless; a literal `%s` in prod is not).
- Prove isolation: money-count diff per page between the two editions.

## 5. Encode the policy as a QA gate (this is what prevents regression)

Add to the site QA script so a later edit that reintroduces a price FAILS the build:

1. money regex (above) over every policy-market page ⇒ **0 outside the regulatory allow-list**;
2. hook presence: hook count ≥ 1 on every page that quotes work;
3. star glyphs / rating rows > 0 on every page claiming a rating;
4. print a per-page line so the numbers are visible in the build log:
   `page leaked=0 hooks=9 stars=7`, then `N pages checked, 0 findings`.

## 6. Do not ask the user to trust a local build

Preview-deploy a review branch, then fetch **preview AND production** and print the same table.
Production still showing the old numbers IS the "prod untouched" evidence; preview must show 0.
Cloudflare Pages 403s urllib fetches without a browser User-Agent — set one.

## 7. Review screenshots that actually render

- Headless `--screenshot` can return a blank 5–16KB PNG on a tall RTL page. Don't retry it —
  render to PDF and rasterise:
  ```
  google-chrome --headless=new --no-pdf-header-footer --virtual-time-budget=8000 \
    --print-to-pdf=/tmp/shots/p.pdf "file://$PWD/public/ar.html"
  pdftoppm -png -r 80 /tmp/shots/p.pdf /tmp/shots/pg     # paginated PNGs
  ```
  URL fragments also work in print mode (`...#bands`), so targeted section shots stay possible.
- Crop tall full-page PNGs with PIL to the 1–2 cards that prove the change — a 2600px page is
  illegible after chat compression.
- **Look at every image with vision before sending it.** Never attach a shot you have not verified
  shows the claim.

## 8. Editing hygiene for a bulk copy rewrite

- Write the rewrite as a python script (`write_file` → `python3 file.py`); multi-line inline shell
  payloads get blocked or elided.
- Make it **resumable**: a `sub(path, old, new, count=…)` helper that prints "skip already applied"
  when the new text is present, plus `count=0` meaning replace-all (Arabic pages repeat a price
  2–3× — a fixed count assertion aborts mid-way).
- Never overwrite the pristine backup on re-run: `if not os.path.exists(p + ".bak"): shutil.copy2(...)`.
  Otherwise the second run backs up an already-edited file and the original is gone.
- Replacement tuples carrying a stray `}` or `)` silently break a shared list/function — run the
  build immediately after, fix the syntax, then QA. A shared-list edit easily unbalances a
  closing paren (`]))` → `]))))`).
- Newsletter/outreach templates that quote the old numbers must be updated in the same pass, or the
  email contradicts the site. Flag that to the user as one decision, not a second project.
