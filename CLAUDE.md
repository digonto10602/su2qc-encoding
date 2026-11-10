# su2qc-encoding — project notes for agents

Physics loop active (see `~/.claude/CLAUDE.md`). Plans in force: one per track, by number range (twelve 000–099, spinnet 100–199, rishon 200–299, fuzzy 300–399, LSH 400–499) — see the table in `notes/STATUS.md`. Conventions: `docs/METHODS.md`. State: `notes/STATUS.md`.

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
**Never run acceptance tests with bare `pytest -n auto`/`-n 16` on this machine (omnicommander = the former supremecommander desktop, fresh Omarchy install; 20 cores, 31 GiB RAM).** Cause of the 2026-11-09/10 crashes: m9 `test_M9_S1_step_orders` built a dense 65536² complex kron (69–137 GB), filled RAM+swap, and systemd-oomd killed the terminal incl. Claude Code; fixed by prompts/007 (acceptance-v15, 2.0 GB). `tools/pytest-safe` and `tools/run-capped <cmd>` run jobs inside the shared `su2qc.slice` (`~/.config/systemd/user/su2qc.slice`: 24G total, no swap; OOMPolicy=continue), so a runaway job loses one worker, never the session. All acceptance tests peak ≤ 2.2 GB. Long jobs (compression rounds, evaluator, Lean builds; Counts.lean ~15 GB) go through `tools/run-capped`. Do not run GParted while jobs run (it crashed the kernel on 2026-11-10 13:48).
Versions: python 3.12, qiskit 2.5.2, qiskit-aer 0.17.2, pygridsynth 1.2.0 (never upgrade; reinstall with `--no-deps`), numpy 2.5.2, scipy 1.18, sympy 1.14, pytest-xdist 3.8.

## Layout
`src/su2plaq/` package (imported via `pythonpath = src`, no install); `tests/acceptance/` LOCKED (planner only); `tests/unit/` builder; `refs/` sources (Digonto's note + script, Paulo's files in `refs/paulo/`, Gu et al.); `results/` JSON with provenance; `compress/` loop data (programs, archive, briefs); `scratch/` gitignored.

## Benchmarks
Regression threshold 10 %. Benchmarked quantities: route-A build time, evaluator time per circuit, compression round wall time.
