# Point browser_exec at YOUR pre-launched Chrome: BU_CDP_URL via workspace .env — proven 2026-08-23

When the `browser_exec` TOOL says `fatal: chrome-not-running` and launches its
OWN Chrome (which fails on a headless VM), or you need a specific Xvfb GUI
Chrome (login flows, OTP handoffs), wire the tool to your existing Chrome:

## The mechanism

The browser-exec daemon reads `BU_CDP_URL` from `{workspace}/.env` at startup
(`os.environ.setdefault`). There is NO shell to export env into when calling the
`browser_exec` tool, so the .env file is the injection point.

**Workspace = `$BH_AGENT_WORKSPACE` = `~/.hermes/cache/browser-use/workspace/<session_ts>_<hash>/`**
— it is NOT `~/agent-workspace`; a .env in the wrong dir is silently ignored.
The exact path is returned as `workspace` in every browser_exec result.

## Steps

1. Start Xvfb (background): `Xvfb :99 -screen 0 1400x900x24`
2. Start GUI Chrome (background):
   `DISPLAY=:99 google-chrome --no-sandbox --disable-gpu --remote-debugging-port=9255 --remote-allow-origins=* --user-data-dir=/tmp/chrome-<task> --no-first-run --disable-infobars --window-size=1400,900 about:blank`
3. Verify BEFORE every CDP step: `curl -s http://localhost:9255/json/version` → Browser JSON
4. Write `BU_CDP_URL=http://localhost:9255` into `<workspace>/.env`
5. Call browser_exec — a fresh daemon reads the .env and drives YOUR Chrome.
   Confirm wiring with `page_info()` on the first call.

## Pitfalls (all hit in one session)

- **Chrome crash → daemon lies**: after Chrome dies and is restarted, the daemon
  still reports `BU_CDP_URL ... unreachable after 30s` (stale daemon). Kill all
  daemons `pkill -9 -f "[b]rowser_harness"` then retry — a fresh daemon connects.
- **`pkill -9 -f "<pattern>"` self-match**: if the pattern appears in your own
  command line (e.g. `pkill -9 -f "browser_harness"` while running that very
  command), pkill kills YOUR shell — exit -9, the rest of the command never runs.
  Use the bracket trick `[b]rowser_harness` / `[c]hrome`.
- **GUI Chrome without DISPLAY dies silently**: no error, empty log, port never
  binds. Always launch with `DISPLAY=:99` and diagnose with
  `curl -s localhost:9255/json/version` + `ps aux | grep -c "[c]hrome"`.
- **Fresh `--user-data-dir` per task**: reusing a recipe profile path (e.g.
  `/tmp/chrome-gui3` from an earlier Discord session) resurrects old tabs — a
  stale login tab can become the ACTIVE tab and hijack the whole flow. Same port
  is fine; new profile dir is not optional.
- **Port mismatch**: harness's own default is 9242; 9222 is the vanilla Chrome
  convention. Any port works when wired via BU_CDP_URL, but be consistent.

## Related

- `references/slack-workspace-login-magic-code.md` — the login flow this was
  built for (Slack workspace discovery + magic-code handoff), with the same
  session-hygiene pitfalls.
