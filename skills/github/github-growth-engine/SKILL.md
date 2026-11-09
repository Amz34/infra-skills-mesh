---
name: github-growth-engine
description: "Use when boosting a GitHub account or its repos."
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [github, growth, ci, distribution, cron, awesome-list]
    related_skills: [github-repo-management, github-portfolio-polish, shared-tool-listicle-audit, cloudflare-pages-ops, cron-watchdog]
---

# GitHub Growth Engine

Turn a GitHub account from "good repos, zero audience" into a **self-maintaining, verifiable** profile: every repo wired with CI + a release, a live-verified curated list with a public dashboard, a backlink graph between repos and profile, and a distribution loop — all kept fresh by cron so it compounds without manual work.

## When to use

- User asks how to grow / "max out" their GitHub, or get stars and followers.
- A curated "awesome-*" list exists but is not being maintained or verified.
- Repos look good but lack releases, CI badges, or any cross-linking.
- Someone shares a big-star account (e.g. an `awesome-*` repo with 100k+ stars) and asks how to replicate it.

**Honest framing to give the user up front:** CI, releases, dashboards and backlinks are the *mechanics* — they make an account credible and discoverable. They do **not** manufacture stars or followers. Stars follow distribution (posts about a genuinely useful artifact) plus time. Never promise a star count.

## Assets (this VM)

| Path | Role |
|---|---|
| `~/ops/github/awesome-agent-infrastructure/` | the curated list repo (manifest.json = 9 categories × 15 entries = 135; `tools/emit_badge.py`; `.github/workflows/{refresh,verify}.yml`) |
| `~/ops/github/growth/verify_entries.py` | live-verifies every manifest entry via GraphQL batch + REST fallback → `status.json` |
| `~/ops/github/growth/pages_build.py` | builds `site/index.html` (dashboard) from manifest + status |
| `~/ops/github/growth/gh_boost.py` | audits all repos; `--apply` adds CI, first release, README backlinks, issues |
| `~/ops/github/growth/daily_refresh.sh` | verify + rebuild + deploy, **silent unless a verdict changed** |
| `~/ops/github/growth/growth_digest.py` | weekly metrics + gaps + assets digest |
| `~/ops/github/growth/weekly_subject.py` | picks the distribution subject (`--json`; exit 3 = nothing new). `--daily` = **per-new-repo policy**: an undistributed **own** clean-room repo from the trends ledger wins; **curated** (top free/OSS trending repo) only on Wednesdays UTC | |
| `~/ops/github/growth/dist_monitor.py` | cron **monitor** signature: `PENDING\|kind\|name\|url` while a subject awaits distribution, else a date-free `IDLE\|last=…\|n=…` line — idle days are byte-identical so the scheduler suppresses the agent run entirely (no LLM, no message). Wrapper: `~/.hermes/scripts/github_dist_monitor.sh` | |
| `~/ops/github/growth/publish_post.py` | publishes one copy JSON to the channels listed in `lane_config.json` `platforms` — that file is the **source of truth**, so adding/dropping a channel is a config edit, not a code edit (as of 2026-10-07: LinkedIn + Bluesky, X temporarily dropped; `--force-x` overrides deliberately). (Bluesky = `com.atproto.repo.createRecord` over stdlib urllib, creds `BSKY_HANDLE` / `BSKY_APP_PASSWORD` in vault space `hermes-default`, handle `amz34.bsky.social`). LinkedIn (`/rest/posts`, token `~/linkedin_token.json`, urn `urn:li:person:ZXkhXV9MAp`) **and** X (`HOME=~/\.hermes/profiles/invertio/home xurl --app invertio-x`, @AmzBuraq). Runs the content-integrity gate itself and hard-blocks on HIGH findings / X text >275 chars / Bluesky >300 chars, and requires a UTM-tagged `funnel_url` in the copy. `--selftest` proves the enabled channels' rails live (post + delete, nothing left public; channels absent from `platforms` are skipped and reported as `skipped`). `--dry-run` = gate + validation only | |
| `~/ops/github/growth/lane_config.json` | lane config: platforms, hashtag pool size (15) + per-platform caps, funnel base/campaign |
| `~/ops/github/growth/funnel_link.py` | prints the UTM-tagged CTA funnel link per platform (`--platform linkedin\|x\|bluesky [--target dashboard\|list\|repo]`) |
| `~/ops/github/growth/{post_state.json,outbox/,post_log.md}` | distribution state: history (repeat guard), pending copies, human log |
| `~/.hermes/scripts/github_growth_{daily.sh,digest.py}` | cron wrappers (cron `script` must live here) |

Crons: `github-growth-daily-refresh` (04:30 UTC daily, no_agent, silent-on-no-change), `github-growth-weekly-digest` (Mon 06:00 UTC, agent, metrics digest) and **`github-new-repo-distribution (daily, LI + Bluesky; X temporarily dropped)` (12:45 UTC daily = 15:45 KSA, agent, 91308771863f — runs ~80 min after `github-trends-originator`, so a freshly created repo is distributed the same day; behind monitor script `github_dist_monitor.sh`, so a tick with nothing to distribute costs no LLM and sends no message. It picks the subject, researches a 15-tag trending hashtag pool, builds a UTM funnel link, writes LinkedIn + Bluesky copy, gates it, publishes both, DMs the copy to Aamir; it reads `lane_config.json` at run time, so the channel list changes without editing the prompt)**.

## Workflow

1. **Audit** — `cd ~/ops/github/growth && /usr/bin/python3 gh_boost.py` (dry-run) and `/usr/bin/python3 growth_digest.py`. Report real numbers: followers, stars, per-repo gaps.
2. **Verify the list** — `verify_entries.py --selftest` then a full run; write `status.json` into the list repo.
3. **Fix mechanics** — `gh_boost.py --apply` (adds CI, a `v1.0.0` release with generated notes, README backlink, has_issues).
4. **Dashboard** — `pages_build.py`, then `env -u CLOUDFLARE_API_TOKEN npx wrangler@3 pages deploy site --project-name=awesome-agent-infra --commit-dirty=true`.
5. **Read back** — never trust a push: assert remote state (`gh api repos/<r>/releases --jq length`, `.../actions/workflows --jq .total_count`, badge content, homepage).
6. **Automate here** — wrapper in `~/.hermes/scripts/`, then `cronjob` create (`no_agent=True` + `script=` for the watchdog; agent job + `script=` for the digest).
7. **Distribute** — one post per **new repo** (Aamir 2026-10-07: distribution is tied to new repos, not a fixed weekly slot) about a concrete verifiable artifact. **Policy changed by Aamir 2026-10-06: it is now AUTO-POSTED** by the `github-new-repo-distribution (daily, LI + Bluesky; X temporarily dropped)` cron (12:45 UTC daily; the Wednesday run may post a curated repo, every other day posts only when an undistributed own repo exists, else the monitor suppresses the run) — he asked for full autonomy and gets a copy of every post in his Telegram DM. Channels per Aamir 2026-10-07: **LinkedIn + Bluesky**; X was **temporarily dropped** that day after its API credits ran out (HTTP 402 `credits-depleted`) — re-enable by adding `"x"` back to `platforms` in `lane_config.json`. The publisher auto-skips any channel missing from `platforms` and reports `posted_to`. Every post carries the GitHub URL **and** a UTM-tagged CTA funnel link (`funnel_link.py` → dashboard → repo/list), and each run researches a 15-item trending hashtag pool, publishing only the platform-capped slice (LinkedIn 5, Bluesky 3 — X 3 when it is in the lane) because hashtag stuffing cuts reach. The safety rails live in code, not in the prompt: `publish_post.py` re-runs `claim_integrity.py post` and refuses to publish on any HIGH finding, blocks X text over 275 chars and Bluesky over 300 chars, and requires the subject URL plus a UTM-tagged funnel_url. Curated (other people's) repos must credit the author and never read as ours. Only cite numbers that come from the repo API/lane state — never invent benchmarks, users or revenue.

## Pitfalls (all hit for real)

- **GitHub contents API needs `sha` when updating an existing file.** Without it the PUT fails and silent-wrapped calls report success. Always pass `-f sha=<sha>` from the GET, and print the return code.
- **Monitor signatures must be date-free.** `dist_monitor.py` feeds the scheduler's change detection: any timestamp in the signature makes every tick look changed and wakes the agent daily. Emit `PENDING|…` only while a subject is genuinely undistributed, and a constant `IDLE|last=…|n=…` line otherwise — then idle ticks are byte-identical and cost zero LLM.
- **Dedupe lives in `post_state.json`, not the picker.** `weekly_subject.py` never writes state; a subject stays available until `publish_post.py` records a successful publish, so a failed run is retried automatically on the next tick and a published repo is never picked twice.
- **Change detection must be semantic.** Timestamped status files make md5 differ every run, so a "silent unless changed" watchdog fires daily. Fingerprint the *verdict map* (`.verdict_fp` = sha256 of `{repo: verdict}`), not the file bytes.
- **GraphQL `{}` is not "gone".** A batch query returns `null` for a deleted/renamed repo but an empty dict in other cases; treat only `None` as GONE, and fall back to REST `repos/{full}` per entry so one dead repo cannot fail the batch.
- **cron `script` paths must be relative to `~/.hermes/scripts/`** — absolute paths are rejected. Use a wrapper there that `exec`s the real script.
- **`env -u CLOUDFLARE_API_TOKEN`** before `npx wrangler`, or the read-only env token shadows the OAuth session.
- **PATH for npx under cron** — wrappers must export `$HOME/.local/bin` (node/npx live there).
- **Brand isolation:** never add our profile/backlink to client-branded repos (`BRAND_SKIP` in `gh_boost.py`). CI and releases are neutral; README backlinks are not.
- **`git pull --rebase` conflicts** when repo-side CI commits `status.json` — resolve by resetting to `origin/<branch>` and regenerating locally, then push.
- **X API credits deplete (HTTP 402 `credits-depleted`).** Posting to X is metered; when the balance hits zero every call fails with 402 and the publisher used to burn 3 retries on it. `post_x` breaks immediately on 402 (no wasted retries). Aamir chose the drop on 2026-10-07: `"x"` is gone from `platforms` in `lane_config.json`, so the publisher skips it automatically (`--skip-x` is now implicit and the receipt reports `posted_to: ["linkedin", "bluesky"]`). To bring X back: top up the credits, re-add `"x"` to `platforms`, then `--selftest` to prove the rail. `--force-x` is a one-off override only — never use it in the cron.
- **Bluesky needs the app password from the vault, not env.** `bsky_creds()` reads `BSKY_HANDLE`/`BSKY_APP_PASSWORD` from env first, else `vault get hermes-default <KEY>` (space `hermes-default`). Verify a rail without leaving public content: `publish_post.py --selftest` posts then deletes on all three platforms.
- **LinkedIn carries the WHOLE 15-tag pool (Aamir 2026-10-07).** A 15-tag pool is researched per run and `lane_config.json` now has `hashtags.mode: "all15"` + `per_platform.linkedin: 15` — the 5-tag slice read as an *incomplete post*. Bluesky stays capped at 3 (300-char limit). Revert = `mode: "tuned"` + `linkedin: 5`. If `web_search` returns 0 results (search lane degraded), build the pool from REAL GitHub topic data (`gh api repos/<owner>/<repo>/topics --jq .names[]` over the shortlist in `~/ops/github/trends/latest_trends.json`) instead of inventing tags.
- **Fixing an already-published post:** `linkedin_edit_post.py --apply <date.json>` (in `~/ops/github/growth/`) sets the full 15-tag commentary on an existing share via `POST /rest/posts/{urn}` + `X-Restli-Method: PARTIAL_UPDATE` (returns 204). Read-back is limited: the publish token's GET is 403 (`ACCESS_DENIED …partnerApiPostsExternal.GET`), and the guest post page shows only the ~490-char preview — verify by read-back where possible, and say so honestly when not.
- **Content integrity:** any public post's numbers must come from `status.json`/the API, or be dropped. Run `~/ops/verify/claim_integrity.py` on the draft.

## Post-copy gate (2026-10-07)

LinkedIn copy must pass the **completeness gate** `~/ops/github/growth/li_gate.py`
before publishing — it is wired into `publish_post.py` and blocks the run
(rc 1, `problems`) when the text looks cut.

Two half posts went live on 2026-10-07, both from the same cause: `POST
/rest/posts` silently truncates `commentary` to ~473 chars **when the copy
contains an inline URL**, and returns 201 anyway. Hard rules for this lane:

- long copy (any length) must be **link-free**;
- a copy that carries a link must be **≤ ~450 chars including the URL** (the
  live fix post is 423 chars);
- after publishing, read the post back through the public embed
  (`li_embed_read.py <urn> --expect-file <copy>`) and only then call it done.
  `publish_post.py` now does this automatically and flags `TRUNCATED`.

Full recipe + incident timeline: skill `linkedin-api-posting`, section
"Publish gate + verification".

## Verification checklist

- [ ] `verify_entries.py --selftest` exits 0 (its controls include an intentional must-fail case).
- [ ] Full verify: `checked == total entries`, and the `NON_LIVE` count is reported explicitly (STALE != dead; say which).
- [ ] A live negative control (real dead/archived repo) is classified GONE/ARCHIVED, not LIVE.
- [ ] Dashboard URL returns HTTP 200 with the expected link count.
- [ ] Remote read-back of every write (release count, workflow count, badge JSON, homepage).
- [ ] Watchdog proven **both** ways: silent on no change, reports on a simulated verdict change.
