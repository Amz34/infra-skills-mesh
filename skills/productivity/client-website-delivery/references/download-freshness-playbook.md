# Download Buttons & Freshness Playbook (2026-08, A.S Love 7.0)

Companion to `service-worker-caching-pitfalls.md` and
`pwa-install-debugging.md`. Captures the client-side download fix and the
"first page should be home" verification that emerged in later fix rounds.

## Blob force-download (in-app browsers ignore `<a download>`)

In-app browsers (WhatsApp/Telegram/Instagram) and iOS Safari IGNORE the
native `download` attribute — tapping the link just opens the file. Make
every `.dl-btn` link force-download via blob:

```js
document.addEventListener("click", function (e) {
  var a = e.target.closest ? e.target.closest(".dl-btn") : null;
  if (!a) return;
  e.preventDefault();
  var url = a.href, name = (a.getAttribute("download") || url.split("/").pop());
  a.textContent = "Preparing…";
  fetch(url).then(function (r) {
    if (!r.ok) throw 0;
    return r.blob();
  }).then(function (b) {
    var o = URL.createObjectURL(b), t = document.createElement("a");
    t.href = o; t.download = name; document.body.appendChild(t); t.click();
    setTimeout(function () { URL.revokeObjectURL(o); t.remove(); }, 4000);
    a.textContent = a.getAttribute("data-label") || "Download";
  }).catch(function () { window.location.href = url; });
});
```

Each `.dl-btn` carries `data-label` (original text) + `download="exact filename"`.
Server MUST also send `Content-Disposition: attachment; filename="..."` for
the fallback path — verify with
`curl -sI <tunnel>/assets/docs/<file> | grep -i content-disposition`.

## Extra freshness layer: no-cache meta on HTML pages

Even with network-first SW, some browsers cache HTML aggressively. Add to
every page's `<head>`: `<meta http-equiv="Cache-Control" content="no-cache">`
(loop with `sed -i 's|<meta name="viewport"|<meta http-equiv="Cache-Control" content="no-cache">\n<meta name="viewport"|' *.html`).
Forces the browser to revalidate HTML, so the fresh SW version string reaches
the device on FIRST load, not the second.

## "First page should be home" — 3-layer verification

When the user says the site opens on the wrong page, verify ALL THREE entry
layers — any one can point elsewhere:

1. **Root URL** — `curl -s <site>/ | grep -o "<title>[^<]*</title>"` must
   show the home title. A `private_server.py`-style server defaults to
   `index.html`.
2. **PWA manifest `start_url`** — must be `./index.html` (or `./`).
3. **SW `CORE` precache list** — `./` and `./index.html` FIRST entries.

Usually all three are already correct and the user simply navigated to a
subpage (tapped "Read my letter →") and expected the next fresh open to land
home anyway. Confirm each layer, then tell the user: a fresh open of the
root URL always starts at home; subpages open only via their buttons.

## Testing recipe (headless verify of dynamic pages)

`google-chrome --headless=new --no-sandbox --disable-gpu --window-size=390,844
--virtual-time-budget=6000 --dump-dom <url> > live.html` then grep for
JS-built elements (gallery counts, gate markup). Virtual-time-budget lets
JS-built DOM finish. For exact mobile emulation use CDP
`Emulation.setDeviceMetricsOverride` (see headless-browser-automation).
