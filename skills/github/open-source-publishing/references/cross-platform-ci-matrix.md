# Cross-platform CI matrix (linux / macos / windows)

Widening a Python repo's CI from one runner to an OS × Python matrix is the cheapest way to find
real portability bugs, because every `/proc`, `statvfs`, `getloadavg`-style assumption fails on
exactly one runner. Expect the first matrix run to be red; that red is the value, not a mistake.
Proven 2026-09 on `Amz34/agent-operating-model` (3 bugs found, all real).

## Workflow

```yaml
strategy:
  fail-fast: false        # one OS failing must not cancel its siblings
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python-version: ["3.11", "3.12"]
```

- `fail-fast: false` — with the default, the first red job cancels the others and you lose the
  evidence from the platforms you added the matrix for.
- Carry the matrix values into the job name (`test (${{ matrix.os }} / ${{ matrix.python-version }})`)
  so `gh run view <id> --json jobs` reads like a coverage table.
- Prefer adding the matrix before the first push; otherwise accept one red run, fix the cause, then
  delete that run from the Actions tab (`references/ci-proof-and-publish-hygiene.md`).
- Read jobs individually after a fix — a partly-green run still looks green in some views:
  `gh run view <id> --json jobs -q '.jobs[] | "\(.name) -> \(.conclusion)"'`.

## The three bugs a 3-OS matrix actually found

1. **Windows: `os.statvfs` does not exist** — it raises `AttributeError`, not `OSError`.

```python
disk_total, disk_used = 0.0, 0.0
try:                       # statvfs is POSIX-only and Windows has no /proc either
    st = os.statvfs("/")
    disk_total = st.f_blocks * st.f_frsize / 2**30
    disk_used = (st.f_blocks - st.f_bfree) * st.f_frsize / 2**30
except (AttributeError, OSError):
    try:
        usage = shutil.disk_usage(os.path.abspath(os.sep))
        disk_total, disk_used = usage.total / 2**30, usage.used / 2**30
    except OSError:
        pass
```

2. **macOS: `/proc`-derived metrics are `None`, and `None` poisons aggregation.**
   `sum()`/`max()` over a list containing `None` raises
   `TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'` — inside a rollup, i.e. the
   crash surfaces far from the collector that produced the gap. Fix at the boundary and keep the
   absence visible:

```python
def _num(value):
    """Metrics are missing on platforms without /proc; that must never become a crash."""
    return value if isinstance(value, (int, float)) else None


def _spread(values):
    seen = [v for v in values if v is not None]
    if not seen:
        return {"max": None, "avg": None}     # report the gap, do not invent a 0
    return {"max": max(seen), "avg": round(sum(seen) / len(seen), 2)}
```

   Trap: `record.get(key, {}).get("used_pct", 0)` — a key that *exists* with value `None` returns
   `None`, never the default. Guard at read time, not with a `.get` default.

3. **Schema/type tests: `None` is `"null"`, not `"NoneType"`.** A test comparing
   `type(value).__name__` against JSON-schema type names passes on Linux and fails only where the
   metric is missing:

```python
def _kind(value):
    return "null" if value is None else type(value).__name__
```

## Rules for the Linux-only parts

- Mark `/proc`-dependent tests instead of deleting them:
  `LINUX = pytest.mark.skipif(sys.platform != "linux", reason="reads /proc, Linux only")`.
- Relax range assertions to admit absence: `pct is None or 0 <= pct <= 100` — a Windows reader
  should see "not available", not a fabricated 0.
- Keep the package importable everywhere: `requires-python` matching the syntax actually used, no
  platform-specific hard dependencies, and `console_scripts` entry points that do not crash on
  Windows (a crashing entry point is a portability bug shipped as a feature).
- Then re-run locally (the Linux path) AND read the matrix jobs — do not declare victory from a
  local green.

## Screenshot it

The matrix run is the strongest single proof asset in a README: OS names, job names, green ticks.
Refresh the capture whenever jobs are added (SKILL.md §10(b)).
