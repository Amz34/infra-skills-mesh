# Case: AVVS Triatek Venturi 30s Clone-Voice Ad (Sep 2026)

Worked example of the full pipeline. AVVS = bilingual (EN+AR) client; Image 2 =
split-screen conference photo of AVVS's 2 reps (presenter + listener, both
blue-suit + white turban + beard) — client-owned, consent route = rep's own
30–60s clean voice recording as clone source.

## Positioning (reused from client's own email campaign — never invent)

> "Your Triatek valves are not obsolete — expert service extends their life,
> at a fraction of replacement cost." (source: /home/ubuntu/avvs-email/avvs-email-venturi.eml)

## Approved EN script (~82 words, "expert no mistake" tone)

> "At AVVS, we know what keeps a critical facility safe: precision airflow —
> and valves that never let you down. Your Triatek venturi valves were
> engineered for isolation rooms, laboratories, and clean spaces. Age doesn't
> mean failure. Calibration does. Genuine parts do. Expert hands do. We are
> factory-trained on Triatek systems. We diagnose on-site, we fit only genuine
> components, and we keep your facility online — never offline. Stable. Within
> spec. In the safe zone. At a fraction of the cost of replacement. Your
> Triatek valves are not obsolete. Talk to our engineers today."

AR script: production-pack.md me (parallel meaning, trimmed — Arabic is verbose).

## Duration tuning data (edge-tts, exact measured)

| Voice | Rate | Duration | Verdict |
|-------|------|----------|---------|
| en-US-AndrewMultilingualNeural | -8% (full 82w) | 43.99s | overshoot |
| same | +2% (tight text) | **29.52s** | ✅ EN fits 30s |
| ar-SA-HamedNeural | +14% | 34.30s | ❌ |
| ar-SA-HamedNeural | +16% | 32.09s | ❌ |
| ar-SA-HamedNeural | **+18%** | **29.76s** | ✅ AR fits 30s |

Lesson: Arabic runs ~25–30% longer than English per word count. Each language
tuned independently; EN needs only +2%.

## Scene map (5 scenes, sums to ~29.5s = audio bound)

1. 0–5s: Image 2 presenter (zoom-in 1.00→1.15) — hook
2. 5–13s: ref-venturi-closeup.png (1.10→1.00) — product
3. 13–17.5s: ref-service.png (1.00→1.12) — factory-trained
4. 17.5–22s: ref-controller.png (1.12→1.00) — genuine components
5. 22–29.5s: Image 2 wapas (1.00→1.08) — CTA ("Talk to our engineers today")

Next polish steps: CTA text overlay + logo last 3–4s; AR rough cut; then HeyGen
talking-head render on this skeleton.

## Asset paths (this project)

- Production pack: /home/ubuntu/clients/AVVS-Triatek/venturi-ad/production-pack.md
- Audio demos: .../venturi-ad/audio/demo-en30.mp3, demo-ar30.mp3
- Rough cut: .../venturi-ad/preview/avvs-venturi-roughcut.mp4
- Image 2 (clone source): /home/ubuntu/.hermes/cache/images/img_54ff2ce4b9d4.jpg
- b-roll: /home/ubuntu/clients/AVVS-Triatek/site/assets/img/{ref-venturi-closeup,ref-service,ref-controller,airvalve}.png
- Existing 56s site video = SILENT industrial b-roll (BGM only) — NOT usable as
  voice/presenter clone reference (verified: ffprobe volumedetect mean -25.9 dB,
  faster-whisper empty, llava frames = equipment closeups, no people).

## Verification toolkit used

- ffprobe duration: `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 file`
- Audio has signal: `ffmpeg -i x.wav -af volumedetect -f null -`
- Local vision (no cloud): `ollama run llava:7b "describe" /path/img.jpg`
  (slow on CPU — allow 2–3 min/frame, check only key frames; frame verify of
  rough cut used same route)
