# noVNC quick-tunnel desktop (on-demand VM GUI for user-driven logins)

Tab use karo jab user ko **VM ka browser** chahiye ho (Google OAuth / kisi app ka sign-in) aur RustDesk
client install karne ki firad na ho: phone/laptop ke normal browser me VM ka `:99` desktop khol do.

## One-shot expose
Ready script: `/home/ubuntu/.hermes/scripts/vm-desktop-novnc.sh` (30 lines) — Xvfb `:99` ko x11vnc +
websockify/noVNC se share karta hai aur cloudflared quick tunnel ka public URL print karta hai
(saath VNC password bhi — wahi chat me bhejna hai). Local server: `http://127.0.0.1:6080/vnc.html`.

Manual equivalent:
```bash
Xvfb :99 -screen 0 1600x900x24 &                                  # agar pehle se nahi chal raha
x11vnc -display :99 -rfbport 5900 -localhost -passwd <throwaway> -forever -shared &
websockify --web=/usr/share/novnc 6080 127.0.0.1:5900 &
cloudflared tunnel --url http://127.0.0.1:6080                   # random trycloudflare URL print karta hai
```
User ko bhejne wala link: `https://<rand>.trycloudflare.com/vnc.html?autoconnect=1&resize=scale&password=<pw>`
(`autoconnect=1` + `password=` se user ko kuch type nahi karna padta).

## Critical: the app URL must open INSIDE the VM
OAuth/tool ka printed URL aksar `http://127.0.0.1:<port>/...` hota hai → user ke laptop/phone se **kabhi**
nahi khulega. VM ke apne Chrome me window kholo:
```bash
DISPLAY=:99 google-chrome --user-data-dir=/home/ubuntu/.cache/chrome-vnc --new-window "<printed-url>" &
```
`--user-data-dir` dedicated rakho taake automation ka apna Chrome profile (`Job Application Form` windows
etc.) alag rahe. User VNC se wahi window drive karta hai → callback **VM ke andar** complete ho jata hai
(rclone jaise tools token khud likh lete hain, user ko code copy karne ki zarurat nahi).

## Hygiene (yeh temporary public exposure hai)
- Kaam khatam hote hi band karo:
  `pkill -f "[c]loudflared tunnel --url http://127.0.0.1:6080"`; `pkill -f "[w]ebsockify"`; `pkill -f "[x]11vnc"`.
  **Bracket trick lazmi** — plain `pkill -f "x11vnc -display :99"` apne hi shell ki command line match kar leta hai
  (session `exit -15` se mar jata hai; 2026-09-10 ko dobara hit hua).
- VNC password throwaway rakho; chat me jaata hai isliye session ke baad process kill + password badlo.
- User ka Google/app password **kabhi** assistant type na kare — login user khud kare (CAPTCHA/lockout risk).
- VM desktop pe pehle se khuli windows (automation ke Chrome/Form windows, RustDesk) user ko "chhedni nahi" —
  handover message me likho.

## Port conflicts + password mismatch — is deployment ka chain (proven 2026-09-12)
Yahan generic script ki jagah systemd units chain hai: `munder-vnc.service` (x11vnc `:99`, port **5900**, auth
`~/.munder-vnc-passwd`) + `munder-novnc.service` (websockify `6080` → `127.0.0.1:5900`) +
`munder-vnc-tunnel.service` (cloudflared → 6080). URL + password print: `bash ~/.hermes/scripts/munder-vnc-url.sh`
(password `MUNDER_VNC_PASSWORD`, `~/.hermes/.env` me).

- **Symptom: user ka password reject hota hai, ya unit `activating` pe atka rehta hai.** Wajah = stray
  duplicate processes jo port pehle se pakde hue hain — aksar PURANE auth file ke saath, is liye documented
  password match hi nahi karta. Diagnose:
  `ss -ltnp | grep -E '5900|5901|6080'` + `ps -eo pid,args | grep -E 'x11vnc|websockify'`, phir
  `systemctl --user cat munder-vnc.service munder-novnc.service` se compare karo. Stray ko `kill <pid>`
  (bracket trick), units `restart`, aur `ss` se dobara confirm (5900 + 6080 dono listening).
  Is session me ek stray x11vnc `:99 --rfbport 5901` (`~/.vnc/passwd`) + stray websockify `6080 → 5901` the —
  documented password 5900 wale server ka tha. Cleanup ke baad chain chal gaya.
- **Password verify karo bina VNC client ke:** `x11vnc -storepasswd <password ke pehle 8 chars> /tmp/t.passwd`
  → `cmp /tmp/t.passwd ~/.munder-vnc-passwd` (MATCH = running server wahi accept karega). Note: **VNC password
  sirf 8 characters tak hota hai** — 15-char password bhi first-8 se compare hota hai, to user poori string
  type kar sakta hai, kaam karega.
- **Chain ka end-to-end proof:** `curl -s -o /dev/null -w '%{http_code}' https://<url>/vnc.html` → `200`;
  aur local port pe raw RFB probe: socket connect → banner `RFB 003.008` → version bhejo → security types
  (`[2]` = VNC auth chalu = password lagega, `[1]` = bilkul open).
- **Quick-tunnel URL kabhi `sort -u | tail -1` se na uthao.** Tunnel restart ke baad log me purane + naye dono
  URLs hote hain; alphabetical pick dead URL de deta hai (is session me alphabetical pick → HTTP 000 jabke
  live URL file-order me `tail -1` tha). Fix (`munder-vnc-url.sh` me lagaya gaya): URLs file order me nikalo
  aur har ek pe `/vnc.html` probe karke pehla **200** wala use karo.
- **Agent-driven login handoff:** agar page agent ke apne CDP Chrome me khula hai to user ko sirf CAPTCHA
  checkbox click karwana hai — pehle us tab ko visible window banao
  (`cdp('Target.createTarget', url=…, newWindow=True)`) aur fields prefill kar do, phir VNC link + password
  bhejo. Detail: `headless-browser-automation` → Turnstile section.

## Duplicate websockify → dropped/split sessions + self-heal + reconnect (proven 2026-09-12)
- **Symptom:** user connect karta hai par session bar bar girta hai / split hota hai, ya tab band karne pe poora
  desktop gaya lagta hai.
- **Root cause:** ek se zyada websockify processes ek hi port (6080) pe bind (`SO_REUSEPORT`) — incoming
  connections do gateways me baant jati hain. `ss -ltnp | grep 6080` sirf **ek** line dikhata hai, is liye
  process list se count karo, socket se nahi.
- **Count karne ka sahi tareeqa = process GROUPS, not PIDs:** websockify ek child fork karta hai, to
  `ps -eo pid,pgid,args | grep websockify` me 2 PIDs dikhte hain jabke logically 1 hi process hai. PID count
  se health check khud ko "duplicate" samajh ke chain restart karta rehta hai — aur user ka live session gir
  jata hai. One-liner: `ps -eo pgid,args | awk '/[w]ebsockify/ {print $1}' | sort -u | wc -l` → exactly `1`.
- **Cleanup:** pehle exact PIDs nikalo (`ps -eo pid,comm,args | awk '$2=="python3" && /websockify/ {print $1}'`),
  phir `kill $PIDS`, phir `systemctl --user restart munder-novnc.service`. `pkill -f 'websockify --web=/usr/share/novnc'`
  apne hi shell ko bhi maar deta hai (**exit -15**) — bracket trick ya exact PID use karo.
- **Self-heal (yahan deploy):** `~/.hermes/scripts/munder-vnc-health.sh` (success pe silent, log
  `/tmp/munder-vnc-health.log`) + `munder-vnc-health.service` (oneshot) + `munder-vnc-health.timer`
  (`OnBootSec=2min`, `OnUnitActiveSec=2min`, `AccuracySec=15s`). Yeh exactly 1 websockify group + live
  5900/6080 + tunnel process enforce karta hai. Generic/portable version: `scripts/novnc-chain-health.sh`.
- **Auto-reconnect URL:** `munder-vnc-url.sh` ab
  `?autoconnect=1&reconnect=1&reconnect_delay=2000&resize=scale` print karta hai → transient drop/tab band
  ke baad noVNC khud wapas connect kar leta hai. (Pehle sirf `autoconnect=1&resize=scale` tha.)
- **User ko expectation set karo:** tab band karne se sirf *view* band hota hai — **VM desktop, x11vnc, VM ke
  andar khula Chrome aur prefilled form state waise hi zinda rehte hain**; wahi link dobara kholne pe ~5 second
  me wapas. Lekin cloudflared quick-tunnel restart pe **hostname badal jata hai** — purana link dead (HTTP 000),
  naya `munder-vnc-url.sh` se print karke bhejo. Confirm karne ka tareeqa: `curl -s -o /dev/null -w '%{http_code}'
  https://<url>/vnc.html` = `200` + local port pe raw RFB probe (banner `RFB 003.008`, security types `[2]`).

## Verification — "user ne login kar diya" proof nahi hai
VNC band karne se pehle app-level assert karo ke kaam waqai hua. OAuth/rclone case me:
`rclone lsf gdrive:Hermes-Telegram-Backup/` me expected archives + `rclone size` sane ho
(wrong account pe free-tier quota ~khaali dikhta hai) — detail: `cloud-vm-backup-dr` → `references/rclone-wrong-account-recovery.md`.
