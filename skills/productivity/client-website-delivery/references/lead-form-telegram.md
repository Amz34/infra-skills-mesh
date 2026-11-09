# Lead Form → Telegram (Cloudflare Pages Function)

Pattern proven on AVVS Triatek site (`~/clients/AVVS-Triatek/site/`).
Goal: contact form on a static client site delivers leads to Aamir's
Telegram DM instantly — no database, no email backend, $0.

## Pieces

- `functions/api/lead.js` — Pages Function (auto-detected by Cloudflare
  Pages from the `functions/` dir at project root; endpoint = `/api/lead`).
- Env vars: `TELEGRAM_BOT_TOKEN` (from ~/.hermes/.env), `TELEGRAM_CHAT_ID`
  = Aamir's DM chat id **8843884232** (find any user id in
  `~/.hermes/channel_directory.json`).
- Local dev secrets: `.dev.vars` at project root (gitignored), read by
  `npx wrangler pages dev public/`.
- Form JS: `fetch('/api/lead', {method:'POST', headers:{'Content-Type':
  'application/json'}, body: JSON.stringify({...})})` — fields: name, email,
  phone, company, country, interest, message, plus a HIDDEN `website` field
  as honeypot.

## functions/api/lead.js (canonical)

```js
export async function onRequestPost({ request, env }) {
  const cors = { "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type" };
  if (request.method === "OPTIONS")
    return new Response(null, { status: 204, headers: cors });
  try {
    const body = await request.json();
    if (body.website && String(body.website).trim() !== "") // honeypot
      return new Response(JSON.stringify({ ok: true }), { status: 200, headers: cors });
    const { name, email, phone, company, country, interest, message } = body;
    if (!name || !email || !phone || !interest)
      return new Response(JSON.stringify({ ok: false, error: "Required fields missing" }), { status: 400, headers: cors });
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(String(email)))
      return new Response(JSON.stringify({ ok: false, error: "Invalid email" }), { status: 400, headers: cors });
    const text = [
      "🔔 *NEW LEAD — AVVS Website*",
      `👤 Name: ${String(name).slice(0,100)}`,
      `📧 Email: ${String(email).slice(0,150)}`,
      `📱 Phone: ${String(phone).slice(0,50)}`,
      `🏢 Company: ${String(company || "—").slice(0,100)}`,
      `🌍 Country: ${String(country || "—").slice(0,50)}`,
      `🎯 Interest: ${String(interest).slice(0,100)}`,
      `📝 Message: ${String(message || "—").slice(0,500)}`,
      `_via website contact form_`,
    ].join("\n");
    const tg = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: env.TELEGRAM_CHAT_ID, text, parse_mode: "Markdown", disable_web_page_preview: true }),
    });
    const tgRes = await tg.json();
    if (!tgRes.ok) throw new Error("Telegram send failed: " + (tgRes.description || "unknown"));
    return new Response(JSON.stringify({ ok: true }), { status: 200, headers: cors });
  } catch (e) {
    return new Response(JSON.stringify({ ok: false, error: e.message }), { status: 500, headers: cors });
  }
}
```

## Deploy + secrets

```bash
npx wrangler pages dev public/            # local test (uses .dev.vars)
npx wrangler pages deploy public/         # preview/prod URL printed
npx wrangler pages secret put TELEGRAM_BOT_TOKEN
npx wrangler pages secret put TELEGRAM_CHAT_ID
```

Verify end-to-end: submit the form on the deployed preview, confirm the
lead arrives in Telegram, then tell the user the production URL. Test the
channel early (sendMessage curl) so failures surface before the site is live.

## Notes

- Bots spam the endpoint: honeypot field + basic email regex + required
  fields; enough for client lead sites.
- Client said "save in SQL or send on Telegram" — Telegram chosen (zero
  DB); if a local SQLite mirror is later wanted, a cron can append from
  Telegram or the function can also POST to a collector endpoint.
