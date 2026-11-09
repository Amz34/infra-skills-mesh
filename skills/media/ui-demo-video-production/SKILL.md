---
name: ui-demo-video-production
description: Use when making product demo videos from real app UI + VO.
version: 1.0.0
author: hermes-curator
license: CC-BY-4.0
metadata:
  hermes:
    tags: [video, ffmpeg, tts, demo, screenshots, voiceover]
    related_skills: [voice-cloning-tts, stock-video-content-pipeline]
---

# UI Demo Video Production (real screenshots + TTS VO)

## When to Use
- Product/client demo or walkthrough video where the UI must be PROOF —
  no invented screens, no AI video generators (they hallucinate UI).
- Bilingual (EN/AR) or single-language demo reels from a real deployed app
  + TTS voiceover, for LinkedIn or socials.
- Deterministic, scriptable, re-buildable demo pipeline (not a screen recorder).

Product demo / walkthrough video from REAL app UI. AI video generators
(Sora/Runway/etc) hallucinate UI — reject them when the video must be proof.
Real browser walkthrough + TTS voiceover is the honest, working alternative.

Pipeline: capture 16:9 stills → verify DOM state per shot → TTS VO per beat →
measure VO durations → zoompan stills into silent video → numpy audio placement
(NEVER ffmpeg adelay/amix — silently drops lines) → remux → QA.

## 1. Shot capture (browser_exec / headless browser)
- Viewport: `window.resizeTo` is blocked → CDP `Emulation.setDeviceMetricsOverride`
  width=1280 height=720 deviceScaleFactor=1 mobile=False.
- Helper: `snap(name)` = `capture_screenshot()` + `shutil.copy(p, dst)`.
  **`import shutil` required** (missing → NameError).
- After `goto_url`: sleep ~4.5s, wait for loading overlay to clear, THEN verify
  state via `js()` querySelector reads (URL, lang btn, chips, list items,
  tagline/footer text). Model is text-only: it cannot see screenshots, so every
  shot must carry its DOM-state string as the source of truth.
- Canvas-rendered UI (3D viewers): scene objects are NOT in the DOM. Drive the
  real clickable DOM (list items with `li.onclick`, buttons, search input +
  input-event dispatch). Module-scope functions (e.g. `selectOrgan`) are not
  callable from console.
- Detail/bone-card mode often empties the master list → fresh page load before
  each search/region demo.
- **Data-honesty pre-flight**: audit the data file first (python count of
  translated terms in organs.json etc). Only demo content that actually exists
  in the site. Pick real terms (e.g. 'كلية' existed; قلب/دماغ did not).
- Filename = DOM state, e.g. `s03_ar_bone_card.png` — descriptive, not s1/s2.

## 2. Voiceover (smallest.ai Blake — same voice EN+AR)
- POST `https://api.smallest.ai/waves/v1/tts`, model **`lightning_v3.1_pro`**
  (`"lightning"` returns HTTP 400), voice `blake`, body
  `{"text","voice_id","model","sample_rate":"24000","speed":1.3}` — `speed` IS
  honoured (1.3 ≈ 19% shorter, punchier); output = raw s16le 24 kHz mono.
  **Duration = bytes / 48000.**
- Key: `SMALLEST_API_KEY` in ~/.hermes/.env.
- raw→wav: `ffmpeg -f s16le -ar 24000 -ac 1 -i in.raw in.wav`
- Generate one line per shot/beat up front, THEN measure all durations and
  budget: speech total must fit video length minus ~1–2s headroom per shot.
  Trim by dropping weakest beats or shortening the closing tagline.

## 3. Silent video from stills (zoompan)
Per shot (vary zoom direction per shot so motion differs):
```
ffmpeg -y -loop 1 -framerate 30 -t DUR -i shot.png -vf \
"scale=1920:1080,zoompan=z='min(zoom+0.0015,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=FRAMES:s=1280x720:fps=30,format=yuv420p" \
-c:v libx264 -crf 20 -preset medium shotN.mp4
```
FRAMES = DUR*30. Concat with demuxer file list (`-f concat -safe 0 -i list.txt -c copy`).
Build silent master first; audio separately; remux `-c:v copy -c:a aac -b:a 128k -shortest`.

## 4. Audio timeline — CRITICAL PITFALL (verified)
ffmpeg `adelay`/`amix` chains with several VO inputs **silently drop lines**
(first 3 vanished in a real build; only later ones audible — caught by
volumedetect window probes). Deterministic fix: decode each VO to float
samples, place at exact sample offset into a zeroed numpy track, clip, write
WAV (wave module or ffmpeg). See `scripts/place_vo_on_timeline.py`.

## 4b. Canvas-renderer reels (data-driven graph / "canvas" style)
When there is no real UI to film (a headless automation stack, an API-only
service), do NOT fake screenshots of a UI you can't open. Render the visual
yourself from REAL data (`<canvas>` = total control, deterministic, crisp):
- One HTML file: `const R = /*__DATA__*/;` + `function renderAt(t)` that draws the
  frame for absolute time `t` (camera keyframes, packets, panels). No CSS
  animation, no `Date.now()`, no random → identical frames on every run.
- Sanitised payload built by a python step from live data (counts/durations read
  from the API/DB); every label authored in that builder, never copied verbatim
  from the source → nothing confidential can leak (grep the generated HTML for
  emails/hosts/keys/tokens as a gate).
- Camera = keyframe list `[t, cx, cy, scale]` (quintic ease per segment) +
  world→screen `setTransform(scale,0,0,scale, W/2-cx*scale, H/2-cy*scale)`;
  divide stroke widths/font-free line widths by `scale` (`inv=1/s`) so lines stay
  optically constant while text zooms.
- Beat/overlay windows are `pulse(t, t0, dur, fadeIn, fadeOut)` helpers keyed to
  the MEASURED voice-line windows, so captions and visual beats cannot drift.
- **Fit every large headline**: `fitSize(text, base, maxw, ls)` measuring with
  `ctx.measureText` — fixed 130-150 px titles clip at 1080 px width.
- Capture loop: CDP `Target.createTarget` (send NO width/height — "Target
  position can only be set for new windows"), `Target.attachToTarget(flatten=True)`,
  `Emulation.setDeviceMetricsOverride(1080x1920,dpr=1)`, then per frame
  `Runtime.evaluate(renderAt(i/30))` + `Page.captureScreenshot(jpeg q94)`.
  ~0.13 s/frame → 1350 frames ≈ 3 min.
- **Resumable capture is mandatory**: ws `timeout=180`, skip frames already on
  disk, reconnect + retry on `WebSocketTimeoutException` (a live Chrome with many
  tabs drops long sessions), close the tab when done.
- Encode `-framerate 30 -i f%05d.jpg` + numpy-placed VO (see §4) + `-shortest`.
- QA gate: exact duration, 1080x1920@30, frame 0 must carry readable text (first
  frame = autoplay thumbnail), no clipped headline, `im.max()>120` not-blank
  test, speech span/coverage, zero clipped samples.

## 4c. Live app in motion: CDP screencast → 9:16 social clip
When the thing being demoed is LIVE and animated — a camera console catching a
hazard, a dashboard updating, anything whose point is the moment it reacts —
do NOT zoompan stills (§3): you would be faking the one frame that matters.
Record the real run instead:

1. Drive the app with your normal browser-E2E driver (fake camera, scripted
   clicks) and start the stream in the same session:
   `Page.startScreencast(format='jpeg', quality=80, everyNthFrame=1)`.
   **Ack every frame** — each `Page.screencastFrame` event carries a `sessionId`
   that must be answered with `Page.screencastFrameAck`, or the stream stalls
   after ~2 frames. Write the base64 payloads to `frames/f%05d.jpg`.
2. Record a little before and after the event (e.g. 3 s idle → alert fires →
   5 s of banner + boxes) so the clip has a before/after, not just an aftermath.
3. Stitch and compose to 1080x1920:
   ```
   ffmpeg -y -framerate 12 -i frames/f%05d.jpg -c:v libx264 -crf 20 -pix_fmt yuv420p live.mp4
   ffmpeg -y -i live.mp4 -i plate_top.png -i plate_bottom.png \
     -filter_complex "[0:v]scale=900:-2[v];[1:v]scale=1080:-2[t];[2:v]scale=1080:-2[b];\
     [t][v][b]vconcat=inputs=3[out]" -map "[out]" -r 30 -crf 20 out_9x16.mp4
   ```
   (or overlay instead of vconcat if you want the phone on a styled background).
   Phone viewport 430x932 scales cleanly into a 1080-wide frame with caption
   plates above/below; generate the plates with PIL (`DejaVuSans-Bold.ttf`) —
   keep caption text plain and factual, and the first frame must be readable
   since it becomes the autoplay thumbnail.
4. QA: `ffprobe` for exact duration/resolution, extract the alert frame
   (`-ss <t> -frames:v 1`) and LOOK at it — check no cut-off text, the banner is
   present, and the detection boxes are visible.
5. **Recut for publication — strip anything private from the frame.** A console
   capture usually carries operator detail in a footer/header strip (the alert
   destination email, a hostname, a site name). Before the clip goes public,
   re-run the composition with that band cropped out and confirm with vision on
   the final frame. Keep the recut script in the PRIVATE repo (it embeds private
   paths/geometry); publish only the finished clip.
6. **HARD-CAP the recompose with `-t`, never rely on `-shortest`.**
   `ffmpeg -loop 1 -i plate.png` never reaches EOF, so a looped image plate
   mixed with a real clip makes the encode run FOREVER — `-shortest` does not
   stop it (the looped input is always "still producing"). Symptom: the outer
   `timeout` kills it (exit 124), or with `-shortest` alone it exits 1.
   Authoritative fix — take the duration from the real clip and cap the output:
   ```bash
   DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 live.mp4)
   ffmpeg -y -i live.mp4 -loop 1 -i plate_top.png -loop 1 -i plate_bottom.png \
     -filter_complex "[0:v]scale=900:-2[v];[1:v]scale=1080:-2[t];[2:v]scale=1080:-2[b];[t][v][b]vconcat=inputs=3[out]" \
     -map "[out]" -t "$DUR" -r 30 -crf 20 out_9x16.mp4      # -t is the fix; -shortest is belt-and-braces only
   ```
   Then verify: `ffprobe` the OUTPUT duration == source duration (this is the
   regression check worth keeping in any verifier — an uncapped build reports a
   duration of hours or never finishes).

**HARD RULE — no human faces/living beings in delivered media** (user's standing
rule for client-facing work). Demo clips and proof screenshots are delivered
media. Crop the SOURCE frame before recording so no crowd enters the feed
(`keep the top ~55-62%` of a street/crowd scene), then verify with vision on the
final frame before sending. Never ship a raw camera sample because "it was only
QA".

## 5. QA checklist
- `ffprobe`: exact duration (e.g. 45.000s), codecs h264+aac, size limit (≤200MB easy).
- Audio window probes per VO line:
  `ffmpeg -ss S -t T -i out.mp4 -map 0:a -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"`
  every VO window loud; gaps silent.
- Visual: extract frames `ffmpeg -ss X -frames:v 1 chk.jpg` at several
  timestamps → PIL: blank frame has std≈0; mean luminance + center-region
  distinguishes dark boot overlays from content; diff consecutive frames ⇒ motion.

## Pitfalls
- Proof/demo media must contain **no human faces or living beings** (user's HARD
  RULE for client-facing work) — crop the source before recording and verify the
  final frame with vision. A QA screenshot is still delivered media.
- Multi-input ffmpeg syntax: `Argument 'x.wav' provided as input filename, but
  'y.wav' was already specified` = flag placement error; reorder or use
  `-i` per input consistently with filter labels.
- Long write_file calls can truncate → verify length after writing scripts;
  re-write in one clean pass if cut.
- **`-loop 1` plate + `-shortest` = infinite encode.** A looped image input
  never EOFs, so the muxer never hits "shortest" and the render runs until the
  outer timeout kills it. Always pass `-t <ffprobe duration of the real clip>`
  (§4c step 6). If a build hangs or exits 124/1 at the compose step, that is the
  cause — not a codec problem.
- **Private detail hides in the chrome, not the subject.** Before publishing any
  demo media, grep/vision the full frame for emails, hostnames, site names,
  tokens in a status bar — then re-cut with that band cropped rather than
  blurring (a blur over text can be reversed; a crop cannot).
- Compact tool outputs: never trust capture/terminal summaries for identity —
  verify files with ls/ffprobe/PIL/DOM-state strings.
- Voiceover speech budget EARLY: measure all VO before assembly, then size
  shots to fit the exact total (auto-computed timeline, 45.0s exact).

## References
- `references/anatomy-45s-recipe.md` — worked example: 8 shots + 9 VO lines,
  45s exact, EN↔AR, Arabic RTL showcase.
