# Measurement-backed repos (the number IS the product)

Pattern proven 2026-09-21: a repo whose reason to exist is a **measured** claim (this stack is
faster / cheaper / better on a specific decision than a chat model), launched as a public repo
plus a poster on LinkedIn + X + Bluesky. The repo has to survive someone trying to reproduce it.

## 1. Ship so a stranger can reproduce without spending anything

- **A runnable harness with `--dry-run`.** The dry-run prints the exact request payload and the
  schema, so the whole design is inspectable with **no API key and no network**. First command in
  the README should be the offline one.
- **Synthetic data only** in the demo set — never client rows, never real ticket text.
- **An offline `make verify`** as the repo's canonical self-check: parsers round-trip the API
  contract, the batching contract holds, the demo data is well-formed, assets are real (frame
  count > 1, non-zero bytes), the canonical repo URL appears where it claims to, and a leak scan
  finds no key material / internal names. 21 checks, no key, no network, exit 0 = good.
- **Ship the assets + the command that rebuilds them** (`make poster`). A poster that only exists
  in a feed cannot be corrected or audited later.
- **A `docs/measurements.md`** carrying the real numbers, the lane definitions (what was held
  constant, what changed) and the raw report file — that is the artifact a claim gets tagged to.

## 2. Report the finding even when it undercuts the pitch

The honest headline here was *"accuracy was a wash (26.7% vs 28.3%) — buy the latency and the
probability, not the intelligence"*, plus the real bottleneck (*the gold label was in the
candidate list only 47% of the time*). Both facts weaken a naive "our model is smarter" pitch and
both make the repo credible. A README section that says **where this does not help** is the single
highest-value paragraph in a measurement repo; unhedged marketing inside an audit-yourself repo
destroys the claim (same rule as §8/§9 of the skill).

## 3. Auditing a third party's claims

When the artifact audits a vendor's ad/positioning:

- Keep **their claim** and **our measurement** in visibly separate columns; never present our
  number as if they published it.
- Publish the finding constructively ("the ad sells accuracy; the measured advantage is
  latency/cost/determinism") — an ad audit is not an attack piece, and a client may be the vendor.
- If a claim cannot be measured, say so instead of ranking it.

## 4. Integrity-gate interplay (get this right or you ship a false claim)

The content gate that guards claims (`~/ops/verify/claim_integrity.py`) reads **text files**:

- **Paragraph scope**: a `[src: …]` tag on the line ABOVE a metric does not clear it — a metric on
  its own line below its tag failed as a HIGH. In one-claim-per-line drafts, put the tag at the
  **end of the same line**.
- **The gate cannot see your PNG.** The rendered visual is an unguarded claim surface: the card
  said `18×` while the measurement was `17.6×` and the caption said `17.6×`. Cross-check the
  rendered text against the gated draft, and prefer the exact measured figure over a round one.
- **Strip the tags before publishing** (`[src: …]`, `[claim-ok: …]`) — they belong to the review
  trail, not to a post, a client deliverable, or a printed artifact.
- Own measurements are the strongest evidence tier: tag the reproducible report + the command that
  regenerates it.

## 5. Verifying the launch

Ad-hoc `/tmp/hermes-verify-<topic>.py` over the changed set (see skill §7) and remember it reaches
things the repo's own suite cannot:

- `make verify` in the repo (the canonical command) **plus** the platform-side facts.
- **Copy that shipped == copy the gate passed** — compare each draft's length against the platform
  limit *in the platform's own units*: **X counts every URL as 23 chars**, so `len()` fails a post
  that X actually accepted. LinkedIn's length was compared unstripped and looked off by one.
- Read-back per platform: Bluesky has a **public read API** (`app.bsky.feed.getPostThread`, no
  auth) → verifies the post, its image embed and the QA reply. X verifies from the create
  response's `data.id` + attached media key. LinkedIn verifies from the 201's `x-restli-id` only.
- When a check fails, first ask whether the **assertion** is wrong (units, stripped vs raw) —
  two of three failures in the reference session were bad assertions, not bad artifacts. Fix the
  check, re-run, and say so; don't quietly drop it.
