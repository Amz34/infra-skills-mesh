#!/usr/bin/env python3
"""Decode n8n's `execution_data.data` blob and print per-node item counts + errors.

Why this exists: `execution_data.data` is `flatted`-encoded (a JSON array whose entries are
referenced by numeric *string* values, e.g. {"resultData": "2"}). Plain json.loads() returns a
list, so `data['resultData']` raises `'list' object has no attribute 'get'`. Resolve those
string indices against the top-level array and it reads like normal JSON.

This is the fast way to answer "did BOTH branches of my workflow actually receive items?"
without opening the editor — the systemd log only shows the failure text.

Usage:
  python3 decode_execution_data.py <execution_id> [--db /path/to/database.sqlite]
  python3 decode_execution_data.py --last 3          # newest 3 executions
"""
import json
import os
import sqlite3
import sys


def flatted(text):
    arr = json.loads(text)

    def rev(v):
        if isinstance(v, list):
            return [rev(x) for x in v]
        if isinstance(v, dict):
            return {k: rev(x) for k, x in v.items()}
        if isinstance(v, str) and v.isdigit() and int(v) < len(arr):
            return rev(arr[int(v)])
        return v
    return rev(arr[0])


def show(c, eid):
    row = c.execute('select "workflowId", status, mode, "startedAt" from execution_entity '
                    'where id=?', (eid,)).fetchone()
    print('execution %s -> %s' % (eid, row))
    raw = c.execute('select data from execution_data where "executionId"=?', (eid,)).fetchone()
    if not raw or raw[0] is None:
        print('  (no execution_data row)')
        return
    try:
        run_data = flatted(raw[0])['resultData']['runData']
    except Exception as e:
        print('  decode failed: %s' % e)
        return
    for name, runs in run_data.items():
        for run in runs:
            main_out = (run.get('data') or {}).get('main') or []
            print('  %-32s items=%-12s err=%s' % (
                name, [len(x) for x in main_out],
                ((run.get('error') or {}).get('message') or '')[:70]))


def main():
    db = os.path.expanduser('~/.n8n/database.sqlite')
    if '--db' in sys.argv:
        db = sys.argv[sys.argv.index('--db') + 1]
    c = sqlite3.connect('file:%s?mode=ro' % db, uri=True)

    args = [a for a in sys.argv[1:] if not a.startswith('--') and a != db]
    if not args or '--last' in sys.argv:
        n = 3
        if '--last' in sys.argv:
            n = int(sys.argv[sys.argv.index('--last') + 1])
        ids = [r[0] for r in c.execute(
            'select id from execution_entity order by id desc limit ?', (n,))]
        for eid in reversed(ids):
            show(c, eid)
        return 0
    show(c, args[0])
    return 0


if __name__ == '__main__':
    sys.exit(main())
