# rclone → Google Drive — Headless OAuth Recipe (verified 2026-08-21)

Working flow for a headless VM (no browser) + user on Telegram. No Google Cloud Console needed — rclone's public client works.

## 1. Install + create remote (non-interactive)
```bash
sudo apt-get install -y rclone
rclone config create gdrive drive scope drive config_is_local false
# config_is_local false → headless; scope drive = full Drive access
```

## 2. Generate login link (send to user on Telegram)
Build the auth URL with rclone's PUBLIC client:
```
https://accounts.google.com/o/oauth2/auth?client_id=202264815644.apps.googleusercontent.com&redirect_uri=http%3A%2F%2F127.0.0.1%3A53682%2F&response_type=code&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive&access_type=offline&prompt=consent
```
`access_type=offline` → refresh_token milega (auto-renew). `prompt=consent` → re-login pe bhi refresh_token milta hai.

## 3. User steps (Telegram copy-paste)
1. Link kholo → **"Use another account"** (NOT "Create account") → azengineeringapp@gmail.com login
2. "Google hasn't verified this app" → **Advanced → Go to rclone (unsafe)** — public client, safe
3. Allow → **"This site can't be reached" page is NORMAL** (redirect 127.0.0.1:53682 VM pe hai)
4. Address bar se **FULL URL copy** karke bhejo (usme `code=...` hota hai)

## 4. Exchange code → token (assistant side)
```bash
curl -s -X POST https://oauth2.googleapis.com/token \
  -d "code=<CODE>" \
  -d "client_id=202264815644.apps.googleusercontent.com" \
  -d "client_secret=X4Z3ca8xfWDb1Voo-F9a7ZxJ" \
  -d "redirect_uri=http://127.0.0.1:53682/" \
  -d "grant_type=authorization_code" > /tmp/gdrive_token.json
```

## 5. Write token DIRECTLY into rclone.conf (never rclone config create)
```bash
python3 - <<'EOF'
import json, datetime
tok = json.load(open('/tmp/gdrive_token.json'))
# expiry MUST be the real one (now + expires_in, RFC3339). An empty expiry OR a far-future
# sentinel like 2035 means "never refresh" -> the 1h access_token goes stale -> permanent 401
# (that was the 2-night DR outage of 2026-09-11/12). With a real expiry rclone self-refreshes.
exp = tok.get("expiry") or (datetime.datetime.now(datetime.timezone.utc)
                            + datetime.timedelta(seconds=int(tok.get("expires_in", 3599)))
                            ).strftime("%Y-%m-%dT%H:%M:%SZ")
rt = {"access_token": tok["access_token"],
      "token_type": tok.get("token_type", "Bearer"),
      "refresh_token": tok["refresh_token"],
      "expiry": exp}
path = '/home/ubuntu/.config/rclone/rclone.conf'
conf = open(path).read()
# replace existing token line (or append after [gdrive] block)
import re
conf = re.sub(r'token = .*', 'token = ' + json.dumps(rt), conf)
open(path, 'w').write(conf)
EOF
```

## 6. Verify
```bash
rclone lsl gdrive:Sanad-Backup/   # lsl/lsf/size — reliable
rclone about gdrive:              # may rate-limit transiently right after upload — retry or use lsl
```

## 7. FAST FIX for stale access_token (no user login needed — verified 2026-09-01)
If `rclone lsd` → `401 Unauthorized: Invalid Credentials` but stored `refresh_token` is still valid, exchange it directly (saves the whole user re-login dance):
```bash
curl -s -X POST https://oauth2.googleapis.com/token \
  -d "client_id=202264815644.apps.googleusercontent.com" \
  -d "client_secret=X4Z3ca8xfWDb1Voo-F9a7ZxJ" \
  -d "refresh_token=<STORED_REFRESH_TOKEN>" \
  -d "grant_type=refresh_token" > /tmp/gdrive_refresh.json
```
Then overwrite the access_token + **a REAL expiry** in rclone.conf's token JSON (keep the same refresh_token). Verify: `rclone lsd gdrive:` — 401 gone. Check token state first: grep the token line — a `refresh_token` present is what makes this fix work; the `expiry` field must be a REAL timestamp (now + `expires_in`), **never a 2035 sentinel** — that sentinel is exactly what caused the outage (see main SKILL gotcha 3).
Trigger: 401 right after a long idle period (access_token ~1h TTL expires; refresh_token ~decades). Storage folder on Drive: `Hermes-Telegram-Backup` (NOT Sanad-Backup — backup.sh default matches this since 2026-09-01).

## 8. 401 triage order (observations 2026-09-10)
Symptom cluster: nightly backup log me `[backup] ⚠️ rclone gdrive not ready — archive kept locally`, aur manual call `401 ... Invalid Credentials` — halanki **usi din subah** wahi remote (as ubuntu user) successfully upload kar chuka tha. Matlab credentials nahi, **token state** badla hai.

Pehle stored token ka STRUCTURE dekho (values kabhi print mat karo):
```bash
python3 -c "
import re;p=open('/home/ubuntu/.config/rclone/rclone.conf').read()
print('refresh_token:', bool(re.search(r'refresh_token', p)), '| expiry key:', bool(re.search(r'expiry', p)))"
```
- **`refresh_token` mojood hai par `expiry` key hi nahi** → oauth2 token ko "not expired" mana jata hai → rclone refresh hi nahi karta → stale access_token bhejta rehta hai → permanent 401. Cheapest fix pehle: **step 7** ka direct refresh exchange (fresh access_token + far-future expiry likh deta hai). Wahan se `invalid_grant` aaye to refresh token khud mar chuka hai → poora re-login (steps 2–4) ya section 9.
- **`invalid_grant` / "Token has been expired or revoked"** → refresh token dead (testing-mode OAuth clients ka refresh token ~7 din me expire hota hai) → sirf asli Google login bachata hai.
- Ye bhi check karo ke command **kis user** se chal rahi hai: root ke paas apni rclone config nahi hoti — tab error "didn't find section in config file" aata hai, 401 nahi. (See main SKILL gotcha 14.)

## 9. `rclone config reconnect gdrive:` on a headless VM — do branches
Interactive prompts (order me): `Already have a token - refresh?` → `y`, phir `Use auto config?`
- `y` (auto config) → `http://127.0.0.1:53682/auth?state=<state>` print karta hai aur callback ka intezaar karta hai. Complete sirf tab hoga jab **VM ke apne browser** me URL khule (is VM pe desktop + Chrome + RustDesk available hai → user RustDesk se login kare; assistant user ka Google password kabhi na daale).
- `n` → rclone kehta hai: jis machine pe browser + rclone dono ho, wahan `rclone authorize "drive" "<state>"` chalao, phir return hua token JSON prompt pe paste karo.
Driver pattern: `terminal(pty=true, background=true)` se start karo, prompts `process(action='submit')` se answer karo, URL aane par poll karo — prompt ko link ki ~10 min validity se zyada mat latkao.
**Auto-config branch ab END-TO-END VERIFIED hai (2026-09-10):** VM ke apne desktop se chalao (noVNC quick tunnel → recipe `rustdesk-headless-vm-access` → `references/novnc-quick-tunnel-desktop.md`), printed URL `DISPLAY=:99` ke Chrome me kholo, user Allow kare → rclone khud "Got code" keh ke token likh leta hai. Par: us run me browser ka default Google session **galat account** tha aur token chup-chaap usi ka ban gaya → **Account-verification mandatory hai** → recovery + account check: `references/rclone-wrong-account-recovery.md`. Headless branch (`n`, `rclone authorize`) ab tak unverified hai.

## Pitfalls (learned the hard way)
- **Auth code is single-use.** Exchange ONCE + save file. Test curl consumed the code → had to ask user for a fresh login link.
- `rclone config create ... token '{"..."}'` re-opens interactive OAuth and hangs → write config file directly (step 5).
- Empty `"expiry": ""` in token → rclone auth errors. Set far-future date; refresh_token renews.
- `rclone authorize` / `config reconnect` on a headless VM apne aap browser nahi kholta aur wait karta hai. Auto-config branch ke liye browser **VM pe hi** chahiye (RustDesk se login karwao); headless branch ke liye user ki machine pe rclone chahiye. Dono ke steps section 9 me. Verified end-to-end: steps 2–5 (code exchange) aur section 9 ka auto-config branch (VM ke apne browser se, 2026-09-10) — headless branch (`rclone authorize`) ab tak unverified.
- Windows pe upload fail ho par remote `lsd` chale → user/config mismatch (gotcha 14 in SKILL.md: root ke paas config nahi).
- Gmail SMTP (sending mail) needs its own 16-char App Password — Drive token is NOT reusable for mail.
