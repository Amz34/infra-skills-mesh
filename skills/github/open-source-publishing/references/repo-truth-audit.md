# Repo truth audit — numbers, behaviour, assets, cross-links

Run before a public push and again after any change that moves a number or a behaviour.
Proven 2026-09-17 on `Amz34/agent-operating-model` (router fix + README/screenshot refresh)
and its `selfhosted-agent-stack` sibling.

## 0. Fresh-clone QA (stranger's path) — always the first gate

`scripts/qa-fresh-repo.sh <git-url-or-local-path> [out-dir]`

- Clones into `/tmp`, runs the suite the README tells a stranger to run, prints the clone SHA +
  a compact PASS/FAIL table, hard-fails on tracked secrets, logs everything.
- **Pass a LOCAL path to clean-room the commit you have not pushed yet** —
  `git clone /home/ubuntu/publish/<repo>` works, so the same script audits both the published
  revision and your fix. Testing only the working tree proves nothing: a stranger cannot see it.
- Record the clone SHA in the log so the QA claim is tied to a commit
  (`### CLONE: ba430c2 fix(router): match signals on token edges`).
- A fresh clone also catches files that exist only locally.

## 1. Number audit

Every count that appears twice must agree. Find them, then re-run the command that produces each.

```bash
grep -rnE "badge/|[0-9]+ (passing|tests|seats|planes|%|ms)|TOTAL|coverage" \
  README.md CHANGELOG.md pyproject.toml .github/workflows/*.yml | head -40
python -m pytest -q | tail -3                                   # real test count
python -m pytest --cov=<pkg> --cov-report=term-missing -q | grep TOTAL   # real coverage
python -m ruff check .                                          # lint claim
```

Places a number hides: badge URL, README prose + tables, CHANGELOG blurb, `pyproject` version,
the rendered proof screenshot, the launch post/PH copy, cron digest text. Move **all of them in
one commit** — a screenshot reading `33 passed` beside a badge saying 37 is worse than either
stale number alone. Bump `version` + add the CHANGELOG entry in the same commit as the code fix.

## 2. Behaviour audit

- Run every README example verbatim and compare to the stated output **and exit code**.
- Exit codes are a contract: locate where they are set before calling one a bug —
  `sed -n '/^def main/,/^if __name__/p' <cli>.py`. (`--strict` exiting 1 on an *unrouted*
  task is correct; exiting 1 on a routed one would be the bug.)
- Adversarial probes, not just the documented example (see SKILL.md §10d): gibberish, real
  words that contain a short signal, two-signal ambiguity, empty input.
- Check the unknown/unmatched path is non-zero under the strict flag and zero without it.

## 3. Asset freshness

- A screenshot must show the CURRENT output. Nothing greps inside a PNG — read it with vision.
- If the asset is a real capture, re-capture from the real command; never hand-type numbers into
  a picture.

## 4. Faithful regeneration of an existing Chrome-rendered asset

When the repo ships a Chrome-rendered terminal card and only the numbers moved, regenerate in the
SAME visual style — a PIL-drawn card is a different visual style and the diff is obvious.

1. Measure the old PNG with PIL: page bg colour, card bounds (scan rows/cols for the card fill),
   text-band y-offsets, prompt/dot/result lines, canvas size.
2. Write an HTML twin: absolutely-positioned card at the measured left/top with the same px
   width/height and font stack, real command output pasted in.
3. Render:
   `google-chrome --headless=new --no-sandbox --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --window-size=1200,156 --screenshot=/tmp/new.png file:///…/.card.html`
4. **Diff numerically before replacing**: `PIL.ImageChops.difference` → mean abs diff per region;
   target < ~1 with no changed text bands outside the numbers. Wrong card fill = wrong geometry:
   fix the HTML, don't "close enough" it.
5. Copy over the asset, delete the generator from the repo tree (keep it beside the QA log), and
   confirm `git ls-files assets/` is clean before the commit.

## 5. Sibling-repo / suite hygiene

```bash
for r in OWNER/repoA OWNER/repoB; do
  gh api repos/$r --jq '"\(.full_name) stars=\(.stargazers_count) forks=\(.forks_count) pages=\(.has_pages) pushed=\(.pushed_at)"'
done
grep -l "repoB" repoA/README.md ; grep -l "repoA" repoB/README.md   # mutual cross-links
gh api repos/OWNER/repoB/tags --jq 'length'                          # tags / releases
```

Real gap found 2026-09-17: two launched repos had **zero** references to each other, and one had
no live demo (`has_pages: false`), no tag and no release while its sibling had both — so the
"suite" story existed only in the pitch. Fix in one pass: mutual README cross-links, a `v1.0.0`
tag + release per repo, a Pages demo (or a recorded terminal demo) wherever a demo is claimed,
and the sibling list in each description.

## 6. Honesty notes — write the defensible version

- Perf claims are load-dependent: README `~10 ms` reproduced as 11.0–12.8 ms median (n=30) while
  the box was under memory pressure (swap 96% full). Write a range (`~10–15 ms`) or state the
  measurement (`n=30, median 12.8 ms`) — a range is unattackable, a point estimate is not.
- Coverage differs by command: 94% plain vs 95% with `--cov-report=term-missing`. Name the
  command next to the number, or quote what the reader's own command will print.
- If a claim cannot be verified, say so plainly in the report instead of softening it into a
  positive.

## 7. Report + approval gate

Write the pass to `~/ops/artifacts/<topic>-qa/qa-report-<date>.md` (English) with: scope/method,
verified-claims table, findings, fixes, re-verification (fresh-clone log excerpt), and an explicit
**"awaiting approval"** list. Commit locally — the push and any public post are the user's call:
hand over the SHA plus the exact next command, and leave `git status` clean.
