# Escrow settlement & payout rails (verified 2026-09-12, escrow.com)

Everything below was read off escrow.com's own fee/disbursement/country pages plus
bank/regulatory references — do NOT re-invent these numbers, and do NOT quote the old
3.25% schedule (that is the superseded table).

## What escrow is for in a flip
- Escrow has **no role in BUYING** a domain (no escrow at registrar checkout). The account is only
  needed for the **sale** — creating it is free and links **no bank**.
- **The payout method is supplied at CLOSING, per transaction** (create transaction → buyer funds →
  seller pushes domain + marks delivered → buyer inspects/accepts → **then** seller fills disbursement).
  Escrow will not advance a transaction without a disbursement method. Never tell the user to
  "link the bank at signup" — that instruction is wrong and wastes their time.

## Fees (escrow.com, USD)
| Item | Amount |
|---|---|
| Standard escrow fee, $0–5,000 | **2.6%**, minimum **$50** |
| On a $2,400 sale | **$62.40** |
| Seller payout, international wire | **$20** |
| Buyer pays by international wire | **+$25** (buyer side) |
| Local GST/VAT on the fees | applies (India) — fees, not principal |

Other marketplaces for comparison: Afternic 25% (NS) / 30% (fast transfer), Sedo 10–20%,
Atom 7.5% / 4.5% AtomPay, Efty $15–36/mo + 5%. Escrow + own lander is the cheapest rail
for a single-name direct flip.

## Rails + hard constraints
- **Disbursement goes to a REAL BANK ACCOUNT only** — no Wise, no Payoneer, no PayPal.
- **Account holder name must match the escrow profile name EXACTLY** (spelling, order) or the wire
  is returned. Third parties cannot be paid — no "send it to my cousin/company" workaround.
- **Supported countries include Saudi Arabia ✅ and India ✅** (unsupported examples: Egypt, Pakistan,
  Yemen). Verify the destination country BEFORE promising a rail.
- Payout needs at minimum: SWIFT/BIC, account number/IBAN, beneficiary name + address matching the
  profile, plus IFSC for India; intermediary bank details may be requested.

## Payout rail: KSA (fewest formalities)
- Single hop, no purpose code, **no e-FIRC**; KSA personal income tax zero.
- Incoming wire cost ≈ SAR 25–75 + FX spread.
- Verify the bank's exact **English** beneficiary spelling (SNB shows `Aamir Malik Zameer`) matches
  the escrow profile name character-for-character.

## Payout rail: India (own-name NRE/NRO account)
- Money arrives as a **USD wire**, converted by the bank; ask for **e-FIRC** as remittance proof.
- Purpose code: **P1590** for personal inward remittance < $10,000; **P0017** for an entity selling
  an intangible asset. Use **NRE** (repatriable, tax-free interest) — NRO also works for a KSA resident.
- Bank/FX charges ≈ ₹600–1,600 all-in. GST registration not required below the ₹20 lakh threshold.
- Non-resident foreign-source income is not taxable in India; a resident holding < 24 months is
  short-term at slab rate — final call belongs to a CA, present it as "confirm with your CA".

## Transaction timeline to quote the user
Account (free) → transaction created against the buyer → **buyer funds 1–5 business days** →
seller pushes domain (same-registrar push = instant; ICANN 60-day transfer lock applies to
registrar moves) → **buyer inspects/accepts 1–3 business days** → seller sets disbursement
→ **international wire 3–5 business days** → bank credit.

## Signup field map (escrow.com/signup-page)
Fields as enumerated: `input[name=username]` (the VISIBLE email box), `input[name=password]`,
`input[name=first-name]`, `input[name=last-name]`, `input[type=email]` (**hidden Olark chat
widget field — not the form**), `input[name=olark-custom-element-#0/#1]`, hidden
`cf-turnstile-response`. Cloudflare Turnstile guards submission — automation cannot pass it
(see `headless-browser-automation` → Turnstile-on-signup bullet); hand the checkbox + submit to
the user and keep the generated password in the vault.

## Data to collect from the user BEFORE the closing (one ask, not a drip)
1. Exact account-holder name as the bank shows it in English.
2. Account number / IBAN + SWIFT/BIC.
3. Full beneficiary address (street, city, postal code, country).
4. Profile address + phone (KYC/verification codes land on this phone).
5. Decision: sale on the **individual's** name vs a **business** name — this drives the escrow
   profile, the WHOIS registrant, and the bank account designation, so it must be settled first.

## Login wall after signup — and how to keep agent control (proven 2026-09-12)
Cloudflare Turnstile guards `/log-in` too, not just `/signup-page`: two programmatic submits with
correct credentials returned to `https://www.escrow.com/log-in?` with **empty fields** (no error shown).
Do NOT respond by sending the user to their own laptop — the agent then loses the session and must
dictate every profile/KYC field by hand. The working handoff renders the *agent's own* CDP tab as a
visible window on the VM's Xvfb screen so the user clicks only the checkbox:
```python
cdp('Target.createTarget', url='https://www.escrow.com/log-in', newWindow=True)  # visible on :99
fill_input('input[name=username]', 'aamir1zahran@gmail.com')
fill_input('input[type=password]', <vault value>)          # prefill, DO NOT submit
```
Then hand over the noVNC/RustDesk screen (`rustdesk-headless-vm-access` →
`references/novnc-quick-tunnel-desktop.md`): user clicks "Verify you are human" + Secure Login, and the
harness — still attached to that same tab — does the profile/address/bank filling afterwards. Verify the
user is looking at *your* window: `DISPLAY=:99 xdotool getwindowpid <win>` must equal the CDP Chrome pid.
Full technique: `headless-browser-automation` → "The LOGIN page is Turnstile-walled too".

## Verifying bank data without guessing (verified 2026-09-12, SNB)
- **IBAN**: 24 chars, first 2 = country, chars 5–6 = bank code. `SA69 1000 0011 1000 2448 9702` → bank
  code **`10` = SNB/NCB**. Run the **mod-97** check in Python before storing — it catches transcription
  slips instantly and costs nothing.
- **SWIFT/BIC**: never quote from memory. Read it from the bank app (`Account details → SWIFT/BIC`);
  SAMA/SWIFT records list SNB as **`NCBKSAJE`** (legacy `NCBK` = National Commercial Bank). Treat any
  candidate the user hasn't confirmed as unconfirmed, and tell them to eyeball it once.
- **Unlabelled numbers are ambiguous** — the user sent `Snb swift / <name> / <IBAN> /0574268856`; that
  last value was the **Saudi mobile**, not an account number. Ask "mobile ya account number?" before it
  lands in a profile field.
- Store everything as named vault keys in one space (`SNB_IBAN`, `SNB_HOLDER`, `SNB_SWIFT`,
  `SNB_BANK_CODE`, `ESCROW_COM_EMAIL/PASSWORD`) so the values never need to be re-typed into chat.

## Saudi National Address → escrow profile field map (Jeddah sample, 2026-09-12)
A Saudi National Address block prints 7-digit-padded values; escrow/postal forms want the standard
5-digit code. Normalize, don't paste:
| National Address field | Escrow field |
|---|---|
| Street Name `7480` (can be a NUMBER) | Address line 1: `7480, <district>` |
| District Name `King Abdul Aziz Medical City` | part of address line 1 |
| Building No. `07480`, Additional No. `3522`, Unit `00003522` | Address line 2 (verbatim) |
| City `JEDDAH` / `جدة` | City: `Jeddah` (Latin script) |
| Zip `0022382` (**leading-zero padding**) | Postal code `22382`, or `22382-3522` if a full-code field exists |
| Mobile `+966 57 426 8856` | Profile phone: `+966 57 426 8856` (bank-registered number preferred — OTP lands there) |
| — | State/Province `Makkah`, Country `Saudi Arabia` |

Explain the zip normalization in the handover message ("`0022382` → `22382`") so the user doesn't think
the agent mistyped their address — and keep the additional/unit numbers out of the postal field.
