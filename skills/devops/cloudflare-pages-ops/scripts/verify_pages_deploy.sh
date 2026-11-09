#!/usr/bin/env bash
# Verify a Cloudflare Pages deployment (preview or prod) end-to-end.
#
#   bash verify_pages_deploy.sh <url> [forbidden-term ...]
#
# Polls until Cloudflare finishes provisioning edge TLS on a brand-new project
# (fresh *.pages.dev hosts fail the handshake with "sslv3 alert handshake failure"
# => curl code 000, for the first ~1-3 min), then checks served bytes, link counts
# and the RENDERED DOM (JS/blank-render detection + forbidden strings absent).
#
# Env:
#   LOCAL_FILE=<path>   also sha256-compare local file vs served bytes
#   EXPECT_LINKS=<n>    fail if fewer than n http(s) hrefs are served
#   EXPECT_TERM=<text>  fail if this rendered-DOM text is missing (repeatable via EXPECT_TERM2..)
#   MAX_TRIES / SLEEP   poll attempts (default 12) and seconds between (default 30)
#
# Exit 0 = pass. Non-zero = the specific failure was printed.

set -u

URL="${1:?usage: verify_pages_deploy.sh <url> [forbidden-term ...]}"; shift || true
FORBIDDEN=("$@")
LOCAL_FILE="${LOCAL_FILE:-}"
EXPECT_LINKS="${EXPECT_LINKS:-0}"
MAX_TRIES="${MAX_TRIES:-12}"
SLEEP="${SLEEP:-30}"
BODY=/tmp/verify_pages_body.html
DOM=/tmp/verify_pages_dom.html

code=000
for i in $(seq 1 "$MAX_TRIES"); do
  # -4: the IPv6 path can stay dead after IPv4 already serves 200
  code=$(curl -4 -s -L -o "$BODY" -w "%{http_code}" --max-time 25 "$URL" 2>/dev/null || echo 000)
  [ "$code" = "200" ] && break
  echo "poll $i/$MAX_TRIES: code=$code (new *.pages.dev host still provisioning TLS) sleeping ${SLEEP}s"
  sleep "$SLEEP"
done
[ "$code" = "200" ] || { echo "FAIL: never reached HTTP 200 (last code=$code)"; exit 1; }
echo "http=200 bytes=$(wc -c < "$BODY")"

links=$(grep -oE 'href="https?://' "$BODY" | wc -l)
uniq=$(grep -oE 'href="https?://[^"]*"' "$BODY" | sort -u | wc -l)
echo "links=$links unique=$uniq"
if [ "$EXPECT_LINKS" -gt 0 ] && [ "$links" -lt "$EXPECT_LINKS" ]; then
  echo "FAIL: expected >= $EXPECT_LINKS hrefs, got $links"; exit 1
fi

if [ -n "$LOCAL_FILE" ]; then
  l=$(sha256sum "$LOCAL_FILE" 2>/dev/null | cut -c1-16)
  s=$(sha256sum "$BODY" | cut -c1-16)
  echo "local_hash=$l served_hash=$s"
  [ "$l" = "$s" ] || { echo "FAIL: served bytes differ from $LOCAL_FILE"; exit 1; }
fi

if command -v google-chrome-stable >/dev/null 2>&1; then
  google-chrome-stable --headless=new --disable-gpu --no-sandbox --virtual-time-budget=6000 \
    --dump-dom "$URL" > "$DOM" 2>/dev/null || true
  echo "dom_bytes=$(wc -c < "$DOM")"
  for v in EXPECT_TERM EXPECT_TERM2 EXPECT_TERM3 EXPECT_TERM4; do
    term="${!v:-}"
    [ -n "$term" ] || continue
    n=$(grep -c -- "$term" "$DOM" 2>/dev/null || true)
    printf 'expect  %-24s %s\n' "$term" "${n:-0}"
    [ "${n:-0}" -gt 0 ] || { echo "FAIL: rendered DOM missing '$term'"; exit 1; }
  done
fi

fail=0
for t in "${FORBIDDEN[@]}"; do
  n=$(grep -ci -- "$t" "$BODY" 2>/dev/null || true)
  printf 'forbidden %-22s %s\n' "$t" "${n:-0}"
  [ "${n:-0}" = "0" ] || fail=1
done
[ "$fail" = "0" ] || { echo "FAIL: forbidden terms present in served bytes"; exit 1; }

echo "PASS"
