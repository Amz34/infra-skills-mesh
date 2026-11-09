# Cold-email campaign summary data map (AVVS Triatek, verified 2026-08-25)

When Aamir asks "avvs ka summary" (or any campaign summary: leads messaged, regions, total sends, attached docs, technical data) — compute from SEND LOGS + LEAD LISTS, never from memory.

## Where the AVVS data lives

Send logs (JSONL, one obj per line: `{ts, company, to, subject, status, error}`):
- `/home/ubuntu/clients/AVVS-Triatek/outreach/sent_emails.jsonl` — wave 1 (31 real, 2026-08-24)
- `/home/ubuntu/clients/AVVS-Triatek/outreach/followup_log.jsonl` — followups (2 TEST only)
- `/home/ubuntu/clients/AVVS-Triatek/outreach/wave2/wave2_sent.jsonl` — wave 2 (92 entries = 90 real + 2 TEST, 2026-08-25)
- Send scripts: `send_venturi_outreach.py` (wave1), `wave2/send_venturi_wave2.py`, `send_venturi_followup.py`

Lead lists:
- `outreach/wave2/avvs_triatek_worldwide_leads.csv` — 277 leads, 141 with email. Header: `company,country,segment,website,contact_email,email_confidence,contact_name,contact_title,notes`
- `/home/ubuntu/avvs_leads_me_asia.csv` (92), `avvs_leads_americas.csv` (80), `avvs_leads_europe.csv` (80)
- `/home/ubuntu/avvs_candidates.json` — 104 candidates (company/city/country/segment/website/lang/notes)
- `/home/ubuntu/avvs_emails_raw.json` — 104 raw companies, mostly no email and NO region field

Attached docs / assets:
- `wave2/carousel.pdf` (7 slides) + `wave2/slides/*.png` — wave2 attachment
- `wave2/email.html` + `wave2/email.txt` (wave2 body), `template_328.eml` (wave1 body), `followup1_body.txt`
- `/home/ubuntu/avvs-email/avvs-email-venturi.eml`
- Site video: `clients/AVVS-Triatek/site/assets/video/avvs-video.mp4` (+ `wp-avvs/uploads/.../avvs-video.mp4`), `clients/AVVS-Triatek/avvs_files.zip`
- Landing page: https://avvs-triatek.pages.dev
- Sender: azengineeringapp@gmail.com (himalaya, `GMAIL_USER`/`GMAIL_APP_PASSWORD` env)

## Summary computation pattern

```python
import json, csv, collections
def load(p): return [json.loads(l) for l in open(p) if l.strip()]
rows = load('sent_emails.jsonl') + load('followup_log.jsonl') + load('wave2/wave2_sent.jsonl')
uniq = {r['to'].lower().strip() for r in rows}          # unique leads messaged
test = sum(1 for r in rows if '[TEST]' in r.get('subject',''))  # NEVER count as real
# email->country join (first-wins across all 4 CSVs), then collections.Counter per country
```

Verified result (2026-08-25): 121 unique recipients = 121 real sends (wave1 31 + wave2 90), 4 TEST sends; 33 countries covered; USA largest, then Germany, India, Saudi, UAE, Sweden.

## Pitfalls

- **`[TEST]` prefix in subject = test send** — report separately, never as real outreach.
- **Wave-1 (31) recipients are NOT in the 4 lead CSVs** (they were US-heavy: reps/distributors/lab-controls + Zamil-Oman, Almajdouie-Saudi, Exyte). Map by company name against `avvs_candidates.json`, else label honestly as unclassified.
- Segment stats come from the worldwide CSV's `segment` column (hospital ≈ 40, HVAC distributor/OEM/rep, pharma/biotech, research lab, semiconductor/data-center, MEP contractor, FM).
- Technical angles to quote: Triatek Venturi valve calibration/certification (OEM-grade, auditor-ready reports), commissioning/retrofits room-by-room, genuine parts, preventive maintenance; pain point = valve drift → room-pressure test fail → alarm → wing stall; 48-hour on-site fix; "valves not obsolete" positioning.
