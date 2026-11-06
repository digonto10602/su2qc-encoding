# Benchmark report 200 - M5 rishon (SU(2) quantum link model) general circuit (mode benchmark, desktop track R)

- Date: 2026-11-06. Commit: `86fda8e` (branch `m5-rishon`; `git status`: only this benchmark's own untracked files `results/benchmarks/rishon-m5*`; no source, test or prompt file edited).
- Prompt in force: `prompts/200-rishon-m5-plan.md` (+ one-off test fix `prompts/201`); acceptance tag `acceptance-v8` (`acceptance-check`: PASS, `tools/check_lock.py`: LOCK OK, both run at the end of this session).
- Gate state: tester full PASS `reports/tests/207` (and audit-fix recheck `reports/tests/208`), auditor PASS WITH NOTES `reports/audits/200`.
- Related: previous benchmark `reports/benchmarks/002-m1-twelve-qubit.md` (laptop i7-8750H, commit `5b2cbce`); tester `reports/tests/207-m5-gate-full.md`, `reports/tests/204`, `reports/tests/205`, `reports/tests/206`.
- Raw numbers: `results/benchmarks/rishon-m5.json` (summary, medians and spreads, pytest per-test times, results-script log, T1 comparison). Raw per-process records: `results/benchmarks/rishon-m5-raw/*.jsonl`, logs, junit XML and `/usr/bin/time -v` files. Scripts: `results/benchmarks/rishon-m5-scripts/` (`rishon_bench_worker.py`, `rishon_bench_twelve_worker.py` = copy of `bench_worker_m1.py` with the path changed and a T-table task added, `rishon_bench_driver.py`, `rishon_bench_phase3.sh`/`phase4`/`phase5`, `rishon_bench_lean.sh`, `rishon_bench_l3.py`, `rishon_monitor.sh`, `rishon_bench_collect.py`). `m0-baseline.json`, `m1.json` and the old `results/benchmarks/scripts/` are untouched.

## 0. Machine, settings, how the numbers were taken
- Machine `SupremeCommander`: Intel Core i7-12700KF (8 P-cores with SMT + 4 E-cores = 20 hardware threads, P max 4.9 GHz, E max 3.8 GHz, governor `powersave`), 31.9 GB RAM, NVIDIA RTX 3070 (0 % load, not used), Linux 7.0.0-38. No GPU path exists for these circuits. The laptop of report 002 is an i7-8750H (12 threads), so timings are **not like-for-like with 002** (section 5).
- Core set: every job under `taskset -c 10-19` = hardware threads 10-15 (three P-cores, two SMT threads each) plus threads 16-19 (four E-cores). A single-thread process normally sits on a P-core thread (logged for the 43 single-process records: 33 started on thread 12 or 13, the others on 10, 14, 15 or 18, and all 43 finished on thread 12 or 13); the E-core effect is measured separately (section 4.3).
- Software: conda `su2qc-coding`, python 3.12.16; `OMP/OPENBLAS/MKL_NUM_THREADS=1`; `PYTHONHASHSEED=20261104`; library gauss-sample seed 20261104; `ct_compile` seed 12345; Lean toolchain `leanprover/lean4:v4.35.0`.
- Parameters: $(\alpha,\beta)=(0.37,0.61)$; 38 432 physical states, 1296 inner codes; 16 data qubits + 32 outer qubits in the JW register; `verify` default (`tol_err` $10^{-10}$, 256 sampled + 17 closed Gauss states, sparse engine, cap $5\times10^{6}$); $\varepsilon\in\{10^{-4},10^{-6},10^{-8},10^{-10}\}$.
- Method: one task per **fresh process** (same convention as 001/002); 3 processes per task where a task takes < 60 s, 1 where longer. "First" = first call in the fresh process (cold, includes lazy library imports and caches); "later" = following calls. Statistic: median [min, max]. Peak RSS = `ru_maxrss` of the process (pytest and Lean: `/usr/bin/time -v`).
- Machine cleanliness: the cron job `su2qc-worker` (`tick.sh`, every 15 min) was idle (`state.json` = `{}`, no run in progress). A sampler logged load average and the three busiest processes every 10 s (407 samples, 08:21 to 09:29, `results/benchmarks/rishon-m5-raw/monitor.log`): in the single-process window the 1-min load average was <= 1.15 and never two busy python processes; no process other than my jobs (python, pytest, lean, lake) used > 20 % CPU in any sample. Phases ran strictly one after the other, except the P-core/E-core pair in 4.3.
- Commands:
```
cd ~/Projects/su2qc-rishon && source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=20261104; source ~/.elan/env
python results/benchmarks/rishon-m5-scripts/rishon_bench_driver.py <out.jsonl> import:3 basis:3 inner:3 build:3 ttable_{UE,UB,step,step2,UE_outer_row}:3 verify_{UE,UB,step,step2}:3 synth_UE_1e-6:3 synth_UB_1e-6:1
RISHON_WORKER=rishon_bench_twelve_worker.py python .../rishon_bench_driver.py <out.jsonl> m1_build:3 eval_UE:3 eval_UB:3 eval_step1:3 ttable_UE:3 ttable_UB:3 ttable_step1:3 synth_UB:3 paulo_m1:1
bash .../rishon_bench_phase3.sh      # pytest -n 10 -m "not slow" m5 (x1); same with -k "not T1" (x3); -m slow (L3, x1); Lean timings; L3 certificate timings
bash .../rishon_bench_phase4.sh      # Lean JW 3rd rep; pytest -n 3 -k T1
bash .../rishon_bench_phase5.sh      # T1[step] alone on cpu 12 (P) and, at the same time, on cpu 18 (E)
python .../rishon_bench_collect.py   # -> results/benchmarks/rishon-m5.json
```

## 1. Headline table (medians; spread = (max-min)/median)
| quantity | plan target | median [min, max] | RSS | verdict |
|---|---|---|---|---|
| `rishon_basis()` build, 38 432 states (cold, includes the corner kernels) | <= 60 s | **2.372 s** [2.369, 2.376] (0.3 %) | 96 MB after build, 312 MB process end | PASS (25x margin) |
| same, second `_build_basis()` with kernels cached | - | 0.494 s | - | info |
| `inner_span` (1296 x 1296) | - | 0.779 s | - | info |
| inner plaquette operator $W$ build (`_W`, after `_sector_ops`) | "0.06 s" (plan estimate) | 0.0685 s [0.0681, 0.0689] (+14 % vs the estimate) | - | PASS (not a threshold) |
| `eigh` of the 1296 block $H_B^{in}$, complex128 with vectors | "1 s" (plan estimate) | **1.275 s** [1.271, 1.281] (3 repeats x 3 processes) | 339 MB | PASS (+27 % vs the estimate, not a threshold) |
| `eigvalsh` complex128 / `eigh` of the real part | - | 0.332 s / 0.169 s | - | info |
| `_bright()` (81 component eigendecompositions) | - | 0.0178 s | - | info |
| `inner_target` UE / UB / step 1 / step 2 | - | 5.0 ms (first), 1.8 ms later / 1.005 s / 1.225 s / 1.455 s | - | info |
| `build_UE(0.37)` cold / warm | - | 0.132 s / 35 $\mu$s | - | info |
| `build_UB(0.61)` cold / warm | - | 1.838 s (lazy Qiskit library import) / 11.5 ms | - | info |
| `build_step` order 1 / order 2 (warm) | - | 11.8 ms / 11.6 ms | - | info |
| `verify` UE, exact angles (sparse) | 10-120 s (plan, step 5.7) | 4.74 s [4.71, 4.75] first, 4.67 s later | 587 MB | PASS |
| `verify` UB | same | 6.38 s [6.34, 6.39] first, 6.03 s later | 687 MB | PASS |
| `verify` step order 1 | same | 6.58 s [6.55, 6.64] first, 6.28 s later | 686 MB | PASS |
| `verify` step order 2 | same | 6.84 s [6.83, 6.86] first, 6.54 s later | 687 MB | PASS |
| synthesis $\varepsilon=10^{-6}$ + `verify` UE (4 rotations, 676 gates) | - | 0.346 s + 6.95 s [6.94, 6.99]; process 10.07 s | 839 MB | PASS |
| synthesis $\varepsilon=10^{-6}$ + `verify` UB (162 rotations, 52 006 gates), 1 run | - | 0.389 s + **276.6 s**; process 281.9 s | 1388 MB | PASS |
| `t_table` (pygridsynth sums, 4 $\varepsilon$), UB/step/step2, `qiskit=False` cold | - | 0.71 / 0.79 / 0.79 s | 324-333 MB | info |
| `t_table` with Qiskit Clifford+T (`qiskit=True`, seed 12345), UB/step/step2 | - | 0.83 / 0.86 / 0.86 s | - | info |
| `pytest -n 10 -m "not slow" tests/acceptance/m5` (33 tests, includes T1), 1 run | < 10 min | **672.4 s (11.2 min)**, 33 passed | max single process 6.64 GB; summed python RSS peak 6.53 GB (5-s sampling) | **FLAG (+12 % over 10 min)** |
| same with `-k "not T1"` (30 tests), 3 runs | - | 102.6 s [99.7, 102.7] | 6.64 GB | PASS |
| `pytest -m slow` (L3 certificate test, the only test carrying the marker) | - | 2.9 s test, 3.35 s wall | 0.8 GB | PASS |
| T1 tests `pytest -n 3 -k T1` (3 tests, 1 run) | - | 581.8 s wall: T1[UE] 11.8 s, T1[UB] 376.5 s, T1[step] 581.1 s | max process 1.86 GB | see 4.3 |
| Lean `lake build Su2Plaq.Rishon.Counts` (cached replay), 3 runs | - | 3.5 s [3.4, 4.3] | 1.0 GB | PASS |
| Lean `lake build Su2Plaq.Rishon.JW` (cached), 3 runs | - | 0.57 s [0.57, 0.58] | 0.82 GB | PASS |
| Lean `lake env lean Rishon/Counts.lean` (**from source**, no `.olean` written), 3 runs | <= 600 s, <= 15 GB (plan) | 8.04 s [7.92, 8.34] | 8.30 GB | PASS |
| Lean `lake env lean Rishon/JW.lean` (**from source**), 3 runs | within limits | 61.10 s [61.01, 61.16] | 7.07 GB | PASS |
| L3 certificate: export 0.092 s, write Lean file 0.3 ms, exact-integer Python check 5 ms, **native Lean check (certified)** 1.36 s [1.30, 1.39], tampered $\kappa$ 2 to 1 **rejected** 1.44 s [1.41, 1.48] | - | 3 + 3 runs | 0.82 GB (Lean child) | PASS |

Notes on the Lean rows: "cached" = `lake build` with everything up to date (it only re-checks traces and loads Mathlib-dependent `.olean` files; 3.5 s for Counts is Mathlib import resolution, JW has no Mathlib import). "From source" = `lake env lean <file>` (re-elaboration, kernel `decide`), which does not write build products. `lean/Su2Plaq/Structure/Counts.lean` and its `.olean` (mtime 2026-11-05 23:54) were not rebuilt; `git status` of `lean/` is clean. The tester report 206 timings (Counts 31.8 s, JW 264.8 s) were taken with a 6 GB results job running at the same time; uncontended they are 8.0 s and 61.1 s (4.0x and 4.3x faster).

## 2. Circuit resource table (HEAD, recomputed by the benchmark workers; identical to the stored JSON of `results/rishon/`)
| circuit | qubits (anc.) | CX | $n_{rot}$ | $T_{fixed}$ | lowered depth | macro depth | $T_{total}$ at $10^{-4}$ / $10^{-6}$ / $10^{-8}$ / $10^{-10}$ (pygridsynth) |
|---|---|---|---|---|---|---|---|
| $U_E$ (16 data qubits) | 16 (0) | **8** | 4 | 0 | 3 | 3 | 176 / 256 / 328 / 416 |
| $U_E$ + outer row (48 qubits) | 48 (0) | 24 | 12 | 0 | 3 | 3 | 528 / 768 / 984 / 1248 |
| $U_B$ | 26 (10) | **10 094** | 162 | 10 218 | 13 682 | 2402 | 17 150 / 20 394 / 23 954 / 27 066 |
| step, order 1 | 26 (10) | **10 102** | 166 | 10 218 | 13 685 | 2405 | 17 326 / 20 650 / 24 282 / 27 482 |
| step, order 2 | 26 (10) | 10 110 | 170 | 10 218 | 13 688 | 2408 | 17 486 / 20 922 / 24 626 / 27 898 |

Check: UE 8 CX, UB 10 094 CX, step 10 102 CX, 26 qubits all as in the brief. $T_{total}=T_{fixed}+\sum_r T_r$ and every one of the 20 table rows (5 circuits x 4 $\varepsilon$, all columns incl. Qiskit $T$, CX and depth) is **identical** to the stored `results/rishon/*.json` in all 15 benchmark processes (3 repeats x 5 circuits), as are the lowered gate counts. Qiskit Clifford+T $T$-counts are 0.0-9.6 % below the pygridsynth sums (worst: $U_B$ at $10^{-4}$, 15 502 vs 17 150, -9.6 %), inside the 10 % limit of `tests/acceptance/m5`.

Against the 12-qubit encoding (`results/twelve/*.json`, same $\alpha,\beta$): UB 294 CX, 6 rotations, $T_{fixed}$ 312, lowered depth 292, 34 qubits, $T_{total}(10^{-6})=696$; step 294 CX, 10 rotations, $T(10^{-6})=952$; UE 0 CX, 12 qubits, $T(10^{-6})=256$. Rishon / 12-qubit: UB CX 34.3x, $n_{rot}$ 27x, $T_{fixed}$ 32.8x, lowered depth 46.9x, $T_{total}(10^{-6})$ 29.3x, step $T(10^{-6})$ 21.7x; UE has the identical $T$ table (176 / 256 / 328 / 416) and 8 extra CX; the rishon register uses fewer qubits (26 vs 34). This is a property of the circuit (larger local Hilbert space and the $\mathrm{SU}(2)$ plaquette in two-rishon form), not a timing result.

## 3. Same-machine re-measure of the 12-qubit quantities (scale and speed factor against report 002)
Run with a copy of the 002 worker (`rishon_bench_twelve_worker.py`) on this machine, 3 fresh processes per task; physics outputs are identical to 002 on every digit shown.

| quantity (12-qubit) | 002 laptop (i7-8750H) cold / warm | now, desktop cold / warm, median [min, max] | speed factor cold / warm | RSS now (002) |
|---|---|---|---|---|
| `evaluate(build_UE)` | 6.70 / 2.02 s | 2.672 [2.669, 2.686] / 0.718 [0.712, 0.722] s | 2.5x / 2.8x | 575 MB (578) |
| `evaluate(build_UB)` | 8.16 / 2.31 s | 3.079 [3.072, 3.093] / 0.800 [0.796, 0.837] s | 2.7x / 2.9x | 658 MB (655) |
| `evaluate(build_step, order 1)` | 8.07 / 2.30 s | 3.077 [3.073, 3.077] / 0.800 [0.797, 0.822] s | 2.6x / 2.9x | 658 MB (656) |
| `evaluate(synth UB, 1e-6)` (6 rotations) | 8.22 / 3.56 s | 3.095 / 1.147 [1.144, 1.148] s | 2.7x / 3.1x | 662 MB (657) |
| `synthesize(UB, 1e-6)` | 1.62 / 0.0286 s | 0.464 / 0.0083 s | 3.5x / 3.4x | - |
| `build_UE` / `build_UB` (cold, 1st call) | 0.354 / 1.59e-3 s | 0.104 / 5.0e-4 s | 3.4x / 3.2x | 115 MB (116) |
| Paulo QPY `evaluate` (aer_mps), 1 run | 83.07 s | 24.34 s | 3.4x | 1512 MB (1488) |

Outputs: `evaluate` op-norm errors UE $1.21\times10^{-13}$, UB $2.42\times10^{-13}$, step $2.69\times10^{-13}$, Gauss $5.3\times10^{-16}$ / $7.6\times10^{-16}$ / $3.9\times10^{-15}$ (002: the same); Paulo ok, op-norm $1.0756\times10^{-5}$ (002: $1.0756\times10^{-5}$ combined). So the desktop is about 2.5-3.5x faster than the laptop for this workload, and the 12-qubit code did not change in speed or memory beyond that factor (RSS within +/- 2 %, including the Paulo evaluation that was flagged +33 % in 002 and is unchanged at 1.51 GB).

Rishon vs 12-qubit on the same machine (warm `verify` / `evaluate`): UE 4.67 s vs 0.72 s (6.5x), UB 6.03 s vs 0.80 s (7.5x), step 6.28 s vs 0.80 s (7.8x); `verify` includes the 256+17-state Gauss sample and the 1296-code inner view (vs 625 codes). Peak RSS of `verify(UB)` 687 MB vs 658 MB (+4 %). Synthesised $U_B$ at $10^{-6}$: 276.6 s (162 rotations, 52 006 gates) vs 1.15 s (6 rotations, 1.8 k gates).

## 4. Pytest and the results script
### 4.1 `tests/acceptance/m5` (command `taskset -c 10-19 pytest -n 10 -m "not slow" tests/acceptance/m5 -q --durations=0`)
33 passed, 0 failed, 0 skipped, wall 672.4 s (1 run; `/usr/bin/time -v` 11:12.6). Slowest tests: T1[step] 670.9 s, T1[UB] 416.3 s, S1[order 2] 98.9 s, S1[order 1] 65.2 s, B1 magnetic inner block $\beta$=1.0 62.3 s and $\beta$=0.61 62.1 s, E1 electric step 57.1 / 54.7 s, B1 verifier sensitivity 55.9 s, B1 physical-with-outer 51.9 s, T1[UE] 43.4 s, X1 plaquette structure 38.7 s; the other tests <= 38 s, L1/L2 Lean tests 17.6 s / 10.4 s. Without the two T1 tests the suite is about 100 s (`-k "not T1"`, 3 runs: 99.7, 102.6, 102.7 s). The wall time of the full non-slow run equals the single longest test (T1[step]); more workers cannot reduce it. Note the `slow` marker is carried only by the L3 test (`pytest.ini`: `slow: long-running (minutes)`), which takes 2.9 s; the T1 tests are not marked.

### 4.2 Results script log (`results/rishon/m5_results-b4c1917.log`, not rerun)
`python scripts/m5_results.py --jobs 6` at `b4c1917`: **total wall 4130.8 s = 68.8 min** (provenance in every JSON), peak RSS main 0.51 GB, largest worker 2.97 GB. The "58 min" in STATUS/the brief is the earlier run at `56b466d` (3491 s, `reports/tests/205`); this regeneration was slower. Per-task seconds inside the 6-worker pool (25 tasks):

| circuit | exact-angle `verify` | synth $10^{-4}$ | synth $10^{-6}$ | synth $10^{-8}$ | synth $10^{-10}$ |
|---|---|---|---|---|---|
| UE | 20.5 | 24.7 | 22.4 | 22.1 | 23.6 |
| UE + outer row (sampled check) | 0.1 | 16.7 | 5.8 | 5.6 | 7.1 |
| UB | 16.1 | 1699.0 | 1100.9 | 596.1 | 651.6 |
| step, order 1 | 31.7 | 2866.9 | 2266.7 | 690.6 | 981.8 |
| step, order 2 | 32.3 | 3135.1 | 1680.6 | 758.2 | 789.3 |

The critical path is the coarsest-$\varepsilon$ re-verification of step order 2 (3135 s). Compared with the uncontended single runs of this benchmark, pool tasks were slower: exact UB 16.1 s (pool) vs 6.4 s (alone), synth UE $10^{-6}$ 22.4 s vs 7.3 s (synthesis + verify), synth UB $10^{-6}$ 1100.9 s vs 281.9 s (alone, 3.9x). Guess (not tested): 6 workers plus the main process on 3 P-cores (6 threads) + 4 E-cores put several jobs on SMT siblings and E-cores, and the sparse-simulator work is memory-bound. Smaller $\varepsilon$ is not slower: the coarse $\varepsilon$ rows are the most expensive, consistent with more non-negligible amplitudes surviving the $10^{-12}$-level pruning when the synthesis error is larger (guess).

### 4.3 T1 timings and core placement (flag)
| run | T1[UE] | T1[UB] | T1[step] | note |
|---|---|---|---|---|
| gate reports 207 / 208 (`-n 10`, whole m5) | - | 366.0 / 357.3 s | 473.3 / 482.0 s | UB and step ran one after the other on the same worker (473+366 = 840 s total wall) |
| this session, `-n 10 -m "not slow"` | 43.4 s | 416.3 s | 670.9 s | UB and step on different workers: wall 672 s |
| this session, `-n 3 -k T1` | 11.8 s | 376.5 s | 581.1 s | wall 581.8 s |
| this session, T1[step] alone on cpu 12 (P-core thread) | - | - | **607.7 s** | other core busy with the E-core run |
| this session, T1[step] alone on cpu 18 (E-core), at the same time | - | - | **917.6 s** | 1.51x slower than the P-core |

Same code (`86fda8e` equals the tree tested in 208), yet T1[step] on a P-core now takes 608 s against 473-482 s in the gate runs (+26 %), and 671 s inside the 10-worker run (+39 %). The E-core measurement shows that where `-n 10` places a worker changes a single test by 1.5x. The extra +26 % on an isolated P-core is not explained (guess: different clock/thermal state or SMT-sibling occupancy at the time of the gate run; I cannot tell without the gate runs' placement). Not a code change as far as I can see: the 10 verify processes in section 1 reproduce the stored verdicts bit for bit.

## 5. Comparison with report 002, and what is and is not a regression test
- No like-for-like regression test of M5 quantities is possible: this is the first rishon benchmark, and 002 was measured on the laptop. The same-machine 12-qubit re-measure (section 3) shows no change of the inherited 12-qubit code in memory (+/- 2 %) or physics output. Time against 002 is a machine factor of 2.5-3.5x (not a regression and not a threshold test). Nothing in 002's flag list (Paulo RSS +33 %, warm `logical_metrics` +6 ms) changed relative to the machine factor: Paulo RSS 1512 MB (002: 1488-1523 MB).
- Physics output unchanged: stored `results/rishon/{UE,UB,step,step_order2,UE_outer_row}.json` (generated at `b4c1917`) vs recomputation at HEAD: `verify` UE / UB / step / step2: `ok`, `certified`, sparse; op-norm $1.1\times10^{-16}$ / $3.43\times10^{-13}$ / $4.12\times10^{-13}$ / $4.10\times10^{-13}$, block error $1.1\times10^{-16}$ / $4.14\times10^{-14}$ / $4.49\times10^{-14}$ / $4.51\times10^{-14}$, Gauss residual $1.8\times10^{-16}$ / $2.26\times10^{-15}$ / $2.66\times10^{-15}$ / $2.27\times10^{-15}$ - **equal to all printed digits** in all 3 repeats. Synthesised $\varepsilon=10^{-6}$: UE op-norm $2.1737\times10^{-6}$ (budget $4.0\times10^{-6}$; uses 54 %), block $1.858\times10^{-6}$, leak $3.15\times10^{-7}$, Gauss $2.1\times10^{-16}$, 4 rotations, $T_{rot}$ 256; UB op-norm $1.8427\times10^{-5}$ (budget $1.62\times10^{-4}$; uses 11.4 %), block $6.13\times10^{-6}$, leak $1.23\times10^{-5}$, dropped $4.66\times10^{-10}$, Gauss $5.59\times10^{-6}$, 162 rotations, $T_{rot}$ 10 176, certified - equal to the stored values. The audit-fix code changes after `b4c1917` (N4, N5, N7, N8) therefore changed no number.
- Inner-block checks while timing: $H_B^{in}$ eigenvalue multiplicities $\pm4\sqrt2$ (1 each), $\pm2$ (48), $\pm1$ (32), $0$ (1134); Hermiticity error 0; $\|H V - V\Lambda\|_\infty=4.3\times10^{-15}$; unitarity of the inner targets $\le7.8\times10^{-16}$.

## 6. Verdict and flags for the coordinator
Everything recorded; no physics change; no memory or time number is above the plan limits for the quantities the plan sets a target for, except the suite wall time.

| # | flag | numbers | guessed cause |
|---|---|---|---|
| F1 | `tests/acceptance/m5` "non-slow" wall time above the plan target (< 10 min on 10 cores) | 672.4 s (11.2 min), +12 % over 600 s; without T1: ~100 s | the two T1 tests are not marked `slow`; T1[step] (581-671 s, one process) alone exceeds 10 min; parallelism cannot help. Planner decision: mark T1 `slow` or accept; I did not touch it |
| F2 | T1[step] slower than in gate reports 207/208 | P-core alone 608 s, `-n 3` 581 s, `-n 10` 671 s vs 473-482 s (+21 to +42 %); E-core 918 s | worker placement on E-cores / SMT siblings (E-core factor 1.51x measured); the residual +26 % on an isolated P-core unexplained |
| F3 | results script slower than the quoted "58 min" | 4130.8 s = 68.8 min at `b4c1917` (`--jobs 6`); 58 min was the earlier run (3491 s) | pool contention: the same tasks are 3.9x faster alone |
| F4 | plan estimates exceeded (informational) | $W$ build 0.0685 s vs 0.06 s; `eigh` 1.275 s vs 1 s | rough planner estimates, not thresholds |
| F5 | memory headroom | pytest single process 6.64 GB, summed python RSS 6.53 GB; Lean Counts from source 8.30 GB (limit 10 GB; plan 15 GB), JW 7.07 GB | one test or fixture allocates ~6.6 GB (also seen in 207: 6.8 GB); unchanged, not attributed |

Notes: (1) no check in this report changes a tolerance or a test; (2) 12-qubit timings quoted from 002 are laptop values; (3) the `T_total` values in section 2 are the pygridsynth sums, the Qiskit column is in the JSON; (4) `graphify update .` not needed: no source changed.

VERDICT: PASS (benchmark recorded; physics output bit-identical to the stored results; plan targets met for basis build (2.4 s vs 60 s), `verify` (4.7-6.8 s), Lean builds and L3; flags F1-F5 above, F1 and F2 for the coordinator/planner).
