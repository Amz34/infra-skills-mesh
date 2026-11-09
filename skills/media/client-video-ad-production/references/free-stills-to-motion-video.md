# Free stills → motion video lane (no GPU, no paid video model)

Verified 2026-09-16: KSA guest-amenities promo, 21.6s, 1080×1920 + 1080×1080, silent h264, **$0, no watermark**.
Use when the free AI-video quota is dead (HF ZeroGPU anonymous ≈ 3 short clips/day then a clean `GPU refused`), no paid video model is available, and a finished social/promo cut is needed today.

## Pipeline
1. **Stills** — `fluxgen "<prompt>, no text, no writing, no labels, no watermark" -o stills/NN_slug.jpg --preset story`
   (presets: `story` 1080×1920, `carousel` 1080×1350, `square` 1024², `og` 1200×630). 6–7 stills = one video.
2. **Per-shot clip** — Ken-Burns zoom + caption burn-in, 3s each @30fps.
3. **Assemble** — xfade chain, `-movflags +faststart`, then a second pass for the 1:1 variant.

```bash
# clip from one still (zoom-in)
ffmpeg -y -loop 1 -i still.jpg -t 3 -r 30 -vf \
 "scale=1620:-1,zoompan=z='min(1+0.0012*on,1.15)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,format=yuv420p" \
 -c:v libx264 -preset veryfast -crf 20 clip.mp4

# caption: textfile= avoids ffmpeg escaping hell entirely
drawtext=textfile=caps/01a.txt:fontcolor=white:fontsize=52:box=1:boxcolor=black@0.45:boxborderw=18:x=(w-text_w)/2:y=h-300
```

- **xfade chain:** `[0][1]xfade=transition=fade:duration=0.6:offset=<t>` where t for clip *i* = sum(durations before i) − 0.6×i.
- **Square variant that keeps the full vertical frame** (no caption crop): blurred cover bg + centered overlay —
  `[0:v]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,gblur=sigma=28[bg];[0:v]scale=1080:-1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2`
- Keep masters **silent** (platforms add music; LinkedIn autoplays muted), h264 + yuv420p + faststart.

## Caption auto-fit (same bug hit twice)
drawtext never wraps: long captions overflow and are clipped on **both** sides.
Compute the size before rendering:
`fs = base; while fs > lo and n_chars*fs*0.60 > W-120: fs -= 2`
(base ≈ 78 headline / 52 body / 38 sub, floor 26–40). End cards with long headlines are the worst offenders — never hardcode fontsize 100.

## QA gates — run all four before delivering
1. **ffprobe per file** (one file per call; multi-input `-show_entries` prints nothing usable): expect W×H, `r_frame_rate 30/1`, `nb_frames ≈ duration×30`, and format duration/size.
2. **Contact sheet from the FINAL mp4, then LOOK at it:**
   `ffmpeg -i v.mp4 -vf "fps=1/<dur/8>,scale=270:480,tile=4x2" -frames:v 1 sheet.png` → check caption clipping, transition frames, humans, garbled text. Sample so the last tile lands *before* the fade-out, otherwise it reads as a black tile.
3. **Still-level QA is the cheapest gate** — tile the stills (`-pattern_type glob -i '*.jpg' -vf "scale=360:-1,tile=3x2"`) and inspect before rendering any clip. This is how garbled calligraphy and fake brand labels were caught in 2 regen rounds instead of after render.
4. **Content-integrity gate on the on-screen caption text:** `python3 ~/ops/verify/claim_integrity.py post <caps.txt> --json` → must pass.

## Reusable builder + theme spec (repeatable content system)
`~/projects/ksa-amenities-video/vidtheme.py --theme themes/<name>.json [--no-gen]`
- Theme JSON: `name`, `rules[]`, `shots[{id, prompt, cap1, cap2, motion, big}]`, end card last with `big: true`.
- `--no-gen` re-renders clips + assembly from existing stills — the fast loop after a caption or still fix.
- Outputs `~/work/<name>/` with `stills/`, `caps/`, `clips/`, `<name>_9x16.mp4`, `<name>_1x1.mp4`.
- Weekly angle-rotation cron (job `dddcb5c9c7c6`, Mon 05:00 UTC) produces a fresh draft and delivers it for approval — never auto-post on the user's behalf.

## Pitfalls
- **Never prompt printed material**: menu cards, tea-chest labels, bottle labels, signage all render as AI gibberish. Add "no printed material, no signage, no labels, no menu cards" to every prompt *and* to the theme `rules`.
- **Never accept garbled script/calligraphy** on client-facing stills (KSA: prayer mat, plaque, packaging). Regenerate text-free: "plain cream woven fabric, completely simple trim, completely blank, no writing or motifs".
- Clip duration must be ≥ 2× transition duration or the xfade math yields a stalled/black tail.
- If a short-and-simple prompt stops matching the subject (e.g. robe+slippers came back as a towel pile), tighten the subject words explicitly rather than relying on mood wording.
- Cheap re-iteration order: fix still → `--no-gen` rebuild → contact sheet → vision check → re-probe.
