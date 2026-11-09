---
name: link-safety-triage
description: "Use when judging a suspicious link or domain."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [security, phishing, scam, url, domain-age, rdap, urlscan, hibp, whatsapp]
---

# Link / Domain Safety Triage (key-less-first)

## When to Use

- a client, family member or user forwards a link: "ye safe hai?" / "is it a scam?"
- WhatsApp/SMS phishing, fake courier, fake bank (KSA/India patterns)
- an unknown shortener, a domain that looks like a brand, a "verify your account" page
- before ANY agent/bot opens a URL supplied by an untrusted party

## Tool

`~/ops/scripts/link_safety.py <url|domain> [...]` — one verdict block per target.
Never open a suspicious URL in a browser; the script only does metadata HEAD/GET on
public JSON APIs.

```bash
python3 ~/ops/scripts/link_safety.py "https://alrajhi-bank-verify.tk/login"
python3 ~/ops/scripts/link_safety.py https://bit.ly/xxxx --json
python3 ~/ops/scripts/link_safety.py suspicious.com legit.com    # batch
```

## Signals (descending evidential weight)

| Signal | Source | Key-less? |
|---|---|---|
| Domain registration age (days since created) | RDAP `rdap.org/domain/<d>` | yes |
| Existing scan verdicts / IP history | urlscan.io `api/v1/search/?q=domain:` | yes |
| Domain in known breach catalogues | HIBP `api/v3/breaches` (1.1 MB, cached daily) | yes |
| Full redirect chain + real final host | curl `-sIL --max-redirs` | yes |
| Homoglyph / punycode / brand-lookalike (paypa1, arnazon, xn--) | local heuristics | yes |
| Suspicious TLD, URL shortener, no-TLS login form | local heuristics | yes |
| File / URL malware verdict | VirusTotal v3 (`VT_API_KEY`) | **key required → skipped when absent** |

Verdict bands: `LIKELY MALICIOUS` / `SUSPICIOUS` / `UNKNOWN` / `LIKELY SAFE`, each with
its reasons list. Domain age under 90 days is the strongest cheap signal.

## Workflow

1. Get the **real** link — shorteners/t.co are expanded by the script's redirect chain,
   don't ask the user to click anything.
2. Run the script. `UNKNOWN` is an honest answer: say "no public evidence either way",
   never "safe".
3. Read the reasons: brand keyword in a non-brand domain + young domain + no archive
   snapshot = the classic phishing triad.
4. Report as: verdict + 2–3 concrete reasons + the safe action ("do not enter
   credentials; open the bank app directly instead").
5. Real incident: advise password change + 2FA + reporting. Never collect the victim's
   credentials yourself.

## Pitfalls

- Public WHOIS is gated/rate-limited from cloud IPs → **use RDAP** (`rdap.org`,
  `rdap.verisign.com`) and follow the redirect (`curl -L`) or the body comes back empty.
- The HIBP **breaches** endpoint is key-less; the *account* endpoints
  (`/breachedaccount/<email>`) need a paid key — never promise an email-leak check
  from a key-less setup.
- VirusTotal free tier is 4 req/min and needs a free key: keep it optional so the script
  still works with `VT_API_KEY` unset (it reports the skip explicitly).
- Google Safe Browsing needs a key too — absence of a hit is NOT a green light.
- Homoglyph heuristics false-positive on long legit domains — verdicts are advisory;
  never auto-block client traffic on them.
- A `.com` clone can also be a parked/scam domain: domain age beats spelling.

## Verification

- Script exits 0 and prints one block per target; `--json` for machine use.
- Cache: `~/.cache/link_safety/breaches.json` (daily) — delete to force refresh.
- Cross-check any `LIKELY MALICIOUS` verdict against a second source (the urlscan report
  URL, or VT when a key exists) before telling a client it is malware.

## Related

- `devops/secrets-vault-ops` — where a VT key belongs if the user adds one.
- `research/blocked-page-recovery` — when a legit page is blocked by a WAF.
