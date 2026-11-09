# Free / Grey-Market Model-API Relay: Due Diligence + Airlock Design

Use when a post, DM, forum thread, or Aamir himself pushes a **"free models / ~10× cheaper than official / one API key for every model"** gateway (apinex.bond, and the endless clones). Goal: a defensible verdict in minutes, plus — if he still wants to try it — an *airlock* design so it can never take down client-facing infra.

Core rule: **an external model gateway is an untrusted dependency, same class as a random webhook.** Default route kabhi nahi. Client data kabhi nahi. Advice-only unless he says otherwise.

## 1. Recon ladder (all read-only, ~5 min)

1. **Resolve the pitch link** before judging: `curl -sIL -o /dev/null -w '%{url_effective}\n' https://t.co/XXXX` (X posts) — never analyze the tweet's words alone.
2. **Domain forensics:** `whois <domain> | grep -iE 'creat|expir|registrar|name server'`. Sub-6-month `Creation Date` + cheap TLD (.bond/.xyz/.top) + Cloudflare proxy + registrar no one recognises = high-risk by default. Cross-check `scamadviser.com/check-website/<domain>` (low trust score is a signal, not proof).
3. **Map the real product surface via sitemap — do NOT fight the SPA.** Marketing sites for these things are Next.js/SPA: `web_extract` returns 2 lines of hero copy and nothing else. Cheap unlock:
   ```bash
   curl -sL --max-time 20 https://<domain>/sitemap.xml | grep -o '<loc>[^<]*' | sed 's/<loc>//'
   ```
   This is what exposed the smoking guns: `/developers/airdrop` and `/developers/tools/solana` — i.e. an LLM relay with a crypto-airdrop growth layer, which the landing page never mentions.
4. **Distribution pattern:** search `<domain>` + `review scam legit`, and `<brand> free models` — look for: referral/invite-and-earn codes spammed on Telegram/X, YouTube shill videos, low-effort forum threads ("I don't know how long this event will last"), anonymous X accounts with high view counts. Affiliate fuel > product.
5. **Economic sanity check:** "official se 10× sasta" for frontier models is **not achievable legitimately** (upstream cost sets the floor). Actual explanations: stolen/leaked keys, carded credits, trial-account farming, or a subsidised funnel to a token/airdrop. Say which is most likely; don't hedge it into mush.
6. **Free-tier design tells you the business model.** Signals of deliberate account farming: "Google login + strict 1 account per IP + 1M free tokens/day", weight-based billing, `$0/1M` rows, free voice STT at 30 RPM. An IP-locked daily grant means **our single VM = exactly one account** and any tunnel/VPN churn risks a ban; making an account per Hermes profile = AUP violation + IP flag.
7. **Quota/limit reality:** pull numbers from doc pages via search snippets (the pages themselves are SPA-empty). Look for: RPM limits, concurrency, and **balance "temporary reservation" → 402 even when you have balance** (per-request pre-auth hold; long agentic runs stall on it). Note if `/v1/models` is 401 without a key: then the advertised model IDs are **unverifiable** — silent substitution (small open model behind a big name) is the standard trick, and relays quietly drop streaming/tool-calls.
8. **Data path:** every prompt transits a stranger's server, no DPA, unverifiable logging, unknown jurisdiction. Anything client, PII, or credential-adjacent is disqualified on this line alone.

## 2. Verdict shape

State it in three lines: (a) what the thing actually is, with the evidence bullets; (b) the exact ways it would break *our* infra; (c) the recommendation. Then give the airlock design so the answer isn't just "no". Close by confirming **nothing was changed** when he said advice-only.

## 3. Airlock design (if he wants to experiment anyway)

Sandbox-only "airlock" — every control is client-side, because the provider controls nothing:

| Control | Setting |
|---|---|
| Isolation | Separate profile (`<brand>-lab`) — never the default profile (bot-token 409 rule), separate keys dir |
| Auth | Key in the **vault**, never plaintext in `config.yaml` |
| Route | Dedicated alias (`provider: custom`, `base_url: https://api.<domain>/v1`) — never a default, never in a cron chain |
| Task allow-list | public-content summary, drafting, i18n string passes, test/dev scaffolding, eval baselines |
| Task deny-list | client deliverables (Sanad/AVVS), leads, tender docs, bot replies, anything PII → run `~/.hermes/scripts/pii_gate.py` first |
| Flow control | limiter at ~⅔ of the published RPM, max concurrency 1, retries ≤2 with exp-backoff+jitter, honour `Retry-After` |
| Circuit breaker | 3 consecutive 429/5xx → alias disabled 15 min; fallback chain → `local` (qwen2.5:7b) → `deepseek-v4-flash` |
| Quota ledger | daily token counter in the workspace; 80% warn, 90% hard stop → no unbounded cron loop can hit it |
| Canary + kill switch | 6-hourly one-line ping; fail = disable alias + pause dependent cron; separate logs for attribution |
| Never | card/top-up, main Google account, bot tokens, account-per-profile, key reuse from other services |

## 4. Case study — APInex (2026-09-11, X post by @k2sbhai, 15.4K views)

- Advertised: "DeepSeek V4.1 Flash FREE + DeepSeek V4 Pro, Gemini 3.8 Flash, GLM 5.3 Flash, Muse Spark 1.3, GPT-5.6 Luna, Qwen 3.8 Max" via `t.co` → `apinex.bond`.
- Found: domain **created 2026-08-01** (~6 weeks old), `.bond`, Cloudflare-proxied, Scamadviser low trust; sitemap showed `/developers/airdrop` + `/developers/tools/solana`; Telegram referral code spam ("my ref if you want use in invite and earn"); NodeLoc thread advertising "1M free tokens/day, Google login, strict IP check (one IP only allows creating one account)".
- Pricing page: "~10× cheaper than official", from $0.07/1M, **weight-based billing**; free voice STT 30 RPM; `/v1/models` → 401 without a key.
- Verdict given: grey-market relay with a crypto-growth layer — **skip for client work**, sandbox-only if curiosity; nothing configured.

## 5. Legit alternatives already on this VM (offer these instead)

`local` / `local-fast` Ollama aliases (zero cost, PII-safe — route explicitly, nothing auto-routes local), HF Spaces inference, Kaggle GPU, Cloudflare Workers AI, and official free tiers (Google AI Studio, Groq) with documented limits and your own key. Cheapest paid path (deepseek-v4-flash ~$0.28/1M) is usually far below the risk-adjusted value of a grey relay.
