# LinkedIn algorithm: what is extractable, and our outside-in reach loop

Session evidence: 2026-09-16. Companion tool built that day: `~/ops/linkedin/reach/li_reach.py`
(17 real posts seeded, `score`/`gate`/`ingest`/`report` all executed end-to-end).
Study doc: `~/ops/kb/linkedin-algorithm-reverse-study.md`.
Prior internal knowledge: `~/ops/kb/linkedin-virality-playbook.md`, `~/ops/kb/linkedin-content-constraints.md`.

## 1. The three-way verdict (use this shape for any "extract their algorithm" ask)

| Question | Answer |
|---|---|
| Can the *architecture* be extracted? | Yes — blueprint level. LinkedIn open-sources its own infra. Extractable knowledge, not runnable value at our scale. |
| Can the *ranking algorithm* be copied? | No, and copying is worthless: the ranker's value is LinkedIn's training data (1.2B members' graph + interaction logs), not the code. Code without that data ranks nothing. |
| What actually works? | Treat the ranker as a **black box** and model it *from the outside* on our own posts + our own metrics. This is legal, cheap, and buildable on the VM. |

## 2. Verified public facts about the current ranker (2026)

- **Feed SR — arXiv 2602.12354** ("An Industrial-Scale Sequential Recommender for LinkedIn Feed"):
  transformer-based **sequential** ranking model that **replaced the DCNv2-based ranker**; serves the
  majority of feed traffic at **1.2 billion members** scale. Online A/B vs the previous production model:
  **+2.10% time spent**, **+3.52% likes/comments/reshares**. The paper states they also deployed
  alternative sequential and **LLM-based ranking architectures** and still chose Feed SR for the best
  online-metrics / production-efficiency combination → "bigger LLM = more reach" is not a mechanism.
  Fetch the abstract without scraping: `http://export.arxiv.org/api/query?id_list=2602.12354` and regex
  `<title>` / `<summary>` (the arXiv abs page via web_extract returned only a length line).
- **360Brew** — LinkedIn Research's 150B-parameter foundation model for ranking/recsys; the arXiv paper was
  **withdrawn**. Cite it as direction, not as the live ranker.
- **TwHIN / entity embeddings** — public candidate-generation work. Patents exist on dwell/**skip (P(skip))**
  prediction. So: mechanism is published, weights are not.

## 3. Architecture blueprint (extractable, but do NOT propose running it)

```
events → Kafka → Brooklin (stream bridge) / Gobblin (batch ETL) → Samza (stream processing: features+labels)
      → Venice / Espresso (derived data stores) → Pinot (real-time OLAP, feature lookup)
      → ranking service (candidate generation → ranking → blending) → Feed
ops: ThirdEye (anomaly detection), DataHub (metadata), Helix + Cruise Control (cluster management)
```
All components are LinkedIn OSS (`github.com/linkedin/*`). They are designed for thousands of nodes; on a
2-core / 12GB ARM VM there is no tuning point and no data to put in them. Say this plainly instead of
proposing a mini-Kafka "so we look systematic".

## 4. Verified API reality — metrics CANNOT be read with the current token

Probe run 2026-09-16 with `~/linkedin_token.json` (`w_member_social` only, 60-day; app has publish scope):

| Endpoint | Result |
|---|---|
| `GET /rest/posts?author=urn:li:person:<id>&q=author` | **403** `ACCESS_DENIED` `partnerApiPostsExternal.FINDER-author` |
| `GET /rest/socialActions/{share_urn}` | **403** `ACCESS_DENIED` `partnerApiSocialActions.GET` |
| `GET /rest/memberCreatorPostAnalytics?q=author…` | **404** `RESOURCE_NOT_FOUND No virtual resource found` |
| `GET /v2/organizationalEntityShareStatistics?q=organizationalEntity…` | **403** `ACCESS_DENIED` (no org scope) |
| `GET /v2/userinfo` | **200** (publish + identity only) |

Consequences: post analytics (impressions / members reached / profile viewers / follows) must come from the
**LinkedIn UI**, pasted into the ledger via `li_reach.py ingest` (~20 s per post). Automated reads would need
an approved analytics / Member-Data-Portability scope — treat that as an application, not a workaround.
Do not re-probe these endpoints each session expecting a different answer; re-probe only if the token gains
new scopes. Probe snippet (`/tmp/liprobe.py` style) prints status + first 200 chars per endpoint — run it
before claiming an API can or cannot do something.

## 5. The outside-in ranker (the thing that is actually useful)

```
draft/post text ─► features (deterministic, stdlib) ─► readiness score 0-100 ─► --gate blocks < 62
own metrics (UI) ─► ledger.jsonl ─► Spearman feature↔reach + per-band means ─► weekly report/plan
```

```bash
cd ~/ops/linkedin/reach
python3 li_reach.py seed                     # import already-posted URNs from ops logs
python3 li_reach.py score draft.md           # feature table + readiness + fix list
python3 li_reach.py score draft.md --gate     # exit 1 when score < 62 (pre-flight gate)
python3 li_reach.py add --urn urn:li:share:… --file post.txt --at 2026-08-30T13:00:00+00:00 --topic x
python3 li_reach.py ingest urn:li:share:… --impressions 4200 --reactions 61 --comments 14 --reposts 3
python3 li_reach.py list ; python3 li_reach.py report
```

Feature set encodes the *published* levers only: hook archetype / first-line length, substance (words,
digits, question), dwell design, save-worthiness, CTA type, hashtag count, **external link in body (hard
penalty)**, engagement-bait phrases, media format, posting slot (Tue–Thu Gulf). Readiness bands from the real
posts scored so far: weak thin post ≈ mid-50s, substantive advisory post 83-85. Model side: needs ~20-30
metric-bearing rows before correlations mean anything — before that the ledger is honest rails, say so.

Reality check to keep in the reply: LinkedIn is deliberately **not** a virality platform (personalized
distribution + anti-viral-spam gates). Achievable = raise the per-post floor (hook + dwell + no penalty,
repeatable multiple-x), raise the frequency of right-tail hits (~1 in 10-15 posts), and win the first 60
minutes with genuine replies. Pods / paid engagement / engagement automation = shadowban territory; refuse them.

## 6. Open next steps (as handed over)

1. Metrics get ingested per post (user pastes numbers or sends a screenshot).
2. Wire `--gate` into the existing `post_linkedin_*.py` runners so no weak draft publishes.
3. Comment-depth tracker (30-80 word real comments are the heaviest silent signal).
4. Weekly cron: Monday report + next-week plan, silent when there is no data.
5. Optional: apply for an approved analytics scope so ingest becomes automatic.
