#!/usr/bin/env python3
"""Hybrid cost report — cloud token consumption + local/cloud split signal.

Local (Ollama) calls have NO price table -> estimated_cost_usd = 0/None.
So a rising api_call_count with near-zero cost = local doing the heavy lifting.
Prints a compact report for cron delivery.
"""
import json
import os
import sqlite3

DB = os.path.expanduser("~/.hermes/state.db")

q_totals = """
SELECT COALESCE(SUM(api_call_count),0), COALESCE(SUM(input_tokens),0),
       COALESCE(SUM(output_tokens),0), COALESCE(SUM(cache_read_tokens),0),
       COALESCE(SUM(estimated_cost_usd),0), COUNT(*)
FROM sessions
WHERE last_activity_at > strftime('%s','now') - 604800
"""
q_top = """
SELECT id, title, api_call_count, input_tokens, output_tokens,
       cache_read_tokens, estimated_cost_usd
FROM sessions
WHERE last_activity_at > strftime('%s','now') - 604800
ORDER BY estimated_cost_usd DESC NULLS LAST LIMIT 5
"""

conn = sqlite3.connect(DB)
calls, inp, out, cache, cost, n = conn.execute(q_totals).fetchone()

lines = [
    "📊 **Hybrid cost report (7 days)**",
    f"- Sessions active: {n}",
    f"- API calls: {calls:,}",
    f"- Tokens: {inp:,} in / {out:,} out / {cache:,} cache-read",
    f"- Estimated cloud cost: ${cost:.2f}" if cost else "- Estimated cloud cost: $0.00 (local model calls are free)",
]
rows = conn.execute(q_top).fetchall()
if rows:
    lines.append("\n**Top sessions by cost:**")
    for r in rows:
        lines.append(f"- {r[1][:50] or '(untitled)'} | calls={r[2]} | est=${r[6] or 0:.2f}")

# Local inference volume (ollama, if it keeps request logs we can count; here: model-level signal)
try:
    model_usage = conn.execute(
        "SELECT model, COUNT(*), SUM(input_tokens) FROM session_model_usage "
        "WHERE last_used_at > strftime('%s','now') - 604800 GROUP BY model ORDER BY 2 DESC LIMIT 8"
    ).fetchall()
    if model_usage:
        lines.append("\n**Model usage (calls):**")
        for m, c, t in model_usage:
            lines.append(f"- {m}: {c} calls")
except Exception:
    pass

print("\n".join(lines))
conn.close()
