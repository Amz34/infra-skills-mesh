#!/usr/bin/env python3
"""One-shot: inject Google Search Console verification meta into all HTML pages.
Usage: python3 add_gsc_verify.py '<content-token>'  (token = google-site-verification content value)
Replaces an existing verification tag if present, else inserts before <title>.
Runs over *.html + ar/*.html (bilingual sites). Delete after use / keep gitignored.
"""
import glob, sys

token = sys.argv[1].strip()
assert len(token) > 10, "token too short"
tag = f'<meta name="google-site-verification" content="{token}" />'
count = 0
for path in glob.glob("*.html") + glob.glob("ar/*.html"):
    html = open(path, encoding="utf-8").read()
    if "google-site-verification" in html:
        start = html.index('<meta name="google-site-verification"')
        end = html.index("/>", start) + 2
        html = html[:start] + tag + html[end:]
    else:
        html = html.replace("<title>", "  " + tag + "\n  <title>", 1)
    open(path, "w", encoding="utf-8").write(html)
    count += 1
print(f"Injected verification tag into {count} files")
