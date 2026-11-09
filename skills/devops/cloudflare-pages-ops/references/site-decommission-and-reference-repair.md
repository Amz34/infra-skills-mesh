# Decommissioned a Pages site — and repaired what the delete broke

Worked case: `az-consultants` (Pages project + local `~/az_consultants/site/**`) deleted on user
order, while two sibling projects (`azconsultants-india`, `azconsultants-ksa`) were KEPT live and a
cold-outreach campaign with 2 pending systemd-timer waves lived inside the same folder.

## What the delete actually broke (the expensive part)

| Breakage | Why | Fix |
|---|---|---|
| Dead site URL baked into campaign copy | `outreach/tmpl.py` `body()` + `sms()` hardcoded `az-consultants.pages.dev` | replaced with the live sibling domain in the template module |
| Dead URL inside a generated attachment | `AZ_Tender_Outreach_List.xlsx` built by `mkxlsx2.py` from a `SITE =` constant — 41 embedded refs, `grep` cannot see inside the zip | patched the constant, re-ran `mkxlsx2.py` |
| Build script failed after cleanup | `mkxlsx2.py` read `~/az_consultants/master_raw.json`, which step 4 had deleted | selective restore from the tar |
| SMS silently became 2 SMS | new domain 7 chars longer → worst case 164 chars | trimmed the template (see below) |
| Copy's claims became false | the replacement site is a brochure; the copy still promised "the tender map, the buyer groups, the 14-point pass" *on that page* | grepped the claim words against the live target (0 hits) → reframed the copy so the promise rides the reply-"BID" funnel file; the page link demoted to "background on the practice" |
| Attachment label pointed at nothing real | xlsx row said `Gated funnel document → <new-site>/funnel`, which 200s but opens the plain brochure | row relabelled to the real channel: `Funnel file (on reply "BID") | emailed as attachment`; `mkxlsx2.py` patched + workbook rebuilt |
| Fulfilment file deleted with the site | the file promised to repliers lived under the deleted tree — disk had none, only the tar | restored from the tar into the campaign dir, verified self-contained (`0` refs to the dead domain) and that its own claims are inside it |

## Commands

Recon before touching anything:
```bash
npx wrangler pages project list
grep -rl "az-consultants" ~/.config/systemd/user/ ~/.hermes/scripts/ 2>/dev/null
systemctl --user list-timers 'az-*' --all      # 2 wave timers pending → their dir must survive
```

Backup + delete + verify death:
```bash
tar czf ~/backups/az_consultants_$(date +%Y%m%d_%H%M).tar.gz -C /home/ubuntu az_consultants
npx wrangler pages project delete az-consultants
dig +short az-consultants.pages.dev            # empty = really gone
```

Find every dead reference, including inside binaries:
```python
import pathlib, re, zipfile
OLD, NEW = 'az-consultants.pages.dev', 'azconsultants-india.pages.dev'
for f in pathlib.Path('.').rglob('*'):
    if not f.is_file(): continue
    if f.suffix in ('.xlsx', '.zip'):                      # grep cannot see inside these
        z = zipfile.ZipFile(f)
        blob = ''.join(z.read(n).decode('utf8','ignore') for n in z.namelist() if n.endswith('.xml'))
        print(f, 'new', len(re.findall(NEW, blob)), 'dead', len(re.findall(OLD, blob)))
    else:
        t = f.read_text(errors='ignore')
        if OLD in t: print('TEXT', f, t.count(OLD))
```
Also `rm -rf <dir>/__pycache__` — stale `.pyc` still held the old string and would keep showing up
in greps after the source was fixed.

Selective restore of one file the surviving script needed:
```bash
tar xzf ~/backups/az_consultants_20260911_2230.tar.gz -C /home/ubuntu az_consultants/master_raw.json
```

## SMS length recompute (per lead, worst case)

New domain = +7 chars → 164 chars on the longest firm name = 2 SMS for that lead.
```python
import importlib.util, json
spec = importlib.util.spec_from_file_location('t', 'tmpl.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
leads = json.load(open('sms_send2.json'))
worst = max(leads, key=lambda l: len(m.sms(l)))
print(len(m.sms(worst)), m.sms(worst))          # 164 → over budget
```
Trim filler, keep the CTA: `"Reply BID or see <url>"` → `"Reply BID: <url>"` (−6) → worst case 158.
Final state: `max sms 158 | over160 0 | gsm7 True`.

## Verification bar used (report these, not "done")

- whole-tree grep for the dead domain → **0 hits**
- rebuilt attachment: `xlsx: new_link 41 | dead_link 0`
- dry render (`send_campaign.py --render`, no send) shows the new URL in email body + SMS
- wave markers still ABSENT (`.email_wave2_done` / `.sms_wave2_done`) → timers will still fire
- `systemctl --user list-timers 'az-*' --all` → wave-2 still scheduled (Mon 04:30 / 05:15 UTC)
- kept siblings untouched: `azconsultants-india.pages.dev`, `azconsultants-ksa.pages.dev` live

## Lessons

- Deleting "just a website" can break money-path automation in the same folder. Grep for the
  domain and the folder path across systemd units, cron, and scripts BEFORE the delete.
- Cleanup that deletes data files can break build scripts that survive. Prefer deleting the
  site/build outputs and keeping raw data, or be ready to restore one path from the tar.
- Verify a delete from DNS, not from the dashboard.
- "0 hits in the sources" is not enough — check generated artifacts (xlsx/zip) and stale caches.
