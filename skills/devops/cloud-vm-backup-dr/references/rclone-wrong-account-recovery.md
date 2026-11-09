# rclone wrong-account re-auth + archive-based token recovery (verified 2026-09-10)

Ye tab hai jab OAuth "safal" hota hai par **galat Google account** ka token ban jata hai — koi error nahi,
bas offsite data gayab. `rclone config reconnect` / koi bhi browser login **browser ka default Google
session** authorize kar deta hai; us waqt Chrome me jo account signed-in tha, wahi token ban jata hai.

## Symptoms (silent — "login done" ≠ kaam ho gaya)
- `rclone lsf gdrive:Hermes-Telegram-Backup/` → `directory not found` (folder dikhta hi nahi)
- `rclone about gdrive:` khaali free account: ~40 MiB used / 15 GiB — jabki asli folder me ~3.8 GiB archives
- `rclone lsd gdrive:` me ajnabi folders (is case: `Gemini Gems`, `Google AI Studio`, `Job Application Form (File responses)`)
- `rclone lsf --drive-shared-with-me gdrive:` me kuch unrelated docx/pdf
- Remote `about`/`lsd` chalta rehta hai (auth valid hai!) — isliye nightly backup/mirror "success" dikhata rahega

**Fast detector:** free-tier quota hi answer de deta hai. 15 GiB quota pe ~40 MiB used = us account me tumhara
kuch nahi hai; tumhara folder (~3.8 GiB) kisi doosre account me pada hai.

## Recovery — user se dobara login karane se PEHLE ye try karo
Nightly encrypted archive me purani **0600 rclone config** (refresh_token sameta) maujood hoti hai, aur wo
token long-lived hota hai → usi ke refresh_token ko direct exchange karo. User round-trip bach jata hai.

```bash
A=$(ls -t /home/ubuntu/ops/backups/*.tar.gz.gpg | head -1)
sudo -n gpg -d --batch --quiet --passphrase-file /home/ubuntu/ops/backups/.gpg_passphrase "$A" \
  | tar -xzO ./config/rclone/rclone.conf > /tmp/old-rclone.conf
ls -l /tmp/old-rclone.conf      # 0 bytes = extraction fail (galat passphrase path / galat member path)
```
- Archive ke andar home tree `./config/...`, `./n8n/...` ke naam se hota hai — member path
  `tar -tz | grep rclone` se confirm karo.
- Passphrase file `ops/backups/.gpg_passphrase` hai; **galat path dene pe gpg chup-chaap fail hota hai aur
  file khaali ban jaati hai** (koi error nahi) — isliye write se pehle `ls -l` se size check lazmi.
- Phir §7 wala refresh exchange archived `refresh_token` pe chalao (client_id/secret §4 me), aur jeeta hua
  token + `expiry: 2035-01-01` **original config** ke saath wapas likho. Sirf token line badalna kaafi nahi:
  scope/root_folder_id/team_drive settings wrong-account config ke reh jayenge → poora original config restore karo
  (jisme sirf token line replace ho).
- Ready-made script: `~/work/n8n/fix_gdrive_token.py` — archived config se refresh_token nikalta hai,
  exchange karta hai, expiry pin karta hai, kuch bhi secret print nahi karta.
- Agar refresh `invalid_grant` de → wo refresh token bhi mar chuka → tab hi asli login (steps 2–4) karo.
- Is case me isne **bina user login** original account + 4 archives wapas la diye (3.77 GiB visible).

## Verification (do checks — mandatory)
```bash
rclone lsf gdrive:Hermes-Telegram-Backup/ | tail     # expected archives dikhne chahiye
rclone size gdrive:Hermes-Telegram-Backup/           # ~3.8 GiB (khaali 15 GiB/40 MiB = wrong account)
```
"Aap login kar liye" **proof nahi hai** — pehle yahi assert karo, phir aage badho.

## Handover rule (jab user ko login flow dena hi pade)
- Account **naam se** likho: backup Drive account = `azengineeringapp@gmail.com`.
- "Use another account" choose karwao — "Create account" kabhi nahi.
- Browser me pehle se koi doosra session ho to usay sign out karwao ya fresh Chrome profile use karo
  (`--user-data-dir=/home/ubuntu/.cache/chrome-vnc`).
- Flow ke baad upar ke do checks chalao, **phir** tunnel/desktop band karo.
