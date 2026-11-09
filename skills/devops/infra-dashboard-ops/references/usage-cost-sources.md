# Cost / Usage Data Sources for Dashboard Panels

Condensed knowledge from the API-usage-chart build (verified against live DBs, 2026-09).

## Hermes state.db — the usage ground truth

Files (5): `~/.hermes/state.db` (default profile) + `~/.hermes/profiles/*/state.db`
(each profile dir = a "bot"/client: invertio, whatsapp, avvs…). The gateway writes a
row per session on EVERY LLM turn — so these DBs are live and drift second-to-second.

### Connection rules
- Open read-only: `sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=3)`
  with `conn.execute("PRAGMA query_only=ON")` — never block the live gateway writer.
- WAL mode means a plain `file:` copy via `shutil.copy2` while the gateway is writing
  is safe enough for deterministic tests, but freeze FIRST, then query both paths
  against the frozen copies.

### sessions table (columns verified via PRAGMA)
- `billing_provider` (e.g. deepseek, gemini, zai, custom, openrouter…)
- `model` (e.g. deepseek-v4-flash, gemini-3.7-flash, glm-4.7-flash…)
- `estimated_cost_usd` and `actual_cost_usd` (actual wins when provider reports it)
- `api_call_count` (calls per session), `last_activity_at` (unix ts, updates per turn)
- Rows with empty model = non-LLM sessions (tool-only) — exclude from usage.

### Core aggregation SQL
```sql
SELECT COALESCE(billing_provider,'?'), COUNT(*), SUM(api_call_count),
       SUM(COALESCE(actual_cost_usd, estimated_cost_usd, 0))
FROM sessions
WHERE COALESCE(model,'') <> ''
  AND (cutoff IS NULL OR last_activity_at >= cutoff)   -- cutoff: unix seconds
GROUP BY 1 ORDER BY 4 DESC
```
Same shape with `GROUP BY model` for per-model view. Iterate the 5 DBs and merge in
Python (small data). Live sanity numbers: deepseek-v4-flash ~24.7k calls/$19.7 in 30d
across profiles — the dominant cost line.

### Provider/model quirks
- Provider keys ≠ labels: `gemini` = Gemini (Google); `zai` = Z.ai (glm models);
  `custom` = Ollama/local or free-proxy route (costs $0).
- A model id can appear under several providers (fallback reroutes e.g.
  deepseek-v4-flash billed under `gemini`, whatsapp's free `custom` route) — group by
  model ACROSS providers for true per-model spend; group by provider for the bill.
- Per-model/UI color: deterministic prefix palette (`apiColor()`: deepseek=blue,
  gemini=purple, openai=green, anthropic=pink, openrouter=teal, mistral=amber, zai=red)
  beats a fixed model->color map since model ids are open-ended.

### Window semantics
24h / 7d / 30d = `int(time.time()) - 86400*n`. All-time must be a `None` sentinel —
passing 0 gives cutoff `now - 0 = now` and matches nothing (real bug hit; fixed).

## DeepSeek balance API (only live balance source)
- `GET https://api.deepseek.com/user/balance` with `Authorization: Bearer <key>`.
- Returns `balance_infos` (currency + `total_balance`) — CURRENT BALANCE ONLY.
  No usage endpoint exists; spend must come from the local state.db aggregation.
- Cheap endpoint; cache 5 min (`BAL_FRESH=300`) is plenty for a live dashboard card —
  balance visibly ticks down between refreshes as gateway calls bill.
- Reference wrapper: `~/.hermes/scripts/deepseek_balance_watch.sh`.

## Sub-cent display threshold
Skip slices < $0.01 from pie/legend lists (they render as "$0.00" noise rows) but keep
them inside totals. Threshold 0.01, not 0.001.

## Deterministic QA recipe (live-drift safe)
1. `tmp=$(mktemp -d)`; copy all 5 DBs into it.
2. Run collector aggregation AND an independent SQL SUM over the SAME copies.
3. Compare per-slice `(usd, calls)` with tolerance ~1e-4 (collector rounds to 4dp).
   A 1e-9 tolerance false-positives on rounding. Sum-of-slices must equal 30d total.
