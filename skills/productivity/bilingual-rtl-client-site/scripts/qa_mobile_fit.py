#!/usr/bin/env python3
"""qa_mobile_fit.py - gate: every page must fit a phone without a pinch-out.

Why this exists: the Arabic (dir=rtl) edition of the KSA property once measured
10389px wide because a honeypot input used `left:-9999px` (negative inline
overflow is scrollable in RTL), so phones had to pinch out. Static checks never
saw it, so this gate renders every page in real headless Chrome at 390/360/320
CSS px and inspects the live layout.

Two signals per page/width:
  1. documentElement.scrollWidth vs clientWidth  (page can be panned sideways)
  2. any element whose box sticks out past the viewport and is NOT clipped by an
     ancestor that fits (overflow-x: hidden/clip/auto/scroll) - this catches
     content silently cut off by an overflow-x:clip guard.
Exit 0 = every page fits, 1 = overflow found, 2 = harness failure.

Usage: python3 build/qa_mobile_fit.py [--widths 390,360,320] [--verbose]
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = "/home/ubuntu/clients/invertio"
DIRS = [("KSA", os.path.join(ROOT, "advisory-site/public")),
        ("INDIA", os.path.join(ROOT, "india-site/public"))]
CHROME = (shutil.which("google-chrome") or shutil.which("google-chrome-stable")
          or shutil.which("chromium") or "/usr/bin/google-chrome")

WRAPPER = """<!doctype html><html><head><meta charset="utf-8"><title>mobile fit</title>
<style>html,body{margin:0;background:#fff}iframe{border:0;display:block;margin:0}</style></head>
<body><div id="host"></div>
<script>
const CASES = %(cases)s;
const host = document.getElementById('host');
const frames = CASES.map(c => {
  const f = document.createElement('iframe');
  f.style.width = c.width + 'px'; f.style.height = '900px'; f.src = c.url;
  f.dataset.label = c.label; f.dataset.slug = c.slug; f.dataset.width = c.width;
  host.appendChild(f); return f;
});

const MEASURE = `(function () {
  const doc = document.documentElement;
  const vw = doc.clientWidth;
  const scrollable = doc.scrollWidth;
  function clippedByAncestor(el) {
    // Only an INNER scroller excuses a wide box (.table-scroll etc).
    // The html/body overflow-x:clip guard is not an excuse - it hides content.
    for (let p = el.parentElement; p && p !== document.body && p !== document.documentElement; p = p.parentElement) {
      const cs = getComputedStyle(p);
      if (/hidden|clip|auto|scroll/.test(cs.overflowX)) {
        const r = p.getBoundingClientRect();
        if (r.right <= vw + 1) return true;
      }
    }
    return false;
  }
  const wide = [];
  const all = document.querySelectorAll('body *');
  for (const el of all) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    const over = Math.max(r.right - vw, -r.left);
    if (over <= 1) continue;
    if (clippedByAncestor(el)) continue;
    wide.push([Math.round(over), el.tagName + '.' + (el.className || '').toString().split(' ')[0]].join(':'));
  }
  wide.sort(function (a, b) { return parseInt(b) - parseInt(a); });
  return JSON.stringify({vw: vw, scrollable: scrollable, wide: wide.slice(0, 4), n: wide.length});
})()`;

function report() {
  if (document.getElementById('mf-out')) return;
  const pre = document.createElement('pre'); pre.id = 'mf-out';
  const lines = frames.map(f => {
    let m;
    try { m = JSON.parse(f.contentWindow.eval(MEASURE)); }
    catch (e) {
      return 'MF ' + f.dataset.label + ' ' + f.dataset.slug + ' ' + f.dataset.width + ' ERROR ' + e.message;
    }
    const bad = (m.scrollable > m.vw + 1) || (m.n > 0);
    return 'MF ' + f.dataset.label + ' ' + f.dataset.slug + ' ' + f.dataset.width +
           ' scroll=' + m.scrollable + '/' + m.vw + ' wideElements=' + m.n +
           ' ' + (bad ? 'FAIL' : 'PASS') + (m.n ? ' [' + m.wide.join(', ') + ']' : '');
  });
  pre.textContent = lines.join('\\n');
  document.body.appendChild(pre);
}
let pending = frames.length;
frames.forEach(f => f.addEventListener('load', () => { if (--pending <= 0) report(); }));
setTimeout(report, 8000);
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--widths", default="390,360,320")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    widths = [int(w) for w in args.widths.split(",")]

    cases = []
    for label, d in DIRS:
        for path in sorted(glob.glob(os.path.join(d, "*.html"))):
            for w in widths:
                cases.append({"label": label, "slug": os.path.basename(path), "width": w,
                              "url": "file://" + path})
    if not cases:
        print("no pages found")
        return 2

    tmp = tempfile.mkdtemp(prefix="mf-")
    wrapper = os.path.join(tmp, "wrap.html")
    with open(wrapper, "w", encoding="utf-8") as fh:
        fh.write(WRAPPER % {"cases": json.dumps(cases)})
    cmd = [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
           "--allow-file-access-from-files", "--virtual-time-budget=30000", "--dump-dom",
           "--user-data-dir=" + os.path.join(tmp, "prof"), "file://" + wrapper]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=420).stdout
    except subprocess.TimeoutExpired:
        print("HARNESS FAILURE: chrome timed out")
        return 2

    lines = [l.strip() for l in out.splitlines() if l.strip().startswith("MF ")]
    if not lines:
        print("HARNESS FAILURE: no measurements returned (chrome dump had %d chars)" % len(out))
        return 2

    fails, errors = [], []
    for l in lines:
        p = l.split()
        if len(p) < 5:
            continue
        verdict = "FAIL" if "FAIL" in l else ("ERROR" if "ERROR" in l else "PASS")
        if verdict == "FAIL":
            fails.append(l[len("MF "):])
        elif verdict == "ERROR":
            errors.append(l[len("MF "):])
    if args.verbose:
        for l in lines:
            print(l)
    pages = len(cases) // len(widths)
    print("mobile fit: %d measurements, %d pages x %s px" % (len(lines), pages, widths))
    if fails:
        print("OVERFLOW FINDINGS (%d):" % len(fails))
        for f in fails[:25]:
            print("  " + f)
    if errors:
        print("HARNESS/CROSS-FRAME ERRORS (%d):" % len(errors))
        for e in errors[:10]:
            print("  " + e)
    if fails:
        return 1
    if errors:
        return 2
    print("PASS: no page pans sideways and nothing sticks out of the viewport")
    return 0


if __name__ == "__main__":
    sys.exit(main())
