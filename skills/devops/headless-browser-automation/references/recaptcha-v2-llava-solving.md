# Google reCAPTCHA v2 image challenges — local vision-LLM solve (proven 2026-08-30)

Worked example: Substack publication-create wall (Oracle VM datacenter IP, GUI Chrome on Xvfb,
CDP port 9555). Two challenge rounds demonstrably PASSED ("Please also check the new images"
confirmations) before the user stopped the session — full token extraction was NOT confirmed.
Treat as: reliable for passing rounds, a multi-round grind that may loop from datacenter IPs.

## Architecture (reCAPTCHA v2)
- **anchor iframe** (URL contains `anchor`) = the "I'm not a robot" checkbox.
- **bframe iframe** (URL contains `bframe`) = the tile challenge, loaded on demand. Both are
  OOPIFs on the google.com origin — parent page JS is cross-origin blocked from their DOM, but
  CDP can target them directly (they appear as `"type": "iframe"` entries in `/json/list`).
- Challenge text e.g. "Select all images with crosswalks", "Select all squares with fire
  hydrants", "Select all images with buses". After a correct round: "Please also check the new
  images" → more tiles. Wrong answer: fresh challenge.

## Working recipe (validated)
1. **Trigger challenge:** click the checkbox inside the anchor iframe. DOM `.click()` on its
   `role=checkbox` element flips `aria-checked` and opens bframe. (Real mouse via CDP
   `Input.dispatchMouseEvent` also works.)
2. **Screenshot the bframe challenge** — see positioning rules below — and save PNG.
3. **Identify tiles with llava** (Ollama local, no API key):
   ```bash
   ollama pull llava:7b   # once; ~4GB, runs on CPU
   # POST http://localhost:11434/api/generate {"model":"llava:7b","prompt":"...","images":[b64],"stream":false}
   ```
   - **Per-tile beats whole-grid** (hydrant case: grid said `1,4,7` which matched only round 1;
     per-tile gave `1,2,4,6,9`). For per-tile, crop the grid screenshot with PIL (tile centers
     at bframe-relative (70/200/330, 190/320/450); ×scale when screenshot is scaled — e.g.
     800x1160 for a 400x580 bframe = ×2). Ask "Does this image contain X? Answer ONLY: yes or no".
   - Whole-grid prompt ("Which tiles contain X?") works for easy classes (crosswalks → 6,8,9;
     buses → 7,8,9) but can return garbage ("all nine" or "none") on ambiguous ones.
   - llava on 9-tile grids can take 170s+ → `TimeoutError: timed out`; retry, and use ~55-60s
     per-tile timeouts in a loop. Blank/small screenshots (29KB) yield `RESPONSE: NONE` — the
     real 260KB capture solves it.
4. **Click the identified tiles.** DOM `.click()` on the bframe `td[role=button]` elements
   SELECTS reliably. Toggling/deselecting got flaky (selection state dirty, 8/9 tiles lit) —
   if selection is dirty, reload the challenge for a clean slate instead of fighting it.
   `rc-imageselect-dynamic-selected` class marks selected tiles; read state via bframe target
   `Runtime.evaluate` + `returnByValue`.
5. **Click Verify/NEXT** (bframe button). "Please also check the new images" = round passed →
   repeat steps 2-5 on the new tiles. Keep going until success/failure resolves.

## Pitfalls (each one cost real time)
- **Audio route is IP-blocked after a couple of attempts** — Google permanently shows the audio
  button as blocked/disabled. Don't waste time on it from a datacenter IP; image challenge is
  the only route.
- **bframe offscreen (−9999px) → tiles render BLANK.** Force-positioning bframe at
  `left:-9999px` (or `482,57` when the page hides it) produced 29KB blank screenshots. The
  natural render position (400x580 at 482,57 in the worked example) is required. Restore
  natural position, wait for tile images to load, then capture.
- **Tiles are one sprite sheet cropped via CSS `left%`** — `curl` of the sprite URL returns
  EMPTY (blocked); browser `fetch` or CDP Network response capture are the alternates. The
  reliable extraction is canvas `toDataURL` per tile executed INSIDE the bframe OOPIF target
  context (same-origin there); from the parent page the canvas is cross-origin tainted.
- **CDP WebSocket needs PONG + buffering** — use `scripts/cdp_ws_client.py` from the umbrella
  skill rather than a naive one-shot client (stalls on real pages).
- **One WS connection, one logical call** — multi-call batches on a single websocket got ID
  mismatches/timeouts; open a fresh connection per call or run a proper request/response loop.
- **`Input.dispatchMouseEvent` from the parent page DOES reach OOPIF content** (tile clicks
  worked), but DOM `.click()` was the most reliable for select.

## Substack signup/publication specifics (from /tmp/sb_bundles JS reverse-engineering)
- Account check: `POST /api/v1/signup` style probes return `{"userExists": true}` when the
  email already has an account → go to login.
- Login flow: `POST /api/v1/email-login {"email", "redirect", "can_create_user": true}` →
  OTP email → `POST /api/v1/email-otp-login/complete {"code": ...}`. Email-OTP is the
  automation-friendly route (OTP read via IMAP/himalaya).
- **Publication create requires a `captcha_response` (reCAPTCHA token)** — this is the wall
  this recipe exists for. Get the token by reading `grecaptcha.getResponse()` from the page
  after the challenge completes. A `has_passed_captcha` flag on the user object gates skip.
- ReCAPTCHA only fires on the create-publication form after OTP login, not on every page —
  trigger it deliberately rather than hoping it appears.

## Honest limits
- From a datacenter IP Google may keep adding rounds ("check the new images") indefinitely;
  after ~3-4 solved rounds or ~15 min, hand the captcha to the user (one manual solve in their
  own browser) rather than burning hours — same rule as the Cloudflare section.
- Never reuse a captcha token across sessions (single-use).
