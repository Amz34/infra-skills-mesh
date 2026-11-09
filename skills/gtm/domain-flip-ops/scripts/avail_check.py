#!/usr/bin/env python3
"""Domain availability checker with MANDATORY control tests.

Usage:
    python3 avail_check.py name1.com name2.ai name3.com ...

Why the control tests: a broken `.ai` parser once reported thousands of taken names as
"available" and the artifact looked like a discovery. Every run therefore checks known-taken
names first; if a control reads "available" the whole run is declared unreliable and exits 1.

Exit codes: 0 = controls passed (candidate rows may be trusted)
            1 = control failure  (method broken — fix before believing anything)
            2 = usage / no candidates
Requires: curl on PATH (RDAP) and `whois` for .ai. No credentials, no API keys.
"""
import subprocess
import sys

CONTROLS = [("google.com", True), ("orchestra.ai", True)]  # name, expected_registered


def _curl_code(url: str, timeout: int = 25) -> str:
    try:
        r = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 10,
        )
        return (r.stdout or "").strip()
    except Exception:
        return "000"


def check_com(name: str):
    """Verisign RDAP for .com — 200 registered, 404 available, anything else unknown."""
    code = _curl_code(f"https://rdap.verisign.com/com/v1/domain/{name}")
    if code == "200":
        return True, "rdap 200"
    if code == "404":
        return False, "rdap 404"
    code2 = _curl_code(f"https://rdap.org/domain/{name}")
    if code2 == "200":
        return True, "rdap.org 200"
    if code2 == "404":
        return False, "rdap.org 404"
    return None, f"unknown ({code}/{code2})"


def check_ai(name: str):
    """whois.nic.ai: a registered name prints a 'Domain Name:' block."""
    try:
        r = subprocess.run(["whois", "-h", "whois.nic.ai", name],
                           capture_output=True, text=True, timeout=30)
    except Exception as e:
        return None, f"whois error {e}"
    out = (r.stdout or "").lower()
    if not out.strip():
        return None, "empty whois"
    if "not found" in out or "no match" in out or "no entries found" in out:
        return False, "whois no match"
    if "domain name:" in out or "registry domain id" in out or "creation date" in out:
        return True, "whois record"
    return None, "unparsed whois"


def check(name: str):
    if name.endswith(".ai"):
        return check_ai(name)
    if name.endswith(".com"):
        return check_com(name)
    code = _curl_code(f"https://rdap.org/domain/{name}")
    if code == "200":
        return True, "rdap.org 200"
    if code == "404":
        return False, "rdap.org 404"
    return None, f"unknown ({code})"


def main() -> int:
    args = [a.strip().lower() for a in sys.argv[1:] if a.strip()]
    if not args:
        print(__doc__)
        return 2

    print("== control tests ==")
    bad = []
    for name, expected in CONTROLS:
        got, why = check(name)
        ok = (got == expected)
        if not ok:
            bad.append(name)
        print(f"  {name:24s} registered={str(got):5s} expected={str(expected):5s} "
              f"{'OK' if ok else 'FAIL'}  ({why})")
    if bad:
        print(f"\nCONTROL FAILURE: {', '.join(bad)} — this method cannot be trusted. "
              "Fix the parser/endpoint before using any result below.")
        return 1

    print("\n== candidates ==")
    free, taken, unknown = [], [], []
    for name in args:
        got, why = check(name)
        label = "AVAILABLE?" if got is False else ("TAKEN" if got else "UNKNOWN")
        print(f"  {name:30s} {label:11s} ({why})")
        (free if got is False else (taken if got else unknown)).append(name)

    print(f"\nlikely-free={len(free)}  taken={len(taken)}  unknown={len(unknown)}")
    if free:
        print("Re-check each of these immediately before paying; 404 means 'likely available' — "
              "the registrar confirms at checkout.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
