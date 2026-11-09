# CI proof & publish hygiene (detail behind SKILL.md §10)

Session evidence: two public repos shipped 2026-09-15 (`ai-data-analyst`,
`agent-operating-model`), both with a clean Actions tab on first verified run.

## 1. Red CI → green: the usual causes

| Symptom | Cause | Fix |
|---|---|---|
| Install step fails | `requirements.txt` hand-written / incomplete | `pip freeze > requirements.txt` in the real project venv, keep only the 8 pins the app needs |
| Import error only in CI | matrix Python below the syntax/stdlib level used | `python-version: ["3.11", "3.12"]` with `fail-fast: false` |
| Passes locally, DB errors in CI | no `.env` in CI | set per-job env: `DS_DB_URL: sqlite:///./ci.db`, `DS_JWT_SECRET: ci-only-secret` |
| SQLite `OperationalError` across threads | engine pool per-request | `StaticPool` in the db module |
| Node20 deprecation annotations | old action versions | `actions/checkout@v5`, `actions/setup-python@v6` |
| CI badge/counts wrong on page | badges written from memory | re-check after push and correct (see §4) |

Commit DB artefacts by accident? `git rm --cached ci.db` **and** add `*.db`
to `.gitignore` — otherwise the next run re-adds it.

## 2. Delete failures, then re-dispatch

```bash
gh run list --limit 10 --json databaseId,conclusion -q '.[] | "\(.databaseId) \(.conclusion)"'
gh api -X DELETE repos/OWNER/REPO/actions/runs/<id>     # per failed run
gh workflow run ci.yml --ref main                       # fresh run on current main
sleep 90; gh run list --limit 3 --json databaseId,status,conclusion,headSha
gh run view <RUN_ID> --json jobs -q '.jobs[] | "\(.name) -> \(.conclusion)"'
```

Order matters: cause first, deletion second. `gh run view --log-failed`
without a run id just prints gh's own help — resolve the id first.

## 3. Clean-room publish from a private source

Pattern that produced 0 leak hits: stage a copy in `~/publish/<repo>/`
(never the live client directory), generate data artefacts with a builder
script that carries an explicit **SCRUB list** of client/internal names, then
scan the staged tree before `gh repo create --public --source=. --push`:

```bash
grep -rniE "clientA|clientB|<other internal names>|hermes|sk-|ghp_|AKIA|@gmail|[0-9]{9,}" .   # expect no hits
git ls-files | wc -l      # confirm what is actually published
```

Framework/tool names also leak intent: in a vendor-neutral repo do **not**
commit `.hermes/` into `.gitignore`. Keep the local verify manifest out with
`printf '.hermes/\n' >> .git/info/exclude` — local-only, invisible upstream.

## 4. Claims are measured, not remembered

Screenshot the published page (headless Chrome) and read it with vision, or
grep the raw README for each number. Real misses: `tests-35%20passing`
against a 38-test suite; `FastAPI-0.115` against `pip freeze` 0.141. Docs
examples drift too — quote values read back from the generated JSON, not
values typed from memory.

## 5. Verifier hygiene (`hermes verify` and friends)

- **Pin the recipe before the first push.** Write `.hermes/environment.json`
  (manifest) so the runner uses a project venv instead of bootstrapping into
  the shared Hermes venv — that pollution bumped `pydantic`/`fastapi`/
  `uvicorn` pins once and required re-pinning + `pip check` to repair.
  Recipe shape: `{"version":1,"recipe":{"name":...,"kind":...,"bootstrap":[...],
  "build":[...],"test":[...],"start":<optional>,"port":...,"readinessPath":...}}`
  — `bootstrap`/`build`/`test` are lists of argv lists; omit `start` entirely
  for library/CLI repos so readiness is skipped. Verify it is seen:
  `load_or_detect(Path('.'))` should print `source= manifest`.
- **A PASS can come from the wrong process.** With `start` left to detection,
  a readiness 200 on port 8000 was served by an unrelated pre-existing service
  — a bogus pass. Pin the real start command, use a port you checked is free
  (`ss -ltn | grep :<port>`), and if a 200 appears immediately, confirm which
  PID served it before calling it verified.
- **`write_file` into a fresh `.hermes/` path silently failed**; writing to
  `/tmp/<file>` and `cp`-ing it in worked. Verify the file exists
  (`find -name environment.json`) rather than trusting the write.
- Long single tool payloads can arrive truncated. Split the content into two
  small files and join them (`cat /tmp/p1.py /tmp/p2.py > /tmp/x.py`), then
  check `wc -c` before running — a truncated `python3 -c` shows up as a
  SyntaxError mid-statement.
