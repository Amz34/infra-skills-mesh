---
name: agy-vertex-lane
description: Run agy CLI on Vertex ADC lane (not consumer quota).
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [agy, antigravity, vertex-ai, gcp, adc, telegram, cron]
    related_skills: [hermes-agent, model-tier-selection, hermes-cloud-vm-ops]
---

# agy on the Vertex (ADC) lane

## When to Use

- Running `agy` from Telegram/Hermes console, cron, systemd, or any script.
- Plain `agy` returns `Quota exceeded ... daily cloud code` (consumer lane exhausted).
- You need agy's model catalog for this GCP project, or a model/location that actually resolves.
- Do NOT use for one-off interactive TUI sessions (just run `agy` in a terminal).

`agy` defaults to Google's Antigravity consumer backend (`daily-cloudcode-pa.googleapis.com`), which
reports `Quota exceeded ... daily cloud code` once the free daily credits are gone. The same CLI can
run on Vertex AI using the machine's existing gcloud ADC (`amer231105@gmail.com`), billed to GCP
project `project-8c42a42e-60f3-4ca3-8c2` (billing enabled, `aiplatform.googleapis.com` on, trial credits).
No new OAuth flow is needed.

## Trigger

Any of these, always through the wrapper:

- Telegram / Hermes console: user says "agy se yeh karo" or gives a prompt → agent runs
  `terminal("cd <workdir> && env -i HOME=/home/ubuntu PATH=/usr/bin:/bin timeout 300 /home/ubuntu/.local/bin/agy-v -p '<prompt>'")`.
- Scripts / cron / systemd: same command. The wrapper sets PATH itself, so no `.bashrc` dependency.

## The three variables that actually matter

```
AGY_ADC_AUTH=1                 # official ADC sign-in switch (in agy's own changelog)
GOOGLE_CLOUD_PROJECT=<project>
GOOGLE_CLOUD_LOCATION=global   # NOT us-central1 for Argon / 3.1 Pro
```

`AGY_VERTEX_PROJECT` / `AGY_VERTEX_REGION` / `AGY_VERTEX_MODELS` are **not read** by the binary —
they were a guess. `GOOGLE_GENAI_USE_VERTEXAI=true` is also set by the wrapper (harmless, standard SDK var).

## Wrapper (already installed)

`/home/ubuntu/.local/bin/agy-v`:

```bash
agy-v -p "prompt"                              # default gemini-3.8-flash-high
AGY_MODEL=gemini-3.8-flash-low agy-v -p "..."  # cheap/fast
agy-v -p "..." --model gemini-4-argon-high     # heavy reasoning
agy-v models                                   # live catalog for this project
```

It unsets `GOOGLE_API_KEY` / `GEMINI_API_KEY*` so a leftover AI Studio key cannot hijack the lane,
and appends one line per run to `~/.local/state/agy-vertex/runs.log` (model, rc, seconds).

## Argon is the default on the `agy-argon` instance (Oct 2026)

`agy-argon` (the Vertex/`Gemini Studio Argon` instance) now defaults to
`gemini-4-argon-high` instead of `gemini-3.8-flash-high`. Catalog ids are tiered:
`gemini-4-argon-low|medium|high` — the tier is part of the model name, there is no
`gemini-4-argon` plain entry.

Override per call without editing the wrapper:

```bash
agy-argon -p "..."                          # argon-high
AGY_MODEL=gemini-4-argon-low agy-argon -p "..."   # cheaper tier
AGY_MODEL=gemini-3.8-flash-high agy-argon -p "..." # back to flash for bulk work
```

**Fail-open fallback:** if an argon call exits non-zero, the wrapper retries once on
`gemini-3.8-flash-high` and logs `model=gemini-4-argon-high->gemini-3.8-flash-high`.
Verified by forcing a bogus model name (rc=1 → fallback → SUCCESS). Disable with
`AGY_NO_FALLBACK=1`.

**Latency reality (measured):** 28 s trivial prompt, 97 s one shell tool call, 194 s
reading one file and reviewing it — versus ~4 s on `3.8-flash-high`. Argon's value is
judgement quality, not speed; give it `timeout 300+` and never put it on an
interactive path without a spinner.

**Regression guard:** `agy-instances` now fails if the last argon run's model is not
`gemini-4-argon*`, so a silent drift back to flash gets caught.

## Model catalog (live, Oct 2026 — read `agy-v models` first)

The catalog drifts: names that worked last month (`gemini-2.5-flash`, `gemini-2.5-pro`) are now
rejected client-side with `not recognized as a known model`, which then prints the whole list.
Rules that hold regardless of drift:

- `global` carries the full catalog: `gemini-4-argon-*`, `gemini-3.8-flash-*`, `gemini-3.7/3.6/3.5-flash*`,
  `gemini-3.1-pro-low-thinking`, `gemini-3.1-flash-lite-preview`, `gemini-3-flash-preview`, plus
  `claude-*-5-5-*` entries.
- `gemini-3.8-flash` on `us-central1` → 404 `Publisher model ... was not found`. Region problems
  look like model problems; the matrix below is a snapshot, `agy-v models` is the truth.
- Verified end-to-end on `global`: `gemini-3.8-flash-low/high`, `gemini-4-argon-*`.

Use `global`. Latency: ~7 s single-turn; ~2.5 min when the agent runs tools (file write test).

## Pitfalls

- Plain `agy -p` (no env) = consumer lane → `Quota exceeded` even though ADC is valid. Never use it in cron/bots.
- **Lane values are forced, not defaulted.** `agy-v` uses `GOOGLE_CLOUD_PROJECT="${AGY_PROJECT:-<canonical>}"`
  and `GOOGLE_CLOUD_LOCATION="${AGY_LOCATION:-global}"`. It must never be written as
  `${GOOGLE_CLOUD_LOCATION:-global}`: an inherited `us-central1` in the parent shell then silently
  demotes the lane and every catalog model 404s. Deliberate overrides: `AGY_LOCATION=us-central1`,
  `AGY_PROJECT=...`.
- Wrapper exits `78` (stderr only) when the ADC file is unreadable — stdout stays clean for `-p`.
  `runs.log` records `model= loc= proj= rc= secs=`; `loc=`/`proj=` show what was *requested*, never
  what was reached — endpoint proof requires the cli log.
- Passing a raw Vertex name outside agy's catalog (`--model gemini-2.5-flash`) fails client-side with
  `not recognized as a known model`; use catalog names from `agy-v models`.
- A catalog model can still 404 on a region (e.g. `gemini-3.8-flash` on `us-central1`): that is a location
  problem, not auth. Switch `GOOGLE_CLOUD_LOCATION=global`.
- `-p` mode auto-settles approval prompts (settings.json: `autoApprove`, `allowNonWorkspaceAccess`), but
  long tool loops need `timeout 300+`; don't run it with the default 180 s terminal timeout.
- ADC here is `authorized_user` (refresh token, `quota_project_id` set) — it refreshes over HTTP; the
  `gcloud` binary is not required at runtime.
- The `vertex-argon-proxy` caches its ADC token ~50 min. If that token is revoked/rotated early, the
  proxy returns 401 UNAUTHENTICATED until the cache refreshes. The proxy now invalidates+retries once
  on 401/403 (self-heals, no restart). If 401s persist despite the retry, the `authorized_user`
  refresh_token itself is dead — re-run `gcloud auth application-default login` as `amer231105@gmail.com`.

## Web console (antigravity.google.com) — named instances

`agy remote-control` pairs a CLI session to the web console. Facts that cost time to discover:

- Instance name lives in `$HOME/.gemini/config/config.json` → `userSettings.cliRemoteControlHostname`.
  `agy remote-control start --name "X"` only rewrites that key, then needs a signed-in token.
- One instance == one HOME. `installation_id` in `$HOME/.gemini/antigravity-cli/` is the console's
  identity, so a **second instance = second HOME**, not a second `--name` on the same HOME.
- `remote-control status` is NOT HOME-scoped: it reports the hardcoded
  `antigravity-cli-daemon.service` regardless of `$HOME` (it printed "active since" the *other*
  daemon). Trust `config.json` for the name, `systemctl` for the unit, the per-HOME
  `remote-control-serve-telemetry.json` timestamp for registration success.
- The daemon's own env is the lane for every web-launched session. A vanilla
  `agy remote-control serve` unit has **zero** Vertex vars → web sessions silently use the consumer
  lane while `agy-v` on the CLI looks perfect.
- `useG1Credits` is stripped from `settings.json` by the CLI on first run; lane is decided by env
  (`AGY_ADC_AUTH`, `GOOGLE_GENAI_USE_VERTEXAI`, project, location), not by that key.
- ADC with an overridden HOME: set `GOOGLE_APPLICATION_CREDENTIALS` to the real gcloud ADC path
  instead of copying the secret into the new HOME.

Working layout on this VM (`agy-instances` asserts it, exit 0 = healthy):

| instance | HOME | unit | lane |
|---|---|---|---|
| `invertio-infra` | `/home/ubuntu` | `antigravity-cli-daemon.service` | consumer (untouched, on purpose) |
| `Gemini Studio Argon` | `/home/ubuntu/agy-argon-home` | `agy-argon.service` | Vertex `global`, project forced |

CLI entry point for the same Argon context: `agy-argon -p "..."` (logs to
`agy-argon-home/.local/state/agy-vertex/runs.log`). Build/rollback recipe: `references/web-instances.md`.

## Verify the lane (10 s)

```bash
/usr/bin/time -f "TOTAL=%es" /home/ubuntu/.local/bin/agy-health   # 7 checks, exit 0 = healthy
/home/ubuntu/.local/state/agy-vertex/qa-6gate.sh                   # deterministic gates, exit 0 = 7/7
```

`qa-6gate.sh` is the assert-not-print version: catalog, live turn, state-log rc, endpoint mix,
lane-hijack regression (decoy keys + hostile region/project), isolated endpoint count, forced global.
Use it after any wrapper/binary/env change — `agy-health` reports, `qa-6gate.sh` fails.

Full phase-wise diagnosis (binary strings, ADC/billing, region matrix, endpoint proof,
Hermes/Telegram rules, symptom→cause table): `references/runbook.md`.

Manual one-liner:

```bash
env -i HOME=/home/ubuntu PATH=/usr/bin:/bin /home/ubuntu/.local/bin/agy-v -p "Reply with exactly: OK"
# proof of endpoint actually used:
L=$(ls -t ~/.gemini/antigravity-cli/log/cli-*.log | head -1)
grep -oE "aiplatform.googleapis.com/v1/projects/[^\"]+" "$L" | tail -3
```

## Cost rule

Vertex usage burns the GCP trial credits, not free quota. Bulk work: `gemini-3.8-flash-*`.
Hard reasoning, long-context review, architecture calls: `gemini-4-argon-*` on purpose.
`agy-argon` defaults to argon because that instance exists for heavy work — everything else
should use `agy-v` with flash.

## Hermes / Telegram access — alias vs picker row

Two routes to the same Vertex credits (both bill project `project-8c42a42e-...`):

- `/model argon` — model alias at the local proxy (`~/ops/vertex-argon-proxy`, port 8801,
  `chat_completions`). Session-scoped unless `--global`; fine for a one-task switch or a sub-agent.
- `/model` picker → **Argon Vertex** — a top-level `custom_providers:` entry (base_url
  `http://127.0.0.1:8801/v1`, `discover_models: false`) listing `gemini-4-argon`, `3.8-flash`,
  `3.7-flash`, `3.1-pro-low-thinking`. **An alias never renders as a picker provider** — the
  `custom_providers` entry is what makes the button exist. Recipe + verification snippet:
  skill `hermes-agent` → `references/providers-and-models.md`.

Delegation one-liner when the user asks "kya prompt dena hoga": `/model argon` for the whole chat,
`agy-argon -p "<task>"` for a single task. Project / location / model never go in the prompt — the wrapper
forces them; bare `agy` is the consumer lane and must not be used. `/model argon` bills every later
turn, so revert to the cheap default once the heavy task is done.

**Token-source proof** (rerun after any proxy/config change): the proxy ignores the client's placeholder
bearer (`no-key-required`) and injects an ADC token, so picker traffic hits `aiplatform.googleapis.com`,
never AI Studio. Evidence = `200` from `POST http://127.0.0.1:8801/v1/chat/completions` **plus** the
model id echoed back, and `aiplatform` hits in the newest
`~/.gemini/antigravity-cli/log/cli-*.log` with zero `daily-cloudcode-pa` lines.

