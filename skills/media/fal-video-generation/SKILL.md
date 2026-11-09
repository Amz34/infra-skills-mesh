---
name: fal-video-generation
description: Use when generating fal.ai video or judging a fal promo.
version: 1.0.0
author: Hermes (curator)
license: proprietary
metadata:
  tags: [video, fal, generation, cost-gate, h3-max]
  related_skills: [free-flux-image-api, client-video-ad-production, linkedin-video-content-engine, model-tier-selection]
---

# fal.ai video generation (H3 Max) with a cost gate

## When to use
- A task needs generated **video** (client ad, reel hook, UI demo B-roll) and stock/ffmpeg is not enough.
- Someone shares a fal.ai / MiniMax H3 / "genmedia" promo and you must judge whether it fits our infra.
- Anything that would spend money on fal.

Images are NOT this lane - stills stay on the free flux lane (`fluxgen`, ~170/day free).

## Ground truth (re-verify before quoting, rates move)
- Endpoints: `minimax/h3-max/text-to-video`, `minimax/h3-max/image-to-video`,
  and the cheaper `minimax/h3-max-turbo/{text,image}-to-video`.
- Live per-second rates live in each endpoint's docs: `https://fal.ai/models/<endpoint>/llms.txt`
  (promo line + "after which" post-promo line). Never quote a price from memory or from an ad post.
- Account/billing truth: `https://fal.ai/docs/documentation/agent/access-and-pricing.md`.
  `fal Agent Starter $50/mo` returns **$50 of credits** spent before pay-as-you-go and rolled over -
  a prepay credit line, **not** an API discount. Genuinely free: the sandbox allowance
  (5 requests/day, `"sandboxFreeRequests": 5`), which is **UI-only, not the API**.
- An agency/creator can apply for **$1,000+** complimentary credits at `fal.ai/agent-access/claim`.

## Commands
```bash
falgen --rates [--refresh]                 # live $/second table + 5s @768p cost
falgen --estimate --model h3-max --res 768p --seconds 5
falgen "prompt" --model turbo --res 768p --seconds 5      # cheapest by default
falgen "prompt" --image ./still.png -o hero.mp4           # image-to-video
falgen --usage --budget 50                 # month-to-date vs budget, clips left
falgen --check                             # key + endpoint self-test (no spend)
python3 ~/ops/verify/fal_promo_check.py    # re-derive promo claims from fal's own pages
```
Key resolution: `$FAL_KEY` -> `vault get infra FAL_KEY` -> genmedia config.
Set it with `vault set infra FAL_KEY FAL_KEY=<value>`.
Exit codes: 0 ok | 2 no key/misconfig | 3 budget guard refused | 4 provider error.

## Cost discipline (house rule)
- Default to `turbo` + 768p; ask before 1080p (2x). One 5s clip at promo rates: h3-max $0.20,
  turbo $0.10; after the launch promo these double.
- Every paid run is bounded by `FAL_MONTHLY_BUDGET` and `--max-cost`; the guard refuses and exits 3
  unless `--allow-spend` is explicit. Runs are logged to `~/.local/state/falgen/spend.jsonl`.
- Never silently retry an expensive run: report the estimate and wait.

## Pitfalls (learned the hard way, 2026-09-16)
1. fal's `llms.txt` bolds **both** the price and the label: `**$0.04** per second at **768p**`.
   A regex like `\$([0-9.]+)\s*per second at \*\*768p\*\*` silently matches nothing - and if your
   code falls back to a hardcoded table you will report stale prices as "live". Parse with
   `\*\*\$([0-9.]+)\*\*\s*per second at \*\*(480p|768p|1080p)\*\*` and mark the source honestly.
2. fal publishes the promo end as **"September 31"** - an impossible date. Treat it as 30 Sep / 1 Oct
   and let the `fal-rate-monitor` cron catch the real cutover.
3. The post's "under 3 seconds" is inference time only; wall-clock includes queue wait + encode.
4. The official `genmedia` CLI needs a key even for model *search* (install:
   `curl -fsSL https://genmedia.sh/install | sh`; a linux-arm64 build exists) and it reads
   `FAL_KEY` from the environment - export it before calling.
5. Sign-up is GitHub / Google / Microsoft / SSO only (no email+password): account creation is a
   **human step**, never automate the OAuth/CAPTCHA.
6. LinkedIn short links (`lnkd.in/...`) keep the post text in the resolved page's og:description -
   strip it to verify a claimed number instead of trusting the ad copy.

## Verification before you report success
1. `python3 ~/ops/verify/fal_promo_check.py` -> exit 0 and every claim PASS/WARN (never FAIL).
2. `falgen --rates --refresh --json` -> `models.*.source == "docs"` (not `fallback`).
3. After a real generation: file exists, non-zero bytes, and one line appended to the spend ledger.
4. Registry: the capability is declared in `~/ops/observability/autonomy.json`
   (`falgen video generation (fal.ai H3 Max)`, L3, spend gate) - keep it in sync if the gate changes.
