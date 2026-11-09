#!/usr/bin/env python3
"""Class-drift checker: markup classes vs CSS selectors, BOTH directions.

WHY: when a page is assembled by hand (new markup written against new CSS,
or new markup dropped onto reused CSS) the two drift apart. A used-but-undefined
class renders an element as a plain unstyled block and looks like a layout bug
("the footer lost its navy background / the cards lost their styling"), while a
defined-but-unused selector is dead weight. Real case: markup said `class="foot"`
while the stylesheet still had `footer.site-foot` -> the whole footer rendered
unstyled and the client saw it as "broken".

USAGE
    python3 check_class_drift.py index.html
    python3 check_class_drift.py public/index.html public/style.css --css-dir public
Exit 0 = no drift. Exit 1 = at least one used-but-undefined class (fix before QA).

Notes
- Classes referenced only from JS (`classList.add('x')`, `querySelector('.x')`)
  count as USED, so a JS-toggled state class that has no CSS rule is reported.
- Ignore-list (framework utilities you do not own): --ignore a,b,c
- Pure stdlib; safe on any static HTML/CSS file set.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CLASS_DEF = re.compile(r"\.(-?[A-Za-z_][-\w]*)")
CLASS_ATTR = re.compile(r"""class\s*=\s*(?:"([^"]*)"|'([^']*)')""")
JS_CLASS = re.compile(
    r"""(?:classList\.(?:add|remove|toggle|contains)|querySelector(?:All)?|closest|matches)\(\s*['"`]\.([-\w]+)"""
)
STYLE_BLOCK = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)


def css_text(paths: list[Path]) -> str:
    out = []
    for p in paths:
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if p.suffix == ".css":
            out.append(txt)
        else:
            out.extend(STYLE_BLOCK.findall(txt))
    return "\n".join(out)


def defined_classes(css: str) -> set[str]:
    # strip CSS comments so commented-out rules do not mask real drift
    return set(CLASS_DEF.findall(re.sub(r"/\*.*?\*/", "", css, flags=re.S)))


def used_classes(html: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for m in CLASS_ATTR.finditer(html):
        for tok in (m.group(1) or m.group(2) or "").split():
            counts[tok] = counts.get(tok, 0) + 1
    for m in JS_CLASS.finditer(html):
        counts.setdefault(m.group(1), 0)
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="html (and optional .css) files")
    ap.add_argument("--css-dir", default=None, help="also load every .css in this dir")
    ap.add_argument("--ignore", default="", help="comma-separated classes to skip")
    ap.add_argument("--quiet-unused", action="store_true", help="do not list unused selectors")
    a = ap.parse_args()

    html_paths = [Path(f) for f in a.files if Path(f).suffix.lower() in (".html", ".htm", ".js", ".svg")]
    css_paths = [Path(f) for f in a.files if Path(f).suffix.lower() == ".css"]
    if a.css_dir:
        css_paths += sorted(Path(a.css_dir).glob("*.css"))
    if not html_paths:
        print("no html files given", file=sys.stderr)
        return 2
    css_all = css_text(css_paths if css_paths else html_paths)
    if not css_all.strip():
        print("no CSS found - nothing to compare", file=sys.stderr)
        return 2

    defined = defined_classes(css_all)
    used: dict[str, int] = {}
    for p in html_paths:
        for k, v in used_classes(p.read_text(encoding="utf-8", errors="ignore")).items():
            used[k] = used.get(k, 0) + v
    ignore = {s for s in a.ignore.split(",") if s}

    undefined = sorted(k for k in used if k not in defined and k not in ignore)
    unused = sorted(defined - set(used))

    print(f"css selectors defined : {len(defined)}")
    print(f"classes used in markup: {len(used)}")
    if unused and not a.quiet_unused:
        print(f"\n-- defined but never used ({len(unused)}) [dead CSS / typo in markup] --")
        print("   " + " ".join(unused[:80]))
    if undefined:
        print(f"\n!! USED BUT UNDEFINED ({len(undefined)}) -> these render UNSTYLED !!")
        for c in undefined:
            print(f"   .{c}  (used {used[c]}x)")
        print("\nFix: add the rule, or rename the markup class to match the stylesheet.")
        return 1
    print("\nOK - every class used in markup has a CSS rule")
    return 0


if __name__ == "__main__":
    sys.exit(main())
