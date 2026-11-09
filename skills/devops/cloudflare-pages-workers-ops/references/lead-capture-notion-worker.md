# Lead capture → Notion master DB (silent side-copy)

Landing email-gate ka lead **email pipeline (formsubmit.co) untouched** rehta
hai — Notion capture sirf ek silent extra copy hai. Token kabhi browser me
expose nahi hota: browser → CF Worker proxy → Notion API.

## Architecture

1. **Landing page** (`landing/index.html`): email form submit success `.then()`
   block me ek fire-and-forget beacon:
   ```js
   .then(() => {
     notifyNotion(email.value);          // email = captured input value
     document.getElementById('dl').classList.add('show');
   })
   // notifyNotion = fetch('<worker>.workers.dev/lead', {method:'POST',
   //   headers:{'Content-Type':'application/json'},
   //   body: JSON.stringify({email, source:'az-ebook', page:'landing'})})
   //   .catch(()=>{})  // silent — kabhi form flow break nahi karna
   ```
2. **CF Worker** (`notion-lead-worker/`): `POST /lead` → validate email regex →
   Notion API create-page in master DB. Response 200/201 (created) / 400 (bad) /
   503 (Notion down). OPTIONS preflight + CORS.
3. **Notion master DB**: har lead ek row — Email (title), Source (select),
   Page (select), Status (select: New/Downloaded), Date.

## Notion API hard rules (sikhe hue)

- **Internal integration token sirf USER bana sakta hai** — agent kabhi nahi
  (Notion hard rule). User step: https://www.notion.so/my-integrations → New
  integration → copy `ntn_...` token.
- **Naya integration = ZERO page access.** `POST /v1/search` → 0 results tab tak
  jab tak user grant na de. Grant paths (user ke liye exact steps):
  - https://www.notion.so/my-integrations → integration → **Access** → select
    pages ya "All pages"/workspace, ya
  - kisi page par `•••` → Connections → Connect to → integration search.
  - Agent API se "connect page link" nahi de sakta — direct URLs hi answer hain.
- API: base `https://api.notion.com/v1`, header **`Notion-Version` required**
  (e.g. `2025-09-03`). Status semantics: 401 = bad token; 403/404 = page access
  nahi (grant pending); 400 = payload/version issue.
- Token store: `~/.config/notion/token` chmod 600. `ntn` CLI 0.23.1 at
  `~/.local/bin/ntn` — PATH me `~/.local/bin` hamesha nahi hota; verify with
  `export PATH="$PATH:$HOME/.ntn/bin:$HOME/.local/bin"`.

## Master DB banana (2025-09-03 API quirks — VERIFIED 2026-09)

Naya model: database object me `data_sources[]` array hota hai (har DB me 1
default data source), top-level `properties` **nahi** hota. Property schema
data source par rehta hai. Ye sequence end-to-end tested hai:

1. **DB create** = `POST /v1/databases` ONLY. `POST /v1/data_sources` refuse
   karta hai: *"Creating new databases with data sources is not supported in
   this endpoint for API version 2025-09-03 and later. Use the Create Database
   API instead"* (aur `initial_data_source_properties` se 400 *"body.properties
   should be defined"* aata hai — ye key ghalat hai).
   ```json
   POST /v1/databases  {"parent":{"page_id":"<parentPage>"},
     "title":[{"text":{"content":"Website Leads"}}], "properties":{...}}
   ```
2. **TRAP:** `properties` payload create par **silently IGNORE** hota hai — 200
   aata hai lekin DB me sirf default **"Name"** title property wala data source
   banta hai. Isliye response se DB id + `data_sources[0].id` dono le lo.
3. **Properties add karo:** `PATCH /v1/data_sources/{ds_id}` body
   ```json
   {"properties": {
     "Email": {"title": {}},
     "Source": {"select": {"options": [{"name":"az-ebook.pages.dev"},{"name":"LinkedIn"},{"name":"Other"}]}},
     "Status": {"select": {"options": [{"name":"New"},{"name":"Contacted"},{"name":"Qualified"},{"name":"Converted"}]}},
     "Signed Up": {"date": {}},
     "Name": {"name": "Email"}    // default title ka rename, ek hi PATCH me
   }}
   ```
   → 200, saari properties live. (Rename + add same PATCH me chalta hai.)
4. Row create ab bhi **classic**: `POST /v1/pages {"parent":{"database_id":...},
   "properties":{...}}` → 201 kaam karta hai (worker yehi karta hai).
5. Row verify/query: `POST /v1/databases/{id}/query` **Notion-Version:
   2022-06-28** header ke saath → 200 rows (classic compat). Naye-model
   endpoints (`/data_sources/{id}/items`, `/query`) invalid_request_url 400
   dete hain. `POST /v1/search` + query-string rows ke liye reliable NAHI hai.
6. Select write par value ka naam DB option se **exact** match hona chahiye —
   mismatch par Notion naya option auto-create kar deta hai (junk options).
   Isliye worker payload `source:'az-ebook.pages.dev', page:'Guide Download'`
   — DB options se exact.

## Worker deploy + secret

```bash
# wrangler.toml: name="az-notion-lead", main="src/worker.js",
# [vars] NOTION_DB_ID="" (DB banne ke baad bharo)
printf '%s' "$(cat ~/.config/notion/token)" | npx wrangler secret put NOTION_TOKEN
npx wrangler deploy        # worker dir me
```

## Test lead (har deploy ke baad)

1. `curl -X POST https://<worker>.workers.dev/lead -H 'Content-Type: application/json' -d '{"email":"test@example.com","source":"az-ebook","page":"landing"}'` → 201.
2. Verify row Notion DB me (user ya API se) + confirm formsubmit email bhi aayi
   (pipeline untouched proof).
3. Landing pe `notifyNotion` base URL worker se replace karo → redeploy Pages.

## DB schema (master — "AZ Master Leads" page → "Website Leads" DB)

Columns (data source properties): **Email** (title — default "Name" rename se),
**Source** (select: az-ebook.pages.dev / LinkedIn / Other), **Page** (select:
Guide Download / Contact / Other), **Status** (select: New / Contacted /
Qualified / Converted / No Reply), **Signed Up** (date, auto today).
Full creation+fix flow upar (Master DB banana section) — pehle create, phir
data source PATCH. User ko approval ke liye DB URL bhejo
(`https://app.notion.com/p/<db-id-no-dashes>` — API response ka `url` field).
User ke pehle connected page ko parent banao (access scope me rahega).
All-pages grant hone par bhi naya DB parent page ke andar hi banao — safe.
