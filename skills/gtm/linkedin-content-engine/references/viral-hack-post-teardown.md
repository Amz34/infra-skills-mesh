# Teardown: viral LinkedIn "hack" / growth posts (decode before replicating)

## When to use

Aamir forwards a LinkedIn short link (`lnkd.in/p/…`) and says *"expertly analyze the trick"* or
*"replicate this"*. Do **not** restate the post's claims and do not copy its copy. Decode the machine
first, in this order: (1) what is the technical mechanic, (2) who monetises it, (3) what is actually
reusable by us.

## Extraction recipe (all works logged-out)

1. **Resolve the shortener.** For `lnkd.in/p/<id>` a HEAD gives `HTTP/2 301` + `location:` = the canonical
   `/posts/<slug>` URL:
   ```bash
   curl -sIL --max-time 25 -A "<chrome UA>" "https://lnkd.in/p/d22VidNC" | grep -iE "^(HTTP|location)"
   ```
   (Some `lnkd.in/<id>` forms answer HEAD with 200 and no `location` — then fetch with `-L` and read
   `%{url_effective}`.)
2. **Pull the FULL post body with a crawler UA.** The public post HTML carries the *entire* post text in
   `og:description` — observed 3,870 chars on a long post, not the usual truncated snippet:
   ```bash
   curl -s --max-time 35 -A "Googlebot/2.1 (+http://www.google.com/bot.html)" -L "<post url>" -o /tmp/li.html
   ```
   Then regex `og:title` / `og:description` / `og:image` (handle both `property`-before-`content` and the
   reverse order) and `html.unescape`. If an og-field is thin, fall back to the visible-text segments of
   the DOM.
3. **Follow the post's outbound link** — that is where the business model lives. This is the step that
   turns "a hack post" into an explainable funnel.

## Anatomy of the pattern (worked case: `lnkd.in/p/d22VidNC` → author `sahajbana`, 2026-09-15)

1. Hook = number + superlative: *"this 30-second LinkedIn Hack is gold"*.
2. 3-4 micro-blocks, each independently screenshot-able, each closing on a curiosity gap.
3. **Engagement bait finish**: *"screenshot this… see you in the comments"* (forces a comment-section
   visit) plus a headline DM CTA (*"Can't find a job? reach out to me!"*).
4. Outbound `lnkd.in/gq6fiVbR` → the author's own landing page (`sahajbana.in/home-1`) → a **paid
   "Job Search Workshop"**.
5. **Date tell**: the landing page said 28-30 Aug while the post said 25-27 Sep → rolling dates =
   evergreen funnel, not a one-off event.
6. **Proof-less status claims** ("4,500+ professionals", "100% hikes from Apple/BCG/Goldman") with no
   artefact behind them → marketing claim, not evidence. Never reuse them in our own copy.

## The technical layer

The mechanic is usually a real but minor URL parameter dressed up as a discovery. Verified example:
`f_TPR=r<seconds>` (30-minute job filter) — tested commands, live counts and caveats live in
`exec-search-company-ops` → `references/linkedin-jobs-fresh-posting-sourcing.md`. Novelty is typically
zero (the same hack has circulated since early 2025); the value in such a post is **packaging**, not
discovery — say so plainly.

## Reporting standard

- Separate **verified mechanic** (we reproduced it; give numbers/timestamps) from **directional claim**
  (the author's assertion) and label each explicitly.
- State the funnel economics outright — what is being sold, at which step — because that is the part
  Aamir can actually reuse or defend against.
- Close with the usable-for-us version: if the mechanic holds, what changes in our outreach or ops.
- Save the written analysis as a brain note when it is durable
  (`~/brains/ops/knowledge/<domain>/…` + INDEX row) and run the claim-integrity gate on that file before
  finishing.
