# Reference-stack gap audit (our infra vs. a syllabus / architecture diagram)

Trigger: user drops a link (course, vendor landing page, "here's the stack we should have" post)
and asks some form of **"analyze it — what gaps are there in our infra?"**. There is no artifact to
install and no claim to verify. The deliverable is a **capability scorecard of this host against the
layers that link describes**, every line backed by evidence from this box.

## Output shape that landed (keep this)

1. **One line on what the link actually is**, target URL spelled out: `linkedin.com/safety/go/?url=…`
   → `lnkd.in/gkBTnPYv` → `https://educationellipse.com/landing/aws/`, plus the syllabus layers in
   one compressed arrow chain (Core Infra → Compute & DB → IaC → Data Lake & Spark → Warehouse).
2. **Score line**: `7 OK · 8 partial · 8 GAP (5 critical)` — never an unscored narrative.
3. **Critical gaps**, each = the risk in one sentence + the cheap fix. Risk first, tool second.
4. **Partial** layer in a single dense line.
5. **Where we are AHEAD** — non-negotiable section (see pitfalls in SKILL.md).
6. **Fix order** by week, free tier first, with an explicit *skip* list (Spark/EMR/Redshift/Snowflake
   until a client pays).
7. Artifact paths so the number is reproducible: script + timestamped JSON under `~/ops/`.
8. Hinglish prose, artifacts/JSON in English. Close with a single yes/no action offer
   ("bolo to Week-1 free HA + R2 tier start kar dun — preview pehle, prod baad me").

## The 23-check taxonomy (grouped by capability layer)

| Layer | Checks |
|---|---|
| Compute & resilience | node count / cluster, container orchestrator, local headroom (cores/RAM/disk), **single-point-of-failure** |
| Cloud platform & data services | cloud CLI + credentials, object-storage client/remote, lakehouse libs (pyarrow/duckdb/polars/iceberg/delta), distributed compute (spark-submit/pyspark), warehouse (dbt + snowflake/redshift/bigquery clients), queue/stream (redis/kafka/rabbitmq/sqs) |
| Orchestration & pipelines | scheduler (airflow/dagster/prefect vs cron/n8n), workflow/webhook engine, IaC (terraform/opentofu/pulumi/cdk) |
| Data assets | operational data store (sqlite/postgres size), vector/RAG store, backup volume, analytics-ready formats (parquet/iceberg files) |
| Delivery & ops | CI workflows, offsite DR (rclone remote + archive age + encrypted), secrets hygiene, verification/observability ledger, model-provider keys, agent-ops surface (skills / MCP servers / cron) |

Statuses: `ok` / `partial` / `gap`, with a `critical` flag on the ones that are actual risk
(SPOF, no offsite copy, no IaC, no queue, no analytics path). Baseline run on this VM:
`2026-09-16T10:59:47Z` → `{total: 23, ok: 7, partial: 8, gap: 8, critical_gaps: 5}`,
`operational data store: 1`.

Run it: `python3 ~/.hermes/skills/<this skill>/scripts/infra_capability_audit.py`
(add `--json`, `--severity gap|critical`, `--fail-on-critical` for cron use).

## Worked case (Education Ellipse "AWS Masterclass")

Reference layers vs. this box, as of Sep-2026:

- **Critical:** single VM runs every client workload (OCI A1 Always-Free capped at 2 OCPU/12 GB since
  Jun-2026) → second Always-Free VM + Caddy/Tailscale failover is the fix; no AWS account at all
  (boto3 present, no cloud behind it); no IaC (hand-typed bash + systemd); no Spark/distributed
  compute; no object-storage *tier* (rclone `gdrive:` is a DR target, not a data lake); no
  lakehouse/columnar layer (pyarrow/duckdb/polars all absent); no queue/event bus (async = cron +
  files + webhooks); warehouse layer partial (one postgres container, no dbt).
- **Partial:** orchestration (no Airflow — n8n + Hermes cron), CI (GitHub Actions in one repo only),
  secret hygiene (several env/token files on disk, no vault/KMS/rotation), model gateway (one key
  shared across profiles → 429 collisions), RAG (small Chroma store — practice scale, not
  production), SQLite ops store at GB scale with no warehouse above it.
- **Ahead of the syllabus:** agent-ops layer — many scheduled jobs incl. `no_agent` watchdogs,
  MCP system-of-record connectors, reviewed skill store, verify-ledger + L0-L4 autonomy registry.
  No data-engineering syllabus covers this; do not let the scorecard imply parity means catch-up.

## Remediation ladder (cost-ordered — free first)

1. **Week 1** — `oci-cli` in a venv (keys already in `~/.oci`, `pip install oci-cli`), 2× AMD micro
   Always-Free VM, Caddy + Tailscale for failover → SPOF mostly gone for free. Cloudflare R2 free
   10 GB (S3-compatible) → real object tier + second offsite copy.
2. **Week 2** — OpenTofu (free) for VM + DNS + R2 as code; GitHub Actions CI on all client repos.
3. **Week 3** — DuckDB + pyarrow + Parquet local lake on existing free disk (client analytics/BI
   deliverable with no cloud bill); Redis container for webhook queueing.
4. **Skip** — Spark/EMR/Redshift/Snowflake/Databricks until a client's money depends on them.

## Evidence recipes worth reusing

- Resolve wrapped links: see the t.co/lnkd.in pitfall in SKILL.md — the header path can return a bare
  `HTTP/2 200` with no `Location:`; fetch the body and grep external URLs.
- Prefer `impfetch` over `web_extract` for landing pages behind bot walls (produced the only fully
  retained capture; a `web_extract` of the same page returned a fraction of the text).
- For any multi-command probe, write a **script file and run it** rather than a long inline one-liner:
  complex nested quoting gets refused by the inline guard, and script output also survives output
  truncation better.
- Never persist secrets while auditing: `~/.aws`, `~/.config/rclone/rclone.conf`, `~/.oci/config`,
  client `.secrets` are recorded as existence + shape only, values `[REDACTED]`. A reduction pattern
  that keeps the audit useful: grep the key/expiry line and `sed` the value to `<redacted>`.
- Cross-check DR claims against the *service log*, not the last memory note — a stale "backup
  local-only" note was contradicted by the current run's upload + md5-parity PASS.
