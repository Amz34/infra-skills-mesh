# Compiling a post inventory from local records (2026-09-04, verified)

Task: "list all my LinkedIn post links for <client/campaign>". Do NOT start from
session_search — go straight to the filesystem sources below, in this order.

## Sources of truth (order matters)

1. **Campaign `POSTS_LOG.md`** — maintained dated pipe-row log kept next to the
   posting scripts, e.g. `~/clients/<client>/email-pitch/linkedin/POSTS_LOG.md`.
   Primary record of what was posted, when, by which script.
2. **Cron no_agent posting outputs** — `~/.hermes/cron/output/<jobid>/<ts>.md`.
   Scripts print a `POSTED: <feed/update URL>` (or `share:<urn>`) line; that is
   the authoritative posted-URL confirmation. Grep across all job dirs:
   `grep -rh "POSTED\|urn:li:..." ~/.hermes/cron/output/*/*.md`.
3. **Scripts embed URLs/URNs** — harvest with
   `grep -ohrE "urn:li:(share|activity|ugcPost):[0-9]+" <folder> | sort -u`
   (full-URL grep patterns with embedded quotes tend to fail shell quoting —
   extract the urn component instead).
4. session_search / full-home-dir grep only as corroboration AFTER the above;
   a wholesale `/home/ubuntu` content search can time out — target folders.

## Live verification + dedupe

- Curl each candidate with a **browser UA** — LinkedIn non-200s default curl UAs:
  `curl -s -L --max-time 15 -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0" "<url>"`
  → HTTP 200 + real `<title>` = live post. Grab the title to map URL→content:
  `... | grep -oE '<title>[^<]*' | head -1` (title is "Author — hashtag string").
- **share vs activity duality (dedupe trap)**: the SAME post has two URL forms
  with DIFFERENT numeric IDs:
  - API-created posts report `urn:li:share:XXXX` → `linkedin.com/feed/update/urn:li:share:XXXX`
  - the canonical shareable URL is `linkedin.com/posts/<author>_<hashtag-slug>-activity-YYYY-pNOY`
    (what the mobile app "copy link" gives — note the `member_android` utm)
  Both resolve 200 with identical `<title>`, so a naive list shows one post twice.
  Resolve by comparing `og:url`/`canonical` in each page's HTML — same canonical
  = same post. Present the `/posts/...` form (cleaner) and note the share form
  as alternate, or vice versa — never as two entries.
- Candidates verified in one command batch by looping over `share:`/`activity:`
  ids; keep a label per id so the final list maps URL → post topic.
- Distinguish same-folder neighbors: a scripts folder may hold OTHER clients'
  scripts (e.g. `post_linkedin_luxewave.py` inside an invertio folder) or the
  user's own-brand authority posts alongside the campaign posts — check each
  script's content before declaring everything "campaign X".
