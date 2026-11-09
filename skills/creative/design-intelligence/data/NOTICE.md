# Third-party data notice

The CSV/JSON catalogs in this `data/` directory (styles, colors, products, typography,
ux-guidelines, app-interface, motion, charts, icons, landing, stacks/*) are derived from:

- **Project:** `nextlevelbuilder/ui-ux-pro-max-skill`
- **Upstream path:** `.claude/skills/ui-ux-pro-max/data/`
- **License:** MIT (Copyright (c) 2025 nextlevelbuilder)
- **Retrieved:** 2026-10-05
- **Vendored here:** core design catalogs only. Upstream's bulk font DB
  (`google-fonts.csv`, 747 KB), `phosphor-icons-upstream.json` (824 KB) and
  `google-font-licenses.json` (433 KB) were deliberately **not** vendored.

MIT permits reuse and redistribution with attribution; this notice satisfies that.

Not vendored from upstream, and **not** covered by the MIT grant above:

- `scripts/ds.py` — written for Hermes (stdlib only, no network, no install bootstrap).
- `SKILL.md` — the workflow, command surface and brand gates are ours.

Upstream's `core.py`, `design_system.py`, `search.py`, `reasoning_contract.py` were **not** copied.
