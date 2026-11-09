# AI-video lane inventory + reference-clip teardown evidence (as of 2026-09-21)

Use when the question is "can our infra make video like THIS clip?" — pair with the
teardown section in SKILL.md. **Prices/quotas below move: re-probe before quoting
them to the user**, and never quote a promo/ad post's number as fact.

## 1. Lanes we already have

| lane | what it actually does | cost | state on this VM |
|---|---|---|---|
| free stills → motion (`~/ops/adsforge`, FLUX via CF Workers AI + ffmpeg) | stills, Ken-Burns/zoompan motion, captions, 12-rule ad gate | $0 | working |
| **reference-format replica** (`~/ops/linkedin/replicate/`) | fingerprint → self-prompt → free plate → billboard homography → matte → eased push-in + breakout + social-chrome mock → 11-check QA gate (PASS, score 1.00) | $0 | working; `out/A_clean_1080.mp4`, `out/B_feed_lookalike_1080.mp4` |
| higgsfield CLI (`higgsfield`, creds `~/.config/higgsfield/api_keys.env`) | aggregator: ~35 video models (Veo 3.1, Kling 3.0, Seedance 2.5, Wan 3.0…), marketing-studio ad formats, stills | credits | authed, but plan = **free, 10 credits** (watermarked) |
| fal.ai (`falgen`) | h3-max / turbo t2v+i2v, cost gate + spend ledger | $/s | key resolved via vault; see `fal-video-generation` |
| HF Spaces ZeroGPU (`~/ops/probe/video_space_probe.py`) | free i2v/t2v on live Spaces | $0 (queue) | spaces RUNNING, but needs an HF token for the GPU quota |
| Kaggle free GPU (`kaggle-gpu-notebook-ops`) | T4×2 ≈30 h/week → Wan 2.2 / LTX i2v locally | $0 | available (slower) |
| CF Workers AI | Flux **stills** only — no usable i2v | $0 | working |
| local GPU | — | — | none on this VM |

**Capability boundary (state it plainly):** our free lane animates camera + 2D layers
(static matted subject, push-in, breakout, chrome mock). It **cannot** generate a
subject's locomotion (a walking animal/person, fur, physics). That is image-to-video
(i2v) only — the single integration gap.

## 2. Higgsfield CLI (read-only probes — do these BEFORE any spend)

```bash
higgsfield account status          # plan + credits (free = 10, watermarked)
higgsfield model list --video      # ~35 video models
higgsfield generate cost <model> --prompt "..." [--duration N]   # credit cost, no spend
higgsfield workflow list | higgsfield marketing-studio ad-formats list
```
Measured costs (2026-09-21): `kling3_0` 10 s = **10 cr**, `veo3_1` 8 s = **32 cr**,
`seedance_2_5` 5 s = **35 cr** → the free 10 credits ≈ one Kling clip.
Plan anchors: Basic ≈ $9/mo ≈ 120 cr (≈12 kling-10 s, ≈3 seedance-5 s), Pro ≈ $23/mo ≈ 600 cr.
`higgsfield effects list | grep -iE "breakout|billboard"` returned **nothing** — do not
assert a named "breakout/billboard" preset exists unless the CLI list shows it.

## 3. Paid per-second anchors (verify on the provider page / `falgen --rates`)

- fal **Wan 2.2 A14B i2v**: ≈ $0.08/s @720p (10 s ≈ $0.80); cheaper tiers per fal page.
- Seedance 2 via fal/Replicate: ≈ $0.34–0.68/s @1080p (third-party comparators — treat as
  an order-of-magnitude anchor only).
- Budget rule: **×3–5 attempts per usable clip** (seeds/retries). Quote per finished clip,
  not per credit/second.

## 4. Free web tools (manual/browser — watermark, no commercial rights)

Kling AI, Hailuo/MiniMax, Vidu: daily free credits (commonly cited ~66/day for Kling —
**treat as unverified**; check the account page). Google AI Studio / Gemini: imaging, no
free Veo. Pollinations: stills filler only. Any of these is a human-in-the-loop step
(OAuth/CAPTCHA) — never automate the signup.

## 5. Teardown evidence log — LinkedIn-chrome + tiger breakout clip

Source of this session's teardown; same format as the `~/ops/linkedin/replicate` pilot.

- Fingerprint: 720×720, 10.033 s, 30 fps, 301 frames, **no audio**, 823 kbps.
- Plate = **real** Shibuya footage (TSUTAYA / STARBUCKS / BOOKS TAISEIDO legible), billboard
  creative swapped in as a still (text stays sharp).
- Subject = **generated** (i2v): fur/stripes visibly softer than the plate, paws melt/merge
  at ~8 s, ground contact smears.
- Chrome (metrics bar `37K / 776 comments / 669 reposts`, Like/Comment/Repost/Send, author
  row) is **pixel-identical every frame** → static PNG layer; the subject's fur **occludes**
  the chrome text late in the clip → media layer sits ABOVE the chrome and scales = breakout.
- Motion = eased push-in peaking ~8.5–9 s then settling = scale/zoompan, not a dolly.
- Attribution: the publisher's own words ("AI-made, adapted from a cat to a tiger cub") are
  data; naming `nano_banana_2` / `soul-id` / `seedance_2_5` is **inference** — label it so.
- Ethics note delivered with the teardown: a chrome mock carrying a real person's name + his
  engagement numbers is fake-authority/impersonation → make our own chrome with our handle
  and real numbers; no faces/living beings (standing rule).

## 6. Recommendation shape (Aamir is cost-sensitive)

1. Prove free first: HF token (free) → ZeroGPU Wan/LTX i2v, or Kaggle T4×2 → 3 test clips, $0.
2. Only for a client deliverable: buy **monthly**, not annual (credits don't roll over);
   Higgsfield Basic (~$9) or fal per-second — whichever the clip geometry favours.
3. Never buy on the strength of a viral post's claim; re-verify the lane's live price first.
