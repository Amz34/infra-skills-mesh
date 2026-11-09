# Project audit — <project name>

**Audit date:** YYYY-MM-DD · **Auditor:** Hermes · **Scope:** <repo/path, deployed services>

## 1. Verdict (one paragraph, lead with the answer)

<Is it ready to ship / sell? What is the single biggest blocker? What is the recommended next move?>

## 2. Last update — evidence from git

| Item | Value |
|---|---|
| Newest commit | `<hash>` — `YYYY-MM-DD HH:MM TZ` — <subject> |
| Functional feature commit | `<hash>` — <subject> |
| Uncommitted work | <files, or "none"> |
| Sibling repos checked | <public mirror, demo, deploy copy — with their newest commit> |

## 3. Live state — probed, not read from docs

| Check | Command / endpoint | Observed |
|---|---|---|
| Service active | `systemctl --user is-active <units>` | |
| Health | `curl -s -o /dev/null -w "%{http_code}"` | |
| Latency | health/status payload | p50 / p95 |
| Real inputs | configured sources actually connected | |
| Output produced | alerts/events generated | |
| Human feedback | verdicts received / total | |
| Test suite | `venv/bin/python -m pytest tests -q` | N passed, M failed |

## 4. Shipped vs ever-exercised

<Which features are merged but have never run against a real input — config pointing at
localhost/test stubs, zero real tenants, zero verdicts? State it plainly.>

## 5. Gaps (evidence per line)

1. **<licence/legal>** — <one line of evidence>
2. **<deployment / demo not shipped>** — <evidence>
3. **<real-data validation>** — <evidence>
4. **<hardening: stable origin, auth, retention>** — <evidence>
5. **<privacy / regulatory doc>** — <evidence>

## 6. Ranked next actions

| # | Action | Why now (what it unblocks) | Effort |
|---|---|---|---|
| 1 | | | |
| 2 | | | |

## 7. Monetization verdict

- **Buyer:** <who pays>
- **Channel fit:** <how they discover it; what the channel skims>
- **Verdict:** <e.g. public app-store listing is the wrong rail — reasons>
- **Price bands (from the project's own decision docs):** <numbers, not inventions>

## 8. Deliverable notes

- Live/installable link supplied: <URL> — <ephemeral? rotate access code before sharing?>
- What the user asked to do next: <one concrete offered action>
