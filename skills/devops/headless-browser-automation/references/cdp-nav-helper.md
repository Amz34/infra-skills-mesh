# cdp_nav.py — minimal CDP fetch helper (works when browser_exec is dead)

Location: `/home/ubuntu/ops/scripts/cdp_nav.py` (run with `/home/ubuntu/.venvs/gws/bin/python`).

```
DISPLAY=:99 python cdp_nav.py <port> <user-data-dir> <url> \
    [--wait 14] [--text 2000] [--js "<expr>"] [--shot /tmp/x.png] [--keep]
```

- Prints `FINAL_URL`, `TITLE`, `TEXT_LEN`, `----TEXT----`, and `JS_RESULT:` (JSON of the `--js` expression value).
- Launches Chrome itself if `http://127.0.0.1:<port>/json/version` is down; reuses a running instance otherwise.
- `CHROME_EXTRA="--headless=new"` env var injects extra Chrome flags.
- Known-good profile/port pairs on this VM: `chrome-automation`:9333 (logged-out guest),
  `chrome-forms`:9223 (Google account `aamir1zahran@gmail.com`), `chrome-oauth`:9444.

## Pitfalls learned
- Keep printed output small (<~1KB): the tool result gets collapsed to "1 lines output" when a blob is large.
  Write long dumps to a file and print only `grep`/`cut` slices.
- Never `pkill -f "remote-debugging-port=XXXX"` — the pattern matches your own shell and kills the call
  (SIGTERM). Use `pgrep -f "remote-debugging-port=92[4]5"` (bracket trick) then `kill <PID>`.
- The interactive profile (`~/.config/google-chrome`) refuses to start with a debug port if another
  instance holds it; `--headless=new` on that profile also failed to open the port — use the dedicated
  automation profiles instead.
- `chrome_tab_guard.py` reaps orphaned *headless* Chrome instances that lost their CDP client; keep
  sessions short or stay attached.

## Reading an authwalled LinkedIn profile without login
`linkedin.com/in/...` returns HTTP 999 to curl and an Arabic authwall in a guest browser. Working detour:
drive Google in the guest Chrome and read the indexed profile + AI Overview:

```
cdp_nav.py 9333 ~/.config/chrome-automation \
  "https://www.google.com/search?q=%22<profile-slug>%22&hl=en" --wait 14 \
  --js "JSON.stringify({res:Array.from(document.querySelectorAll('h3')).slice(0,4).map(h=>h.innerText.slice(0,80)),snips:Array.from(document.querySelectorAll('div.VwiC3b,span.aCOpRe,div.kb0PBd')).slice(0,6).map(s=>s.innerText.slice(0,160))})"
```

The slug-specific query (`"mahmoud-khalifa-mba-mit"`) pins the exact person, and the AI Overview returns
current role, company, location, tenure and prior employers. Treat it as index-derived, not source-verified.
