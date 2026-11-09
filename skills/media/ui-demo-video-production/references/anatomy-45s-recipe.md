# Worked Example: Anatomy 45s bilingual demo (2026-09)

Real build from session: Open Anatomy (open-anatomy.pages.dev) 45s demo video,
8 shots + 9 VO lines, exact 45.000s, 1280×720 h264+aac 4.6MB, EN↔AR Blake VO.

## Data-honesty pre-flight (organs.json audit)
- Only ~11 organ names have Arabic `ar` names (kidney, pancreas…); facts are
  Arabic; generic terms قلب/دماغ/فك NOT present.
- Demo search term chosen: **'كلية'** (2 matches → الكلية اليمنى/اليسرى).
- Arabic UI DOM-verified: الجمجمة, العمود الفقري chips; العظم الغربالي fact;
  Eastern Arabic numerals ١٩٩/٢١٣; full RTL flip via ?lang=ar.
- Deep-link behavior: `?lang=ar&bone=ethmoid` opens FULL BODY first (card not
  open) — that fix itself became a video beat ("every link opens the whole body").

## Timeline math (VO budget)
- Generated 11 VO lines first, measured raw: **duration = bytes/48000**.
- 11 lines = 51.5s speech > 45s budget → dropped beats b02/b07, shortened
  closing AR tagline to 2.56s (122,880 bytes).
- Final: 8 shots × zoompan + 9 VO lines, shot durations auto-sized so sum = 45.0s.
- Verified VO windows (volumedetect probes): b01@0.5–1.5s, gap@4.6–5.2s,
  b03@5.6–6.6s, b04_AR@11–12s, b06_AR@22.5–23.5s, b08_EN@27.1–28.1s,
  b09_EN@32.5–33.5s, b10_EN@38.5–39.5s, b11_AR@42.7–43.7s.

## Shot sequence (filenames = DOM state)
s01_boot_home_en → s02_bone_card_en → s03_ar_bone_card →
s05_ar_search_kidney → s06_ar_kidney_card → s07_ar_explode →
s08_deeplink_ar_body → s09_en_home (10 captured; 8 used in 45s cut).

## The bug that shaped the pipeline
First build used ffmpeg `adelay`/`amix` chain → **first 3 VO lines SILENT**
(volumedetect window probes caught it; astats RMS confirmed). Fix:
`build_audio2.py` numpy placement → decode each raw to samples, place at exact
offset into zeroed 45.0s float track, clip, write wav → remux with `-c:v copy
-c:a aac -b:a 128k -shortest`. All 9 lines then clean in their windows.

## Shot identity verification (model is text-only)
- PIL ImageChops diff + mean luminance + center-region: dark boot overlay shot
  vs normal home shot differ by center luminance — filenames confirmed.
- Final QA: ffprobe duration/size, frames at 2/13/24/35/44s, std≈24–26 (content,
  not blank), md5sum for delivery record.
