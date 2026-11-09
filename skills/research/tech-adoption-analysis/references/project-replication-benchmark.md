# Replication branch: "can we build this kind of thing?" (project posts)

Trigger: user shares a post/repo/link of a *finished project* (CV model, ML demo, SaaS clone)
and asks whether we can replicate it. Deliverable = verified recipe + measured proof + honest
blockers + cost, then one build offer.

## 1. Resolve the link to a primary source
`lnkd.in` does NOT emit a `Location` header to curl (even with browser UAs) — do not burn calls on it.
Go around it: search the post title/signature + keywords → find the GitHub repo / live demo.
Verify the repo via API, not the HTML page:
```bash
curl -s https://api.github.com/repos/<owner>/<repo> | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['created_at'], d['pushed_at'], d.get('license'), d['stargazers_count'], d['size'], d['description'])"
```
`license: None` = all-rights-reserved; flag it. `size` tells you whether weights/data are committed.

## 2. Read the recipe from primary artifacts (cheap, raw.githubusercontent)
`README.md`, the app file, and — the highest-value file — **`results*.csv`** (per-epoch metrics)
and the training notebook (`args.yaml` / `train(...)` call). Pull:
model + imgsz + epochs + batch + device, dataset source and licence, preprocessing (e.g. CLAHE),
and the **final-epoch P / R / mAP50 / mAP50-95** as the real quality claim. Marketing captions
("high accuracy") are usually mAP50 ≈ 0.75 — say the number.

## 3. Measure on THIS box (the decisive evidence)
Any "real-time / fast / lightweight" claim must be measured, never repeated.
```bash
python3 -m venv ~/<lab>/venv && cd ~/<lab>
# ARM/aarch64: plain `pip install ultralytics` drags CUDA nvidia-* wheels (GBs).
# Use the CPU index first, then ultralytics:
./venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
./venv/bin/pip install ultralytics
./venv/bin/pip install onnx onnxruntime streamlit   # as needed
curl -sL -o best.pt https://raw.githubusercontent.com/<owner>/<repo>/main/weights/best.pt
```
Then, in a small script: warm up, time 8–10 frames per imgsz (320/480/640), report ms → FPS,
export `model.export(format='onnx', imgsz=<sz>)` and re-time (ONNX RT is ~1.3–1.5x faster on CPU;
exported ONNX is fixed-shape, so export once per resolution — a 480 model will refuse 320).
Always include a **negative control** image (expect 0 detections) and a hard case to expose
false negatives. Save `res.plot()` outputs and view them with vision before claiming they work.

Reference numbers on the 2 vCPU Neoverse box: YOLO11n 320px = 68 ms torch / 43 ms ONNX (≈23 FPS),
640px = 204 / 155 ms (≈6 FPS).

## 4. Blockers to state honestly (in this order)
1. Licence: repo licence file, and the framework licence (Ultralytics = AGPL-3.0 → Enterprise
   licence for closed-source client delivery; Apache-2.0 alternatives: YOLOX, NanoDet, DETR).
2. Dataset licence (CC0/CC-BY = fine commercially; "research only" = not fine).
3. Leaked secrets in the source (public repos routinely commit SMTP app passwords — never copy
   the pattern; credentials come from env/vault).
4. Safety-critical domains (fire, medical, security): certified systems exist (NFPA 72 / EN 54) →
   position as supplementary early warning with a written disclaimer.
5. Hardware reality: CPU-only inference ≈ 1 camera stream per core at 320px; training must run
   off-box (free Kaggle T4 / HF Jobs) — the VM cannot train.

## 5. Build the cheap replica in the same session
Write our OWN app (no copied code, env-var credentials, logo-free demo imagery), run it on a local
port, screenshot it, and attach that plus the measured table. A running prototype beats any prose
verdict about feasibility.
