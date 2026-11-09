#!/usr/bin/env bash
# launch-preflight.sh — pre-flight an open-source launch before you push or post.
#
# Usage:
#   bash scripts/launch-preflight.sh OWNER/REPO [url ...]
#
# Example:
#   bash scripts/launch-preflight.sh Amz34/zeroegress \
#     https://raw.githubusercontent.com/Amz34/zeroegress/main/README.md \
#     https://github.com/Amz34/zeroegress/releases/tag/v0.1.0
#
# Exit 0 = every check passed. Any FAIL line means: fix it before publishing
# (a failed check that reaches a launch post is a credibility leak).
set -uo pipefail

REPO="${1:-}"
shift || true
if [ -z "$REPO" ]; then
  echo "usage: launch-preflight.sh OWNER/REPO [url ...]" >&2
  exit 2
fi

fail=0
ok()   { echo "ok   $*"; }
bad()  { echo "FAIL $*"; fail=1; }

echo "== tooling =="
command -v gh   >/dev/null 2>&1 && ok "gh present"   || bad "gh not installed (headless auth: device flow in SKILL.md)"
command -v curl >/dev/null 2>&1 && ok "curl present" || bad "curl missing"

echo "== github auth =="
if gh auth status >/dev/null 2>&1; then
  who=$(gh api user --jq .login 2>/dev/null)
  ok "gh authenticated as ${who:-unknown}"
  gh auth status 2>&1 | grep -qi "workflow" \
    && ok "token has 'workflow' scope (CI file can be pushed)" \
    || echo "warn no 'workflow' scope -> .github/workflows push will be rejected (see SKILL.md 3.5)"
else
  bad "gh not authenticated (see 'Headless auth' in SKILL.md)"
fi

echo "== git identity =="
n=$(git config --get user.name  2>/dev/null || true)
e=$(git config --get user.email 2>/dev/null || true)
[ -n "$n" ] && ok "user.name = $n"  || bad "git user.name unset"
[ -n "$e" ] && ok "user.email = $e" || bad "git user.email unset"

echo "== repo state =="
if gh repo view "$REPO" --json name,visibility,licenseInfo \
     --jq '"\(.name) \(.visibility) license=\(.licenseInfo.spdxId // "none")"' >/dev/null 2>&1; then
  ok "repo exists: $(gh repo view "$REPO" --json name,visibility,licenseInfo \
        --jq '"\(.name) \(.visibility) license=\(.licenseInfo.spdxId // "none")"')"
else
  bad "repo $REPO not visible to this token"
fi
if [ -d .git ]; then
  dirty=$(git status --porcelain | wc -l | tr -d ' ')
  [ "$dirty" = "0" ] && ok "working tree clean" || bad "$dirty uncommitted file(s)"
  l=$(git rev-parse --short HEAD 2>/dev/null || echo none)
  r=$(git rev-parse --short origin/main 2>/dev/null || echo none)
  [ "$l" = "$r" ] && ok "HEAD == origin/main ($l)" || bad "HEAD $l != origin/main $r (push pending?)"
else
  echo "warn not inside a git repo — skipping local git checks"
fi

echo "== ci =="
gh run list -R "$REPO" --limit 1 2>/dev/null | head -1 \
  | grep -q "success" && ok "last CI run: success" || echo "warn no successful CI run yet (check 'gh run list -R $REPO')"

echo "== live artefacts =="
for u in "$@"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -L -A "Mozilla/5.0 Chrome/126" "$u")
  case "$code" in
    200) ok "http $code  $u" ;;
    999) echo "warn http 999 (LinkedIn bot-block on guest fetch — not proof of failure)  $u" ;;
    *)   bad  "http $code  $u" ;;
  esac
done

echo
if [ "$fail" = "0" ]; then
  echo "PREFLIGHT OK — safe to push / post."
  exit 0
fi
echo "PREFLIGHT FAILED — fix the FAIL lines first." >&2
exit 1
