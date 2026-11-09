# Review-request mechanics (Telegram → LinkedIn service page)

Goal: a candidate finishes the free deliverable at peak gratitude and can leave a public
review without thinking, typing, or deciding anything.

## The link

- Review composer: `https://www.linkedin.com/services/page/<page-id>/review/create/`
- The plain service page (`…/services/page/<id>/`) and the `/admin/` page do **not** put the
  visitor in the composer — always the `/review/create/` path.
- **No prefill exists.** LinkedIn accepts no query parameter, fragment, or form field that
  pre-loads review text. Any instruction along the lines of "already typed in the box" must be
  honoured by shipping the text inside the chat instead. Say copy-paste, never prefilled.

## Message shape (one bubble, ~1,000 chars)

```
<b>One more thing before you go.</b>       <- value already delivered above this
…this stays free / pay it forward…       <- neuromarketing, no signup-card-upsell wording
<b>I've already written the review for you.</b>

<b>⭐ Your review is ready — 20 seconds</b>
1. Tap Open the review box
2. Tap the draft to copy, long-press → Paste
3. 5 stars → submit

<pre>{draft}</pre>                       <- tap-to-copy on Telegram
<i>Swap a word or two so it sounds like you — this goes on your own profile.</i>

[⭐ Open the review box](review/create)   [🔄 Different draft](callback review:new)
```

`<pre>` gives a one-tap copy; `<code>` wraps badly at 300+ characters. HTML-escape the draft
before interpolating (`html.escape`) or an apostrophe plus angle bracket kills the send — and
`sendMessage` returns `ok:false` with the reason in `description`, so log it.

## Draft variety that survives scrutiny

- Three slot pools: opener (what happened), middle (what the report actually did), closer
  (recommendation). ~10 each ⇒ ~1,000 combinations, 205–295 characters per draft, which fits
  LinkedIn's box without scrolling or editing.
- Persist served drafts in `state/reviews_served.json`: skip anything in this chat's last 8 and
  in the last 80 served bot-wide. Two candidates posting identical public text on different
  profiles is the fastest way to get the reviews filtered.
- Walk alternatives with `(random + salt + attempt) % len(pool)` over ~40 attempts before
  falling back to a fixed combination — a pure random draw can collide three times in a row.
- Pass `salt=int(time.time())` from the regenerate callback so `🔄 Different draft` never
  returns the same text twice within the same second.
- Keep every clause about the *service*, not the outcome: free, fast, specific score breakdown,
  keyword gaps, rewritten bullets, 30-day plan. A draft promising "three interviews" is a lie
  the reviewer is about to publish under their real name.

## Funnel placement

Send the audit report first, then the CTA as the message immediately after it (never prepend the
ask). Regenerating the draft sends a fresh bubble rather than editing the old one — the button
stays usable and the history shows intent.

## Daily cap instead of a paywall

`state/resume_audits.json` keyed by chat id, N audits/user/day (4 is enough), friendly reset
message. Capping protects the shared free-tier model quota without ever hinting at payment.
