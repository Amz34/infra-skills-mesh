# Second console instance ("Gemini Studio Argon") — build & rollback

Why a separate HOME: the console keys an instance on
`$HOME/.gemini/antigravity-cli/installation_id`. Two names on one HOME = one instance renamed.

## Build

```bash
H=/home/ubuntu/agy-argon-home
mkdir -p $H/.gemini/config $H/.gemini/antigravity-cli
install -m 600 ~/.gemini/antigravity-cli/antigravity-oauth-token $H/.gemini/antigravity-cli/
python3 - <<'PY'
import json; p="/home/ubuntu/agy-argon-home/.gemini/config/config.json"
json.dump({"userSettings":{"cliRemoteControlHostname":"Gemini Studio Argon",
  "enableNotificationsForSpecialEvents":False,"toolPermission":"always-proceed"}}, open(p,"w"), indent=2)
PY
# unit: ~/.config/systemd/user/agy-argon.service  (Version 1 with HOME + Vertex env + ADC path)
systemctl --user daemon-reload && systemctl --user enable --now agy-argon.service
```

Token copy is a *refresh-token copy* of the same account — no new OAuth login. ADC is **not** copied;
the unit points `GOOGLE_APPLICATION_CREDENTIALS` at the real gcloud ADC.

## Verify

```bash
agy-instances                 # exit 0 = 2/2 healthy
agy-argon -p "reply OK"        # same context the web console spawns
journalctl --user -u agy-argon.service -n 20
```

## Rollback

```bash
systemctl --user disable --now agy-argon.service
rm -f ~/.config/systemd/user/agy-argon.service
rm -rf /home/ubuntu/agy-argon-home        # removes the second instance + its token copy
systemctl --user daemon-reload
```

## Lane3 Gemini API key (secondary credential)

An `AQ.Ab8RN6…` key is a **Gemini API (AI Studio) key — a prepay pool, not project billing.**
It cannot reach a Cloud project's Vertex AI credits: inference on
`generativelanguage.googleapis.com` returns `402 prepayment credits are depleted`, and Vertex
express mode (`aiplatform…?key=`) returns `403 API_KEY_SERVICE_BLOCKED`. Treat "the $300 is in
Vertex" and "here is an API key" as two unrelated money pools until a live call proves otherwise.

Registry + tools (key at `~/.config/agy-argon/lane3.key`, mode 600, never in argv/env of a unit):

```bash
lane3-check                          # models list + generateContent + express mode; exit 0 only if usable
agy-argon --lane key -p "ping"       # force the key lane (by reference, key read from the file)
agy-instances                        # lane3 status is INFO, never a failure — Vertex is the billing lane
```

Key presence does **not** demote the lane: a turn with `GEMINI_API_KEY` + `GOOGLE_API_KEY` set and
`GOOGLE_GENAI_USE_VERTEXAI=true` still logged `aiplatform=2 cloudcode=0`. Still, keep the key out of
the systemd unit — the daemon bills through ADC and a secret in a unit leaks via `systemctl show`.

## Pitfalls

- `remote-control status` prints the *other* daemon's uptime regardless of HOME; it is not evidence.
- The daemon always calls `daily-cloudcode-pa` for `loadCodeAssist` / `fetchAvailableModels`
  (entitlement + catalog). Those logs contain no `aiplatform` and are **not** inference evidence.
- Model traffic marker in `cli-*.log` is `URL: https://aiplatform.googleapis.com/v1/projects/...`
  — the RPC name is not on that line, so do not grep for `generateContent`.
- `useG1Credits` is silently dropped by the CLI when it rewrites `settings.json`; the lane is env-driven.
- Copied `settings.json` keeps `autoApprove`/`command(.*)` grants: a web session on this instance can run
  shell on the VM. Tighten `~/.gemini/antigravity-cli/settings.json` in the argon HOME if that is unwanted.
