#!/usr/bin/env python3
"""Minimal Telegram Bot API client for this fleet — token from a FILE, never argv.

Why this exists: the tricky BotFather calls (a JSON-object `photo` field alongside a multipart
file) and the token-hygiene rule are both easy to get wrong from a one-off heredoc.
The API call SHAPES here are the ones verified on @KsaAzConsults_Bot (2026-09-21); the wrapper
is a cleanup of that throwaway client.

Token sources (both accepted, never printed, never in argv):
    --token-file ~/.hermes/profiles/<p>/.env   # finds TELEGRAM_BOT_TOKEN=<id>:<secret>
    --token-file /tmp/.bottok                  # bare token in one line (chmod 600)

Usage:
    tg_bot_api.py --token-file F getMe
    tg_bot_api.py --token-file F metadata                 # name/short/desc/commands summary
    tg_bot_api.py --token-file F setName  --text "AZ Consultants KSA"
    tg_bot_api.py --token-file F setShort --text "KSA advisory desk"
    tg_bot_api.py --token-file F setDesc  --text-file desc.txt
    tg_bot_api.py --token-file F setCommands --json-file commands.json
    tg_bot_api.py --token-file F setPhoto --file avatar.png      # attach://avatar form
    tg_bot_api.py --token-file F getPhotos --download /tmp/readback.png
    tg_bot_api.py --token-file F getWebhookInfo
    tg_bot_api.py --token-file F call getChat --json '{"chat_id": 8843884232}'

Requires: requests  (pip install requests)
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import socket
import sys
import time

API = "https://api.telegram.org"
TOKEN_RE = r"([0-9]{5,}:[A-Za-z0-9_\-]{25,})"


def prefer_ipv4() -> None:
    """Prefer A records: this fleet's VM has an intermittent IPv6 route to api.telegram.org
    (Errno 101/115) while IPv4 is reliable. Harmless elsewhere."""
    orig = socket.getaddrinfo

    def gai(host, port, family=0, type=0, proto=0, flags=0):
        if family in (0, socket.AF_UNSPEC, socket.AF_INET):
            try:
                res = orig(host, port, socket.AF_INET, type, proto, flags)
                if res:
                    return res
            except OSError:
                pass
        return orig(host, port, family, type, proto, flags)

    socket.getaddrinfo = gai


def read_token(path: str) -> str:
    if not os.path.isfile(path):
        sys.exit(f"token file not found: {path}")
    txt = open(path).read()
    m = re.search(r"^\s*TELEGRAM_BOT_TOKEN\s*=\s*[\"']?" + TOKEN_RE, txt, re.M)
    if m:
        return m.group(1)
    m = re.search(r"^\s*[\"']?" + TOKEN_RE + r"[\"']?\s*$", txt, re.M)
    if m:
        return m.group(1)
    sys.exit(f"no bot token found in {path} (expected TELEGRAM_BOT_TOKEN=<id>:<secret>)")


def call(token: str, method: str, data=None, file_field=None, file_path=None) -> dict:
    """POST one method. Never prints the URL (a requests exception would embed the token)."""
    import requests

    url = f"{API}/bot{token}/{method}"
    payload = {k: v for k, v in (data or {}).items() if v is not None}
    last = ""
    for attempt in range(3):
        opened = None
        files = None
        try:
            if file_field:
                opened = open(file_path, "rb")
                mime = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
                files = {file_field: (os.path.basename(file_path), opened, mime)}
            return requests.post(url, data=payload, files=files, timeout=60).json()
        except Exception as exc:  # noqa: BLE001
            last = type(exc).__name__          # deliberately NOT str(exc): it contains the URL
            time.sleep(1.5 * (attempt + 1))
        finally:
            if opened:
                opened.close()
    sys.exit(f"{method}: network error after 3 attempts ({last})")


def show(res: dict, method: str) -> dict:
    if not res.get("ok"):
        print(f"{method}: FAILED code={res.get('error_code')} desc={res.get('description')!r}")
        sys.exit(2)
    return res.get("result", {})


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("command")
    p.add_argument("--token-file", required=True)
    p.add_argument("--text")
    p.add_argument("--text-file")
    p.add_argument("--json")
    p.add_argument("--json-file")
    p.add_argument("--file")
    p.add_argument("--download")
    a = p.parse_args()

    prefer_ipv4()
    tok = read_token(a.token_file)
    cmd = a.command

    text = a.text
    if a.text_file:
        text = open(a.text_file).read().strip()
    blob = None
    if a.json_file:
        blob = json.load(open(a.json_file))
    elif a.json:
        blob = json.loads(a.json)

    if cmd == "getMe":
        print(json.dumps(show(call(tok, "getMe"), cmd), ensure_ascii=False))

    elif cmd == "metadata":
        # one-line summary; read-backs are the only proof a field actually landed
        name = show(call(tok, "getMyName"), "getMyName")
        short = show(call(tok, "getMyShortDescription"), "getMyShortDescription")
        desc = show(call(tok, "getMyDescription"), "getMyDescription")
        cmds = show(call(tok, "getMyCommands"), "getMyCommands")
        photos = show(call(tok, "getUserProfilePhotos"), "getUserProfilePhotos")
        print(f"name={name.get('name')!r} short={short.get('short_description')!r} "
              f"desc={(desc.get('description') or '')[:60]!r}… len={len(desc.get('description') or '')} "
              f"commands={len(cmds) if isinstance(cmds, list) else 0} "
              f"photos={photos.get('total_count')}")

    elif cmd in ("setName", "setShort", "setDesc"):
        if not text:
            sys.exit(f"{cmd} needs --text/--text-file")
        field = {"setName": "name", "setShort": "short_description", "setDesc": "description"}[cmd]
        meth = {"setName": "setMyName", "setShort": "setMyShortDescription",
                "setDesc": "setMyDescription"}[cmd]
        print(json.dumps(show(call(tok, meth, {field: text}), meth)))

    elif cmd == "setCommands":
        if blob is None:
            sys.exit("setCommands needs --json-file/--json (array of {command,description})")
        print(json.dumps(show(call(tok, "setMyCommands", {"commands": json.dumps(blob)}),
                             "setMyCommands")))

    elif cmd == "setPhoto":
        if not a.file:
            sys.exit("setPhoto needs --file <png/jpg>")
        # The `photo` field MUST be an InputProfilePhoto JSON object, with the upload referenced
        # by attach://<file field name>. A plain file field returns
        # 400 "Bad Request: photo isn't specified".
        data = {"photo": json.dumps({"type": "static", "photo": "attach://avatar"})}
        print(json.dumps(show(call(tok, "setMyProfilePhoto", data,
                                   file_field="avatar", file_path=a.file), "setMyProfilePhoto")))

    elif cmd == "getPhotos":
        import requests

        res = show(call(tok, "getUserProfilePhotos"), "getUserProfilePhotos")
        sizes = res.get("photos") or []
        if not sizes:
            sys.exit("no profile photos set")
        best = sorted(sizes[-1], key=lambda s: s.get("file_size") or s.get("width", 0))[-1]
        print(f"total={res.get('total_count')} newest_file_id={best['file_id']} "
              f"{best.get('width')}x{best.get('height')} {best.get('file_size')}B")
        if a.download:
            meta = show(call(tok, "getFile", {"file_id": best["file_id"]}), "getFile")
            url = f"{API}/file/bot{tok}/{meta['file_path']}"
            open(a.download, "wb").write(requests.get(url, timeout=60).content)
            print(f"downloaded -> {a.download} ({os.path.getsize(a.download)}B)  "
                  f"now LOOK at it (vision) before calling the avatar done")

    else:  # raw escape hatch: tg_bot_api.py --token-file F getWebhookInfo
        data = {}
        if blob is not None:
            data = blob if isinstance(blob, dict) else {"data": blob}
        if text:
            data["text"] = text
        print(json.dumps(call(tok, cmd, data), ensure_ascii=False)[:2000])


if __name__ == "__main__":
    main()
