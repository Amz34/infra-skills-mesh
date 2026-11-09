#!/usr/bin/env python3
"""Sitemap probe — fetch & analyze any site's sitemap for SEO gap analysis.
Usage: python3 sitemap_probe.py domain1.com domain2.com ...
Tries: /sitemap.xml, /sitemap_index.xml, robots.txt Sitemap: directive.
"""
import urllib.request, re, sys
from collections import Counter

def fetch(url, t=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"})
    return urllib.request.urlopen(req, timeout=t).read().decode('utf-8', 'ignore')

def get_sitemap(domain):
    """Try common sitemap locations. Returns (source_url, locs, body)."""
    for u in [f"https://{domain}/sitemap.xml", f"https://{domain}/sitemap_index.xml",
              f"https://{domain}/robots.txt"]:
        try:
            body = fetch(u)
            if 'sitemap' in u:
                locs = re.findall(r'<loc>(.*?)</loc>', body)
                if locs:
                    return u, locs, body
            else:  # robots.txt → Sitemap: directive
                sm = re.findall(r'Sitemap:\s*(.+)', body, re.I)
                if sm:
                    body2 = fetch(sm[0].strip())
                    locs = re.findall(r'<loc>(.*?)</loc>', body2)
                    return sm[0].strip(), locs, body2
        except Exception:
            continue
    return None, [], ""

def main():
    for domain in sys.argv[1:]:
        src, locs, _ = get_sitemap(domain)
        print(f"\n=== {domain} ===")
        if not locs:
            print("  SITEMAP: NOT FOUND")
            continue
        print(f"  Source: {src}")
        print(f"  Total URLs: {len(locs)}")
        types = Counter()
        for l in locs:
            path = l.replace(f"https://{domain}", "").replace("http://", "").strip("/")
            types["home" if not path else path.split("/")[0]] += 1
        print("  Page types:", dict(types.most_common(12)))
        print("  Sample:", locs[:5])

if __name__ == "__main__":
    main()
