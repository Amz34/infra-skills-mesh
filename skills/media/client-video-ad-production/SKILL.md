---
name: client-video-ad-production
description: "Use when producing or replicating a promo/ad video."
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [video, ad-production, ffmpeg, edge-tts, ken-burns, voiceover, avatar, heygen]
    related_skills: [voice-cloning-tts, stock-video-content-pipeline]
---

# Client Video Ad Production

## When to Use

- Client asks for a short promo ad / clone-voice ad / talking-head ad (e.g.
  "30-sec expert no mistake" AVVS Venturi brief).
- You have stills/b-roll + a script and need a duration-fit demo, rough-cut
  preview, or final render plan — free-first, paid render only for client work.
- Bilingual (EN+AR) client ads where both language versions must fit the same
  time budget.
- Aamir forwards a viral AI/social clip ("ye kaise bana? hamari infra ye kar
  sakti hai?") → reference-clip teardown + lane inventory, **advice-only by
  default** (see the teardown section below).

End-to-end production of short promo video ads for clients (AVVS, Invertio, etc.):
script → pacing demo → rough-cut preview → final render (avatar route optional).
Bilingual EN+AR support. Cost-sensitive by default; client-paid work justifies paid
render routes (HeyGen etc.), but ALWAYS prove pacing + visual flow free first.

## Workflow (free-first, pay-later)

1. **Intake**: client brief (duration target, tone, faces allowed?) + any reference
   campaign copy (email campaigns, site copy) — reuse client's proven positioning,
   never invent new marketing copy. Extract b-roll assets from client site dirs:
   `site/assets/img/`, `site/assets/video/`, `pdf/`.
2. **Script** (~82 words EN ≈ 30s confident delivery). Verify facts/positioning from
   client's own collateral (e.g. existing `.eml` campaign). Present script verbatim;
   user says "Ok" = approved.
3. **Production pack**: write `production-pack.md` (EN + AR scripts, storyboard,
   b-roll/overlay plan, CTA). Keeps authoritative script text recoverable after
   context compaction.
4. **Pacing demos (FREE)**: local `edge-tts` (see scripts/tts_pacing.sh) to prove the
   script fits the duration budget BEFORE any paid render. Play both language demos
   for the user via MEDIA: paths. Target: ≤ duration budget (e.g. 30s).
5. **Rough-cut preview (FREE)**: ffmpeg Ken Burns stills + b-roll rough cut, audio
   muxed (see scripts/ken_burns_roughcut.sh). User reviews scene timing/pacing.
   Verify frames with local `ollama run llava:7b` if no vision tool — slow on CPU,
   allow ~2min/frame timeout, run only 1–2 key frames.
6. **Approval loop**: CTA text overlay + client logo last 3–4s, AR rough cut, scene
   duration tweaks — iterate on the free cut until user approves.
7. **Final render (PAID, client work only)**: avatar route (voice clone + talking
   head) — see voice-cloning-tts skill. Face/voice source = client's own rep
   recording (consent), NOT stock faces.

## Language / script pitfalls

- **Never let an image model draw the script.** Generated calligraphy/writing on packaging, mats,
  plaques or branded items always comes out as confident gibberish — regenerate the still text-free
  (see `references/client-facing-still-safety.md`) and burn real text in afterwards with ffmpeg.
- **Arabic renders ~25–30% longer than English** for the same word count. To fit a
  30s AR slot: rate +18% (edge-tts `ar-SA-HamedNeural`) or trim script — +14% gave
  34.3s, +16% gave 32.1s, +18% hit 29.8s. English fit at only +2% (`en-US-AndrewMultilingualNeural`).
- Never assume one script length fits both languages — demo EACH language
  separately and tune independently.
- **NO em dashes (—) in mixed EN/AR on-screen text** (captions, overlays, lower
  thirds) — the em dash breaks Arabic bidi rendering at the EN/AR boundary and text
  visibly overlaps. Use periods, commas, colons. Proper nouns (BodyParts3D,
  Z-Anatomy) stay Latin in both language versions; Arabic numerals (١٩٩) in AR text.
  Same rule applies to any bilingual EN/AR copy Aamir posts (learned 09-06 on a
  LinkedIn post that "overlapped on the video").

## Real-site / product demo videos (screen walkthroughs — advice 09-06, TEST CLIP EXECUTED 09-06 on Open Anatomy)

- **NEVER use text-to-video AI (Sora/Runway/Veo) for a demo of a REAL product or
  website** — it hallucinates UI/screens, which breaks the "video is the proof"
  positioning. A real demo = screen recording of the actual product + VO. AI video
  gen is only for abstract/mood footage where invented frames are acceptable.
- Real walkthrough pipeline (executed): drive the live site in headless Chrome →
  real screenshots → ffmpeg zoompan motion → VO mux. Work dir example:
  `/home/ubuntu/anatomy-demo-test/` (3 PNGs + vo_*.raw → test mp4).
- **Same-voice EN+AR "mixed voiceover" = smallest.ai blake** (client's Sanad male
  voice; key `SMALLEST_API_KEY` in `~/.hermes/.env`). Working pipeline to copy:
  `~/.hermes/scripts/linkedin_video_build.py` — its `tts()` returns RAW PCM at
  `RATE=24000` (s16le mono). Convert before use:
  `ffmpeg -f s16le -ar 24000 -ac 1 -i vo_en.raw vo_en.wav`; concat lines with the
  `concat` filter, then `adelay=500|500` before muxing so VO starts after the cut.
  XTTS-v2 also speaks both languages but blake is the established client voice.
- **Screenshot capture pitfalls (all hit):**
  - `window.resizeTo()` is a NO-OP in headless — force the viewport with CDP
    `Emulation.setDeviceMetricsOverride` (width 1280, height 720) BEFORE
    capturing; PNGs then come out exactly 1280x720.
  - **Canvas-rendered product UIs (e.g. 3D skeleton viewers) ignore synthetic
    DOM/coordinate clicks** — feature panels are hit-tested inside the canvas and
    scripted clicks won't open them. Don't burn rounds fighting it: capture honest
    reachable states instead (deep-link URLs like `?lang=ar` as the Arabic-RTL
    shot) and tell the user which interaction shot couldn't be automated.
- **Test-clip assembly (verified):** N stills × 3.6s each, subtle zoompan
  `z='min(zoom+0.0008,1.10)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=90:s=1280x720:fps=25`, `setsar=1` after each, `concat=n=N:v=1:a=0`, mux VO with
  `-t <n*3.6>`. Verify motion is real: extract frames at two timestamps
  (`ffmpeg -ss N -frames:v 1`) and pixel-diff (numpy) — large diff = zoom working.
  Pitfall: **ffprobe accepts only ONE input file per invocation** (probe wavs
  separately or just the final mix).
- **LinkedIn plays videos muted (silent autoplay) → burned-in captions matter as
  much as the VO** for the first seconds. 16:9 or square, mp4/h264, ≤200MB.
- Pacing: ~82 words EN ≈ 30s, so ~120–130 words ≈ 45s. Bilingual: keep EN/AR
  roughly balanced per beat; AR segment runs ~25–30% longer than its EN equivalent.
- Offer a short test clip (10s, one feature + voice sample) before the full render
  — cheap proof the concept lands before spending render time. User reviews
  voice quality (esp. Arabic), zoom smoothness, and per-shot pacing.

## ffmpeg Ken Burns pitfalls (all hit in production)

- **Bash float arithmetic**: `$(( 4.5 * 25 ))` fails — bash only does integers. Use
  `awk 'BEGIN{printf "%d", dur*fps}'` for frame counts.
- **zoompan SAR mismatch**: zoompan output must get `setsar=1` before concat or
  concat fails/desyncs.
- **Jitter**: pre-scale input to ~8000px wide before zoompan
  (`scale=8000:-1,zoompan=...:s=WxH:fps=N`) then let zoompan downscale to target —
  avoids pixel-stepping jitter on slow zooms.
- Linear zoom expression: `z='(ZS)+(ZE-ZS)*on/F'` with per-segment frame count F
  (smooth from zoom start ZS to zoom end ZE).
- Mux audio with `-shortest` so video length is bounded by the audio.
- Export `-pix_fmt yuv420p` for Telegram playback.

## Content rules (Aamir)

- NO human faces/people in client-facing public content — EXCEPT client's own
  personnel in client's own promo (AVVS Image 2 = presenter + listener, both AVVS
  reps, client-owned photo) and Aamir's own photo on his own profile with approval.
- VOICE cloning requires a real recording from the person (30–60s clean voice note);
  an existing promo video that is silent b-roll only (BGM, no speech) CANNOT serve
  as clone reference — check with ffprobe volumedetect + whisper/llava first.

## Free lane: stills → motion (no GPU / no paid video model)

When the free AI-video quota is dead (HF ZeroGPU anonymous ≈ 3 short clips/day, then a clean
`GPU refused`) or the client has no b-roll at all: generate 6–7 FLUX stills, animate them with
ffmpeg Ken-Burns + burned-in captions, chain with xfade, ship 9:16 + 1:1. Verified end-to-end at
$0 with no watermark (KSA guest-amenities promo: 21.6s, 1080×1920 and 1080×1080, silent h264).

- Recipes, auto-fit caption math, square-variant filter, QA gates and the reusable
  `vidtheme.py` theme-JSON content system → `references/free-stills-to-motion-video.md`
- Hard rules for those stills (no printed material, no garbled calligraphy, no fake brand
  labels, tile-and-look gate) → `references/client-facing-still-safety.md`

## Higgsfield generated-video lane (MCP-only — VERIFIED WORKING 2026-10-10)

- Trial/REST limitation: `higgsfield generate` returns
  `{"error_type":"only_mcp_usage_on_trial_is_available"}`. On trial, generation MUST go
  through the MCP endpoint `https://mcp.higgsfield.ai/mcp` (Clerk OAuth, no API key).
- Working lane lives in `~/ops/higgsfield/`:
  - `hfmcp.py` — headless streamable-HTTP JSON-RPC client.
    `tools | describe <tool> | call <tool> '<json>' | token | refresh`.
    Creds `~/.config/higgsfield/credentials.json` (self-refreshing); kept alive by cron
    `higgsfield-token-keepalive` (6-hourly, silent unless refresh fails).
  - `hfpipe.py` — ONE command: prompt audit → free cost preflight → spend cap → submit →
    poll → download → post-render QA → JSON report.
    `python3 hfpipe.py --model kling3_0 --prompt "..." --aspect 9:16 --duration 5 [--max-credits 25] [--preflight-only]`
  - `hfqa.py` — negation-aware prompt audit (`audit_prompt(prompt, faces_ok)`) and
    post-render QA (`qa_media`: ffprobe + OCR on-image-text detection + frame grabs).
  - `catcher.py` + `oauth_finish.py` — re-auth path if the refresh token ever dies.
- MCP call shapes (learned the hard way):
  - FREE preflight, no job submitted: `generate_video {"params":{...,"get_cost":true}}`
    → `structuredContent.cost.credits`
  - submit: `generate_video {"params":{model,prompt,aspect_ratio,duration,count},"context":"..."}`
    → `structuredContent.results[].id`
  - poll: `job_status {"jobId":"<uuid>","sync":true}` — **camelCase, top level** (not in
    params) → `generation.status`; terminal values completed/failed.
  - asset: `generation.results.rawUrl` → direct CloudFront MP4, plain curl download.
- Cost map (plus account, 9:16): kling3_0 5s=10 · 8s=16 · 10s=20 · 12s=24 · **15s=30**;
  kling3_0_turbo 5s=7.5 · 15s=22.5; veo3_1_lite flat 6 (5s) / **12 (8–15s)**; wan2_7 5s=7.5 ·
  15s=22.5; seedance_2_0_mini 5s=5 · 15s=15; grok_video_v15_lite 5s=5 · 15s=15; minimax_h3
  5s=10 · 15s=30; veo3_1 flat 16/32; seedance_2_0 5s=22.5 · 15s=67.5. 15s IS allowed on
  kling3_0/turbo, veo3_1(_lite), wan2_7, seedance(_mini), minimax_h3. Always run the free
  preflight first (`~/ops/higgsfield/cost_matrix.py` prints the whole matrix free).
- OAuth gotchas: the Clerk token endpoint blocks python-urllib (Cloudflare 1010) — send a
  browser `User-Agent` plus `Origin`/`Referer`. Killing `higgsfield auth login` mid-flight
  WIPES `credentials.json`. Never `pkill -f higgsfield...` (the harness matches its own
  command line → self-kill); kill by PID.
- Verified smoke render: seedance_2_0_mini → 720×1280 h264+aac, 5.04s, 5 credits, clean
  inanimate product shot, 0 on-image text (QA PASS).

## Aura-framing edit recipe (client ad from AI clips — PROVEN, Luxe Wave 2026-10-10)

Canonical lane: `~/clients/<client>/media/ads/aura-ad/` (spec.json · render_clips.py ·
build_overlays.py · assemble.py · qa_final.py · ad_copy.md). Copy the folder for the next client.

1. **Recon** — pull the client's real product facts from THEIR site (stats, certifications, CR
   no.); reuse brand palette + logo from their CSS/`brand/` dir. Never invent numbers.
2. **Spec** — 3 clips × 5s @ 9:16, `kling3_0` (10 cr each = 30 cr for a 15s ad with real cuts).
   Prompts: inanimate product/room shots, camera move named, ending with
   "No people, no faces, no text, no lettering, no logos, no watermark."
3. **Render** — `render_clips.py` runs hfpipe per clip sequentially; check `render_log.jsonl`.
   ~3 min/clip. Balance check: `hfmcp.py call balance '{}'`.
4. **Overlays** — PIL (`build_overlays.py`): navy scrims top+bottom, gold aura frame
   (blurred thick outline = the glow, then crisp 3px border + corner accents), logo top-centre,
   one PNG per text beat, opaque navy end card (logo + gold CTA pill + WhatsApp + URLs + CR line).
5. **VO** — `~/.venvs/tts/bin/edge-tts --voice en-US-AndrewNeural --rate=-4% --pitch=-2Hz`
   (male, confident; NO music — single VO track = satisfies "male VO / avoid music / no female").
   Fit the script to the video length by re-generating at a higher `--rate`, don't stretch audio.
6. **Assemble** — ffmpeg: 3 looped clip inputs + 6 looped PNG inputs, per-beat
   `format=rgba,fade=in/out:alpha=1` + `overlay=enable='between(t,a,b)'`, VO with
   `atempo`/`adelay`, `-r 30 -c:v libx264 -crf 19 -pix_fmt yuv420p -c:a aac -shortest
   -movflags +faststart`.
7. **QA** — `qa_final.py` (ffprobe + audio volumedetect + OCR + forbidden-string scan) AND
   view the beat frames yourself with vision (faces, legibility, clipping).

Pitfalls (all hit in production):
- **Audit false positive**: `hfqa.py` PEOPLE_WORDS is substring-matched — the word "foot"
  in "throw at the foot of the bed" BLOCKS the prompt. Write scene prompts free of
  person-words entirely ("at the end of the bed"), don't fight the gate.
- **OCR misses gold serif headlines** at native 720p with `--psm 3`. Use 2× upscale +
  `--psm 6` and `--psm 11`, aggregate, then match tokens fuzzily
  (`difflib.SequenceMatcher >= 0.72`) against MUST-HAVE strings; keep the phone number and
  URL as hard, exact assertions.
- **Text legibility**: gold/cream copy over bright marble/bedding fails. Put a soft navy
  plate (rounded rect, alpha ≈ 120–140, GaussianBlur ≈ 32) behind every text block.
- **edge-tts 403**: the Hermes-venv copy 403s (`Sec-MS-GEC` too old). Fix:
  `python3 -m venv ~/.venvs/tts && ~/.venvs/tts/bin/pip install -U edge-tts` (7.2.8 works).
  Negative CLI values need `--rate=-4%` (with `=`) or argparse eats them as flags.
- **Claim gate** (`~/ops/verify/claim_integrity.py text <file>`): the `[src: …]` tag clears
  ONE PARAGRAPH — put it on the same line as the claim, and never repeat credential words
  ("certified partner") in an untagged note line below, or CI-01 re-fires.
- Old creative may carry a stale phone number — Luxe Wave's Sept LinkedIn ad shows
  +966 582 104 381; the correct KSA number is +966 57 426 8856. Add a forbidden-string
  check for retired numbers to `qa_final.py`.
- Number check: strip non-digits before comparing (a "4★" tofu artefact once tripped a
  forbidden-"4" rule → assert on raw OCR text for tofu, digits-only for phone numbers).

## Reference-clip teardown → replication ("ye kaise bana? hamari infra ye kar sakti hai?")

Default = **advice only** unless he says "karo". Deliver five things: fingerprint →
layer-by-layer teardown with evidence → which tools make it (free vs paid) → honest
self-audit (what we ALREADY have vs the one gap) → cost math + recommendation.

1. **Fingerprint first** — `ffprobe`: res / fps / frame count / duration / bitrate / audio.
   Silent 720×720 @30 fps = feed-autoplay asset (no VO, no music, needs no sound design).
2. **Frame grabs + contact sheet** — `ffmpeg -v error -i in.mp4 -vf fps=2,scale=640:-1 f_%03d.jpg`
   → `montage f_*.jpg -tile 5x4 -geometry 320x320+2+2 -background black sheet.jpg` → vision on
   the sheet; then **zoom crops** (`crop=W:H:X:Y,scale=…`) of the suspects (paws, crowd, UI text)
   for artifact proof. Re-extract a fresh series instead of reusing stale frames.
3. **Layer decomposition — the tell for each layer:**
   - Real plate vs generated: real footage keeps signage/UI text crisp and legible; a generated
     video warps text. (Plate real + subject generated is the common hybrid.)
   - Subject generated? Fur/stripes softer than the plate, paws melt or merge, ground-contact
     smear, soft motion blur = classic i2v artifact.
   - UI chrome (LinkedIn/Twitter mock, metrics bar, author row) = **static PNG** when its size and
     position are pixel-identical in every frame. If the subject later occludes chrome text, the
     media layer sits ABOVE the chrome and scales = the "breakout" trick — that, not the AI model,
     is what makes these clips look expensive.
   - "Camera" that eases in, peaks (~8–9 s) then settles = scale/zoompan animation on the layer,
     not a real dolly.
   - Attribution honesty: the publisher's own claim about his tool is *data*; naming an exact
     model/preset is **inference** — label it as such and never cite a named preset you have not
     seen in that tool's own CLI list.
4. **Our lanes + the gap** → `references/ai-video-lane-inventory.md`. Short version: UI/chrome/
   zoom/QA/matte work is fully in-house at $0; only a subject's **locomotion** (walking animal,
   fur, physics) needs image-to-video — that single lane is the integration gap, and it is free
   (HF ZeroGPU with a token, Kaggle GPU) before it is paid.
5. **Ethics line ships with any teardown:** replaying another person's chrome with his name and
   his engagement numbers is fake-authority/impersonation — build our own chrome with our handle
   and real numbers; no faces/living beings (standing rule).

## Support files

- `references/ai-video-lane-inventory.md` — lane inventory (Higgsfield CLI / HF ZeroGPU / Kaggle /
  fal / free web tools), live-probe commands, cost math, and the verified teardown evidence log.
- `scripts/tts_pacing.sh` — edge-tts pacing demo generator (EN/AR, rate controls).
- `references/free-stills-to-motion-video.md` — free FLUX-stills → ffmpeg motion lane.
- `references/client-facing-still-safety.md` — text/label/calligraphy safety for generated stills.
- `scripts/ken_burns_roughcut.sh` — ffmpeg Ken Burns rough-cut builder (scenes list
  in the header; copies to ./preview/).
- `references/avvs-venturi-ad-case.md` — worked example: AVVS Triatek 30s ad
  (scripts, durations per rate, scene map, assets).
