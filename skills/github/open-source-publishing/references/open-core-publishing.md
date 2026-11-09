# Open-core publishing — worked example & licence reasoning

Session: 2026-09-13, product **Fire & Smoke Watch** (mobile-camera fire/smoke
detector + email alerts). Public repo: `github.com/Amz34/fire-smoke-watch`
(Apache-2.0). Private layer stayed in `~/fire-lab`.

## 1. The split that was actually shipped

Public (`~/fire-lab-public`, 14 tracked files, separate git repo):

| Path | Purpose |
|---|---|
| `firewatch/__init__.py`, `firewatch/detector.py` | runtime: onnxruntime + opencv + numpy only |
| `examples/detect_image.py` | one runnable example, `--json` output |
| `bench/bench_onnx.py`, `bench/RESULTS.md`, `bench/results.json` | measured numbers + the harness that made them |
| `kaggle/train_firewatch.ipynb` | training recipe (AGPL-aware note inside) |
| `demo/firewatch_demo_9x16.mp4`, `demo/console.png` | launch media |
| `README.md`, `LICENSES.md`, `LICENSE`, `requirements.txt`, `.gitignore` | |

Private (never in the public repo): FastAPI console/server, alert engine
(3-confirm policy, cooldown, evidence JPEG), browser E2E tooling, multi-camera,
reports, and **all weights** (`best.pt`, `best_{320,480,640}.onnx`).

Design rule that made the runtime defensible: **inference deliberately
framework-free** — `onnxruntime` + `opencv` + `numpy`, no Ultralytics runtime
import. The notebook is the only AGPL-touching artefact and says so.

## 2. Licence map (`LICENSES.md`)

- Repo code: Apache-2.0.
- **Weights: NOT redistributed.** The checkpoint came from a third-party repo
  with no LICENSE file → publishing it would be unlicensed redistribution.
  `.gitignore` blocks `*.onnx` / `*.pt` so it cannot be committed by accident.
- Ultralytics position (checked 2026-09-13): training code AND the resulting
  models are AGPL-3.0; commercial/closed/SaaS/hardware use needs an Enterprise
  licence even if you train from scratch. Consequence: to sell this
  closed-source, either buy Enterprise or move the detector to an Apache/MIT
  stack (RT-DETR official repo, YOLOX, NanoDet, torchvision detectors).
- AGPL is **irreversible**: whatever ships AGPL today is AGPL forever. Draw the
  line before the first push, not after.
- Honest disclaimer in README: supplementary early warning, NOT a certified
  fire alarm (NFPA 72 / EN 54 / Saudi Civil Defense approvals still required).

## 3. Benchmark that a stranger can trust

- Machine stated in `RESULTS.md`: Oracle Cloud Always Free Ampere A1, aarch64,
  2 vCPU Neoverse-N1, **no GPU** — so CPU-only numbers are the honest floor.
- Harness reads the input size **from the ONNX file itself**
  (`--pattern "$HOME/fire-lab/best_{imgsz}.onnx"`), so a renamed file cannot
  silently benchmark the wrong resolution.
- A bad model path must fail loudly (`cannot determine the input size of …`),
  never silently pass with default shapes.
- Numbers reported are medians of N runs, e.g. 320/480/640 px. When a later
  re-run on a loaded VM showed 223 ms vs the published 97 ms, the *published*
  figures stayed as-is and the contention was disclosed in the reply — do not
  silently swap in a number from a busy machine.

Consumer contract of `examples/detect_image.py --json` (document it with a real
example in the README, and assert exactly this in any verifier):

```json
{"image": "...", "imgsz": 480, "latency_ms": 12.3,
 "detections": [{"cls_id": 0, "name": "Smoke", "conf": 0.79, "xyxy": [x1,y1,x2,y2]}]}
```

`xyxy` is in **original-image pixels**, not model-input pixels.

## 4. Incidents worth remembering

- **LICENSE first line blank → GitHub reported `license: none`.** `head -3
  LICENSE | cat -A` showed `^$` on line 1. Fixed with `lstrip("\n")`, re-pushed,
  then confirmed `gh api repos/.../license --jq .license.spdx_id` = `Apache-2.0`.
- **Raw CDN served stale README for minutes after a good push** (grep count 0 on
  raw, blob SHA matched the commit). No action was needed; re-querying the
  contents API proved the push landed.
- **Demo clip leaked the operator's email** in a footer strip. Fix was to
  re-record/recut from the private master with the footer cropped out
  (recut script kept in the PRIVATE repo, `tools/make_public_demo.py`) — never
  publish the original capture and never publish the recut script if it embeds
  private paths.
- **Verifier false failure**: the duration-cap regression check ran against a
  legacy internal clip on disk. A verifier must assert on the artefact the tool
  PRODUCES (the published clip), not on any stale file that happens to match the
  glob.

## 5. Verifier design (ad-hoc, no test runner in the repo)

The public repo has no test suite, so verification was a throwaway script
(`/tmp/hermes-verify-<topic>.py`, deleted after the run; a permanent copy lives
in the private repo's `tools/`) that drives the repo's REAL CLIs and asserts on
their real output:

1. package imports + exported class surface
2. `examples/detect_image.py` → exit 0, annotated image written, JSON envelope
   keys and per-detection keys
3. `bench/bench_onnx.py` both modes + the load-bearing failure case
4. `.gitignore` actually ignores weights/secrets (`git check-ignore`) and no
   weight file is tracked
5. demo clip duration capped (regression on the ffmpeg loop bug)
6. media-redaction code path present (crop constant + duration cap)

Report it to the user as **ad-hoc verification, not "the suite is green"** — the
distinction matters and the user reads the difference.
