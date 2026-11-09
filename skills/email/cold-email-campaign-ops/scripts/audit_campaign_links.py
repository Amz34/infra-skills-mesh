#!/usr/bin/env python3
"""Audit a cold-outreach campaign dir for links that changed or died.

Use when a client site/domain is renamed, replaced, or deleted while campaign
templates and pending waves still reference the old URL.

Checks, in order:
  1. Text files + zip/xlsx artifacts (grep cannot see inside a zip) for --old.
  2. Reports where the replacement domain already appears.
  3. Optional: import the template module and measure the real SMS length per
     lead (GSM-7) so a longer domain does not silently turn 1 SMS into 2.
  4. Optional: dry-render the sender script if it supports --render.

Exit code 0 = no dead reference left anywhere; 1 = something survived.

Usage:
  audit_campaign_links.py ~/az_consultants/outreach \
      --old az-consultants.pages.dev --new azconsultants-india.pages.dev \
      --tmpl tmpl.py --leads sms_send2.json,wave2_send.json

Notes:
  - URL change only matters for the *SMS* cap when the link sits in the SMS
    template; always measure the WORST-led (longest firm name), never the mean.
  - Delete __pycache__ after editing a template module, or stale .pyc files keep
    reporting the old string (use --clean-pyc).
"""
import argparse
import importlib.util
import json
import pathlib
import re
import shutil
import sys

ZIP_SUFFIXES = {".xlsx", ".xlsm", ".docx", ".zip", ".pptx"}
TEXT_SUFFIXES = {".py", ".sh", ".txt", ".json", ".csv", ".md", ".html", ".js", ".xml", ".toml", ".yaml", ".yml"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__"}


def iter_files(root: pathlib.Path):
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        yield p


def count_zip(path: pathlib.Path, needles):
    import zipfile

    counts = {n: 0 for n in needles}
    try:
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if not name.endswith(".xml"):
                    continue
                blob = z.read(name).decode("utf-8", "ignore")
                for n in needles:
                    counts[n] += len(re.findall(re.escape(n), blob))
    except Exception as exc:  # corrupt/legacy archive — report, do not crash
        print(f"  ! could not read {path.name}: {exc}")
    return counts


def scan(root: pathlib.Path, old: str, new: str):
    text_hits, zip_hits = [], []
    for p in iter_files(root):
        suffix = p.suffix.lower()
        if suffix == ".pyc":
            continue
        if suffix in ZIP_SUFFIXES:
            counts = count_zip(p, (old, new))
            if counts[old] or counts[new]:
                zip_hits.append((p, counts))
        else:
            try:
                t = p.read_text(errors="ignore")
            except Exception:
                continue
            n_old, n_new = t.count(old), t.count(new)
            if n_old or n_new:
                text_hits.append((p, n_old, n_new, suffix in TEXT_SUFFIXES))
    return text_hits, zip_hits


def sms_report(root: pathlib.Path, tmpl_name: str, leads_csv: str):
    tmpl_path = root / tmpl_name
    if not tmpl_path.exists():
        print(f"  ! template module {tmpl_name} not found — skipped")
        return
    spec = importlib.util.spec_from_file_location("audited_tmpl", tmpl_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "sms"):
        print("  ! template has no sms() — skipped")
        return
    for leads_name in [s.strip() for s in leads_csv.split(",") if s.strip()]:
        lp = root / leads_name
        if not lp.exists():
            print(f"  ! {leads_name} not found — skipped")
            continue
        leads = json.loads(lp.read_text())
        if not isinstance(leads, list) or not leads:
            print(f"  ! {leads_name}: no leads — skipped")
            continue
        rendered = [(len(mod.sms(l)), l) for l in leads]
        worst_len, worst_lead = max(rendered, key=lambda x: x[0])
        over = sum(1 for ln, _ in rendered if ln > 160)
        gsm7 = all(ord(ch) <= 0x7F for _, l in rendered[:1] for ch in mod.sms(l)) if rendered else True
        flag = "OK" if over == 0 else f"OVER BUDGET on {over} lead(s)"
        print(f"  {leads_name}: n={len(rendered)} worst={worst_len} over160={over} gsm7_ascii={gsm7} -> {flag}")
        if over:
            print(f"    worst lead: {json.dumps(worst_lead, ensure_ascii=False)[:160]}")
            print(f"    rendered : {mod.sms(worst_lead)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", help="campaign directory to audit")
    ap.add_argument("--old", required=True, help="dead/old domain or URL fragment")
    ap.add_argument("--new", required=True, help="replacement domain")
    ap.add_argument("--tmpl", default="tmpl.py", help="template module name inside the dir")
    ap.add_argument("--leads", default="", help="comma-separated lead JSON files for SMS length check")
    ap.add_argument("--render", action="store_true", help="also try `python3 send_campaign.py --render`")
    ap.add_argument("--clean-pyc", action="store_true", help="delete __pycache__ dirs first")
    args = ap.parse_args()

    root = pathlib.Path(args.dir).expanduser().resolve()
    if not root.is_dir():
        print(f"not a directory: {root}")
        return 2
    if args.clean_pyc:
        removed = 0
        for cache in root.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)
            removed += 1
        print(f"cleaned {removed} __pycache__ dir(s)")

    print(f"== scanning {root}\n   old='{args.old}'  new='{args.new}'")
    text_hits, zip_hits = scan(root, args.old, args.new)

    dead_text = [h for h in text_hits if h[1]]
    print(f"\n[text] {len(text_hits)} file(s) mention either domain, {len(dead_text)} still hold the OLD one")
    for p, n_old, n_new, is_text in text_hits:
        tag = "DEAD" if n_old else "ok  "
        print(f"  {tag} {p.relative_to(root)}  old={n_old} new={n_new}")

    print(f"\n[zip/xlsx] {len(zip_hits)} artifact(s) mention either domain")
    dead_zip = 0
    for p, counts in zip_hits:
        dead_zip += counts[args.old]
        tag = "DEAD" if counts[args.old] else "ok  "
        print(f"  {tag} {p.relative_to(root)}  old={counts[args.old]} new={counts[args.new]}")

    if args.leads:
        print("\n[sms] length check (GSM-7 target: worst case <= 160 = 1 SMS)")
        sms_report(root, args.tmpl, args.leads)

    if args.render:
        script = root / "send_campaign.py"
        if script.exists():
            import subprocess

            print("\n[render] dry render (no sends)")
            out = subprocess.run([sys.executable, str(script), "--render"], cwd=str(root),
                                 capture_output=True, text=True).stdout
            for line in out.splitlines():
                if args.old in line or args.new in line or re.search(r"sms|SMS", line):
                    print("  " + line.strip()[:160])

    remaining = len(dead_text) + dead_zip
    print(f"\nRESULT: {remaining} surviving OLD reference(s) — "
          f"{'PASS (0 dead refs)' if remaining == 0 else 'FAIL, fix the source template and rebuild generated artifacts'}")
    return 0 if remaining == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
