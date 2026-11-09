#!/usr/bin/env python3
"""Trigger-precision test: would a real model route each probe to the right skill?

Feeds the model exactly what Hermes puts in the system prompt (name: description per
skill) and asks, per probe, which skill it would load. 5 positives + 3 negatives per
touched skill, plus 3 control probes on untouched skills.
"""
import glob, json, os, re, time, urllib.request

env = {}
for line in open("/home/ubuntu/.hermes/.env"):
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
KEY = env.get("DEEPSEEK_API_KEY", "")
MODEL = env.get("DEEPSEEK_MODEL") or "deepseek-chat"

P = "/home/ubuntu/.hermes/profiles/azwork/skills"
lines, names = [], set()
for f in sorted(glob.glob(P + "/**/SKILL.md", recursive=True)):
    t = open(f, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---", t, re.S)
    if not m:
        continue
    nm = re.search(r"^name:\s*(.+)$", m.group(1), re.M)
    ds = re.search(r"^description:\s*(.+)$", m.group(1), re.M)
    if nm and ds:
        lines.append(f"{nm.group(1).strip()}: {ds.group(1).strip()}")
        names.add(nm.group(1).strip())
INDEX = "\n".join(lines)

SYS = ("You are Hermes Agent. These are your installed skills (name: description). "
       "A skill is auto-loaded only when its description matches the user's request.\n\n"
       + INDEX +
       "\n\nFor the user message, reply with ONLY the exact skill name you would load, "
       "or the single word none if no skill applies. No explanation.")

ANALYSED = {"jev": "jev-cli-ops", "desk": "paper-trading-desk-ops",
            "rw": "remotework-operator", "m365": "microsoft-365-tenant-support"}

# (probe, expected_skill|None, group, alternates_ok)
PROBES = [
    ("jev ka triage lane chalao aur gate counts do", "jev-cli-ops", "jev", []),
    ("python3 -m jev.cli selftest chalao", "jev-cli-ops", "jev", []),
    ("jev live run Cloudflare pe karna hai, 402 aa raha hai", "jev-cli-ops", "jev", []),
    ("queue-gate ne escalate kyun diya, debug karo", "jev-cli-ops", "jev", []),
    ("jev ka calibrate sweep chalao aur results batao", "jev-cli-ops", "jev", []),
    ("freqtrade ka paper trade open karo", None, "jev", []),
    ("Gmail se last invoice nikaalo", None, "jev", []),
    ("invertio ka carousel banao", None, "jev", []),

    ("freqtrade dry-run desk ka API 401 de raha hai, verify karo", "paper-trading-desk-ops", "desk", []),
    ("60 din ka backtest chalao aur numbers do", "paper-trading-desk-ops", "desk", []),
    ("forceenter se paper trade open karo", "paper-trading-desk-ops", "desk", []),
    ("finelo funnel CTA desk se connect hai check karo", "paper-trading-desk-ops", "desk", []),
    ("trading config me exchange.token missing hai", "paper-trading-desk-ops", "desk", []),
    ("jev ka support lane chalao", None, "desk", []),
    ("naya client onboard karna hai", None, "desk", []),
    ("domain flip ki valuation karo", None, "desk", []),

    ("Aamir ne RW-0007 approve kiya, send kar do", "remotework-operator", "rw", []),
    ("job ke liye paypal link mint karo", "remotework-operator", "rw", []),
    ("az.work pipeline ka aaj ka shortlist banao", "remotework-operator", "rw", []),
    ("client X ke liye 500 ka invoice banao", "remotework-operator", "rw", ["finance-quotation-invoicing"]),
    ("remotework repo push fail ho raha hai credential helper", "remotework-operator", "rw", []),
    ("cold email wave bhejo", None, "rw", []),
    ("brain me note add karo", None, "rw", []),
    ("KSA tender eligibility check karo", None, "rw", []),

    ("Teams bot AZ Engineering restart karo, gateway 3978", "microsoft-365-tenant-support", "m365", []),
    ("M365 tenant azengineeringapp pe sign-in issue hai", "microsoft-365-tenant-support", "m365", []),
    ("teams-bot package ka manifest update karo", "microsoft-365-tenant-support", "m365", []),
    ("bot ke liye devtunnels URL change karna hai", "microsoft-365-tenant-support", "m365", []),
    ("AZ Engineering Teams channel me bot reply nahi karta", "microsoft-365-tenant-support", "m365", []),
    ("Gmail IMAP se mail padho", None, "m365", []),
    ("Notion DB sync karo", None, "m365", []),
    ("wrangler se demo site deploy karo", None, "m365", []),

    ("domain flip ki sale odds nikalo", "domain-flip-valuation", "ctrl", []),
    ("Invertio carousel ke liye slides design karo", "invertio-content-production", "ctrl", []),
    ("P6 schedule ka critical path analysis karo", "primavera-p6-integration", "ctrl", []),
]


def ask(prompt):
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": prompt}],
        "temperature": 0, "max_tokens": 1500}).encode()
    req = urllib.request.Request("https://api.deepseek.com/chat/completions", data=body,
                                headers={"Authorization": f"Bearer {KEY}",
                                         "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read())
    u = d.get("usage") or {}
    USAGE["in"] += u.get("prompt_tokens", 0)
    USAGE["out"] += u.get("completion_tokens", 0)
    msg = d["choices"][0]["message"]
    c = (msg.get("content") or "").strip()
    if not c:  # reasoning model: answer may sit in the reasoning trace
        c = (msg.get("reasoning_content") or "").strip().split("\n")[-1]
    return c


def norm(s):
    s = s.strip().strip('.').strip('`').lower()
    s = re.sub(r"[^a-z0-9-]", "", s)
    return s


results, stats = [], {}
USAGE = {"in": 0, "out": 0}
CACHE = "/tmp/trigger_results.json"
cache = {}
if os.path.exists(CACHE):
    for r in json.load(open(CACHE)):
        cache[r["probe"]] = r
for probe, target, grp, alts in PROBES:
    err = None
    if probe in cache and cache[probe].get("verdict") not in ("ERROR", None):
        raw = cache[probe]["got"]
    else:
        try:
            raw = ask(probe)
        except Exception as e:
            raw, err = "", f"{type(e).__name__}: {e}"
    g = norm(str(raw))
    if err:
        verdict = "ERROR"
    elif target:
        verdict = "PASS" if g == target else ("SOFT" if g in alts else "FAIL")
    else:
        # negative: pass when the analysed skill did NOT fire; naming another skill is fine
        verdict = "PASS" if g != ANALYSED.get(grp, "") else "FALSE-FIRE"
    results.append({"group": grp, "probe": probe, "expected": target or f"NOT {ANALYSED.get(grp,'-')}",
                    "got": raw or err, "verdict": verdict})
    s = stats.setdefault(grp, {"PASS": 0, "SOFT": 0, "FAIL": 0, "FALSE-FIRE": 0, "ERROR": 0})
    s[verdict] = s.get(verdict, 0) + 1
    time.sleep(0.2)

print(f"model={MODEL} skills_in_index={len(names)} index_chars={len(INDEX)} probes={len(PROBES)}")
for r in results:
    got = str(r["got"] or "")[:42]
    want = str(r["expected"] or "")[:34]
    print(f"{r['verdict']:<10} [{r['group']:<5}] got={got:<42} want={want:<34} | {r['probe'][:58]}")
print("\nSUMMARY", json.dumps(stats))
print("TOKENS", json.dumps(USAGE))
json.dump(results, open(CACHE, "w"), indent=1)
