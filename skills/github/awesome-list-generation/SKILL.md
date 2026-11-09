---
name: awesome-list-generation
description: Use when building a curated awesome-list repo.
---

# Awesome-list generation (live-checked, relevance-gated)

Highest-yield GitHub discovery asset for an unknown account: a curated list ranks in search, gets
linked by other lists, and converts readers into followers. The failure mode is a dump of loosely
related repos — gate every entry.

## When to use
- User wants GitHub growth / discovery, or asks for an "awesome-<topic>" repo.
- Any curated index that must not rot (the recipe ships a weekly refresh workflow).

## Build (generator script)

1. **Enumerate candidates** with `gh search repos`, one query per section keyword:
   ```bash
   gh search repos --limit 60 --sort stars \
     --json fullName,stargazerCount,description,url,pushedAt,isArchived,isFork "agent memory store"
   ```
2. **Hard gate each candidate** (all must hold):
   - `stargazerCount >= 800`
   - `isArchived == false`, `isFork == false`
   - `pushedAt >= 2025-04-01` (active)
   - non-empty `description`
   - **at least one section keyword appears in `name + description`** — mention-only matches are what
     produce off-topic bleed; check the field, not the search score.
3. **Cross-section de-dupe**: each repo appears in exactly one section.
4. **Render** one markdown table per section:
   `| [owner/repo](url) | stars | license | description | last push |`
   plus Contents anchors, badge row, a public "How this list stays honest" (state the gate), Contributing, License.
5. **Put the count in a badge** (`entries-N`) so the README is self-verifying with a single grep.

## Publish

- Repo surfaces are **English only** (README, docs, commits, CLI output).
- Commit the generator (`build_awesome.py`) **and** `.github/workflows/refresh.yml` (cron `17 3 * * 1`)
  so the list refreshes itself — that is what keeps it credible over time.
- Add LICENSE (MIT), CONTRIBUTING.md, `.github/ISSUE_TEMPLATE/suggest-project.yml`, 20 topics.
- Cross-link: profile README + flagship repos link the list (every entry point reaches every artifact).

## Pitfalls (all hit in practice)

- **`gh search repos --json` has NO `repositoryTopics` field.** Passing it makes *every* call exit rc=1
  and the build silently returns nothing. Valid: `fullName, stargazerCount, description, url, pushedAt,
  isArchived, isFork, owner, name, language, license, updatedAt`. Dump the field list to a file and read
  it before scripting.
- **A secret-scanner that greps the bare words `token|secret|key|password` false-positives** on any
  agent-infra copy. Scan for *shapes* instead:
  `gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN|eyJ[A-Za-z0-9_-]{20,}\.`
- **Never `git add -A` without a `.gitignore`** covering `build.log`, `run.txt`, `build.err`; stray logs
  otherwise need an API delete (`gh api -X DELETE .../contents/<f> -f sha=<sha>`).
- **Do not publish until the entry count is verified by grep against the remote raw README**, not the local copy.
- Helper `subprocess.run` must use `cwd=`, never `workdir=` (silently aborts every command).

## Verify

```bash
curl -s https://raw.githubusercontent.com/<owner>/<repo>/main/README.md \
  | grep -cE '^\| \[[^]]+\]\(https://github.com/'      # == badge count
gh api repos/<owner>/<repo> --jq '{topics:(.topics|length), lic:.license.spdx_id}'
curl -s -o /dev/null -w '%{http_code}\n' https://github.com/<owner>/<repo>   # 200
```
