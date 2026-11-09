# Self-Hosted Analytics on Cloudflare Pages (KV-backed, zero login, zero cookie)

Use when the client site needs pageview analytics but NO dashboard login is
available (VM browser not logged into Cloudflare, RUM API 401s with the
wrangler OAuth token, user won't/can't enable CF Web Analytics). This is the
"khud karlo" fallback — fully self-contained, privacy-friendly, works on any
Pages site. PROVEN live on AVVS Triatek (2026-08).

## Design
- `functions/api/t.js` — tracking pixel endpoint: `GET /api/t?p=<path>&r=<referrer>`.
  No cookies, no personal data, no third-party calls. Aggregates into KV:
  lifetime `v:<path>` counter + daily `d:<YYYY-MM-DD>:<path>` counter.
- `functions/api/stats.js` — `GET /api/stats` returns JSON: total pageviews,
  per-path counts, referrer domains, daily breakdown (last N days).
- Inline snippet in every HTML page: on load, `fetch('/api/t?p='+path+'&r='+referrer)`.
- KV namespace `AVVS_ANALYTICS` bound in `wrangler.toml` as `AVVS_ANALYTICS`.

## Steps
```bash
# 1. Create + bind KV namespace
npx wrangler kv namespace create AVVS_ANALYTICS
#    → copy the id; add to wrangler.toml:
#      [[kv_namespaces]]
#      binding = "AVVS_ANALYTICS"
#      id = "<the-new-id>"
# 2. Write functions/api/t.js and functions/api/stats.js (below)
# 3. Inject snippet into every page (EN + ar/ subfolder):
#    python3 - <<'EOF'
#    import glob
#    for p in glob.glob("*.html") + glob.glob("ar/*.html"):
#        s = open(p, encoding="utf-8").read()
#        snip = '<script>fetch("/api/t?p="+location.pathname+"&r="+encodeURIComponent(document.referrer)).catch(()=>{});</script>'
#        if "/api/t" not in s:
#            s = s.replace("<head>", "<head>\n" + snip, 1)
#            open(p, "w", encoding="utf-8").write(s)
#    EOF
# 4. Deploy, then RE-DEPLOY (see pitfall below), then verify:
curl -s "https://<site>.pages.dev/api/t?p=/test&r=https://www.google.com"
curl -s "https://<site>.pages.dev/api/stats"
```

## functions/api/t.js (tracker)
```js
export async function onRequestGet(ctx) {
  const { searchParams } = new URL(ctx.request.url);
  const p = (searchParams.get("p") || "/").slice(0, 200);
  const r = (searchParams.get("r") || "").slice(0, 200);
  const kv = ctx.env.AVVS_ANALYTICS;
  const today = new Date().toISOString().slice(0, 10);
  const refDomain = (() => {
    try { return r ? new URL(r).hostname.replace(/^www\./, "") : "direct"; }
    catch { return "direct"; }
  })();
  await Promise.all([
    kv.put(`v:${p}`, String((parseInt(await kv.get(`v:${p}`)) || 0) + 1)),
    kv.put(`d:${today}:${p}`, String((parseInt(await kv.get(`d:${today}:${p}`)) || 0) + 1)),
    kv.put(`ref:${today}:${refDomain}`, String((parseInt(await kv.get(`ref:${today}:${refDomain}`)) || 0) + 1)),
  ]);
  return new Response("ok", { headers: { "Access-Control-Allow-Origin": "*" } });
}
```

## functions/api/stats.js (reader)
```js
export async function onRequestGet(ctx) {
  const kv = ctx.env.AVVS_ANALYTICS;
  const list = await kv.list({ limit: 1000 });
  const out = { total: 0, pages: {}, days: {}, refs: {} };
  for (const k of list.keys) {
    const v = parseInt(await kv.get(k.name)) || 0;
    if (k.name.startsWith("v:")) { out.pages[k.name.slice(2)] = v; out.total += v; }
    else if (k.name.startsWith("d:")) out.days[k.name.slice(2)] = v;
    else if (k.name.startsWith("ref:")) out.refs[k.name.slice(4)] = v;
  }
  return Response.json(out);
}
```

## PITFALL — first deploy 404s on /api/*
The FIRST `wrangler pages deploy` after adding `functions/` may report
"Uploaded 0 files (N already uploaded)" and skip the functions bundle —
`/api/t` and `/api/stats` then 404 (propagation/upload quirk). FIX: just
deploy AGAIN; the second run prints "✨ Uploading Functions bundle" and the
endpoints go live. Always verify with curl after the SECOND deploy, not the
first. (Same class of "first test fails = propagation delay" as lead.js
secrets — check getMe/endpoint before assuming the code is wrong.)

## Stats check-in
`/api/stats` is a live JSON endpoint — share it with the user or pull it
yourself whenever they ask "stats bata". It accumulates from deploy time
onward; there's no historical data before installation.
