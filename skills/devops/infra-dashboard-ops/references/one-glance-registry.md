# One-glance registry: data model, health semantics, crash-proof & QA (2026-09-16)

Whole-infra register for `clients/invertio/infra-dashboard/`: every project, website,
schedule, cron, service, MCP on the VM in one view (`#glance`), plus a standalone
offline artifact. This file is the detail behind the SKILL.md section of the same name.

## Files

| File | Role |
|---|---|
| `registry.py` (~27 KB) | **single source of truth**; merges curated RAG knowledge + live probes + `autonomy_audit.py --json` → writes `registry.json` |
| `registry.json` | built snapshot (rebuild: `python3 registry.py` or `registry.build(force=True)`) |
| `web/glance-core.js` | pure renderer `(root, data)` — used by BOTH the live view and the artifact |
| `web/glance.js` | live fetcher/refresher; exposes `window.GlanceMount` |
| `web/one-glance.html` | generated standalone artifact (single file, no deps, offline-safe) |
| `verify/one_glance.py` | artifact generator (embeds snapshot + `glance-core.js`) |
| `verify/registry_qa.py` | self-QA, ~46 checks |
| `server.py` | `GET /registry.json` (private hosts only) + `/services.json` injects `crash_prone` / `delete_allowed` |

Endpoints: `GET /registry.json`, `GET /one-glance.html` (~200 KB), `GET /services.json`.
All private-host-only — the public host (`aslove7…`) returns an empty stub.

## Snapshot shape (2026-09-16 final)

`projects=90` (28 curated `SEED` + 62 workspace dirs kept visible as `untracked`),
`websites=8/10 live`, `services=131/269 up`, `crash_prone=1`, `delete_blocked=101`,
`schedules=120 declared + 35 systemd timers (11 ours, 24 OS)`,
`hermes_crons=82 (47 enabled, 5 profiles)`, `raw cron lines=10`, `MCP servers=5`.

Honesty rule Aamir cares about: nothing is hidden. Unregistered workspace dirs stay in
the table as `untracked`; a dead project stays as `down`, not deleted from the view.

## project health derivation (get this right — it produced false "down" rows)

```python
lu  = [u for u in p["units"] if u.get("long_running")]          # load-bearing only
bad = [u for u in p["units"] if u.get("crash_prone")
       or u.get("active") in ("failed", "activating")]
ups = [u for u in lu if u.get("active") == "active"]
code = p.get("http")
bad_code = isinstance(code, int) and (code == 0 or code >= 400)
if code in (401, 403):                                          # auth-protected = ALIVE
    bad_code = False
health = "long"  # then: bad -> "down"; bad_code -> "degraded"; ups<len(lu) -> "degraded"
```

Rules that matter:

- **`401/403` from an HTTP probe means the site is UP** (private/auth-gated), never
  "degraded". Only `0` (unreachable/DNS) or `>=400` (other than 401/403) degrades.
- **oneshot / wave units are not load-bearing**: `long_running` = non-oneshot AND
  (`active == "active"` OR (`inactive` AND `Result in ("", "success")`)). Without this,
  `sanad-backup.service` / `*-wave.service` types flip healthy projects to `down`.
- **`p["units"]` projection must include `long_running` (+ `unit_type`, `result`).**
  If the projection omits it, `u.get("long_running")` is `None` → `lu` is empty → every
  project reads `0/N` and looks degraded even though the units are active.
- Never leave the health block nested under an earlier `if p["status"] == "blocked":`
  branch: the list you compute there leaks into the next project (`lu`/`ups` from the
  previous iteration) → phantom "down" rows for the first few projects. Verify
  indentation with a solo `read_file` of that region before rebuilding.

## crash-prone detection (drives no-delete + bounded retries)

Crash-prone when ANY of: `SubState == "auto-restart"`, `Result == "start-limit-hit"`,
or (`ActiveState == "failed"` AND `NRestarts > 0`). Exclude oneshot `exited` units.

- `crash_flags()` is injected into `/services.json` per unit; the UI hides Remove when
  `u.protected || u.crash_prone`, and `controls.py` refuses anyway + audits the attempt.
- Real case: `munder-app.service` was a 360-restart flap loop whose source dir
  (`~/munder-difflin/src`) is gone → `203/EXEC`. Correct handling is *bounded* retries
  (`StartLimitIntervalSec`/`Burst`) + `down` + no-delete, **not** uninstall. Say plainly
  "source folder gayab hai, isliye theek nahi kar sakta" instead of hiding the row.

## user-scope units need the user bus env

`systemctl --user show <unit>` FAILS from a plain script (no `XDG_RUNTIME_DIR`) and the
unit then looks absent → missed crash detection. Every helper needs an env hook:

```python
sh(cmd, t, env={"XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}"})
```

Symptom of getting this wrong: munder-app (a user unit) reported fine/green while the
host said `failed, NRestarts=5`.

## caching trap: registry.py edits are NOT live until the service restarts

`server.py` keeps the built registry in memory. After editing `registry.py`, a rebuild
updates `registry.json` on disk but `GET /registry.json` still serves the OLD build —
you will see stale health chips in the browser and in screenshots and think the fix
failed. Always: `sudo -n systemctl restart infra-dash.service`, then re-curl the
endpoint and check `Counter(p['health'])` before shooting evidence. The live UI polls
every 20 s; the deep link must be registered in `const VIEWS=[...]` (`data-v="glance"`,
section `#glanceSec`) or `#glance` silently opens Panels.

## CSS / renderer traps (both hit here)

- The dashboard defines a GLOBAL `.chip` (large gradient pill). A new renderer reusing
  `.chip` inherits it → overlapping pills and broken columns. Namespace everything
  (`#glanceSec .gchip`, `.hchip`); never reuse global class names (`.chip`, `.mono`).
- The standalone artifact loads CSS scoped to `#glanceSec`; if the generator writes
  `id="glanceRoot"` the file renders **unstyled** from `file://`. Ids must match.
- Verify a render change from a real DOM, not the source: `google-chrome --headless=new
  --dump-dom <url>` then count rows/chips in Python (slicing between `glanceSec` and the
  first `<script` hits the CSS rule first — anchor on a table/row marker instead).

## QA (all green 2026-09-16)

```bash
python3 verify/one_glance.py      # regenerate artifact + evidence copy
python3 verify/registry_qa.py     # 46/46  (counts vs live host: crons, timers, projects,
                                  #          endpoints, artifact render, crash-proof policy)
python3 verify/svc_qa.py          # 21/21
python3 verify/parity_services.py # 12/12 — asserts served dash-build tag (v58) + ?v=N bumps
python3 verify/drive.py           # PASS 59 rows
```

Bugs the self-QA caught — worth re-checking after any registry change: global `.chip`
leak; unstyled artifact (`glanceRoot` vs `glanceSec`); false "down" from oneshot units;
stale served cache; timers undercount (10 in registry vs 35 on host → `collect_timers()`
for every systemd timer, ours vs OS); `#glance` deep link opening Panels.

Evidence: `verify/evidence/2026-09-16-one-glance-view.png`,
`2026-09-16-one-glance-artifact.png`, `one-glance-2026-09-16.html`.

## Asset-edit checklist (unchanged, still bites)

1. bump `?v=N` on every changed JS asset (`glance-core.js`, `glance.js`,
   `services-control.js`) **in index.html**;
2. bump `<meta name="dash-build" content="vN">`;
3. bump the same tag asserted inside `verify/parity_services.py`;
4. `node --check` every touched JS;
5. restart the service if `registry.py`/`server.py` changed;
6. re-run the four suites above before reporting.
