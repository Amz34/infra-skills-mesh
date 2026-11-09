# Hiring / funnel post replication (LinkedIn)

Recipe from 2026-09-15: replicate a recruiter's hiring post into our own bilingual candidate-intake
funnel post (post + poster image + QR -> form), with the source's company name stripped.

## Read the source properly first

- `lnkd.in` short links do NOT redirect on HEAD: `curl -sIL` returns `HTTP/2 200` with no `location`.
  Resolve them in a browser instead (stacked CDP page, or the anonymous probe) and read the final
  `location.href`. Only then fetch the post.
  Nuance (2026-09-19): with a real browser UA on `curl -sIL -A "Mozilla/5.0 (Windows NT 10.0; Win64;
  x64) …"` the redirect chain and destination CAN come back in the headers, and a second request with the
  same UA returns the destination HTML. Check which of the two you actually got (headers vs login wall)
  instead of assuming either—and note the lnkd.in resolution is only needed for the seed; the post body
  itself always comes from the `og:description` fetch below.
- The post body lives in `og:description` / `twitter:description` of the public post page (fetch with a
  Googlebot-style UA). That yields the role list, the location/nationality lines and the apply link —
  enough to replicate without cloning anyone's file.
- Log which extras the source carried so the user's strip-list can be applied to BOTH creative and copy
  (this source had "Free Accommodation & Transportation" — removed on instruction — plus
  `#WalkInInterview` / `#Aramco`, which we did not carry over because we cannot back those claims).

## Replicated-funnel framing rules (honesty = conversion, not a brake)

- No company name anywhere: creative, copy, hashtags. The post author's own profile carries identity.
- Keep the hooks specific and true: 16 exact role titles (self-relevance), "one form, 2 minutes" (friction),
  "reviewed in order received — early applicants are contacted first" (recency/loss aversion),
  "no fees to candidates, ever" (trust/reciprocity), "confidential, only shortlisted profiles are
  contacted directly" (risk reduction), gold CTA bar + QR (salience + instant action).
- Never fabricate: no applicant counts, no fake deadlines, no implied client (drop `#Aramco`-style tags
  unless real). Frame as a talent pool "for current & upcoming projects", never as a vacancy we do not have.
- First ~210 chars must hook alone — that is all LinkedIn shows before "...see more".
- Structure: EN block (hook, roles, apply link + "or scan the QR", numbered what-happens-next,
  confidentiality) then the AR block as a true mirror, then the hashtag ladder. Hashtags: 20-24 tags,
  mixing volume (#Hiring #SaudiJobs) with niche/role tags (#QAQC #NDT #WeldingInspector) — no
  unrelated trend tags.
- Creative: 1080x1350, inanimate industrial background, big type, role list in 2x8 grid, white-carded QR,
  gold CTA bar, footer with review order + confidentiality. No logos, no faces.

## Deliverable shape that worked

- Files: poster PNG (final pixel size), separate QR PNG, post copy deck (EN+AR+hashtags) — copy deck is
  also pasted inline in chat because the user posts it by hand.
- State the blockers plainly: (1) walled/limited capture step + exact fix steps, (2) anything you could
  not verify (e.g. the group name behind a login wall).
- **LinkedIn Groups cannot be posted to via API** — the Groups API is retired, and `/rest/posts` targets
  member/org authors only. Group posting is a manual user step: hand over paste-ready copy + image and ask
  for the group link if the target needs tailoring. Do not promise an automated group post.
- QA before delivery: content-integrity gate on the copy (`~/ops/verify/claim_integrity.py post <file>`),
  QR exact-URL decode, OCR sweep for banned terms, vision pass on the rendered PNG.
  Full pre-flight: `client-deliverable-patterns` -> `references/funnel-capture-preflight.md`.
  When the replication is judged on *sentiment* parity rather than funnel capture, add the measured chain
  (`sentiment_audit.py` + `parity.py` + card verification) from
  `references/replication-qa-sentiment-and-cards.md` — OCR/vision alone is not proof.
