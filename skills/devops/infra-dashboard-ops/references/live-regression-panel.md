# Shipping a live "debug pass / fixes" panel on the dashboard

Use when the user says "dashboard pe debug fixes ka update add karo" — the ask is
almost never a static changelog. A text changelog rots the moment it is written:
next week nobody re-checks it, and a fix silently regresses (observed: a briefing
poster service stayed dead for 7 days while the dashboard showed green).

## Rule: ship PROBES, not prose

Ship an array of live checks that the collector re-runs on every tick. The card
then flips amber/red on its own when a fix regresses. Prose is a bonus second
half of the card, not the mechanism.

Each check: `{name, state (ok|warn|down|off), detail, hint}` and one line of what
to do when it is not `ok`.

Checks that have paid for themselves:
- sandbox/namespace probe — actually EXECUTE a trivial namespaced command
  (`bwrap --dev-bind / / --unshare-net true`), never read a sysctl value back.
  Reading the knob is not proof the mechanism works.
- child-credential probe — assert the harness can resolve the key from its
  fallback env file. Report presence + source, never the value.
- last-run probe — read the runner's `state.json` counts; any non-`ok` = warn.
- scheduled-service probe — timer `active` + last error state from `systemctl`
  (or the job history), because a disabled timer is invisible otherwise.

## Wiring a new top-level payload key — four touch points

A new key is not done until all four land, or you get a silently blank card:

1. **collector.py** — produce the value inside the snapshot build. Wrap each probe
   in its own `try/except` and degrade that one entry to `warn` on exception; a
   probe must never kill the snapshot for every other panel.
2. **server.py** — add the pass-through line next to the other `snap.get(...)`
   entries in the payload dict.
3. **server.py (public build)** — if a public/redacted host is served, `pop()` the
   key there so internal probes do not leak. Shape: `pub.pop("fixes", None)`.
   `eco` and `fixes` both stay private; the public payload carries neither.
4. **web/index.html** — card markup + a render hook called from `renderAll()`,
   then bump the service-worker `CACHE` string (`infra-dash-vNN`). If you forget
   the bump, clients keep serving the precached old shell and the "fix" is
   invisible to the user no matter how correct the backend is.

## Gate pitfalls (both of these actually broke the gates)

- `verify/drive.py` counts rows by CSS class and asserts `rows == items` (e.g. 58
  rows = 58 services). New rows that reuse an existing label class (`.lbl`) break
  that invariant. Give new rows their own class names, then re-run the gates.
- Injected tab sections must toggle the `.hidden` class ONLY. Inline `display`
  styling gets stripped by the render path and blanks sibling tabs.
- Canonical gates, exit 0 = pass: `python3 verify/drive.py` and
  `python3 fleet/check_tab.py`. Run both AFTER any payload/markup change, plus a
  headless-browser DOM check (card visible, expected state classes present, zero
  console errors) — see the `headless-browser-automation` skill.

## Honesty rules

- A card that shows `3 of 4 green · 1 to watch` is a feature: the amber entry is
  the outstanding user action (e.g. bot not in the group). Do not hide it to make
  the panel look green.
- Never put a credential value in a probe detail. Presence + source path only.
- When a background verification run finishes late, its output can describe the
  PRE-fix state. Re-read `state.json` / the live endpoint before reporting; do not
  re-report a stale failing line as current.
