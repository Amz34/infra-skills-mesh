#!/usr/bin/env python3
"""ds.py - offline design-intelligence lookup (Hermes-native).

Stdlib only. Reads CSVs from ../data/. ZERO network calls, no install bootstrapping.

Commands
  catalogs                                  list catalogs + row counts
  search  <query> [--catalog C] [-n N]      ranked rows from one catalog (or all)
  system  <query> [--stack S] [--persist D] full design system for a product/industry
  stack   <name> <query> [-n N]             stack-specific guidelines

Vendored dataset: nextlevelbuilder/ui-ux-pro-max-skill (MIT). Search/aggregation
logic here is our own; see SKILL.md for provenance and the attribution note.
"""
import argparse
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
STACKDIR = os.path.join(DATA, "stacks")

# catalog -> (file, boost_columns, display_columns)
CATALOGS = {
    "styles": ("styles.csv", ["Keywords", "Style Category"],
               ["Style Category", "Type", "Keywords", "Primary Colors", "Secondary Colors",
                "Effects & Animation", "Best For", "Do Not Use For", "Complexity",
                "Performance", "Accessibility", "Implementation"]),
    "colors": ("colors.csv", ["Product Type"],
               ["Product Type", "Primary", "On Primary", "Secondary", "Accent",
                "Background", "Foreground", "Card", "Card Foreground", "Muted",
                "Muted Foreground", "Border", "Ring", "Notes"]),
    "products": ("products.csv", ["Product Type", "Keywords"],
                 ["Product Type", "Primary Style Recommendation", "Secondary Styles",
                  "Landing Page Pattern", "Dashboard Style (if applicable)",
                  "Color Palette Focus", "Key Considerations"]),
    "typography": ("typography.csv", ["Mood/Style Keywords", "Best For", "Font Pairing Name"],
                   ["Font Pairing Name", "Category", "Heading Font", "Body Font",
                    "Mood/Style Keywords", "Best For", "CSS Import", "Tailwind Config", "Notes"]),
    "ux": ("ux-guidelines.csv", ["Issue", "Category", "Description"],
           ["Category", "Issue", "Platform", "Description", "Do", "Don't",
            "Code Example Good", "Code Example Bad", "Severity"]),
    "motion": ("motion.csv", ["Category", "Keywords", "Trigger"],
               ["Category", "Intensity Tier", "Keywords", "Trigger", "Duration",
                "Easing", "GSAP Snippet", "Framework Notes", "Do", "Don't",
                "Performance Notes"]),
    "charts": ("charts.csv", ["Data Type", "Keywords", "Best Chart Type"],
               ["Data Type", "Best Chart Type", "Secondary Options", "When to Use",
                "When NOT to Use", "Data Volume Threshold", "Color Guidance",
                "Accessibility Grade", "Accessibility Notes", "Library Recommendation"]),
    "icons": ("icons.csv", ["Icon Name", "Keywords", "Category"],
              ["Category", "Icon Name", "Library", "Import Code", "Usage", "Best For",
               "Semantic Role", "Allowed Contexts"]),
    "landing": ("landing.csv", ["Pattern Name", "Keywords", "Aliases"],
                ["Pattern Name", "Keywords", "Section Order", "Primary CTA Placement",
                 "Color Strategy", "Recommended Effects", "Conversion Optimization"]),
    "app": ("app-interface.csv", ["Category", "Issue", "Keywords"],
            ["Category", "Issue", "Platform", "Description", "Do", "Don't",
             "Code Example Good", "Severity"]),
}

STOP = {"the", "a", "an", "for", "and", "with", "of", "to", "in", "on", "a", "our",
        "that", "this", "is", "are", "it", "we", "you", "need", "want", "make",
        "build", "site", "website", "page", "design", "looking", "like", "new"}


def tokens(q):
    raw = re.split(r"[^a-z0-9+#.]+", q.lower())
    return [t for t in dict.fromkeys(raw) if len(t) > 1 and t not in STOP]


def load(name):
    path = os.path.join(DATA, CATALOGS[name][0])
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r.get("No")]


def score_row(row, qt, boost):
    s = 0.0
    for col, val in row.items():
        if col == "No" or not val:
            continue
        v = str(val).lower()
        w = 3.0 if col in boost else 1.0
        for t in qt:
            if t in v:
                s += w * (2.0 if re.search(r"(?<![a-z0-9])" + re.escape(t), v) else 1.0)
    return s


def rank(name, query, n=5):
    rows = load(name)
    qt = tokens(query)
    if not qt or not rows:
        return []
    boost = CATALOGS[name][1]
    scored = [(score_row(r, qt, boost), r) for r in rows]
    scored = [(s, r) for s, r in scored if s > 0]
    scored.sort(key=lambda x: -x[0])
    return scored[:n]


def fmt_block(title, row, cols, width=100):
    out = [f"### {title}"]
    for c in cols:
        v = str(row.get(c, "") or "").strip()
        if not v:
            continue
        if len(v) > 400:
            v = v[:397] + "..."
        out.append(f"- **{c}**: {v}")
    out.append("")
    return "\n".join(out)


def cmd_catalogs(_a):
    print(f"data dir: {DATA}")
    for name in CATALOGS:
        print(f"  {name:<11} {len(load(name)):>4} rows   {CATALOGS[name][0]}")
    stacks = sorted(f[:-4] for f in os.listdir(STACKDIR)) if os.path.isdir(STACKDIR) else []
    print(f"  stacks     {len(stacks):>4}       {', '.join(stacks)}")


def cmd_search(a):
    names = [a.catalog] if a.catalog != "all" else list(CATALOGS)
    for name in names:
        hits = rank(name, a.query, a.n)
        if not hits:
            continue
        for i, (sc, row) in enumerate(hits, 1):
            key = row.get(CATALOGS[name][1][0], "")
            print(f"\n=== {name} #{i}  score={sc:.1f}  {key}")
            print(fmt_block(CATALOGS[name][0], row, CATALOGS[name][2]))


def stack_rows(name):
    path = os.path.join(STACKDIR, f"{name}.csv")
    if not os.path.exists(path):
        avail = sorted(f[:-4] for f in os.listdir(STACKDIR)) if os.path.isdir(STACKDIR) else []
        print(f"unknown stack '{name}'. available: {', '.join(avail)}", file=sys.stderr)
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r.get("No")]


BOOST = ["Guideline", "Issue", "Category", "Best Practice", "Rule"]


def cmd_stack(a):
    rows = stack_rows(a.name)
    if not rows:
        return
    qt = tokens(a.query)
    scored = sorted([(score_row(r, qt, BOOST), r) for r in rows], key=lambda x: -x[0])
    hit = [x for x in scored if x[0] > 0][: a.n]
    # no keyword hit -> don't lie about it; surface the index of what the stack covers
    if not hit:
        cats = {}
        for r in rows:
            cats.setdefault(r.get("Category") or "misc", 0)
            cats[r.get("Category") or "misc"] += 1
        print(f"# stack: {a.name} — no keyword match for '{a.query}'")
        print("\n## categories covered (query one of these)")
        for c, k in sorted(cats.items()):
            print(f"- {c} ({k} rules)")
        hi = [r for _, r in scored if (r.get("Severity") or "") == "High"][: a.n]
        if hi:
            print("\n## High-severity rules in this stack")
            for r in hi:
                g = r.get("Guideline") or r.get("Category")
                _do = r.get("Do")
                _dont = r.get("Don't")
                print(f"- **{g}**: DO {_do} — DON'T {_dont}")
        return
    cols = [c for c in rows[0] if c != "No"]
    print(f"# stack: {a.name}\n")
    for sc, r in hit:
        title = r.get("Guideline") or r.get("Issue") or r.get("Category") or "rule"
        print(fmt_block(f"{title}  [score={sc:.1f}]", r, cols))


def build_system(query, stack=None, n=6):
    """Aggregate a design system from a product/industry query."""
    qt = tokens(query)
    out = {"query": query, "stack": stack}

    prod = rank("products", query, 1)
    out["product"] = prod[0][1] if prod else None

    # palette: colours.csv is keyed by the same Product Type labels as products.csv
    pal = None
    if out["product"]:
        want = (out["product"].get("Product Type") or "").strip().lower()
        for r in load("colors"):
            if (r.get("Product Type") or "").strip().lower() == want:
                pal = r
                break
    if pal is None:
        c = rank("colors", query, 1)
        pal = c[0][1] if c else None
    out["palette"] = pal

    style_q = query
    if out["product"]:
        style_q += " " + (out["product"].get("Primary Style Recommendation") or "")
    st = rank("styles", style_q, 2)
    out["styles"] = [r for _, r in st]

    type_q = query + " " + " ".join(
        w for w in [" ".join((s.get("Best For") or "").split(",")[:4]) for _, s in st])
    out["type"] = [r for _, r in rank("typography", type_q, 1)]

    # UX rules must never come back empty — a design system without Do/Don't is useless.
    ux = [r for _, r in rank("ux", query, n)]
    if len(ux) < 3:
        have = {r.get("Issue") for r in ux}
        for r in load("ux"):
            if len(ux) >= n:
                break
            if r.get("Issue") not in have and (r.get("Severity") or "") == "High":
                ux.append(r)
                have.add(r.get("Issue"))
    out["ux"] = ux[:n]

    mot = [r for _, r in rank("motion", query, 3)]
    out["motion"] = mot or [r for r in load("motion")[:3]]
    out["landing"] = [r for _, r in rank("landing", query, 1)] or [r for r in load("landing")[:1]]
    if stack:
        rows = stack_rows(stack)
        scored = sorted([(score_row(r, qt, BOOST), r) for r in rows], key=lambda x: -x[0])
        pos = [r for sc, r in scored if sc > 0][:n]
        out["stack_rows"] = pos or [r for _, r in scored[:n]]
    return out


def render(sy):
    L = []
    L.append(f"# Design system — {sy['query']}")
    if sy.get("stack"):
        L.append(f"\n_Stack: {sy['stack']}_")
    p = sy.get("product")
    if p:
        L.append("\n## Product fit")
        L.append(f"- **Product type**: {p.get('Product Type')}")
        L.append(f"- **Primary style**: {p.get('Primary Style Recommendation')}")
        L.append(f"- **Secondary styles**: {p.get('Secondary Styles')}")
        L.append(f"- **Landing pattern**: {p.get('Landing Page Pattern')}")
        L.append(f"- **Palette focus**: {p.get('Color Palette Focus')}")
        L.append(f"- **Key considerations**: {p.get('Key Considerations')}")
    for i, s in enumerate(sy.get("styles") or [], 1):
        L.append(f"\n## Style {i} — {s.get('Style Category')}  ({s.get('Type')})")
        L.append(f"- **Keywords**: {s.get('Keywords')}")
        L.append(f"- **Colors**: {s.get('Primary Colors')} / {s.get('Secondary Colors')}")
        L.append(f"- **Effects & motion**: {s.get('Effects & Animation')}")
        L.append(f"- **Best for**: {s.get('Best For')}")
        L.append(f"- **Do NOT use for**: {s.get('Do Not Use For')}")
        L.append(f"- **Implementation**: {s.get('Implementation')}")
    pal = sy.get("palette")
    if pal:
        L.append(f"\n## Palette — {pal.get('Product Type')}")
        L.append("| token | hex |")
        L.append("|---|---|")
        for k in ["Primary", "On Primary", "Secondary", "On Secondary", "Accent",
                  "Background", "Foreground", "Card", "Card Foreground", "Muted",
                  "Muted Foreground", "Border", "Destructive", "Ring"]:
            if pal.get(k):
                L.append(f"| {k} | `{pal[k]}` |")
        if pal.get("Notes"):
            L.append(f"\n_{pal['Notes']}_")
    for t in sy.get("type") or []:
        L.append(f"\n## Typography — {t.get('Font Pairing Name')}")
        L.append(f"- **Heading**: {t.get('Heading Font')}   **Body**: {t.get('Body Font')}")
        L.append(f"- **Mood**: {t.get('Mood/Style Keywords')}")
        L.append(f"- **Best for**: {t.get('Best For')}")
        if t.get("CSS Import"):
            L.append(f"- **CSS**: `{t['CSS Import']}`")
        if t.get("Tailwind Config"):
            L.append(f"- **Tailwind**: `{t['Tailwind Config']}`")
    if sy.get("landing"):
        lp = sy["landing"][0]
        L.append(f"\n## Landing pattern — {lp.get('Pattern Name')}")
        L.append(f"- **Section order**: {lp.get('Section Order')}")
        L.append(f"- **CTA placement**: {lp.get('Primary CTA Placement')}")
        L.append(f"- **Conversion**: {lp.get('Conversion Optimization')}")
    if sy.get("ux"):
        L.append("\n## UX rules to honour (severity High first)")
        for r in sorted(sy["ux"], key=lambda x: (x.get("Severity") != "High",)):
            _sev = r.get("Severity")
            _do = r.get("Do")
            _dont = r.get("Don't")
            L.append(f"- **[{_sev}] {r.get('Issue')}** ({r.get('Category')}): "
                     f"DO {_do} — DON'T {_dont}")
    if sy.get("motion"):
        L.append("\n## Motion")
        for r in sy["motion"]:
            L.append(f"- **{r.get('Category')}** ({r.get('Intensity Tier')}): {r.get('Trigger')} "
                     f"→ {r.get('Duration')} {r.get('Easing')}")
    if sy.get("stack_rows"):
        L.append(f"\n## {sy['stack']} guidelines")
        for r in sy["stack_rows"]:
            cols = [c for c in r if c != "No"]
            L.append(fmt_block(r.get("Issue") or r.get("Category") or "rule", r, cols))
    return "\n".join(L) + "\n"


def cmd_system(a):
    sy = build_system(a.query, a.stack, a.n)
    if getattr(a, "json", False):
        print(json.dumps(sy, indent=1, ensure_ascii=False))
        return
    text = render(sy)
    print(text)
    if a.persist:
        os.makedirs(a.persist, exist_ok=True)
        path = os.path.join(a.persist, "MASTER.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"\n[persisted] {path}")


def main():
    ap = argparse.ArgumentParser(prog="ds.py", description="offline design intelligence")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("catalogs").set_defaults(fn=cmd_catalogs)

    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--catalog", default="all")
    s.add_argument("-n", type=int, default=5)
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_search)

    y = sub.add_parser("system")
    y.add_argument("query")
    y.add_argument("--stack")
    y.add_argument("--persist")
    y.add_argument("-n", type=int, default=6)
    y.add_argument("--json", action="store_true")
    y.set_defaults(fn=cmd_system)

    k = sub.add_parser("stack")
    k.add_argument("name")
    k.add_argument("query")
    k.add_argument("-n", type=int, default=8)
    k.add_argument("--json", action="store_true")
    k.set_defaults(fn=cmd_stack)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
