---
name: linkedin-content-engine
description: Use when creating LinkedIn posts, comments, DMs, carousels.
version: 1.0.0
author: Aamir Zameer — Hermes
license: MIT (ported from Prospeda claude-gtm-skills)
metadata:
  hermes:
    tags: [linkedin, content, gtm, personal-brand, carousel]
    related_skills: [b2b-outreach-email, cold-email-tone-matrix]
---

> **Claim-integrity gate (mandatory, 2026-09-15):** every claim in this output must be provable.
> Before ship run `python3 ~/ops/verify/claim_integrity.py <mode> <file|dir>` and clear all HIGH
> with `[src: ...]` evidence or `[claim-ok: reason]`. Rule: `~/brains/ops/rules/content-integrity.md`.
> Skill: `content-integrity-guardrail`.

# LinkedIn Content Engine

Ported from Prospeda's GTM library (MIT) and adapted for Aamir's stack: personal brand
(Hyderabadi Urdu / Deccani Roman Urdu voice), Sanad (client-facing, pure English, one-word brand)
and AVVS (bilingual corporate).

## When to Use

- Weekly LinkedIn content for the personal brand (posts, carousels, comments).
- Client-facing LinkedIn presence for Sanad/AVVS (pure English / bilingual corporate).
- Warm outreach via LinkedIn DM (with a signal, not spam).
- Profile optimization (headline, about, featured).

## Content Rules (non-negotiable)

- **NO human faces or living beings** in any post/carousel image — inanimate visuals only
  (architecture, buildings, office interiors, servers, tech/data graphics).
- **NO phone number in public posts** — naam + designation + email only. Phone sirf DM/prospects me.
- Personal brand voice: Hyderabadi Urdu (Deccani) Roman Urdu — baba/miyan/arre flavor, natural
  AI-free tone. Client-facing (Sanad/AVVS): pure English, one-word brand, AI-free copy.
- Every post needs a real insight or story — no AI-slop filler.

## Patterns

### Post Types (7)

```
Write a LinkedIn post about [TOPIC] using [TYPE].

Context:
- My audience: [WHO FOLLOWS ME]
- My voice: [SELECT: Hyderabadi Urdu personal / English professional / Bilingual corporate]
- Goal: [ENGAGEMENT / AUTHORITY / LEADS]

Types:
1. Story (personal lesson, 3-4 lines, relatable)
2. Insight (contrarian take on industry assumption)
3. How-to (numbered steps, save-worthy)
4. Opinion (position on a topic, invite debate)
5. Client result (case study, no names without permission)
6. Behind-the-scenes (process, tools, real work)
7. Question (community engagement, answers feed next posts)
8. Correction / audit ("that list doing the rounds is wrong — here is the verified version")

Rules: hook in first 2 lines, one idea per post, end with a question or CTA, under 150 words.
```

### The Hook Bank

```
Generate 20 hooks for LinkedIn posts about [TOPIC].

Mix:
- Curiosity gaps ("The reason most [X] fail is not what you think")
- Contrarian ("Everyone says [X]. They're wrong.")
- Specific numbers ("In 30 days, [RESULT]")
- Story openers ("Three years ago, I...")
- Direct address ("If you run [TYPE OF BUSINESS], read this")

Rules: under 12 words each, no clickbait, no ALL-CAPS, honest.
```

### Comment Strategy (3 types)

```
Write LinkedIn comments for [POST CONTEXT].

Types:
1. Add-value comment (insight/experience that extends the post)
2. Agree-and-extend (support + your angle)
3. Question comment (curiosity that starts a thread)

Rules:
- First comment within 60 minutes of the post going live
- Comments longer than the post feel desperate — keep under 2 lines
- Reference the post's idea, not the person's fame
- No "Great post!" — add something they can't get from the post itself
```

### Warm DM Outreach

```
Write a LinkedIn DM to [PERSON] at [COMPANY].

Context:
- Signal: [WHAT TRIGGERED THIS — THEIR POST, HIRE, LAUNCH]
- My offer: [WHAT YOU DO]
- Goal: [CONVERSATION / CALL / INTRO]

Rules:
- Reference something specific from their profile or activity
- Under 60 words
- No sales language
- Ask one small question
- Never send the DM with a connection request template
```

### Profile Optimization

```
Rewrite my LinkedIn profile sections.

My positioning: [WHAT I DO + WHO I SERVE + RESULT]
My background: [KEY FACTS, YEARS, CREDENTIALS — e.g. SCE 317164, PME 13+ yrs]
My voice: [SELECT]

Sections:
1. Headline (under 220 chars, keyword-rich, outcome-focused)
2. About (first 3 lines must hook — rest is cut off)
3. Experience summaries (results over duties)
4. Featured post ideas (3)

Rules: no buzzwords, no "passionate about", numbers where possible.
```

### Weekly Content Plan

```
Create a 7-day LinkedIn content plan for [ACCOUNT TYPE: personal / Sanad / AVVS].

Include per day:
- Post idea (type + topic + hook)
- Carousel or text post?
- Best posting time (audience: [TIMEZONE])
- One engagement action (comment on 3-5 relevant posts)

Rules:
- Mix: 2 educational, 1 story, 1 opinion, 1 client/behind-scenes, 2 engagement
- All ideas must be authentic to [VOICE]
- No repetitive "motivation" content
```

### Carousel Structures (client-facing)

```
Create a LinkedIn carousel outline on [TOPIC].

Structure (10 slides max):
1. Hook slide (bold claim or question)
2-3. Problem slides (paint the pain)
4-7. Solution/value slides (one idea per slide)
8. Proof (numbers, client result)
9. CTA slide (single clear ask)
10. Brand slide (wordmark + contact line)

Rules:
- ONE idea per slide, max 8 words per slide headline
- Inanimate visuals only (NO human faces) — architecture, buildings, offices, servers, data graphics
- Client-facing copy: pure English (Sanad) / bilingual EN+AR (AVVS)
- Build technique: see the carousel-pdf reference inside the `b2b-outreach-email` skill (square slides PDF)
```

## Verified Correction Posts (user sends a document → audit → post)

Aamir often forwards a PDF / "top 10" list / calendar / scheme sheet that is doing the rounds and asks
for an expert post. The winning format is a **fact-audit post**: verify every row against the primary
source, then publish the corrections + the official links + a 4:5 correction card.
Full recipe (extraction commands, four-axis audit, card loop, caption skeleton):
`references/verified-list-audit-posts.md`.

Non-negotiables:

- **Audit the primary source, never the aggregator.** For schemes / tenders / portals: open the official
  portal for each claim. `pdftotext` drops a PDF's hyperlinks — use `pdftohtml -c -i -noframes` + `grep -o
  'href="[^"]*"'` when the links are part of the deliverable ("all links in the description").
- **Check what is MISSING, not just what is wrong.** Eligibility filters (gender, city tier, marks,
  streams, final-year status) and application windows decide real outcomes — an omission is a correction.
- **Provenance tell**: forwarded AI-compiled lists keep `?utm_source=chatgpt.com` on their links. It is
  countable, so it is an honest curiosity hook ("10 of its 20 links still carry it") and it explains the
  stale numbers. Claim only the number you measured.
- **Self-audit the hook count before publishing.** This session's first draft said "7 things are wrong";
  re-checking against the evidence gave 4 stale numbers + 6 non-government/dead links + zero deadlines.
  The honest version was just as punchy — an inflated count on a jobs/scheme post gets checked.
- **Ship every link the user asked for.** Commentary is capped at 3000 chars — `len()` it and trim prose,
  never the links. For an audit post the official-portal list IS the value: no "link in first comment" variant.
- **Card**: 1200×1500 HTML → headless Chrome screenshot → look at the PNG with vision → patch CSS → re-render.
  Fill leftover vertical space with **more verified rows** (extra correction cards, a "what's open now" date
  strip), never by inflating padding. Inanimate visuals only.
- **Comment-keyword CTA** (e.g. `Comment "CALENDAR"`) obliges the user to DM the asset by hand — an API
  cannot comment or DM. Say so in the handoff message and offer to build the 1-page verified tracker.

## Viral Hack-Post Teardown (decode before replicate)

When Aamir forwards a LinkedIn short link (`lnkd.in/p/…`) with *"expertly analyze the trick"* or
*"replicate this"*, do not restate the post's claims and do not copy its copy. Resolve the link, pull the
**full body** (crawler UA — the entire post text sits in `og:description`), then follow the post's
**outbound link** to see who monetises it, and report the verified mechanic separately from the author's
directional claim. Anatomy checklist, extraction commands and a worked case:
`references/viral-hack-post-teardown.md`.

## Replication QA — measure parity, do not eyeball it

When the ask is *"replicate this post, audit the sentiment, do QA yourself, use CLI"*, the deliverable is the
copy **plus** a reproducible audit that proves it. Working template: `~/ops/linkedin/newposition/`
(`./run_qa.sh` = VADER sentiment audit → source-vs-draft parity bands → `li_reach.py score` gate →
claim-integrity → card render → deterministic card verification → one-glance summary, all into `out/`).
Full recipe, the headless-measurement trick and the OCR/VADER pitfalls:
`references/replication-qa-sentiment-and-cards.md`.

- Measure the source first (sentiment dims + gate score), then measure each draft against it. Report the
  numbers you got, including the residual gate deductions — never reword a finding to defend copy.
- Deterministic checks are the primary evidence: headless Chrome geometry + WCAG contrast + OCR per card.
  A vision pass is secondary confirmation, not the proof.
- The emotional signature usually lives in the source's short human asides, not its structure — copying the
  skeleton alone shows up as a warmth DRIFT.

## Algorithm Reality & the Reach Loop (outside-in ranker)

When Aamir asks to *"extract / replicate LinkedIn's algorithm"*, to *"implement it on our infra"*, or to make
posts *"viral on every post"* — answer with the three-way verdict and then ship the cheap artifact in the
**same session** (his `karo / khud karlo` pattern means verdict-only replies come back as another ask).
Full verified evidence — Feed SR paper facts, the OSS architecture blueprint, the token-scope probe table,
tool usage — is in `references/reach-loop-and-algorithm-facts.md`.

- **Architecture**: extractable as a blueprint only (LinkedIn open-sources Kafka/Samza/Pinot/Venice/…).
  Never propose running that stack on the VM — thousands-of-nodes design, zero data to feed it.
- **Algorithm**: not extractable, and a copy would be worthless — the ranker's value is 1.2B members'
  interaction data, not the code. The *mechanism* is public (arXiv **2602.12354** Feed SR transformer that
  replaced DCNv2; sequential user history; dwell/**P(skip)** prediction; early-momentum test slice), and
  mechanism is what we optimise against.
- **What we do instead**: model the ranker from the outside on our own posts —
  `~/ops/linkedin/reach/li_reach.py` (`seed`, `score draft.md [--gate]`, `add`, `ingest`, `list`, `report`;
  ledger `ledger.jsonl`; gate blocks < 62/100). Study doc: `~/ops/kb/linkedin-algorithm-reverse-study.md`.
- **Metrics come from the UI, not the API**: the token is publish-only (`w_member_social`) — every analytics
  read returns 403/404 (probe table in the reference). Have the numbers pasted into `ingest` (~20 s/post);
  correlations need ~20-30 metric rows, so call the ledger "rails" until then, not a model.
- **Never promise virality.** LinkedIn is not a virality platform (personalized distribution + anti-spam
  gates). Promise the per-post floor lift + more right-tail hits, and refuse pods/engagement automation
  (shadowban risk). The honest verdict is what Aamir is buying.

## Voice Cheat-Sheet

| Context | Voice | Example flavor |
|---|---|---|
| Personal brand (Aamir) | Hyderabadi Urdu Deccani | "Arre baba, maine 13 saal PM ka kaam kiya…" |
| Sanad | Pure English, AI-free | One-word brand, service-led |
| AVVS | Bilingual EN+AR corporate | EN body + Arabic accent lines |

## Image Post Flow (v2 ugcPosts — VERIFIED)

1. Design card: HTML → headless Chrome screenshot (`google-chrome-stable --headless=new --screenshot --window-size=1200,627`), Inter font installed. Verify render via tesseract OCR + pixel-check the CTA button region.
2. `POST /v2/assets?action=registerUpload` — recipes `urn:li:digitalmediaRecipe:feedshare-image`, owner URN, serviceRelationships OWNER/userGeneratedContent → get `asset` URN + uploadUrl.
3. `PUT` image bytes to uploadUrl (Content-Type: application/octet-stream).
4. `POST /v2/ugcPosts` — shareMediaCategory `IMAGE`, media `[{status: READY, media: asset_urn}]`. **PITFALL: omit the `description` field entirely — a plain string returns 422 "record type is not backed by a DataMap".**
5. Verify live: web_extract the post URL (renders for logged-out).

## Text Post + Comment Flow (VERIFIED 08-27)

Text post via `/rest/posts` — same payload as video but **omit `content` entirely**:
```json
{"author": "urn:li:person:...", "commentary": "...", "visibility": "PUBLIC",
 "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
 "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": false}
```
Response header `x-restli-id` → post_urn `urn:li:share:{id}`; post URL = `linkedin.com/feed/update/{post_urn}` or the /posts/ activity URL from og:url.

Comment on own post (GitHub-link first-comment play):
- ❌ `/rest/socialActions/{post_urn}/comments` + `LinkedIn-Version` header → `403 ACCESS_DENIED partnerApiSocialActions.CREATE` (token lacks this permission)
- ✅ `/v2/socialActions/{post_urn}/comments` with `X-Restli-Protocol-Version: 2.0.0`, **NO LinkedIn-Version header** → 201 + comment id. Body: `{"actor": person_urn, "message": {"text": "..."}}`
- ⚠️ Both endpoints need the URN **URL-encoded** in the path (`urn%3Ali%3Ashare%3A...`) or you get `400 Syntax exception in path variables`
- ⚠️ GET comments (`/rest/socialActions/{post}/comments`) → `403 GET_ALL.NO_VERSION` with w_member_social token — verify comment via CREATE's 201 id, not a GET readback

## Comment-Gated Lead Magnets (keyword → DM the asset)

Highest-converting pattern for a big reference asset (dataset, tender/channel map, playbook): the asset is
**never linked publicly**. The post asks for a **comment keyword**, and the asset goes out by DM to
commenters only.

- **One assign word**, short/uppercase/on-brand (e.g. `BID`), written in BOTH the post and **on the creative
  itself** (`COMMENT "BID" → full file · No obligation`) so the poster still works when shared out of context.
- **Never** put the link in the post or in the first comment — it kills the gate and LinkedIn suppresses links.
- The asset must be **publishable before the post ships**. Notion page publishing is a UI-only user step (see
  the `notion` skill) — get that action first or the giveaway breaks on launch day.
- CTA is DM-based and soft: `Comment "BID" and I will send it to you directly.` A free "send me one live
  tender and I'll tell you honestly if it's winnable" demo offer converts far better than a hard sell.
- Comments are warm signals: follow up in DM, deliver one link, do not run the whole pitch in the comments.

### Poster / single-image creative rules (Aamir's standard)

- Big, OCR-readable type (hook ~70px+ on a 1200×1500 canvas). Render headless Chrome, then run `tesseract`
  over the PNG before posting — if OCR garbles it, a human on a phone will too.
- Show **figures + capabilities** (coverage counts, what we fix, process steps) — never a headcount/years claim.
- **No email and no phone** on public client creatives. DM-only CTA.
- A number the user flags as a claim ("don't say 13") gets **diplomatic phrasing** ("a decade+ of delivery"),
  not a gap in the copy.
- India peak window: **08:30 IST = 03:00 UTC**. Verify the runner's timezone with `date -u` before arming the
  cron, then arm it as a one-shot and tell the user how to cancel.

### Brand separation (hard rule)

`Az. Consultants` (tender & bid advisory) is a **separate brand** from HMW and every other client company.
No name, workspace, parent page, or research context from one brand may appear in another brand's
deliverable — check the **Notion parent page** you build under, not just the copy. If a build lands under the
wrong brand's parent, fix it before delivery (Notion `parent` is immutable → recreate, or the user drags it).

## Pitfalls

- LinkedIn kills links in posts — put the URL in comments or profile, not the post. **But when the
  user explicitly asks for links in the post, do not silently drop them**: ship TWO labelled variants
  — (A) link in the body, exactly as asked; (B) reach-friendly, body says "link in the first comment"
  and the real URLs (2 max: site + profile) go in the first comment. Give the trade-off in one line
  and let the user choose. Deliver both, offer to post, never post unasked.
- Public-post hygiene for advisory/lead-gen copy: **no phone number** (DM only), no emoji, **5-8
  relevant hashtags** (Aamir: "always remember to add relevant hashtags"), **and name the organisations
  involved by their full names** (Aamir: "company names also add") — e.g. "INCOIS (Indian National
  Centre for Ocean Information Services) HVAC CAMC on GeM (Government e-Marketplace)". He reads spelled-out
  org names as genuine provenance, not clutter. No "we are the best" claims. Genuine reads as: one real tender, real rupee figures that are
  NOT in the tender document, one honest limit, and a soft CTA ("DM me the tender, 15-minute screen
  share, I'll tell you straight whether it is winnable"). Never leak the client's own floor price /
  rate build-up in a public post — headline exposure and profit figures only.
- Ready-to-fill shape (tender / bid-advisory post, VERIFIED 2026-09-12): `templates/tender-advisory-post.md`.
- **"Make it concise" means MEASURE words, not feel.** Punchy target for a text post: **≤130 words
  (≤ ~800 chars)**. Cautionary case (2026-09-12): the trim pass went 131 → 154 words because full
  organisation names were added, then two more rewrites only reached 129 → 124. When names/hashtags go
  in, trade words away (drop the optional 4th bullet, tighten each line) — never raise the cap. Have the
  posting script print `chars | words` for the commentary and read that number before publishing.
- **"Link in the comment" request = body link + a paste-ready comment file.** The comment API is 403
  (see `linkedin-api-posting`), so: publish with the main URL in the body, AND save a 2-link comment
  block next to the post (`~/az_consultants/linkedin-first-comment.txt`: asset/site + profile), then say
  in the handoff which link is already live and that the comment is a 10-second paste in the app. Never
  imply you posted the comment.
- **A single-pass OCR read of a rendered card is not verification.** Whole-card `--psm 6` reported a 96px
  line as `e` and missed a dark-on-accent `SWIPE` pill that were both really there; `favourite` scores 0.0 in
  VADER's US-only lexicon while `favorite` scores 0.459, so a warmth dimension tuned with British spellings
  silently does nothing. Multi-PSM (4/6/11) + crop-OCR for reversed text + `document.title` measurement JS:
  `references/replication-qa-sentiment-and-cards.md`.
- Posting >3x/week without real substance hurts reach — quality over frequency.
- DMs are for warm signals — cold DM blasting gets the account flagged.
- Carousel slide 1 is 80% of the swipe — make the hook slide stand alone.
- Never publish client names/case numbers without permission.
- **Security / QA findings about a named app: never a public post.** Not the client name, app name,
  package id, counts, screenshots or report. The postable version is anonymized category-level copy
  (what class of thing was exposed, the afternoon-sized fix, the ownership line) — skeleton and pre-send
  checklist in `app-safety-evaluation` → `references/findings-disclosure-and-public-framing.md`. Offer it;
  never post it unasked. Same for a recommendation on the client's profile: the client gives the
  testimonial, the auditor does not write one about them while their exposure is live.
- **A contact's role cannot be read off LinkedIn.** `/in/<slug>` redirects anonymous callers to
  `/authwall` (curl, extractor, headless browser alike), and name searches return same-name noise — do not
  present a search hit as identification. Ask the user for the role before any DM/post that depends on it
  ("reference something specific from their profile" needs that specific to come from the user).

## Related

- `b2b-outreach-email` — carousel PDF build technique, bilingual fonts (Noto Sans Arabic).
- `signal-based-outreach` — signal hooks work for DMs too.
- `baoyu-infographic` — alternative visual style for LinkedIn graphics (infographic layouts).
