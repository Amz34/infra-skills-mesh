# Downloading client files from Google Drive share links (reliable recipe)

Validated Aug 2026 on the Oracle VM (AVVS Triatek intake, 39.6MB zip).

## Symptom
`curl -L "https://drive.google.com/uc?export=download&id=FILE_ID"` returns a
small HTML file titled **"Google Drive - Virus scan warning"** for large
files. `file out.zip` says `HTML document`, not a zip.

## Fix: gdown (handles the confirm token automatically)
```bash
python3 -m venv /tmp/gdvenv                      # VM is PEP 668 — venv required
/tmp/gdvenv/bin/pip install -q gdown
/tmp/gdvenv/bin/gdown "https://drive.google.com/file/d/<FILE_ID>/view" -O file.zip
```

## Link-shape pitfalls
- Real share link: `https://drive.google.com/file/d/<ID>/view?usp=sharing`
- Folder: `https://drive.google.com/drive/folders/<ID>?usp=sharing`
- **Gmail proxy lookalike:** `https://ci3.googleusercontent.com/meips/...`
  — that's an icon/image URL from inside an email, NOT the file. Ask for the
  real `drive.google.com/file/d/...` link.
- Without **"Anyone with the link"** permission, gdown/curl fail (file
  not-found / permission page). Ask the user to set Share → Viewer for anyone.

## Extract (unzip binary is often missing on the VM)
```bash
python3 -c "import zipfile; zipfile.ZipFile('file.zip').extractall('extracted')"
```

## Verify
`file downloaded.zip` → must say Zip/PDF, not HTML. Then list contents with
`find extracted -type f` and inventory: PDFs, video, images, CSVs.
