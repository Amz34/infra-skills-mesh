---
name: bluesky-posting
description: Post to Bluesky (bsky.social); 'bfly' is Bluesky shorthand.
---

# Bluesky Posting ("bfly")

## Trigger
- User says **"bfly"**, **"bsky"**, ya **"Bluesky"** — sab same platform: Bluesky (bsky.social).
- "bfly" = Aamir ka shorthand (PyPI package `bfly` = "Basic Bluesky CLI Tool"). Kabhi poocho mat "bfly kya hai" — it's Bluesky.
- Task: text post, link post, ya image post Bluesky pe.

## Credentials
- Env vars: `BLUESKY_HANDLE` + `BLUESKY_APP_PASSWORD` (dono required).
- App Password: user bluesky.app → **Settings → Privacy & Security → App Passwords → Add App Password** → 16-char password, **sirf ek baar dikhta hai** (khoya to naya banao; purane app passwords independent hain, sab valid rehte hain).
- Account creation = user step (email OTP chahiye) — guide karo, khud signup mat karo.

## Setup
- CLI: `uv tool install bfly` → `~/.local/bin/bfly`
- atproto Python lib bfly ke uv venv me hota hai: `/home/ubuntu/.local/share/uv/tools/bfly/lib/python3.11/site-packages/` — scripts usko import kar sakte hain.

## bfly CLI
- `bfly post "text"` — plain text post. Limit: **300 chars** (URLs raw length count, no t.co-style shortening).
- `bfly announce "text" URL` — text + link card (app.bsky.embed.external). **Help text me typo hai**: "annouce" likha dikhta hai, real subcommand `announce` hai.
- **LIMITATION: bfly image upload support nahi karta.** Image post ke liye atproto script use karo (neeche).

## Image posts (atproto)
Working script: `~/.hermes/scripts/post_bluesky_luxewave.py` (generic copy: `scripts/bsky_post.py` is skill ke andar).
Flow: `com.atproto.server.createSession` (JWT) → `com.atproto.repo.uploadBlob` (image/jpeg) → `com.atproto.repo.createRecord` with `app.bsky.feed.post` + `app.bsky.embed.images`.
- **Image ≤1MB** Bluesky limit — bada ho to PIL se downscale/compress.
- Alt text: `images[].alt` (≤1000 chars).
- URL text me daalo to clickable hai (auto link-card nahi banta — card chahiye to `announce` / embed.external use karo).

## Cross-platform posts (X + Bluesky)
- Same copy + same hero image dono platforms pe chalta hai.
- Limits: X 280 (URL = 23 chars via t.co), Bluesky 300 (URL = raw length). Copy ≤ ~275 chars dono pe safe.
- X posting ke liye `xurl` skill; X auth/re-auth gotchas: `social-platform-integration` skill ke pitfalls + `references/x-headless-oauth.md`.

## Pitfalls
- bfly help ke subcommand names typo-prone hain — `bfly --help` pehle check karo.
- Handle format: `name.bsky.social` ya custom domain handle.
- User se app password Telegram chat me mangwana OK hai (private bot chat; secrets-safe pattern `social-platform-integration` me hai) — write to 600-perm env file immediately, kabhi echo mat karo.

## Support files
- `scripts/bsky_post.py` — generic atproto image+text post script (env-driven)
