# Client Media Intake → Shopify Product Photos

Workflow for taking a client's media delivery (zip/Drive folder) and turning it into
high-quality product images on a Shopify store. Validated 2026-08-22 on Luxewave.

## Step 0 — Locate the file

- Check local inbox FIRST: `~/clients/<name>/inbox/` — the "55MB file" the user mentions
  is often already on the VM from an earlier upload. `find /home/ubuntu -maxdepth 4
  \( -iname "*.zip" -o -iname "*.mp4" -o -iname "*.mov" \) -size +1M -newermt "<date>"`.
- If it's a Drive link: `gdown --folder <url>` in an empty dir. **401 = folder private**
  → ask user to flip sharing to "Anyone with the link" OR upload to the chat directly
  (chat upload is fastest, no auth issues). rclone token may be expired — check
  `rclone config show` before relying on it.

## Step 1 — Inventory the zip

```bash
unzip -l file.zip            # list contents — are there standalone photos or just PDFs?
```

Typical client delivery: **PDFs only** (catalogue, price list, company profile, brochures)
+ logo files. Real product photos are usually embedded INSIDE the catalogue PDF, not
loose files.

## Step 2 — Extract from the catalogue PDF

poppler-utils (`pdfimages`, `pdftoppm`) — install once with `sudo apt-get install -y poppler-utils`.

```bash
mkdir -p media/raw && cd media/raw
pdfimages -all "Catalogue.pdf" cat        # dumps EVERY embedded image
# → usually 400-500 files, but mostly 1-8KB THUMBNAILS (icons, textures) — low-res, useless for hero shots

pdftoppm -jpeg -r 150 -f 1 -l N "Catalogue.pdf" page   # render full pages instead
# → ~1772x1182 px per page at 150dpi — usable source for cropping product shots
# bump to -r 300 for ~3500px if the PDF holds vector/high-res artwork
```

**Pitfall — catalogue may be a DESIGN GUIDE, not photo source:** Luxewave's "Catalogue
for private label.pdf" was bottle shapes + SKU codes + spec text (OCR'd via tesseract),
NOT real product photographs. `pdfimages` gave 511 tiny images; page renders gave the
usable layout. If the catalogue has no real product shots, the honest answer to the
client is: **original high-res photos needed** (Drive/chat) — generated tiles are a
stopgap, not a substitute.

## Step 3 — Check what's currently on the store

```bash
# products.json → for each product: len(images), images[0].src
```

- 0 images = never uploaded.
- Images whose src/filename looks like `tile`/`coll-`/generated = placeholders live,
  real photos never made it → this is what "product photos sahi add nahi hue" means.

## Step 4 — Polish & upload

- Polish: PIL batch — clean/white luxury background, consistent canvas size, brand
  colors (navy/gold), no faces (client rule). See `admin-api-store-build.md` for the
  tile-generator pattern.
- Upload: `POST /products/{id}/images.json` with `{image: {attachment: <base64>,
  filename, position}}` — **works for multi-MB files**, no 2048-char cap (that's only
  GraphQL fileCreate). 2-4 images per product = gallery. `position` controls order.
- Videos: portrait 10s MP4s are typical from clients — hero video section on homepage
  + per-product via media API; poster frame required.

## Session-specific evidence (Luxewave 2026-08-22)

- Zip: `~/clients/luxewave/inbox/Shopify-Luxewave.zip` (24MB: catalogue PDF, price list,
  logos, company profile, magazines — NO standalone product photos).
- `pdfimages -all` → 511 files, ~1-8KB each; page renders at 150dpi → 1772x1182 usable.
- Store had 33 products × 1 tile image (navy/gold generated tiles) — real photos never
  added, matching user's complaint.
- Drive folder `11n2oHfY_Vhg9MvuiYxVuAHA3sGATbijM` = PRIVATE (gdown 401); rclone token
  expired → user asked to share publicly or upload via chat.
