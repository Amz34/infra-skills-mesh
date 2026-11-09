# Topmate-Style Personal Profile / Monetization Page

Use when the user says "topmate jaisa page banao", "replicate of my account",
or drops a topmate.io/cal.com/linktree-style profile URL to clone for
themselves. Proven 2026-08: analyzed topmate.io/tajamulkhan → built Aamir's
replica at `~/projects/topmate-aamir/index.html` (single static file).

## Profile anatomy (from topmate.io reference profiles)

Reference pages are one-page monetization profiles, NOT multi-page sites:

1. **Sticky profile card** (left column, ~330px on desktop): avatar, name,
   credential-rich headline (certs, years, sectors, languages), trust badges
   (rating stars, "Trusted Profile", SCE/license numbers), social icon row,
   CTA buttons ("Book a call" + "Message"), booking/trust note.
2. **Services grid** (2-col cards), each card has:
   - type badge: `1:1 Call` / `Digital Product` / `Priority DM` / `Package`
   - duration badge (30 mins / 48 hrs / instant)
   - title + benefit copy, price + strikethrough original, Book/Get button
3. **About me** (first-person, proof-rich) + skill chips.
4. **Testimonials** (cards + stars).
5. **JSON-LD Person schema** (`sameAs`, `jobTitle`, `knowsAbout`) — mirrors
   how topmate embeds schema.org data.

## Build rules (Aamir)

- **Avatar rule (updated 2026-08-31):** default = monogram initials ("AZ"
  gradient circle), NO other people's faces — but **Aamir's OWN profile page
  may use his photo when he approves** ("use my photo no issue"). He sent a
  WhatsApp photo → square-crop + resize to 600×600 (PIL, RGB) for the avatar.
  The no-humans rule still applies to all OTHER client-facing work.
- **Booking wiring:** 1:1 calls → Cal.com link
  (`https://cal.com/aamir-zahran-epkodq/15min`); DM/products/packages →
  prefilled WhatsApp (`https://wa.me/966574268856?text=...`). Wire EVERY
  service card to one of these two.
- **Fresh copy + different palette** — never an identical scrape of the
  reference (duplicate-content + copyright). Topmate's purple → navy/emerald
  etc. Same structure/UX, 100% own copy.
- **Placeholder testimonials:** build the section but mark sample quotes
  clearly (`<-- replace with real reviews -->`) and TELL the user they must
  be swapped before launch. Never fabricate client reviews silently.
- **Prices are estimates** unless the user gives them — flag for review.

## Build + verify + preview flow (CLI)

```bash
mkdir -p ~/projects/<name> && cd ~/projects/<name>
# write index.html (single file, inline CSS, no external deps)
```

1. Serve: `python3 -m http.server 8765` via terminal(background=true).
2. Verify: `curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/`
   → 200, then grep counts (services, booking links, schema, sections).
3. Render check — real browser screenshot (browser-use harness CDP can fail
   on this VM with `Not supported`; chrome CLI is the reliable fallback):
   ```bash
   google-chrome --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
     --window-size=1280,1600 --screenshot=/tmp/shot.png \
     --virtual-time-budget=4000 http://localhost:8765/index.html
   ```
   A 200+KB PNG = real render; send it to the user as the visual proof.
   - **Remote images may NOT load in CLI screenshots** (proven 2026-08-31):
     the avatar region rendered flat (9 unique colors, 0 skin pixels) with
     `--virtual-time-budget=4000`. Bump to `--virtual-time-budget=6000` and
     add `--run-all-compositor-stages-before-draw`; then VERIFY the photo
     actually drew by pixel-scanning the avatar region (PIL: count
     skin-tone pixels + unique colors — a rendered face shows hundreds of
     skin pixels, an empty slot shows ~0). Don't trust file size alone.
   - **Photo-slot bug (replica):** an `<img>` with only
     `onerror="this.classList.remove('show')"` NEVER displays — the `show`
     class is only ever removed, never added. Add
     `onload="this.classList.add('show')"`, and to hide the fallback
     monogram once the photo loads: `.avatar img.show ~ .mono{display:none}`.
     Verify via live browser DOM (naturalWidth=600, display:block) — the
     browser-use session shows it even when CLI screenshots don't.
4. Preview link: cloudflare quick tunnel (see `cloudflare-quick-tunnel`
   skill) — URL from `grep -oE "https://[a-z0-9-]+\.trycloudflare\.com"
   /tmp/tm-tunnel.log | tail -1`, curl-verify 200 + `<title>` before sharing.
   **NO production deploy without user review/approval** (standing rule).
5. After approval → Cloudflare Pages (`--branch master`, see
   `references/cloudflare-pages-deploy.md`).

## Deliverable summary format for the user

Analysis of reference (what layout elements it uses) → what was built with
real user data → verification numbers (HTTP 200, N services, N booking
links) → preview link + screenshot → explicit ⚠️ list: sample testimonials,
price estimates, rating badge claims that need user input before launch.

## Managing the REAL Topmate account (products, pricing, photo)

Creating digital products (free magnets + paid books), the USD/commission
settings, the "Link to external page" content bypass, and the profile-photo
manual fallback → `references/topmate-dashboard-ops.md`.
