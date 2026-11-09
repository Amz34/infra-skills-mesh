#!/usr/bin/env python3
"""scope_creep.py -- deterministic scope-creep triage for one git diff.

Read-only and OFFLINE: no network calls, no writes, no changes to the working
tree, index, commits or branches. Every signal is a review prompt, never proof
of intent.

Upstream concept: Shubhamsaboo/awesome-llm-apps -> agent_skills/scope-creep-detector
(Apache-2.0, Matt Van Horn). This file is an independent Hermes-native
implementation (stdlib only, no code shared with upstream).

Usage
-----
  python3 scope_creep.py --repo . --intent "fix null deref in parser" --json
  python3 scope_creep.py --repo . --staged --intent "add retry to webhook" --md
  python3 scope_creep.py --repo . --base main --intent "parser fix"
  git diff --staged | python3 scope_creep.py --diff - --intent "parser fix"
  python3 scope_creep.py --repo . --intent "..." --hunk-threshold 80

Exit: 0 = report produced (triage is never fatal). 1 = usage/git error.
"""

import argparse
import json
import os
import re
import subprocess
import sys

BRANCH_WORDS = {
    "fix", "fixes", "fixed", "bug", "bugfix", "feat", "feature", "features",
    "change", "changes", "changed", "update", "updates", "updated", "add",
    "adds", "added", "make", "makes", "support", "supporting", "improve",
    "improves", "the", "a", "an", "to", "in", "on", "of", "for", "and", "or",
    "with", "without", "into", "from", "that", "this", "it", "its", "new",
    "when", "while", "so", "then", "also", "only", "not", "no", "is", "are",
}
DEP_MANIFESTS = ("requirements", "package.json", "pyproject.toml")
CI_PREFIX = ".github/"
BUILD_NAMES = ("dockerfile", "docker-compose", "makefile", "cmake",
               "cmakelists.txt", "meson.build", "procfile", "makefile.am")
CONFIG_SUFFIX = (".toml", ".yml", ".yaml", ".ini", ".cfg", ".conf")
RENAME_WINDOW = 12          # diff lines between removed and added declaration
PY_DECL = re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)")
PY_CLASS = re.compile(r"^\s*class\s+([A-Za-z_]\w*)")
JS_DECL = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)")
JS_CLASS = re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)")
PKG_LINE = re.compile(r'^[\s\-"]*"?([A-Za-z0-9_.@/\-]+)"?\s*(?:==|>=|<=|~=|>|<|\^|:)\s*[^,\s]')


def sh(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("%s -> %s" % (" ".join(cmd), (p.stderr or "").strip()))
    return p.stdout


def get_diff(args):
    if args.diff:
        if args.diff == "-":
            return sys.stdin.read(), "stdin"
        with open(args.diff, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(), args.diff
    repo = args.repo or "."
    if args.staged:
        return sh(["git", "-C", repo, "diff", "--cached", "--no-color",
                   "--no-ext-diff", "--unified=3"]), "staged (git diff --cached)"
    if args.base:
        return sh(["git", "-C", repo, "diff", "--no-color", "--no-ext-diff",
                   "--unified=3", "%s...HEAD" % args.base]), "branch vs %s" % args.base
    return sh(["git", "-C", repo, "diff", "--no-color", "--no-ext-diff",
               "--unified=3"]), "working tree"


def tokens(text):
    out = []
    for raw in re.split(r"[^0-9A-Za-z]+", text.lower()):
        if len(raw) < 2 or raw.isdigit() or raw in BRANCH_WORDS:
            continue
        out.append(raw)
    return out


def parse(diff):
    """Return [{'path':..., 'adds':int, 'dels':int, 'hunks':[[(sign, text)]]}]."""
    files, cur, hunk = [], None, None
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            cur = {"path": None, "adds": 0, "dels": 0, "hunks": [], "binary": False}
            files.append(cur)
            hunk = None
        elif cur is None:
            continue
        elif line.startswith("+++ "):
            cur["path"] = line[6:].strip().split("\t")[0]
        elif line.startswith("--- "):
            if cur["path"] is None:
                cur["path"] = line[6:].strip().split("\t")[0]
        elif line.startswith("Binary files") or line.startswith("GIT binary patch"):
            cur["binary"] = True
        elif line.startswith("@@"):
            hunk = []
            cur["hunks"].append(hunk)
        elif hunk is not None and line[:1] in "+-":
            if line.startswith("+++") or line.startswith("---"):
                continue
            hunk.append((line[0], line[1:]))
            if line[0] == "+":
                cur["adds"] += 1
            else:
                cur["dels"] += 1
    for f in files:
        if f["path"] in (None, "/dev/null"):
            f["path"] = "?unknown"
        f["path"] = re.sub(r"^(?:a|b)/", "", f["path"])
    return [f for f in files if not f["binary"]]


def dep_candidates(f):
    name = os.path.basename(f["path"]).lower()
    if not any(m in name for m in DEP_MANIFESTS):
        return []
    added, removed = [], []
    for hunk in f["hunks"]:
        for sign, text in hunk:
            line = text.strip()
            if name.startswith("requirements"):
                m = re.match(r"^([A-Za-z0-9_.\-]+)\s*(?:[=<>~!]=?.*)?$", line)
            else:
                m = PKG_LINE.match(line)
            if not m:
                continue
            (added if sign == "+" else removed).append(m.group(1).lower())
    new = [d for d in added if d not in removed]
    seen, out = set(), []
    for d in new:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def api_renames(f):
    out = []
    for hunk in f["hunks"]:
        decls = []
        for i, (sign, text) in enumerate(hunk):
            for rx, kind in ((PY_DECL, "function"), (PY_CLASS, "class"),
                             (JS_DECL, "function"), (JS_CLASS, "class")):
                m = rx.match(text)
                if m:
                    decls.append((i, sign, kind, m.group(1)))
                    break
        gone = [d for d in decls if d[1] == "-"]
        came = [d for d in decls if d[1] == "+"]
        for g in gone:
            for c in came:
                if g[2] == c[2] and g[3] != c[3] and abs(g[0] - c[0]) <= RENAME_WINDOW:
                    out.append({"from": g[3], "to": c[3], "kind": g[2]})
    return out


def config_kind(path):
    p = path.lower()
    if p.startswith(CI_PREFIX):
        return "CI"
    base = os.path.basename(p)
    if base in ("makefile", "makefile.am") or base.startswith("dockerfile") \
            or base.startswith("docker-compose") or base in BUILD_NAMES \
            or p.endswith(".dockerfile"):
        return "build"
    if p.endswith(CONFIG_SUFFIX):
        return "config"
    return None


def formatting_only(f):
    pairs = []
    for hunk in f["hunks"]:
        dels = [t for s, t in hunk if s == "-"]
        adds = [t for s, t in hunk if s == "+"]
        if len(dels) != len(adds) or not dels:
            return False
        pairs.append((dels, adds))
    if not pairs:
        return False
    def nows(line):
        return re.sub(r"\s+", "", line)

    for dels, adds in pairs:
        if sorted(nows(d) for d in dels) != sorted(nows(a) for a in adds):
            return False
        if any(not nows(d) for d in dels):
            return False
    return True


def classify(files, intent, threshold):
    itok = tokens(intent)
    iset = set(itok)
    report = {
        "intent": intent,
        "intent_tokens": itok,
        "in_scope": [],
        "likely_creep": [],
        "new_deps": [],
        "api_renames": [],
        "config_edits": [],
        "stats": {"files": 0, "additions": 0, "deletions": 0,
                  "subsystems": [], "oversized_hunks": [],
                  "formatting_only": []},
    }
    subs = set()
    for f in files:
        path = f["path"]
        subs.add(path.split("/")[0] if "/" in path else "(root)")
        report["stats"]["files"] += 1
        report["stats"]["additions"] += f["adds"]
        report["stats"]["deletions"] += f["dels"]
        ptok = set(tokens(path.replace("/", " ").replace("_", " ")))
        shared = sorted(ptok & iset)
        signals = []
        for h in f["hunks"]:
            churn = len(h)
            if churn > threshold:
                signals.append("oversized hunk (%d changed lines)" % churn)
                report["stats"]["oversized_hunks"].append(
                    {"path": path, "churn": churn})
        deps = dep_candidates(f)
        if deps:
            signals.append("adds dependency: %s" % ", ".join(deps))
            report["new_deps"].append({"path": path, "packages": deps})
        renames = api_renames(f)
        if renames:
            for r in renames:
                signals.append("public %s rename %s -> %s"
                               % (r["kind"], r["from"], r["to"]))
            report["api_renames"].append({"path": path, "renames": renames})
        ck = config_kind(path)
        if ck:
            signals.append("%s edit" % ck)
            report["config_edits"].append({"path": path, "kind": ck})
        if formatting_only(f):
            signals.append("formatting-only file")
            report["stats"]["formatting_only"].append(path)
        entry = {"path": path, "adds": f["adds"], "dels": f["dels"],
                 "signals": signals}
        if not itok:
            entry["reason"] = "no usable intent tokens - verify relatedness by hand"
            entry["suggested"] = "review"
            report["likely_creep"].append(entry)
        elif shared:
            entry["reason"] = "shares intent token(s): %s" % ", ".join(shared)
            report["in_scope"].append(entry)
        else:
            entry["reason"] = "no intent/path token overlap"
            if any(s.startswith(("adds dependency", "public")) for s in signals) \
                    or "formatting-only file" in signals:
                entry["suggested"] = "split"
            elif any(s.endswith("edit") for s in signals):
                entry["suggested"] = "justify or split"
            else:
                entry["suggested"] = "review then split"
            report["likely_creep"].append(entry)
    report["stats"]["subsystems"] = sorted(subs)
    report["verdict"] = (
        "no scope signal detected" if not report["likely_creep"] else
        "%d path(s) flagged" % len(report["likely_creep"]))
    report["caveat"] = ("Deterministic triage, not proof of intent. A zero "
                        "overlap score can mean a vague intent or a necessary "
                        "indirect file. Confirm before recommending a split.")
    return report


def to_md(r):
    L = []
    L.append("# Scope report")
    L.append("")
    L.append("**Intent:** %s" % (r["intent"] or "(none given - branch fallback)"))
    L.append("")
    s = r["stats"]
    L.append("**Diff:** %d file(s), +%d/-%d, %d subsystem(s): %s"
             % (s["files"], s["additions"], s["deletions"],
                len(s["subsystems"]), ", ".join(s["subsystems"])))
    L.append("")
    L.append("**Verdict:** %s" % r["verdict"])
    L.append("")
    L.append("## In scope (token overlap with intent)")
    L.extend(["- `%s` (+%d/-%d) - %s" % (e["path"], e["adds"], e["dels"], e["reason"])
              for e in r["in_scope"]] or ["- (none)"])
    L.append("")
    L.append("## Likely creep")
    if r["likely_creep"]:
        for e in r["likely_creep"]:
            sig = ("; signals: " + "; ".join(e["signals"])) if e["signals"] else ""
            L.append("- `%s` (+%d/-%d) - %s%s -> **%s**"
                     % (e["path"], e["adds"], e["dels"], e["reason"], sig,
                        e["suggested"]))
    else:
        L.append("- (none)")
    L.append("")
    if r["new_deps"] or r["api_renames"] or r["config_edits"]:
        L.append("## Cross-cutting edits")
        for d in r["new_deps"]:
            L.append("- new dependency in `%s`: %s" % (d["path"], ", ".join(d["packages"])))
        for a in r["api_renames"]:
            for rr in a["renames"]:
                L.append("- %s rename in `%s`: %s -> %s"
                         % (rr["kind"], a["path"], rr["from"], rr["to"]))
        for c in r["config_edits"]:
            L.append("- %s edit: `%s`" % (c["kind"], c["path"]))
        L.append("")
    L.append("## Disposition table")
    L.append("| path | disposition | why |")
    L.append("|---|---|---|")
    for e in r["in_scope"]:
        L.append("| `%s` | keep | %s |" % (e["path"], e["reason"]))
    for e in r["likely_creep"]:
        L.append("| `%s` | %s | %s%s |" % (e["path"], e["suggested"], e["reason"],
                                           ("; " + "; ".join(e["signals"])) if e["signals"] else ""))
    L.append("")
    if s["oversized_hunks"] or s["formatting_only"]:
        L.append("## Churn watch")
        for o in s["oversized_hunks"]:
            L.append("- oversized hunk in `%s` (%d changed lines)" % (o["path"], o["churn"]))
        for p in s["formatting_only"]:
            L.append("- formatting-only file: `%s`" % p)
        L.append("")
    L.append("> %s" % r["caveat"])
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Scope-creep triage for one git diff (read-only, offline).")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--intent", default="")
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--base")
    ap.add_argument("--diff")
    ap.add_argument("--hunk-threshold", type=int, default=80)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--md", action="store_true")
    a = ap.parse_args()

    intent = a.intent.strip()
    source = None
    try:
        diff, source = get_diff(a)
    except Exception as e:  # git missing / not a repo / bad base
        print("error: %s" % e, file=sys.stderr)
        return 1
    if not intent:
        try:
            intent = sh(["git", "-C", a.repo, "rev-parse", "--abbrev-ref", "HEAD"]).strip()
            source += " (intent from branch name)"
        except Exception:
            intent = ""
    files = parse(diff)
    r = classify(files, intent, a.hunk_threshold)
    r["diff_source"] = source
    if a.json or not a.md:
        print(json.dumps(r, indent=2))
    else:
        print(to_md(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
