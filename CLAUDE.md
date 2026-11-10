# su2qc-encoding — project notes for agents

Physics loop active (see `~/.claude/CLAUDE.md`). Plan in force: highest-numbered file in `prompts/` (now `prompts/002-m0-m2-foundation-twelve-qubit-compression.md`). Conventions: `docs/METHODS.md`. State: `notes/STATUS.md`.

## Environment and commands
```
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding
cd /home/digimonk/Projects/su2qc-encoding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
tools/pytest-safe -n 8 tests/unit                          # FAST check after every edit
tools/pytest-safe -n 8 -m "not slow" tests/acceptance/mN   # step acceptance (named ids: ... -k <id>)
tools/pytest-safe -n 8 tests/acceptance                    # FULL (milestone gate)
pytest --collect-only -q tests/acceptance                  # must stay clean
python tools/check_lock.py && ~/.claude/bin/acceptance-check
graphify update .                                          # after code changes
```
**Never run acceptance tests with bare `pytest -n auto`/`-n 16` on this machine (31 GiB RAM).** `tests/acceptance/m9/test_fuzzy_circuits.py::test_M9_S1_step_orders` builds a dense 65536² complex kron (69 GB; 137 GB for order 2) and is not marked slow; in parallel it filled RAM+swap and systemd-oomd killed the whole terminal incl. Claude Code (2026-11-09 23:50, 2026-11-10 12:17). `tools/pytest-safe` runs pytest in a capped systemd scope (22G, no swap, only the offending worker dies) and deselects that test (`PYTEST_BIGMEM=1` to keep it; large-memory host only). Every other acceptance test peaks ≤ 2.2 GB. Long jobs (compression rounds, Lean builds; Counts.lean ~15 GB) also belong under `systemd-run --user --scope -p MemoryMax=22G -p MemorySwapMax=0`.
Versions: python 3.12, qiskit 2.5.2, qiskit-aer 0.17.2, pygridsynth 1.2.0 (never upgrade; reinstall with `--no-deps`), numpy 2.5.2, scipy 1.18, sympy 1.14, pytest-xdist 3.8.

## Layout
`src/su2plaq/` package (imported via `pythonpath = src`, no install); `tests/acceptance/` LOCKED (planner only); `tests/unit/` builder; `refs/` sources (Digonto's note + script, Paulo's files in `refs/paulo/`, Gu et al.); `results/` JSON with provenance; `compress/` loop data (programs, archive, briefs); `scratch/` gitignored.

## Benchmarks
Regression threshold 10 %. Benchmarked quantities: route-A build time, evaluator time per circuit, compression round wall time.
