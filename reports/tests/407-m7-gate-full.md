# Tester report 407: M7 gate step 1 (mode full)

- Date: 2026-11-12 (runs started 2026-11-11 evening). Git: `f8cc138` (HEAD). The working tree also holds other agents' uncommitted fuzzy_ub files, `scripts/m4_results.py` and `tests/unit/test_spinnet_m4_results_unit.py` (not mine; the unit run included them).
- Plan in force: `prompts/400` (LSH M7); acceptance lock acceptance-v18. Mode: full, milestone gate step 1. Cores 14-19, `-n 6`.
- Related reports: 400-403, 406 (LSH), 404 (M4 gate). Raw numbers: `results/lsh_tester/tester-407-gate.json`; logs in `scratch/tester-m7gate/`.

## Verdict: PASS

0 failed, 0 pending, 0 skipped/xfailed anywhere. No new failures vs. report 406 (the unit count is 934 vs 932 there: two tests added by another agent in the working tree).

## Commands (all from the project root, env `OMP/OPENBLAS/MKL_NUM_THREADS=1`)

```
cd lean && PER_JOB_MEM=16G ../tools/run-capped taskset -c 14-19 lake build Su2Plaq Su2PlaqCert su2plaq_cert_lsh su2plaq_cert_spinnet
taskset -c 14-19 tools/pytest-safe -n 6 -q tests/acceptance/<m>     # m7 m0 m1 m3 m3x m4 m2 (no marker filter: slow included)
taskset -c 14-19 tools/pytest-safe -n 6 -q tests/unit
pytest --collect-only -q tests/acceptance; python tools/check_lock.py; ~/.claude/bin/acceptance-check
PYTHONPATH=src taskset -c 14-19 tools/run-capped python scripts/m7_results.py --out scratch/tester-m7gate/regen
```
The test scripts ran sequentially, one `pytest-safe` after another (`scratch/tester-m7gate/run.sh`).

## Results table

| Check | Expected | Got | Tolerance | Result |
|---|---|---|---|---|
| `lake build Su2Plaq Su2PlaqCert su2plaq_cert_lsh su2plaq_cert_spinnet` | builds | "Build completed successfully (9128 jobs)", 3 s (all up to date), 0 lines containing "error" | - | PASS |
| `tests/acceptance/m7` (incl. L1-L3 Lean) | all pass | 29 passed, 10.6 s | - | PASS |
| `tests/acceptance/m0` | all pass | 34 passed, 18.2 s | - | PASS |
| `tests/acceptance/m1` (incl. slow) | all pass | 22 passed, 95.5 s | - | PASS |
| `tests/acceptance/m2` (incl. slow) | all pass | 46 passed, 172.4 s | - | PASS |
| `tests/acceptance/m3` | all pass | 24 passed, 10.8 s | - | PASS |
| `tests/acceptance/m3x` | all pass | 4 passed, 6.8 s | - | PASS |
| `tests/acceptance/m4` | all pass | 19 passed, 43.8 s | - | PASS |
| `tests/unit` | all pass | 934 passed, 355 s | - | PASS |
| acceptance total (m0+m1+m2+m3+m3x+m4+m7) | - | 178 passed / 0 failed | - | PASS |
| `pytest --collect-only -q tests/acceptance` | clean | 341 tests collected, no errors | - | PASS |
| `tools/check_lock.py` | LOCK OK | `LOCK OK` | - | PASS |
| `~/.claude/bin/acceptance-check` | PASS | `PASS: tests/acceptance matches acceptance-v18` (latest tag acceptance-v18) | - | PASS |

m2c, m5, m5x, m6, m9, m10 are outside the gate scope and were not run here (m2c is PENDING by design until the consolidation Phase B).

## Provenance of `results/lsh/{UE,UB,step}.json`

- Provenance block of all three: `git_commit` = `3d99f68`, `git_dirty` = False, host omnicommander, command `python scripts/m7_results.py`, seeds `transpiler_logical` 20261104, `trial_subset` 0, wall 8.07 s, peak RSS 281 MB, numpy 2.5.4, scipy 1.18.1, qiskit 2.5.2, pygridsynth 1.2.0.
- Files changed since `3d99f68` (`git diff 3d99f68 HEAD --stat -- src scripts/m7_results.py`): only `circuits/rishon.py`, `lean/structure.py`, `lsh/lean_export.py` (731da36, 7.L3), and `rishon/*` (compress/spec, observables, physical, results, verify). Of the paths you named, `src/su2plaq/lsh/*` changed only in `lean_export.py`; `circuits/lsh.py`, `encodings/lsh.py`, `lsh/{operators,walk}.py`, `scripts/m7_results.py` are unchanged. `grep` shows `scripts/m7_results.py`, `circuits/lsh.py` and `encodings/lsh.py` do not import `lean_export` (imports are `circuits.lsh/spinnet`, `encodings.lsh`, `evaluate.evaluator`, `exact.*`, `lsh.operators/walk`, `metrics.*`), and none of the changed rishon/lean files is imported by the script.
- Empirical confirmation: I re-ran `scripts/m7_results.py` at HEAD into `scratch/tester-m7gate/regen/` (8.4 s). After removing provenance, `seconds`, `wall_seconds`, `peak_rss_mb`, timestamps and the `files` block, `UE.json`, `UB.json`, `step.json` have 0 differing values (floats compared with exact `!=`). All 10 circuit files (`UE`, `UB`, `step`, `step_order2` as `.qpy` + `.qasm3`, `UE_outer_row.qpy/.qasm3`) are byte-identical to the committed ones (`cmp`). So the committed numbers are reproduced bit for bit at HEAD.
- Headline values read from the committed files: $U_E$: 0 CX, 8 rotations, $T(10^{-6})=512$, verdict ok, op-norm error $4.4\cdot10^{-16}$. $U_B$: 94 CX, 4 rotations, $T_{\rm fixed}=88$, $T(10^{-6})=342$, error $1.4\cdot10^{-14}$. Step (order 1): 94 CX, 8 rotations, $T(10^{-6})=598$, error $1.6\cdot10^{-14}$. Every synthesised verdict at $\varepsilon=10^{-4},\dots,10^{-10}$ is `ok` and `certified`, measured sum within $\approx0.2$-$0.35$ of the budget. These equal the plan values (94 CX, 598 T).

## Byproducts and restore

The test runs rewrote `results/lsh/certs/lsh-step-o1-ddc1571c27bd.json` and the five `results/spinnet/certs/spinnet-*.json` (provenance only). I restored them with `git checkout -- results/spinnet/certs results/lsh/certs`; `git status` afterwards shows no change under `results/lsh`, `results/spinnet`, `compress/lean`. Other writes: `scratch/tester-m7gate/*` (gitignored), `results/lsh_tester/tester-407-gate.json`, this report. `lake build` was a no-op. I did not touch fuzzy files, `scripts/m4_results.py` or `tests/unit/test_spinnet_m4_results_unit.py` (other agents'). No source, acceptance test or tolerance edited.

## Notes (not failures)

- `-p no:cacheprovider` was used to avoid `.pytest_cache` writes; no effect on results.
- Carried over from 406 (builder, cosmetic): `Main.lean` header says "copy of `su2plaq_cert_lsh`"; hygiene test scans only `Counts.lean`/`Circuit.lean`; the committed LSH cert JSON churns on every test run (restore command above).
- Benchmark step has not been run (needs auditor PASS first).
