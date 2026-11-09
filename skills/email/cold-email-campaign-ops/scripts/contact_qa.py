#!/usr/bin/env python3
"""Contact QA + dedupe gate for cold email/SMS waves (channel-agnostic).

Usage
-----
    python3 contact_qa.py candidates.json [--exclude wave1.json ...] [--max-firm-chars 22]

Input  : JSON list of {"firm": str, "email": str?, "mobile": str?} (extra keys kept).
Output : prints one JSON list to stdout = PASSING records, one per firm, deduped,
         plus a short `# rejected: <reason> xN` summary on stderr.

Why this exists
---------------
Raw scrape output inflates a wave with junk that burns sender reputation:
placeholder addresses, vendor/aggregator domains, addresses on an unrelated
domain, duplicate firms, and landline "mobiles". Hard rules live in code here.

Gates applied
-------------
* Email: no `firstname`/`yourname`/`example`/`test`/`info@example` locals;
  domain must not be an aggregator/broker; no `+` tags; DNS-shape check.
* Domain-match: when the record carries a `domain`/`site` field the email domain
  must match it, else the address belongs to someone else (common scrape error).
* Mobile (default India +91): strip non-digits, drop leading 91/0, require 10
  digits starting 6-9, reject landline STD code pairs 62-65, reject 0000/5555 tails.
* One record per firm per channel (first wins); firms listed in --exclude files
  are dropped entirely (previous waves).
"""
import argparse
import json
import re
import sys

AGGREGATOR = (
    "indiamart", "tradeindia", "exportersindia", "go4worldbusiness", "justdial",
    "tracxn", "tendershark", "b2bmit", "eworldtradefair", "linkedin.com",
    "facebook.com", "zaubacorp", "thecompanycheck", "tofler", "dialindia",
)
BAD_LOCAL = ("firstname", "lastname", "yourname", "your.email", "example",
             "test", "noreply", "no-reply", "email", "sample", "abc")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def norm_firm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def qa_email(rec):
    e = (rec.get("email") or "").strip().lower()
    if not e:
        return None, "no-email"
    if not EMAIL_RE.match(e) or e.count("@") != 1:
        return None, "bad-shape"
    local, _, dom = e.partition("@")
    if any(b in local for b in BAD_LOCAL):
        return None, "placeholder-local"
    if "+" in local:
        return None, "plus-tag"
    if any(a in dom for a in AGGREGATOR):
        return None, "aggregator-domain"
    hint = (rec.get("domain") or rec.get("site") or "").lower()
    root = dom.split(".")[-2] if dom.count(".") >= 1 else dom
    if hint and root not in hint and hint not in dom:
        return None, "domain-mismatch"
    return e, None


def qa_mobile(rec):
    raw = rec.get("mobile") or rec.get("phone") or ""
    d = re.sub(r"\D", "", raw)
    if d.startswith("0091"):
        d = d[4:]
    if d.startswith("91") and len(d) > 10:
        d = d[2:]
    if d.startswith("0") and len(d) > 10:
        d = d[1:]
    if len(d) != 10 or d[0] not in "6789":
        return None, "not-mobile"
    if d[:2] in ("62", "63", "64", "65"):
        return None, "landline-std"
    if d.endswith("0000") or d.endswith("5555"):
        return None, "fake-tail"
    return "+91" + d, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("candidates")
    ap.add_argument("--exclude", action="append", default=[],
                    help="JSON file of already-contacted records (repeatable)")
    args = ap.parse_args()

    recs = json.load(open(args.candidates))
    if isinstance(recs, dict):
        recs = list(recs.values())

    skip = set()
    for f in args.exclude:
        try:
            prev = json.load(open(f))
            if isinstance(prev, dict):
                prev = list(prev.values())
            skip |= {norm_firm(p.get("firm")) for p in prev}
        except Exception as exc:  # missing/corrupt previous wave must NOT silently pass
            sys.exit(f"exclude file unreadable ({f}): {exc}")

    seen_firm, out, rejects = set(), [], {}
    for r in recs:
        key = norm_firm(r.get("firm"))
        if not key:
            rejects["no-firm"] = rejects.get("no-firm", 0) + 1
            continue
        if key in skip:
            rejects["already-contacted"] = rejects.get("already-contacted", 0) + 1
            continue
        if key in seen_firm:
            rejects["dup-firm"] = rejects.get("dup-firm", 0) + 1
            continue
        em, why_e = qa_email(r)
        mb, why_m = qa_mobile(r)
        if not em and not mb:
            rejects[why_e or why_m or "no-contact"] = rejects.get(why_e or "no-contact", 0) + 1
            continue
        seen_firm.add(key)
        rec = dict(r)
        if em:
            rec["email"] = em
        else:
            rec.pop("email", None)
        if mb:
            rec["mobile"] = mb
        else:
            rec.pop("mobile", None)
            rec.pop("phone", None)
        out.append(rec)

    print(json.dumps(out, indent=1))
    print(f"# pass {len(out)} | " + " ".join(f"rejected:{k} x{v}" for k, v in sorted(rejects.items())),
          file=sys.stderr)


if __name__ == "__main__":
    main()
