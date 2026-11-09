#!/usr/bin/env python3
"""Minimal n8n Public API client + safe activate/deactivate route probe.

Key is read from /etc/n8n/env at call time (mode 600, root) and is NEVER printed.

Usage:
  python3 n8n_api.py probe                 # create throwaway wf, probe /deactivate, delete
  python3 n8n_api.py list                  # id | active | name for all workflows
  python3 n8n_api.py activate <id>
  python3 n8n_api.py deactivate <id>
  python3 n8n_api.py import <file.json>    # create workflow from export JSON
  python3 n8n_api.py update <id> <f.json>  # PUT full body {name,nodes,connections,settings}
                                           # -> RESTART n8n afterwards for it to take effect
  python3 n8n_api.py delete <id>
"""
import json
import subprocess
import sys
import urllib.error
import urllib.request

BASE = 'http://127.0.0.1:5678/api/v1'


def _key():
    return subprocess.run(
        ['sudo', '-n', 'sed', '-n', 's/^N8N_API_KEY=//p', '/etc/n8n/env'],
        capture_output=True, text=True).stdout.strip()


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={'X-N8N-API-KEY': _key(), 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw.strip() else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            raw = json.loads(raw)
        except Exception:
            pass
        return e.code, raw


def list_workflows():
    out = []
    cursor = None
    while True:
        p = '/workflows?limit=100' + (('&cursor=' + cursor) if cursor else '')
        st, b = call('GET', p)
        if st != 200:
            return out, (st, b)
        out += b.get('data', [])
        cursor = b.get('nextCursor')
        if not cursor:
            return out, None


def probe():
    """Create a throwaway workflow and probe the deactivate route (no live impact)."""
    body = {'name': 'ZZ API Probe (delete me)', 'nodes': [
        {'id': 'p1', 'name': 'NoOp', 'type': 'n8n-nodes-base.noOp',
         'typeVersion': 1, 'position': [0, 0], 'parameters': {}}],
        'connections': {}, 'settings': {'executionOrder': 'v1'}}
    st, b = call('POST', '/workflows', body)
    print('create probe:', st, (b or {}).get('id') if isinstance(b, dict) else b)
    if st not in (200, 201):
        return
    wid = b['id']
    st2, b2 = call('POST', '/workflows/%s/deactivate' % wid)
    print('POST /deactivate ->', st2, json.dumps(b2)[:200] if not isinstance(b2, str) else b2)
    st3, b3 = call('POST', '/workflows/%s/activate' % wid)
    print('POST /activate   ->', st3, json.dumps(b3)[:200] if not isinstance(b3, str) else b3)
    st4, b4 = call('DELETE', '/workflows/%s' % wid)
    print('DELETE probe     ->', st4, json.dumps(b4)[:120] if not isinstance(b4, str) else b4)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'list'
    if cmd == 'probe':
        probe()
    elif cmd == 'list':
        wfs, err = list_workflows()
        if err:
            print('error', err)
        for w in wfs:
            print('%-22s active=%-5s %s' % (w['id'], w.get('active'), w['name']))
    elif cmd in ('activate', 'deactivate', 'delete'):
        wid = sys.argv[2]
        m = {'activate': 'POST', 'deactivate': 'POST', 'delete': 'DELETE'}[cmd]
        p = '/workflows/%s' % wid + ('' if cmd == 'delete' else '/' + cmd)
        st, b = call(m, p)
        print(cmd, wid, '->', st, (json.dumps(b) if not isinstance(b, str) else b)[:200])
    elif cmd == 'import':
        wf = json.load(open(sys.argv[2]))
        st, b = call('POST', '/workflows', wf)
        print('import ->', st, (b or {}).get('id') if isinstance(b, dict) else b)
    elif cmd == 'update':
        wid = sys.argv[2]
        wf = json.load(open(sys.argv[3]))
        st, b = call('PUT', '/workflows/%s' % wid, wf)
        msg = json.dumps(b) if not isinstance(b, str) else b
        print('update', wid, '->', st, msg[:300])
        if isinstance(b, dict):
            print('  nodes returned:', len(b.get('nodes', [])), '| active:', b.get('active'))
