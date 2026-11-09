# LinkedIn Post Publish via API (Aamir's profile)

Proven recipe — AVVS post published 2026-08 (`urn:li:share:7496175315040468993`).
Used for Layer-4 SEO / client promo posts without touching the browser.

## Prereqs (already set up on the VM)
- Token: `~/linkedin_token.json` (keys: access_token, scope `w_member_social`,
  obtained_at, expires_in=5184000 ≈ 60 days — refresh when expired)
- Person URN: `~/linkedin_person_id.txt` (value `ZXkhXV9MAp` — Aamir's own
  profile; posts appear on HIS profile, there is no AVVS company page)
- App: IFMI (client 77hjlj8tf5eq0y) — use its token, scope has post rights

## Publish (Python, no deps)

```python
import json, urllib.request
tok = json.load(open('linkedin_token.json'))['access_token']
person = open('linkedin_person_id.txt').read().strip()
text = """...post body..."""
payload = {
    "author": f"urn:li:person:{person}",
    "lifecycleState": "PUBLISHED",
    "specificContent": {"com.linkedin.ugc.ShareContent": {
        "shareCommentary": {"text": text},
        "shareMediaCategory": "NONE"}},
    "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
}
req = urllib.request.Request(
    "https://api.linkedin.com/v2/ugcPosts",
    data=json.dumps(payload).encode(),
    headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json",
             "X-Restli-Protocol-Version": "2.0.0"},
    method="POST")
print(json.loads(urllib.request.urlopen(req).read()))
# success → {"id": "urn:li:share:..."} ; HTTPError → read e.read().decode()[:500]
```

## Post URL for the user
`https://www.linkedin.com/feed/update/urn:li:share:<id>`

## Content rules (AVVS/client posts)
- Pure English, hooky/pain-point opener ("Isolation room pressure drift =
  infection risk"), silent-degradations list, services bullets, link
  `avvs-triatek.pages.dev`, CTA comment/share/follow + 3–5 hashtags.
- Client-facing: no AI-fluff, professional tone. Emoji minimal (👉👇 only).
- Sanad standard (pure English, one-word brand, NO emojis) applies to Sanad
  posts only — AVVS posts may use the light arrows above.
