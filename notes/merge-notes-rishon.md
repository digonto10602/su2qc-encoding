# Merge notes — track rishon (desktop, branch `m5-rishon`, milestones M5/M6)

For the laptop session merging this branch. Lists every shared-file append, every requested change to a laptop-owned file (with the exact diff), and the desktop environment.

## Environment (desktop)
- Activation: `source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding` (Python 3.12.16; qiskit 2.5.2, qiskit-aer 0.17.2, pygridsynth 1.2.0 `--no-deps`, numpy 2.5.2, scipy 1.18.0, sympy 1.14.0, pytest-xdist 3.8.0). The desktop's own env named `coding` is Python 3.14, so a separate env was made. Full log: `~/su2qc-sync/setup-log.md`.
- Lean: elan 4.2.4, toolchain v4.35.0, Mathlib from `lake exe cache get`.
- Clone: `~/Projects/su2qc-rishon`; siblings under `~/Projects/siblings/<sibling>/` (plans' `/home/digimonk/Projects/<sibling>/` paths are read there).

## Resource split
20 logical cores, 31 GB RAM, RTX 3070 unused. This track: `taskset -c 10-19`, `pytest -n 10`, Lean builds under `taskset -c 10-19` (lake has no `-j`), `OMP/OPENBLAS/MKL_NUM_THREADS=1`, about 15 GB RAM.

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
From the planner (prompts/200, reports/research/200):
1. Per-circuit Lean checker (`Su2PlaqCert`, laptop steps 2.L4+): please accept a **third base angle** $e^{i\sqrt2\beta}$. The rishon $U_B$ contains the rotation angle $8\sqrt2\beta$ (the bright-pair coupling $4\sqrt2$ is intrinsic to the model), so without it $U_B$ and the step are reported `Lean: n_a`.
2. New file outside the track's Lean folders: `lean/certs/rishon-hb-structure.lean` (native_decide structure certificate, prompts/006 folder rule for native certificates). Will be listed under shared-file appends when created.

## Model decisions taken without Digonto (default; flagged for review)
- SU(2) quantum link model with two fermionic rishons per link; SU(2) Gauss law only; **det coupling $\gamma=0$** (defined, not built). With $\gamma=0$ the U(1) charges are conserved (431 sectors; the U(2)-QLM sector has 2192 states). Adding the det term would be a third Trotter layer = a plan amendment.
- Register 48 qubits (16 inert far-end qubits kept); the 36-qubit codeword variant is a register-size row only.
