---
name: agentic-tooling-research
description: Use when researching agentic AI tooling on GitHub/X.
---

# Agentic Tooling Research — GitHub + X + Tiered Advice

Aamir ke liye recurring pattern: system upgrade ke liye "kya chahiye" research (GitHub pe kya trending, X pe kya trending) → grounded advice. Ye bhi tab use karo jab user "X ka fida hai?" style tool evaluation pooche. Output format: Hinglish, **tiered plan (Tier 1 abhi / Tier 2 agle mahine / Tier 3 jab revenue aaye)**, sab **OSS/free pehle** (user cost-sensitive — paid tool sirf real kaam pe), table for repos (name, stars, use-case for OUR stack).

## Workflow

1. **GitHub search** — star-sorted, multiple angles (don't stop at 1 query):
   ```
   curl -s "https://api.github.com/search/repositories?q=agentic+ai&sort=stars&per_page=10"
   ```
   Deep queries: `agent+memory+llm`, `agent+observability+evaluation`, `mcp+server+collection`, `agent+os+desktop`. (Unauthenticated API: 10 req/min — batch in one loop.)
2. **Verify star counts + descriptions** — `api.github.com/repos/<owner>/<repo>` per candidate, parse with python to get clean `⭐N | description`. NEVER cite stars from memory — verify.
3. **X research** — xurl auth nahi hoti to: `web_search("site:x.com <topic> 2026")`. X **articles** (`x.com/<user>/article/<id>`) web_extract se full-read hote hain — search snippets se zyada value. web_search results bade aate hain → `execute_code` me compact print (titles+URLs) karo.
4. **Extract top 2-3 sources fully** — web_extract on X articles + top repo READMEs. `web_extract` result display compact hota hai; content agle step me synthesize karo.
5. **Synthesize → roadmap doc** — save to `~/ops/kb/<topic>-next-levels.md`: findings table + tiered plan + per-workflow audit table. Then implement Tier 1 (0₹, same session if user approves).

## Advice format (Aamir ke liye)
- **Tiered by value**: Tier 1 abhi karo (free, is week), Tier 2 agle mahine (free), Tier 3 production-grade (revenue ke saath, phir bhi OSS).
- **Map to HIS stack**: har repo/article ka use-case batana chahiye (client bots, LinkedIn engine, cron workers, n8n) — generic "yeh cool hai" nahi.
- **Include the counter-intuitive principle** if found (e.g. "2 diverse agents ≥ 16 homogeneous agents" — naya agent sirf evidence diversity ke liye).
- End with concrete offer: "roadmap doc save + Tier 1 implement karoon?" — user "Ok" bole to turant dono karo.

## Known-good research bank (2026-08-25, verified)
References: `references/agentic-next-levels-2026-08.md` — 6 repos (superpowers 277K⭐, ECC 243K⭐, agency-agents 148K⭐, deer-flow 81K⭐, mem0 64K⭐, RagaAI 16K⭐) + 2 X articles (4-plane architecture, 5 building blocks) + tiered plan. Roadmap doc: `~/ops/kb/agentic-next-levels.md`.

## Research bank 2026-09-06 (Astra GA)
GPT-6 Astra GA (Sep 3, 2026) post analysis (top 20 builds): roadmap doc `~/ops/kb/astra-ga-2026-09.md` — 20-build→pattern table, director-pattern (#20), model-tier selection + real-task A/B (#2/#7), video-as-spec (#9), SVG code visuals (#10), content remix (#19). Derived skills: video-spec-brief, model-tier-selection, content-remix-engine, mcp-tool-servers, svg-vector-visuals. Astra API facts: `gpt-6-astra`, $10/$50 per M tokens, 1.05M ctx, 128K out, cyber-restricted.

## Key patterns discovered (reuse in upgrades)
- **Four-plane lens**: Control / Communication / State / Verification — har workflow ke liye define karo.
- **Verification gate**: har cron/delegation me explicit verify step (exit code + artifact + 201/URL) — "verification bina = completion nahi".
- **Progress-note continuity**: `STEP COMPLETED / KEY DECISIONS / CURRENT STATE / NEXT STEP` 4-line note cron prompts me — continuity-flag ke saath auto-carry hota hai.
- **Long cron prompt edit**: full prompt `~/.hermes/cron/jobs.json` me hai (cronjob list sirf preview deta hai). Exact copy → append → `cronjob action=update` → jobs.json read-back verify.

## Pitfalls
- Star counts/galat descriptions cite karna — hamesha API verify karo pehle.
- `web_search` huge results → execute_code me compact print (titles/URLs) karo, raw dump mat karo.
- `web_extract`/`web_search` tool results display me truncated lagte hain — content tumhare paas aaya hai, output par bharosa karo, re-fetch mat karo bina zaroorat.
- X articles web_extract se aate hain; X search page nahi — `site:x.com` query + article URL extraction use karo.
- User-owned skills (e.g. agent-orchestration) curator patch se refused hote hain — usme update chahiye to `hermes curator adopt` recommend karo.
