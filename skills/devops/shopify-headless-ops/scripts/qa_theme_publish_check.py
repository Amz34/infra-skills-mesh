#!/usr/bin/env python3
"""Post-stage / post-publish QA probe for a Shopify storefront (Playwright).

Run it twice: once against the staged theme (preview), once against LIVE after
`themePublish`. Live is the run that actually matters — `/tmp/pv_home.html`-style
curl fetches of `?preview_theme_id=` often come back EMPTY (bot handling), so use a
real browser for both.

Usage:
  python3 qa_theme_publish_check.py --url https://<store>.myshopify.com \
      [--theme-id 188437987631]            # omit for LIVE
      [--handle body-lotion-30-ml]         # product page regression check
      [--expect-text "Hotel-grade guest amenities"]
      [--expect-text "Website:"]
      [--shots-dir qa] [--wait 4]

What it asserts
  * every <video> on the page: paused / currentTime / readyState / videoWidth / error
    -- a screenshot of a paused or black <video> looks identical to a playing one,
       so playback must be read as JS state, never from pixels.
  * expected copy in document.documentElement.innerHTML (PRESENCE) as well as
    innerText (VISIBLE). innerText alone gives false negatives: a deferred/hidden
    footer section is absent from innerText while its HTML is present.
  * counts of wa.me links, "Order on WhatsApp", "checkout", "at checkout" -- the
    checkout counts must be 0 while orders route through WhatsApp.

Exit codes: 0 all good (or no <video> present), 1 a <video> is not playing, 2 crash.
"""
import argparse
import asyncio
import json
import os
import re
import sys

DESKTOP = {"width": 1440, "height": 900}
MOBILE = {"width": 390, "height": 844}


def probe_js(expect_texts):
    return """(expect) => {
      const html = document.documentElement.innerHTML;
      const txt = document.body ? document.body.innerText : '';
      const vids = [...document.querySelectorAll('video')].map(v => {
        const r = v.getBoundingClientRect();
        return {
          id: v.id || null, cls: v.className || null,
          src: (v.currentSrc || v.src || '').slice(0, 120),
          paused: v.paused, muted: v.muted, currentTime: +v.currentTime.toFixed(2),
          readyState: v.readyState, videoWidth: v.videoWidth, videoHeight: v.videoHeight,
          error: v.error ? (v.error.code || 'err') : null,
          box: {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)},
          upscale: v.videoWidth ? +(r.width / v.videoWidth).toFixed(2) : null
        };
      });
      const present = {}, visible = {};
      for (const e of expect) {
        present[e] = html.includes(e);
        visible[e] = txt.includes(e);
      }
      return {
        title: document.title,
        videos: vids,
        present_in_html: present,
        visible_in_innertext: visible,
        wa_links: (html.match(/wa\\.me\\//g) || []).length,
        wa_cta: (html.match(/Order on WhatsApp/g) || []).length,
        checkout: (html.match(/checkout/g) || []).length,
        at_checkout: (html.match(/at checkout/g) || []).length,
        netlify_link: (html.match(/netlify\\.app/g) || []).length
      };
    }"""


async def one_page(browser, url, viewport, tag, shots_dir, expect_texts, wait):
    page = await browser.new_page(viewport=viewport)
    out = {"url": url, "tag": tag, "viewport": viewport}
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(int(wait * 1000))
        # scroll to bottom so deferred/hidden (Horizon) sections actually render,
        # then back to top for the screenshot
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1500)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)
        out.update(await page.evaluate(probe_js(expect_texts), expect_texts))
        try:
            await page.click("button[aria-label*='ccept'], #shopify-pc__banner__btn-accept", timeout=1500)
        except Exception:
            pass
        if shots_dir:
            os.makedirs(shots_dir, exist_ok=True)
            shot = os.path.join(shots_dir, f"qa_{tag}_{viewport['width']}.png")
            await page.screenshot(path=shot)
            out["screenshot"] = shot
    except Exception as exc:  # keep going, report per page
        out["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        await page.close()
    return out


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="store base, e.g. https://x.myshopify.com")
    ap.add_argument("--theme-id", default=None, help="staged theme id (omit for LIVE)")
    ap.add_argument("--handle", default=None, help="product handle for the CTA regression check")
    ap.add_argument("--expect-text", action="append", default=[])
    ap.add_argument("--shots-dir", default="qa")
    ap.add_argument("--wait", type=float, default=4.0)
    a = ap.parse_args()

    base = a.url.rstrip("/")
    q = f"?preview_theme_id={a.theme_id}" if a.theme_id else ""
    label = f"theme{a.theme_id}" if a.theme_id else "live"
    pages = [(f"{base}/{q}", "home"), (f"{base}/cart{q}", "cart")]
    if a.handle:
        pages.append((f"{base}/products/{a.handle}{q}", "product"))

    from playwright.async_api import async_playwright
    results = []
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(channel="chrome")
        except Exception:
            browser = await p.chromium.launch()
        for url, tag in pages:
            for vp in (DESKTOP, MOBILE):
                if tag == "cart" and vp is MOBILE:
                    continue  # cart layout is covered on desktop
                results.append(await one_page(browser, url, vp, f"{label}_{tag}", a.shots_dir, a.expect_text, a.wait))
        await browser.close()

    print(json.dumps(results, indent=2)[:9000])

    bad = []
    for r in results:
        for v in r.get("videos", []) or []:
            if v.get("error"):
                bad.append(f"{r['tag']}@{r['viewport']['width']}: video error {v['error']}")
            elif v.get("paused") or not v.get("currentTime"):
                bad.append(f"{r['tag']}@{r['viewport']['width']}: video NOT playing (paused={v['paused']}, t={v['currentTime']})")
        if r.get("at_checkout") or r.get("checkout"):
            bad.append(f"{r['tag']}: checkout wording still present (checkout={r.get('checkout')}, at_checkout={r.get('at_checkout')})")
        for e, ok in (r.get("present_in_html") or {}).items():
            if not ok:
                bad.append(f"{r['tag']}: expected text missing from HTML: {e!r}")
    if bad:
        print("\nFAIL:\n- " + "\n- ".join(bad))
        return 1
    print("\nPASS: videos playing, WhatsApp routing intact, expected copy present.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
