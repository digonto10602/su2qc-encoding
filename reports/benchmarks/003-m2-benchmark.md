# Benchmark report 003 - M2 (mode benchmark, M2 gate step 3)

- Date: 2026-11-06. Commit: `0aca224` plus the builder's uncommitted audit-note fixes (verified PASS in `reports/tests/042-m2-audit-notes-fixes.md`; none of the changed files is in the evaluator hash list or on a measured path except `compress/round.py`/`report.py`, which no benchmarked call uses). Tester: Sonnet 5.5.
- Prompt in force: `prompts/002-m0-m2-foundation-twelve-qubit-compression.md` (with 003 to 006 addenda). Auditor: `reports/audits/004-m2-compression-lean-audit.md` (PASS WITH NOTES). Previous benchmark: `reports/benchmarks/002-m1-twelve-qubit.md` (commit `5b2cbce`), raw `results/benchmarks/m1.json`.
- Machine, versions, settings: same machine as 001/002 (i7-8750H, 12 logical CPUs, 62 GB, no GPU; python 3.12.14, numpy 2.5.2, scipy 1.18.0, qiskit 2.5.2, aer 0.17.2, pygridsynth 1.2.0); `OMP/OPENBLAS/MKL_NUM_THREADS=1`, `PYTHONHASHSEED=20261104`, seed 20261104, `ct_compile` seed 12345, `-n auto` = 12 workers. Parameters: $\alpha=0.37$, $\beta=0.61$, $j_{\max}=1/2$ (dim 433), $\varepsilon=10^{-6}$, Paulo vs $U_B(\beta=1)$ with `tol_err = tol_gauss = 2\times10^{-5}$, `engine="auto"`.
- Raw numbers: `results/benchmarks/m2.json` (all comparisons, suite walls, physics diff, load samples), raw driver output `results/benchmarks/m2-raw/_raw.json`, `_m1_raw.json`, partial files, and the three `run_candidate` JSONs `rc_1..3.json`. Scripts unchanged: `results/benchmarks/scripts/bench_driver.py`, `bench_driver_m1.py` (workers `bench_worker.py`, `bench_worker_m1.py`).
- Method: identical to 002 (one task per fresh process, 3 processes per task, Paulo evaluation 1 run; "first" = cold first call in the process, "later" = remaining calls, median over processes; peak RSS = `ru_maxrss`). Threshold 10 % on medians.
- Machine load (`uptime`): before the M0 driver `load average: 3.66` (my own Lean run had just ended); before the M1 driver `5.08` (1-min value still including the preceding 12-worker `pytest` runs); before each of the three timed `run_candidate` runs `0.80, 1.35, 1.30`. The 1-min load average was also sampled every 15 s through the whole run (`m2.json::loadavg_1min_during_drivers`, 268 samples). During the single-process tasks the median load was 1.9 (M0 tasks, 13:02 to 13:09) and 1.35 (M1 tasks, 13:27 to 13:41), maximum 5.2 (the sample window includes the end of one pytest suite); the pytest suites (12 workers) raise it to 8 to 15 by construction. Other agent sessions were alive on the machine but idle.

```
python results/benchmarks/scripts/bench_driver.py        # M0 tasks x3, acceptance m0 x3, unit x3
python results/benchmarks/scripts/bench_driver_m1.py     # M1 tasks x3, m1_results.py, acceptance m0+m1 x3, unit x3
for i in 1 2 3: python -m su2plaq.compress.run_candidate compress/programs/twelve/F2/005-outer-t2-peephole.py \
        --encoding twelve --kind step --full --json <scratch>/rc_$i.json        # fresh process each, wall + ru_maxrss
python tools/check_lock.py ; ~/.claude/bin/acceptance-check                     # see report 042
```

## 1. Route-A build, evaluator and metrics tasks vs 002 (same scripts, same settings)
Every one of the 102 task/statistic pairs is in `m2.json::task_comparison_vs_002`. **No pair differs by more than 8 %** (largest: cached-lookup 5 microseconds $-7.6\,\%$, `target(UE)` first call 0.9 ms $+6.0\,\%$, `rebuild_paulo_uncompiled` $-5.3\,\%$) and no pair is flagged.

| quantity (task) | statistic | 002 (5b2cbce) | now | change |
|---|---|---|---|---|
| route A `h_magnetic_phys` (`ops`) | first / later, s | 0.1915 / 0.06932 | 0.1951 / 0.06978 | +1.9 % / +0.7 % |
| route B `h_magnetic_phys_6j` | first / later, s | 0.01443 / 0.01461 | 0.01489 / 0.01487 | +3.2 % / +1.8 % |
| `physical_basis()` cold | s | 0.2989 | 0.2935 | -1.8 % |
| `target(step)` / `target(UB)` | later, s | 0.2404 / 0.2202 | 0.2431 / 0.2216 | +1.1 % / +0.7 % |
| `evaluate` identity, inner_span (`eval_id_span`) | cold / warm, s | 6.660 / 2.017 | 6.751 / 2.019 | +1.4 % / +0.1 % |
| `evaluate` identity, physical | cold / warm, s | 1.400 / 0.929 | 1.366 / 0.932 | -2.4 % / +0.3 % |
| `evaluate` 3 outer bits | cold / warm, s | 1.419 / 0.989 | 1.391 / 0.960 | -2.0 % / -3.0 % |
| `evaluate(build_UE)` (`eval_UE`) | cold / warm, s | 6.696 / 2.018 | 6.641 / 1.991 | -0.8 % / -1.3 % |
| `evaluate(build_UB)` | cold / warm, s | 8.161 / 2.310 | 8.031 / 2.294 | -1.6 % / -0.7 % |
| `evaluate(step, order 1)` | cold / warm, s | 8.066 / 2.302 | 8.199 / 2.347 | +1.7 % / +2.0 % |
| `evaluate(step, order 2)` | cold / warm, s | 8.156 / 2.320 | 8.077 / 2.295 | -1.0 % / -1.0 % |
| `evaluate(synth UB)` (6 rot.) | cold / warm, s | 8.217 / 3.560 | 8.285 / 3.550 | +0.8 % / -0.3 % |
| `evaluate(synth step 1)` (10 rot.) | cold / warm, s | 12.144 / 7.350 | 11.943 / 7.291 | -1.7 % / -0.8 % |
| `evaluate(synth step 2)` (14 rot.) | cold / warm, s | 12.114 / 7.526 | 12.092 / 7.555 | -0.2 % / +0.4 % |
| `synthesize(step 1, 1e-6)` | cold / warm, s | 1.725 / 0.0339 | 1.735 / 0.0332 | +0.6 % / -2.2 % |
| `logical_metrics` (Paulo) | cold / warm, s | 1.357 / 0.01673 | 1.369 / 0.01702 | +0.9 % / +1.7 % |
| `t_table(qiskit=False)` | cold / warm, s | 2.005 / 0.01701 | 2.017 / 0.01734 | +0.6 % / +2.0 % |
| `t_table(qiskit=True)` / `ct_compile` | later, s | 0.2912 / 0.0630 | 0.2907 / 0.0631 | -0.1 % / +0.1 % |
| **Paulo QPY evaluate** (aer_mps, 1 run, M0 task) | wall, s | 83.97 | 84.07 | +0.1 % |
| Paulo QPY evaluate (M1 task) | wall, s | 83.07 | 83.50 | +0.5 % |
| **Paulo QPY evaluate** | peak RSS, MB | 1523 (M0 task) / 1488 (M1 task) | 1523 / 1471 | 0.0 % / -1.2 % |
| peak RSS of all other tasks | MB | 60 ... 692 | 60 ... 692 | $\le$ +2.5 % |
| `tests/acceptance/m0` (34 tests, 3 runs) | wall, s | 33.90 [33.79, 34.14] | 33.83 [33.49, 34.14] | -0.2 % |
| `pytest m0+m1 acceptance` (56 passed, 3 runs) | wall, s | 199.6 [197.6, 203.5] | 199.7 [198.1, 201.4] | +0.1 % |
| `scripts/m1_results.py` (1 run) | wall, s | 212.0 | 212.1 | +0.0 % |
| `tests/unit` | wall, s | 59.9 (178 tests) | 381.7 to 396.8 (401 tests; 6 runs: 382.5, 396.8, 395.9, 395.2, 381.7, 381.6) | not like-for-like, see 3 |

The two items that 002 flagged (Paulo-evaluation peak RSS +33 % from M0 to M1; warm `logical_metrics`/`t_table` +6 ms) are **unchanged** against the 002 baseline - no further growth - but they were also not reduced (RSS still 1.47 to 1.52 GB, warm `logical_metrics` 17.0 ms vs 10.4 ms in report 001).

## 2. Compression round wall time (new in M2)
Rounds 1 to 5 from `results/compress/twelve/round-00N.json` (`wall_s`, `lean_seconds`), measured on the machine as it was during the loop (each file's `provenance` says `cpu_count` 12; the machine was shared and the loop's own evaluations ran in parallel with proposer agents, so these are loop-time walls, not quiet-machine ones). There is no earlier round wall to compare with, so these are the baseline for later encodings.

| round | wall_s | of which Lean certificate, s | non-Lean wall, s | valid / invalid | commit (dirty) |
|---|---|---|---|---|---|
| 0 (seeds, for reference) | 163.8 | 0 | 163.8 | 5 / 0 | a4c28a6 (yes) |
| 1 | 529.3 | 85.2 | 444.1 | 4 / 0 | 84a20af (yes) |
| 2 | 135.2 | 78.8 | 56.4 | 4 / 0 | afa1865 (yes) |
| 3 | 137.3 | 86.9 | 50.5 | 3 / 0 | 418de65 (yes) |
| 4 | 136.9 | 87.6 | 49.3 | 3 / 0 | 3f90240 (yes) |
| 5 | 526.7 | 352.1 | 174.6 | 3 / 0 | d05f973 (yes) |

Reading: rounds 2 to 4 cost 135 to 137 s each (about 2.3 min), dominated by a 79 to 88 s Lean check of the round's best; round 5 is long because its best (`r05-F2-005`, 31 qubits) needed a 352 s Lean check; round 1 (444 s without Lean) contains the heavy F1-style circuits that read all 8 outer bits (known issue in STATUS: about 240 s per circuit at the nominal pair on a loaded machine). Per-entry evaluation walls in the archive: 6.7 to 14.2 s for the 12 round-2 to round-5 entries except `r05-F2-005` = 36.2 s (`archive/twelve/entries/*.json::wall_s`).

**Timed re-evaluation of the global best** (`run_candidate --full`, `r05-F2-005`, fresh process, quiet machine, no cache):

| run | uptime before | wall (process), s | wall reported, s | peak RSS, MB | result |
|---|---|---|---|---|---|
| 1 | load 0.80 | 36.97 | 36.56 | 375.8 | valid, CX 111, T(1e-6) 912, depth_CT 1663, 31 qubits, op-norm error $1.004\times10^{-13}$ |
| 2 | load 1.35 | 36.84 | 36.42 | 379.0 | identical |
| 3 | load 1.30 | 36.82 | 36.41 | 375.9 | identical |

Median 36.84 s [36.82, 36.97] versus the archived `wall_s` = 36.19 s measured during the loop: **+1.8 %** (within threshold). Key and metrics identical to the archive entry (CX 111, T 912, depth_CT 1663, qubits 31), engine `sparse`, certified. For the Lean checker alone: 350 s (`certify_best` on a quiet machine, report 042) versus the recorded 352.1 s (+/- 0.6 %); an old-format certificate re-checked in 325 s.

## 3. Test-suite walls
- The unit suite grew from 178 tests (59.9 s, 002) to 401 tests (381.6 to 396.8 s, six runs): +6.4x time for +2.25x tests. Not like-for-like (223 new tests, most of them M2 compression and Lean-pipeline tests that build circuits, call the compiled Lean checker or run whole `run_round` cycles); no per-test regression can be claimed from these numbers. Run-to-run spread of the six runs: 3.8 %. Peak RSS of the unit run (children max) 6.7 GB (002: 0.96 GB), again from the new heavy tests running 12 in parallel. The baseline for M3 is therefore 382 to 397 s with `-n auto`.
- The `acceptance/m0 + m1` suite and `m1_results.py` wall times are unchanged (+0.1 % and +0.0 %), peak RSS 1.84 to 2.14 GB (002: 2.12 GB).

## 4. Physics output unchanged
| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| all 19 benchmark tasks: every non-float field of the evaluator verdict / counts / spectra / `t_table` / `ct_compile` vs 002 (ok, reason, engine, method, certified, n_blocks, read, gauss, leak amplitude, T and CX counts, spectra) | identical | identical in all three repeats of every task | exact | PASS |
| `op_norm_error` and `block_error` of the 10 tasks that run the evaluator (the other 9 tasks have no such field) vs 002 | same values | all 10 differ from 002 in the last digits only; the absolute difference is at most $5.4\times10^{-23}$ (UE, at the $1.2\times10^{-13}$ span floor), $3.2\times10^{-18}$ / $3.9\times10^{-18}$ (step 1 / 2, exact), $6.6\times10^{-17}$ / $4.9\times10^{-16}$ / $1.5\times10^{-16}$ (synthesised UB / step 1 / step 2, values $1.9$ to $3.5\times10^{-6}$), $2.1\times10^{-21}$ (Paulo, $1.0756\times10^{-5}$) | $10^{-10}$ (floor), $\le 10^{-9}$ on synthesised | PASS |
| Paulo QPY: ok / engine / certified / combined error | True / aer_mps / True / $1.075586\times10^{-5}\le 2\times10^{-5}$ | identical (block $2.904794\times10^{-6}$ to the printed digits) | $2\times10^{-5}$ | PASS |
| `run_candidate --full` best circuit | CX 111, T 912, depth_CT 1663, 31 qubits, valid | identical in 3 runs; same op-norm error to 17 digits | exact | PASS |

The last-digit differences in `op_norm_error` (relative up to $4\times10^{-11}$ of a $10^{-13}$ floor value, i.e. $5\times10^{-23}$ absolute) are a rounding effect of the M2 step 2.3 change of `src/su2plaq/evaluate/evaluator.py` (commit `cb94221`: the phase `tr = np.trace(V^dag A)` became `np.vdot(V_c, A_c)` to support the trial-mode state subset). It changes summation order only; no verdict, count or spectrum changed.

## 5. Verdict
**PASS (benchmark recorded)**: no slowdown above the 10 % threshold on any of the 102 task statistics, the three suite walls, the Paulo evaluation or the Lean check; the only deltas above 10 % are the unit-suite wall time (178 -> 401 tests, not like-for-like). No physics-output change beyond $1.6\times10^{-16}$ in synthesised-circuit error values (rounding, cause above) and no change in any count, verdict or key.

Flags for the coordinator (carried over from 002, not new, none above 10 % versus 002):
1. Paulo-evaluation peak RSS 1.47 to 1.52 GB (+33 % vs report 001) persists.
2. Warm `logical_metrics` / `t_table(qiskit=False)` 17.0 ms (+60 % vs report 001, +6 ms) persists; the compression loop calls `logical_metrics` once per evaluation (about 1 per 6.7 to 36 s), so it is negligible there.
3. Baselines to use from now on: warm `evaluate` 2.0 to 2.35 s (cold 6.6 to 8.2 s), unit suite 382 to 397 s, acceptance m0+m1 199.7 s, `run_candidate --full` of the 31-qubit best 36.8 s, loop round 135 s without heavy circuits.
4. A fresh note: the unit suite now takes 6.5 min and needs 6.7 GB of RAM at 12 workers; consider this when running it on the desktop.
