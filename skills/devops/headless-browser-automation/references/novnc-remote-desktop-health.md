# Watching/driving the automation desktop remotely: noVNC chain health

When the headless VM's automation Chrome must be *seen* (CAPTCHA, OAuth consent, showing the
user a live session), the chain is:

`Xvfb :99` → `x11vnc` (:5900, VNC auth) → `websockify` + noVNC (:6080) → `cloudflared` quick tunnel → browser URL.

## Pitfalls that cost real time

1. **Count websockify by process GROUP, not PID.** websockify forks a child, so `pgrep -c websockify`
   sees "1" while two groups are bound to :6080 — or sees 2 PIDs of the *same* group and reports a
   phantom duplicate. Dedupe on `pgid` (`ps -o pid,pgid,etime -C websockify`, group by `$2`).
   A PID-based health check produced endless false "reset" storms.
2. **Never `pkill -f 'websockify --web=...'` from the very shell you're running in** — the pattern
   matches the wrapper shell too and kills it (tool reports exit `-15`). Select the PIDs with awk,
   or just `systemctl --user restart munder-novnc.service`.
3. **Quick-tunnel hostname rotates.** Pick the NEWEST URL by file order in the cloudflared log
   (`awk '!seen[$0]++' … | tail -1` on the extracted hostnames), never `sort -u | tail -1` — the
   alphabetical winner is often a dead older hostname that returns HTTP `000`.
   Always probe the candidate (`curl -s -o /dev/null -w '%{http_code}' <url>/vnc.html`) and confirm
   the raw RFB banner (`RFB 003.008 | security types: [2]`) before handing the URL to a user.
4. **Client URL should self-reconnect.** Append
   `?autoconnect=1&reconnect=1&reconnect_delay=2000&resize=scale` to `/vnc.html` — closing the tab
   or a transient drop then re-attaches on reopen. (Closing the tab still ends the *client* session;
   the VM-side desktop keeps running regardless.)
5. **Self-heal as a user timer, silent on success.** oneshot `.service` + `.timer` (2 min,
   `AccuracySec=15s`) that only logs when it actually repairs something; verify it is BOTH
   `is-active` and `is-enabled`, and prove the repair script is idempotent by running it 3×
   back-to-back (exit 0, empty log).

## Verify before declaring the chain up

```bash
ss -ltnp | grep -E ':(5900|6080)\b'          # exactly ONE websockify group on 6080
curl -s -o /dev/null -w '%{http_code}\n' "$URL/vnc.html"   # expect 200
timeout 5 bash -c "exec 3<>/dev/tcp/127.0.0.1/5900; head -c 12 <&3"   # expect RFB banner
systemctl --user is-active munder-vnc-health.timer; systemctl --user is-enabled munder-vnc-health.timer
```

Poll for a real client session (`ss -tn | grep :5900 | grep ESTAB`) when you need to know whether
the user actually connected, rather than asking them.

## Credentials

The VNC password lives in `~/.vnc/passwd` / `~/.munder-vnc-passwd` (obfuscated, not plaintext).
`cmp`-match candidate passwords against those files to verify a stored value; never reproduce the
password in chat, logs, or skill text — hand it to the user out-of-band and keep it `[REDACTED]`
everywhere else.
