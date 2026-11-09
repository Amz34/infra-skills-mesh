# Quota-budget guard rails: fossil alarms, alert-level design, verification harness

Case: Cloudflare KV free tier (1,000 writes + 1,000 deletes + 1,000 lists + 100,000 reads per
**account** per UTC day, shared by every Worker and Pages Function). Sep 2026, 7 Workers on one
account. Treated here as the general pattern for ANY threshold/quota watchdog (API quota, SMS
quota, storage, rate limits, cost budgets).

## 1. Spend-based alerting cries wolf after a fix ("fossil alarm")

The guard projected end-of-day as `used / day_fraction`. Arithmetically fine, semantically wrong:
after the noisy producer is fixed, the writes burnt BEFORE the fix stay in the counter, so the
fixed system still looks like the broken one.

Live sequence:
- 04:40 UTC — producer fixed + redeployed (12 writes/run → 0 in steady state)
- 19:54 UTC — `WARN 709/1000 used (71%), projected 945/day (95%)` → Telegram alert, user had to
  investigate an already-fixed problem
- truth: ~26 writes in the previous 14.7 h (~2/h) → the day would end at ~716 → **no risk at all**

Rule: **alert on exhaustion risk, not on how much of the period is spent.** Also demote
"spent a lot but the current rate is sustainable" to a log-only NOTE — visible in logs, never a
push notification.

## 2. Alert-level design that survives a fix

```
CRITICAL : actual >= 85%  or  recent-slope projection >= 95%   -> push
WARN     : recent-slope projection >= 85%                      -> push
NOTE     : actual >= 60% but slope is sustainable              -> log line only
```
Dedup: same level ≤1 per 6 h, escalation immediate, de-escalation sends (a warning after a
critical is information, not noise). `--dry-run` must print and return **before** touching state.

## 3. Projection algorithm (never invent a rate)

Raw counters are appended to the state file on every live run as `_samples` (prune to ~34
entries; a 7-day history trim must exclude keys starting with `_`).

```
same-day samples exist?
  newest sample aged [20 min, 6 h] -> rate = (used_now - used_then)/hours
                                      projected = used_now + rate * hours_left
  none inside that window          -> projected = None   (unknown; do not extrapolate)
no same-day samples at all
  day_fraction >= 0.25             -> projected = used / day_fraction   (conservative)
  else                             -> projected = None
```
- Clamp negatives to 0 so a counter reset at the day boundary never yields a negative rate.
- The cumulative branch is allowed **only** when the period has no samples at all. If samples
  exist but none qualifies (too fresh, too stale), cumulative re-creates §1's false alarm.
- Too-fresh = no rate yet; too-stale may predate a deploy. Both mean "unknown", and the
  actual-based thresholds (60/85%) still catch a genuine runaway.

## 4. Root-cause fixes cost the producer nothing (do this before tuning thresholds)

The producer wrote 12 keys per run × 288 runs/day = 3,456 writes/day (346% of the budget).
Fixes, in order of value:
1. **Diff before write** — `material(state)` = `ok|fails|alerted|status|has-error`; never include
   ms/timestamps/volatile error strings. Steady state = 0 writes.
2. **Cap counters** (`fails = min(prev+1, THRESHOLD)`) or a permanently dead target writes every run.
3. **One heartbeat key, ≤1/hour**, written early when the down-count changes.
4. **Never let a write failure stop the run** — wrap in `safePut()` so a 429 cannot silence alerting.
5. **Drop write-only keys.** A pageview tracker wrote a per-day key `d:<date>` that nothing read
   (`all.days[date]` already held the counts) → removing it halved pageview cost (2 puts → 1).
   Grep the key's consumers before deleting a write.

## 5. Deleting keys is NOT a mitigation

Deletes have their **own** allowance and refund nothing to the write counter; there is no "spam"
to clean in a healthy monitor (11 target keys + heartbeat is normal). Edge-cache purges are
unrelated to storage quota. Tell the user this explicitly — "can we delete junk to fix it?" is a
natural but wrong question. The only lever is the producing code.

## 6. Verification harness for a guard change (kept as permanent tests)

1. **Split the decision into a pure function** (`evaluate(counters, by_ns, now, samples)`,
   `project(action, used, samples, now)`). A level decision buried inside `guard()` is untestable.
2. Point the state path at a tempfile and **stub the push sender** — the harness must never
   send a real alert.
3. Fake the clock by subclassing `datetime` and assigning it onto the module
   (`mod.datetime = FakeDateTime`) — every `datetime.now()` in the module then follows it.
4. Prove "dry-run persists nothing" with an **invariant trap**, not a file hash: monkeypatch
   `save_state` to count/raise, call `guard(..., dry_run=True)`, assert 0 hits. A hash comparison
   is invalid whenever a cron writes the same state file concurrently.
5. Run the CLI read-only against the live source once and assert the output contains no
   WARN/CRITICAL — that is the end-to-end proof the false alarm is gone.
6. Check the fix is actually DEPLOYED: compare the local file mtime with the deployed build
   timestamp (deployed older than the fix → not live yet).

Harness bugs cost two re-runs in the case study — **when a check fails, re-verify the check
before touching the code**: (a) a scenario whose step order ended in a *suppressed* alert, so the
code path under test never ran; (b) a restore-before-assert ordering bug. Also
`subprocess.run(...)` without `capture_output=True` returns `stdout=None` → `TypeError`.

## 7. Regression cron for the guard itself

`~/ops/scripts/kv_tests.sh` runs the test files, prints nothing on success, and on failure prints
the failing output and exits 1. Cron entrypoints must be REAL files in `~/.hermes/scripts/`, so a
one-line `exec` wrapper lives there. Registered as a script-only (`no_agent`) cron at
`30 20 * * *`: empty stdout = silent tick, non-empty = delivered verbatim. Alert *logic* is code
too — give it the same silent-on-pass watchdog treatment as the service it watches.

## 8. Baseline evidence (Sep 2026)

```
t0 19:58:21Z write=711   t1 20:18:23Z write=711   -> delta 0 over 20 min
(old code: 12 writes/run x 3 runs/15 min = ~36 writes in the same window)
projected end-of-day 711/1000 (71.1%) — 289 writes of headroom
producer deployed modified_on 2026-09-17T04:41:32Z vs local fix mtime 04:38:54 -> fix live
producer unit tests 9/9 pass
```
