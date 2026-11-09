---
name: persistent-browser-workflow
description: Use when you need persistent browser sessions or replay.
---

# Persistent Browser + Workflow Recorder

Grok Bot ke "own computer" layer ka free equivalent. Single-file tool:
`/home/ubuntu/ops/persistent-browser/pb.py` (README sath hai).

## Kab use karo
- Kisi site par login karke session 24/7 persistent chahiye (har run par dobara login nahi)
- Ek workflow ek baar record karke baar-baar replay karna (cron se bhi)

## Commands
```bash
python3 /home/ubuntu/ops/persistent-browser/pb.py run <routine.json>
python3 /home/ubuntu/ops/persistent-browser/pb.py record <script.py> <out.json>
python3 /home/ubuntu/ops/persistent-browser/pb.py state|clear|new
```

## Key facts (verified)
- `python3` = Hermes venv (has `playwright`); system `/usr/bin/python3` does NOT.
- Chrome binary = `/opt/google/chrome/chrome` (Playwright's own chromium is NOT downloaded;
  `~/.hermes/browser-use/chromium-1248/` is empty). Pass `executable_path` explicitly.
- Persistent context = `chromium.launch_persistent_context(profile_dir, executable_path=CHROME, headless=True, args=['--no-sandbox','--disable-gpu'])`.
- Profile dir = `~/.config/persistent-browser/profile`.

## Persistence semantics
- localStorage → persists across processes ✓
- cookies with `expires` → persist ✓ (use `cookie_set` step; it sets expiry automatically)
- session-only cookies (no expiry) → do NOT persist (standard browser behavior)

## Pitfalls
- Headless only, no GPU. Human ke *click* ki headed recording ke liye
  `chrome-automation.service` (CDP 9333) ya VNC use karo, pb.py nahi.
- `pkill -f 'http.server 8123'` khud ko bhi match karta hai (shell command mein wahi
  string hota hai) — `pkill -f '[h]ttp.server 8123'` bracket trick use karo.
- Steps JSON mein unknown key → step FAIL hota hai, routine abort.

## Step types (routine JSON)
goto, click, fill, select, type, wait/sleep, wait_for, text, js, screenshot,
assert {selector,contains}, set_local {key,value}, get_local, cookie_set {name,value,url,days}, cookies.