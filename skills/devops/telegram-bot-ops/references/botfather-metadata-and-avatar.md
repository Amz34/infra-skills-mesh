# BotFather metadata + bot avatar — the shapes that actually work

Verified 2026-09-21 on @KsaAzConsults_Bot (fleet: brand bots per client, one profile each).
Use together with `scripts/tg_bot_api.py` (token read from a file, never argv) and the
Phase-2 section of `new-bot-profile-onboarding.md`.

## 1. Metadata methods — always set, then read back

```
setMyName(name)                                  → getMyName
setMyShortDescription(short_description)          → getMyShortDescription
setMyDescription(description)                     → getMyDescription
setMyCommands(commands=[{"command":…,"description":…}, …]) → getMyCommands
setMyProfilePhoto(photo)                          → getUserProfilePhotos
```

- Limits: name ≤64, short description ≤120, description ≤512, up to 100 commands.
- Read-back is the proof. An empty read-back (or `{"name":""}`) means the call did not land —
  do not report a field as configured on the strength of `ok:true`.
- Space calls ~1s apart; `setMy*` bursts can 429 even when polling is healthy.
- Descriptions support simple HTML/Markdown when parse-mode is set at call time; plain text is
  safest for a client-facing brand bot. No emoji/marketing fluff for this client class.
- `deleteMyCommands` does not exist; overwrite the array (or pass `commands=[]`) instead.

## 2. `setMyProfilePhoto` — the JSON-object requirement

The straightforward multipart upload **fails**:

```
POST setMyProfilePhoto   files={"photo": open("avatar.png","rb")}
→ {"ok": false, "error_code": 400, "description": "Bad Request: photo isn't specified"}
```

The `photo` field must be an **InputProfilePhoto JSON object serialised as a string**, with any
uploaded file referenced by an `attach://` name:

```python
data  = {"photo": json.dumps({"type": "static", "photo": "attach://avatar"})}
files = {"avatar": ("avatar.png", open(path, "rb"), "image/png")}
requests.post(f"{API}/bot{token}/setMyProfilePhoto", data=data, files=files)
→ {"ok": true, "result": true}
```

- `type` is `static` for an image (a video variant exists in the API; the static form is the one
  verified here). The inner `photo` value may also be a public URL or an existing `file_id`
  instead of `attach://`.
- Mixed multipart: **string fields and file fields in the same request** — a client that can only
  send one or the other cannot set a bot photo. See `scripts/tg_bot_api.py`.
- Verify by round-trip, not by `ok:true`: `getUserProfilePhotos` → `total_count: 1`, take the
  largest `file_id`, `getFile` → download `/file/bot<token>/<file_path>`, then **look at the image**
  (vision). Real case: 18,284 B / 640×640 readback confirmed the right wordmark and colour.
- Telegram re-encodes/resizes; if the readback is blurrier than expected, upload a square ≥640×640
  PNG with high-contrast type rather than a low-res JPEG.

## 3. Building an avatar that matches the sibling brand

Client fleets grow one bot at a time; the new avatar must look like the family. Recipe:

1. **Fetch the existing sibling avatar** (`getUserProfilePhotos` → `getFile` → download) and
   inspect it with vision.
2. **Measure it numerically** (PIL + numpy) instead of eyeballing: background colour from corner
   pixels; the ink bounding box of the wordmark (rows/cols whose pixels differ from bg) and of
   any second text line. Worked numbers for the AZ fleet mark (640×640, brand-ink bg):
   main wordmark band rows **191–403**, sub-line band rows **465–507**.
3. **Re-render with the same bands** using a locally available face of matching weight — check
   `fc-list : family style`, or reuse the client site's own font file (`…/public/fonts/*.woff2`).
   Match the measured stroke ratio rather than guessing: sweep weights and compare side by side
   (heavier strokes clog letterforms at avatar scale).
4. **Compare existing vs new in one image** and check it with vision before uploading — cheapest
   possible catch of a wrong glyph, clipped ascender, or off-brand colour.
5. **Keep the asset in the repo, not /tmp:** `<client-repo>/build/assets/bot-avatars/` plus
   `~/.hermes/profiles/<name>/assets/`. Brand rule for client-facing assets: wordmark/typography
   only, **no human faces or living beings**.

## 4. Egress quirk when driving the API from this fleet's VM

Direct Python/urllib calls to `api.telegram.org` intermittently failed (`Errno 101/115`) while
`curl -4` succeeded — a flaky IPv6 route. Fix inside the client: prefer A records by filtering
`socket.getaddrinfo` to `AF_INET` before calling, and retry 3× with backoff. Did not affect
`files=` uploads once that was in place; no server-side change needed.
