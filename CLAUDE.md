# su2qc-encoding — project notes for agents

Physics loop active (see `~/.claude/CLAUDE.md`). Plan in force: highest-numbered file in `prompts/` (now `prompts/002-m0-m2-foundation-twelve-qubit-compression.md`). Conventions: `docs/METHODS.md`. State: `notes/STATUS.md`.

## Environment and commands
```
source /home/digimonk/anaconda3/etc/profile.d/conda.sh && conda activate coding
cd /home/digimonk/Projects/su2qc-encoding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
pytest -n auto tests/unit                                  # FAST check after every edit
pytest -n auto -m "not slow" tests/acceptance/mN           # step acceptance (named ids: pytest ... -k <id>)
pytest -n auto tests/acceptance                            # FULL (milestone gate)
pytest --collect-only -q tests/acceptance                  # must stay clean
python tools/check_lock.py && ~/.claude/bin/acceptance-check
graphify update .                                          # after code changes
```
Versions: python 3.12, qiskit 2.5.2, qiskit-aer 0.17.2, pygridsynth 1.2.0 (never upgrade; reinstall with `--no-deps`), numpy 2.5.2, scipy 1.18, sympy 1.14, pytest-xdist 3.8.

## Layout
`src/su2plaq/` package (imported via `pythonpath = src`, no install); `tests/acceptance/` LOCKED (planner only); `tests/unit/` builder; `refs/` sources (Digonto's note + script, Paulo's files in `refs/paulo/`, Gu et al.); `results/` JSON with provenance; `compress/` loop data (programs, archive, briefs); `scratch/` gitignored.

## Benchmarks
Regression threshold 10 %. Benchmarked quantities: route-A build time, evaluator time per circuit, compression round wall time.
