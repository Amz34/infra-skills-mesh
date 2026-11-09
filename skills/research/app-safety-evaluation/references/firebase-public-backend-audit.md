# Firebase public-backend audit (unauthenticated, read-only)

Purpose: turn a "looks fine, Data Safety says no data collected" listing into a real verdict by
testing the **live backend** anonymously. Small dev shops ship open rules constantly; the store
declaration is developer-typed text and is frequently false.

Rules of engagement: **GET / list only. Never write, never POST/PATCH/DELETE, never upload.**
No API key is needed for the read tests below — for an anonymous caller a public rule answers
200 and a correct rule answers 403 `PERMISSION_DENIED`. That is the whole signal.

## Endpoints

```bash
P=<firebase-project-id>            # from the app's public config / listing ecosystem
B=<project-id>.firebasestorage.app # or <project-id>.appspot.com

# 1) Firestore: enumerate a collection anonymously
curl -s -m 20 -o /tmp/f_users.json -w "users=%{http_code}:" \
  "https://firestore.googleapis.com/v1/projects/$P/databases/(default)/documents/users?pageSize=300"
grep -o '"name":' /tmp/f_users.json | wc -l      # doc count

# 2) Storage: list objects anonymously
curl -s -m 25 -o /tmp/objs.json \
  "https://firebasestorage.googleapis.com/v0/b/$B/o?maxResults=1000&fields=items(name,size)"

# 3) Storage: download one object anonymously (proves egress exposure + real bytes)
curl -s -m 25 -o /dev/null -w "unauth=%{http_code} bytes=%{size_download}\n" \
  "https://firebasestorage.googleapis.com/v0/b/$B/o/<url-encoded/path.jpg>?alt=media"
```

## Reading the result

| Result | Meaning |
|---|---|
| `403 PERMISSION_DENIED` | Rules are doing their job. Say so — credit where due. |
| `200` + doc count | Full anonymous enumeration: every field of every doc (uids, exact lat/lng, notes, image URLs, emails). P0. |
| `200` + real bytes on `?alt=media` | Anyone can download user photos and the owner pays the egress. P0. |
| `200` with 0 docs | Collection exists but is empty → the feature has no backend yet (see "empty social layer" pitfall in SKILL.md). |

Also revealing, all read-only:
- Prefix listing per directory (`o?prefix=care/`, `photos/`, `profileImages/`, `docs/`) → object counts per feature area, plus whatever the dev dumped there.
- One doc's field shape (`/tmp/f_users.json`) → reconstruct the data model, spot arrays-in-doc (1 MiB cap risk).
- Policy PDFs / `preview.html` sitting in the same public bucket → stale versions, no changelog, privacy-policy link pointing at a raw storage blob.

## Remediation to hand over (advice only)

```
match /{document=**} { allow read, write: if false; }
```
then per-collection: public read only for aggregate/leaderboard views, geo rounded for public
read (precision-limited, never raw lat-lng), `request.auth != null` + owner check on storage,
App Check on callables. Flag the false Data Safety declaration as a **separate** Play suspension
risk, not just a backend bug.

## Worked example (Invertio "The Forest" / `com.plantcommunity.dev`, 2026-09-18)

- Firebase project `invertio-1702627006371`; bucket `*.firebasestorage.app`.
- Firestore sweep: `users=200:24`, `trees=200:163`, `posts/activity/leaderboards/notifications=200:0`
  — all anonymous.
- Storage: 232 objects (`photos/` 197, `profileImages/` 20, `care/` 6, `docs/` 4, `placeholder/` 5);
  `care/<id>.jpg` fetched unauthenticated → `200`, 779,685 B (~780 KB/photo).
- Consequence for the verdict: public GPS of 163 trees + 24 uids + all user photos; "No data
  collected / no data shared" declared on the listing while email/Google/Apple + camera + precise
  location are collected → P0 security **and** P0 policy.
- Architecture findings from the same dump: `careHistory[] / waterHistory[] / careLog[]` stored as
  arrays inside the tree doc (1 MiB cap + full-doc rewrite per watering); community layer with zero
  docs (client-derived from other users' data); gamified rankings with no anti-fraud control.
