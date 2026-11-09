#!/usr/bin/env python3
"""Hybrid Router — decides where a workload runs: local (Ollama) or cloud.

Decision table (Perplexity hybrid-compute pattern):
  1. PII level high  -> LOCAL  (privacy: sensitive data never leaves the box)
  2. task in classify/extract/summarize + short text -> LOCAL (cost: free tokens)
  3. everything else -> CLOUD  (frontier models for heavy reasoning)

Modes:
  --decide : print routing decision JSON only
  --run    : execute local task via Ollama and print result (cloud = passthrough)

Pipelines (cron scripts, form intake, lead scoring) can call this as their
LLM entry point: sensitive input never reaches the cloud LLM.
"""
import argparse
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pii_gate  # noqa: E402

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
LOCAL_MODEL = os.environ.get("LOCAL_MODEL", "qwen2.5:7b")
FAST_MODEL = os.environ.get("LOCAL_FAST_MODEL", "qwen2.5:3b")

LOCAL_TASKS = {"classify", "extract", "summarize", "normalize", "dedupe", "score"}
MAX_LOCAL_TEXT = 2000

PROMPTS = {
    "classify": "Classify the following text into one category: lead, enquiry, complaint, order, spam, other. Reply with ONLY the category word.\n\nTEXT: {text}",
    "extract": "Extract key structured info from the text (names, phone, email, amounts, dates). Reply as compact JSON.\n\nTEXT: {text}",
    "summarize": "Summarize in 2-3 bullet points, same language as the text.\n\nTEXT: {text}",
    "score": "Score this sales lead 0-10 based on urgency and buying signals. Reply with ONLY the number and one short reason.\n\nTEXT: {text}",
    "normalize": "Normalize: fix spelling, format phone as +<country><number>, keep all facts intact. Reply with the normalized text only.\n\nTEXT: {text}",
}


def decide(text: str, task: str):
    verdict = pii_gate.classify(text, use_llm=True)
    if verdict["pii"]:
        return {
            "route": "local",
            "reason": f"privacy:PII level {verdict['level']} ({verdict['categories']})",
            "verdict": verdict,
        }
    if task in LOCAL_TASKS and len(text) <= MAX_LOCAL_TEXT:
        return {"route": "local", "reason": f"cost:task={task},len={len(text)}", "verdict": verdict}
    return {"route": "cloud", "reason": "heavy_reasoning", "verdict": verdict}


def run_local(text: str, task: str, model: str):
    prompt = PROMPTS.get(task, "Respond helpfully.\n\n{text}").format(text=text[:4000])
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "keep_alive": "30m",
    }
    req = urllib.request.Request(
        f"{OLLAMA_URL}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.load(resp)
    return data["choices"][0]["message"]["content"].strip()


def main():
    ap = argparse.ArgumentParser(description="Hybrid local/cloud router")
    ap.add_argument("--text", help="text to route")
    ap.add_argument("--file", help="read text from file")
    ap.add_argument("--stdin", action="store_true", help="read from stdin")
    ap.add_argument("--task", default="classify", choices=list(PROMPTS.keys()) + ["generic"])
    ap.add_argument("--run", action="store_true", help="execute the routed step")
    ap.add_argument("--model", default=None, help="local model override (default qwen2.5:7b)")
    args = ap.parse_args()

    if args.file:
        text = open(args.file, encoding="utf-8", errors="replace").read()
    elif args.stdin:
        text = sys.stdin.read()
    else:
        text = args.text or ""

    decision = decide(text, args.task)

    if not args.run:
        print(json.dumps(decision, ensure_ascii=False))
        return

    if decision["route"] == "local":
        model = args.model or (LOCAL_MODEL if args.task in ("generic",) else FAST_MODEL)
        result = run_local(text, args.task, model)
        print(json.dumps({"route": "local", "model": model, "result": result}, ensure_ascii=False))
    else:
        print(json.dumps({"route": "cloud", "result": text, "note": "send to cloud LLM unchanged"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
