---
name: project-state-audit
description: Use when auditing a project's state and next steps.
version: 1.0.0
author: hermes-curator
license: CC-BY-4.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [audit, status-report, git-history, verification, next-steps, monetization]
---

# Project state audit: current state → last update → ranked next steps

## When to Use

- "Expertly audit <project>", "what's the status of X", "what was the last update?".
- "What should we do next on this?", "is this ready to ship / sell / monetize?".
- Before writing a decision record, a weekly-review item, or a client-facing progress note about
  an existing codebase.

## Deliverable

A short, numeric, honest report — the value is in the GAPS section, not in restating what the
README claims.

## Step 1 — Last update: read git, never memory or brain docs

```bash
git log --date=short --pretty="%h %ad %s" | head -22      # timeline
git status --short | head -20                             # UNCOMMITTED work is often the real latest
git log -1 --stat --date=iso --pretty="%H%n%ad%n%s%n%b" | head -40
```
Report hash + date + one-line subject of the newest commit, AND name any uncommitted artifacts —
an uncommitted audit doc or half-finished feature is part of "last update". Get the same evidence
from every sibling repo/variant directory (public mirror, demo, deploy copy) before answering.

## Step 2 — Live state, not documentation

Docs and reports describe intent. Probe the running thing and quote numbers:

- health/status endpoints (`curl -s -m 8 -o /dev/null -w "%{http_code}"`), latency percentiles
- the counts that actually matter: configured inputs, successful inputs, events produced, verdicts
  received (e.g. cameras connected, alerts fired, operator feedback judged)
- `systemctl --user is-active <units>` / process state for the services and tunnels
- the real test suite through the project's OWN interpreter — `venv/bin/python -m pytest tests -q | tail -3`
  — a bare runner may not resolve deps and a doc's claimed count is not evidence. Quote the count
  you actually got, or say the suite was not run.

## Step 3 — Separate "shipped" from "ever exercised"

The highest-signal finding in most audits: a feature is merged but has never touched reality.
Look for config sources pointing at `localhost`/test stubs, zero real inputs, zero user verdicts,
reconnect counters. Say plainly: "path exists, has never seen a real <camera/tenant/customer>".
This single distinction changes the whole roadmap and is usually missing from the project's own
docs.

## Step 4 — Gaps list (4–6, each with evidence)

Standard candidate set for a near-shippable product: licence/legal gate, deployment vs demo gap,
real-data validation, hardening (stable origin, auth, retention), privacy/regulatory doc,
monitoring/rollback. One line of evidence each — no adjectives without a number.

## Step 5 — Rank next actions by what they UNBLOCK

Sequence that repeatedly holds: clear the legal/licence blocker → ship the free lead layer →
validate on real data → then price/monetize. Give 3–5 actions in order, each with the reason it
comes now and a rough effort hint. Then, and only then, the monetization recommendation.

## Monetization advice = buyer type + channel fit + counterparty cost

Never derive pricing/GTM from the tech stack alone. State: who pays, how they discover the
product, what the channel skims (store cuts, marketplace fees, ad spend), and whether the
counterparty fits local invoicing/regulation. Then give price bands the project's own decision
docs already settled, rather than inventing new numbers.

## Reporting rules for this user

- Chat reply: concise Hinglish, address as "bhai"/"aap" (never "tu"), lead with the verdict.
- Any produced FILE (report, PDF, xlsx, deck, code) is pure English, regardless of chat language.
- Numbers over adjectives; label what you verified live vs what came from a doc.
- Include a live/installable link when the project has one — and caveat ephemeral origins
  (quick-tunnel URLs rotate; say so and tell them to rotate the access code before sharing).
- NEVER fabricate test results, metrics, hashes, or endpoint responses. If a command's output was
  truncated or unreadable, re-run it and capture it; "exit 0" alone is not evidence.
- Close with one concrete offer of the next action ("bolen to main X kar dun?"), not a menu of five.

## Pitfalls

- Answering "last update" from the brain/knowledge base or from memory instead of git — brain docs
  lag the repo and hide uncommitted work.
- Quoting a project's own REPORT.md numbers as if verified. Docs are leads; endpoints are proof.
- Treating truncated/empty tool output as a negative finding ("file missing"). Re-run and capture.
- Recommending distribution or pricing while a licence/deployment blocker is still open — the
  client-visible advice becomes worthless the moment the blocker surfaces.
- Over-sympathising with the project's own narrative (roadmaps, "P0 shipped") instead of reporting
  the gap between merged and exercised.

## Support files

- `templates/audit-report.md` — skeleton for the written audit (state / last update / gaps /
  ranked actions / monetization verdict).
