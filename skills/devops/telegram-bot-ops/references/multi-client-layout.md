# Multi-client bot layout (several clients, one host)

From the Aug 2026 session where the operator runs a client-services business (each client gets their own bot, website, docs) and complained about "mixing up, duplicating work, files stored twice".

## Rules

- **Multiple DIFFERENT bots on the SAME machine is fine** — each token is independent; the one-poller-per-token rule is per-token, not per-host. Don't spread client bots across hosts "to keep them separate" — that creates exactly the duplicate-work/409 risk.
- **Per-client folder convention** on the single host:
  ```
  ~/clients/<slug>/
    site/          website source (deploy-ready)
    bot/           bot.py + .env + logs (or <slug>-bot/ at top level)
    docs/          briefs, pricing, scripts, contracts
    assets/        images, logos, media
    deliverables/  finished output for client handoff
    deploy.sh      canonical deploy command for this client
  ```
- **Registry:** `~/ops/CLIENTS.md` — one row per client: slug, bot username, token reference (never the value), site URL, deploy method, status, contact.
- **Naming:** slug = lowercase-hyphen (`sanad`, `luxe-wave`); bot dir `<slug>-bot`; session titles `<slug> — <task> — <YYYY-MM-DD>`; deliverables `<slug>-<artifact>-<date>.<ext>`.
- **Never mix files between client folders.** Each agent session works inside exactly one `~/clients/<slug>/`.

## 409 pre-flight (before starting ANY bot)

1. Confirm the token is not polled elsewhere: `ps aux | grep "[b]ot.py"` on EVERY host that has a copy of the bot.
2. Check the log isn't growing with 409s before restarting (`stat -c%s log`, sleep, re-stat).
3. Only then start. One token = one poller, always.

## Example

- `~/clients/sanad/` → site = sanad-io.netlify.app, bot = @Sanadgulfbot, deploy = netlify-cli from the host only (never the laptop — laptop deploys broke /ar/ pages).
