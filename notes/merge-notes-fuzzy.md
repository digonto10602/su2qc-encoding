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
- `lean/Su2Plaq.lean`: appended `import Su2Plaq.Fuzzy.Counts` and `import Su2Plaq.Fuzzy.Link`.
- `tests/acceptance/LOCK.json`: m9 added via `python tools/lock.py m9` (acceptance-v8); then hashes of m9/test_fuzzy_circuits.py and m9/test_fuzzy_observables.py updated BY HAND (tools/lock.py refuses re-lock) after Digonto approved prompts/301 (acceptance-v9; v10 = same content, JSON indent restored to 1). Tags acceptance-v8..v10 exist on this branch only — they will collide with laptop/desktop acceptance-vN numbering: rename on merge (e.g. acceptance-fuzzy-v8..v10).
- Lean `Su2Plaq/Fuzzy/Link.lean` takes ~6 min to build (kernel decide on 16x16 Gaussian-integer matrices).

## Laptop-owned files that would need changes (diffs)
(none yet)

## Other
- notes/STATUS.md on this branch is the fuzzy session's; the laptop's copy at branch point is preserved as notes/STATUS-laptop-at-branch-point.md (drop on merge).
- Repo-local git identity set to master's author (pichka_commander <mdhabibeislam.digonto@gmail.com>); host had no global git identity.
- Digonto's uploaded `fuzzy-hamiltonian.pdf` saved as refs/fuzzy/fuzzy-hamiltonian-digonto.pdf; being checked against the paper/plan before the planner run.
