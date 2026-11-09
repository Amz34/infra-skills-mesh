# LinkedIn fresh-posting sourcing — the `f_TPR=r<seconds>` filter

Verified 2026-09-15 (live, logged-out). Use for **outreach timing**, not job-hunting.

## The parameter

- `f_TPR` = "time posted range" in a LinkedIn jobs search URL. The value is **seconds**, prefixed `r`.
- The UI exposes only 3 presets — `r86400` (24h), `r604800` (7d), `r2592000` (30d) — but the backend
  accepts **arbitrary seconds**: `f_TPR=r1800` = jobs posted in the last 30 minutes.

## Machine-readable endpoint (no login, no cookie) — VERIFIED

```bash
curl -s --max-time 25 -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0 Safari/537.36" \
 "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=qa%20qc&location=Saudi%20Arabia&f_TPR=r1800&sortBy=DD&start=0"
```

- Returns HTTP 200 + HTML job cards (`class="base-card"`), each with title, company, location and a
  `<time datetime>` stamp — parse it, no browser needed.
- `&sortBy=DD` = date-descending. **Always stack it**: without it results can come back
  relevance-ordered, which hides exactly the recency the filter is for.
- Paginate with `&start=0,25,50…`.

## Live numbers measured (2026-09-15, keywords `qa qc`, location `Saudi Arabia`)

| `f_TPR` | cards | note |
|---|---|---|
| `r600` (10 min) | 0 | nothing that fresh for this keyword — a low-volume window, *not* proof the value is rejected |
| `r1800` (30 min) | 9 | in-page timestamps "22 minutes ago", "26 minutes ago" → filter genuinely honoured |
| `r3600` (1 h) | 12 | monotonic with the seconds theory |
| `r86400` (24 h) | 30 | page cap |

Sample rows from the 30-minute window: Baker Hughes — QC Supervisor (Dammam); Cognizant — Sr. Test
Analyst (Riyadh); Cognizant — Technology Specialist (Riyadh).

## Why it matters for us

- A posting inside the ≤30-minute window = a **req that just opened** → the hiring manager / recruiter is
  working on it right now. That is the best moment for a retained-search pitch or a "who is running this
  req?" probe, and it beats the 24h window every other agency is looking at.
- KSA engineering/QA competitive intel at 30-minute granularity (who is hiring, in what city, how fast).
- Candidate-side: our own hiring posts compete in this same feed → post freshness is part of the funnel.
- Automation candidate (offered to Aamir 2026-09-15, not yet built): cron polling the guest endpoint for
  5-6 target KSA keywords, dedupe on job id, Telegram alert for new rows only. Keep polling **polite**
  (few keywords, no more often than every 30 min) — this is an undocumented endpoint; treat 401/429 as
  "slow down", not "broken".

## Honesty ledger (keep this framing in any report)

- URL mechanic: **verified** — reproduced twice in one session, corroborated by in-page timestamps and
  monotonic counts, not by the post that advertised it.
- "Applying first ⇒ higher callback": **directional only**. LinkedIn's own marketing repeats it; no
  independent peer-reviewed source was found. The defensible mechanism is queue mechanics — recruiter/ATS
  queues order applications by time and attention decays as the pile grows. Label it as directional and do
  not launder the author's claim into our copy (see `content-integrity-guardrail`).
- The "trick" framing is usually recycled: the same parameter hack has circulated since early 2025, and
  the post that surfaces it typically funnels to a paid asset. Decode the funnel with
  `linkedin-content-engine` → `references/viral-hack-post-teardown.md`.
