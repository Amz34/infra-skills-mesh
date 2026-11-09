---
name: ksa-hospitality-video-lane
description: Use when building the weekly KSA Luxe Wave video.
version: 1.0.0
author: hermes
license: MIT
metadata:
  hermes:
    tags: [video, luxewave, ksa, fluxgen, ffmpeg, cron-lane]
    related_skills: [client-video-ad-production, free-flux-image-api]
---

# KSA hospitality video lane (Luxe Wave)

## When to Use
The weekly KSA hospitality cron lane fires, or Aamir asks for the next Luxe Wave guest-care short (theme JSON -> stills -> clips -> VO -> QA -> draft for approval).

Working dir: `/home/ubuntu/projects/ksa-amenities-video`. Output: `~/work/<slug>/`.
Rotation (weekly): room amenities -> welcome & F&B -> housekeeping & turndown -> front-desk & arrival -> Ramadan & Umrah -> MICE/business.

## Steps
1. `themes/<slug>.json`: 7 shots, last = end card. Mandatory top-level `"brand": "Luxe Wave"` + per-shot `"vo"` (4-5 words, no numbers; closing vo exactly `Luxe Wave.`). No faces/living beings, no text/labels inside stills.
2. Build: `PATH=$HOME/.local/bin:$PATH python3 vidtheme.py --theme themes/<slug>.json` (~10-18 min, run with background). `--no-gen` reuses existing stills and only re-renders clips + assemble.
   - fluxgen quota code 4006 -> retry with `--fallback pollinations`.
3. VO: `python3 add_vo.py --theme themes/<slug>.json --speed 1.12` -> must print `"over_slot": []`; shorten any offending vo line and rerun (TTS cached by text+speed = free).
4. QA (run all): ffprobe both voiced mp4s (1080x1920 / 1080x1080, h264 30fps, ~21.6 s, aac 24 kHz stereo); `volumedetect` (max -3..-1, mean -21..-19 dB); contact sheet `fps=1/2.9,scale=270:480,tile=4x2` + own vision check; `python3 ~/ops/verify/claim_integrity.py post <captions.txt> --json --no-ledger` = pass.
5. Log one line to `~/.local/state/ksa-amenities/runs.jsonl` `{ts,theme,master,square,voiced,qa_verdict}` — square = UNVOICED 1x1 (matches older lines).
6. Deliver DRAFT only (MEDIA:<abs path to 9x16_vo>, 3-line caption + hashtags + brand links + WhatsApp +966 57 426 8856 + one question). Never post. On approval: `~/ops/luxewave/post_video_both.sh <slug> "<title>"`.

## Pitfalls (all hit in production)
- **fluxgen writes lettering into stills.** Folded towels get a monogram/crest; hotel corridors get glowing room numbers/plaques. Fix: pick subjects with no flat surfaces/signage — rolled towels (not folded), lantern close-ups (no walls/doors in frame). Vision-check every still full-res; re-prompt, delete the still, rebuild (only missing stills regenerate).
- **End-card caption overflow.** `vidtheme.py _fit()` used a 0.60 char-width factor; DejaVuSans-Bold is ~0.74, so long caps rendered past the frame. Fixed to 0.80 (do not lower). Test a new size with a `drawtext` render on a `color` lavfi source before a full rebuild.
- **Loudness below spec.** `add_vo.py` mix used `loudnorm=I=-16` -> mean_volume -22.7 dB. Fixed to `I=-14:TP=-1.5` -> mean -20.9, max -1.5. Verify with `volumedetect` after any change.
- Contact sheet `tile=4x2` leaves the 8th cell empty by design (7 shots).
- Always re-run `add_vo.py` after ANY rebuild: the voiced mp4s are muxed from the current master.
- Voiced deliverable does not exist until add_vo succeeds; never deliver/QA the unvoiced master.
- **edge-tts is DEAD on this VM** (403 `Invalid response status`; bumping `CHROMIUM_FULL_VERSION` to `152.0.4191.66` in `edge_tts/constants.py` does not help, VM clock is correct). Working male-VO routes: (a) local **Kokoro** — `~/.venvs/tts/bin/python` + `kokoro-onnx`, model `~/.cache/kokoro/kokoro-v1.0.onnx` + `voices-v1.0.bin`, voice `bm_george` (en-gb), free/offline, ~1 min for 5 lines; (b) Gemini TTS `gemini-2.5-flash-preview-tts` voice `Charon` with `GOOGLE_API_KEY` from `~/.hermes/.env` — good voice but 429s after ~10 calls/day. `~/.venvs/tts` python has the TTS deps; system `python3` does NOT.
- **Place VO takes with `adelay`+`amix=inputs=N:normalize=0,apad`, never pad-to-absolute-then-concat.** The concat approach silently dropped whole lines (per-beat VO coverage read 0.0 / 0.03). Verify with `silencedetect=noise=-40dB:d=0.35` and check speech lands at each planned start.
- **ffmpeg `-map` indexes must match real input order.** Put audio inputs AFTER the image inputs and compute `[N:a]` from the actual order, else ffmpeg fails with `Stream specifier ':v' ... matches no streams`.
- **Overlay collisions:** huge Playfair display lines (168-200 px) clipped/scaled by `_fit` need >=55 px baseline clearance; always re-check the rendered PNG at full res before assembling.
- Higgsfield credits expiring? `hfpipe.py --model veo3_1_lite --duration 4 --aspect 9:16 --count 1` (6 cr) buys one hyper-real hero shot; stretch it with `setpts=PTS*1.55,fps=30` and reuse existing clips for the rest of the cut.
