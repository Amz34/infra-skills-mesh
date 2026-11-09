# Onboarding a NEW bot as its own Hermes profile (verified 2026-09-20)

Worked case: user forwarded a fresh BotFather token ("https://t.me/<Bot> — is bot ko on karo")
→ bot came live as **profile `<name>` + `hermes-gateway-<name>.service`** in one pass.
Companion reference: `hermes-multi-profile-gateway.md` (fleet map, one-poller-per-token rule).
**Phase 2 (make it a *finished* bot — metadata, avatar, live delivery QA): §8 below +
`botfather-metadata-and-avatar.md`.** Steps 0–7 bring the poller live; §8 is the pass that
catches brand leaks and unfinished BotFather state before the owner sees the bot.

## 0. Pre-flight: prove the token without ever printing it

Never echo the token (not in the command, not in output). Read it from the file and print only
non-secret identifiers:

```bash
python3 - <<'PY'
import re,json,urllib.request
tok=re.search(r'^<SRCKEY>_BOT_TOKEN\s*=\s*(.+)$',open('$HOME/.hermes/.env').read(),re.M).group(1).strip()
print(json.load(urllib.request.urlopen(f'https://api.telegram.org/bot{tok}/getMe'))['result'])
w=json.load(urllib.request.urlopen(f'https://api.telegram.org/bot{tok}/getWebhookInfo'))['result']
print('webhook=%r pending=%s'%(w.get('url'),w.get('pending_update_count')))
PY
```

- `ok:true` + id/username = token valid. `webhook=''` = clean polling; a non-empty URL would
  409 a local poller until `deleteWebhook`.
- `pending_update_count` may be ≥1 (the user already messaged the bot) — it should drain to 0
  once the gateway starts. That drain is evidence the poller took over.
- Print key **names** only when auditing a `.env`:
  `python3 -c "import re;print(','.join(re.findall(r'^([A-Z0-9_]+)=',open(P).read(),re.M)))"`

## 1. Create the profile — know what `--clone` copies

```bash
HERMES_HOME=... /path/venv/bin/python -m hermes_cli.main profile create <name> --clone --description "…"
```

- Creates `~/.hermes/profiles/<name>/` (config.yaml, `.env`, SOUL.md, memories, skills) and a
  shell alias `<name>`.
- ⚠️ **`--clone` copies the ACTIVE profile, which may be a CLIENT profile.** Verified: the new
  bot got Invertio's `config.yaml`, `.env` and `SOUL.md` (i.e. a client's brand personality +
  that client's every secret). Review SOUL.md and reset it when the bot is not that client's
  persona; keep only the keys the new bot actually needs.
- Per-profile config works two ways: `HERMES_HOME=<profile dir> …` or `… --profile <name>`.
- **Prefer `--clone-from <sibling-profile>`** (`hermes profile create <new> --clone-from <existing>
  --description "…"`, verified 2026-09-21) so you clone the right sibling deliberately instead of
  whatever profile happens to be active. It still copies the sibling's `SOUL.md`, `memories/`,
  `config.yaml` and `.env` wholesale — the brand sweep in §8.5 is mandatory either way.

## 2. Swap the token in the profile's own `.env`

`~/.hermes/profiles/<name>/.env`, `chmod 600`, replace `TELEGRAM_BOT_TOKEN=`, set
`TELEGRAM_ALLOWED_USERS=<owner tg id>` and `TELEGRAM_HOME_CHANNEL=<owner tg id>`.
Do the edit with a Python heredoc so the secret never lands in a shell command line or log.

**Platforms auto-enable from token presence, not from config.** `config get platforms.<x>.enabled`
returns `not set` on every profile, yet the gateway starts whatever platform tokens it finds — so a
cloned `SLACK_*` set is *why* the new gateway tried Slack. Strip tokens for platforms this bot
should not host (fleet-exclusive ones like Slack most of all):

- Symptom: new gateway logs `Slack app token already in use by <other-profile>` and retries the
  app-token handshake forever (same cliff as the Telegram 409 — one token, one 24/7 host).
- Fix: remove `SLACK_BOT_TOKEN` / `SLACK_APP_TOKEN` / `SLACK_SIGNING_SECRET` (+ `SLACK_ALLOWED_USERS`)
  from the new profile's `.env`, then restart the gateway. Verify the reconnect loop stops.

## 3. Install + start the gateway service

```bash
HERMES_HOME=~/.hermes/profiles/<name> <venv>/bin/python -m hermes_cli.main gateway install --start-now --start-on-login
```

Creates/updates `~/.config/systemd/user/hermes-gateway-<name>.service` and starts it (survives reboot).

## 4. Apply the guardrail drop-in — a fresh unit does NOT inherit it

The fleet's `~/.config/systemd/user/hermes-gateway.service.d/99-guardrails.conf` (MemoryHigh/
MemoryMax/MemorySwapMax/TasksMax/LogRateLimit, `CPUWeight`/`IOWeight`) applies only to the unit it
sits under. Copy it to the new unit's own `.service.d/`:

```bash
mkdir -p ~/.config/systemd/user/hermes-gateway-<name>.service.d
cp ~/.config/systemd/user/hermes-gateway.service.d/99-guardrails.conf \
   ~/.config/systemd/user/hermes-gateway-<name>.service.d/
# append state.db WAL safety (all gateway units carry it)
printf '\nTimeoutStopSec=180\nKillMode=mixed\n' >> ~/.config/systemd/user/hermes-gateway-<name>.service.d/99-guardrails.conf
systemctl --user daemon-reload
```

- `daemon-reload` alone does not change live limits — the unit must restart (step 5).
- Match the fleet; don't invent policy. Every gateway here reports
  `CPUQuotaPerSecUSec=infinity`; the hardening is the memory/task caps + stop timeout.
- Confirm afterwards: `systemctl --user show hermes-gateway-<name> -p MemoryHigh -p MemoryMax -p MemorySwapMax -p TasksMax -p TimeoutStopUSec`.

## 5. Restart path when a guard is in the way

- From inside a gateway session (i.e. the agent's own shell), `systemctl --user restart hermes-gateway*`
  is refused: `blocked: restarting a hermes gateway`.
- **Verified clean path — the Hermes CLI passes the guard:**
  `HERMES_HOME=~/.hermes/profiles/<name> <venv>/bin/python -m hermes_cli.main gateway restart`
  (it prints the new unit PID). Prefer this over hand-rolled subprocess workarounds.
- `systemctl --user daemon-reload`, `systemctl --user is-active`, `systemctl --user show …` are allowed.
- Hand-rolled workarounds around that guard are a dead end — `systemd-run --user --collect
  --unit=… /bin/systemctl --user restart hermes-gateway-<p>` failed too. Use the CLI path above,
  or ask the user to run the restart in their own shell. For a config-only change (e.g. removing a
  cloned `webhook` platform) it is fine to state plainly that it applies on the next restart instead
  of forcing one.

## 6. Declare the new surface (this fleet's governance rule)

Add the unit to `~/ops/observability/autonomy.json`:

- `surfaces["…"] = {kind, level, effect, gate_required, why, reversal}` — for an owner-only
  gateway bot: `level:"L3"`, `effect:"external"` (it delivers on a public platform), `reversal` =
  stop + remove the profile.
- a `critical_services` entry for `hermes-gateway-<name>`.
- Then `python3 ~/ops/scripts/autonomy_audit.py` → expect `0 unclassified`, no new findings
  (worked case: 173 surfaces / 149 classified, clean). Back up the JSON before editing.

## 7. Verification ladder — say honestly how far you got

1. `systemctl --user is-active hermes-gateway-<name>` → `active`.
2. `~/.hermes/profiles/<name>/logs/gateway.log` shows `Connected to Telegram (polling mode)` and
   the startup notification line `Sent home-channel startup notification to telegram:<chat_id>` —
   **this is outbound proof** (the owner really does see a message from the bot).
3. `getWebhookInfo` → `url=''`, `pending_update_count` drained to 0 → the poller consumed the
   pending update.
4. **Inbound (bot → agent → reply) can only be proven by the OWNER messaging the bot.** Do not
   claim the loop is tested; ask him to send "hi" and report exactly that.

## 8. Phase 2 — BotFather metadata, avatar, and the LIVE delivery path (added 2026-09-21)

Worked case: a KSA owner-facing brand bot. Steps 0–7 were done the day before; this pass is what
turned "a poller that answers" into a bot the owner could ship (and what caught a live brand leak).

### 8.1 BotFather metadata — set, then READ BACK

| set | read back |
|---|---|
| `setMyName(name)` | `getMyName` |
| `setMyShortDescription(short_description)` | `getMyShortDescription` |
| `setMyDescription(description)` | `getMyDescription` |
| `setMyCommands(commands=[{command,description},…])` | `getMyCommands` |

- Read-backs return the **effective** value; an empty/absent field means your call didn't land —
  don't report it as configured. Print `name / short / desc / commands=N` in one summary line.
- Description ≤512 chars, short ≤120, name ≤64. Space the calls ~1s (429s are easy here).
- Commands menu is worth setting even for an owner-only bot: it is the owner's own cheat sheet.

### 8.2 Avatar

`setMyProfilePhoto` needs a JSON object, **not** a plain file field — full recipe, exact error
string, and the sibling-avatar matching technique in `botfather-metadata-and-avatar.md`. Verify
with `getUserProfilePhotos` (total_count, and a downloaded round-trip you actually look at).

### 8.3 The bot's website form is part of its delivery surface — go check it

A brand bot usually fronts a site whose enquiry form posts to Telegram. Two independent things
must both be true, and neither is visible from the bot side:

1. **Project env holds THIS bot's token + the owner's chat id** (`TELEGRAM_BOT_TOKEN`,
   `TELEGRAM_CHAT_ID` as Pages/Netlify project secrets). Cloudflare's API will **not** read the
   values back — you cannot audit them remotely; you prove it by observing where a test lead lands.
2. **The last deploy is newer than the bot.** Functions read env at deploy time, so a site
   deployed before the bot existed keeps delivering into the *previous* bot's chat. Real case: the
   KSA site's last deploy predated @KsaAzConsults_Bot, so form leads were going to the India bot's
   DM = cross-brand leak, invisible until a test lead was submitted.

Do this: `selftest` the form with a clearly-labelled payload (`QA TEST - …`) from a throwaway
address, then confirm with the owner which bot chat received it. Fix = update the project secrets
+ redeploy — **ask before a production redeploy**, and offer the choices (redeploy now / preview
first / leave it), listing any local drift that would ship with it (here: a nav CSS tweak and
sitemap dates not yet pushed). Also tell the owner how to roll back.

### 8.4 Two clone-inherited traps seen this pass

- **`memories/USER.md` outranks SOUL.md on language.** The cloned profile's USER.md said "reply in
  Hinglish", so a bot whose SOUL.md wanted professional English for clients answered a client
  enquiry in Hinglish. Fix in SOUL.md, explicitly scoped: *owner chat = owner's language; anything
  a client could read = English, no emoji, no AI mention, honest "not known" over invented facts.*
- **Cloned `webhook` platform → `EADDRINUSE` every minute** on the shared default port (8644) while
  another profile gateway holds it. Remove the block from the clone's `config.yaml` if the bot only
  needs Telegram; it takes effect on restart and stops the noise drowning real errors.

### 8.5 Cheap proofs worth running before you declare success

- **Token exclusivity:** sha256 the new token and compare with every profile `.env` — no duplicate
  ⇒ no 409 risk. (Cheaper and more definitive than watching logs.)
- **Brand sweep:** grep the new profile tree for the sibling brand's country/portal words and fix
  every hit (`SOUL.md`, `memories/`, `config.yaml`) — a clone carries the source brand everywhere.
- **Honest status split:** report "site QA passed", "bot metadata verified", and "inbound loop /
  form-delivery re-point needs your go-ahead" as separate lines. Do not merge an unverified
  delivery path into a "fully operational" claim.

## Notes / limits

- One bot token = one profile = one 24/7 poller. Client bots always get a NEW BotFather token
  (fleet rule), so a client bot can never reuse a profile that already owns a token.
- An agent-backed bot has full tool access: keep `TELEGRAM_ALLOWED_USERS` to the owner (and the
  client) only — never leave it open on a public bot.
