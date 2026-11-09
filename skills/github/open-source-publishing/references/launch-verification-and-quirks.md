# Launch verification, harness quirks, and the "enforcement, not promise" repo pattern

Captured from the ZeroEgress launch (2026-09-11): a privacy/confidentiality
concept shipped as an MIT repo (`github.com/Amz34/zeroegress`, 45 tests, CI
green, release `v0.1.0`) plus a 7-slide LinkedIn document post and a 4-tweet
X thread. Everything below was actually run; numbers are from that launch.

---

## 1. Multi-artifact verification before announcing "done"

A launch is never one artifact. Announce only after every one of these is
green — write ONE throwaway script (`/tmp/hermes-verify-<topic>.sh`) that
runs all of it and prints a compact table.

| Check | Command shape | Expected |
|---|---|---|
| Unit suite | `bash scripts/dev-test.sh` (repo's own runner) | `Ran 45 tests … OK` |
| Smoke (every README command) | `bash scripts/smoke-test.sh` | all `[exit=0]`, plus the *intentional* `[exit=1]` refusal case |
| Shell syntax of changed scripts | `bash -n <script>` | exit 0 |
| Python scripts compile | `python3 -m py_compile <script>` | exit 0 |
| Structural asserts | `grep -c 'class="slide"' carousel.html` → 7; `pdfinfo carousel.pdf \| awk '/^Pages/'` → 7 | match |
| Link/CTA actually embedded | `grep -q '<repo-url>' post_*.py` | present (proves the post text, which read-back can't) |
| Git state | `git status --porcelain` empty; `git rev-parse --short HEAD` == `origin/main` | clean + equal |
| CI | `gh run list -R OWNER/REPO --limit 1` | `completed  success` |
| Live artefacts | `curl -s -o /dev/null -w "%{http_code}"` on raw README, post URL, release URL | 200 |
| Leak scan | `git ls-files -z \| xargs -0 grep -InE "(api[_-]?key *=|sk-[A-Za-z0-9]{16,}\|/home/<user>/)"` | 0 (exclude deliberate test fixtures) |

Notes that cost time when forgotten:

- **Restrict the leak scan to `git ls-files`.** Scanning the whole tree hits
  `.venv/` and drowns the signal (my first pass scanned 25k files).
- **A repo's own test script usually redirects to its own log file**
  (`scripts/dev-test.sh > /tmp/zeroegress_test.txt`) and prints only a
  confirmation. Grep the LOG FILE — grepping the console capture prints an
  empty section and looks like failure.
- The `/home/<user>/` pattern in the leak scan is a portability check, not a
  credential check: it caught a hardcoded `cd /home/ubuntu/projects/<repo>`
  in `scripts/smoke-test.sh`, fixed to `cd "$(dirname "$0")/.."`, re-verified,
  committed (`196ad7f`), CI re-ran green.

## 2. Harness quirks hit while building and verifying the launch

- **Do not pass a big inline heredoc to the terminal tool** (`cat > f <<'EOF' … EOF`
  as one command). It is refused (bare `exit -1`, one line of output). Write
  the script with `write_file` to a real path, then run `bash <path>`, then
  delete it.
- **Long `write_file` / `patch` payloads can land elided.** After writing a
  long file (README, HTML carousel, CLI source), confirm the body survived:
  `grep -n "truncat" <file>` and check the size, and re-read key regions
  before committing. Never commit a file you have not re-read at least once.
- **Verify agent-written files by their effects, not by the tool's success
  message** — e.g. `pdfinfo` for page count, `grep -c` for slide count,
  `python3 -m py_compile` for scripts.

## 3. Repo pattern that makes a privacy claim credible: enforcement, not promise

The reusable design choice from this launch — a claim ("your documents never
reach a cloud model") is only viral/credible if a stranger can *run* it:

- Ship an executable proof: a `prove` subcommand that attempts real
  non-loopback connections and prints each one as `BLOCKED`/`LOCAL`, ending
  with a verdict line. Paste that terminal block into the README, the
  carousel's proof slide, and the X thread — identical output everywhere.
- Enforcement lives below configuration: patch `socket.socket.connect` /
  `getaddrinfo` in a context manager rather than shipping an `allow_cloud: false`
  flag. Say so explicitly in the README ("not a settings toggle, a patched
  socket layer").
- Client-side refusal in the local model client: physically reject a
  non-loopback `base_url` instead of validating it.
- Stable exit-code contract so the tool is scriptable and auditable:
  `0 ok / 1 error / 2 usage / 10 local-only refusal / 11 high-sensitivity`.
- Destructive verbs require explicit confirmation of the target
  (`destroy --client <slug> --confirm <slug>`), and the CLI parser disables
  flag abbreviation (`allow_abbrev=False`) so `--conf` can never mean
  `--confirm`.
- Deliverable a non-technical client can file: a generated trust-pack PDF
  (data-handling statement + NDA clauses + audit guide) — the repo produces
  it, the client keeps it.
- State the limits honestly in the README and in the honest-limits slide
  (no disk encryption, cloud route excluded only when the local route is
  used). Unhedged marketing in an audit-yourself repo destroys the claim.

## 4. Launch-day file layout (reuse, don't rewrite)

```
~/ops/kb/<product>-launch/     carousel.html · carousel.pdf · hi-1..N.png · post URLs
~/.hermes/scripts/post_linkedin_<product>.py     # document post + $set edit
~/.hermes/scripts/post_x_<product>.py            # root tweet
~/.hermes/scripts/post_x_<product>_replies.py    # thread continuation (reply ids)
~/ops/preflight_gh.sh · preflight_pub.sh         # auth + liveness preflight
~/ops/push_<product>.sh                          # init/commit/push in one shot
```

Posting scripts are idempotent-ish from a text file, so a failed tweet or a
403 can be retried without reposting what already went out (see the launch
pitfalls in SKILL.md: root tweet first, then replies against the returned
id; X 403s on `api.<provider>.com` hostnames in replies).
