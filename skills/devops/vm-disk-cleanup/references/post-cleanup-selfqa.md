# Post-cleanup self-QA ("qa urself") — 2026-09-21

Aamir ka "expertly clean ... qa urself" = cleanup + **proof**. Deliverable = reclaim numbers jo
re-run se reproduce ho, plus yeh dikhao ke kuch toota nahi. Artifacts:
`~/ops/kb/infra-cleanup-YYYY-MM-DD.md` (report) + `~/ops/kb/cleanup-YYYYMMDD/` (evidence bundle).

## 1. Evidence bundling (compaction-proof)
Har probe ko file me likho (`/tmp/audit/*.txt`), phir bundle karo:
`mkdir -p ~/ops/kb/cleanup-<date> && cp /tmp/audit/*.txt /tmp/audit/*.py /tmp/audit/*.sh <bundle>/`
Numbers transcript se kabhi quote nahi karo — compaction exact bytes strips kar deta hai.

## 2. Deterministic verifier (`~/ops/verify/cleanup_selfqa_<date>.py`)
Pass/fail self-check jo cleanup ke baad khud chalti hai — 27 checks, grouped:
`df` headroom · per-profile snapshot counts · cache/tmp bounds · failed units = 0 · containers up ·
user-tunnel units active · local service HTTP codes · backup newest-age sane.
Print `N/N checks passed` + per-FAIL line, exit non-zero pe koi fail.

## 3. Threshold design — INVARIANT, absolute size nahi
Sabse mehnga lesson: mera hi `~/.cache < 600MB` check **FAIL** hua next hour, kyunki normal kaam
(mera khud ka `npx wrangler` QA run, uv re-cache) ne cache dobara 709MB kar diya. Woh regression
nahi tha — threshold galat thi. Rules:
- Caches/logs ke liye **bounded** assert karo (`< 1100MB`, `< 1.2G`), post-clean exact value nahi.
- Backups/retention ke liye **structural** assert karo: `per-profile nightly count == N` (parse
  `b.rsplit("-",1)[0]` se basename) — size par nahi, kyunki size har night badalta hai.
- Live-service asserts (units active, HTTP 200) invariant hain — inhe rakho, aur unhe hi release gate banao.
- FAIL mile to pehle poocho "yeh asli regression hai ya meri threshold?", phir fix karo. Threshold bug ko
  regression bata kar user ko alert karna trust ka nuksaan hai.

## 4. Service sweep (kuch toota nahi — proof)
`systemctl list-units --failed` (empty) · `systemctl --user is-active` saare *-tunnel units + timer ·
`docker ps` count (13/13 up) · `curl -o /dev/null -w '%{http_code}'` for each local port that cleanup
touched (8765 infra-dash, 8001 docs) + public sites (priordock.com, Shopify store, live pages.dev).
`daily_selfqa.sh` ka exit code + `ops/verify/claim_integrity.py <report>.md` (CI-01..14) bhi chalao —
report bhi content hai, us pe bhi gate lagta hai.

## 5. Retention change ka sandbox unit-test (template)
```python
import importlib.util, tempfile, glob, os
spec = importlib.util.spec_from_file_location("m", "/home/ubuntu/ops/scripts/state-db-maintenance.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)   # __main__ guard ke bina
d = tempfile.mkdtemp(); os.makedirs(f"{d}/default"); m.NIGHTLY, m.BACKUP_ROOT = f"{d}/nightly", d
for tag in ("20260918","20260919","20260920","20260921","20260922"): open(f"{d}/nightly/state.db-default-{tag}.db","w").close()
m.prune()   # do baar chalao — idempotent hona chahiye
assert sorted(os.listdir(f"{d}/nightly")) == [f"state.db-default-2026092{i}.db" for i in (0,1,2)]
```
Same pattern kisi bhi `KEEP_*`/rotation function pe — module import + tmpdir monkeypatch, real data pe
kabhi destructive test nahi.

## 6. Write-time pitfalls (is harness me)
Bade `write_file`/`patch` silently truncate ho jate hain (session me 2 baar) → scripts **chhote
chunks** me likho aur turant `wc -c`/read-back se verify karo. Long shell commands ka output bhi
elide hota hai ("1 lines output") → hamesha file me redirect + `read_file`.
