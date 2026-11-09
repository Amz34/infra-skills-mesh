---
name: google-flow-generation-ops
description: Use when generating via Google Flow (gflow CLI/MCP).
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [google-flow, veo, imagen, gflow, credits, mcp, headless-login]
    related_skills: [mcp-tool-servers, cloudflare-quick-tunnel, headless-browser-automation, fal-video-generation]
---

# Google Flow (Veo / Imagen) — gflow CLI + MCP ops

Google Flow (`labs.google/Flow`, Antigravity / Gemini-Pro plan) image (Imagen) + video (Veo) generate karta hai
**Flow credits** se. Ye credits LLM tokens se alag bucket hain — isliye media tasks par token burn karne ke
bajaye Flow credits path use karo. Access: `gflow` CLI (browser-profile login backed) + uska MCP server
(Hermes me `gflow_*` tools: `gflow_generate_image`, `gflow_generate_video`, `gflow_get_credits`,
`gflow_auth_status`, `gflow_character_*`, `gflow_upscale_*`).

## When to Use (trigger)
- Video/image generate karna hai aur Flow credits available hain (tokens bachane hain).
- `gflow_*` MCP tools wire/verify karne hain.
- gflow auth/profile problem: login page nahi khulta, "Opening in existing browser session", ya
  profile version/downgrade error.
- Headless VM par kisi bhi **browser-profile-backed vendor CLI** ka Google login handoff karna hai
  (pattern yahan generalise hota hai — har vendor par wahi offscreen/lock/2FA jaal).

## Layout (verified)
- Binary: **`~/.local/bin/gflow`** → pehle `export PATH="$HOME/.local/bin:$PATH"`.
  `~/ops/flow/vendor/gflow-cli` sirf **source repo** hai — usme executable `gflow` nahi hota, wahan se
  `./gflow` chalane par `No such file or directory` aata hai (bekaar debugging loop).
- State: `~/.local/share/gflow-cli/` → `profile_<name>/` (Chrome user-data-dir) + `locks/`.
- Working dir: `~/ops/flow` (screenshots `out/` me likho).
- Commands: `gflow auth status` (unauthenticated = **exit 1**), `gflow auth login --browser chrome
  --profile antigravity --account <email>`, `gflow credits list` (`gflow credits` par `--profile` flag
  **nahi** hai — exit 2 usage error).

## Auth: `--browser chrome` hi bharoso karo
Bundled playwright Chromium purana hota hai; naye system Chrome ne likha profile use karne par
version/downgrade error deta hai aur login window kabhi visible nahi hota. Fix + verified rasta:

```bash
export PATH="$HOME/.local/bin:$PATH"
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
DISPLAY=:99 gflow auth login --browser chrome --profile antigravity --account <email>   # background + notify_on_complete
```

System Chrome chalta hai → profile downgrade skip, aur window **screen par actually dikhti hai**.
Isko **background process** me chalao (interactive Google sign-in chahiye); poora error/recipe:
`references/gflow-auth-profile-troubleshooting.md`.

## Login handoff — Google 2FA user hi karega
Headless VM par agent Google login (password + 2FA) **nahi** kar sakta. User ko remote screen do:
1. Chrome `DISPLAY=:99` par (x11vnc `:5900` + noVNC/websockify `:6080`; hamare units `munder-vnc` /
   `munder-novnc` — dono `active` hone chahiye).
2. Public HTTPS: skill `cloudflare-quick-tunnel` → `https://<name>.trycloudflare.com/vnc.html`
   (HTTP 200 confirm karo, phir hi link bhejo).
3. User ko URL + VNC password do, aur bolo: **pehle password field par click karo** — VNC me focus
   ke bina typing khaali jaati hai. Steps ek-ek, exact field naam ke saath (user non-technical UI
   guidance pasand karte hain).
4. Login ke baad screenshot se verify karo. **Google sign-in ≠ Flow app sign-in**: decisive proof tab
   hai jab Flow ka editor (prompt box / projects list) khule — tab tak "connected" mat bolo,
   "auth pending" bolo.
5. Credentials hygiene: temp login script delete, `history -c; history -w`, password/2FA code kisi
   file/history/chat me persist na ho.

## Offscreen window trap (jaal)
gflow apna Chrome aksar `--window-position=-30000,-30000` par kholta hai → Xvfb/VNC par kuch nahi
dikhta aur lagta hai "kuch hua hi nahi". State guess karne ke bajaye screen se padho:

```bash
export DISPLAY=:99
xdotool search --onlyvisible --name "." | while read w; do
  echo "win=$w $(xdotool getwindowname $w)"; done          # window + title check
import -window root ~/ops/flow/out/live.png                 # phir vision se dekho
```
Blank page dikhe to yaad rakho ki gflow ka apna khaali tab (`about:blank`) bhi list me hota hai —
doosre window ka title/tab asli target hai.

Stale locks: jab pichla gflow SIGTERM se mara ho, `~/.local/share/gflow-cli/locks/profile_<name>-<hash>.lock`
+ profile ke `Singleton*` files hatao. Warna next launch **"Opening in existing browser session"** keh kar
exit 0 deta hai — jhoota success, screen khaali. Lock JSON me NUL-byte prefix ho sakta hai → `json.loads`
fail hoga, digits regex se nikaalo.

## Credits-first billing
Media tasks Flow credits se chalao, LLM tokens se nahi. Balance: `gflow_get_credits` / `gflow credits list`.
MCP side par auth pass hona integration kaam karne ka proof nahi — read-only tools (`status`, `credits`,
`list_*`) pass hote hain par generation plan-gated ho sakta hai: skill `mcp-tool-servers` ka
"Entitlement / plan gating" section (uski apni `references/vendor-mcp-plan-gating.md`) dekho, aur
**decisive call** ek asli generation hi maano.

## Verification (baat karne se pehle)
1. `gflow auth status` → exit 0 + `gflow credits list` chalta ho.
2. Ek asli sasti generation (image pehle, video baad me) + output file/URL read-back.
3. MCP path: `hermes mcp list` me entry + ek real tool call. Registration naye tools agle session me deta
   hai — usi turn me "tool available hai" mat kehna.
4. User-facing reply me credits/plan summary do; andar ke ids/keys/session secrets print mat karo
   (vendor tool text me "internal / do not reveal" markings hoti hain).

## References
- `references/gflow-auth-profile-troubleshooting.md` — auth/profile error transcripts, lock handling,
  window-position diagnosis, VNC handoff checklist.
