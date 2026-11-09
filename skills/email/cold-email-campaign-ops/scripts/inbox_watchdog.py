#!/usr/bin/env python3
"""Campaign inbox watchdog for cron (no_agent).

Prints NOTHING when no new replies (empty stdout = silent tick, no delivery)
and a digest when replies/enquiries arrive (delivered verbatim to the chat).
A marker file rolls the IMAP SINCE window forward so old mail never repeats.

Cron setup: no_agent=True, schedule 'every 6h', script referenced by FILENAME
ONLY (must live in ~/.hermes/scripts/). Empty stdout = silent; non-empty
stdout = delivered as-is. Test manually once before scheduling.
"""
import imaplib
import os
import re
import sys
from datetime import date, timedelta

# ---- CONFIGURE PER CAMPAIGN ----
CAMPAIGN = "Invertio FM"
# From-domains of wave recipients whose replies matter (lowercase)
RECIPIENT_DOMAINS = [
    "musanadah.com.sa", "efsim.sa", "esom.com.sa", "el-seif.com.sa", "emcan.sa",
]
MARKER = os.path.expanduser("~/.hermes/cron/output/.inbox_watch_marker")
ENV_FILE = os.path.expanduser("~/.hermes/.env")
# ---- END CONFIG ----


def load_env():
    env = {}
    try:
        for line in open(ENV_FILE):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return env


def main():
    env = load_env()
    user, pwd = env.get("GMAIL_USER", ""), env.get("GMAIL_APP_PASSWORD", "")
    if not (user and pwd):
        print(f"[{CAMPAIGN}] watchdog: GMAIL_USER/GMAIL_APP_PASSWORD missing in .env")
        return 1
    try:
        since = open(MARKER).read().strip()
    except OSError:
        since = ""
    if not since:
        since = (date.today() - timedelta(days=1)).isoformat()
    rows = []
    try:
        m = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        m.login(user, pwd)
        m.select("INBOX")
        _, data = m.search(None, f'(SINCE {since.replace("-", "")})')
        for num in data[0].split():
            _, d = m.fetch(num, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            head = d[0][1].decode("utf-8", "ignore")
            frm = re.search(r"From:.*?<([^>]+)>", head, re.S)
            subj = re.search(r"Subject: (.*)", head, re.S)
            dt = re.search(r"Date: (.*)", head, re.S)
            addr = (frm.group(1).strip() if frm else "?")
            sender_dom = addr.split("@")[-1].lower() if "@" in addr else ""
            subj_txt = (subj.group(1).strip() if subj else "")
            is_reply = subj_txt.lower().startswith("re:")
            if sender_dom in RECIPIENT_DOMAINS or (is_reply and frm and not addr.lower().startswith(user)):
                rows.append(
                    f"{dt.group(1).strip() if dt else '?'} | {addr} | {subj_txt[:120]}"
                )
        m.logout()
    except Exception as e:  # noqa: BLE001 — watchdog must alert on failure
        print(f"[{CAMPAIGN}] watchdog error: {e}")
        return 1
    with open(MARKER, "w") as f:
        f.write(date.today().isoformat())
    if rows:
        print(f"📬 {CAMPAIGN} — NEW REPLY/ENQUIRY ({len(rows)}):")
        print("\n".join(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
