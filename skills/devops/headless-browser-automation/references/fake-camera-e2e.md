# E2E-testing camera / getUserMedia web apps headlessly (fake camera + CDP)

How to drive a page that asks for a webcam, in a headless VM with no camera, and
assert the UI actually reacted. Verified on `~/fire-lab/tools/browser_e2e.py`
(11/11 pass, both on localhost and through a public tunnel URL).

## 1. Launch Chrome with a fake camera
```bash
chrome --headless=new --disable-gpu --no-first-run --no-default-browser-check \
  --use-fake-ui-for-media-stream \
  --use-fake-device-for-media-stream \
  --use-file-for-fake-video-capture=/tmp/fire.y4m \
  --window-size=430,932 \
  --remote-debugging-port=9222 --remote-allow-origins=* \
  --user-data-dir=/tmp/chrome-firewatch \
  "http://127.0.0.1:8512/?k=$CODE"
```
- `--use-fake-ui-for-media-stream` auto-grants the permission prompt (otherwise the
  page hangs on the dialog and every assertion downstream lies).
- `--use-file-for-fake-video-capture` needs **Y4M** (`yuv420p`), not mp4:
  ```bash
  ffmpeg -y -loop 1 -i frame.jpg -t 6 -r 10 -vf "scale=640:480,format=yuv420p" \
    -pix_fmt yuv420p /tmp/fire.y4m
  ```
  Loop a single image to get a stable, deterministic feed.
- **`--remote-allow-origins=*`** — without it the CDP websocket handshake is
  rejected ("403" on `/json/list` targets / connection refused on the ws upgrade).
- Headless Chrome needs `--headless=new` for `getUserMedia` to exist at all.
- Reuse one `--user-data-dir` per run and delete it afterwards.

## 2. Talk CDP with the stdlib
`websocket-client` + `urllib` is enough — no Playwright/Selenium needed.
Pattern that works:
1. `GET http://127.0.0.1:9222/json/list` until a `page` target appears.
2. **Match the target URL on the host you actually opened** — matching on
   `http://127.0.0.1:8512` breaks the moment you point the driver at a tunnel URL
   (`https://x.trycloudflare.com`). Parse the host from the URL under test
   (`urllib.parse`) and match on that, or on a page-specific marker like `/?k=`.
3. `websocket.create_connection(ws_url, timeout=180)`; `Page.enable`,
   `Runtime.enable`; then `Runtime.evaluate` for JS assertions and
   `Page.captureScreenshot` for artifacts.
4. Wrap `ws.recv()` in a timeout-retry loop; a busy Chrome drops long sessions.
5. `Page.navigate` → poll a DOM readiness signal instead of sleeping blindly.

## 3. Assertions that actually catch bugs
- **Poll the app's own numbers, not decorative text.** A banner/status line can
  legitimately read "muted / next email in 113s" during cooldown; asserting on it
  fails on correct code. Poll the console's alert counter / the server's
  `/api/events` instead.
- **Assert the reactive path, not just that the page loaded**: video element has a
  live `videoWidth`, boxes/labels appear, alert counter goes 0 → 1.
- **Loop the notification all the way out**: after the UI alerts, read the mail
  back over IMAP (see `email-imap-extraction` → send-and-read-back QA). UI alerts
  with no delivered email is the failure clients actually experience.
- **Re-run the whole suite through the public tunnel URL** before handing the link
  over. It is a different code path (proxy, TLS, host headers) and it is the exact
  URL the operator scans.
- Keep the driver re-runnable: it must start its own Chrome, wait for readiness,
  and clean up (`shutil.rmtree(user_data_dir)`) so it can run twice in a row.

## 4. Record the run as a demo clip (no screen recorder needed)
`Page.startScreencast` while the driver runs gives real motion frames of the live
UI: `Page.startScreencast(format='jpeg', quality=80, everyNthFrame=1)`, handle
`Page.screencastFrame` events (`sessionId` must be acked with
`Page.screencastFrameAck` or the stream stalls), write base64 JPEGs to
`frames/f%05d.jpg`, then `ffmpeg -framerate 12 -i frames/f%05d.jpg ...`.
Compose to 9:16 with PIL caption plates — see `ui-demo-video-production`.
