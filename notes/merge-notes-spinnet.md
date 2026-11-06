# Merge notes — track spinnet (desktop, branch `m3-spin-network`, milestones M3/M4)

For the laptop session merging this branch. Lists every shared-file append, every requested change to a laptop-owned file (with the exact diff), and the desktop environment.

## Environment (desktop)
- Activation: `source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding` (Python 3.12.16; qiskit 2.5.2, qiskit-aer 0.17.2, pygridsynth 1.2.0 `--no-deps`, numpy 2.5.2, scipy 1.18.0, sympy 1.14.0, pytest-xdist 3.8.0). The desktop's own env named `coding` is Python 3.14, so a separate env was made. Full log: `~/su2qc-sync/setup-log.md`.
- Lean: elan 4.2.4, toolchain v4.35.0, Mathlib from `lake exe cache get`.
- Clone: `~/Projects/su2qc-spinnet`; siblings under `~/Projects/siblings/<sibling>/` (plans' `/home/digimonk/Projects/<sibling>/` paths are read there).

## Resource split
20 logical cores, 31 GB RAM, RTX 3070 unused. This track: `taskset -c 0-9`, `pytest -n 10`, Lean builds under `taskset -c 0-9` (lake has no `-j`), `OMP/OPENBLAS/MKL_NUM_THREADS=1`, about 15 GB RAM.

## Baseline timings (fresh clone, before any change)
| Command | Result |
|---|---|
| `pytest --collect-only -q tests/acceptance` | 102 collected |
| `pytest -n 10 tests/unit` | 216 passed, 30.9 s (S) / 30.7 s (R) |
| `pytest -n 10 tests/acceptance/m0 tests/acceptance/m1` | 56 passed, 62.8 s (S) / 105.0 s (R, while Lean built on the other cores) |
| `python tools/check_lock.py && ~/.claude/bin/acceptance-check` | LOCK OK, PASS (acceptance-v6) |
| first `lake build` (spinnet; rishon reused the copied `.lake`) | 2 min 15 s, peak RSS 15.7 GB |

## Shared-file appends
(none yet)

## Requested changes to laptop-owned files
From `prompts/100-spinnet-m3-plan.md` §10 (not applied; M3 routes around 2; 1 and 3 are needed for M4):
1. `src/su2plaq/encodings/base.py`: add `NOMINAL_ANGLES["spinnet"] = (0.37, 0.61)` (used by `compress.spec.default_spec("spinnet", …)`).
   ```diff
   +    "spinnet": (0.37, 0.61),
   ```
2. `src/su2plaq/evaluate/evaluator.py::inner_target`: dispatch to `enc.inner_target(kind, alpha, beta, order)` when the encoding defines it.
   ```diff
    def inner_target(enc, kind, alpha, beta, order=1):
   +    if hasattr(enc, "inner_target"):
   +        return enc.inner_target(kind, alpha, beta, order)
   ```
3. `src/su2plaq/compress/baselines.py::import_seed`: add sources `"paulo15"` and `"spinnet_v2"` via `SpinNet.import_map` (M4 round-0 seeds).
