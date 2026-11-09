# Ad-hoc verification harness — design notes

Evidence base: fire-lab YOLOX/ONNX export + demo QA pass, 19-Sep-2026. The ad-hoc
script under `$TMPDIR` (created via `tempfile.mkstemp(prefix='hermes-verify-', suffix='.py')`)
ran 20+/20 across several revisions — but not before it lied four times.

## 1. Every FAIL was the harness, not the product

| Assertion as written | Why it could never pass | Product truth (verified by hand) |
|---|---|---|
| `rc != 0 and "playwright" in out and "Traceback" in out` | The tool prints *friendly guidance* for the wrong interpreter — guidance and traceback are mutually exclusive | `rc=1`, clean guidance, `grep -c Traceback` → 0 |
| `made.is_file() and not (Path.cwd() / rel).exists()` | The script ran with `cwd` = repo root, and `made` lived under exactly that path | File was where it belonged; the assertion required it to be absent |
| `"(1, 6, 6300)" in out` for `--sizes 320` | 6300 is the **640px** anchor count (80²+40²+20²), copied from the incumbent run | `(1, 6, 2100)` = 40²+20²+10² at 320px |
| `s == (1, 6, 64)` for a *default* checkpoint | Read the tool's `(B, 4+nc, N)` tuple as if `N` were the class count | `(1, 6, 84)` = 4+2 channels, 84 anchors at 64px — both correct |

**Rule:** triage product-vs-harness by hand *before* editing product code. For each FAIL,
run the exact failing command yourself and read rc + output + artifacts.

**Rule:** compute expectations from the code under test; never paste a literal from a
previous run. Anchor count for YOLOX-style multi-stride heads:
`sum((size // s) ** 2 for s in (8, 16, 32))` (40²+20²+10² = 2100 @320; 80²+40²+20² = 6300 @640).

## 2. A relative-path check needs a foreign cwd

`--outdir` resolving "against the repo root and not the cwd" is untestable while
`cwd == repo root`. Run the CLI from a scratch dir and assert the artifacts landed
under ROOT *and* that `scratch/<rel>` was never created.

## 3. Cheap permanent regression (pin ordering, not the work)

The real bug: the exporter traced the whole model, then died on a raw
`FileNotFoundError` writing the `.data` sidecar — `--outdir` was never created.

```python
# ~5s, no export at all: a MISSING checkpoint still creates the destination,
# which can only be true if mkdir happens BEFORE the build/export.
p = subprocess.run([VENV, "tools/export_yolox_sizes.py",
                    "--ckpt", str(tmp_path / "absent.pth"),
                    "--sizes", "64", "--outdir", str(nested)], capture_output=True, text=True)
assert p.returncode != 0          # fails loudly
assert nested.is_dir()            # ...but only after setting up its destination
```

Mutation-test it: comment out the `mkdir`, rerun — 2 of 3 tests must go red. Then
restore by copy, `grep -c MUTATION <file>` → 0, `git diff --stat` shows only the
intended change.

## 4. Legible failure beats a raw traceback

Same principle that added guidance to `demo_web_qa.py` (repo-venv run explains itself
instead of raising `ImportError`). In `main()`, after the mkdir:

```python
if not a.ckpt.is_file():
    print(f"[FAIL] no checkpoint at {a.ckpt}", file=sys.stderr)
    return 1
```

Also: a test that demands a *pristine* checkout fails in a dirty tree — baseline what
you touch (`head_before` / `branch_before`) instead of demanding cleanliness.

## 5. torch.onnx opset is not what you ask for

Requesting `opset_version=12` on current torch emits **18** (no back-emit path) and only
warns — the model keeps working. So make the exporter *report* the opset it produced
alongside the shapes, and assert **parity with what already ships** rather than a target
number. Here the incumbents were already opset 18 and the page loads
`onnxruntime-web 1.20.1`, so opset 18 is proven-loadable; the `Failed to convert
model_version=12` noise is harmless.
