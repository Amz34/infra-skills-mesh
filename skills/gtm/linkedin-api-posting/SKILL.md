---
name: linkedin-api-posting
description: Use when posting media to LinkedIn via REST API.
version: 1.0.0
metadata:
  hermes:
    tags: [linkedin, api, posting, carousel, document, video]
    related_skills: [linkedin-content-engine, linkedin-video-content-engine]
---

# LinkedIn API Posting

Mechanical layer for posting media to LinkedIn via REST API. The *content* skill
(`linkedin-content-engine`) owns voice/copy rules; THIS skill owns the HTTP flows.
All flows below are VERIFIED against Aamir's account.

## When to Use

- Posting an image, video, or PDF document carousel to LinkedIn programmatically.
- Building a new posting script or debugging a failed post (401/403/422/500).

## Prerequisites (Aamir's setup)

- Token: `~/linkedin_token.json` — `{"access_token", "expires_in": 5184000 (60d), "scope": w_member_social}`. Refresh via re-auth before expiry.
- PERSON_URN: `urn:li:person:ZXkhXV9MAp`.
- **`LinkedIn-Version: 202607`** is verified active (202408/202506/202512 dead; 202510 & 202601–202608 active). Always send `X-Restli-Protocol-Version: 2.0.0`.
- Verify every post live: `web_extract` the post URL (renders for logged-out viewers).

## Shared Headers

```
Authorization: Bearer <token>
LinkedIn-Version: 202607
X-Restli-Protocol-Version: 2.0.0
Content-Type: application/json   (PUT uploads: application/pdf / application/octet-stream)
```

## Document / PDF Carousel Flow (VERIFIED 2026-08-26)

Carousels post best as a **PDF document** (renders as swipeable carousel, out-performs image posts).

1. **Initialize**: `POST https://api.linkedin.com/rest/documents?action=initializeUpload`
   Body: `{"initializeUploadRequest": {"owner": PERSON_URN}}` — **ONLY `owner`. PITFALL: `mediaCategory` or `serviceRelationship` in this body → HTTP 500** (category is implicit DOCUMENT on this endpoint).
2. **URN location**: the document URN is in the **response BODY `value.document`**, NOT the `x-restli-id` header (differs from image/video registerUpload). `doc_urn = json.loads(body)["value"]["document"]`. Upload URL is `value.uploadUrl`; `value.uploadHeaders` may be empty.
3. **Upload**: `PUT` the PDF bytes to `uploadUrl` with `Content-Type: application/pdf` → 201.
4. **Publish**: `POST https://api.linkedin.com/rest/posts`
   ```json
   {"author": PERSON_URN, "lifecycleState": "PUBLISHED", "visibility": "PUBLIC",
    "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
    "content": {"media": {"id": "urn:li:document:...", "title": "..."}},
    "commentary": "..."}
   ```
   **NO `mediaCategory` field** (same as video flow). Response id = `urn:li:ugcPost:xxx`.
5. **URL**: `https://www.linkedin.com/feed/update/urn:li:ugcPost:xxx` → web_extract to verify.

Working scripts: `~/.hermes/scripts/post_linkedin_carousel_sanad.py` (carousel PDF) and `post_linkedin_az_ebook.py` (single free-preview PDF + value-first commentary + URL, verified 2026-09-03, post urn:li:ugcPost:7501209682565414912) — edit caption/media path per job. Both use /rest/documents → PUT → /rest/posts.

## Video Flow (CORRECTED + VERIFIED 2026-09-13)

1. `POST /v2/videos?action=initializeUpload` — NO `uploadTitle` field (422
   otherwise). Body `{"initializeUploadRequest":{"owner":PERSON_URN,"fileSizeBytes":<bytes>}}`.
   Response `value` keys: `uploadInstructions` (firstByte/lastByte/uploadUrl per part),
   `uploadUrlsExpireAt`, `video`, **`uploadToken` = EMPTY STRING `""`**.
2. Chunked upload: `POST` each part to its `uploadUrl` with
   `Content-Type: application/octet-stream` + `Content-Range: bytes a-b/size` → 200 +
   an **`ETag`** response header per part. Collect every ETag.
3. **`POST /v2/videos?action=finalizeUpload` — MANDATORY, this is the step that was
   silently missing.** Body
   `{"finalizeUploadRequest":{"video":<video urn>,"uploadToken":"","uploadedPartIds":[<ETag per part>]}}`
   → 200. **PITFALL (root cause of a dead-video post): `uploadToken` is `""`, so
   `if val.get("uploadToken"):` is FALSKY and the finalize call gets skipped — the asset
   then sits at `WAITING_UPLOAD` FOREVER and `/rest/posts` still returns 201, publishing a
   post whose video never plays.** Call finalize unconditionally (empty token is fine).
4. Poll `GET /rest/videos/<urlencoded video urn>` until `status == "AVAILABLE"`
   (WAITING_UPLOAD → PROCESSING → AVAILABLE, usually 15–30s). Do NOT publish before
   AVAILABLE.
5. `POST /rest/posts` — `content.media.id = video_urn`, **NO `mediaCategory`** (ugcPosts video + mediaCategory → INVALID_CONTENT_OWNERSHIP). `content.media.title` is accepted.
6. **Capture the returned URN**: `/rest/posts` 201 has an EMPTY body — the id is in the
   **`x-restli-id` response header** (`urn:li:ugcPost:<id>`). Without it you can never
   build the post URL, edit it (`$set`) or delete it.
7. Verify live: browser-UA `curl https://www.linkedin.com/feed/update/<urn>/` → 200 and
   `<meta property="og:title">` shows the media title + author headline. (Video posts
   return `og:type=article`, no `og:video` — the 200 + og:title is the proof.)
8. **Scripts**: `~/.hermes/scripts/post_linkedin_aistack_reel.py` = corrected full flow
   (init → chunk upload → finalize → wait AVAILABLE → publish → print POST_URL).
   ⚠️ Older `post_linkedin_ai_pm_video.py` / `post_linkedin_rest_posts.py` skip
   finalizeUpload → they publish posts with a dead video; port the finalize+wait steps in
   before reusing them.

**Reusing an already-AVAILABLE asset**: the asset can be attached to a later post by its
URN, no re-upload needed (each init creates a NEW asset; nothing is deduped by file hash).

**You CANNOT list your own posts — so an uncaptured URN is unrecoverable (verified 2026-09-13).**
`GET /rest/posts?q=author&author=<person urn>` → **403** and
`GET /v2/ugcPosts?q=authors&authors=List(<person urn>)` → **403** with a
`w_member_social`-only token (author listing is a partner permission). Combined with the
empty 201 body, that means: **if the `x-restli-id` was not captured at publish time, the
post can never be addressed again** — no listing, no search endpoint, no way to derive the
id (the low bits of `urn:li:ugcPost:<id>` are machine+sequence, not derivable). Cold-outreach
"your post is broken" triage then has exactly two outs: the user deletes it in-app
(Activity → post → `...` → Delete), or they paste the post URL and you
`DELETE /rest/posts/<urlencoded urn>` (DELETE works with `w_member_social`).
Sanity-check an URN's age without the API: LinkedIn snowflakes pack epoch-ms in the high
bits — `urn_id >> 22` ≈ creation time in ms (7504808106917376001 → 2026-09-13 ✓).

**Recovery when a dead-video post is ALREADY live**: re-run the full corrected flow
(init → chunk upload → finalize → wait AVAILABLE → publish) to get a working post, then ask
the user to delete the broken one (its video never plays, so deleting is the right call, and
its URN is unrecoverable — see above). Never silently publish twice and leave both: say
plainly "purana post delete karna hai (video play nahi karega), naya link yeh hai".
A partially-uploaded asset CANNOT be finalized later — `uploadedPartIds` are the per-part
ETags returned by that asset's own upload calls, so they are lost with the response; re-init
instead of hunting for them.

## Image Flow (v2 — VERIFIED)

`POST /v2/assets?action=registerUpload` (recipes `urn:li:digitalmediaRecipe:feedshare-image`) → PUT bytes → `POST /v2/ugcPosts` shareMediaCategory IMAGE. **PITFALL: omit the `description` field entirely** — plain string → 422 "record type is not backed by a DataMap".
**Animated GIFs VERIFIED (2026-08-27)**: same flow works for GIF — registerUpload feedshare-image recipe + `Content-Type: image/gif` on the PUT + ugcPosts IMAGE category. No extra fields. (agent-memory-3-layers post urn:li:share:7498704881839575040.)

### Modern single-image flow — /rest/images (VERIFIED 2026-09-12)

Same shape as /rest/documents; prefer it for new scripts (internship-calendar post urn:li:share:7504495029474934784).

1. `POST https://api.linkedin.com/rest/images?action=initializeUpload`, body
   `{"initializeUploadRequest": {"owner": PERSON_URN}}` → the image URN is in the response **BODY**
   `value.image` (`urn:li:image:D4D1...`), upload URL in `value.uploadUrl` (the `x-restli-id` header
   also carries it here — still read the body, the document flow has the opposite convention).
   A 200 here is also the cheap pre-flight that token + w_member_social + upload path are alive.
2. `PUT` the PNG bytes to uploadUrl, `Content-Type: image/png` → 201.
3. `POST /rest/posts` — `content.media.id = urn:li:image:...` (**NO `mediaCategory`**),
   `content.media.altText` for accessibility, full `commentary`. Response id is
   `urn:li:share:<id>` for image/text posts (ugcPost URNs come from the /v2 flows).
4. Working script: `~/.hermes/scripts/post_linkedin_internship_calendar.py` (edit caption + media path).

**Confirm the image really attached** (API read-back is impossible): fetch the public post page
(browser UA curl, or `browser_exec` guest view) and match the image URN prefix inside the rendered
asset URL — `media.licdn.com/dms/image/v2/<URN-prefix>/...`, e.g. `D4D10AQEPd0UbTzgMVQ` from
`urn:li:image:D4D10AQEPd0UbTzgMVQ`. That asset URL + the `og:image`/article-cover meta tag = attached.

**commentary is capped at 3000 chars** — `len(commentary)` before the POST and trim the copy by
tightening sentences (never by dropping URLs the user asked for).

## Comments — API IMPOSSIBLE with community token

`POST /rest/socialActions/{urn}/comments` → **403 ACCESS_DENIED** (`partnerApiSocialActions.CREATE` is Partner-Program permission, not in w_member_social).
**Workarounds**: embed the destination URL directly on the carousel contact slide (e.g. "LIVE LISTING: expatriates.com/cls/64081253"), or paste the comment manually from the app. Never promise an API-comment feature to the user.

## Newsletter Editions — API IMPOSSIBLE (verified 2026-08-26)

LinkedIn newsletter editions can ONLY be published from the web/app UI ("Write article" → pick newsletter → publish). There is NO public API path:
- Posts API schema has no `newsletterUrn` field; the `container` field is for Groups, not newsletters.
- `learn.microsoft.com/.../community-management/newsletters/...` → 404 — no newsletters API page exists.
- SO (2023) + 2026 sources confirm: newsletter edition publishing is not exposed to any API, even with w_member_social.

**Before promising a newsletter post, CHECK whether the article is ALREADY an edition** (common — most pulse articles are published into a newsletter from the start):
- `curl` the article URL → grep for `main-publisher-card` + a `/newsletters/<slug>` link + `+ Subscribe` CTA → it's an edition.
- `curl` the newsletter page (`linkedin.com/newsletters/<slug>-<numeric-id>`) → grep for the article's pulse URL in the editions list.

Aamir's newsletter: **"Elevate FM - Az. Consultants"** → URN `urn:li:newsletter:7358055728915320833` (slug `elevate-fm-az-consultants-7358055728915320833`). His pulse articles (TIME TO ELEVATE FM, Precision Under Pressure, FM Digital Modernization Starter Kit, CFM Credentials, …) are all editions of it.

**What the API CAN do instead**: regular feed post with `content.article` = {source, thumbnail, title, description} → an article-card feed post, NOT a newsletter edition. If the user wants a true newsletter edition, prep the full article draft and hand them a paste-and-publish draft for the UI.

## Token health check — NOT /rest/me (verified 2026-08-27)

`GET https://api.linkedin.com/rest/me` → **403 `partnerApiMe.GET.20260701`
("Not enough permissions") is NORMAL** with a w_member_social-only token
(profile-read scope absent). It says NOTHING about the token being dead —
do not diagnose expiry from it.

**Correct harmless pre-post check**: `POST /rest/documents?action=initializeUpload`
(body: `{"initializeUploadRequest": {"owner": PERSON_URN}}`). 200 = token +
w_member_social + the whole upload path work; it reserves an upload slot but
creates NO post. Use this as the dry-run before a scheduled/cron post.

**Cheap alive/identity check**: `GET https://api.linkedin.com/v2/userinfo` → **200**
`{"sub":"ZXkhXV9MAp","name":"…","email":"…"}` — the token's `openid profile email` scopes make it the
one GET that works (it returns the member id too). Good first probe before concluding a token is dead.

## Post analytics — API IMPOSSIBLE (metrics come from the UI)

Verified 2026-09-16 with the `w_member_social` token — every analytics read is refused, so reach /
engagement numbers CANNOT be automated off this token:

| Endpoint | Result |
|---|---|
| `GET /rest/posts?q=author&author=…` | 403 `partnerApiPostsExternal.FINDER-author` |
| `GET /rest/socialActions/{urn}` | 403 `partnerApiSocialActions.GET` |
| `GET /rest/memberCreatorPostAnalytics?q=author…` | 404 `RESOURCE_NOT_FOUND` (no such virtual resource) |
| `GET /v2/organizationalEntityShareStatistics?q=organizationalEntity…` | 403 (org scopes absent) |

Per-post numbers (impressions, members reached, profile viewers) come from the post's analytics in the
**UI** → paste into the local ledger:
`python3 ~/ops/linkedin/reach/li_reach.py ingest <urn> --impressions … --reactions … --comments … --reposts …`.
Do NOT re-probe each session hoping for a change — only a new (approved analytics / Member-Data-Portability)
scope unlocks it. Reach-loop design + full evidence: `linkedin-content-engine` →
`references/reach-loop-and-algorithm-facts.md`.

## Scheduled posting (cron one-shot)

- `cronjob` `no_agent=true` job whose `script` is a `.sh` wrapper that runs
  the posting python and prints its stdout (post URL + id) — the output is
  delivered verbatim to the origin chat, giving you the URL to verify.
- `script` must be a **relative path under `~/.hermes/scripts/`** (absolute
  paths are rejected at cron creation).
- Schedule in UTC (`date -u`); e.g. 4pm KSA = 13:00 UTC.

## Editing / comments (verified 2026-09-11)

- **Edit your own post** (add a link at the end, fix a typo):
  `POST /rest/posts/<urlencoded urn:li:ugcPost:...>` body
  `{"patch": {"$set": {"commentary": "<FULL text>"}}}` → 204.
  **`$set` replaces the ENTIRE commentary** — send the complete text or you destroy
  the post (a one-line fragment wipes the body; recover by immediately re-patching
  with the full text). Read-back is impossible (`w_member_social` is write-only);
  verify with browser_exec on the public post URL.
- **First comment via API = 403** (`partnerApiSocialActions.CREATE`) with the
  community token — both `/rest/socialActions/<urn>/comments` (URL-encoded URN) and
  `/v2/socialActions/<urn>/comments` (400 syntax exception). So the "link in the
  first comment" trick must be done by hand in the app; ship the URL inside the
  post body instead and accept the small reach hit.
- **Replace a published post (trim / full rewrite) — DELETE + repost, VERIFIED 2026-09-12:**
  `DELETE https://api.linkedin.com/rest/posts/<urlencoded URN>` → **204**, then publish the corrected
  copy normally. Cleaner than `$set` when the whole body changes (a "make it punchier" rewrite), and
  the only path if the user wants the live text to be exactly what you measured. Cost: the post gets a
  NEW `urn:li:share:...` and the OLD public link dies — say it in the handoff ("purana link dead hai,
  naya link use karein"). Safe within the first minutes (near-zero engagement); do NOT churn a post
  that already has comments/likes — use `$set` there instead.
  Working script: `~/.hermes/scripts/linkedin_replace_post.py <old_urn> [text_file]` — deletes,
  republishes from a plain `.txt`, prints `new commentary chars | words` + the new URL (that print is
  how you prove the trim actually landed).
- **"Post nahi hua?" triage (verified 2026-09-12) — live vs gone in one curl.** Public, browser-UA
  `curl -o /tmp/pg.html -w '%{http_code}' https://www.linkedin.com/feed/update/<urn:li:share:...>`:
  **200** = live (and `<title>` + the `D4D1...` image-asset prefix prove it), **307 redirect** = the post
  no longer exists. Check ALL the URNs you know about — during a churn session stale links that the
  user still has open return 307 while the newest one is 200, which is what "post dikh nahi raha"
  usually means. A `DELETE` that returns **404 on a post you created minutes ago** means it is already
  gone (not a permissions bug: DELETE works with `w_member_social`; `GET /rest/posts/<urn>` → 403 for
  every URN, live or dead, so never diagnose from GET). Rapid delete+repost churn (2–3 rewrites in
  minutes) is a plausible cause — publish ONCE when the copy is frozen, verify with the 200, and tell
  the user the old links are dead instead of reposting again.
- **A guest-view cut can land mid-line and look like a broken publish.** A logged-out fetch of a fresh
  post showed the commentary stopping right after the second short paragraph (…"INCOIS") with the rest
  behind "Sign in to view more content" — the post was complete and live; the guest view only truncates
  (and may cut mid-sentence). Never delete/repost out of panic on a guest-view cut; authoritative proof
  = the create response id, and after a replace = the new URN live + the old URL gone.

## Pitfalls (accumulated)

- LinkedIn de-prioritises link-card posts (reach), so the URL usually goes on a
  slide / in a comment / in the profile — but **a plain raw URL at the end of a
  DOCUMENT (carousel) post's commentary does survive** (verified 2026-09-11,
  ZeroEgress launch: `github.com/Amz34/zeroegress` written into the body via
  `$set`, post live and 200). Don't strip the link reflexively; put it in the
  body when the API can't comment.
- **Guest/public fetch TRUNCATES the commentary (~340 chars).** A logged-out
  `curl`/`web_extract` of the post URL showing only the first paragraph, or not
  containing your URL, is NOT evidence the link/edit is missing — the guest view
  ends in "…". Confirm the edit from the POST response (204) plus your own
  written text, and treat the browser fetch as layout confirmation only.
- **POST read-back is IMPOSSIBLE with w_member_social (verified 2026-09-03):** `GET /rest/posts/urn:li:ugcPost:xxx` → 400, `GET /rest/posts/urn:li:share:xxx` → 403, `GET /v2/ugcPosts/<id>` → 403 Forbidden — token is write-only, no read scope. Do NOT diagnose a post's success from API read-backs. The POST response's `urn:li:ugcPost:xxx` id IS the authoritative creation confirmation (same mechanism as every verified post). Public check = `web_extract` the `linkedin.com/feed/update/<urn>` URL (renders for logged-out viewers) or ask the user — an authwall 200/redirect is inconclusive.
- 401 = token expired (60d lifetime) — re-auth, don't retry blindly.
- 422 with "DataMap"/"not backed" = you sent a field the schema doesn't take → strip it.
- Document URN body-vs-header confusion is the #1 cause of a failed /rest/posts after a successful upload (empty media id → HTTP 500).
- 500 after upload usually means the media URN was never captured — check step 2 before retrying the post.
- No-phone rule: public LinkedIn carousel variant strips the WhatsApp row from the contact slide (keep email + link); ads/classifieds copy may keep the phone — keep two HTML variants.
- **share vs activity URN duality**: one post has two numeric IDs — API reports `urn:li:share:XXXX` (`/feed/update/...`) while the app's share link is `/posts/<author>_<slug>-activity-YYYY-pNOY`. Both HTTP 200 with identical title → same post. Dedupe via og:url/canonical before listing "all posts" (verified 2026-09-04).
- Listing a client's posted links: use `POSTS_LOG.md` next to the scripts + cron no_agent outputs (`~/.hermes/cron/output/<jobid>/*.md`, `POSTED:` line) as source of truth; live-verify each URL with a browser-UA curl (LinkedIn non-200s default UAs); harvest URNs via `grep -ohrE "urn:li:(share|activity|ugcPost):[0-9]+"`. Full workflow: `references/post-inventory-from-logs.md`.
