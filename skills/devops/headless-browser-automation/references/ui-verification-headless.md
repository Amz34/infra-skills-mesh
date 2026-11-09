# Verifying a rendered web UI from a headless VM

Use when you must prove what a page actually renders (dashboard view, control table,
routing/hash bug) with no display available.

## Screenshot with JS allowed to finish

```bash
google-chrome --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
  --window-size=1700,1150 --virtual-time-budget=9000 \
  --screenshot=/tmp/out.png 'http://127.0.0.1:8765/#svc'
```

`--virtual-time-budget` is the load-bearing flag: it lets hash routing and the initial
fetches run before the capture. Without it you photograph an empty/unstyled shell and
conclude the feature is broken.

## Dump the DOM — that is the real verification

```bash
google-chrome --headless=new --disable-gpu --no-sandbox --virtual-time-budget=9000 \
  --dump-dom 'http://127.0.0.1:8765/#svc' > /tmp/dom.html
```

Then parse it: count data rows, read the cell order, read button labels / `data-*`
attributes, assert the build tag. This is deterministic text evidence — it is how you
prove "143 rows rendered, running containers show Stop/Restart/Remove, star in column 1".

## Pitfall: do not trust pixel-reading of a screenshot

Screenshots come back to the vision model **downscaled (~50%)**. Pixel estimates and
`region` crop coordinates taken from the preview are then wrong by ~2×, so crops land on
the wrong element. Real consequences seen in one session: a layout bug (action buttons in
the first column, left of the service name) was missed, while a "clipped input" was
"confirmed" that did not exist. Screenshots are for *layout aesthetics* only; facts come
from `--dump-dom` or from the API.

## CDP over websocket

Needs `--remote-allow-origins=*` on the chrome launch, otherwise the websocket handshake
is rejected. Always clear stragglers between runs (`pkill -f 'remote-debugging-port=9222'`)
— a leftover instance makes the next measurement script hang until it is killed. If the
only question is "did the DOM render correctly", `--dump-dom` is cheaper and cannot hang.

## Verify a control UI by driving its endpoints

For anything with buttons, test the API the buttons call (`curl -X POST` with the exact
headers/origin the UI sends) instead of clicking in a headless screenshot. Cover the
refusals too: protected target, public host, missing header, malformed name, unknown
action, and one full lifecycle on a throwaway object. Commit that suite next to the app
and re-run it after every change — "the screenshot looked right" is not QA.
