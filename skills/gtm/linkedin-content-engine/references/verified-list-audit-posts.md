# Verified Correction Posts — user sends a document, you audit it, you post the truth

Session that produced this recipe: Aamir forwarded a ChatGPT-compiled "2026 Internship Calendar" PDF
(10 government internship schemes) with the instruction *"expertly analyze and post, concise, all links
in description, punchy hooky, curiosity driven with CTA, also craft a high pitch image."*
Output: https://www.linkedin.com/feed/update/urn:li:share:7504495029474934784 (live, image attached).

Use this whenever the input is a forwarded list / calendar / "top 10" / scheme sheet / tender table —
the value you add is **verification**, not summarising.

---

## 1. Extract the claims AND the links (a PDF's links are not in its text)

```bash
mkdir -p /tmp/pdfx && cp <user-pdf> /tmp/pdfx/in.pdf && cd /tmp/pdfx
pdftotext -layout in.pdf - > t.txt          # claims/table text — DROPS hyperlinks
pdftohtml -c -i -noframes -q in.pdf out.html
grep -o 'href="[^"]*"' out.html | sed 's/href="//;s/"$//' | sort -u > links.txt
grep -c 'utm_source=chatgpt.com' links.txt  # provenance tell (see §3)
```

Print big extraction output through `execute_code` in compact slices — a direct terminal/web dump gets
silently elided ("1 lines output"), which loses the data and forces a re-run.

## 2. Audit every row on four axes (not just the numbers)

| Axis | What to verify | Why it decides the outcome |
|---|---|---|
| Amount / age / duration | official portal or notice, **dated** | revised schemes keep the old figures circulating for months (₹5,000 → ₹9,000; age 21–24 → 18–25) |
| Eligibility filters | gender, city tier, marks, streams, final-year status | the filter, not the stipend, is what rejects people |
| Window / deadline | which days each month, is it open **today** | a list with "zero deadlines" is useless |
| Link destination + liveness | official domain vs blog, and HTTP state | 4 of 10 rows pointed at ClearTax / Unstop / GovtInternship / eGovtSchemes; one official path was a dead 404 |

Liveness sweep:

```bash
for u in <urls>; do curl -s -o /dev/null -w "%{http_code} $u\n" -L --max-time 15 -A 'Mozilla/5.0' "$u"; done
```

**Gov portals return 403/404 to bare curl yet load fine in a real browser** — confirm in
`browser_exec` before you call a link dead or run a "works / broken" claim on it. Same for
certificate warnings: a Chrome `ERR_CERT_AUTHORITY_INVALID` on one machine is not publishable
evidence, so do not put it in the post.

## 3. The provenance tell (best hook ingredient)

Forwarded AI-compiled lists keep `?utm_source=chatgpt.com` on their links. It is **countable**, so
it is honest, curiosity-driving, and it explains the stale numbers in one line:

> *"10 of its 20 links still carry `?utm_source=chatgpt.com`. Compiled by an AI, forwarded by humans,
> verified by nobody."*

Count it (`grep -c`) — say the number you measured, never "every link".

## 4. Self-audit your own headline before publishing

The punchiest sentence is usually the false one. First draft said **"7 things in it are wrong"** —
re-reading the source against the evidence showed only 4 rows genuinely wrong, 2 merely incomplete,
and 2 correct. Honest, still punchy, and defensible:

> **"4 numbers are outdated, 6 links don't go to a government site, and there is not a single
> deadline in it — except one."**

Rule: the hook number must equal the verified findings, row by row. A scheme/jobs audience checks.

## 5. Card — 4:5 (1200×1500), render → look → patch

- Layout that works: kicker ("VERIFIED <date>") → red-accent headline → one row per finding
  (`name` / struck-through wrong value / corrected value) → a "what's open now" date strip →
  footer ("official portals in the caption").
- Loop: build HTML → `google-chrome --headless=new --screenshot=card.png --window-size=1200,1500
  --hide-scrollbars --force-device-scale-factor=1 file://...` → **look at the PNG with vision** →
  patch CSS → re-render. Two or three passes is normal.
- **Leftover vertical gap = add verified rows, never inflate padding.** This session filled ~330px by
  adding correction cards and a dates strip, which raised the card's value instead of ballooning it.
- Inanimate visuals only — no faces, no emoji on the card.
- Working file: `/home/ubuntu/az_internship_calendar/card.html` (+ `card.png`, `linkedin-post.txt`).

## 6. Caption skeleton (≤3000 chars — count with `len()`)

```
hook line (curiosity + the verifiable tell)
what I did ("I opened all 10 official portals this morning")
numbered corrections — only verified rows; mark the rows the source got RIGHT as right
official portal list — every link, one per line, "verify here, never on an aggregator"
"open today (<date>): …" strip (the deadlines the source omitted)
save / repost CTA + comment-keyword CTA
```

Trim by tightening sentences, **never by dropping links** — the user asked for all of them. Post with
links in the body (this user's explicit ask); the audit post has no "link in first comment" variant,
the list IS the value.

## 7. Post + verify

Image flow + verification: `linkedin-api-posting` skill (`/rest/images` → PUT → `/rest/posts`; confirm
attachment by matching the image-URN prefix in the rendered `media.licdn.com` asset URL).
Script template: `~/.hermes/scripts/post_linkedin_internship_calendar.py`.

## 8. Handoff message (Hinglish, short)

Live URL · the single best catch · corrections as bullets · **the comment-keyword CTA needs the user to
DM replies** (an API cannot do it) · offer the 1-page verified tracker as the DM asset.
