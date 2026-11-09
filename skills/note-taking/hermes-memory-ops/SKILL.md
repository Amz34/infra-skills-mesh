---
name: hermes-memory-ops
description: "Use when backing up, sizing, or offloading Hermes memory."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [memory, backup, restore, ops, hermes]
---

# Hermes Memory Ops — 3 Layer Memory Solution

Use when backing up, restoring, or versioning Hermes memory/config files,
when the user asks about "memory backup", "desktop guide", when memory
files need protection against loss, or when memory is near its char cap and
standing facts need offloading into a curated layer (see
`references/memory-offload-to-brain.md`).

## The 3 Layers

1. **Layer 1 — Hermes Skill** (this file): procedure lives in the skill
   system — always available, survives sessions.
2. **Layer 2 — Desktop Guide**: human-readable `MEMORY_BACKUP_GUIDE.md` on
   the user's desktop (Windows/OneDrive path) — the user can follow it
   manually even without Hermes.
3. **Layer 3 — GitHub Private Repo**: automated backup of memory + ops +
   clients to a private GitHub repo (`memory-backup`). No secrets.

## Backup Procedure (Layer 3 — GitHub)

```bash
# 1. Create/update the backup repo
mkdir -p /home/ubuntu/memory-backup/memories
cp /home/ubuntu/.hermes/memories/MEMORY.md /home/ubuntu/memory-backup/memories/
cp /home/ubuntu/.hermes/memories/USER.md /home/ubuntu/memory-backup/memories/
cp -r /home/ubuntu/ops/* /home/ubuntu/memory-backup/ops/ 2>/dev/null
cp -r /home/ubuntu/clients/* /home/ubuntu/memory-backup/clients/ 2>/dev/null

# 2. NEVER copy secrets
# .env, *token*.json, creds.json — exclude always

# 3. Commit + push
cd /home/ubuntu/memory-backup
git add -A
git -c user.name="Aamir Zahran" -c user.email="aamir1zahran@gmail.com" commit -m "Backup $(date -u +%Y-%m-%d)"
git push origin main
```

## Desktop Guide Sync (Layer 2)

Guide path on user's machine (Windows):
`C:\Users\<user>\OneDrive\Desktop\MEMORY_BACKUP_GUIDE.md`
(Windows + OneDrive Desktop — paths shift, always re-locate with search)

## Sizing the char limits (memory / user budget)

`memory.memory_char_limit` (default 2200) + `memory.user_char_limit` (default 1375) live in
`~/.hermes/config.yaml`; both files are injected into **every** turn, so raising them is a recurring
token cost (~2.75 chars/token → +2000 chars ≈ +700 tokens/request). Set with
`hermes config set memory.memory_char_limit 6000`, and remember the limit is baked at **agent init**:
a running session keeps the old number until a new session / gateway restart. Thresholds, the
fresh-process verification snippet, the cost math, and how to tell the memory window apart from the
model context window and `compression.threshold_tokens`: `references/limit-tuning.md`.

## Editing memory when it is at / near the cap

Once the store is ~95%+ full a lone `add` is **rejected** — which is exactly the situation you are
in when you are *reducing* memory (offloading standing facts to a brain/wiki/kb). The char limit is
checked only on the **final result of a batch**, so free space and add in the SAME call:

```
memory(operations=[
  {"action": "replace", "old_text": "<stale entry substring>", "content": "<tighter rewrite>"},
  {"action": "remove",  "old_text": "<low-value entry substring>"},
  {"action": "add",     "content": "<the new durable fact / pointer>"},
])
```

Rules that make this cheap and safe:

- **Batch the whole pass into one call.** Two sequential calls each re-check the limit, so the
  second one can be refused even though the total is smaller.
- **Trim to ~80% headroom, not 100%.** A store sitting at the cap turns the next session's first
  capture into a rejection loop, and the "remove something" reaction happens under time pressure.
- **Shortening beats deleting.** Dropping examples, dates and parentheticals from the longest
  entries usually frees more than removing a whole entry, while losing less signal.
- **The second half of every offload is a POINTER.** After a brain/kb absorbs the detail, rewrite
  the memory entry as *path + cadence + skill name* — never keep a duplicate of the content, or the
  two copies drift and the memory text silently becomes the stale one.
- Capture the entry's exact old substring before editing; a `replace` whose `old_text` no longer
  matches fails the whole batch (all-or-nothing), so verify the anchor is still present.
- The full offload procedure — inventory → curated markdown layer → pointer rewrite → verify, plus the
  worked example and the "two copies drift" pitfall: `references/memory-offload-to-brain.md`.

## Pitfalls

- **NEVER commit**: `.env`, `token.json`, `creds.json`, session files,
  API keys — .gitignore them FIRST.
- Memory files are 0600 perms — fine for cp, but verify the backup dir
  doesn't accidentally include `.lock` files (harmless, skip).
- If repo doesn't exist yet: `gh repo create memory-backup --private` first.
- Desktop guide must be plain English/Hinglish — user reads it manually.
