# QA invariant design — hard-won rules (2026-09-21)

Four suites (`svc_qa`, `parity`, `registry_qa`, `spend_qa`) went from 1/4 green to 4/4 by fixing
**check design**, not by relaxing assertions. Every failure below was a check that could not
distinguish "healthy box" from "broken box".

## Rules

1. **Never anchor a baseline in `/tmp`.** `parity_services.py` read `/tmp/d1.json`; the file had
   never been written and `/tmp` is wiped on reboot, so the suite died before running a single
   check (silently — a crashed suite still reports "1/4 suites green"). Keep baselines in
   `verify/fixtures/*.json` and self-heal (create from current state on first run).
2. **Never pin a live count.** `len(units) == 269` failed once the fleet grew to 279. Assert
   shape + self-consistency instead (`len(units) >= 250 and counts.all == len(units)`).
3. **Never assert live state that is legitimately zero on a healthy box.** "crash-prone detected
   >= 1" fails when nothing is crash-looping. Assert the *ability* (`crash_prone` present on
   every unit) plus the real invariant (no crash-prone unit may be deleted).
4. **A timestamp anchor must post-date the last real edit.** `find web/index_public.html
   -newermt '2026-09-16 14:00'` flagged a legitimate 2026-09-18 edit.
5. **Never pin a build tag in a check.** "build tag v61 served" goes stale on every bump. Compare
   the served tag against `web/index.html` on disk.
6. **Invalidate caches on mutation, and do not read through a cache in QA.** `server.py` cached
   `/services.json` for 60 s with no invalidation on POST, so star/fixture QA reads saw the
   pre-action snapshot (and users saw a stale star for up to a minute). Fix: drop the cache when
   `controls.action()` returns `ok`, and let QA read the fresh state.
7. **Every nav entry in `VIEWS` needs a real button.** `glance` was in `VIEWS` + scripts + section
   markup but had no `data-v="glance"` button, so the One-glance register was reachable only by
   typing the deep link. QA caught it; the nav binding is generic (`closest("[data-v]")` +
   `#viewToggle button` toggle loop), so adding the button was enough.

8. **A check script must not depend on the caller's environment.** The Layer-3 verifier runs
   deterministic checks with a *bare* env (no `PATH`): `shutil.which("ollama")` returned None, the
   check crashed, and the suite went red while proving nothing about the box. Normalize `PATH` at
   import, resolve binaries absolutely, and print an explicit `skip:` label when a CLI genuinely
   cannot run — an unverifiable check must never render as a pass.
9. **A fixture created outside the API is not a mutation, so caches are not invalidated.** `svc_qa`
   created a systemd unit and then read `/services.json`; the 60 s cache served the pre-fixture list
   (21/21 on one run, 20/21 on the next). Fix: loopback-only `?fresh=1` on read endpoints
   (`if "fresh=1" in self.path` → rebuild under the same lock) and QA reads use it; the public-host
   stub returns *before* the query is honoured, so nothing leaks.
10. **Flaky ≠ broken — run the suite 3× before diagnosing.** 21/21 then 20/21 is a race (cache/TTL);
    a stable 20/21 is a real defect. Here the "regression" turned out to be a *second, real* defect
    (a service with a legitimately unbounded swap ceiling) that only surfaced once the first was fixed.

## Debugging a red wrapper (and a truncated-looking report)

`daily_selfqa.sh` prints only a **tail** of the verifier JSON, so a failure can look like truncated
output. Don't guess — run the canonical verifier directly and read the full JSON:

```bash
python3 ~/ops/verify/independent_check.py --mode deterministic \
  --checks ~/ops/verify/checks-selfqa.json --label manual
# the failing check names itself: `memory containment invariants hold | exit=1 want=0`
```

Then reproduce under the verifier's *actual* conditions before touching the check:

```bash
env -i /usr/bin/python3 ~/ops/scripts/mem_containment_check.py     # bare env → reproduces it
```

## What "verified" must look like

Report **rc per gate plus the ledger line**, never a claim: `run_qa.py` rc + `qa-ledger.jsonl`
(`svc_qa 21/21`, `parity 12/12`, `registry 60/60`, `drive ok=True`), `daily_selfqa.sh` rc +
`verify-ledger.jsonl` verdict, `kv_tests.sh` rc, containment-checker rc, and the watchdog's line
count (0 = silent). There is no `Makefile` in this workspace — those commands ARE the canonical
entry points.

## Verify a UI fix with the real page, not with the file

```bash
google-chrome --headless=new --disable-gpu --no-sandbox --virtual-time-budget=6000 \
  --dump-dom http://127.0.0.1:8765/ > /tmp/dom.html
grep -oE 'data-v="[a-z]+"' /tmp/dom.html | sort | uniq -c     # nav really rendered
grep -oE 'name="dash-build" content="[^"]+"' /tmp/dom.html     # served build tag
```
(The browser-harness daemon is blocked for 127.0.0.1 on this VM — drive Chrome directly, same as
`verify/drive.py` does.)

## Resource-containment invariants (same philosophy, memory instead of HTTP)

`~/ops/scripts/mem_containment_check.py` (wired into Layer-3 `checks-selfqa.json`) asserts
guarantees, not readings: ollama slice swap ceiling present, no memory-heavy service with
unbounded swap, user manager ceiling, keep-alive ceiling, no oversize local model. It stays
green on a busy box and fails the moment a ceiling is removed. Companion rules in
`~/ops/resource_watchdog.sh`: a ceiling being *used* is not an alert (`llmcgroup` only fires at
ceiling AND low MemAvailable), and `zramfull` needs disk swap > 2 GB before it means anything.
