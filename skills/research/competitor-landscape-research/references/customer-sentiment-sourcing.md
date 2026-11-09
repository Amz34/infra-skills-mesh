# Sourcing Customer Sentiment for a Product Category

Companion to the "Sentiment layer" section of SKILL.md. Provenance tags used below:
**[E]** = read from an extracted page body · **[S]** = search-snippet level only
(cite as snippet, never as a read page) · **[A]** = review-aggregator synthesis of
third-party reviews · **[K]** = already in the in-repo knowledge base.

## 1. The source ladder (cheapest useful density first)

| Rung | Source type | Why it earns the slot | Watch for |
|------|-------------|----------------------|-----------|
| 1 | Review-aggregator synthesis pages (G2 / Capterra / Trustpilot / app-store / forum roundups combined) | Highest sentiment density per fetch; usually quotes reviewers verbatim **and** states n per source | Aggregator's own framing; verify quotes are attributed, and carry the n forward |
| 2 | Vendor & consultancy engineering blogs on the *category's operational economics* | Where the hard numbers live (false-alarm rates, alert-fatigue thresholds, cost-of-ownership models) | Vendor = motivated; use only for **numbers they cite from elsewhere**, and name the original study |
| 3 | Product pages on review platforms | Full body extracts fine; often exposes a per-dimension sentiment split (ease of use vs cost vs support) | Invited-review bias; a sub-score outlier is the story |
| 4 | Forum threads (Reddit, vendor forums, IPVM-style trade sites) | Raw practitioner voice, best for "does it survive contact with reality" | Frequently walled from a datacenter IP → snippet-only; trade sites paywalled |
| 5 | Tender/procurement docs, union/association reports | Confirms price + complaint patterns with defensible provenance | Slow; use to confirm rungs 1–4, not to discover |

**Rule:** a sentiment finding is a *pair* — the quote/theme AND the n/source it came
from. A theme with no countable source is an opinion you invented.

## 2. When a forum host is walled (datacenter IP)

Symptom seen: the thread URL returns a login interstitial / 403 to the extraction
tool, to a plain `curl` with a browser UA, and to a bot-wall-fetch helper. Do **not**
burn calls retrying the same host, and do not write "source unreachable" as a
finding. Pivot instead:

1. Keep the **search snippet** — it often already carries the load-bearing sentence
   (a practitioner explaining *why* the free/open approach fails at the harder
   detection case). Cite it as *snippet-level*, and only for what it literally says.
2. Get the same theme from rung 1–2 (aggregators + engineering blogs), where the
   numbers are quotable.
3. Note the gap explicitly in the deliverable's "gaps in this research" section —
   an honest "forum voice sampled at snippet level only" beats a fabricated
   paraphrase.

## 3. Worked example — AI video fire & smoke detection over CCTV (Sep 2026)

**Punish themes, in damage order** (this order matters: it is the churn order):

1. **False alarms destroy the product, not the accuracy.** Up to 98% of security
   camera alarm activations are false **[E]**; the operational cliff reported in
   field write-ups is **>~2 false alarms per camera per day → operators stop reading
   alerts within the first week** **[E]**. Independent engineering numbers from the
   D-Fire benchmark work: raw per-frame false-alarm rate 19.4% → **8.9%** after
   temporal validation, and an uncertainty-aware post-detection stage moved
   precision **0.712 → 0.845** (mAP@50 0.625 → 0.651) **[E]**. Implication: sell and
   demo *false alarms per camera per day*, and publish the measured number.
2. **Opaque pricing + stacked subscriptions.** Cloud VMS roughly $50–150 per
   camera per month; monitored guard/human services ~$50–80k per year; wildfire
   detection ~$50k per station per year (quote-only at enterprise tier) **[E/K]**.
   Buyers repeatedly ask for a **5-year cost model** and don't get one.
3. **Lock-in + internet dependency.** Per-camera licence lapse → cameras stop
   working; site offline → no alerts. Trustpilot sentiment for the incumbent brand
   sits ~1.9★ over ~13 individual reviewers even while its ease-of-use sub-score is
   ~4.6/5 over 141 G2 reviewers **[A]** — i.e. easy to use, painful to own.
4. **Privacy / regulatory.** Breach history and regulator action are now
   procurement questions; biometric identification sits in the high-risk lane of
   the EU AI Act (Aug-2026 obligations) — deliberately staying non-biometric is a
   *selling point*, not a limitation.
5. **Integration pain.** ONVIF "supported" often means discovery-only; many brands
   need a separate ONVIF user; ports 80/8899 vary; the standard 403s and
   integrators learn the RTSP dialect by hand **[K]**.
6. **Certification line.** Category is supplement-only: no video detection product
   is UL-listed, only a few are FM-approved, and standards bodies recognise video
   detection only under performance-based design **[K]** — insurer and fire-marshal
   language is where a careless claim becomes a liability.

**Praise themes:** works with cameras the buyer already owns ("no rip-and-replace,
no additional hardware investment") **[E]**; minutes-not-weeks setup; a clean audit
trail for compliance; alert lands in the tool the team already lives in
(WhatsApp/Teams/Slack); quantified outcomes in the reference call.

**Rating-distortion case to cite:** 5.0★ over 12 *vendor-invited* reviewers on a
seller page **[E]** vs a competitor's 4.7★ over 141 **[A]** vs 1.9★ over 13
independent **[A]**. Always report n plus the invitation channel.

**Free/open floor check (always do this in a sentiment pass too):** the
practitioner consensus is that the free NVR/AI tier does motion-region single-frame
object detection, and **smoke has no stable bounding box**, so "does it do smoke?"
is the honest wedge question **[S]**. A sentiment pass that doesn't check the free
floor will over-claim the wedge.

## 4. Turning sentiment into a changes list (template that worked)

```
| # | Sentiment evidence (source) | Gap in our product | Change | Effort | Status |
|---|-----------------------------|--------------------|--------|--------|--------|
| C1| >2 FA/cam/day → alerts unread | no FAR metric, no throttle | instrument FAR per camera + auto-throttle + tile | S | PARTIAL (feedback loop exists) |
| C4| certification is a liability line | copy may imply certification | compliance-safe wording + claim gate | S | BUILD |
| C5| buyers punish opaque pricing | quote-only ourselves | publish pilot + per-camera price | S | BUILD |
```

Two disciplines that make the table trustworthy:
- **Verify status against the code/docs before writing HAVE.** Grep the repo (API
  routes, policy/feedback functions, export endpoints) — several "changes" turned
  out to be half-built already, and marking them BUILD would have queued duplicate
  work.
- **Effort in `S/M/L` or days, never "quick".** The user decides *what* to build
  from this table; give them the ranking, and end with one question ("P0 build, or
  the 1-day copy+pricing win first?").
