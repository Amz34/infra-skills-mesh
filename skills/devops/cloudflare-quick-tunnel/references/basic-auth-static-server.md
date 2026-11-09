# Basic Auth on a Python http.server Static Server (quick-tunnel privacy)

When a trycloudflare quick tunnel must NOT be public, gate the origin server with HTTP Basic Auth. The tunnel has no auth option; the app layer is the only gate.

## Recipe (verified 2026-08, A.S Love 7.0 deploy)

Add to `private_server.py` (subclass of `SimpleHTTPRequestHandler`):

```python
import base64, hmac, os

AUTH_USER = "aslove7"
AUTH_REALM = "A.S Love 7.0 Private"   # MUST be pure ASCII (see Pitfalls)
_PASS = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "caddy", ".pass.txt")).read().strip()

class PrivateHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_ROOT, **kwargs)

    def _authorized(self):
        h = self.headers.get("Authorization", "")
        if not h.startswith("Basic "):
            return False
        try:
            user, _, pw = base64.b64decode(h[6:]).decode("utf-8", "replace").partition(":")
        except Exception:
            return False
        return hmac.compare_digest(user, AUTH_USER) and hmac.compare_digest(pw, _PASS)

    def _deny(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", f'Basic realm="{AUTH_REALM}"')
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if not self._authorized():
            self._deny(); return
        super().do_GET()

    def do_HEAD(self):
        if not self._authorized():
            self._deny(); return
        super().do_HEAD()
```

- **Password from a plaintext file** (`.pass.txt` owned by the site dir) — reuse the same credential store the reverse-proxy route uses, so the user has ONE username/password for both deploy routes.
- `hmac.compare_digest` on both user and password = constant-time, no timing leak.
- `WWW-Authenticate` header is what triggers the browser login popup. Without it Chrome shows a bare error page instead of prompting.

## Pitfalls

- **Non-ASCII realm crashes startup**: `WWW-Authenticate: Basic realm="A.S Love 7.0 — Private"` (em-dash) dies on first request with `UnicodeEncodeError: 'latin-1' codec can't encode character` — the header is latin-1-encoded. Server starts fine, then explodes on the first hit (looks like a hang → actually a crash loop). Fix: ASCII-only realm.
- **Restart discipline**: `pkill -f private_server.py` from a shell whose own command line contains that string kills the shell (exit -15). Kill by session/pid instead.

## Verification (through the gate)

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:PORT/          # 401
curl -s -o /dev/null -w "%{http_code}\n" -u user:pass http://localhost:PORT/  # 200
# Same checks against the tunnel URL — the gate must be live end-to-end.
```

**Headless Chrome cannot answer the basic-auth popup** (no UI to type into). To confirm the real page renders behind auth, embed credentials in the URL:

```bash
google-chrome --headless=new --no-sandbox --user-data-dir=/tmp/auth-test \
  --dump-dom "https://user:pass@<tunnel>.trycloudflare.com/" | grep -c "expected-title-marker"
```

- SW precache, audio, images all work for the logged-in owner — same-origin fetch carries the Authorization header automatically.
- Delivering credentials: the USER (owner) gets username + password in chat; never write them into files/logs/summaries meant to be shared.
