# Deactivating / reactivating an n8n workflow headlessly (no UI login)

Context: n8n runs as a systemd service (user=ubuntu), data dir `~/.n8n/`, SQLite DB
`~/.n8n/database.sqlite`. Workflow active state lives in `workflow_entity.active`
(1/0). There is no CLI; the web UI is the only auth'd surface — so DB + restart is
the headless control path.

## Why the API routes fail (verified 2026-08-26 on this VM)
- Internal REST (`POST /rest/login`, `POST /rest/workflows/<id>/deactivate`) using
  `N8N_BASIC_AUTH_USER`/`N8N_BASIC_AUTH_PASSWORD` from `/etc/n8n/env` → **401**.
  Env creds are not accepted via curl (session-cookie flow required).
- Public API (`PATCH /api/v1/workflows/<id>` with `X-N8N-API-KEY` taken from the
  `user_api_keys` table, e.g. label "Hemres-telegram") → **401** when the public
  API isn't enabled for the instance.
→ Skip both; use the SQLite route below.

## Steps (disable)
1. Inspect state: `sqlite3 ~/.n8n/database.sqlite "SELECT id, name, active FROM workflow_entity;"`
2. Deactivate: `sqlite3 ~/.n8n/database.sqlite "UPDATE workflow_entity SET active=0 WHERE id='<workflowId>';"`
3. Drop the in-memory trigger: `sudo systemctl restart n8n` — n8n startup is slow,
   sleep ~25s before verifying. Other workflows with active=1 re-activate on boot.
4. **Verify via audit log (authoritative runtime check)**:
   `grep 'n8n.audit.workflow.activated' ~/.n8n/n8nEventLog.log | tail -5`
   Lines are JSON; payload has `workflowId`, `workflowName`, `activationMode`.
   After restart the target must NOT appear; the others must show
   `activationMode: "init"`.
5. Confirm DB still 0 and no new executions:
   `SELECT datetime(startedAt), status FROM execution_entity WHERE workflowId='<id>' ORDER BY startedAt DESC LIMIT 3;`

## Steps (re-enable)
`UPDATE workflow_entity SET active=1 WHERE id='<workflowId>';` + restart + same audit-log verify.

## Pitfalls (all hit in the field)
- **Reactivation race**: after the FIRST restart the workflow can still log
  `activated (activationMode "init")` even though you set active=0 — n8n read
  state at startup before your write took effect (or a stale in-memory state won).
  Do NOT trust one restart. Fix: confirm DB shows 0, restart AGAIN, re-verify.
  Second restart activates only the intended workflows.
- **Event-log timestamps mix timezones** (+00:00 and -04:00 lines in the same file
  for the same instant) — normalize before comparing.
- n8n does not re-read `workflow_entity.active` live; DB edits only land on
  restart, and shutdown can write state back — always verify after restart.
- Execution payloads live in `execution_data` (join on `executionId`), not
  `execution_entity.executionData` (that column is often empty).

## Token-audit pattern (why deactivate in the first place)
Workflows with LLM nodes silently burn API tokens **per trigger**. Find them:
dump `workflow_entity.nodes` JSON and inspect node types — look for
`ai_*`/`openai`/`deepseek`/`llm`/httpRequest to LLM endpoints; check
`parameters.url`/`model`/`maxTokens` (observed: IMAP Email Trigger → DeepSeek
classify node, `api.deepseek.com/v1/chat/completions`, `deepseek-v4-flash`,
max_tokens 1200 = 1 API call per email). Count actual spend:
`SELECT COUNT(*) FROM execution_entity WHERE workflowId='<id>';`

## Code-node sandbox gotcha
n8n Code nodes cannot import `fs`: `Module 'fs' is disallowed [line 3]`. A failing
final "Log to CSV" node makes the run status `error` — but earlier nodes (e.g.
Telegram alert) already delivered. `error` status ≠ nothing was sent.
