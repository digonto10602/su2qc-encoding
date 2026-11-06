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
- `lean/Su2Plaq.lean`: two lines appended (step 3.L1/3.L2, commit after reports/tests/105):
  ```
  import Su2Plaq.SpinNet.Counts
  import Su2Plaq.SpinNet.Circuit
  ```
- `lean/Su2Plaq.lean`: one more line appended (prompts/102 W4, reports/tests/107): `import Su2Plaq.SpinNet.Bridge` (pulls in SpinNet.Recoupling, Semantics, Spectrum; all Mathlib-free except Bridge).

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

## Observations on laptop-owned code
- `tests/unit/test_results_unit.py::test_render_is_deterministic_and_contains_only_json_numbers` asserts `"c1" not in t_noq`, but the rendered table contains the git short hash; it fails whenever the hash contains "c1" (seen with `bd37c15`). Suggested fix: strip the commit field before the check, or test for `"| c1 "`.

## Audit notes on laptop-owned code (reports/audits/100)
- N3 (evaluator, laptop-owned): the span leak (amplitude left on valid-but-inadmissible codes) is not included in `op_norm_error`. For the spin-network encoding it is exactly computable: $3.15\cdot10^{-7}$ for synthesised $U_E$ and step at $\varepsilon=10^{-6}$. True totals stay inside the budget ($U_E$: $2.50\cdot10^{-6}\le4.0\cdot10^{-6}$), but the reported error is 13–15 % low, and the Gauss-based span-leak bound alone ($4.41\cdot10^{-6}$) would not certify $U_E$ at $10^{-6}$. Suggest: add the exact span leak to `op_norm_error` when the encoding can compute it (relates to audit 002 R1).

## Tag-name clash warning
Both desktop clones and the laptop create `acceptance-vN` tags independently (both desktop clones started at acceptance-v6 → each made its own acceptance-v7; rishon also acceptance-v8). The outgoing bundles carry only the branch and the `milestone-N` tag, not the `acceptance-v*` tags, so nothing collides on fetch. At merge time, re-lock with `tools/lock.py` and create the next `acceptance-vN` on the merged master.
