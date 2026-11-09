# Adding a guarded mutating control surface to a read-only dashboard

Pattern proven on the private infra dashboard (2026-09-16): a "Services · active list
& control" view sitting beside the read-only views, with star / start / stop / restart /
remove per unit (systemd user+system, docker containers).

## Shape

- One new view beside the existing monitoring views; deep link via the hash (`#svc`).
- **Pitfall (silent failure):** hash routing only honours view ids that are registered in
  the front-end `VIEWS=[...]` array. Miss that and `#newview` silently opens the first
  view — looks like "the feature didn't ship". Add the id in the same commit.
- Backend split: `controls.py` is the ONLY writer (enumerate + mutate in one module),
  exposed as `GET /services.json` (read) and `POST /svc/action` (mutate).
- Response schema must carry everything the UI renders: `unit, scope, active, sub,
  running, enabled, protected, starred`. Keep `running` a real boolean — a UI that
  derives the Stop/Start button from a field the API never sends renders wrong buttons
  forever and no screenshot at 50% scale will tell you.

## Guards — defence in depth, never "the UI hides it"

1. **Private host only.** The public host gets an empty stub for the JSON endpoint and
   the section is NOT added to the public HTML file. Keep a parity test asserting the
   public file is byte-untouched, otherwise a future CSS/JS refactor leaks the controls.
2. **Custom header + same-origin + explicit `confirm` boolean** on every mutation; reject
   otherwise (a plain curl or a CSRF form post must fail).
3. **Unit-name regex allowlist before any subprocess call** — never interpolate a
   client-supplied string into a shell command.
4. **Protected list = built-in regexes + operator file + the autonomy registry's
   `critical_services`.** The registry is the source of truth for "never touch"
   (gateways, edge proxy, dashboard itself, ssh, container runtime, VPN, the survivor
   project, backup/DR). Adding a critical unit to code only — not to the registry —
   is a governance bug.
5. **Kill switch file** (e.g. `~/.config/infra-dash/control-enabled`): absent ⇒ the whole
   surface is read-only, and the API reports `armed:false` so the UI can grey the buttons
   truthfully instead of letting the click 403.
6. **Audit log**: one JSON line per accepted action (ts, unit, scope, action, result, ok)
   so "who stopped that service at 3am" is answerable.

## Mutation semantics

- `stop` / `start` / `restart`: plain unit verbs. Docker containers are NOT systemd units —
  branch on scope, never run `systemctl` on a container name.
- `remove` means **stop + disable**, never `rm` the unit file: systemd `disable --now`,
  docker `--restart=no`. The whole point is that any action is reversible from the same UI.
- Static units (`systemd` units with no `[Install]`) **cannot be disabled**. Say
  "stopped; nothing to disable (unit is static)" — do not report "disabled", and do not
  report failure either. Honest status text beats a clean-looking lie.

## UI details that QA caught

- Keep the pin/star control in the FIRST cell and the action buttons in the LAST cell.
  Putting the button cluster in the first cell (because the star column header is empty)
  renders every row as `Stop Restart Remove | name | scope ...` — only a DOM dump reveals it.
- Bump the asset cache-buster (`?v=N` on the JS) AND a build-tag meta in the HTML on every
  asset edit; verify the served build tag, not your local file.

## Verification (all three must exit 0 before claiming done)

- `verify/svc_qa.py` — control-plane suite: protected-unit refusal, public-host refusal,
  missing-header refusal, malformed unit name, unknown action, full
  star → stop → start → remove lifecycle against a THROWAWAY unit, audit trail written,
  `armed` flag reflected, public stub empty.
- `verify/parity_services.py` — old endpoints still key/byte-stable, `/data.json` /
  `/history.json` / `/fleet.json` unchanged, 404 path unchanged, public HTML untouched,
  build tag served.
- the project's own gate (`verify/drive.py`) — still exits 0 with its row count intact.
- Keep both suites committed in the repo (not `/tmp`) so the next change re-runs them.

## Governance hook

Declare the new surface in the autonomy registry before shipping
(`~/ops/observability/autonomy.json → surfaces`): kind, level, effect, `gate_required`,
why, and the reversal path. A control surface that can stop workloads is not a UI tweak.

## Prod-change protocol note

Internal (non-client) dashboards: when the user asks for the feature in-session and the
change is reversible, apply it AND prove parity afterwards — then state plainly that the
staging-first protocol was skipped, with the one-command reversal (backup path + kill
switch). Do not silently ship, do not silently stall.
