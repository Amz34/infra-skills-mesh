# Permanent campaign log in Notion — working `ntn` recipe

Validated 2026-09-07 on the Open Anatomy campaign (Rounds 1+2, 13 emails). The
`notion` hub skill's documented markdown-PATCH syntax FAILED in practice; this
file carries the shapes that actually worked.

## Setup

```bash
export NOTION_API_TOKEN=$(cat ~/.config/notion/token); export NOTION_KEYRING=0
# ntn CLI: /home/ubuntu/.local/bin/ntn — `ntn api --help` documents `-d @PATH`
```

Hierarchy used:
- Parent page **AZ Master Leads**: `3d06012e-e39a-81f8-96df-d1bf25faf8b5` (holds the "Website Leads" DB)
- Campaign child page: **"Open Anatomy — Lead Gen & Monetization (Permanent Log)"** `3d46012e-e39a-8181-b5de-c2128d5ba4d6`

## 1. Create a child page from markdown

POST `/v1/pages` with a `markdown` body param works (build the JSON with python,
never inline heredoc quoting):

```python
import json
md = open('/tmp/oa-round2-log.md').read()
body = {"parent": {"page_id": "3d06012e-e39a-81f8-96df-d1bf25faf8b5"},
        "title": "Open Anatomy — Lead Gen & Monetization (Permanent Log)",
        "markdown": md}
open('/tmp/ntn_create.json', 'w').write(json.dumps(body))
```

```bash
ntn api v1/pages -X POST -d @/tmp/ntn_create.json
```

Verify read-back immediately:
```bash
ntn api v1/pages/<new_page_id>/markdown | head -40
```

## 2. PATCH the page when the log advances

### What FAILS (do not retry)
- `curl -X PATCH -d '{"markdown": "..."}'` → 400 `body.type should be defined, instead was undefined`
- `{"type":"replace_content","new_str": "..."}` → 400 (new_str must nest under `replace_content`)
- `ntn api v1/pages/<id>/markdown -X PATCH markdown="$(cat /tmp/log.md)"` → multi-line inline arg parse failure

### What WORKS — full replace of page markdown

```python
import json
md = open('/tmp/oa-round2-log.md').read()
body = {"type": "replace_content",
        "replace_content": {"new_str": md}}
open('/tmp/ntn_body.json', 'w').write(json.dumps(body))
```

```bash
ntn api v1/pages/3d46012e-e39a-8181-b5de-c2128d5ba4d6/markdown -X PATCH -d @/tmp/ntn_body.json
```

### Verify the PATCH (required — a 0 exit is not proof)

```bash
ntn api v1/pages/3d46012e-e39a-8181-b5de-c2128d5ba4d6/markdown | grep -c "ROUND 2 — SENT"
```

Grep for content markers. Do NOT compare character counts against the local
source — Notion's markdown renderer inflates them (~6,054 source chars read
back as ~8,152) via link normalization.

## Pitfalls

- Inline multi-line arguments to `ntn api` never parse — ALWAYS `json.dumps` to
  a temp file and use `-d @/tmp/body.json`.
- The top-level `type` field is mandatory and must name a valid content op;
  `replace_content` with nested `replace_content.new_str` is the full-replace form.
- Read-back verification is the only trustworthy success signal for PATCH.
- Keep the local markdown master updated FIRST (source of truth), then mirror;
  never hand-edit the remote page.
