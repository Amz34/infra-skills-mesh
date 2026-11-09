# Competitor marketing-site defect sweep (verified, reproducible)

Run this on any competitor/lead site before writing a teardown. Every item returns a hard
signal you can quote in the report — codes, counts, byte sizes — instead of adjectives.
Method first used on `mikshi.mantratec.com` (14-Sep-2026); findings were 9 real defects that
the competitor's own homepage linked to.

## 0. Setup

Save the served HTML once and grep it repeatedly — never re-fetch per check:

```bash
U="https://target.example"
curl -s --max-time 25 "$U/" -o /tmp/t.html
curl -s --max-time 25 "$U/sitemap.xml" -o /tmp/t-sm.xml
```

Keep commands small. Long inline one-liners get blocked by the command parser — write the
script with `write_file` and run `bash /path/script.sh`, or split into 3-4 short commands.

## 1. Asset and metadata integrity (fastest wins)

```bash
curl -s -o /dev/null -w '%{http_code}' "$U\<og:image path\>"     # og:image / twitter:image
curl -s -o /dev/null -w '%{http_code}' "$U/ms-icon-144x144.png"  # PWA/tile icons
curl -s -o /dev/null -w '%{http_code}' "$U/apple-icon-180x180.png"
curl -s -o /dev/null -w '%{http_code}' "$U/favicon.ico"
```

A 404 on `og:image` means **every** WhatsApp/LinkedIn/X share of the site shows no preview
image — a marketing defect with a one-line fix, and a strong "we noticed something you didn't"
opener.

Also compare `<title>` against the URL per page:

```bash
for p in /case-studies /Blog /AboutUs; do echo -n "$p -> "; curl -s "$U$p" | grep -o '<title>[^<]*' | head -1; done
```

Title/URL mismatches (e.g. a case-studies page titled "...Blog") are usually copy-paste bugs.

## 2. Placeholder and soft-404 detection

```bash
grep -o 'href="/[^"]*"' /tmp/t.html | sort | uniq -c | sort -rn | head -20
curl -s -o /dev/null -w '%{http_code} %{size_download}\n' "$U/CommingSoon"
curl -s -o /dev/null -w '%{http_code} %{size_download}\n' "$U/no-such-page-xyz"
```

- A slug like `/CommingSoon` linked dozens of times = capabilities advertised but not shipped.
- A 404 body of `0` bytes = no branded error page.
- Misspelled routes ("Comming") are worth quoting verbatim: they signal build sloppiness.

## 3. Legal / compliance surface

```bash
for p in Privacy-Policy privacy-policy Terms-Conditions terms-of-service; do echo "$p=$(curl -s -o /dev/null -w '%{http_code}' "$U/$p")"; done
grep -oiE 'href="[^"]*(privacy|terms|cookie|refund)[^"]*"' /tmp/t.html | sort -u
```

No privacy policy while the page runs third-party analytics is both a compliance gap
(DPDP/GDPR) and an enterprise-procurement blocker. Count the trackers in the served HTML to
size the exposure.

## 4. Headers and hardening

```bash
curl -sI "$U/" | tr -d '\r'
```

Quote exactly which are missing: CSP, `X-Frame-Options`, `X-Content-Type-Options`,
`Referrer-Policy`, `Permissions-Policy`. Note HSTS `max-age` (30 days is short) and any
version-disclosing `Server:` header.

## 5. Reachability of the product behind the site

```bash
dig +short app.target.example; dig +short target.example
for p in 80 443; do timeout 8 bash -c "cat < /dev/null > /dev/tcp/app.target.example/$p" && echo "$p OPEN" || echo "$p closed/filtered"; done
```

Marketing host answering while the app host times out means the "Login" link on every page is
a dead end from your vantage. State your vantage and stop there — do not claim it is broken
worldwide. Third-party availability checkers are often Cloudflare-bot-blocked; if so, say the
verdict is unverified rather than guessing.

## 6. Structured data — verify before accusing

`grep -c 'application/ld+json'` returning 0 is **not** proof of missing schema. ASP.NET/Razor
outputs the tag as `application/ld&#x2B;json`; the HTML parser decodes `&#x2B;` to `+`, so the
DOM has valid JSON-LD while the raw text does not match a naive grep. Always cross-check in
the live DOM before writing "no structured data":

```python
print(js("document.querySelectorAll('script[type=\"application/ld+json\"]').length"))
print(js("[...document.querySelectorAll('script[type=\"application/ld+json\"]')].map(s=>JSON.parse(s.textContent)['@type'])"))
```

## 7. Content and conversion model

- `grep -c '<loc>' /tmp/t-sm.xml` → indexable page count; check whether `lastmod` is present.
- Extract every CTA's real target: if "Book a demo", "Talk to expert" and "Free audit" all
  POST to the same lead form, the funnel is sales-led with **no self-serve path** — that is
  the competitive opening.
- Cross-check third-party directories (Capterra/G2/IndiaMART) for a "Starting price" field the
  vendor's own site refuses to publish.

## 8. Reporting rules

- Every defect gets its HTTP code, count or byte size next to it.
- Split "verified here" from "unverified / needs buyer-side check" in a separate section.
- Include a strengths section — a teardown that only lists defects reads as a sales pitch and
  gets discounted by the reader.
- Close with "so what changes for us": openings, what not to copy, where they would beat us.
