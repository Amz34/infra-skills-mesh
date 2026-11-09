---
name: luxewave-video-ad-pipeline
description: Build 30s LuxeWave/Hospitality ads from Flow-credit images + ffmpeg.
---

# LuxeWave Video Pipeline (30s, 1080p)

**Brand fact (correct this first):** Luxe Wave = KSA **hotel-grade guest amenities supplier** (soaps, hair & body care, amenity kits, slippers; 135+ hotels; Riyadh). Contact: WhatsApp **+966 57 426 8856**, site **luxewave-ksa.netlify.app**, CR 7050248579, shop 8k6ikq-g6.myshopify.com. Never brief scenes around coffee cups — brief **hotel bathroom / amenity** scenes.

## Working path (verified 2026-10-16)

1. **Images via Flow web lane** (agent-only composer account):
   `cd ~/ops/flow && DISPLAY=:99 ~/.local/share/uv/tools/gflow-cli/bin/python flow_gen2.py "<prompt>" <outdir>`
   - MUST use the gflow venv python (playwright lives there) and **Chrome must be running** on the profile with CDP **9446**: `bash ~/ops/flow/start_lane.sh`.
   - ~4-6 min per prompt; `flow_harvest.py` saves EVERY canvas image → dedupe by md5, pick the newest per scene (filename is a content hash, so dirs overlap).
2. **Video via Flow agent approvals (real Veo/Omni motion):** the agent-only composer supports video but ONLY via an approval prompt: `Would you like me to kick off this 1 video generation, costing 10 credits?`
   - Approval = a **radio** inside `<flow-permission-message>`: `DIV[role=radio] > span.option-label` with text `Approve`. Historical ones are `read-only`/`dimmed`; the **live** one is the non-read-only row. Click it with a real **CDP mouse** event (`Input.dispatchMouseEvent`) — JS `.click()` and locator clicks silently do nothing.
   - Typing "yes, go ahead" in the composer does NOT approve; it just re-asks. Use `~/ops/flow/approve_live.py`.
   - After approving the agent replies: *"scheduled and is waiting in the queue due to high demand"* → poll `harvest_proj_video.py` every few minutes.
3. **Assembly (local, free):** `python3 ~/ops/flow/build_video.py spec_final.json out.mp4`
   - per-segment Ken Burns (zoompan 1366x768) → lanczos upscale to 1920x1080, soft **gradient scrim** overlay (`assets/scrim_grad.png`) + text shadow so big text stays readable on light marble, then concat `-c copy` + silent AAC. ~9-10 min for 6x5s on this box (run background + notify).

## Text/spec conventions
- Wordmark: Playfair Display (gold `0xE8C07A`); captions: **Lato-Black** 96-100px, subs Lato-Medium 50px; contact line 66px.
- 6 x 5s = 30s: pain → hero amenity flat-lay → macro → social proof (135+ hotels) → benefits → CTA (wordmark + WhatsApp + site + CR).
- Bottom brand tag on every scene: `LUXE WAVE | luxewave-ksa.netlify.app`.

## Pitfalls (all hit for real)
- `gflow video i2v|chain` is **DEAD** for agent-only-composer accounts (upstream issue #799) — no flag fixes it. It also needs `DISPLAY=:99` or Chrome dies instantly ("Target page/browser has been closed"), and the profile needs `.gflow_browser_strategy` = `chrome` to skip the Chromium version-downgrade guard.
- Never `pkill -f profile_antigravity` inline — it kills the agent's own shell; use a script file and a `[t]` bracket trick.
- `flow_harvest_video.py` on the **home** page returns unrelated Flow feed videos (they contain human faces → brand-illegal). Always harvest from the **project** URL.
- No human faces anywhere in client-facing work.

## Publishing lane (QA'd 2026-10-16 AR, 2026-10-17 EN)
- Runner: `bash ~/ops/luxewave/post_video_both.sh <slug> "<title>"` → LinkedIn + X, logs one line to `~/ops/luxewave/POSTS_LOG.md`. Then Bluesky: `~/.venvs/bsky/bin/python ~/.hermes/scripts/post_bsky_video.py <mp4> <caption_bsky.txt> "<alt>"`.
- **Verify, never trust the send:** `python3 ~/ops/github/growth/li_embed_read.py <urn> --expect-file <caption_linkedin.txt>` (rc0 COMPLETE / rc2 TRUNCATED / rc5 UNVERIFIABLE) and `python3 ~/ops/luxewave/bsky_verify_post.py <at://uri> <caption_bsky.txt>`.
- **PITFALL — atproto `InvokeTimeoutError` ≠ failure (hit 2026-10-17, caused a public duplicate).** `send_video` uploads a 6 MB blob, then the client times out while the PDS already committed the post. AppView `getAuthorFeed` also lags minutes, so a "no post yet" check right after can be FALSE. Before any retry, read the repo directly (PDS, no index lag): `c.com.atproto.repo.listRecords({"repo": did, "collection": "app.bsky.feed.post", "limit": 5})` — or just wait ~2 min and re-check the feed. If a dup did land: `c.delete_post(uri)` the extra, then re-verify the keeper + confirm 400 from `public.api.bsky.app/xrpc/app.bsky.feed.getPostThread?uri=<deleted>`.
- X stays **402-blocked** (media upload credits) — expected `X=FAIL/BLOCKED`, not a regression; LinkedIn is the gate.

## Voiceover lane (QA'd 2026-10-16) — Gemini TTS via our existing free key

**Verdict: `gemini-3.8-flash-tts` through the same `GOOGLE_API_KEY` in `~/.hermes/.env` is the best fit** (works today, zero cost, script control). Evidence:
- Takes: 8.5–14 s wall for ~25 s of audio; output **24 kHz mono** PCM WAV (exactly what ffmpeg mux wants); 75-word script → 24.7 s read (fits a 30 s cut).
- Token accounting per take: ~75 text + ~614 audio tokens (returned in `usageMetadata` — count these as **Gemini tokens**, they are not Flow credits).
- **QA method that actually proves quality:** transcribe the take back with `~/.local/bin/whisper_transcribe <wav>` and diff against the script. Charon take came back word-perfect (only `LuxeWave`→"LuxWave", a brand-token artefact).
- **CRITICAL PITFALL:** style/directing text is **read aloud**. `"In a calm, low, premium hotel-narrator voice: <script>"` and a longer "Read this like…" instruction both got vocalised in the render (whisper caught it). → Send the **plain script only**; control tone by choosing the voice (`Charon` = low corporate male; `Orus`, `Puck`, `Kore`, `Aoede`…), never by text hints.
- Call shape: `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash-tts:generateContent?key=$KEY`, body `{"contents":[{"parts":[{"text":SCRIPT}]}],"generationConfig":{"responseModalities":["AUDIO"],"speechConfig":{"voiceConfig":{"prebuiltVoiceConfig":{"voiceName":"Charon"}}}}}`, then base64-decode `candidates[0].content.parts[0].inlineData.data` → 24 kHz mono 16-bit WAV. Scripts: `~/ops/flow/vo_test.py`, `vo_style_ab.py`; takes in `~/ops/flow/out/vo/`.
- Rejected alternatives: **Google Vids** = needs Google Workspace + GUI-only (against the autonomous-CLI rule); **Flow-native Veo audio** = credits + approval per attempt, no script control (keep for SFX later); **edge-tts** = 403 dead; **local kokoro-onnx** = imports OK but the model weights (`kokoro-v1.0.onnx`, `voices-v1.0.bin`) are **absent** from the box → offline fallback only, needs a ~350 MB re-download.
- Mux (verified 2026-10-16, VO-only "no music" variant): `ffmpeg -y -i <video.mp4> -i <vo.wav> -filter_complex "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,adelay=700|700,afade=t=in:st=0.7:d=0.35,apad=whole_dur=30[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 2 -t 30 -movflags +faststart <out.mp4>` → measured **-16.6 LUFS**, 30.000 s, 48 kHz stereo.
  - **PITFALL:** without `aformat … 48000 … stereo` ffmpeg writes **96 kHz mono** AAC (loudnorm's internal 192 k resample leaks through) — some players/social uploads choke on it. Always pin 48 kHz stereo.
  - `vo_mux.sh` (ambient-bed variant) is only for when music/bed is explicitly wanted — default is **VO only**.
  - End-to-end QA: extract `ffmpeg -i <out.mp4> -ac 1 -ar 16000 /tmp/a.wav` and `whisper_transcribe /tmp/a.wav` — must match the script.
- **Neuromarketing hook scripts** that QA'd well (Charon, punchy, no music, ~21-23 s so the outro breathes): v2 winner = *"Stop losing five-star guests to three-star soap. In hospitality, the smallest touch decides the biggest review. LuxeWave delivers hotel-grade custom branded amenities to over 135 hotels across Saudi Arabia. Premium products, monthly restock, prices confirmed on WhatsApp in minutes. Turn every bathroom into a brand moment. LuxeWave, WhatsApp us today."* (23.01 s, 70 in/572 out tokens). Generator: `~/ops/flow/gen_nm_vo.py` (2 takes/run).
  - **PITFALL:** `generationConfig.responseMimeType: "audio/wav"` → HTTP **400 Bad Request**. The field does not exist here; use `responseModalities:["AUDIO"]` and wrap the raw PCM yourself (24 kHz, 16-bit, mono, `wave` module).

## Arabic (RTL) edition lane (QA'd 2026-10-16)

Deliverable = same 6 Flow-credit scenes, **Arabic on-screen text + Arabic VO** (`out/LuxeWave_30s_AR_1080p.mp4`). Build it when the audience is KSA — English captions over Arabic audio is a mismatch.

- **Arabic VO:** `python3 ~/ops/flow/gen_arabic_vo.py` — same endpoint as the English lane but `voiceName: Charon`, plain RTL script. Measured take: **108 in / 624 out tokens**, **25.09 s** (fits 30 s with the 0.7 s lead-in). Script that QA'd well:
  *"لا تخسر ضيوف الفنادق الفاخرة بسبب تفاصيل بسيطة. في قطاع الضيافة، اللمسة الأصغر تصنع التقييم الأكبر. لكس ويف توفر مستلزمات ضيافة فاخرة ومخصصة لأكثر من 135 فندقاً حول المملكة. جودة عالية، توريد شهري منتظم، وأسعار فورية عبر واتساب. ارفع مستوى ضيافتك الآن. تواصل مع لكس ويف."*
  - Brand in speech = transliterated **"لكس ويف"** (whisper round-trip confirmed it twice); keep the on-screen wordmark Latin `Luxe Wave` for brand consistency.
- **RTL text render:** `python3 ~/ops/flow/build_video_ar.py spec_ar.json out.mp4` (same Ken Burns/scrim/ffmpeg pipeline as `build_video.py`, but text comes from `spec_ar.json`). Spec adds a `font` key: omit = Arabic (`Noto Sans Arabic` `/home/ubuntu/.fonts/NotoSansArabic.ttf`, variable-font weights via `set_variation_by_name("Black"/"Bold")`), `"playfair"` = Latin wordmark, `"lato"` = Latin/numeric runs. Items take `{text,size,y,color,start,var,font}`; optional per-scene `tag`.
- **PITFALL 1 — `ffmpeg drawtext` cannot shape Arabic** (no cursive joining / bidi) → text is pre-rendered to full-frame **RGBA PNG overlays** with Pillow and composited with `overlay` + alpha `fade` (the builder does this).
- **PITFALL 2 — Pillow has RaQM (HarfBuzz+FriBidi): `PIL.features.check('raqm')` → True on this box.** Feed **raw logical-order Arabic** and set `direction="rtl", language="ar"` (+ `layout_engine=ImageFont.Layout.RAQM`). Applying `arabic_reshaper`+`python-bidi` on top **double-reverses** it (letters render mirrored). This cost a full rebuild — always check `raqm` first.
- **PITFALL 3 — mixed Arabic + multi-group numbers get re-ordered.** In RTL, `"واتساب  +966 57 426 8856"` renders as `8856 426 57 966+ واتساب` (UBA treats the inter-number spaces as RTL, so the digit groups flip). **Fix: put the phone number on its own line with a Latin font** (`"font":"lato"`, no `direction`) — then it reads correctly `+966 57 426 8856`. Same rule for URLs/CR numbers next to Arabic. Keep per-scene `tag` **Arabic-only** (`"لكس ويف — مستلزمات ضيافة فاخرة"`) instead of Arabic+URL mixes.
- **QA (did all three):** (a) contact sheet of every text layer via `~/ops/flow/qa_ar_text.py` → inspect with `vision_analyze`; (b) extract real frames `ffmpeg -ss <t> -frames:v 1` → tile → vision (catches overlay/clip issues the PNG sheet can't); (c) end-to-end `whisper_transcribe /tmp/a.wav small ar` on the **final mp4** audio.
- Delivery also includes the literal same-visuals cut `out/LuxeWave_30s_VO_Arabic_1080p.mp4` (English captions + Arabic VO) when the client wants visuals untouched.

## Reporting rule (mandatory per output)
Print the block from `bash ~/ops/flow/report.sh`:
1. **Flow credits** — append every generation to `~/ops/flow/credits_ledger.tsv` (image batches + approved video cost, e.g. 10-12 credits/clip). The Flow UI exposes only **PRO tier + 50 bonus credits/day**, no numeric balance, so the ledger is the honest source.
2. **LLM/Gemini tokens** — today's table from `~/.hermes/state.db` table `session_model_usage` (calls, in/out, cache-read, est USD per model).
