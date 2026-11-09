# Relocating / killing a dashboard surface — the text sweep (proven 2026-09-10)

Moving a card, folding a tab into another view, or deleting a screen is **not** an `index.html` edit.
The same object is described in ~9 other places; leave one and the next session re-adds the thing you
just removed (or a gate keeps asserting the old shape). Do the code move, then sweep every text site,
then re-grep for the old name.

## Text sites to sweep (invertio infra-dashboard)

| # | Site | What lives there |
|---|------|------------------|
| 1 | `web/index.html` | markup + inline JS + comments (may appear twice: page code **and** an injected `<script>` copy) |
| 2 | `web/sw.js` | `CACHE` version + the comment describing what the release contains |
| 3 | `collector.py` | the `fixes`/card text payload that the dashboard renders as data |
| 4 | `server.py` | docstrings / endpoint comments (`/fleet.json`, payload keys) |
| 5 | `verify/features/<feature>.md` | the feature doc — **rename the file too** when the surface's role changed (`fleet-tab.md` → `fleet-block.md`) |
| 6 | `verify/features/README.md` | the feature table row (name + one-line description) |
| 7 | `gate/check.sh`, `gate/*.sh` | `run_step "…"` labels |
| 8 | `gate/*.md`, `fleet/README.md` | gate/console docs |
| 9 | `fleet/runner.py`, `fleet/wire_dashboard.py` | status strings, injected-script comments |

Also probe for the surface's own ids: after a removal, `data-v="<id>"`, `id="<id>Sec"`, and the nav
button must all be absent.

## Method that worked

1. Back up first: `cp -a <file> backups/<file>.$(date +%Y%m%d-%H%M%S)` for each file you will touch.
2. Write a **sweep script** with `write_file` (e.g. `/tmp/textpass.py`) holding the replacement pairs
   and a file list, and **assert** on the old text before writing — never `sed -i` across a repo
   blind.
3. Run it with output redirected, then **read the file back**:
   `python3 /tmp/textpass.py > /tmp/tp.txt 2>&1; echo "exit=$?"` → `read_file /tmp/tp.txt`.
   Print a per-file edit count so a no-op file is visible (a file that reports 0 edits is either
   already correct or was missed — check it).
4. Verify: `grep -rn "<old name>" --include=... . | grep -v roadmap/` → expect zero hits outside
   frozen `roadmap/` notes and `verify/evidence/` artifacts (those are history and must keep the old
   wording).
5. Re-run the gates + JS syntax check, then the CDP QA (`references/qa-render-checks.md`).

## Pitfalls

- **Long compound terminal one-liners can come back truncated** (you see `exit 0, 1 lines output`, or
  your own command echoed with `...[truncated]`). Keep command lines short, redirect to a file, and
  `read_file` it; put anything longer than ~2 commands into a script file instead.
- After a rename, any doc/gate that referenced the old filename silently passes while asserting
  nothing (or worse, the gate file ends up in the wrong directory and never runs) — grep the old
  filename explicitly, not just the old label.
- `collector.py` card text is **data**, not UI: changing it requires a collector run
  (`python3 collector.py`) before the dashboard shows it; `server.py` changes need
  `sudo systemctl restart infra-dash.service`.
- Bump `sw.js` `CACHE` for the `index.html` edit, and say "hard refresh" in the report.
