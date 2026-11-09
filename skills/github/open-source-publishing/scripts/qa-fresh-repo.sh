#!/usr/bin/env bash
# qa-fresh-repo.sh — independent QA of a repo from a STRANGER'S path.
#
# Usage: qa-fresh-repo.sh <git-url-or-local-path> [out-dir]
#
# Clones into /tmp (never your working tree), runs the gates a stranger would run,
# prints a compact PASS/FAIL/SKIP table plus the clone SHA, and logs everything.
# Pass a LOCAL path to clean-room a commit you have not pushed yet:
#   qa-fresh-repo.sh /home/ubuntu/publish/agent-operating-model ~/ops/artifacts/aom-qa
#
# Exit 0 = no hard gate failed.  1 = a hard gate failed.  2 = bad usage.
set -u

SRC="${1:-}"
[ -n "$SRC" ] || { echo "usage: qa-fresh-repo.sh <git-url-or-local-path> [out-dir]"; exit 2; }
OUT="${2:-$PWD/qa-artifacts}"
mkdir -p "$OUT"
NAME="$(basename "${SRC%.git}")"
CLONE="/tmp/qa-fresh-$NAME-$$"
LOG="$OUT/qa-fresh-$NAME-$(date -u +%Y%m%dT%H%M%SZ).log"
HARD_FAIL=0

say() { printf '%s\n' "$*" | tee -a "$LOG"; }

# gate <HARD|SOFT> <label> <cmd...>
gate() {
  local kind="$1" label="$2"; shift 2
  { printf '\n### %s\n$ %s\n' "$label" "$*"; } >>"$LOG"
  if "$@" >>"$LOG" 2>&1; then
    say "PASS  $label"
  else
    say "FAIL  $label"
    [ "$kind" = HARD ] && HARD_FAIL=1
  fi
}

skip() { say "SKIP  $1"; }

# ---------- clone (hard) ----------
rm -rf "$CLONE"
if ! git clone -q "$SRC" "$CLONE" >>"$LOG" 2>&1; then
  say "FAIL  clone ($SRC)"; say "see $LOG"; exit 1
fi
SHA="$(git -C "$CLONE" rev-parse --short HEAD 2>/dev/null || echo '?')"
SUBJ="$(git -C "$CLONE" log -1 --pretty=%s 2>/dev/null || echo '?')"
say "### CLONE: $SHA $SUBJ"
say "log:   $LOG"
cd "$CLONE" || exit 1

# ---------- secrets in tracked files (hard) ----------
if git ls-files -z | xargs -0 grep -lniE 'gho_|ghp_|sk-[A-Za-z0-9]{16,}|AIza[0-9A-Za-z_-]{20,}|xox[baprs]-|AKIA[0-9A-Z]{12,}|BEGIN [A-Z ]*PRIVATE KEY' >>"$LOG" 2>/dev/null; then
  say "FAIL  no secrets tracked (see $LOG)"; HARD_FAIL=1
else
  say "PASS  no secrets tracked"
fi

# ---------- python gates ----------
if [ -f pyproject.toml ] || [ -f pytest.ini ] || [ -d tests ]; then
  if python3 -m pytest --version >/dev/null 2>&1; then
    gate HARD "pytest" python3 -m pytest -q
    gate SOFT "coverage" python3 -m pytest -q --cov --cov-report=term-missing
  else
    skip "pytest (not installed)"
  fi
  if python3 -m ruff --version >/dev/null 2>&1; then
    gate SOFT "ruff check" python3 -m ruff check .
  else
    skip "ruff (not installed)"
  fi
  # module-name convention used by these repos: <pkg>.audit
  for mod in governance.audit audit; do
    if [ -e "${mod%%.*}" ]; then gate SOFT "audit ($mod)" python3 -m "$mod"; break; fi
  done
fi

# ---------- node gates ----------
if [ -f package.json ]; then
  if grep -q '"test"' package.json; then gate SOFT "npm test" npm test --silent; else skip "npm test (no script)"; fi
  if grep -q '"lint"' package.json; then gate SOFT "npm lint" npm run lint --silent; else skip "npm lint (no script)"; fi
fi

# ---------- worktree hygiene (soft: informational) ----------
if [ -d .git ]; then
  if [ -z "$(git status --porcelain)" ]; then say "PASS  clone worktree clean"; else say "WARN  clone worktree dirty"; fi
fi

# ---------- verdict ----------
printf '\n=== VERDICT %s @ %s: %s ===\n' "$NAME" "$SHA" \
  "$([ "$HARD_FAIL" -eq 0 ] && echo 'no hard gate failed' || echo 'HARD GATE FAILED')" | tee -a "$LOG"
[ "$HARD_FAIL" -eq 0 ] || exit 1
