# Client Security Audit & Monitoring Services

Use when Aamir asks about offering cybersecurity to clients (e.g. after seeing
a training institute like Abadnet) or says "security audit karo" for a client
site. POSITIONING: cyber TRAINING courses (CompTIA etc.) are out of scope —
needs certified trainers + LMS + credibility. SELL SERVICES instead: audit,
monitoring, hardening. These reuse the existing stack (VM + Hermes cron +
Telegram + Cloudflare) — ~70% ready before any setup.

## The 3 packages (pitch table)

| Pkg | What | Price | Effort |
|---|---|---|---|
| A — Security Audit (one-time) | SSL/TLS check, security headers, malware/blacklist, outdated plugins, open ports → PDF report + fixes | $150–300 | 2–4 hrs |
| B — Security Monitoring (retainer) | 24/7 uptime + SSL expiry (30/14/7d alerts) + defacement change-detection → Telegram alerts + weekly summary | $25–50/mo | 1–2 hrs setup, then automatic = recurring income |
| C — Hardening (one-time) | Cloudflare WAF/DDoS, security headers + CSP, backup automation, 2FA/honeypot | $200–400 | 3–5 hrs |

Demo play: run the mini-audit on an EXISTING client site, show 2–3 REAL
findings ("SSL thik hai, lekin 3 security headers missing hain — 15 min
fix") — the finding IS the pitch. Never fabricate findings.

## Tool install (VM, all free)

```bash
sudo apt-get install -y nmap nikto sqlmap whatweb masscan

# nuclei — ARM64 VM pitfall, see below
VER=$(curl -s https://api.github.com/repos/projectdiscovery/nuclei/releases/latest | grep -oP '"tag_name":\s*"\K[^"]+')
ARCH=$(uname -m | sed 's/aarch64/arm64/; s/x86_64/amd64/')   # MUST map arch
curl -sL "https://github.com/projectdiscovery/nuclei/releases/download/${VER}/nuclei_${VER#v}_linux_${ARCH}.zip" -o nuclei.zip
unzip -oq nuclei.zip && sudo mv nuclei /usr/local/bin/

# testssl.sh (deep TLS audit: heartbleed, weak ciphers)
sudo git clone -q --depth 1 https://github.com/drwetter/testssl.sh.git /opt/testssl.sh
sudo chmod +x /opt/testssl.sh/testssl.sh
```

## Mini-audit smoke test (5 min, read-only)

```bash
whatweb -q --no-errors <site>                     # tech fingerprint
nmap -T4 -F --host-timeout 30s <site>             # top ports
echo | timeout 15 openssl s_client -connect <site>:443 -servername <site> 2>/dev/null \
  | openssl x509 -noout -dates -issuer            # cert validity + issuer (expiry!)
curl -sI https://<site>/ | grep -iE "strict-transport|content-security|x-frame|x-content-type|server:"
```

## Reading results

- Cloudflare-proxied sites show ports 80/443 + 8080/8443 open — that is the
  CF proxy, NOT a server exposure. Don't report it as a finding.
- Missing HSTS / CSP / X-Frame-Options = the classic "3 security headers
  missing" finding (AVVS Triatek live example, 2026-08 — behind CF WAF, low
  severity, but a real report item).
- Cert `notAfter` = the SSL expiry date that feeds the Package B monitoring
  alert.
- `server: cloudflare` + `x-content-type-options: nosniff` = CF + decent baseline.

## Package C: the hardening fix (approved recipe — AVVS 2026-08)

When the user says "Haa fix karde" after a report, implement via Cloudflare
Pages `_headers` file (no dashboard rules needed — file in the deploy root):

```text
/*
  Strict-Transport-Security: max-age=31536000; includeSubDomains
  X-Frame-Options: SAMEORIGIN
  Permissions-Policy: geolocation=(), microphone=(), camera=()
  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'
```

CSP gotchas learned the hard way:
- Sites with inline `<script>` (analytics tracker) and inline `style=` attrs
  NEED `'unsafe-inline'` in script-src/style-src or the page breaks — check
  before writing CSP: `grep -rhoE "(src|href)=['\"](https?://[^/'\"]+)" *.html`
  for external origins, and confirm forms submit via JS fetch (same-origin →
  `connect-src 'self'` covers it). wa.me/t.me links are anchor navigation,
  NOT blocked by CSP — don't over-restrict.
- `frame-ancestors 'self'` in CSP + X-Frame-Options both = belt and braces.

Flow: write `_headers` → `npx wrangler pages deploy . --commit-dirty=true` →
`sleep 6` → `curl -sI https://site/ | grep -iE "strict-transport|x-frame|permissions-policy|content-security"` →
functional check (page renders, `/api/t` analytics still 200, images load) →
git add/commit/push → render updated report with findings "Resolved" +
score bump (86→96) → deliver BOTH reports (before/after) to the client:
"audit → fix same day → verified" is the full-cycle pitch, Package C
deliverable.

## Pitfalls

- **ARM64 VM (Oracle Free tier):** `uname -m` returns `aarch64`. Downloading
  `_linux_amd64.zip` yields "cannot execute binary file: Exec format error".
  Always derive ARCH from `uname -m` (aarch64→arm64, x86_64→amd64).
- **testssl.sh `--version` trips the Hermes gateway guard** (its script text
  matches the "restart/stop the gateway" scanner). Verify presence with
  `test -x /opt/testssl.sh/testssl.sh` — do NOT execute the script just to
  check it installed.
- Nuclei first run may print `[ERR] GOOGLE_API_KEY env variable exists but
  GOOGLE_API_CX does not` — harmless (a template module needs both); ignore.
- Scan only sites Aamir owns or clients approved — no mass scanning of third
  parties.
