# Memory consolidation + priority reorder

File format: entries joined by `\n§\n`, no trailing newline, mode 600.
Loader/roundtrip check: `"\n§\n".join([e.strip() for e in raw.split("\n§\n") if e.strip()]) == raw.strip()`.

## Facts
- `add` appends at END. There is no "move" action -> reordering = rewrite the whole file in priority order.
- Limits: memory 4000 / user 2000 chars (config.yaml). The tool checks the limit on the FINAL batch result, so remove+add in ONE batch. It never auto-compacts: a full file rejects the next add.
- Layout rule: TOP = hard rules / never-do / principles; MIDDLE = topic facts (LLMs lose the middle); END = newest facts next to their topic group.

## Procedure
1. Backup first: `cp ~/.hermes/memories/MEMORY.md ~/memory-backup/memories/MEMORY.md.pre-$(date +%Y%m%d-%H%M%S)`.
2. Build the new entry list (write the script to /tmp, keep it < 1.2 KB).
3. Detect lost facts: `set(re.findall(r"[A-Za-z0-9_.~/+-]{6,}", old)) - set(re.findall(..., new))` and restore anything operational (paths, ids, env vars, project names). Case/punct variants are false positives.
4. Write, then print: chars, entries, headroom, roundtrip_ok, perms.
5. Target >= 200 chars headroom so the next add is not rejected. Compress only facts rediscoverable in one command (`ls`, `wrangler pages project list`).
6. Sync: copy both files into ~/memory-backup/memories/, `rtk git add -A && rtk git commit -m ... && rtk git push origin HEAD`.

## Pitfalls
- Long tool-call arguments get truncated in some sessions: a 6 KB script wrote fine, a 1.4 KB one was cut mid-file. Verify the written file before running it; keep scripts small.
- Terminal stdout is often swallowed (reports "1 line output"): redirect to `/tmp/x.txt` then `read_file` it (reliable under ~1.5 KB; read bigger files in chunks with offset/limit).
- Direct file writes are safe when canonical (same `\n§\n` join) - a non-canonical file makes the memory tool flag drift on its next write.
- New entries land on disk immediately but only enter the system prompt next session (frozen snapshot).
