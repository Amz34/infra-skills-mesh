# Product Videos + Homepage Video Hero + Theme-Asset Galleries (Admin API)

Working recipe from Luxewave (Horizon theme, API 2026-07, `shpat_` token). All verified live.

## 1. Video → product media (canonical flow, 5 dead ends avoided)

**Flow that WORKS (3 GraphQL/admin steps):**

```
1. stagedUploadsCreate(resource: VIDEO, filename, mimeType: "video/mp4", httpMethod: "PUT")
   → { url, parameters: { ...signed GCS params } }
2. HTTP PUT file bytes to url (multipart form-data with the parameters as fields)
   → 204 = file staged
3. productCreateMedia(productId, media: [{ originalSource: <resourceUrl FROM STAGED RESPONSE>,
                                          mediaContentType: VIDEO }])
   → media: [{ id: "gid://shopify/Video/<n>" }], userErrors: []
```

Verify: GraphQL `product(id:) { media { ... on Video { id mediaContentType } } }` — status READY is NOT proof of attach; the product-media list is the proof.

**Dead ends (do NOT retry):**

| Attempt | Result |
|---|---|
| REST Files API multipart upload | 406 |
| `fileCreate` then `productCreateMedia(originalSource: <fileCreate file id>)` | **Duplicate external_video_id** — fileCreate already registers the video as a File, productCreateMedia then re-creates it with the same external id |
| `productCreateMedia(originalSource: resourceUrl)` after a prior `fileCreate` on same file | same duplicate error (fileCreate side-effect persists) |
| `productUpdateMedia` to attach | no-op — it only updates existing media |
| `CreateMediaInput` field `mediaType` | does not exist — it's **`mediaContentType`** |
| `ProductCreateMediaPayload.mediaErrors` | does not exist — it's **`media`** + **`userErrors`** |

So: **NEVER call fileCreate for product videos.** Staged → PUT → productCreateMedia(resourceUrl) is the entire pipeline. Resource URL comes from the stagedUploadsCreate response, not from any file create.

## 2. Homepage video hero (no theme validation pain)

Horizon `hero.liquid` supports `media_type_1: video` + `video_1` setting, BUT theme video settings rejected every URL form tried:
- `https://cdn.shopify.com/...mp4` → 422 "does not point to an applicable shopify-hosted video resource"
- `shopify://videos/<filename>` → "must be a valid video shopify url"
- `shopify://videos/<numeric id>` → same

**Workaround that always works: a `custom-liquid` section with raw `<video>` HTML** — no setting validation at all. Add to `templates/index.json`:

```json
"video_hero_xyz": {
  "type": "custom-liquid",
  "settings": {
    "custom_liquid": "<div ...video+overlay HTML...>",
    "section_width": "full-width",
    "padding-block-start": 0,
    "padding-block-end": 0
  }
}
```

- Custom-liquid setting key is **`custom_liquid`**, NOT `liquid` (silent no-render if wrong).
- CDN video URL: `https://cdn.shopify.com/videos/c/vp/<hash>/<hash>.HD-1080p-4.8Mbps-<n>.mp4` (from the staged video's `sources`).

**Overlap pitfall (real bug this session):** overlay text with `position:absolute` inside the section floats against the PAGE unless the wrapper has `position:relative` — text renders over the next section. Correct skeleton:

```html
<div style="position:relative;width:100%;background:#10182f;">
  <div style="position:relative;width:100%;aspect-ratio:16/9;max-height:82vh;overflow:hidden;">
    <video autoplay muted loop playsinline preload="metadata"
           style="position:absolute;top:0;left:0;width:100%;height:100%;object-fit:cover;">
      <source src="..." type="video/mp4">
    </video>
    <div style="position:absolute;bottom:0;left:0;right:0;padding:40px 5%;
                background:linear-gradient(transparent, rgba(16,24,47,0.92));text-align:center;">
      ...overlay text...
    </div>
  </div>
</div>
```

Also: when adding a video hero, **remove the old image `hero` section** from index.json — two heroes stack/overlap. Section order = `order` array in index.json; PUT the whole file back.

## 3. Ad photos / gallery images as theme assets

Staged-upload IMAGE resource PUT gave `SignatureDoesNotMatch 403` (VIDEO resource worked — image staging differs). **Theme assets route is simpler anyway:**

- `PUT /admin/api/2026-07/themes/{theme_id}/assets.json` `{asset: {key: "assets/<name>.jpg", value: <base64>}}` — works, no size drama.
- **Subfolders refused:** `assets/ads/foo.jpg` → 422 "Theme files may not be stored in subfolders". Flat `assets/` only.
- **public_url is NOT the themes URL:** `.../themes/{theme_id}/assets/<name>` 404s on CDN. Fetch the asset and use its `public_url`: `https://cdn.shopify.com/s/files/1/{shop}/{theme}/t/1/assets/<name>?v=<ts>` (note `t/1` — shop id appears split with slashes in the CDN path).
- Filenames with spaces (WhatsApp exports) must be `urllib.parse.quote()`-ed in API GET query params, and the public_url returned from the API already handles the CDN side.

## 4. Storefront render verification (text-first, no vision)

```python
html = urllib.request.urlopen('https://<store>.myshopify.com/').read().decode()
assert html.count('Luxe Wave Premium Amenities') == 1   # duplicates = overlapping sections
assert 't/1/assets/ad_' in html                          # gallery URLs present
# then HEAD/GET each CDN url -> expect 200 (not 404)
```
`<video>` tag may be `src=` OR nested `<source src=...>` — search both. User-reported "overlap" is often the leftover old hero section still in `order`.
