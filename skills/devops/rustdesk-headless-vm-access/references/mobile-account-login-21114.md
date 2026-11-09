# RustDesk 1.4 mobile account-login → :21114 Connection refused

Session: 2026-09-09, Oracle VM (RustDesk 1.4.9 service as root) + user's Android RustDesk.

## Exact error (from user phone screenshot, OCR'd)
```
Unknown Error: Failed to parse response.
reqwest::Error { kind: Request, url: "http://100.110.242.47:21114/api/login",
source: ... tcp connect error, Connection refused (os error 111) ... }
```
Sequence observed in the app UI:
1. Connect sheet showed a **Login** section with **Username** + **Password** fields
   (where an older app shows just a password box).
2. Leaving Username empty → validation error **"Username missed"**.
3. Filling Username=`root` + Password=<one-time pw> → the `/api/login` POST above,
   connection refused.

## Diagnosis chain
1. `:21114` is the **RustDesk Server Pro** web API port. The deployment runs
   community `rustdesk-server` (hbbs + hbbr only) → nothing listens on 21114.
2. Conclusion: filling Username puts the app in *server account-login mode* — the
   Username/Password sheet is for the SERVER account, not the target peer password.
   Peer one-time/permanent passwords never go through `/api/login`.
3. Corroboration: rustdesk/rustdesk GitHub issue #12875 ("Issue with client
   ios/android after login using self hosted server", ~1.4.1): after setting
   ID server + API server + key and logging in, all connects fail; **logging out
   restores normal connects**. Closed as duplicate of discussion #10127
   (self-hosting Q&A).
4. Even "Username missed" with an empty field = app stuck in account mode; the fix
   is disabling account mode, NOT guessing usernames.

## Fix (user-side, in order of preference)
1. Phone app → Settings → ID/Relay Server config → **delete the "API Server" value**
   (keep only ID server + key). Save and retry.
2. If no API Server field exists: Settings → Account → **Log out**, then retry.
3. Connect with Remote ID + the target's one-time/permanent password only; Username
   blank / Login section collapsed.

Target-side username (only relevant if a non-community login mode is ever used) =
the OS user running the rustdesk service (`root` on this VM; verify with
`ps -o user= -p <pid>`).

## Screen layout identifying the trap (1.4 Android connect sheet)
```
Remote ID   385948621
Login                  ← section header (account mode)
Username   [        ]
Password   [********]
[error text below]     ← /api/login URL visible in full
Chat | Share screen | Settings
```
If "Login" + Username appear where an older app showed only a password prompt →
account mode. OCR the error in full before theorizing — the URL names the culprit.
