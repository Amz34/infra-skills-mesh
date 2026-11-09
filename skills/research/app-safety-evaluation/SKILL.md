---
name: app-safety-evaluation
description: Use when judging if an app is safe or replicable.
version: 1.1.0
author: hermes
license: MIT
metadata:
  hermes:
    tags: [research, app-store, safety, play-store, firebase, backend-security]
    related_skills: [website-stack-fingerprinting, tech-adoption-analysis]
---

# App Safety Evaluation + Build Capability Mapping

## When to Use

The user asks "is this app safe to use?" or "what does it take to build an app like this?" — typically from a Google Play / Chrome Web Store listing they spotted (e.g. Muslim AI Browser "Blur Haram", HaramBlur, PordaAI). Produces two deliverables: (1) honest safety verdict with caveats, (2) development capability breakdown with free-stack costs.

Three modes, same skill:
- **(a) Consumer safety** — is this app safe for the user to install? (sources below)
- **(b) Buildability** — what tech stack + cost would produce it?
- **(c) Owner QA + replica costing** — the app belongs to the user's own group/client (or a competitor they want to match) and they want an expert QA verdict *plus* a real time/money model for an exact production-grade replica. Often phrased as "**no action only advice**": deep **read-only** probing of the live backend and store listing is expected and in scope; any *write* to the target is never in scope. Deliverables: QA findings ranked by blast radius, replica blueprint, infra-capability score vs the one missing capability lane, dev-day table, price lanes, monthly run cost.

## Safety Analysis (sources in priority order)

1. **Play Store listing** — `play.google.com/store/apps/details?id=<pkg>`: developer name, rating, review count, download count, "About this app", **Data Safety section** (the legally-bound declaration: "No data collected", "No data shared with third parties", "Data encrypted in transit", "Data can't be deleted"). This section is the single most reliable quick signal.
2. **Privacy policy page** — always linked in the listing. The REAL signal: read what data is collected, whether AI runs on-device or server-side, analytics disclosure. e.g. Muslim Browser: "ZERO browsing data, AI 100% on-device, minimal pseudonymous crash analytics" = green.
3. **Reviews mining** — `document.body.innerText` regex for review bodies. Recurring complaints (e.g. "AI detection flickers/fails on many images") = quality issues, NOT security issues — separate them explicitly in the verdict.
4. **Developer footprint** — `play.google.com/store/apps/developer?id=<dev>` lists their other apps. Small/unknown dev with unrelated apps (trucking, games) = amateur-but-not-sketchy signal; note it, don't condemn.
5. **Competitor/ecosystem scan** — search `"<app name>" Google Play` to surface the category leader (e.g. HaramBlur 500K+ downloads vs newcomer 10K+). Verdict should name which is more mature.

## Backend Security Audit (when the listing looks clean)

Data Safety declarations are developer-typed and **frequently false**. Small shops shipping on Firebase/BaaS very often ship with open rules — "No data collected" on the listing alongside `allow read: if true` in Firestore is a common, real combination. The listing is a claim; the backend is evidence. Probe it before writing any verdict.

Both endpoints below answer for *anonymous* callers exactly when the rules are wrong. Read-only, GET/list only:

```bash
P=<firebase-project-id>; B=<bucket>.firebasestorage.app
# Firestore: HTTP 200 + a non-zero "name": count ⇒ anonymous enum is ON
for c in users trees posts activity leaderboards notifications; do
  curl -s -m 20 -o /tmp/f_$c.json -w "$c=%{http_code}:" \
    "https://firestore.googleapis.com/v1/projects/$P/databases/(default)/documents/$c?pageSize=300"
  grep -o '"name":' /tmp/f_$c.json | wc -l
done
# Storage: list objects, then fetch one with no credentials
curl -s -m 25 -o /tmp/objs.json "https://firebasestorage.googleapis.com/v0/b/$B/o?maxResults=1000&fields=items(name,size,contentType)"
curl -s -m 25 -o /dev/null -w "unauth=%{http_code} bytes=%{size_download}\n" \
  "https://firebasestorage.googleapis.com/v0/b/$B/o/<url-encoded-path>?alt=media"
```

Reading the result:
- `403 PERMISSION_DENIED` → rules are doing their job (good; say so).
- `200` on a collection → anonymous enumeration of every doc's fields — uid, exact lat/lng, notes, image URLs.
- `200` + real payload bytes on `?alt=media` → anyone can download user photos **and** burn the owner's egress budget.

Also read-only and usually revealing: storage prefixes (`o?prefix=photos/`, `profileImages/`, `care/`, `docs/`) to infer feature surface and media volume; saved doc JSON (`/tmp/f_users.json`) to reconstruct the data model and spot arrays-in-doc; and any policy PDFs parked in the same public bucket (multiple stale versions, no changelog, no versioning story).

**Check the SECOND database. A Firebase project has two stores and the forgotten one usually holds the worse data.** One call reveals the whole data model as node names:

```bash
PID=<firebase-project-id>
curl -s -m 20 "https://$PID-default-rtdb.firebaseio.com/.json?shallow=true"   # top-level node names
for n in users activities trees global appConfig ads; do
  curl -s -m 20 -o /tmp/rtdb_$n.json -w "$n=%{http_code}:" \
    "https://$PID-default-rtdb.firebaseio.com/$n.json"; done
```

`200` + data = anonymously readable. Sept-2026 worked example: Firestore `users` held 24 records and **no email**, while RTDB `/users` held 71 records with **70 valid email addresses**, names, photo URLs, bio and sign-in provider, plus a 249-record activity feed and public `/global/stats` counters. A fix that closes only Firestore leaves every email open. **Never deliver a Firebase audit without the RTDB probe** — the Firestore-only version reads as "another app with open rules" (the most common misconfiguration on earth, so the client shrugs), while the RTDB finding is the one no stock scanner produced.

Also check `/appConfig` (forceUpdate, minSupportedVersion, storeUrl) and `/ads` (ad image + link) if present: these live in the same store, read is provably open, and they are the highest-value *write* target. Report read as proven, write as **untested** — "if write is also open, an anonymous visitor retargets the forced-update storeUrl or the ad link for the whole install base". Never test it.

**The file access control is a secret the server hands out.** Read response *headers*, not just status codes:

```bash
curl -sI -m 20 "https://firebasestorage.googleapis.com/v0/b/$B/o/<url-encoded-path>?alt=media" \
  | grep -i firebasestoragedownloadtokens
```

`x-goog-meta-firebasestoragedownloadtokens` in the header is the file's permanent private link, returned to an unauthenticated caller — 24/24 sampled objects in the worked example, i.e. systematic. Check the Play-required privacy policy PDF too: when it sits in the same bucket behind a token URL, the compliance artifact itself depends on the leak.

Nuances worth stating rather than hiding: `documents:listCollectionIds` answers `403` to anonymous callers even when single collections answer `200`, so collection names must be **guessed** and you cannot claim a collection count; `200 + 0 docs` on `posts`/`activity`/`leaderboards`/`notifications` proves the read rule is open at collection level *and* that the social layer is computed client-side. If a store is later found open after being documented as closed, the probe is the retraction evidence — re-run it rather than reasoning from the old note.

**Is the feature real or a demo? (value-distribution forensics).** Histogram every categorical field in the exposed records. Uniform values mean the feature is stubbed: in the worked example `species` had only `Plant` (122) and the Arabic word for plant (41), `healthStatus` = `excellent` x163, `status` = `healthy` x163, `waterLevel` = `100` x163, `careHistory`/`careLog` empty x163, `waterHistory` exactly one entry x163, `careTips` three identical canned strings. Verdict: the care/health/AI half looks alive on screen and stores only defaults — the single most valuable product finding in the report, and invisible to any security scanner.

Then in the verdict: rank by **blast radius**, not bug name (public GPS of N trees, N user UIDs, N downloadable photos); give the fix as rules *as advice* (default-deny `match /{document=**} { allow read, write: if false; }`, per-collection public read only for aggregate/leaderboard views, rounded geo, `request.auth != null` + owner check on storage, App Check on callables); and flag the false Data Safety declaration as a **store-policy** risk of its own (Play suspension, not just a privacy nit).

**Never write to the target's backend.** These are GET/list probes; a QA pass that mutates someone's live data is a breach, not a test. State explicitly in the reply that you read and changed nothing.

Recipe, worked example (collection counts, field shapes, project IDs) and remediation snippets: `references/firebase-public-backend-audit.md`. Key-free re-runnable probe: `scripts/firebase_public_read_probe.sh`.

## Capability Mapping (what it takes to build it)

Map detected features to free-stack technologies, as a table:
- App shell: Kotlin + Android WebView (browser apps); Chrome extension: JS + TensorFlow.js
- On-device AI: TensorFlow Lite / MediaPipe (image classification, frame-by-frame video)
- Detection model: open-source NSFW models (NudeNet, OpenNSFW) fine-tuned on custom data
- Supporting features: ad blocker (EasyList network interceptor), social feed filters (DOM injection)
- Costs: Android Studio/TFLite/datasets $0; Play Store $25 one-time; training on free GPU (Colab/Kaggle); the real cost is dataset curation + latency tuning (30–60ms blur target)
- Fit note for THIS user: relate to their existing skill set (React/WebView known; ML is the new part) and name the cheapest entry point (e.g. "Chrome extension first, 2-3 weeks to demo").

## Replica Build Model ("what does it take to build exactly this?")

Answer in **four numbers**: dev-days, calendar weeks, one-time cash, monthly run cost. Then the capability-gap verdict. Detail and the worked benchmark: `references/app-replica-costing.md`.

1. **Dev-days by workstream** (two columns: *parity* = same screens/features, *hardened* = production-grade). Typical rows: spec/schema/security rules, backend (DB + functions + push + aggregation), app client (auth, tabs, wizard, camera, map, offline sync), AI pipeline, admin/moderation panel, i18n/AR-RTL + copy, QA (device matrix, rules tests, load, RTL), store compliance + assets. A 4-tab Flutter-style community app (auth + map + 3-step wizard + AI scan + offline + EN/AR) benchmarked at **~73 parity / ~121 hardened dev-days**.
2. **Calendar** — 2 devs ≈ 5-7 weeks parity; 3 devs ≈ 10-14 weeks hardened. Then add the **store window separately** (see pitfalls) — it does not compress with more devs.
3. **Price lanes** — offshore senior (~$15-25/h), Gulf/EU agency (~$40-80/h), or the AI-assisted lane (1 contractor for the mobile build + our agents/CI for backend, admin, AI, docs, content). Always list fixed extras separately: Play $25 one-time, Apple $99/yr, branding, AR/EN copy, security + PDPL review, ASO assets.
4. **Monthly run cost** — pilot ≤1k users ≈ $0-5 (free tiers; Blaze needed for functions/triggers/FCM v1); 10k MAU ≈ $150-450; 100k MAU ≈ $1.5-4k. Force client-side photo compression (~250 KB) or storage + egress dominates.

**The map SDK is the cost trap — decide it before any code.** Google Maps SDK billing per map load means ~10k MAU × 20 loads ≈ **+$1,200/mo**, and ~100k MAU ≈ **+$21k/mo**; self-hosted MapLibre + pmtiles is ~$0-50/mo at the same scale. This single architectural choice outweighs every other line in the run-cost table, so name it explicitly and recommend MapLibre unless a contract mandates Google.

**Infra-capability gap answer.** Score it honestly as a percentage, then name the *one* missing lane. Backend, admin dashboards, AI services, notifications, storage/CDN, analytics, messaging surfaces, CI/CD, monitoring and Arabic content are usually already available; the native **build + store-submit** lane is usually the only gap. Cheapest fix: cloud CI (GitHub Actions ubuntu runner with Flutter + JDK + Android SDK, Firebase App Distribution for tester builds, fastlane for store upload) with the VM kept as control plane — a small-RAM VM is the wrong place for Gradle. Device QA on a cloud device farm / Firebase Test Lab rather than a local emulator.

**The hard truth to deliver:** a 1:1 replica *copies the original's defects* (open rules, arrays-in-doc, client-derived social layer). Recommend replicate-the-features / fix-the-architecture, and name which original choices must NOT be copied.

## Pitfalls

- **AppBrain / apkcombo / apkpure permission pages often render empty or block scraping** — fall back to the Play Store listing itself; expand its "Permissions"/"This app can..." section (needs a JS click; the expander text search `Permissions` + short textContent may fail — try scrolling and re-reading innerText).
- **GitHub search results don't render via JS scraping** — don't rely on `github.com/search` for repo discovery; use site-specific pages or direct known URLs.
- **Play Store "Data safety" claims are developer-declared** — trust + verify against the privacy policy; note "verified reviews" badge existence.
- **Download count ≠ safety** — the 500K-download app can have IAPs, the 10K one can be cleaner. Judge on data declarations + policy, not popularity.
- **Play listing HTML is server-rendered** — `curl -sL -A "<desktop UA>" "https://play.google.com/store/apps/details?id=<pkg>"` then strip tags gives description, Data Safety strings, developer name, "Updated <date>" and download count with no browser lane at all. Do this *first*; it's faster and more reliable than DOM-scraping the listing, and it never returns a 500-char shell page.
- **A clean listing is not a clean backend** — "No data collected / No data shared with third parties" coexists with anonymous Firestore read in the wild. Probe before you repeat the claim as fact.
- **Never audit Firestore only.** The Realtime Database (`https://<pid>-default-rtdb.firebaseio.com/.json?shallow=true`) is the store everyone forgets and it often holds *more* than Firestore — 70 email addresses vs 24 email-less Firestore user records in one real case. Skipping it produces a report that misses the actual user table.
- **Don't infer a PII class from a loose regex.** A digit-run pattern "found" 652 phone hits in one dataset; they were millisecond timestamps and document ids. Claim an exposed class only when the **field name** and the value shape agree, and phrase it as "70 of 71 records carry an email field with a valid address shape".
- **Stored image URLs carry `?alt=media&token=...`** — so revoking or rotating download tokens breaks every image already written into every record. Sequence it as one release: stable URL model → rewrite all stored URLs server-side → verify → then revoke. This is precisely why naive security fixes get rolled back, so put the order in the fix list, not just in a warning.
- **`x-goog-meta-firebasestoragedownloadtokens` in a media response header** = the file's private link given to an unauthenticated caller. Check headers, not only status codes; a `200` list plus a token header is a worse finding than either alone.
- **Uniform field values mean a stubbed feature** — one species name, one health status, always-full water level, empty histories and identical canned tips across every record. Report it as a product-quality finding; no security scanner will surface it and it is usually the most useful thing in the document.
- **Remote app config and ad links sitting in a public store** (forceUpdate / minSupportedVersion / storeUrl / ad link) are a hijack surface, not a data leak: read exposure is provable, write exposure is not. Say exactly that instead of implying you verified writes.
- **Firestore arrays inside a doc** (`careHistory[]`, `waterHistory[]`, `careLog[]`) hit the 1 MiB doc cap, and every event rewrites the whole document (write amplification + contention). Flag as P1 and specify subcollections in any replica.
- **`200` + 0 docs on social collections** (`posts`/`activity`/`leaderboards`/`notifications`) means the "community" layer is derived client-side from other users' data — fine at hundreds of users, a privacy + read-cost disaster at scale. Say that plainly instead of calling the feature "done".
- **Gamified trees/impact with no anti-fraud** (GPS spoofing, duplicate photos) needs Play Integrity + geofence + photo hashing before any launch.
- **Store gates to budget in the plan:** a new *personal* Play account must run closed testing with **12 testers for 14 consecutive days** before production; organization accounts need D-U-N-S verification (2-4 weeks). Add 3-5 weeks to the calendar for the store window alone.
- **Firebase region is immutable** — if KSA PDPL / data residency matters, the project must be created in `me-central2` (Dammam) from the start; it cannot be changed later. Treat it as a differentiator, not an afterthought.
- **Thin-I/O VMs**: keep every probe's stdout to **one line** (`curl -w "%{http_code}"`, counters, `-o file`), and read multi-line results back from the file. Multi-line piped/heredoc output can collapse to a single line on constrained harnesses, and long inline one-liners get rejected — split them into short commands. This output-shape discipline is what made the audit above work; without it the probes look "empty" and the audit stalls.

## Output shape (match user's style)

Verdict first ("Use karna SAFE hai ✅ with caveats"), green flags vs caveats as bullets, then capability table + costs + "tumhare liye angle" (fit to their stack) + concrete next offer (e.g. "proof-of-concept extension bana ke dikha sakta hoon").

**Owner-QA / replica mode ordering:** (1) QA verdict with findings ranked by *blast radius*, not bug name; (2) replica blueprint (screens, collections, pipelines); (3) infra-capability score — what we can already do today vs the single missing lane, with the cheapest fix; (4) dev-day table; (5) price lanes; (6) monthly run cost; (7) store/legal gates. Close with an **offer**, never a unilateral action ("poora English audit + build-spec banao?").

**When the ask is "no action only advice":** probing stays read-only (GET/list only) and the reply must say plainly that you read and changed nothing. Deliverables the user may ask for later are FILES and always in English; chat commentary stays Hinglish and concise.

**Owner-QA findings report for a developer (the "polished version" ask).** When the user says the findings are for the client's developers ("developers ko samajhne ke liye", "aur polished way"), the deliverable is a shareable document, not a chat paragraph, and each finding is one block of **What we found / Proof (copy-paste curl) / Impact / Fix**. Then, always: (1) a Method-and-limits header stating read-only, no account, no keys, nothing created; (2) a severity summary table (Critical/High/Medium) before the detail; (3) an explicit **"not tested"** section — write access above all, since unverified writes are the honest gap that makes the rest credible; (4) a numbered **fix order**, cheapest blast radius first (rules → store declaration → code release) with a one-line time estimate per stage; (5) housekeeping (duplicate/overlapping fields, dates stored as strings) as low severity cleanup; (6) a closing non-technical paragraph: how long it has been live, how short the fix is, and that the real gap is **ownership** — one automated daily check plus one named person who receives the alert. Self-verifying beats persuasive: any developer should be able to confirm every claim in about two minutes from the proof commands.

**Style for this user, verbatim asks:** "make ultra and concise and ai free", "no jargons", "polished way". Plain English, short sentences, no emoji, no em-dashes, no AI-slop phrasing, no self-congratulation. Measure before claiming: quote the median/typical file size and the sample size, not the largest outlier you happened to open, and if a later measurement contradicts an earlier claim, **correct it openly in the next revision** rather than quietly dropping it (in the worked example a "780 KB raw photo" claim became "median 78 KB, max 1.17 MB" and the overclaim was retracted in the report itself). Never print PII into the deliverable: field names, types, lengths and counts only.

**Answer the "is this generic?" question head-on.** Users ask it, and it is a fair challenge: a headline like "Firebase rules are open" is the most common misconfiguration on earth, so the detail has to carry the report. Say which findings a stock scanner could also have produced and which could not (the second database with the email table, the token header on every object, the uniform-value stubbing) and let the rest stand on the proof.

## Sharing the findings (the outbound summary, then anything public)

The report is not the last artifact of an owner-QA engagement. The user then pastes a **short message** (WhatsApp / LinkedIn, to the client or the client's leadership) and asks *"ye message sahi hai?"* — verify it claim by claim against the report and hand back a ready-to-paste block. What this pass changes, every time:

- **Every number must be the report's measured number** (70 emails / 71 names, 232 files, 163 trees, "since June"). If the message rounds up or generalizes, correct it.
- **Downgrade a sample-based generalization to the sample.** "each file gives out its own permanent link" is an overclaim when 24 of 232 objects were sampled → "every file we checked hands out its own permanent link". The client's developer *will* open a random file, and one miss costs the credibility of the whole finding.
- **Let the vendor's own artifact carry third-party/AI claims.** "sends photos to Google Gemini" is an inference; "its own store listing says photos are identified with Gemini Vision AI" is their own words, so the data-safety mismatch cannot be argued away.
- **Add back the operational warning the short message dropped.** The message usually keeps the *what* and loses the *order*; a developer acting on it alone rotates storage download tokens first and breaks every stored image URL. If the fix order is not in the message, add one line — rules first, rewrite stored links, tokens last.
- **Calibrate the blame line to the recipient.** "Open since June, nobody was watching it" is fine for a private owner / decision-maker channel. Where the developer is in the same thread, make it system-level — "no automated check was watching it" — so it points at monitoring, not at a person.
- **Answer "should I post this publicly?" with the split verdict.** The findings are case-study grade, not trivial — but the named version never goes public (client name, app name, counts, screenshots, the PDF). The shareable asset is an anonymized case-study post: what was found in plain categories, the afternoon-sized fix, and the ownership line. Skeleton + the five-claim verification table: `references/findings-disclosure-and-public-framing.md`.
- **Direction of a testimonial.** If the user is considering writing a public recommendation/review about the app's owner, stop him: the auditor does not review the client, and doing it while that exposure is live puts the spotlight on the client's weakest week. The asset that converts is the reverse — ask the client for two lines on the user's own profile.
- **Ask the recipient's role, never infer it.** LinkedIn `/in/<slug>` answers anonymous fetches with a redirect to `/authwall`, and web/name searches return same-name noise (TikTok handles, unrelated people). Get the role from the user, then pick the framing: owner/leadership = management summary; developer = proof commands first.

## Related

- `credit-metered-saas-platform-audit` — same read-only, evidence-first doctrine, but the target is a metered SaaS / AI app-builder platform instead of an installable app: public-surface recon (robots / sitemap / llms.txt via GET), pricing-claim reconciliation, credit to dollar math, the zero-marginal-cost MCP/BYOK build path, and a staged self-prompt chain driver.
- `references/findings-disclosure-and-public-framing.md` — pre-send claim checklist, anonymized public-post skeleton, what never goes public, recipient-role framing.
- `references/firebase-public-backend-audit.md` — unauth Firestore/Storage probe recipe, status-code reading, remediation, worked example.
- `references/app-replica-costing.md` — dev-day table, price lanes, monthly run costs, store gates, residency, the map-SDK cost trap.
- `scripts/firebase_public_read_probe.sh` — key-free GET-only probe (Firestore sweep + Storage list/fetch), safe to re-run against a candidate app.
- `scripts/firebase_multi_store_probe.sh` — the fuller sweep: Firestore + **Realtime Database** + Storage, plus field-name-only output for user-owned nodes and the media-header token check. Prints no values, uids, emails or tokens.
- `references/firebase-multi-store-exposure-audit.md` — why the second database decides the report, the worked example table, migration-order trap, demo-vs-real forensics, privacy discipline while probing, and the developer-facing report shape.
- `tech-adoption-analysis` — for "is this AI/tech worth adopting" questions rather than app safety/replication.
- `website-stack-fingerprinting` — same idea for websites instead of apps.
- Aamir tool-evaluation style: cost-sensitive, wants direct-vs-indirect value + free alternatives; "tool tab lo jab kaam ho, warna backlog" — see user profile.
