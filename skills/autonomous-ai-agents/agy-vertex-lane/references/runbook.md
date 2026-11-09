# agy / Vertex / Hermes — Troubleshooting & Self-QA Runbook

All commands verified on this VM (Ubuntu, Oct 2026). Run from any directory.
Binary: `/home/ubuntu/.local/bin/agy`. Wrapper: `/home/ubuntu/.local/bin/agy-v`.
Automated check: `/home/ubuntu/.local/bin/agy-health` (7 checks, ~17 s, exit 0 = healthy).

## Phase 1 — Binary & environment inspection

**Do not guess env var names.** Confirm them from the binary:

```bash
strings -a "$(command -v agy)" \
  | grep -oE "(AGY_ADC_AUTH|GOOGLE_CLOUD_PROJECT|GOOGLE_CLOUD_LOCATION|GOOGLE_GENAI_USE_VERTEXAI)" \
  | sort | uniq -c
```

Expected: `AGY_ADC_AUTH` (7 hits), `GOOGLE_CLOUD_LOCATION`, `GOOGLE_CLOUD_PROJECT`,
`GOOGLE_GENAI_USE_VERTEXAI` (2 hits).

Do **not** use the loose pattern `grep -E "AGY_|GOOGLE_|VERTEX"` — it emits ~859 lines of
concatenated symbol-table noise, not a list of variables.

**Clean-env test** (this is what cron/systemd/hermes subprocesses see):

```bash
env -i HOME=/home/ubuntu PATH=/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin \
  AGY_ADC_AUTH=1 GOOGLE_GENAI_USE_VERTEXAI=true \
  GOOGLE_CLOUD_PROJECT=project-8c42a42e-60f3-4ca3-8c2 \
  GOOGLE_CLOUD_LOCATION=global \
  timeout 90 agy -p "Reply: ENV_OK"
```

PATH must include `/home/ubuntu/.local/bin`, otherwise `timeout: failed to run command 'agy':
No such file or directory` (exit status is masked to 0 if you pipe into `tail`, so read the text).

Leftover `GEMINI_API_KEY` / `GOOGLE_API_KEY` can hijack the lane — the wrapper unsets them.

## Phase 2 — ADC & billing

```bash
gcloud auth application-default print-access-token --quiet >/dev/null && echo ADC_VALID || echo ADC_EXPIRED
gcloud billing projects describe project-8c42a42e-60f3-4ca3-8c2 --format="value(billingEnabled)" --quiet
gcloud services list --enabled --project project-8c42a42e-60f3-4ca3-8c2 --quiet | grep aiplatform
```

- Use `gcloud billing ...`, **not** `gcloud beta billing ...`: the beta variant prompts for
  component install and dies with "this prompt could not be answered because you are not in an
  interactive session". Add `--quiet` to every gcloud call used from scripts.
- ADC file: `~/.config/gcloud/application_default_credentials.json`, type `authorized_user`,
  account `amer231105@gmail.com`, `quota_project_id = project-8c42a42e-60f3-4ca3-8c2`.
  It refreshes over HTTPS; the `gcloud` binary is not needed at runtime.
- The lane's project comes from ADC's `quota_project_id`. Passing a different
  `GOOGLE_CLOUD_PROJECT` does **not** switch billing (agy resolves the quota project itself).

## Phase 3 — Region & model routing

- `GOOGLE_CLOUD_LOCATION=global` → Argon 4, 3.8/3.7/3.6/3.5 Flash, `gemini-3.1-pro-preview`,
  `gemini-3-flash-preview`, Claude/GPT partner models.
- `GOOGLE_CLOUD_LOCATION=us-central1` → only `gemini-2.5-flash` / `gemini-2.5-pro`.
- `gemini-3-pro-preview`, `gemini-3.1-flash-lite-preview`, `gemini-3.1-flash-preview` → 404 everywhere.

**Trap:** `agy models` is an entitlement list, **not** region-aware. It prints all 18 models even
when the location is wrong, so a healthy-looking catalog can still 404 at request time.

Direct Vertex probe (no agy involved):

```bash
TOKEN=$(gcloud auth application-default print-access-token --quiet)
curl -s -m 45 -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "https://aiplatform.googleapis.com/v1/projects/project-8c42a42e-60f3-4ca3-8c2/locations/global/publishers/google/models/gemini-3.1-pro-preview:generateContent" \
  -d '{"contents":[{"role":"user","parts":[{"text":"ping"}]}],"generationConfig":{"maxOutputTokens":1}}'
```

Codes: `200` reachable, `404` model absent in that location (or not allowlisted), `403` IAM
missing (`roles/aiplatform.user`), `429` quota/credits.

Endpoint host by location: `global` → `aiplatform.googleapis.com`,
regional → `<region>-aiplatform.googleapis.com`.

## Phase 4 — Wrapper & log auditing

`agy-v` must contain: unset of `GOOGLE_API_KEY`/`GEMINI_API_KEY*`; `AGY_ADC_AUTH=1`;
`GOOGLE_CLOUD_LOCATION=global`; default cost-safe model `gemini-3.8-flash-high`.

**Lane values are forced, not defaulted.** The wrapper exports
`GOOGLE_CLOUD_PROJECT="${AGY_PROJECT:-<canonical>}"` and
`GOOGLE_CLOUD_LOCATION="${AGY_LOCATION:-global}"`. It deliberately does **not** read inherited
`GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION` — that pattern (`${VAR:-default}`) let a stray
`GOOGLE_CLOUD_LOCATION=us-central1` in the parent shell silently demote the lane, and every
catalog model except `gemini-2.5-*` then 404s with
`Publisher model ... was not found or your project does not have access to it`.
Deliberate overrides go through `AGY_LOCATION` / `AGY_PROJECT` only.
The wrapper also exits `78` with a stderr message if the ADC file is unreadable (stdout stays clean
so `-p` parsing is never polluted).

`~/.local/state/agy-vertex/runs.log` records `timestamp model= loc= proj= rc= secs=` — it does **not**
prove which endpoint was used. `loc=`/`proj=` prove what the wrapper *asked for*; endpoint proof
comes from agy's own log:

```bash
L=$(ls -t ~/.gemini/antigravity-cli/log/cli-*.log | head -1)
echo "vertex=$(grep -c aiplatform.googleapis.com "$L") consumer=$(grep -c daily-cloudcode-pa.googleapis.com "$L")"
```

Healthy: `vertex>=1 consumer=0`. If `consumer>0`, the call fell back to the consumer lane
(quota error) — check that the wrapper was used and no API key leaked in.

## Phase 5 — Hermes / Telegram execution

`/bash`, `/sh`, `/exec`, `!` are **not** passthrough commands in Hermes — they arrive as plain
prompt text. Never rely on them.

Correct trigger, from Telegram or any Hermes surface:

> "agy-v se yeh karo: <task>"

Agent-side execution standard:

```bash
cd <workdir> && env -i HOME=/home/ubuntu PATH=/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin \
  timeout 300 /home/ubuntu/.local/bin/agy-v -p "<prompt>"
```

- `timeout 300+`: single turn ~7 s, but tool-using loops run 2–3 min (measured 147 s for a
  file-write task).
- Cap returned text before sending to Telegram (`| tail -40`) — agent output can be long.
- One shared Vertex lane means no parallel heavy runs; queue heavy jobs.

### Phase 5 self-QA block (deterministic, 6 gates)

The naive block (`agy-v models | head -n 10` + `agy-v -p ...` + `tail runs.log`) exits 0 even when
the lane is broken: `head` closes the pipe (`Error: writing models: write original-stdout: broken
pipe`) while the pipeline still reports success, and the `QA_PASS` text is never asserted.
Never `2>/dev/null` the catalog probe — that is exactly how an auth crash hides.

```bash
set -uo pipefail
A=/home/ubuntu/.local/bin/agy-v
E="env -i HOME=/home/ubuntu PATH=/usr/bin:/bin"

CAT_OUT=$($E timeout 120 "$A" models 2>&1 | sed -n '1,3p')
[ -n "$CAT_OUT" ] && grep -q "gemini-" <<<"$CAT_OUT" \
  && echo GATE1_CATALOG=PASS || echo "GATE1_CATALOG=FAIL ($CAT_OUT)"

OUT=$($E AGY_MODEL=gemini-3.8-flash-low timeout 120 "$A" -p "Reply: QA_PASS" 2>&1)
printf '%s' "$OUT" | grep -qx 'QA_PASS' && echo GATE2_LIVE_TURN=PASS || echo "GATE2_LIVE_TURN=FAIL ($OUT)"

LAST=$(tail -n 1 ~/.local/state/agy-vertex/runs.log)
case "$LAST" in *" rc=0 "*) echo GATE3_WRAPPER_RC=PASS ;; *) echo "GATE3_WRAPPER_RC=FAIL ($LAST)" ;; esac

L=$(ls -t ~/.gemini/antigravity-cli/log/cli-*.log | head -1)
V=$(grep -c aiplatform.googleapis.com "$L"); C=$(grep -c cloudcode "$L")
[ "$V" -gt 0 ] && [ "$C" -eq 0 ] && echo "GATE4_ENDPOINT=PASS (v=$V c=$C)" || echo "GATE4_ENDPOINT=FAIL (v=$V c=$C)"
```

Gate 6 — the regression test that actually catches lane hijack. Inject consumer keys plus a
hostile region/project; all must be ignored:

```bash
env -i HOME=/home/ubuntu PATH=/usr/bin:/bin \
  GOOGLE_API_KEY=decoy GEMINI_API_KEY=decoy \
  GOOGLE_CLOUD_LOCATION=us-central1 GOOGLE_CLOUD_PROJECT=attacker-project-999 \
  AGY_MODEL=gemini-3.8-flash-low timeout 120 $A -p "Reply exactly: DECOY_BLOCKED"
# must print DECOY_BLOCKED, rc=0; runs.log must show loc=global proj=<canonical>
# newest cli log: aiplatform hits > 0, cloudcode = 0, "attacker-project" = 0
```

Assert on **newly created** cli logs only (`comm -13` of a before/after snapshot) — `ls -t | head -1`
picks a session log that can contain earlier runs, which masks a fresh regression.
Filter with `grep -c cloudcode`, not the full hostname: some builds log the consumer host
without `daily-cloudcode-pa.googleapis.com`.

## 30-second health check

```bash
/usr/bin/time -f "TOTAL=%es" /home/ubuntu/.local/bin/agy-health
```

Prints PASS/FAIL per layer (binary, ADC, billing, API, catalog, live turn, endpoint) and exits
non-zero on any failure. Verified both ways: healthy run = 7×PASS/exit 0; forced bad region =
`clean-env turn` + `endpoint proof` FAIL/exit 1.

Minimal inline version if the script is unavailable:

```bash
env -i HOME=/home/ubuntu PATH=/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin \
  AGY_MODEL=gemini-3.8-flash-low timeout 90 \
  /home/ubuntu/.local/bin/agy-v -p "Reply: QA_PASS" | grep -q QA_PASS && echo LANE_OK || echo LANE_BROKEN
L=$(ls -t ~/.gemini/antigravity-cli/log/cli-*.log | head -1)
grep -c aiplatform.googleapis.com "$L"
```

## Symptom → cause

- `Quota exceeded ... daily cloud code` → consumer lane; env missing or wrapper bypassed.
- `Selected model is not supported in the selected location` + 404 publisher model → wrong
  `GOOGLE_CLOUD_LOCATION`; use `global`.
- `not recognized as a known model` (client-side, no HTTP) → name not in agy catalog; use
  `agy-v models` names.
- `403 PERMISSION_DENIED` → IAM/API/billing on the quota project.
- Token works but requests fail instantly → leftover API key hijacking; run through `agy-v`.
