---
name: open-source-publishing
description: "Use when publishing a project to GitHub as a public repo."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [github, open-source, publishing, release, security, git]
    related_skills: [github-auth, github-repo-management]
---

# Open-Source Publishing

Publish a local project as a public GitHub repository without leaking
secrets, getting stuck on push conflicts, or shipping unverified state.
Complements `github-auth` (auth setup) and `github-repo-management`
(gh/git command reference) — this skill is the end-to-end *release
workflow* with the traps that are not in the command references.

## When to Use

- User says "publish this to GitHub so others can use it", "make it open
  source", "push my X as a public repo"
- Turning accumulated ops work (scripts, patterns, docs) into a public
  project
- Releasing a repo where the same GitHub account pushes from multiple
  machines (laptop + server + another session)

## User language rule (Aamir — ALWAYS English)

GitHub repos are published **entirely in English**: README, docs, commit
messages, CLI/user-facing output, `.env.example` comments. No Hinglish
(Roman Urdu/Hindi) anywhere a reader could see. This was an explicit
correction (Aug 2026) — a repo shipped with Hinglish print messages and a
Hinglish README, and the user asked for a full translation.

Before/after publishing, scan user-facing text for non-English:

```bash
grep -rniE "nahi|karo|karta|chahiye|hoga|mila|ho raha|wala|pehle|bina|tumhara|chalo|batao|dekh lo|band kar|khol" \
  --include="*.py" --include="*.md" --include="*.example" . | grep -v ".git/"
```

Fix by exact-string replacement per message (a Python dict of
old→new lines applied with `str.replace`), then full rewrite of README /
`.env.example`, then `python3 -m py_compile` to confirm nothing broke.
False-positive note: API field names (e.g. `isReshareDisabledByAuthor`)
match English words — don't translate those.

## Workflow (proven order)

### 1. Security audit BEFORE the first commit

Anything pushed is in git history forever — a secret removed later is
still recoverable. Scan the tree for the classic leaks:

```bash
grep -rniE "sk-[a-z0-9]{10}|ghp_|gho_|AKIA|-----BEGIN|158\.101\.|you@gmail\.com" . 2>/dev/null | head
```

Add `.gitignore` FIRST so nothing sensitive can be staged even
accidentally: `.env`, `*.env`, `creds.json`, `session/`,
`lid-mapping-*.json`, `*.log`, `__pycache__/`, `.DS_Store`.

Sanitize hardcoded credentials in scripts → env-var based:
`os.environ.get("VAR")` / `"${VAR:-default}"`, and document the env vars
in the README. Never commit real account emails, private IPs, or tokens.

### 2. Create from a local directory

```bash
git init -b main                      # -b main: older git defaults to master
git add -A
git -c user.name="Name" -c user.email="email" commit -m "Initial release: ..."
gh repo create NAME --source . --public --description "..." --push
```

Pitfalls:
- `--source --push` auto-adds `origin` — a later manual
  `git remote add origin` fails with "Unable to add remote". Verify with
  `git remote -v` instead of re-adding.
- The repo must have a branch before push — `git init -b main` (older git
  defaults to `master`).

### 3. Non-fast-forward push (multi-machine accounts)

Symptom: `git push` → `! [rejected] main -> main (non-fast-forward)` —
another machine/session pushed commits the local repo doesn't have.

```bash
git fetch origin
git log --oneline origin/main -3      # what the remote has
git log --oneline HEAD -3              # what you have
git -c user.name="Name" -c user.email="email" pull --rebase origin main
git push origin main
```

If local has uncommitted changes: `git stash` → pull --rebase →
`git stash pop` → commit → push.

If the remote content is superseded by local (own repo, no collaborators):
`git push --force origin main` is acceptable — but confirm ownership first
(force push rewrites remote history; the terminal will ask for approval).

### 3.5 `.github/workflows/` push rejected — OAuth lacks `workflow` scope

Symptom: repo created fine (`gh repo create --source . --push`), but push
fails: `! [remote rejected] main -> main (refusing to allow an OAuth App to
create or update workflow \`.github/workflows/ci.yml\` without \`workflow\`
scope)`. The `repo` scope allows creating files EXCEPT workflow files —
GitHub hard-blocks OAuth apps without the `workflow` scope.

Two options:

**A. Get the scope (needs one user browser step):**
```bash
gh auth refresh -h github.com -s workflow
# prints a device code + https://github.com/login/device URL for the user
git push -u origin main
```

**B. Ship without CI first, add CI later (no user interaction):**
```bash
git rm -r --cached .github && git commit -m "..." && git push -u origin main
# repo goes live; keep .github/ locally (untracked) and push it after the
# user grants `workflow` scope via option A
```
Note: `gh auth refresh` device flow times out in a non-interactive terminal
foreground call (120s) — run it in the background and hand the code to the
user, or use option B and defer CI.

**VERIFY the scope landed before pushing — "user said done" is not proof
(proven failure, Aug 2026).** After the user claims approval:
```bash
gh auth status 2>&1 | grep -i scopes   # MUST show 'workflow'
stat -c '%y' ~/.config/gh/hosts.yml    # mtime should be NOW, not days ago
```
If scopes still lack `workflow` and hosts.yml mtime is stale, the approval
did NOT complete — the user most likely entered the code and pressed
Continue but skipped the green **Authorize** button (or the code expired,
~15 min lifetime). Don't keep polling the old process: kill it, run
`gh auth refresh -h github.com -s workflow < /dev/null` again in the
background, and give the user an explicit 3-screen walkthrough:
(1) enter code → Continue, (2) **green Authorize button** on the
"Authorize GitHub CLI" screen, (3) "Device Activated" confirmation.
Only then push the CI file.

### 4. Detached-HEAD recovery

Symptom: `git status -sb` shows `## HEAD (no branch)`, pushes report
"Everything up-to-date" while the remote is missing files, and `git pull`
fails with "cannot pull with rebase: Your index contains uncommitted
changes". A botched rebase left HEAD detached with staged work.

Recovery:
```bash
git rebase --abort                       # discard the broken rebase
git checkout main
git log --oneline main -3                # confirm branch state
# if the lost commit exists as a dangling commit, cherry-pick it:
git cherry-pick <sha>                    # may need -c user.name/-c user.email
# if work survives only as staged files, commit them directly:
git add -A && git commit -m "..."
git push origin main
```

### 5. Verify AFTER publish — don't trust "push succeeded"

```bash
# File list on the remote
curl -s "https://api.github.com/repos/OWNER/NAME/git/trees/main?recursive=1"

# Liveness of the rendered README (200 = live)
curl -s -o /dev/null -w "%{http_code}" -L \
  "https://raw.githubusercontent.com/OWNER/NAME/main/README.md"
```

Note: the trees API can lag a few seconds after push; a raw-file 200 is
the stronger liveness signal. If raw gives 404 but the trees API lists the
file, it's CDN lag — re-check after a few seconds rather than re-pushing.

**REVERSE CASE — raw can serve STALE content (proven 2026-09, profile repo
`Amz34/Amz34`):** after a successful push, `raw.githubusercontent.com`
kept serving the PREVIOUS revision for minutes, which looks exactly like a
failed push. Do NOT re-push or amend on that evidence. Compare three
sources and trust the API:

```bash
git show HEAD:README.md | wc -c                      # what you committed
gh api repos/OWNER/REPO/contents/README.md --jq '.size'   # what the remote HAS (authoritative)
gh api repos/OWNER/REPO/contents/README.md --jq '.content' | base64 -d | head -4
curl -s "https://raw.githubusercontent.com/OWNER/REPO/main/README.md?v=$(date +%s)" | head -4  # CDN, may be stale
```

API size/content == your commit → the push landed; only the raw CDN cache
is behind. Announce done on the API evidence and note the raw lag.

**Strongest fingerprint — compare BLOB SHAs, not sizes or prose (proven
2026-09-13, `Amz34/fire-smoke-watch`).** `git hash-object` of the local file
must equal the `.sha` the contents API reports; that is a content hash, so it
cannot be satisfied by a stale or partially-pushed file:

```bash
LOCAL=$(git hash-object README.md)
REMOTE=$(gh api repos/OWNER/REPO/contents/README.md --jq .sha)
[ "$LOCAL" = "$REMOTE" ] && echo "remote == committed content" || echo "MISMATCH"
grep -c "<a string you just added>" README.md        # local: expect >=1
curl -s "https://raw.githubusercontent.com/OWNER/REPO/main/README.md?cb=$(date +%s)" \
  | grep -c "<the same string>"                       # raw: may still be 0 = CDN lag only
```

A `grep -c` of 0 on raw while the blob SHA matches is CDN lag, NOT a failed
push. Never re-push, amend, or force-push on that evidence alone — re-check
the API. The CDN converged later in the same session without any action.

**Licence detection check (GitHub silently says `license: none`).** After the
first push, confirm GitHub actually recognised the licence file:

```bash
gh api repos/OWNER/REPO/license --jq '.license.spdx_id + " " + .path'   # e.g. "Apache-2.0 LICENSE"
gh repo view OWNER/REPO --json licenseInfo                              # may lag/cache — trust the endpoint above
```

If the endpoint 404s, check the file's first bytes: **a LICENSE whose first
line is blank is not recognised** — GitHub's licensee parser needs the text at
the top of the file. Fix and re-push:

```bash
head -3 LICENSE | cat -A                      # "^$" on line 1 = the bug
python3 - <<'PY'
from pathlib import Path
p = Path("LICENSE"); p.write_text(p.read_text().lstrip("\n"))
PY
git commit -am "LICENSE: strip leading blank line so GitHub detects it" && git push
```

Detection can take ~1 min after the push; re-query the endpoint rather than
re-uploading, and confirm the live bytes
(`curl -s .../raw/.../LICENSE | od -c | head -2`).

**Rescan the REMOTE for secrets after push** (proven 2026-08, meeting-mode
scripts added to a public repo): local scans are not enough — verify what's
actually live:
```bash
curl -s https://raw.githubusercontent.com/OWNER/NAME/main/<script>.py | \
  grep -cE "sk-[a-zA-Z0-9]{20}|ghp_|PRIVATE KEY"   # 0 = clean
```
Also re-scan pushed files for the user's PII (phone numbers, emails, tokens)
before announcing "pushed". Safe pattern to follow: scripts read keys from
env (`os.environ.get("KEY")`) with a `~/.hermes/.env` fallback — the secret
value never enters the repo, so the remote scan returns 0.

### 6. Verify CI runs — don't claim "CI green" from a workflow file existing

After the CI file is pushed, a run starts automatically on `push` to the
default branch. Verify the ACTUAL run, not the file:

```bash
gh run list --limit 1                      # run id + status (in_progress…)
gh run view <RUN_ID> --json jobs -q '.jobs[] | "\(.name): \(.status) \(.conclusion)"'
# wait ~45-90s for the first run; every job must say "completed success"
```

Pitfall — CI matrix vs Python syntax era: if the code uses modern type
syntax (`X | Y`, `str | None`), the matrix minimum is 3.10 — a 3.9 entry
fails at COMPILE on syntax, not on tests, and it fails in CI while all
local tests pass. Fix: drop 3.9 from the matrix and set
`requires-python = ">=3.10"`, then re-push (a new run auto-starts). Also
double-check the CI workflow file itself was actually pushed (`.github/`
was `git rm --cached`-ed in option B of §3.5 — `git add .github` before
committing the CI addition).

**Add the OS dimension, not just Python versions (proven 2026-09, two repos).** An
`os: [ubuntu-latest, macos-latest, windows-latest]` × `python-version` matrix with
`fail-fast: false` is the cheapest portability audit available: the first run is usually RED, and
every red is a real bug a user would eventually hit. It found `os.statvfs` (POSIX-only; Windows
raises `AttributeError`, not `OSError`), `/proc`-derived metrics arriving as `None` and poisoning a
`sum()` inside a rollup on macOS, and a schema test asserting `NoneType` where the schema says
`null`. Fixes, snippets and the Linux-only skip-marker rules:
**`references/cross-platform-ci-matrix.md`**. Carry the matrix values into the job name
(`test (${{ matrix.os }} / ${{ matrix.python-version }})`) so `gh run view <id> --json jobs` reads
as a coverage table, and read jobs individually — a partly-green run still looks green in some
views.

The upgrade pass that produces a repo worth putting a matrix under — a deterministic CLI over the
declarations, cost envelopes, an append-only telemetry ledger, packaging, docs, an SVG diagram — is
written up in **`references/executable-model-upgrade.md`**.

## Headless auth (server/VM)

`gh auth login` requires an interactive TTY — piping input times out. Use
the device flow with gh's public client ID:

```bash
# 1. Start device flow
curl -s -X POST "https://github.com/login/device/code" \
  -d "client_id=178c6fc778ccc68e1d6a&scope=repo%20read:org%20gist" \
  -H "Accept: application/json"
# → returns device_code + user_code (e.g. 0BCF-BAC0) + verification_uri

# 2. Give the user: verification_uri + user_code (hyphen included, digits
#    are ZEROS not letter O — GitHub device codes never use O)
# 3. Poll for the token (5s interval):
curl -s -X POST "https://github.com/login/oauth/access_token" \
  -d "client_id=178c6fc778ccc68e1d6a&device_code=<DEVICE_CODE>&grant_type=urn:ietf:params:oauth:grant-type:device_code" \
  -H "Accept: application/json"
# → access_token on success; authorization_pending while waiting

# 4. Store permanently (not just env):
unset GH_TOKEN
echo "$TOKEN" | gh auth login --with-token
```

Poll from a background process with notify_on_complete so the session
doesn't block. Token scopes requested: `repo read:org gist`.

## Profile-value bonus

For a personal account, also create the profile README repo
(`OWNER/OWNER` — the repo named exactly after the username) with a
professional profile: intro, skills, projects, contact. It renders on the
profile page and makes an otherwise-empty account look maintained. A public
release repo + profile README together turn a dormant account into an
"open source contributor" presence.

## Launch post pitfalls (verified 2026-09-11, ZeroEgress launch)

- **X returns 403 `"You are not permitted to perform this action."` when a tweet
  text contains `api.<provider>.com` hostnames in a REPLY** (anti-spam). The same
  text posts fine as a root tweet. Fix: in replies, write `cloud LLM endpoint`
  instead of naming the host, or put the ASCII proof block in the root tweet.
- **X free tier: keep each tweet ≤275 chars** (280 hard limit, count before you
  send) and thread with `{"reply":{"in_reply_to_tweet_id": <prev id>}}`. Verify the
  thread afterwards with `GET /2/tweets?ids=a,b,c&tweet.fields=conversation_id` —
  all should share the root's `conversation_id`.
- **LinkedIn: `POST /rest/socialActions/<ugcPostUrn>/comments` is 403**
  (`partnerApiSocialActions.CREATE`, community token) — you CANNOT add the link as
  a first comment via API. Encode the URN (`urn%3Ali%3AugcPost%3A...`) or v2 path
  both fail. Put the URL at the end of the post body instead.
- **Editing your own post works**: `POST /rest/posts/<urlencoded urn>` with
  `{"patch":{"$set":{"commentary": "<FULL new text>"}}}` → 204. PITFALL: `$set`
  REPLACES the whole commentary — always send the complete text, never a fragment
  (a fragment silently destroys the published post). Read-back is impossible with
  `w_member_social`; verify with a logged-out browser fetch of the post URL.
- **Carousel slides**: 1080x1350 px, `@page { size: 1080px 1350px; margin: 0 }`,
  chrome headless `--print-to-pdf`, then `pdftoppm -png -r 96` + vision check each
  slide for overflow before posting. 7 slides = hook, problem, 3 layers, proof
  terminal output, honest limits, CTA.
- **X rejects animated GIF at POST time (2026-09-21)**: `xurl media upload --media-type
  image/gif` returns a media id, then the create call fails
  `type: https://api.x.com/2/problems/invalid-request`, `title: Invalid Request` (tried
  `--category tweet_gif`, a PNG control, a `3_`-prefixed key). The animated route on X is
  **MP4**: `ffmpeg` the same frames →
  `xurl media upload --media-type video/mp4 --auth oauth1 file.mp4` → `sleep ~15` (transcode) →
  post with `--media-id`. Static PNG posts fine. So **one poster = PNG for LinkedIn/Bluesky +
  MP4 for X** (recipe: `linkedin-gif-pipeline` → `references/poster-renditions-mp4-x.md`).
- **X media must be uploaded with the SAME auth method as the post.** A GIF uploaded under
  `--auth oauth2` and posted under `--auth oauth1` fails `Invalid Request` — match them
  (oauth1 both ways; oauth2 refresh was dead in that session, so don't spend a round trip on it).
- **X reply/quote was 403 on our app tier** (`"You are not permitted to perform this action."`) —
  distinct from the hostname-in-reply anti-spam case above. Consequence for a launch: a
  **self-QA follow-up comment is only automatable on Bluesky** (threaded reply); on X and LinkedIn
  hand the user paste-ready text, and say that up front rather than after building the script.
- **Size the copy in the platform's units**: X counts every URL as **23 chars** regardless of real
  length, so a `len()`-trimmed draft is either over- or under-trimmed. Verify what actually fits.
- **Launch assets live in `~/ops/kb/<product>-launch/`** (html, pdf, slide PNGs,
  post URLs) and the posting scripts in `~/.hermes/scripts/post_{linkedin,x}_<product>*.py`
  — reuse them for the next launch instead of rewriting the API plumbing.

## 7. Verifying a whole LAUNCH (repo + carousel + posts)

A launch is several artefacts, so "tests pass" is not verification. Before
announcing done, run one throwaway script (`/tmp/hermes-verify-<topic>.sh`)
that checks every artefact in a compact table: repo suite + smoke, `bash -n`
/ `python3 -m py_compile` on changed scripts, structural asserts (carousel
slide count in HTML == `pdfinfo` page count, CTA/repo link present in the
posting scripts), `git status` clean + `HEAD == origin/main`, `gh run list`
shows `completed success`, and HTTP 200 on raw README / post URL / release
URL. Full checklist, the exact commands, and the reasoning live in
**`references/launch-verification-and-quirks.md`**.

Re-runnable pre-flight (auth, scopes, git identity, repo visibility, CI,
URL liveness) before you push or post:
**`scripts/launch-preflight.sh OWNER/REPO [url ...]`** → exit 0 = go.

Two habits this launch proved necessary:

- **Never commit or post a file you have not re-read at least once.** Long
  `write_file`/`patch` bodies can land elided — `grep -n "truncat" <file>`
  plus a size check before `git commit`.
- **Never build a script with a giant inline heredoc in one terminal call**
  (it gets refused). `write_file` the script, `bash <path>`, then delete it.
- **Verification scripts must read the artefact's OWN log file.** Repo test
  runners redirect to `/tmp/<x>.txt` and print only a confirmation — grep
  the log, or your verifier prints empty sections that look like failure.

## 8. The "enforcement, not promise" repo pattern

When the repo exists to make a claim (privacy, data residency, "nothing
leaves this machine") credible rather than to be a product, ship the
enforcement so a stranger can run it: a `prove` subcommand that attempts
real non-loopback connections and prints `BLOCKED`/`LOCAL` per attempt with
a verdict line; the identical terminal block pasted into README, the
carousel's proof slide, and the thread; a stable exit-code contract; a CLI
parser with `allow_abbrev=False`; destructive verbs requiring the target
slug to be re-typed; and a generated client-facing trust-pack PDF. State
the limits honestly (missing disk encryption, cloud route) — unhedged
marketing inside an audit-yourself repo destroys the claim. Details and the
ZeroEgress numbers: `references/launch-verification-and-quirks.md` §3.

## 9. Open-core publishing (public credibility repo, private paid layer)

The pattern for "the product is the thing I sell, the repo is the proof I can
build it": publish a *thin, honest* open layer and keep every sellable piece
out of the repo — **not just out of the working tree, out of history too**
(the user's rule: "jo bechni hai wo repo me kabhi na jaye — history me bhi
nahi"). Proven split (2026-09-13, fire/smoke watch):

- **Public:** drop-in detector runtime + one runnable example + honest
  benchmark numbers + the training notebook + demo clip and screenshot.
- **Private (never in the repo):** console/UI, alert engine, multi-camera,
  reporting, per-site dashboard, and any trained weights you can't license.
- Build the public repo as a SEPARATE directory (`~/<product>-public`) and
  copy files in — never publish a cleaned-up `git clone` of the private repo,
  because its history already holds the paid layer.

Gate before the first commit, and re-run it after every content commit:

```bash
git ls-files | wc -l                                  # sanity: only files you meant to ship
git ls-files | grep -E "\.onnx$|\.pt$|\.pth$|weights" || echo "no weights tracked"   # MUST be empty
git ls-files -z | xargs -0 grep -lniE "sk-|ghp_|AKIA|PRIVATE KEY|@gmail\.com|password" || echo "no secrets tracked"
```

- `.gitignore` must carry the weights patterns + `.env` **and the build
  intermediates** of any media you generate (`demo/plate.png`,
  `demo/*_cropped.mp4`). If an intermediate slipped into a commit, remove it
  from tracking without deleting it locally:
  `git rm -q --cached demo/plate.png demo/console_cropped.mp4` then commit.
- Ship `LICENSES.md` — a per-artefact map (runtime code / example /
  notebook / weights / demo media), because "open source" for the repo does
  not mean the same licence for each file inside it. State plainly that
  **no model weights are redistributed** when provenance is unclear.
- Add the honest-limits disclaimer in the README (e.g. "supplementary early
  warning, not a certified fire alarm — NFPA 72 / EN 54 / local Civil
  Defense approvals still apply"). Never let a repo imply a safety
  certification it does not have.
- **Clean-room test before announcing**: `git clone` into `/tmp` and run the
  documented first command there. Nothing else proves a stranger's first
  command works; a fresh clone also catches files that only exist locally.

Worked example, the exact file list, and the licence/provenance reasoning:
`references/open-core-publishing.md`.
Re-runnable end-to-end verifier (file list, licence spdx, blob-SHA match,
tracked-weight scan, clone smoke test):
`scripts/verify-published-repo.sh OWNER/REPO [clone-test-path]`.

## 10. The repo must evidence itself (clean Actions tab + proof assets)

"CI green" and "tests pass" are claims. A stranger deciding whether to clone
wants receipts; the user's standing rule is a public repo with **zero failed
runs visible**. Both artefacts below get verified BEFORE you announce done.

**a) Clean Actions tab — fix the cause, then delete the red runs.**

```bash
gh run list --limit 10 --json databaseId,conclusion -q '.[] | "\(.databaseId) \(.conclusion)"'
gh api -X DELETE repos/OWNER/REPO/actions/runs/<failed_id>   # one call per red run
gh workflow run ci.yml --ref main                            # fresh dispatch, not an amend
gh run list --limit 3 --json databaseId,status,conclusion,headSha
gh run view <RUN_ID> --json jobs -q '.jobs[] | "\(.name) -> \(.conclusion)"'  # every job MUST be success
```

Deleting red runs while the cause still stands just hides a broken build.
Fix the cause first (§1-§3 of `references/ci-proof-and-publish-hygiene.md`:
deps pinned from real `pip freeze`, matrix minimum matching the syntax you
actually use, `actions/checkout@v5` + `actions/setup-python@v6` to clear
Node20 deprecation annotations) — the goal is a repo whose FIRST run was
already green, which means pinning the build recipe before the first push.

**b) Proof images — real captures only, never decoration.** A technical
audience reads stock/AI imagery as marketing and loses trust; a terminal/CI
capture reads as proof. Rules: ≤5 images, each tied to a specific claim,
caption = the exact command that produced it, and **no faces or living
beings in any form** (user hard rule). Two capture paths:

- Terminal output → `scripts/render-term-card.py <out.txt> assets/<name>.png "<command>"`
  (PIL dark card, red for findings, green for passed/clean) — offline,
  deterministic, no browser.
- Live page (Actions run, repo front page) → headless Chrome:
  `google-chrome --headless=new --disable-gpu --no-sandbox --hide-scrollbars
  --user-data-dir=/tmp/chs$RANDOM --window-size=1400,760
  --virtual-time-budget=12000 --screenshot=<out.png> "<url>"`, then read the
  PNG with vision before shipping it.

Wire one image inline next to the claim it proves and the rest into a
`## Proof of life` / `## Build proof` section. Verify they actually serve:
`curl -s -o /dev/null -w '%{http_code} %{size_download}\n' <raw.githubusercontent URL>`
must print **200 with real bytes** for every asset — an image that 404s on
raw makes the README look broken to every visitor.

Three traps that cost real time (2026-09):

- **Check the URL with its extension.** A verification loop over assets collected as bare names
  (`audit-clean`, `ci-green`) requests `<repo>/assets/audit-clean` and 404s on every PNG while the
  one SVG that kept its suffix passes — which reads exactly like "the repo's images are broken".
  Collect with extensions (`grep -o 'assets/[a-z0-9-]*\.\(png\|svg\)' README.md`) and assert the set
  equals the files on disk.
- **Capture the WHOLE README, not the viewport.** `--screenshot` without a tall window stops at the
  fold and hides precisely the proof section you are verifying. Use `--window-size=1280,9600`
  (measure — GitHub READMEs run long), then crop regions with PIL and read them with vision: badges
  render, the SVG diagram renders, each proof image is a real image and not a placeholder, nothing
  clipped or overlapping.
- **A UI screenshot inherits the UI's people.** A GitHub Actions capture includes the commit author's
  avatar, and the no-faces rule covers published assets — crop that row and read it with vision. An
  abstract identicon or letter avatar is fine; a photograph of a person is not, not even the
  operator's own.

**c) Numbers on the page must be measured, not remembered.** Every count in
a badge, README line, or pitch (test count, framework version, seat/plane
counts) is a claim: grep the live page for it after pushing and correct it.
Real misses: badges said `35 passing` when the suite had 38, and
`FastAPI 0.115` when `pip freeze` said 0.141 — both caught by screenshotting
the published page and reading it with vision. Same rule for docs examples:
hand-written sample JSON in a README drifts from the generated data (an
invented role's mandate/level appeared in `roles/README.md`), so read the
generated file back and quote real values. **When a number moves, everything
that quotes it moves in the same commit** — badge, README table, and the
rendered card screenshot. Adding one regression test took a suite 32→33 tests
and coverage 96%→94%; a screenshot still reading `32 passed` beside a badge
saying 33 is worse than either number being stale alone.

  **Extend the same rule to the LAUNCH COPY and to any rendered visual (2026-09-21).** The artifact
  set is badge + README + **poster image** + **the post text on 2-3 platforms**: the number must be
  identical in all of them, and it must be the **measured** one. A card that printed `18×` while the
  measurement was `17.6×` and the caption said `17.6×` is a false claim — rounding for rhythm is the
  same failure whether the figure is invented or merely rounded. The claim gate runs on text files
  and **cannot see your PNG**, so read the rendered card's text back (vision) and diff it against the
  gated draft before shipping; then strip the `[src: …]` / `[claim-ok: …]` tags — they belong to the
  review trail, not to the post. Detail: `references/measurement-backed-repo.md` §4.

**d) Behaviour claims need adversarial probes, not just the happy example.** The
documented example proves the command *runs*; it does not prove the matcher *decides*
right. Run every documented example AND adversarial inputs — gibberish, real words that
CONTAIN a short signal, two-signal ambiguity, empty input — and check the exit-code
contract (which inputs must be non-zero, which must be zero). Proven 2026-09-17 on
`Amz34/agent-operating-model`: a keyword router matched its signals as substrings, so
`ui` fired inside "b**ui**ld" and `bot` inside "**bot**h", misrouting ordinary tasks to
the wrong seat/plane while the documented example passed the whole time. Fix pattern —
edge matching instead of `needle in hay`, tolerant of plurals/suffixes:
`re.search(r"(?<![a-z0-9])" + re.escape(needle) + r"[a-z]{0,5}(?![a-z0-9])", hay, re.I)`,
then one regression test per false positive you found. Before "fixing" an exit code,
locate its source (`sed -n '/^def main/,/^if __name__/p' <cli>.py`) — `--strict` exiting 1
on an *unrouted* task is the contract, not the bug.

Support files: `scripts/render-term-card.py` (terminal → PNG cards),
`scripts/qa-fresh-repo.sh <git-url-or-local-path> [out-dir]` (fresh-clone QA from a
stranger's path — accepts a LOCAL path so you can clean-room a commit you have not pushed
yet; hard-fails on tracked secrets, prints clone SHA + PASS/FAIL/SKIP table),
`references/repo-truth-audit.md` (the full truth-audit pass: number/behaviour/asset
audits, faithful Chrome-card regeneration, sibling-repo suite hygiene, honesty notes,
report + approval gate),
`references/ci-proof-and-publish-hygiene.md` (CI cause table, workflow
skeleton, clean-room scrubbing, verifier-recipe pinning).

## 11. Measurement-backed repos — when the number IS the product

For a repo whose reason to exist is a **measured** claim (our stack is faster/cheaper on this
decision than a chat model), the rule set is stricter than a normal release:

- **Offline first**: the documented first command must work with **no key and no network**
  (`--dry-run` printing the real request payload), and the repo carries an offline
  **`make verify`** self-check (parsers, batching contract, demo data, asset sanity, canonical URL,
  no-leak scan) as its canonical verification command.
- **Synthetic data only**; never client rows in the demo set.
- **Report the finding that undercuts the pitch** — accuracy was a wash (26.7% vs 28.3%), so the
  repo sells latency/cost/determinism instead, and names the real bottleneck (the gold label was in
  the candidate list only 47% of the time). A **"where this does not help"** section is the highest
  value paragraph in this kind of repo.
- **Auditing a vendor's claims**: keep *their claim* and *our measurement* in separate columns,
  publish constructively, and say "not measurable" rather than ranking what you can't measure.
- **The integrity gate sees text, not your image**: a `[src: …]` tag on the line ABOVE a metric
  does not clear it (put the tag at the end of the same line), the rendered card is an unguarded
  claim surface (a poster reading `18×` beside a caption reading `17.6×` is a false claim), and
  **strip the tags before publishing**.
- **Verification is per-platform**: Bluesky has a public read API, X proves itself from the create
  response, LinkedIn only from `x-restli-id`; and size copy in the platform's units (X counts every
  URL as 23 chars).

Full pattern, the gate interplay, and the launch-verification recipe:
**`references/measurement-backed-repo.md`**.

## Pitfalls

- **Don't self-promote inside the repo.** The README should sell the *tool*; the
  commercial CTA (deployment service, sponsorship) belongs in the launch post and
  in one clearly-marked section at the end of the README.

- `.env` grep for keys: `grep -oE "^[A-Z_]*KEY[A-Z_]*="` misses keys whose
  names don't end in KEY — audit by scanning for `=` lines generally.
- `hermes config set fallback_providers '[{...}]'` stores a STRING, not a
  list — config arrays must be written via YAML, not quoted JSON. (Applies
  when publishing config examples too.)
- After force-push, verify the remote tree matches local (`git log` on
  both) before telling the user it's done.
- **`argparse` cannot mix optionals with a trailing `nargs="*"` positional**
  (bpo-15112): a command that looks valid dies with `unrecognized arguments`.
  Either parse with `parse_known_args()` and `parser.error()` on the leftovers,
  or drop the variadic positional. Pair it with `allow_abbrev=False` so a
  destructive flag like `--confirm` can never be reached as `--conf`.
- **Ship an installable-degradeable package**: keep the runtime stdlib-only
  where the claim depends on it (no dependency can phone home), declare
  `requires-python` to match the syntax you actually use, and make the test
  runner self-bootstrapping (creates its own venv, prints `Ran N tests … OK`)
  so a stranger's first command works from a clean clone.
