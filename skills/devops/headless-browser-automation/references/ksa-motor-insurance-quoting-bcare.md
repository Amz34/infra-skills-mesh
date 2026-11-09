# KSA motor insurance quoting (Bcare) — verified working recipe 2026-09

Class of task: "find the cheapest motor insurance price in KSA for <vehicle> and give the link".
Market leader aggregators: **Bcare** (bcare.com.sa, 23 insurers, no account signup —
only an OTP) and **Tameeni** (tameeni.com/motorapp, login-walled). Bcare is the easier
one and it is the one that produced live quotes.

## Inputs you must get from the user

| Input | Why |
|---|---|
| Iqama / National ID (10 digit) | Bcare's required field; pulls the Najm/registry record |
| Vehicle sequence number (الرقم التسلسلي) | identifies the exact vehicle, e.g. 712829110 |
| OTP | Bcare sends a login OTP to the mobile on the record — only the user can read it |

Never write the Iqama into files/summaries; the sequence number + plate are enough to
refer back to the vehicle. Ask for the OTP only when the app is sitting on the OTP screen.

## UI flow (do it through the UI, not by replaying requests)

1. Open `https://www.bcare.com.sa/en/motor-insurance` -> "Get Quotations".
   The site also serves on `https://bcare.com.sa/...` (non-www) which is **same-origin
   with the APIs** — useful if you need in-page fetches.
2. Fill *National Id / Iqama* + *Sequence Number* (native-setter trick, see
   `angular-spa-forms-captcha-otp.md`). Typing the ID auto-fires
   `getVehiclesByNin`, which returns the registered vehicles — use it to confirm
   make/model/year/plate before quoting.
3. Captcha: read the app's image (pad + 8x + your own eyes), set the input, tick the
   agree checkbox, DOM-click **Show Quotations**. Wrong code = "Wrong Input Captcha"
   and the image refreshes; re-read and retry rather than guessing.
4. App moves to `/en/submit-inquiry`: Vehicle Value (auto-filled from the registry,
   e.g. 20,000), Insurance start date (auto = tomorrow), Other Info / Add Driver /
   Discounts → DOM-click **GET QUOTES**.
5. OTP gate ("We have sent OTP code to your mobile number - 05****4381") → get the code
   from the user, fill the 4 boxes, verify.
6. Quotes land at `https://bcare.com.sa/en/quotations/<externalId>` (e.g.
   `3954335f49d0419`). Tabs: **Third Party Liability / Mumayaz / Comprehensive**;
   "Sort By Price" → **Low**; a surplus-discount toggle.
   Each card: Basic Premium, optional admin fee, No Claim Discount, VAT, then two
   totals — **the last number is the final surplus-discounted price**. `BUY NOW` is a
   button (session checkout), not an href, so a deep "buy" link does not exist; the
   quotation URL + the user's own OTP login is the deliverable link.

## API surface (for verification; WAF blocks hand-made replays)

- `GET https://bcare.com.sa/CaptchaApi/api/GetCaptcha?language=en&channel=portal`
  headers `Authorization: Bearer <Math.random()>!!`, `Channel: portal`, `Language: 2`
  → `{data:{image,token}, expiredInSeconds:600}`.
- `GET /InquiryApi/api/InquiryNew/getVehiclesByNin?Nin=<id>` → owner's vehicles.
- `POST /InquiryApi/api/InquiryNew/init-inquiry-request` body
  `{MobileVersion:null, VehicleIdTypeId:"1", captchaInput, captchaToken, nationalId,
  ownerTransfer:false, policyEffectiveDate, sequenceNumber, language:"en",
  channel:"portal"}` → full registry model: vehicle (plate, chassis, cylinders,
  estimated value, usage flag) + driver (birth month/year, education, medical, NCD info).
  * `policyEffectiveDate` must fall inside the **44 days starting tomorrow**; today's
    date returns "Policy effective date should be within 44 days starts from tomorrow".
- `edit-inquiry-request` and the `QuotationApi/*` routes returned 405/404 to hand-made
  fetch calls even same-origin (WAF) while the app's own identical call succeeded.
  Conclusion: drive the UI, don't reimplement the endpoints.

## Reporting the result (what Aamir expects)

- Cheapest first, with the arithmetic visible once (basic - NCD + VAT - surplus = total),
  then a compact runners-up table, then the runners-up categories (cheapest
  Comprehensive, cheapest Mumayaz) since buyers often switch tier.
- Include the live quotation URL and say the OTP login is needed, plus the motor
  insurance entry page.
- Screenshot the sorted list and send it as MEDIA proof.
- Add the insight that actually saves money: the registry's
  `isVehicleUsedCommercially` flag drives the premium. A **2013 Corolla** with
  commercial usage quoted TPL from **SAR 1,111.18** (GIG) while private-use TPL for the
  same car sits far lower — if the car is privately used, tell the user to correct the
  usage code (Absher / Muroor) and re-quote.
- Worked example (Sep 2026, Corolla 2013 XLI 1.6, seq 712829110, 35 y/o Indian expat,
  10 yrs licence, policy start next day): TPL cheapest **GIG 1,111.18**; Tree Digital
  (Tawuniya) 1,329.22; Tawuniya 1,458.48; Liva 1,757.48; Tawuniya Sanad Plus 1,957.58;
  Arabia 2,152.78; … ACIG City 6,317.39. Comprehensive cheapest **Tawuniya 2,401.48**;
  Mumayaz cheapest **Al Etihad 4,226.99**. All VAT-inclusive.
- Reply in Hinglish, tables/bullets compact; state policy start date and that VAT is in.
