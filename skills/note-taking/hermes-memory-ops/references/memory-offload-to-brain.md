# Offloading standing facts out of MEMORY.md into a curated markdown layer

Trigger: memory is ~95%+ full and standing facts (paths, services, conventions) are competing with
volatile ones for space. Reported symptom is usually "MEMORY.md is at 96%".

## Why memory must not simply grow

Both `MEMORY.md` and `USER.md` are injected into **every** turn (see `references/limit-tuning.md` for the
cost math). So a fuller memory is not just a rejection risk — it is a permanent per-request token tax,
and the entries that get squeezed out are the durable ones because volatile task state keeps getting
re-added.

## Division of labour

| Layer | Holds | Failure mode if abused |
|-------|-------|------------------------|
| `MEMORY.md` / `USER.md` | pointers, preferences, hard rules, cadence + skill names | hits the cap, silently drops the oldest durable fact |
| Curated markdown layer (`~/brains/<name>/`) | the detail the pointers point at: knowledge, decisions, provenance | never read if there is no pointer in memory |
| Legacy/raw layer (`~/ops/kb/`) | frozen original history | writers keep editing it and it drifts from the curated copy |

## Procedure

1. **Inventory the standing entries** and group them by topic (infra, clients, tooling, cadence).
   Anything that is *task state* ("PR open", "phase 1 done") is deleted, not offloaded — it goes stale
   in a week.
2. **Confirm the curated layer exists** for that topic; if not, scaffold one first (the brain pattern).
   Do not offload into a layer nobody reads — that is just deleting with extra steps.
3. **Move the detail, then rewrite the memory entry as a pointer:** path + what lives there + cadence +
   skill name. Always include the skill name, otherwise the next session cannot find the procedure.
4. **Freeze the legacy layer's paths in writing** (banner in its README) before people start moving files
   — skills and cron jobs reference absolute paths.
5. **Do the memory edit as ONE batch call** (replace/remove/add together) and read the returned char
   count; aim for ~80% utilisation, not 100%.
6. **Verify by re-reading**, not by trusting the tool message: `wc -c` the memory file, then confirm a
   fresh session/turn would inject it (limits are baked at agent init — see `references/limit-tuning.md`).

## Worked example (2026-09-11)

`~/ops/kb/` (26 flat files) was mislabelled as memory ("memory limits: 4000 chars" era). It became
`source/` inside `~/brains/ops/` — symlinked, never edited — and the memory entry for it was rewritten
into a pointer naming the brain, the frozen raw layer, the sweep cadence and the skill. Existing skills
and crons kept working because not a single legacy file path moved.

## Pitfalls

- **Two copies drift.** If the memory text keeps a copy of the detail "for safety", the memory copy is
  the one that goes stale (it is read first, updated last). Pointer only.
- **Don't offload volatile state** into a knowledge layer — it will be flagged as stale within weeks and
  trains the reader to ignore the layer.
- **Don't lower the char limit as a first move.** Shrinking the budget with a full store causes an
  immediate rejection loop; offload first, shrink later if still desired.
- **A batch is all-or-nothing.** One bad `old_text` anchor aborts every operation in it, so a partial
  "success" is not possible — check the response for the final char count before claiming the offload worked.
