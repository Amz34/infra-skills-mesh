---
name: latex-overleaf-mcp
description: Use when authoring/compiling LaTeX PDFs or syncing Overleaf.
version: 1.0.0
author: Hermes (default profile)
license: MIT
metadata:
  hermes:
    tags: [latex, overleaf, pdf, mcp, documents]
    related_skills: [mcp-tool-servers, pdf, html-to-pdf-ebook-production]
---

# LaTeX / Overleaf MCP (`tex_*` tools)

## When to Use
- A deliverable must be a properly typeset PDF: report, proposal, paper, letter, bilingual EN/AR.
- The user mentions Overleaf, LaTeX, `.tex`, latexmk, or wants source-controlled documents.
- An agent must compile, inspect an outline, or read a built PDF's page count.
- Not for HTML → PDF cards/posters (use `chrome-print-pdf-production` / the `pdf` skill).

Connector that gives every agent on this VM real document capability: **TeX Live compile** +
**Overleaf git bridge** + project scaffolding, exposed as 12 MCP tools. Use whenever the job is
"make a properly typeset PDF" (report, paper, proposal, bilingual EN/AR doc) or "sync with an
Overleaf project".

- Code: `~/latex-connector` (client + `mcp_server.py` + `tests/verify_tex.py` + README)
- Workspace: `~/tex-projects/<project>/` (each project = `main.tex`, `notes.md`, `build/`)
- Config: `~/.config/latex-connector/config.json` (0600) · token: `overleaf.token` (0600)
- Service: `latex-mcp.service` (systemd --user, streamable HTTP on `127.0.0.1:8795/mcp`)
- Hermes entry: `mcp_servers.latex.url = http://127.0.0.1:8795/mcp`

## Tools

`tex_health` → always first. Then `tex_project_list`, `tex_file_list`, `tex_file_read`,
`tex_structure`, `tex_pdf_info` (reads); `tex_new_project`, `tex_file_write` (writes, gated);
`tex_compile` (latexmk, pdflatex default / xelatex for Arabic); `tex_overleaf_status`,
`tex_overleaf_link`, `tex_overleaf_sync` (bridge).

## Gates (never bypass)

| gate | default | meaning |
|---|---|---|
| `TEX_WRITE_ENABLED` | 1 in the service | scaffold / file writes inside `~/tex-projects` |
| `TEX_PUSH_ENABLED` | **0** | `tex_overleaf_sync(direction="push")` stays refused until the owner turns it on |
| `dry_run` args | `true` for writes | first call returns the planned change, second call applies |

`tex_file_write(dry_run=False)` refuses every path outside the project dir (traversal guard), and
`redact()` strips the Overleaf token from all git output — including remote URLs.

## Workflow

1. `tex_health` → confirm `latex_ready`, workspace, gates.
2. `tex_new_project(name, template="article|report|letter|arabic")`.
3. `tex_file_write(project, "main.tex", content, dry_run=True)` → inspect delta → repeat with
   `dry_run=False`.
4. `tex_compile(project)` → check `ok`, `errors[]`, `pdf.pages`; `tex_structure` for the outline.
5. Delivery: `tex_pdf_info` for the page count, then hand over the PDF path (or copy into
   `~/ops/artifacts/`). Charts/diagrams: generate SVG/PNG first and `\includegraphics` it.

## Overleaf live sync (one user step)

1. Overleaf → Account Settings → Git Integration → Create Token →
   `printf '%s' 'olp_xxx' > ~/.config/latex-connector/overleaf.token && chmod 600` it, restart
   the service.
2. `tex_overleaf_link(project="paper-one", project_id="<id from the Overleaf URL>")`.
3. `tex_overleaf_status` → `probe.ok=true`; then `tex_overleaf_sync(project, "pull")`, and `"push"`
   only with `TEX_PUSH_ENABLED=1`.
   Self-hosted Overleaf / any git remote: set `TEX_OVERLEAF_REMOTE` (bridge is plain git).

## Verification / health

```bash
~/latex-connector/.venv/bin/python ~/latex-connector/tests/verify_tex.py   # 27/27, exit 0 = pass
~/latex-connector/.venv/bin/python ~/latex-connector/tests/probe_http.py --scaffold   # live service
systemctl --user status latex-mcp.service
```

## Pitfalls (learned)

- **polyglossia Arabic env is `\begin{Arabic}`** (capitalised). `\begin{arabic}` expands LaTeX's
  `\arabic` counter formatter → `Missing number, treated as zero` + weird `\c@ه` error.
  Bilingual docs must compile with `xelatex`; Amiri is installed as a system font.
- `pdfinfo` returns `Pages` as a **string** — cast before numeric comparisons.
- First compile of a fresh project takes a few seconds (fmt files); `-halt-on-error` off so the
  harness can parse real errors; broken docs must return `ok=False` with parsed `errors[]`, never
  an exception.
- Harness must run with an **isolated `TEX_WORKSPACE` + `TEX_CONFIG_FILE`** so the live workspace
  and live config are never touched, and it must test the push refusal *before* enabling pushes.
- Push/pull verify against a local **bare-repo mock** (`git init --bare`), then read the bare
  repo's log to prove the commit landed — that is the real proof, not the tool's own `ok`.
- Service env comes from the unit file, not the shell: after editing the unit or the config file,
  `systemctl --user restart latex-mcp.service` and re-probe.
