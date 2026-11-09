---
name: secrets-vault-ops
description: Use when handling VM secrets - store, rotate, audit leaks.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [secrets, vault, age, credentials, security, audit, backup]
    related_skills: [infra-hardening-crashproof, cloud-vm-backup-dr, hermes-memory-ops]
---

# Secrets Vault Ops (age, offline, zero-cost)

Self-hosted encrypted vault for every credential on the box. It is the **system of record** for
secrets, while the original scattered `~/.../.env` / `credentials.json` / `token` files stay in
place so live services keep working.

## When to use
- A new API key / token / password needs storing → put it in the vault, not a loose file.
- A script or cron needs a secret → `vault exec <space> -- cmd`, never a hardcoded value.
- "Kahan kahan secrets pade hain / leak ho sakte hain?" → `vault audit`.
- Backup/DR of credentials → `vault backup` (ciphertext only, safe to offload).
- Rotating a leaked/expired credential → `vault set` + fix the source + re-verify.

## Layout
| Path | What |
|---|---|
| `~/.config/space-vault/identity.txt` | age private key, mode 600 — **lose it and all data is gone** |
| `~/.config/space-vault/store/<space>.json.age` | one age-encrypted JSON per space (secrets + `files` + meta) |
| `~/.config/space-vault/backups/` | ciphertext backups |
| `~/.config/space-vault/RECOVERY.md` | recovery steps (read before touching the vault) |
| `~/.hermes/scripts/vault.py` | the CLI (`vault` wrapper lives in `~/.local/bin/vault`) |
| `~/.hermes/scripts/vault_migrate.py` | PLAN table: source → space import, perms tightening, `--verify` |
| `~/.hermes/scripts/vault_watchdog.sh` | silent weekly cron (`vault-watchdog`, Mon 03:30 UTC) |
| `~/.hermes/scripts/cf_token_check.py`, `find_cf_tokens.py` | live-credential probes (hash-only output) |

Spaces in use: `infra`, `hermes-default`, `hermes-profiles`, `zoho-books`, `sanad`, `avvs`,
`invertio`, `luxewave`, `az-consultants`, `servicetitan`, `hmw`, `personal`.

## Commands
```bash
vault init | verify | spaces                       # setup, self-test, inventory
vault list <space> | show <space>                  # key NAMES only (safe to paste in chat)
vault get <space> KEY                              # print one value
vault set <space> KEY=VAL                          # add/update (KV lands in shell history → prefer:)
printf '%s=%s' KEY "$VAL" | vault set-stdin <space>   # VERIFIED 2026-09-18: set-stdin takes ONLY <space>;
                                                      # the KEY=VAL pair comes on stdin. `--stdin` flag does NOT exist.
vault rm <space> KEY
vault import <space> <file.env> [--prefix P]       # bulk import KEY=VALUE
vault exec <space> -- cmd args...                  # inject as env vars, nothing written to disk
vault export <space> <out.env>                     # plaintext 600 file for legacy tools
vault put-file <space> <name> <path>               # store a whole file (json/toml/yml)
vault get-file <space> <name> --out <path>
vault list-files <space> | rm-file <space> <name>
vault audit [--json|--strict|--quiet|--all]        # leaks / perms / unvaulted / drift / git
vault backup --out <dir>                           # ciphertext only
vault rekey                                        # rotate identity, re-encrypt all spaces
```

## Conventions
1. **New secret → `vault set` first**, then wire the consumer (`vault exec` for scripts/cron;
   `vault export` only when a tool insists on an env file).
2. One space per brand/domain (`sanad`, `avvs`, `az-consultants`, …) + `infra` for VM-level
   platform creds. Never mix client secrets across spaces.
3. Values never go into chat/summary output — print **names** (`vault list`) or hashes when
   reporting; use the `cf_token_check.py` pattern (sha256 prefix + live HTTP status).
4. Deleting a source file is optional; keep it until you've proven the consumer reads the
   vault. `vault audit` reports "vaulted-but-still-on-disk" as INFO, not a problem.
5. After editing a source by hand, re-import or the audit flags DRIFT:
   `python3 ~/.hermes/scripts/vault_migrate.py --apply`.

## Migrating a new scattered credential
1. Add a line to `PLAN` in `vault_migrate.py`:
   `("~/path/file.env", "env")` | `("~/path/file.json", "file:custom-name.json")` | `("~/path/x", "raw:KEY_NAME")`
2. `python3 ~/.hermes/scripts/vault_migrate.py --dry-run` → sanity-check the plan.
3. `--apply` then `--verify` (expect `N match, 0 mismatch`).
4. `vault audit` → expect `0 actionable`.

## Pitfalls (all hit for real)
- **`vault exec <space> -- bash -c '...'` quoting**: nested quotes get eaten. Put the logic in a
  `.py`/`.sh` file and run `vault exec <space> -- python3 /path/script.py`.
- **Two sources, same filename** (e.g. two `credentials.json`) → the second silently overwrites
  the first. Always use `file:<unique-name>`.
- **Comment-only templates** (`~/.config/ai-memory/env`) look like creds but hold none — the
  audit requires a non-comment `KEY=VALUE` line, so it won't flag them.
- **Browser profile internals** ("Trust Tokens", `TrustTokenKeyCommitments`, `scoped_dir*`,
  chrome-forms profiles) flood a naive `token`/`keys` grep — excluded via `BROWSER_RE`.
- **Session state ≠ secrets**: WhatsApp/Telegram session dirs are thousands of managed files;
  the audit reports them as "managed session files skipped" — don't vault them.
- **401 on a "vaulted" token doesn't mean the vault is wrong** — it means the *source* holds a
  stale credential. Probe live before trusting a stored key (`find_cf_tokens.py` found both
  CF API tokens dead while deploys actually authenticate via wrangler OAuth in
  `~/.wrangler/config/default.toml`).
- **Drift is silent**: services read the on-disk file, not the vault. A hand-edit makes vault and
  disk disagree — that's what `--verify` and the watchdog exist to catch.

## Recovery / DR
- Identity backup: copy the line in `identity.txt` into a password manager **once** (user action).
- Restore: paste identity back to `~/.config/space-vault/identity.txt`, `chmod 600`, `vault verify`.
- Ciphertext backups may live in Drive/bucket/git — the identity must NOT sit next to them.
- `vault rekey` after any suspected identity exposure, then re-run `vault backup`.

## Verification checklist
```bash
vault verify                                          # roundtrip ok
vault audit                                           # 0 actionable
python3 ~/.hermes/scripts/vault_migrate.py --verify   # 0 mismatch
bash ~/.hermes/scripts/vault_watchdog.sh              # prints nothing when clean
```
