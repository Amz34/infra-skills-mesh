#!/usr/bin/env python3
"""Lead scoring pipeline — hybrid compute (Perplexity pattern).

Chain: raw lead (stdin/text/file) OR form payload (--payload JSON)
  1. PII gate  -> classify + redact, FULLY LOCAL (deterministic-first + 3b confirm)
  2. Local score -> qwen2.5:7b (OpenAI-compat /v1) with optional client rubric
  3. Cloud step  -> ONLY if zero PII remains and --cloud-summary given:
                    sanitized text -> DeepSeek for a refined summary (fail-safe:
                    PII present -> cloud auto-skipped, text never leaves the box)
  4. Store       -> ~/.hermes/leads/scored.jsonl (REDACTED text only, never raw)

Usage:
  echo "raw lead text" | python3 lead_pipeline.py --stdin
  python3 lead_pipeline.py --text "lead text"
  python3 lead_pipeline.py --file lead.txt
  python3 lead_pipeline.py --payload '{"q1":"v1","q2":"v2"}' --rubric "..." --threshold 60
  ... --cloud-summary --lang ar|en --model qwen2.5:7b --no-store

Output: single JSON object to stdout:
  {route, reason, pii{...}, score, qualified, summary, redacted_text,
   cloud_summary: {used, model, summary} | None}
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pii_gate  # noqa: E402

LOCAL_URL = os.environ.get("OLLAMA_V1_URL", "http://localhost:11434/v1")
DEFAULT_MODEL = "qwen2.5:7b"
DEFAULT_RUBRIC = (
    "Qualified lead: real business need, decision-maker signal, budget or "
    "timeline mentioned. Unqualified: generic enquiry, no need, no budget, "
    "no timeline, or competitor-shopping with no urgency."
)
DEFAULT_THRESHOLD = 60
STORAGE = os.path.expanduser("~/.hermes/leads/scored.jsonl")
LANG_NAMES = {"en": "English", "ar": "Arabic"}


def _load_env(path=os.path.expanduser("~/.hermes/.env")) -> dict:
    env = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return env


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text).strip()
    text = re.sub(r"\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    raise ValueError(f"Model returned non-JSON: {text[:300]}")


def _build_lead_text(payload: dict | None, raw: str) -> str:
    if payload:
        lines = []
        for k, v in payload.items():
            if v not in (None, "", []):
                lines.append(f"- {k}: {v}")
        return "\n".join(lines) or "- (no answers provided)"
    return raw


def score_prompt(text: str, rubric: str, threshold: int, lang: str) -> str:
    lang_name = LANG_NAMES.get(lang, "English")
    system = (
        "You are a strict senior sales qualification engine. Score the lead "
        "against the rubric. Be honest and strict: unqualified leads cost money, "
        "so do not inflate scores. Answer ONLY with valid JSON, no markdown, no commentary.\n\n"
        f"CLIENT RUBRIC:\n{rubric}\n\n"
        f"PASS THRESHOLD: score >= {threshold} means qualified.\n"
        'JSON SCHEMA: {"score": <int 0-100>, "qualified": <bool>, '
        f'"summary": "<1-2 sentence lead summary, decisive tone, MUST be written in {lang_name}>"}}'
    )
    return f"{system}\n\nLEAD:\n{text}\n\nReturn the JSON now."


def score_local(text: str, rubric: str, threshold: int, lang: str, model: str) -> dict:
    """Score via Ollama /v1 (OpenAI-compatible). Local only — no cloud path here."""
    body = {
        "model": model,
        "messages": [{"role": "user", "content": score_prompt(text, rubric, threshold, lang)}],
        "temperature": 0.1,
        "max_tokens": 200,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        f"{LOCAL_URL}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=420) as resp:
            data = json.loads(resp.read())
    except Exception as e:  # noqa: BLE001
        return {"score": 0, "qualified": False, "summary": f"local scoring error: {e}"}
    content = data["choices"][0]["message"].get("content") or ""
    try:
        result = _extract_json(content)
    except Exception:  # noqa: BLE001 — truncated/invalid JSON must never crash the pipe
        result = {}
    return {
        "score": max(0, min(100, int(result.get("score", 0)))),
        "qualified": bool(result.get("qualified", False)),
        "summary": str(result.get("summary", "")).strip(),
    }


def cloud_summary(text: str) -> dict | None:
    """Refined 1-2 sentence summary via DeepSeek. Caller MUST have gated PII."""
    env = _load_env()
    key = env.get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return {"used": False, "reason": "no DEEPSEEK_API_KEY in ~/.hermes/.env"}
    url = env.get("LLM_API_URL", "https://api.deepseek.com/chat/completions")
    model = env.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You write crisp 1-2 sentence lead summaries. Reply with plain text only."},
            {"role": "user", "content": f"Summarize this lead for a salesperson:\n\n{text}"},
        ],
        "temperature": 0.2,
        "max_tokens": 200,
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        summary = data["choices"][0]["message"].get("content", "").strip()
        return {"used": True, "model": model, "summary": summary}
    except Exception as e:  # noqa: BLE001
        return {"used": False, "reason": f"cloud error: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Hybrid lead scoring pipeline (PII-gated).")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--stdin", action="store_true", help="read raw lead from stdin")
    src.add_argument("--text", help="raw lead text")
    src.add_argument("--file", help="read raw lead from file")
    src.add_argument("--payload", help='form payload JSON, e.g. \'{"q1":"v1"}\'')
    ap.add_argument("--rubric", default=DEFAULT_RUBRIC, help="client scoring rubric")
    ap.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    ap.add_argument("--lang", default="en", choices=["en", "ar"])
    ap.add_argument("--model", default=DEFAULT_MODEL, help="local model (default qwen2.5:7b)")
    ap.add_argument("--cloud-summary", action="store_true",
                    help="refine summary via DeepSeek ONLY if zero PII remains")
    ap.add_argument("--no-store", action="store_true", help="skip writing scored.jsonl")
    args = ap.parse_args()

    if args.stdin:
        raw = sys.stdin.read()
    elif args.text:
        raw = args.text
    elif args.file:
        with open(os.path.expanduser(args.file), encoding="utf-8") as fh:
            raw = fh.read()
    else:
        raw = ""

    payload = None
    if args.payload:
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError:
            print(json.dumps({"error": "invalid --payload JSON"}))
            return 2
    if not raw.strip() and not payload:
        print(json.dumps({"error": "no input"}))
        return 1

    try:
        lead_text = _build_lead_text(payload, raw)
        verdict = pii_gate.classify(lead_text)  # fully local (deterministic + 3b confirm)

        if verdict.get("pii"):
            work_text = verdict["redacted_text"]  # classify() already redacts (merge-first)
            route, reason = "local", f"privacy:PII level {verdict.get('level')} ({', '.join(verdict.get('categories', []))})"
        else:
            work_text = lead_text
            route, reason = "local", "cost:local tasks + short text stay local"

        scored = score_local(work_text, args.rubric, args.threshold, args.lang, args.model)

        cloud = None
        if args.cloud_summary:
            if verdict.get("pii"):
                cloud = {"used": False, "reason": "PII present — cloud step auto-skipped (fail-safe)"}
            else:
                cloud = cloud_summary(work_text)  # only PII-free text may leave the box

        out = {
            "route": route,
            "reason": reason,
            "pii": {k: verdict.get(k) for k in ("pii", "level", "categories")},
            "score": scored["score"],
            "qualified": scored["qualified"],
            "summary": cloud["summary"] if cloud and cloud.get("used") else scored["summary"],
            "redacted_text": work_text if verdict.get("pii") else None,
            "cloud_summary": cloud,
        }

        if not args.no_store:
            os.makedirs(os.path.dirname(STORAGE), exist_ok=True)
            record = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "route": route,
                "reason": reason,
                "pii_level": verdict.get("level"),
                "score": out["score"],
                "qualified": out["qualified"],
                "summary": out["summary"],
                "redacted_text": work_text,  # raw text is NEVER persisted
                "cloud_summary_used": bool(cloud and cloud.get("used")),
            }
            with open(STORAGE, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")

        print(json.dumps(out, ensure_ascii=False))
        return 0
    except Exception as e:  # noqa: BLE001 — never emit empty stdout
        print(json.dumps({"error": f"pipeline failed: {e}"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
