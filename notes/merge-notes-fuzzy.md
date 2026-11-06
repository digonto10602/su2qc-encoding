# Merge notes — branch m9-fuzzy (fuzzy encoding, 48-core machine)

Base: master 9b5443d. Numbers: prompts/reports 300+.

## Environment / activation
```
source ~/venvs/coding/bin/activate     # uv-made venv, CPython 3.12.14 (no conda on this host)
source ~/.elan/env; export PATH=$HOME/tools/gitenv/bin:$PATH   # git 2.56 needed by lake (system git 2.25 lacks --filter)
cd ~/Projects/su2qc-fuzzy
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
```
- env/requirements-coding.txt has 139 `pkg @ file:///home/conda/...` lines (conda-built); installed those unpinned from PyPI. Pinned core versions verified: qiskit 2.5.2, qiskit-aer 0.17.2, pygridsynth 1.2.0, numpy 2.5.4, scipy 1.18.1.
- Package installed editable (`uv pip install --no-deps -e .`).
- `lake build -j 24` is not accepted by this lake (unknown option -j); used `LEAN_NUM_THREADS=24 lake build`.

## Shared-file appends (to merge by hand)
(none yet)

## Laptop-owned files that would need changes (diffs)
(none yet)

## Other
- notes/STATUS.md on this branch is the fuzzy session's; the laptop's copy at branch point is preserved as notes/STATUS-laptop-at-branch-point.md (drop on merge).
