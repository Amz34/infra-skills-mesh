# Sizing the memory limits (char budget)

The two memory files are injected into the system prompt on **every turn**, so their char limits are a
per-request token cost, not just a storage knob.

## Where the knobs live

- `~/.hermes/config.yaml` → `memory.memory_char_limit` (default **2200**), `memory.user_char_limit`
  (default **1375**). This box: memory raised **4000 → 6000** on 2026-09-10, user left at 2000.
- Read/set with the CLI (dot path):
  ```bash
  hermes config get memory.memory_char_limit      # -> 6000
  hermes config set memory.memory_char_limit 6000
  ```
- The limit is what the system-prompt header prints (`MEMORY [95% — 3,657/4,000 chars]`) and what the
  `memory` tool returns as `current/limit`. Raising it is *not* a filesystem change — nothing in
  `MEMORY.md` is rewritten.

## When a change actually takes effect

The store is built at **agent init**, and the limit is baked in at that moment. Prove the *file* value
from a fresh process:

```bash
cd ~/.hermes/hermes-agent && venv/bin/python -c "
import sys; sys.path.insert(0,'.')
from tools.memory_tool import get_builtin_memory_config
c = get_builtin_memory_config(); print(c.get('memory_char_limit'), c.get('user_char_limit'))"
```

A **running session keeps the old limit** — observed live: right after `hermes config set … 6000`, the
in-session `memory` tool still answered `…/4,000`. So report it as "naya session / gateway restart ke
baad lagu" rather than implying it is already live; the next agent init picks the new number up.

## Cost math

~2.75 chars/token, and **both** files ride along every request: +2000 chars of memory ≈ **+700 tokens
per request**, multiplied by every turn. Cheap on cheap models, not free. Raise it only when the files
are genuinely near-full (this box hit 95% of 4000), and check `hermes-token-cost-ops` for the wider
picture. Order policy (hard rules TOP, new facts END next to their topic) stays in
`references/consolidation-reorder.md` — a bigger budget does *not* change the ordering rules.

## Don't confuse three different "windows"

| how the user may phrase it | real knob | value on this box |
|---|---|---|
| memory window / "the 4000 one" | `memory.memory_char_limit` | 6000 (was 4000) |
| chat context window (tokens) | `model.context_length` (unset → provider default; deepseek = 128k) or `model_overrides.<provider>.<model>.context_window` | 128k |
| when a chat auto-compacts | `compression.threshold_tokens` | 60000 |

A bare number like "extend to 6000" maps to the memory char budget — the only knob in that magnitude.
Do that, then name the other two knobs with their current values so the user can redirect if they meant
one of those; asking a blocking question instead of acting wastes a turn on a reversible config change.
