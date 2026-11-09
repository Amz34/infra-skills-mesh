#!/usr/bin/env python3
"""Post image + text to Bluesky via atproto REST (stdlib only — no deps).

Usage:
  BLUESKY_HANDLE=user.bsky.social BLUESKY_APP_PASSWORD=xxxx \\
    python3 bsky_post.py IMAGE.jpg "Post text" ["alt text"]

Notes:
- Image must be JPEG/PNG and <=1MB (Bluesky limit) — downscale with PIL first if needed.
- Text <=300 chars; a URL in the text is clickable (no auto link-card).
- Prints the bsky.app post URL on success.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

PDS = "https://bsky.social"
HANDLE = os.environ["BLUESKY_HANDLE"]
PASSWORD = os.environ["BLUESKY_APP_PASSWORD"]
image_path, text = sys.argv[1], sys.argv[2]
alt = sys.argv[3] if len(sys.argv) > 3 else ""


def api(path, payload=None, token=None, raw=False):
    req = urllib.request.Request(PDS + path, method="POST" if payload is not None else "GET")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = payload if not raw else None
    body = json.dumps(data).encode() if data is not None else None
    with urllib.request.urlopen(req, body) as r:
        return json.loads(r.read())


# 1) session JWT
session = api("/xrpc/com.atproto.server.createSession",
              {"identifier": HANDLE, "password": PASSWORD})
tok = session["accessJwt"]

# 2) upload image blob
with open(image_path, "rb") as f:
    img = f.read()
req = urllib.request.Request(PDS + "/xrpc/com.atproto.repo.uploadBlob", data=img, method="POST")
req.add_header("Content-Type", "image/jpeg")
req.add_header("Authorization", "Bearer " + tok)
blob = json.loads(urllib.request.urlopen(req).read())["blob"]

# 3) create post with image embed
record = {
    "text": text,
    "createdAt": datetime.now(timezone.utc).isoformat(),
    "embed": {
        "$type": "app.bsky.embed.images",
        "images": [{"image": blob, "alt": alt}],
    },
}
res = api("/xrpc/com.atproto.repo.createRecord",
          {"repo": HANDLE, "collection": "app.bsky.feed.post", "record": record}, tok)
print("POSTED:", "https://bsky.app/profile/" + HANDLE + "/post/" + res["uri"].split("/")[-1])
