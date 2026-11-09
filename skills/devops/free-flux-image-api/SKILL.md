---
name: free-flux-image-api
description: Use when any task needs images/photos — fire fluxgen first.
version: 2.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [image-generation, flux, cloudflare, workers-ai, free-tier, api, default-visuals]
    related_skills:
      - cloudflare-pages-ops
      - secrets-vault-ops
      - client-website-delivery
      - linkedin-content-engine
---

# Free FLUX Image API (Cloudflare Workers AI) — default image source

A Worker we own calls `@cf/black-forest-labs/flux-1-schnell` on Cloudflare's **free**
Workers AI allocation (10,000 neurons/day, resets **00:00 UTC**). No VM GPU, no per-image
cost, no ImagineArt plan, no watermark.

## STANDING RULE — auto-fire on any visual need (Aamir, 2026-09-15)

**Whenever a task or deliverable needs a photo/image — hero shots, blog/carousel art, OG
cards, thumbnails, ebook/site backgrounds, deck or email visuals, placeholders, mockup
filler — generate it yourself with `fluxgen` in the same turn. Do not ask, do not use
stock/placeholder images, do not ship a "put an image here" gap.**

- Generate → verify (JPEG magic + dimensions) → embed the real file in the deliverable
  (HTML `<img>`, PPTX, PDF, MEDIA: path on Telegram) → done in one pass.
- Aim for a **professional look**: name the subject, the light, the medium and the framing
  (`cinematic light`, `35mm product photography`, `soft studio lighting`, `matte texture`,
  `shallow depth of field`), and always add `no text, no watermark, no logos`.
- Client-facing work: **no human faces / living beings** (Aamir's hard rule) — describe
  objects, places, textures, abstract tech. Fire-lab / Fire & Smoke Watch is the only
  exception (crowds/faces allowed there).
- Batch work (multi-slide carousels, blog figure sets): `fluxbatch prompts.txt --outdir DIR --preset carousel`.
- Keep it cheap: `flux` model is the default for everything; see the cost table below.

## Presets (exact output sizes via `--preset`)

| preset | size | use |
|---|---|---|
| `square` | 1024×1024 | default, social square |
| `og` | 1200×630 | OG/share card, email header |
| `hero` | 1600×900 | site hero, 16:9 |
| `wide` | 1280×720 | blog/thumbnail widescreen |
| `carousel` | 1080×1350 | LinkedIn carousel slide (4:5) |
| `story` | 1080×1920 | reel/short cover (9:16) |
| `cover` | 1600×2400 | e-book / report cover |
| `thumb` | 640×360 | small card |

Presets generate then centre-crop ("cover") to the exact size with PIL — never
letterbox, never stretched.

## Neuron cost — know before you burn the day's free quota

| model | cost | notes |
|---|---|---|
| `flux` (flux-1-schnell) | **~58 neurons/image** | ≈ **170 free images/day**; prompt+steps only |
| `origin` (lucid-origin) | **~3,100 neurons/image** | ≈ **3/day MAX**; seed/width/height ok |

- `fluxgen --usage` prints today's est. used neurons, image count and time to reset.
- `fluxgen` **refuses `--model origin`** (exit 4) unless `--allow-expensive` is passed, so a casual
  auto-fire can never eat the whole day. Use `origin` only when Aamir explicitly wants
  high-fidelity / a fixed seed.
- When the free allocation is gone the API returns `4006 ... used up your daily free
  allocation of 10,000 neurons`; reset is 00:00 UTC. `fluxgen` then auto-chains to the HF
  ZeroGPU Space (real FLUX, default `--fallback auto`) and only then Pollinations. Don't
  retry in a loop.

## Live instance

- Repo: `~/projects/flux-api` (worker `flux-api`, wrangler project)
- Endpoint: `https://flux-api.sanad-io.workers.dev` — `GET /health`, `GET/POST /generate`
- Auth key: vault `infra/FLUX_API_KEY` == Worker secret `FLUX_KEY` (never printed)
- CLIs: `fluxgen` (single) · `fluxbatch` (many, from a prompts file) · config `~/.config/flux-api/config.json`
- Backends: `--backend cloudflare|hf` · `--fallback auto|hf|pollinations|none` (auto = HF, then Pollinations)
- Latency ~2.5–4.3 s, ~0.5–0.7 MB JPEG. `/health` costs no neurons.
- Usage log: `~/.local/state/flux-api/usage.jsonl`

## Steps

1. **Generate:** `fluxgen "<prompt>" -o /tmp/img.jpg --preset og` — exit 0 + printed path
   is the proof. Key comes from vault automatically.
2. **Batch:** `fluxbatch prompts.txt --outdir /tmp/art --preset carousel` (one prompt per
   line, `#` = comment, `||` splits prompt from filename).
3. **HTTP:** header `x-api-key: <key>`, then
   `GET /generate?prompt=<urlencoded>&model=flux&steps=4&format=raw` → JPEG bytes
   (`format=raw` is what `<img src>` needs), or `POST /generate` JSON
   `{prompt, model, steps, width, height, format:"b64"}` → `{ok, model, ms, image_b64}`.
4. **Always send an explicit `User-Agent`** — default urllib UA ⇒ `403 error code: 1010`.
5. **Verify the bytes, not the status:** first two bytes `FF D8` (JPEG) + dimensions via PIL;
   a 200 carrying `{error:...}` JSON is still a failure (fluxgen already does both).
6. **Redeploy after editing the Worker:** `cd ~/projects/flux-api && npx wrangler deploy`.
7. **Rotate the key:** `printf 'FLUX_API_KEY=%s\n' "$NEW" | vault set-stdin infra`
   → `vault exec infra -- python3 scripts/set_worker_secret.py`. Callers need no change.
8. **Smoke test:** `vault exec infra -- python3 scripts/smoke.py` (health, 401 on bad key,
   flux raw, origin raw, b64 shape). `README.md` has the full pitfall list.

## Secondary backend — HF ZeroGPU FLUX (implemented + verified 2026-09-15)

`--backend hf` (and the `--fallback auto` chain) runs
`~/projects/flux-api/scripts/hf_flux.py`, which drives the official
`black-forest-labs/FLUX.1-schnell` Space on Hugging Face **ZeroGPU**:

- **No key, no watermark, real FLUX.1-schnell.** The Space returns **WEBP**; the script
  converts to JPEG q92 so callers always get `FF D8` JPEG at the requested size.
- Gradio shape: `POST https://black-forest-labs-flux-1-schnell.hf.space/gradio_api/call/infer`
  with `{data:[prompt, seed, randomize, width, height, steps]}` → `event_id` → read the SSE
  stream at `/gradio_api/call/infer/<event_id>` until the `complete` event.
- Measured: **warm call ≈ 9–25 s** for 1024²/1200×630 (cold start much longer). It produced a
  clean 1200×630 JPEG in 9.4 s right after the CF quota ran out.
- Exit codes: `3` = GPU quota/saturation (fall through to Pollinations), `4` = transport/schema.
- **Anonymous quota lasts only a couple of images/day.** Set a free `HF_TOKEN` (env or
  `vault exec`) to raise it; `hf_flux.py` sends it as a bearer automatically.
- Probe helpers: `scripts/hf_probe2.py` (lists RUNNING `zero-a10g` FLUX Spaces),
  `scripts/hf_introspect.py` (prints a Space's gradio endpoints + param names),
  `scripts/hf_debug_sse.py` (dumps the raw SSE stream when a Space misbehaves).

## Pitfalls

- **Quota is shared** across every Workers AI use on `aamir1zahran@gmail.com`; 3 test calls
  to `origin` can wipe a whole day (verified the hard way 2026-09-15). Always check `--usage`.
- **`flux-1-schnell` rejects unknown fields** (`seed` → `5006`); the Worker whitelists
  per-model params and silently drops the rest — no seeds on `flux`, use `origin` for that.
- **Cloudflare error 1010** bans default/empty user-agents; any explicit UA passes. Same trap
  on any other `*.workers.dev` call.
- **wrangler OAuth token** (`~/.wrangler/config/default.toml`) is deploy-only and expires
  hourly; the vault `CLOUDFLARE_API_TOKEN` has **no** Workers AI scope. Runtime uses the
  Worker binding, not tokens.
- **`vault set-stdin <space>`** takes `KEY=VALUE` lines; `vault set-stdin infra KEY` is invalid.
- **Backup chain is `hf` → `pollinations`, in that order.** The HF ZeroGPU Space is real,
  watermark-free FLUX.1-schnell; its **anonymous** GPU quota is tiny though (measured
  2026-09-15: 2 images, then `event: error` / `data: null`, which the script maps to exit 3).
  A free `HF_TOKEN` raises that quota — set `HF_TOKEN` in the env (e.g. `vault exec <space>`)
  and `hf_flux.py` sends it as a bearer automatically.
- **Pollinations is the last resort**: Sana 768² and it **stamps a `pollinations.ai` logo
  bottom-right** (verified 2026-09-15; `nologo=true` does not remove it) — drafts / internal
  filler only, never client-facing work.
- **Gemini image gen is not a viable backup here**: the shared `GOOGLE_API_KEY` returns
  `429` on `gemini-2.5-flash-image` (probed 2026-09-15). Only a dedicated key would work.
- `--preset` cover-crops, so keep the subject centred in the prompt ("centred composition").
