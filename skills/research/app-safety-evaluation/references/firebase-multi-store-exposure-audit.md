# Firebase multi-store exposure audit (read-only)

Companion to the backend section of SKILL.md. One Firebase project is **three stores**, and
audits that stop at Firestore + Storage miss the worst exposure. Everything below is GET / HEAD /
LIST only: no account, no key, no console, no writes, no full file downloads.

## Why multi-store matters (the lesson that flips a report from generic to eye-opening)

Worked example, Sept 2026, an app whose listing declared **"No data collected / No data shared
with third parties"** (green-tint Flutter community app, package `com.plantcommunity.dev`,
project `invertio-1702627006371`, live ~3 months):

| Store | Anonymous read | What it held |
|---|---|---|
| Firestore `users` | 200 | 24 records, 3 fields, **no email** |
| Firestore `trees` | 200 | 163 records, precise geo + owner uid |
| **Realtime Database `/users`** | **200** | **71 records, 70 with valid email**, names, photo URLs, bio, provider |
| **Realtime Database `/activities`** | **200** | 249 feed records: name, uid, location, notes, 85 photo URLs |
| **Realtime Database `/global/stats`** | **200** | totalTrees, totalCommunity, activeUsers, totalCared |
| **Realtime Database `/appConfig`, `/ads`** | **200** | forceUpdate, minSupportedVersion, storeUrl; ad image + link |
| Storage bucket listing | 200 | 232 objects (photos 197, profileImages 20, care 6, docs 4, placeholder 5) |
| Storage media HEAD | 200 | token header on 24/24 sampled objects |

The Firestore-only version of this report reads as "another app with open Firebase rules" — the
most common misconfiguration in existence, so the headline is generic and a client shrugs. The
**RTDB finding is what makes it non-generic**: the real user table, the emails, and the app's remote
config were in the store that no reviewer opened. Fixing Firestore alone leaves it all open.

Corollary for the write-up: generic headline + specific proof is fine, but make sure at least one
finding could not have been produced by pointing a stock scanner at the app.

## Probe order

Run `scripts/firebase_multi_store_probe.sh <project-id> [bucket]` for the whole sweep. Manual
sequence, one line of output per call:

```bash
PID=<firebase-project-id>; B=<bucket>.firebasestorage.app

# 1. Firestore: per-collection anonymous GET. Names must be GUESSED —
#    documents:listCollectionIds answers 403 to anonymous callers.
for c in users trees posts activity leaderboards notifications; do
  curl -s -m 20 -o /tmp/fs_$c.json -w "$c=%{http_code}:" \
    "https://firestore.googleapis.com/v1/projects/$PID/databases/(default)/documents/$c?pageSize=300"
  grep -o '"name":' /tmp/fs_$c.json | wc -l
done

# 2. Realtime Database: one call reveals the whole data model as node names.
curl -s -m 20 "https://$PID-default-rtdb.firebaseio.com/.json?shallow=true"
for n in users activities trees global appConfig ads; do
  curl -s -m 20 -o /tmp/rtdb_$n.json -w "$n=%{http_code}:" \
    "https://$PID-default-rtdb.firebaseio.com/$n.json"; done

# 3. Storage: list, then read response HEADERS (not just status).
curl -s -m 25 -o /tmp/objs.json \
  "https://firebasestorage.googleapis.com/v0/b/$B/o?maxResults=1000&fields=items(name,size,contentType)"
curl -sI -m 20 "https://firebasestorage.googleapis.com/v0/b/$B/o/<url-encoded-path>?alt=media" \
  | grep -i firebasestoragedownloadtokens
```

## Reading the results

- Firestore `200` on a collection → anonymous enumeration; per-record fields exposed.
- Firestore `200` + `0` docs → the **read rule is open at collection level** and the collection is
  simply empty (a social layer that does not exist). That is a finding, not a non-finding: it proves
  the rule shape, and it means the community features are computed client-side from other users' data.
- Firestore `403` on `listCollectionIds` while single collections answer `200` → you cannot enumerate
  names anonymously; sweep a guessed list and never claim "N collections exist".
- RTDB `/.json?shallow=true` → `200` plus a key list is the app's real data model in one request.
  `Permission denied` → rules correct, say so.
- Storage `200` on the object list → anonymous enumeration; `200` + payload on `?alt=media` →
  unauthenticated download and the owner's egress budget is open.
- `x-goog-meta-firebasestoragedownloadtokens` in the media response header → **the file's permanent
  private link, handed to an unauthenticated caller.** Sampled 24/24 in the worked example, i.e.
  systematic. Also present on the Play-required privacy policy PDF parked in the same bucket, which
  makes the compliance artifact itself depend on the leak.

## Migration-order trap (the reason security fixes get rolled back)

Stored `imageUrl` / `photoURL` values in the app's own records normally contain
`?alt=media&token=...`. Revoking or rotating download tokens, or turning public read off, breaks
**every image already stored in every record** — 163 tree records + 48 user photo URLs in the worked
example. Correct sequence, in one release: define the stable URL model → rewrite all stored URLs with
a server-side migration script → verify one old and one new record → only then revoke the old tokens.

## Is the product real, or a demo? (value-distribution forensics)

Read-only data answers a question scanners cannot. Compute histograms of every categorical field,
then read uniformity:

- `species` = only `Plant` (122) and the Arabic word for plant (41); `healthStatus` = `excellent`
  ×163; `status` = `healthy` ×163; `waterLevel` = `100` ×163; `careHistory` and `careLog` empty ×163;
  `waterHistory` = exactly one entry ×163; `careTips` = 3 identical canned strings.
- Verdict: the care / health / AI-identification half of the app looks alive on screen and stores
  **only defaults**. That is the most valuable product finding in the report and it is invisible to
  any security scanner.
- Related smells: `id` duplicating the document key (163/163); two overlapping status fields
  (`status` + `healthStatus`); `uid` (28-char auth id) alongside `plantedBy` (a display name);
  timestamps stored as **strings** instead of Timestamp/ISO types (weak sorting and range queries).

## Privacy discipline while probing (non-negotiable)

- Print **field names, value types, lengths and aggregate counts only** once a node is user-owned.
  Never names, emails, uids, coordinates, note bodies, tokens, or signed URLs into stdout, the
  report, or the chat.
- Do not infer a data class from a loose regex. In the worked example a digit-run regex flagged
  "652 phone hits" — they were millisecond timestamps and doc ids, not phone numbers. Claim a PII
  class only when the **field name** (e.g. `email`) and its shape agree, and report it as
  "70 of 71 records carry an email field with a valid address shape".
- Never write to the target. Read-only is the whole contract of an advice-only QA pass; state
  explicitly in the reply that nothing was created, changed or deleted.
- Writes are **unverified** by definition. When a node looks writable (public read on `/appConfig`,
  `/ads`), report the read exposure as proven and the write exposure as untested — and let the risk
  statement carry it ("if write is also open, an anonymous visitor can retarget the forced-update
  storeUrl or the ad link for the whole install base"). Do not test it.

## Developer-facing findings report shape

One block per finding: **What we found / Proof (copy-paste curl) / Impact / Fix**. Then, always:

1. A "Method and limits" header naming what was tested and stating read-only, no account, no keys.
2. A severity summary table (Critical / High / Medium) before the detail.
3. An explicit **"not tested"** section — write access above all. Honesty here is what makes the
   rest credible to the developer reading it.
4. A numbered **fix order**, cheapest-blast-radius first (rules → declaration → code release),
   with a one-line time estimate per stage.
5. Housekeeping (duplicate/overlapping fields, string dates) as low-severity cleanup.
6. A closing non-technical paragraph: how long it has been live, how short the fix is, and that the
   gap is **ownership** — one automated daily check plus one named person who receives the alert.

Style for this user (verbatim asks: "make ultra and concise and ai free", "no jargons",
"polished way"): plain English, no emoji, no em-dashes, no AI-slop phrasing, short sentences,
every claim verifiable by the reader within two minutes. Report file in pure English; chat
commentary in Hinglish. Measure before claiming: state median/typical sizes, not the largest
outlier you happened to open, and when a later measurement contradicts an earlier claim, correct it
openly in the next revision instead of dropping it silently.
