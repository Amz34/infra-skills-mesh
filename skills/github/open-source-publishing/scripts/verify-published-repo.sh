#!/usr/bin/env bash
# verify-published-repo.sh OWNER/REPO [local-repo-dir] [clone-test-dir]
#
# Independently verify a published public GitHub repo WITHOUT trusting the
# push output. Checks: liveness, licence detection, blob-SHA match against the
# local tree, tracked-file hygiene (no weights/secrets), and optionally a
# clean-room clone. Exit 0 = all checks passed.
#
# Usage:
#   scripts/verify-published-repo.sh Amz34/fire-smoke-watch ~/fire-lab-public
#
# Requires: gh (authenticated), git, curl.

set -uo pipefail

REPO="${1:?usage: verify-published-repo.sh OWNER/REPO [local-repo-dir] [clone-test-dir]}"
LOCAL_DIR="${2:-}"
CLONE_DIR="${3:-/tmp/published-repo-clonetest}"
BRANCH="${BRANCH:-main}"

pass=0; fail=0
ok()   { echo "  [PASS] $*"; pass=$((pass+1)); }
bad()  { echo "  [FAIL] $*"; fail=$((fail+1)); }
info() { echo "  [info] $*"; }

echo "== 1. repo liveness =="
vis=$(gh repo view "$REPO" --json visibility,defaultBranchRef,url \
        -q '.visibility + " " + .defaultBranchRef.name + " " + .url' 2>/dev/null)
if [ -n "$vis" ]; then ok "repo reachable — $vis"; else bad "gh repo view failed for $REPO"; fi

echo "== 2. licence detected by GitHub =="
# A LICENSE whose first line is blank is NOT detected -> spdx_id empty / 404.
spdx=$(gh api "repos/$REPO/license" --jq '.license.spdx_id + " " + .path' 2>/dev/null)
if [ -n "$spdx" ]; then ok "licence endpoint: $spdx"
else bad "no licence detected (blank first line in LICENSE is the classic cause)"; fi

echo "== 3. remote tree + blob-SHA match (local vs committed) =="
if [ -n "$LOCAL_DIR" ] && [ -d "$LOCAL_DIR/.git" ]; then
  (
    cd "$LOCAL_DIR" || exit 1
    mismatch=0; checked=0
    while IFS= read -r f; do
      [ -f "$f" ] || continue
      L=$(git hash-object "$f")
      R=$(gh api "repos/$REPO/contents/$f?ref=$BRANCH" --jq .sha 2>/dev/null)
      checked=$((checked+1))
      [ -n "$R" ] && [ "$L" = "$R" ] || { echo "  [FAIL] blob mismatch: $f"; mismatch=$((mismatch+1)); }
    done < <(git ls-files)
    echo "  [info] compared $checked files"
    exit $mismatch
  ) && ok "every tracked file's blob SHA matches the remote" \
    || bad "at least one tracked file differs from the remote (or push incomplete)"
else
  info "no local repo dir given — skipped (pass it as arg 2 for the strongest check)"
fi

echo "== 4. remote has no weights tracked =="
if [ -n "$LOCAL_DIR" ] && [ -d "$LOCAL_DIR/.git" ]; then
  hits=$(cd "$LOCAL_DIR" && git ls-files | grep -E '\.(onnx|pt|pth|h5|safetensors)$' || true)
else
  hits=$(gh api "repos/$REPO/git/trees/$BRANCH?recursive=1" --jq '.tree[].path' 2>/dev/null \
         | grep -E '\.(onnx|pt|pth|h5|safetensors)$' || true)
fi
[ -z "$hits" ] && ok "no model weights tracked" || bad "weights tracked: $hits"

echo "== 5. remote secret / PII scan =="
scan=$(gh api "repos/$REPO/git/trees/$BRANCH?recursive=1" --jq '.tree[] | select(.type=="blob") | .path' 2>/dev/null \
       | grep -E '\.(py|md|json|yaml|yml|example|txt|sh|ipynb)$' || true)
leaks=0
while IFS= read -r f; do
  [ -n "$f" ] || continue
  body=$(gh api "repos/$REPO/contents/$f?ref=$BRANCH" --jq .content 2>/dev/null | base64 -d 2>/dev/null)
  if printf '%s' "$body" | grep -qiE 'sk-[a-zA-Z0-9]{20}|ghp_[A-Za-z0-9]{20}|AKIA[0-9A-Z]{12}|-----BEGIN.*PRIVATE KEY'; then
    echo "  [FAIL] secret-shaped string in $f"; leaks=$((leaks+1))
  fi
  if printf '%s' "$body" | grep -qE '@gmail\.com|[0-9]{10,13}'; then
    echo "  [warn] possible personal contact detail in $f (check it is intentional)"
  fi
done <<< "$scan"
[ "$leaks" -eq 0 ] && ok "no secret-shaped strings in tracked text files" || bad "$leaks file(s) with secrets"

echo "== 6. clean-room clone =="
rm -rf "$CLONE_DIR"
if git clone -q "https://github.com/$REPO" "$CLONE_DIR" 2>/dev/null; then
  n=$(cd "$CLONE_DIR" && git ls-files | wc -l | tr -d ' ')
  ok "clone ok — $n files"
  info "now run the README's FIRST documented command inside $CLONE_DIR before announcing"
else
  bad "clone failed"
fi

echo
echo "passed=$pass failed=$fail"
[ "$fail" -eq 0 ] && { echo "ALL CHECKS PASSED"; exit 0; } || { echo "CHECKS FAILED"; exit 1; }
