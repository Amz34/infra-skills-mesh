# Reference-agent lanes — R9b evidence, measured 2026-09-18

An **import probe (R9a) is not a delivery**. This file is how the second half of R9 was built:
one reference agent per framework lane that actually runs, writing a hash-bound run log the gate reads.

## Why it exists (the measurement that forced it)

`llama_index` imported cleanly (`import OK`, version 0.14.24) and then **died on its first
`agent.run()`**. If an offer had been sold on "the lane is ready" from the import probe alone, the
deliverable would have been broken on arrival. So a lane is only a lane once an agent has **run** in
it, and the gate now requires both halves.

## The three lanes, as measured

| Lane | Framework (ver) | Reference agent does | Run |
|---|---|---|---|
| `smolagents` | smolagents 1.26.0 | multi-step agent, 2 tools; reads `offers.json` + disk probe | 4 steps / 141 s |
| `llamaindex` | llama-index 0.14.24 | RAG (bge-m3 embeddings over a local note) + function tool | 382 s |
| `langgraph` | langgraph 1.2.11 | 3-node graph + conditional edge; audits the gate report | 9.5 s |

Model for all three: **local `qwen2.5:3b` via Ollama** → API cost ~0 for reference runs. The box has
no GPU; keep-capacity accounting separate (R5 / R10).

Combined framework RSS: ~52.2 MB (the frameworks are cheap; the **models** are the memory).

## Run-log schema (`reference/logs/<lane>.json`)

Written by the reference script itself; `verify_reference.py` reads it and fails closed.

```
lane, framework, model, ran_at, elapsed_s, exit_code, output (the real answer),
script, script_sha256, local_only: true, role: "reference agent", workarounds: [...]
```

`verify_reference.py` checks: sha on disk == sha in log, exit 0, non-empty output, age, and that the
run did not claim an external/paid call. A **tampered** log must fail (`selftest-ref-tampered.json`).

## Trap 1 — `pip install workflows` shadows the real package

`llama-index-workflows` imports as `workflows`. There is an unrelated PyPI distribution literally
named **`workflows`** (Diamond Light Source). Installing it (e.g. from a careless
`pip install -U workflows`) **shadows the runtime** → the llama-index agent breaks with confusing
import/attribute errors. Fix: `pip uninstall -y workflows`, restore `llama-index-core`; keep a
layer-3 check that the wrong dist is absent from the venv.

## Trap 2 — `FunctionAgent` is unhashable (`TypeError: unhashable type`)

llama-index's `FunctionAgent` is a pydantic model with `__hash__ = None`, while the workflows runtime
stores it in a `WeakKeyDictionary` → every `agent.run()` raises `TypeError: unhashable type:
'FunctionAgent'`. Confirmed by minimal repro (`hash before: None`). Fix in the reference script:

```python
FunctionAgent.__hash__ = object.__hash__   # identity hashing; run log records it as a 'workaround'
```

The monkey-patch lives in the reference script and the fact is **recorded in the run log's output** —
evidence surfaced, never hidden. Debug path that worked: minimal repro file first
(`weakref ok` / `hash before` / `hash after`), then patch the reference agent, then re-run.

## Operating rules that came out of running them

- **Pre-warm the model** (`keep_alive` on the first call) or the first run's timing is dominated by
  load, not by the agent.
- **Unload after**: runs pin ~2.6 GB; `reference/unload_models.py` (`keep_alive=0`) returns the box to
  baseline (`ollama ps` empty). `RESERVED_LOCAL_MODELS_MB = 2600` in the gate's R5 cap accounts for a
  run being in flight.
- **Never let a live run change a verdict** — that is exactly why R5 is plan-based and live free RAM
  is only the R5b advisory line.
- **Reference-grade ≠ client-grade.** These prove the lane executes on our own box with our own data.
  They do **not** prove a client deliverable. Keep that in the write-up's non-claims section.

## Adding a new lane (checklist)

1. `pip install <framework>` in the `~/agentlab` venv; record version.
2. Write `reference/ref_<framework>.py` that does real work on real local artifacts (not `print("ok")`).
3. Pre-warm the model, run it, fix whatever the run exposes (expect at least one real trap).
4. Confirm `reference/logs/<framework>.json` has a matching `script_sha256`; run
   `verify_reference.py` → lane count up by one.
5. Add the lane + probe command to `frameworks.json` (R9a command **and** R9b requirement).
6. Add a layer-3 check for the lane; run `unload_models.py`; re-run `run_all.sh`.
