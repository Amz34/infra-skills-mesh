# Agent Usage Audit — worked example (v0 subscription decision, 2026-09)

Context: Invertio project group. User sent a v0 Premium $20/mo subscribe
screenshot and asked: "expertly analyze our api usage till now — is it
beneficial if we subscribe to v0 vercel?"

## Steps that worked

1. **Read the screenshot.** If direct image viewing is unavailable/undesired,
   OCR fallback: 2x LANCZOS upscale (`Image.LANCZOS`) + tesseract `--psm 3`
   per horizontal band gave legible text of the pricing modal (raw psm on the
   original resolution produced garbage). Price figures were cross-checked
   against the official pricing pages before being quoted in the verdict.

2. **Whole-profile usage totals** (SQL in SKILL.md). Useful variants:

   By model (which model carries the cost):
   ```sql
   SELECT model, COUNT(*), SUM(api_call_count), SUM(input_tokens),
          SUM(output_tokens), SUM(cache_read_tokens),
          ROUND(SUM(estimated_cost_usd),2)
   FROM sessions GROUP BY model ORDER BY 7 DESC;
   ```
   Trailing window (activity within N days):
   ```sql
   WHERE last_activity_at >= strftime('%s','now') - 30*86400
   ```

3. **Live balance cross-check with the PROFILE's own key** — grep the key
   from `~/.hermes/profiles/<name>/.env`, curl
   `https://api.deepseek.com/user/balance` with it. Echo keys masked
   (`${KEY:0:6}...`); never print values.

4. **Evidence query — was the tool ever used?**
   ```sql
   SELECT datetime(timestamp,'unixepoch'), role, substr(content,1,200)
   FROM messages
   WHERE content LIKE '%v0.dev%' AND role IN ('user','assistant')
   ORDER BY timestamp DESC LIMIT 10;
   ```
   → 0 real hits across the agent's whole history = no track record to
   justify paying.

## False positive found

`LIKE '%vercel%'` returned 42 hits — nearly all compaction-handoff
boilerplate (system summaries re-mention tool names/platforms). Always peek
at actual rows before trusting a count; the role filter above kills most
noise.

## Verdict framing that landed (numbers-first, no fluff)

- Their whole always-on AI ops = ~$2.76 over 30 days (3,039 API calls, 54
  sessions) → v0 at $20/mo = **7x the entire API bill** for one UI tool.
- Workflow mismatch: v0 emits React/Next/Tailwind; their client deliverables
  are static HTML/CSS on surge.sh → porting overhead = hidden rework cost.
- Credit mechanics: "$20 credits + $2/day login" is a retention hook —
  unused monthly credits expire; not burning them = pure waste.
- Revisit condition: React/Next.js client builds at scale, or free tier
  (7 msgs/day) repeatedly blocking billable work — then $20 recovers in one
  client job.
- Bonus finding worth always reporting: DeepSeek balance was ~$0.75 left →
  a $5 top-up ≈ 2 months runway is the actual immediate cost concern, not
  the subscription.
