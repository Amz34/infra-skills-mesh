# gflow auth / profile troubleshooting (session recipes, verified on headless VM)

Context: headless OCI VM (Xvfb `:99`), gflow CLI, Chrome profile `antigravity`, Google account on
Antigravity/Gemini-Pro plan. Goal: Flow credits path live for image/video generation.

## 1. Binary / path confusion
- `~/ops/flow/vendor/gflow-cli/` = cloned **source** repo. Koi `gflow` executable nahi.
  `./vendor/gflow-cli/gflow auth status` → `timeout: failed to run command './.../gflow': No such file or directory`.
- Real CLI: `which gflow` → **`~/.local/bin/gflow`**. Har call se pehle `export PATH="$HOME/.local/bin:$PATH"`.

## 2. Command surface actually available
| command | result |
|---|---|
| `gflow --version` / `gflow --help` | exit 0 |
| `gflow auth status` | unauth = **exit 1**; authenticated = exit 0 |
| `gflow credits` | exit 2 usage error — `credits` khud command group hai |
| `gflow credits list` | exit 0 (balance/plan) |
| `gflow credits --profile antigravity` | `Error: No such option '--profile'` (exit 2) — `--profile` **sirf** `auth` subcommands par |
| `gflow auth login --browser chrome --profile antigravity --account <email>` | interactive; background me chalao |

## 3. Profile version-mismatch → `--browser chrome` (asli fix)
Symptom: login window launch hota hai par kuch visible nahi / playwright engine purana hone ki wajah se
system Chrome ke likhe profile par downgrade error (Chrome 149 ka user-data-dir vs bundled playwright
Chromium).
Fix (verified working — Google password page live aa gayi, aur window screen par 0,0 par dikhi):

```bash
export PATH="$HOME/.local/bin:$PATH"
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
DISPLAY=:99 gflow auth login --browser chrome --profile antigravity --account <email>
```
Background me chalao + `notify_on_complete` (interactive login, 2FA user karega).

## 4. Stale lock / jhoota success
- `~/.local/share/gflow-cli/locks/profile_antigravity-<hash>.lock` — JSON par aage NUL byte hota hai,
  isliye plain `json.loads()` `JSONDecodeError` deta hai; `re` se pid/mtime nikaalo.
- Pichla gflow SIGTERM se mara ho (`exit -15`) to lock + profile ke `SingletonLock` / `SingletonCookie` /
  `SingletonSocket` stale reh jaate hain. Next launch **"Opening in existing browser session"** keh kar
  exit 0 de deta hai ≈ jhoota success; screen khaali. Fix: stale lock/Singleton files hatao, phir login
  dobara chalao.
- Purane background procs (Chrome, gflow) ek saath na chhodo — do Chrome same `--user-data-dir` par
  "existing browser session" wali confusion paida karte hain.

## 5. Screen se verify karo (guess na karo)
```bash
export DISPLAY=:99
xdotool search --onlyvisible --name "." | while read w; do echo "$w $(xdotool getwindowname $w)"; done
import -window root ~/ops/flow/out/screen_now.png
```
Phir screenshot `vision_analyze` se padho. Traps:
- gflow apna tab `--window-position=-30000,-30000` par kholta hai (playwright path) → offscreen, kuch dikhta nahi.
- `about:blank` blank page = gflow ka khaali tab; asli Chrome window ka title alag hota hai.
- Decisive state: **Flow editor** (prompt box / projects). Google sign-in hote hi Flow app sign-in maan
  lena galti hai → trade-off: reply me "auth pending" likho, jab tak editor na dikhe.

## 6. User-in-the-loop 2FA handoff checklist
1. `systemctl --user is-active munder-vnc munder-novnc` → dono `active` (x11vnc :5900, noVNC/websockify :6080).
2. Cloudflare quick tunnel (skill `cloudflare-quick-tunnel`) → `https://<name>.trycloudflare.com/vnc.html`,
   `curl --noproxy '*' -o /dev/null -w '%{http_code}'` se 200 confirm.
3. User ko: URL + VNC password + "**pehle password box par click karo**, phir type karo" + ek-ek step.
4. Login ke baad screenshot verify, phir `gflow auth status` (exit 0) + `gflow credits list`.
5. Cleanup: temp login script delete, `history -c; history -w`, chat me password/2FA code dobara na likho.
