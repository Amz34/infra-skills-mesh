#!/usr/bin/env python3
"""PII Gate — local, deterministic-first sensitivity classifier + redactor.

Perplexity hybrid-compute inspired (post: lnkd.in/p/d2-JAxf5):
decide where a workload runs BEFORE any cloud LLM call.

Layers (cheapest first):
  1. Regex patterns  -> instant, zero tokens, deterministic
  2. Luhn check      -> credit cards
  3. Sensitivity keywords -> flags candidate text
  4. Local LLM (qwen2.5:3b) -> confirmation ONLY for keyword-only sensitivity

Modes:
  --check   : JSON verdict {pii, level, categories, matches}
  --redact  : replace PII spans with [REDACTED:<type>]
  --classify: full pipeline (regex + keyword + LLM confirm) -> JSON

Exit code 0 always; verdict in stdout JSON. Never sends data to cloud.
"""
import argparse
import json
import os
import re
import sys
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
FAST_MODEL = os.environ.get("LOCAL_FAST_MODEL", "qwen2.5:3b")

# ---------- patterns ----------
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3}[\s-]?\d{4}(?:[\s-]?\d{2,4})?"
)
CC_RAW_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
SA_ID_RE = re.compile(r"\b[12]\d{9}\b")  # Saudi national ID / Iqama
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
PASSPORT_RE = re.compile(r"\b[A-Z]{1,2}\d{6,9}\b")
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
URL_CRED_RE = re.compile(r"\bhttps?://[^\s:@/]+:[^\s@/]+@")

SENSITIVE_KEYWORDS = [
    "bloodwork", "blood work", "tax return", "tax", "litigation", "medical record",
    "diagnosis", "patient", "treatment", "prescription", "bank statement", "bank account",
    "credit card", "salary", "payslip", "passport", "national id", "iqama", "insurance claim",
    "court", "lawsuit", "contract", "nda", "financial", "otp", "password", "secret",
    "تقرير طبي", "تشخيص", "مريض", "حساب بنكي", "بطاقة ائتمان", "راتب", "جواز سفر",
]

PATTERNS = [
    ("email", EMAIL_RE),
    ("phone", PHONE_RE),
    ("sa_id", SA_ID_RE),
    ("iban", IBAN_RE),
    ("passport", PASSPORT_RE),
    ("ip", IP_RE),
    ("url_credentials", URL_CRED_RE),
]


def luhn_valid(digits: str) -> bool:
    digits = re.sub(r"\D", "", digits)
    if len(digits) < 13 or len(digits) > 19:
        return False
    total = 0
    reverse = digits[::-1]
    for i, ch in enumerate(reverse):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def scan(text: str):
    """Return {type: [spans]} with (start, end) tuples, deduped."""
    found = {}
    for name, pattern in PATTERNS:
        for m in pattern.finditer(text):
            found.setdefault(name, []).append((m.start(), m.end()))
    # credit cards: Luhn-validated only
    for m in CC_RAW_RE.finditer(text):
        if luhn_valid(m.group()):
            found.setdefault("credit_card", []).append((m.start(), m.end()))
    return found


def keyword_hit(text: str):
    lower = text.lower()
    return [k for k in SENSITIVE_KEYWORDS if k in lower]


def llm_confirm_sensitive(text: str) -> bool:
    """Local LLM confirms whether keyword-flagged text is truly sensitive.
    Fallback: keyword hit itself is enough (fail closed toward local)."""
    snippet = text[:1200]
    prompt = (
        "You are a privacy router. Does this text contain sensitive personal or "
        "confidential information (medical, financial, legal, identity, credentials)?\n"
        'Reply with ONLY one word: YES or NO.\n\nTEXT:\n' + snippet
    )
    payload = {
        "model": FAST_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8,
        "temperature": 0,
        "keep_alive": "30m",
    }
    try:
        req = urllib.request.Request(
            f"{OLLAMA_URL}/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.load(resp)
        answer = data["choices"][0]["message"]["content"].strip().upper()
        return answer.startswith("YES")
    except Exception:
        # Fail closed: if the local model is unavailable, treat as sensitive.
        return True


def redact(text: str, spans_by_type) -> str:
    """Replace spans with [REDACTED:<type>]. Overlapping spans merged first."""
    spans = sorted(
        ((s, e, t) for t, ss in spans_by_type.items() for s, e in ss),
        key=lambda x: (x[0], -x[1]),
    )
    merged = []
    for s, e, t in spans:
        if merged and s < merged[-1][1]:
            if e > merged[-1][1]:
                merged[-1] = (merged[-1][0], e, merged[-1][2])
        else:
            merged.append([s, e, t])
    out = text
    for s, e, t in reversed(merged):
        out = out[:s] + f"[REDACTED:{t}]" + out[e:]
    return out


def classify(text: str, use_llm: bool = True):
    spans = scan(text)
    keywords = keyword_hit(text)
    categories = sorted(set(list(spans.keys()) + (["keyword:" + k for k in keywords])))
    if spans:
        level = "high"  # hard PII: phone/email/id/iban/cc/ip/credentials
    elif keywords:
        if use_llm:
            level = "high" if llm_confirm_sensitive(text) else "medium"
        else:
            level = "medium"
    else:
        level = "low"
    return {
        "pii": level != "low",
        "level": level,
        "categories": categories,
        "match_count": sum(len(v) for v in spans.values()),
        "redacted_text": redact(text, spans) if spans else text,
    }


def main():
    ap = argparse.ArgumentParser(description="PII gate: classify/redact locally")
    ap.add_argument("--text", help="text to analyze")
    ap.add_argument("--file", help="read text from file")
    ap.add_argument("--stdin", action="store_true", help="read text from stdin")
    ap.add_argument("--mode", choices=["check", "redact", "classify"], default="classify")
    ap.add_argument("--no-llm", action="store_true", help="skip local LLM confirmation")
    args = ap.parse_args()

    if args.file:
        text = open(args.file, encoding="utf-8", errors="replace").read()
    elif args.stdin:
        text = sys.stdin.read()
    else:
        text = args.text or ""

    if args.mode == "check":
        spans = scan(text)
        result = {
            "pii": bool(spans),
            "categories": sorted(spans.keys()),
            "match_count": sum(len(v) for v in spans.values()),
        }
    elif args.mode == "redact":
        result = {"redacted_text": redact(text, scan(text))}
    else:
        result = classify(text, use_llm=not args.no_llm)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
