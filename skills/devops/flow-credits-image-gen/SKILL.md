---
name: flow-credits-image-gen
description: Use when image/video gen should burn free Flow credits.
---

# Flow credits image/video generation (agent-composer UI lane)

Use when: a task needs an image/video and we want to spend **Google Flow credits** (account `amer231105@gmail.com`, "Antigravity" profile) instead of Flux/paid models.

## Why not the gflow CLI
`gflow auth status` verifies fine, but this account is on Flow's **agent-only composer** → `gflow image t2i` dies with `client.persistent_context_launch` / no driver (upstream issue #799). Generation through the **web UI** works and consumes credits, so drive the UI.

## Working pipeline (verified)
1. Chrome must be running on the logged-in profile (Xvfb `:99`):
   ```
   export DISPLAY=:99
   google-chrome --user-data-dir="$HOME/.local/share/gflow-cli/profile_antigravity" \
     --password-store=basic --no-first-run --no-default-browser-check \
     --remote-debugging-port=9446 --remote-allow-origins=* \
     --window-position=0,0 --window-size=1440x900 "https://flow.google.com/"
   ```
2. Generate (one command, prompt → downloaded PNG):
   ```
   cd ~/ops/flow && DISPLAY=:99 ~/.local/share/uv/tools/gflow-cli/bin/python \
     flow_gen2.py "<prompt, no human faces for client work>" ~/ops/flow/out/flowgen
   ```
   It opens/creates a project, clicks "Start new session", types into the composer
   (`div[contenteditable=true][aria-label*="What do you want"]`), clicks
   `button[aria-label="Start generation"]`, waits for the agent's "I've created…" text, then
   harvests media.
3. `~/.local/share/uv/tools/gflow-cli/bin/python ~/ops/flow/flow_harvest.py [outdir]` —
   collects `<img src>` + `performance.getEntriesByType('resource')` URLs matching
   `asb|googleusercontent`, fetches them **with page cookies** (`pg.request.get`), keeps bodies
   >60KB, sha1-dedupes via `<outdir>/.hashes`, saves `.webp`. Full-res 16:9 = **1376x768**.
4. Convert for delivery: system `python3 -c "from PIL import Image; ...convert('RGB').save(...png)"`
   (gflow venv has **no PIL** — never `import PIL` inside gflow-venv scripts).

## Pitfalls
- Composer text sometimes doesn't register → fallback = JS ClipboardEvent paste (already in flow_gen2.py).
- One Flow project is reused: "Start new session" keeps context clean; old canvas images stay visible, so harvest dedupes by content hash.
- Agent takes **4-8 min** for 2 images; the 480s completion poll is intentional. Don't harvest during a short window — harvest after the "created" text.
- Only **one** Chrome may hold `profile_antigravity`; a second launch hands off ("Opening in existing browser session") and the CLI's own launch then fails.
- Login needs Google password + 2FA (user taps the shown number) — the only human step; then `gflow auth status` shows the account verified. Set `default_profile = "antigravity"` in `~/.local/share/gflow-cli/config.toml`.
- Never print or store the Google password or cookie values.

## Files
- `~/ops/flow/flow_gen2.py` — prompt → generation → download (one command).
- `~/ops/flow/flow_harvest.py` — media URL harvester with hash dedupe.
- `~/ops/flow/flow_ui.py` — CDP connect helper (`pages(host)`, `dump`, `shot`).
- Outputs: `~/ops/flow/out/flowgen/flow_<sha1[:8]>.{webp,png}`.
