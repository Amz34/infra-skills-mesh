# Disclosing owner-QA findings: the outbound message, then anything public

Companion to `references/firebase-multi-store-exposure-audit.md`. That file covers producing the report;
this one covers what happens after it exists — the short message the user sends, and the "should I post
this?" question that follows.

## 1. The pre-send claim pass (user asks "ye sahi hai?")

Verify the message line by line against the report, then return a corrected ready-to-paste block.
Worked example (The Forest / Invertio, Sep 2026):

| Message claim | Report evidence | Verdict / edit |
|---|---|---|
| "70 user emails, 71 names, photos and locations" | RTDB `/users` 71 records; 70 valid-address email fields; name + photo URL in all; location+bio in a subset | OK as written |
| "All 232 files can be listed, each gives out its own permanent link" | 232 objects listable; token header present on 24/24 **sampled** | Soften: "every file we checked hands out its own permanent link" |
| "Exact tree locations (~1 cm) are public, app shows only the province" | 13-15 decimal lat/lng per tree; UI shows "Riyadh Province Saudi Arabia" | OK, strongest finding after the email table |
| "Play form says no data collected but app stores email/location/photos and sends photos to Gemini" | Listing declares no collection/no sharing; the listing itself states photos are identified with Gemini Vision AI | Re-source to their own words: "its own listing says photos are identified with Gemini Vision AI" |
| "care/health screens show data never recorded; all 163 trees same defaults" | `healthStatus`/`status`/`waterLevel` uniform x163; histories empty | OK |
| "a few hours of work for one person" | fix stages 1-3 costed as an afternoon | OK |
| "open for three months because nobody was watching" | live since June 2026 | OK in a private owner channel; system-level wording if the developer is present |

Rule of thumb: **numbers from the report, generalizations from the sample, and every third-party claim
sourced to the vendor's own artifact.** Add back anything whose absence would cause damage if the short
message is the only thing the developer reads — above all the token/link rotation order.

## 2. What never goes public

Named client, app name, package id, Firebase project id, record/object/user counts, exact GPS or any
coordinates, screenshots of real screens, the finding PDF, proof commands that name the tenant. Also: no
"we found a security hole in X" phrasing — that is exposure, not auditing.

## 3. Anonymized case-study post skeleton (shareable)

Category-level only, no identifiers, no counts:

```
Did a read-only QA pass on a live production app this week. No account created, no write, nothing changed.

Five findings:
1. The realtime database was open. Anyone could read user emails, names, photos and locations without logging in.
2. Every uploaded file could be listed without an account, and files handed out their own permanent download links.
3. Exact GPS coordinates were public while the app itself showed only the province.
4. The store's data safety form declared no data collected, while the app stored email, location and photos.
5. Three screens displayed data that was never actually recorded on the backend.

The security fix is an afternoon of work for one person. The gap was not skill. It was ownership:
nothing would have told them the door was open.

If your product has real users and no one has looked at it in a quarter, that is the actual risk.
Read-only external QA is the cheapest thing you can buy.
```

Handoff rules for it: offer it, do not post it; run the claim-integrity gate
(`~/ops/verify/claim_integrity.py`) before shipping; add hashtags + the org name in the user's normal
post format; no emoji, no em-dash, no client identifiers.

## 4. Recipient framing

- **Owner / founder / leadership** — management summary: what is exposed, in plain terms, blast radius,
  fix cost in hours, and the ownership line. They decide priorities and budget.
- **Developer** — proof commands first, severity table, explicit "not tested" section, numbered fix order.
- **Same thread for both** — keep the message system-level. "No automated check was watching it" lands on
  monitoring; "nobody was watching it" lands on a person in front of his boss.

## 5. Trying to look up the recipient

`https://www.linkedin.com/in/<slug>` returns an authwall redirect to anonymous callers (curl, extractor,
impfetch, headless browser alike) — the profile body is not fetchable without a session, so a role
(owner? developer? employee?) cannot be verified this way. Name searches add same-name noise (e.g. a
TikTok handle that merely resembles the slug). Ask the user which role the recipient holds and frame from
that answer; do not present search hits as identification.
