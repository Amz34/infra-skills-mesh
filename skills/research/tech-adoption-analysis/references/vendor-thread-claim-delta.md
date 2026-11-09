# Vendor-thread claim-DELTA audit

For the case: bhai forwards/dumps a vendor mail thread ("analyze the *jev jev jev* emails in
`<acct>@gmail.com` and see how it's useful for our infra — QA yourself") for a product we have
**already audited once**. The deliverable is not "summarise the email" — it is
**what changed since our last verdict, and does that change the verdict**.

## 1. Reconstruct the lifecycle from the mailbox (do this first)

Never analyse only the mail he named. A vendor product thread is a lifecycle and the important
mails sit at the ends of it. With `hermes-email-access`:

```bash
cd /tmp && env HOME=/home/ubuntu himalaya -c ~/.config/himalaya/config.toml \
  -a <account> envelope list --page-size 200 -m INBOX > /tmp/all.txt
grep -iE "<brand>|<apex-domain>" /tmp/all.txt     # BOTH — transactional mail uses the domain
```

Then read each UID to its own file (`message read <UID> -m INBOX > /tmp/<tag>_<uid>.txt`) and
present a **dated UID timeline**. The 2026-09-21 Jev/TypeSafe run produced:

| UID | when | from | what it was worth |
|-----|------|------|-------------------|
| 8399 | 20-Sep 00:27 | Google | third-party OAuth consent (proves the signup path) |
| 8401 | 20-Sep 07:45 | TypeSafe | "You're on the waitlist" |
| 8392 | 19-Sep 16:16 | Joon | first marketing contact (JEV video scoring) |
| 8437 | 21-Sep 01:57 | TypeSafe | **account ready** + `console.typesafe.ai/login?waitlist=<email>` → the actionable one |
| 8438 | 21-Sep 05:16 | TypeSafe | **sign-in OTP — expired ~10 min later**, login never completed |
| 8447 | 21-Sep 12:54 | Vaibhav Sisinty | the "JEV JEV JEV" newsletter everyone quotes |
| 8449 | 21-Sep 14:04 | The Code | second newsletter, "finally try new model Jev" |

Two lessons: the **account-ready / OTP mails carry the actionable capability** (key minting), and
the **newsletters carry only the marketing numbers**, which are the weakest evidence in the thread.

## 2. Re-verify ONLY the previously-unverifiable claims

Pull the last audit's own unresolved items and re-test exactly those. Cheap probes, all read-only:
`curl -s https://pypi.org/pypi/<pkg>/json`, `https://registry.npmjs.org/<pkg>`,
`https://api.github.com/repos/<owner>/<repo>` (stars + `pushed_at` proves a repo is alive, not
parked), the docs `llms.txt` for claim numbers, and the vendor console/pricing URL for reachability.

Result of the 2026-09-21 delta on the 19-Sep audit:

- `cooksafe` **0.1.0 now on PyPI** + pypi.typesafe.ai serving 0.1.0/0.1.1/0.1.2 → the offline
  benchmark replay is reproducible on our box. This single line retired the audit's only blocker
  ("not independently reproducible") and upgraded the whole class from watchlist to *decidable*.
- `@typesafe-ai/sdk` v0.6.0, MIT, first publish 12-Sep-2026 → the SDK is real, not a landing page.
- Repos named in the mail (`itsaam/slop-detector` pushed 20-Sep, `valentynkit/jev-skip`,
  a 226★ adapter) are live → **the links in the mail are not phantom inflation** (see
  `ai-newsletter-verification.md` for that whole checklist — reuse it here).
- Docs cookbook `parallel_questions`: 13 questions, 12.2x cheaper / 10.0x faster — matches the
  spec-sheet claim, still vendor-run.

## 3. Report the delta, and separate "cannot verify" from "measured false"

Three buckets, never blurred:

1. **Verified today** — with the probe output.
2. **Structurally unverifiable** — "18x faster on Vercel", "half a second", "ChatGPT co-inventor",
   a rival 50x on-device claim (Laya, published since Mar-2025 → makes the "first/brand-new" framing
   shaky), and pricing (the page 404s, so there is no public price to compare).
3. **Measured by us** — and here the proxy-lane rule bites: our negative numbers came from the
   `system-one-adapter` + DeepSeek lane, NOT real Jev. Say "unreproduced on our lanes via a
   stand-in adapter; the real-key head-to-head is pending", never "the 7.3% claim is false".

## 4. Close with the sharpest remaining action

The thread ended with the two mail-derived next steps: the real key exists (account ready) and the
waitlist OTP had already expired, so the reply offered **one** concrete action — "I trigger the OTP,
read it from the mailbox, mint the key, re-run the 531-pair head-to-head in ~30 min" — and asked
before creating credentials on a third-party account. Credential creation on someone else's account
is not read-only recon; offer it, don't do it silently.

Also worth reusing: the vendor's own SDK ships >20 cookbooks whose *patterns* (guardrails,
prompt-injection passage filtering, citation checking, confidence/intent routing) port into our
stacks (`rag-connector`, `claim_integrity`, model-tier cost gate) regardless of whether the vendor's
headline benchmark survives — so a "not proven" verdict on the numbers can still be a "worth
porting the patterns" verdict on the architecture.
