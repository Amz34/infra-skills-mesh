# Confidential mode (local-only profile + gate + client vaults)

Built 2026-09-10 on the Oracle Cloud VM (`hermes-vnic`). Keeps bid/tender/client
material off third-party AI APIs.

## 1. `confidential` profile — the hard guarantee

```bash
hermes profile create confidential --description "Local-only models, no cloud APIs"
C=/home/ubuntu/.local/bin/confidential        # wrapper: hermes -p confidential "$@"
$C config set model.default llama3.2:3b
$C config set model.provider custom
$C config set model.base_url http://127.0.0.1:11434/v1
$C config set model.context_length 131072     # llama3.2:3b native window
$C config set model.fallback_providers '[]'
$C config set telemetry.enabled false
```

Pitfalls learned:

- A fresh profile has an empty `.env` → **no API keys**. Keep it that way: this is
  what makes "no cloud egress" a physical fact instead of a promise. Never copy
  the default profile's `.env`.
- `model.default` must be a **real model name**, not an alias: Hermes passes the
  string to the provider verbatim (`404 model 'local' not found` otherwise).
- Hermes refuses models with a context window < 64000. `qwen2.5:7b` reports 32768
  natively → either use `llama3.2:3b` (131072) or build an Ollama variant with
  `PARAMETER num_ctx 65536` and set `model.context_length` to match.
- On a 2-vCPU box `qwen2.5:7b-64k` needs ~5 min per reply. `llama3.2:3b` answers in
  ~30-160s. Set `OLLAMA_KEEP_ALIVE=30m` (systemd override on `ollama.service`) so
  repeat turns skip the model-load penalty.
- Verify with `confidential chat -q "Reply with exactly: OK"` — check the answer
  text, not just the exit code (a session summary prints even when the model
  returns nothing).

## 2. `secure-bid` gate — `~/.hermes/scripts/bid_secure.sh`

`gate` (via `pii_gate.py --mode classify`, exit 0 clean / 10 local-only / 11
sensitive), `ask` (local chat), `rag` (local hmw_bid chroma), `scan <dir>`,
`redact`, `status`.

## 3. `client-vault` — `~/.hermes/scripts/client_vault.sh`

`~/clients/<slug>/{vault,manifest.jsonl}`, key per client in
`~/.config/client-vaults/<slug>.key` (600). AES-256 OpenPGP symmetric via
`gpg --passphrase-file`.

Pitfalls:

- `gpg --list-packets` exits 2 on symmetric files (it tries to unwrap the session
  key) → do NOT use it as an integrity test. Verify by decrypting and piping into
  `tar -tzf -` with `--pinentry-mode loopback --passphrase-file`.
- With `set -u`, a helper `manifest()` that reads `$1` fails the moment any call
  site forgets the argument (`$1: unbound variable`, then paths resolve to `/`).
  Pass the client explicitly everywhere.
- Store paths relative to `/` (`tar -C / ... "${p#/}"`) to avoid leading-slash tar
  warnings and keep extraction paths predictable.

## 4. Client-facing statement

`~/az_consultants/trust-pack/` — HTML (`part_a/b/c.html`) + 6-page PDF, English,
no emojis/faces, honest limits (no ISO 27001 claim, disk encryption not claimed,
cloud LLM use disclosed for non-confidential chat only).
