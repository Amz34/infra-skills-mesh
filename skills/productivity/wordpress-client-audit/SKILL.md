---
name: wordpress-client-audit
description: Use when auditing/fixing client WordPress sites.
---

# WordPress Client Audit & Fix (REST API)

Kisi bhi WordPress site pe (client ho ya demo) — REST API + Application Password se audit, report, fix pipeline. Asli selling point: **outdated plugin/theme = security risk** findings.

## Tools
- `/home/ubuntu/sanad-site/wp-tools/wp-audit.py` — generic audit/fix CLI (works on ANY WP site)
- Demo sandbox: `http://localhost:8080` (docker compose in `/home/ubuntu/wp-sandbox/`, creds in `wp-tools/.env`)

## Quick start (client site)
```bash
cd /home/ubuntu/sanad-site/wp-tools
python3 wp-audit.py scan --url https://CLIENT-SITE --user CLIENT-ADMIN --pass "APP-PASSWORD" --md /tmp/report.md
python3 wp-audit.py fix-update-plugins --url https://CLIENT-SITE --user ... --pass "..."
python3 wp-audit.py fix-deactivate --url ... --plugin plugin-slug
```

## Client onboarding steps (Security Audit service)
1. Client se: site URL + admin user **Application Password** (wp-admin → Users → Profile → Application Passwords → Add New). Kabhi real password nahi — app password hi use karo.
2. `scan` → JSON + Markdown report
3. High issues (outdated plugins) → `fix-update-plugins`
4. Inactive plugins/themes → client ko cleanup recommend karo (fix-deactivate)
5. Security headers missing → `.htaccess` fix (production me Cloudflare/nginx pe headers bhi add kar sakte ho)

## REST API gotchas
- **Application Passwords HTTPS-only by default** — localhost HTTP pe mu-plugin chahiye (sandbox me: `wp-content/mu-plugins/allow-http-auth.php` with `wp_is_application_passwords_available` filter). Production HTTPS pe bina filter ke chalega.
- **Plugin `update` field** REST response me tab tak nahi aata jab tak site update transient fresh na ho (admin visit/cron). Script wordpress.org API se cross-check karta hai — bina auth, robust.
- **Pretty permalinks zaroori** — REST `/wp-json/` 404 aaye toh `wp rewrite structure "/%postname%/" --hard` + flush. Without it REST root itself fails.
- **Themes endpoint** me `theme` field nahi — `stylesheet` field use karo.
- **Users roles** sirf `?context=edit` se aate hain (admin detect ke liye).
- **HSTS** sirf HTTPS pe valid — HTTP site pe false positive na dikhao.
- Docker sandbox me `.htaccess` kaam nahi karta jab tak `AllowOverride All` + `a2enmod headers` na ho.
- **WP-CLI root warning**: container me `php wp-cli.phar --allow-root` chahiye.

## Content ops (client blog/updates)
```bash
curl -s -u "USER:APP-PASS" -X POST https://SITE/wp-json/wp/v2/posts \
  -H "Content-Type: application/json" \
  -d '{"title":"...","status":"draft","content":"<p>...</p>"}'
```

## Sandbox lifecycle
- Start: `cd /home/ubuntu/wp-sandbox && docker compose up -d`
- WP-CLI: `docker exec wp-sandbox bash -c 'cd /var/www/html && php wp-cli.phar --allow-root <cmd>'`
- Creds: `sanadadmin` / app-password in `.env` (demo only, never commit)
