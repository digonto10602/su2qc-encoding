# Benchmark report 002 - M1 twelve-qubit (mode benchmark)

- Date: 2026-11-05. Commit: `5b2cbce` (tree clean; the only untracked files are this benchmark's own scripts/results). `results/twelve/*` were produced at `a9702e5`, `git_dirty` False.
- Prompt in force: `prompts/005-relative-prune-cap.md` (on 004, 003, 002). Auditor: `reports/audits/003` (PASS WITH NOTES, all notes fixed and verified in `reports/tests/022`, `023`). Previous benchmark: `reports/benchmarks/001-m0-baseline.md` (commit `30b38a0`), raw `results/benchmarks/m0-baseline.json`.
- Machine, versions, settings: identical to report 001 (i7-8750H, 12 logical CPUs, 62 GB, no GPU; python 3.12.14, numpy 2.5.2, scipy 1.18.0, qiskit 2.5.2, aer 0.17.2, pygridsynth 1.2.0; `OMP/OPENBLAS/MKL_NUM_THREADS=1`, `PYTHONHASHSEED=20261104`; seed 20261104, `ct_compile` seed 12345; `-n auto` = 12 workers). Benchmarks were run one after the other, nothing else running (load average 0.95 before start).
- Parameters: $\alpha=0.37$, $\beta=0.61$, $j_{\max}=1/2$ (dim 433); synthesis $\varepsilon=10^{-6}$ with `synth_tolerances(n_rot, eps)`; Paulo's circuit vs $U_B(\beta=1)$, `tol_err = tol_gauss = 2e-5`, `engine="auto"`.
- Raw numbers (all repeats, provenance): `results/benchmarks/m1.json`. Scripts: `results/benchmarks/scripts/bench_driver.py` + `bench_worker.py` (M0 tasks, unchanged), `bench_driver_m1.py` + `bench_worker_m1.py` (new M1 tasks).
- Method: as in 001 - one task per fresh process, 3 processes per task (Paulo evaluation and `m1_results.py`: 1 run), "first" = first call of the fresh process (cold), "later" = the remaining calls; statistic median [min, max]; peak RSS = `ru_maxrss` of the process.

```
python results/benchmarks/scripts/bench_driver.py       # M0 tasks re-run + m0 suite x3 + unit suite x3
python results/benchmarks/scripts/bench_driver_m1.py    # M1 tasks, scripts/m1_results.py --out <scratch>, pytest m0+m1 x3, unit x3
python tools/check_lock.py ; ~/.claude/bin/acceptance-check   # LOCK OK ; PASS: tests/acceptance matches acceptance-v5
```

## 1. M0 baseline tasks re-run vs report 001 (same scripts, same settings)
Threshold 10 % on medians. Only rows that matter shown in full; every row (59 task/statistic pairs) is in the comparison I computed from `m1.json` (`worker` blocks) vs `m0-baseline.json::raw`.

| task | statistic | 001 (30b38a0) | now (5b2cbce) | change | flag |
|---|---|---|---|---|---|
| `physical_basis()` cold | first, s | 0.2954 [0.290, 0.302] | 0.2989 [0.295, 0.300] | +1.2 % | - |
| route B `h_magnetic_phys_6j` | first / later, s | 0.01495 / 0.01472 | 0.01443 / 0.01461 | -3.5 % / -0.7 % | - |
| `h_magnetic_phys` (route A) | first / later, s | 0.1999 / 0.06944 | 0.1915 / 0.06932 | -4.2 % / -0.2 % | - |
| `target(step)`, `target(UB)` | later, s | 0.2428, 0.2213 | 0.2404, 0.2202 | -1.0 %, -0.5 % | - |
| `evaluate` identity, `inner_span` | cold / warm, s | 6.736 / 2.031 | 6.660 / 2.017 | -1.1 % / -0.7 % | - |
| `evaluate` identity, `physical` | cold / warm, s | 1.390 / 0.932 | 1.400 / 0.929 | +0.7 % / -0.3 % | - |
| `evaluate` $U_E$ as 4 `p` gates | cold / warm, s | 6.653 / 2.023 | 6.690 / 2.016 | +0.6 % / -0.4 % | - |
| `evaluate` 3 outer bits | cold / warm, s | 1.431 / 0.991 | 1.419 / 0.989 | -0.8 % / -0.2 % | - |
| **Paulo QPY evaluate** (aer_mps), 1 run | wall, s | 83.13 | 83.97 (and 83.07 in the M1 task; 83.14 at 30b38a0 re-run today) | +1.0 % | - |
| **Paulo QPY evaluate** | **peak RSS, MB** | **1127** | **1523 (M0 task), 1488 (M1 task); 30b38a0 re-run today: 1142** | **+32 to +35 %** | **FLAG (memory)** |
| `logical_metrics` (Paulo uncompiled) | cold / warm, s | 1.298 / 0.01041 | 1.357 / **0.01673** | +4.5 % / **+60.7 %** | **FLAG (warm, 6 ms abs.)** |
| `t_table(qiskit=False)` | cold / warm, s | 2.010 / 0.01067 | 2.005 / **0.01701** | -0.3 % / **+59.4 %** | **FLAG (warm, 6 ms abs.)** |
| `t_table(qiskit=True)` after False | later, s | 0.2772 | 0.2912 | +5.0 % | within threshold |
| `t_table(qiskit=True)` cold, `ct_compile` | s | 3.661 / 0.0767 | 3.633 / 0.0784 | -0.8 % / +2.2 % | - |
| `tests/acceptance/m0` (34 tests, 3 runs) | wall, s | 33.39 [33.14, 34.17] | 33.90 [33.79, 34.14] | +1.5 % | - |
| `tests/unit` (3 runs) | wall, s | 47.69 [47.46, 47.93] (140 tests) | 59.68 [59.65, 61.42] (178 tests) | +25 % | not like-for-like: 38 more tests (608 added lines in 8 test files, M1 unit tests incl. sparse_sim and circuit tests); no per-test regression can be claimed |
| peak RSS of the other 9 tasks | MB | 60 / 148 / 571 / 226 / 574 / 230 / 207 / 206 / 123 | 60 / 148 / 571 / 224 / 574 / 231 / 210 / 206 / 123 | <= +1.5 % | - |

Reading of the flags:
1. **Paulo evaluation memory +33 %** (1127 -> 1488-1523 MB) is real: I re-ran the old commit `30b38a0` in a separate git worktree on the same machine today and got 1142 MB, so it is not machine drift. Time and output are unchanged. Guess at the cause: the M1 rewrite of `lower()` (gate-by-gate lowering with an extra lowered copy of the 34-qubit circuit and cached decompositions) and/or the `sparse_sim` translation caches (`git diff --stat 30b38a0 HEAD -- src`: `sparse_sim.py` 199 changed lines, `logical.py` 69). Not diagnosed further (tester does not touch source). 1.5 GB is still far below the 62 GB machine; I raise it because the 10 % rule applies.
2. **Warm `logical_metrics` / `t_table(qiskit=False)`: +6 ms per call** (10.4 -> 16.7 ms; 10.7 -> 17.0 ms), spread of both sets is < 3 %, so the increase is genuine though absolute size is tiny (< 20 ms). Guess: the new gate-by-gate `lower()` (Python loop over the 1.1 k instructions instead of one `transpile`) - it is the common code path of both calls; the cold first call is unchanged because it is dominated by Qiskit's lazy set-up.

## 2. New M1 quantities (problem size: 433 physical states, 625 inner codes; circuits on 34 qubits = 12 data + 22 ancilla)
Each row: 3 fresh processes, 4 `evaluate` calls per process (1 cold + 3 warm; 3 + 3 for the synthesised ones), median [min, max]. Seconds. RSS = whole process (includes imports).

| quantity | cold (first call), s | warm, s | peak RSS, MB |
|---|---|---|---|
| `import su2plaq.circuits.twelve, encodings.twelve, evaluator, cliffordt` | 0.316 [0.311, 0.319] | - | - |
| `build_UE(0.37)` (4 `p`) | 0.354 [0.354, 0.354] (includes lazy `qiskit` circuit-library import) | 5.8e-5 [5.5e-5, 6.9e-5] | 116 (whole build task) |
| `build_UB(0.61)` (rccx 60, cx 50, x 50, ...; 34 qubits) | 1.59e-3 [1.58e-3, 1.63e-3] | 1.54e-3 [1.51e-3, 2.03e-3] | - |
| `build_step(0.37, 0.61, order 1)` | 1.89e-3 [1.84e-3, 2.12e-3] | 1.81e-3 [1.77e-3, 1.85e-3] | - |
| `build_step(..., order 2)` | 2.11e-3 [2.07e-3, 2.35e-3] | 2.14e-3 [1.86e-3, 2.48e-3] | - |
| `evaluate(build_UE(0.37))` | 6.70 [6.61, 6.84] | 2.02 [2.00, 2.08] | 578 [577, 578] |
| `evaluate(build_UB(0.61))` | 8.16 [8.05, 8.22] | 2.31 [2.28, 2.34] | 655 [654, 655] |
| `evaluate(build_step(.37,.61), order 1)` | 8.07 [8.04, 8.29] | 2.30 [2.29, 2.35] | 656 [655, 656] |
| `evaluate(build_step(.37,.61), order 2)` | 8.16 [8.05, 8.27] | 2.32 [2.31, 2.36] | 658 [658, 660] |
| `synthesize(build_UB(0.61), 1e-6)` | 1.62 [1.62, 1.64] (cold pygridsynth word cache) | 0.0286 [0.0280, 0.0291] | 657 |
| `evaluate(synth UB, tol=n_rot eps+1e-9)` (6 rotations, 1838 gates) | 8.22 [8.16, 8.27] | 3.56 [3.53, 3.60] | 657 |
| `synthesize(step order 1, 1e-6)` | 1.73 [1.71, 1.73] | 0.0339 [0.0328, 0.0345] | 685 |
| `evaluate(synth step 1)` (10 rotations, 2506 gates) | 12.14 [11.90, 12.20] | 7.35 [7.33, 7.57] | 685 |
| `synthesize(step order 2, 1e-6)` | 1.69 [1.69, 1.69] | 0.0382 [0.0376, 0.0393] | 685 |
| `evaluate(synth step 2)` (14 rotations, 3214 gates) | 12.11 [12.10, 12.10] | 7.53 [7.49, 7.61] | 685 |
| `paulo_circuit()` load from QPY | 0.351 (1 run) | - | - |
| `paulo_circuit()` `evaluate` (aer_mps, auto, 1 run) | 83.07 | - | 1488 |
| `python scripts/m1_results.py --out <scratch>` (full, incl. Paulo ~83 s; 1 run) | 212.0 | - | 1775 (process tree) |
| `pytest -n auto tests/acceptance/m0 tests/acceptance/m1` incl. slow, 3 runs: 56 passed each | **199.6 [197.6, 203.5]** | - | 2123 (children max) |
| `pytest -n auto tests/unit`, 3 runs: 178 passed each | **59.9 [59.7, 60.4]** | - | 938 (children max) |

Observations: all four exact-angle evaluations cost about the same warm (2.0-2.3 s) - circuit complexity is not the bottleneck, the inner-span set-up is; the cold start costs 4.7-5.9 s extra per process (as in 001). Synthesised circuits are 1.5-3.3x slower warm (1.8k-3.2k gates). `m1_results.py` at 212 s is dominated by the Paulo evaluation (83 s) plus the synthesised re-verifications at 4 values of $\varepsilon$ per circuit; the m0+m1 acceptance suite (199.6 s) is dominated by the slow tests. Spread (max-min)/median is < 6 % for all new calls above 100 ms.

## 3. Physics output unchanged
| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| 10 M0 tasks: outputs (counts, spectra, verdict fields, `t_table`, `ct_compile`, Paulo verdict) vs 001 | identical | identical on every key (programmatic dict comparison, `verdict_seconds` excluded) and bit-identical across the 3 repeats | exact | PASS |
| Paulo QPY: ok / engine / certified / block / leak amp / combined | True / aer_mps / True / $2.904794\times10^{-6}$ / $7.851069\times10^{-6}$ / $1.075586\times10^{-5}$ | identical in both the M0 task and the M1 task | $2\times10^{-5}$ | PASS |
| exact-angle verdicts (new): UE / UB / step1 / step2 op-norm | ok, at the span floor | $1.21\times10^{-13}$ / $2.42\times10^{-13}$ / $2.69\times10^{-13}$ / $2.74\times10^{-13}$; Gauss $5.3\times10^{-16}$ / $7.6\times10^{-16}$ / $3.9\times10^{-15}$ / $9.6\times10^{-16}$; sparse, certified, 0 outer bits read | $10^{-10}$ | PASS |
| synthesised $\varepsilon=10^{-6}$: UB / step1 / step2 op-norm vs $n_{\rm rot}\varepsilon+10^{-9}$ | within | $1.85\times10^{-6}$ ($\le6.0\times10^{-6}$) / $3.24\times10^{-6}$ ($\le1.0\times10^{-5}$) / $3.49\times10^{-6}$ ($\le1.4\times10^{-5}$); Gauss $1.9\times10^{-15}$ / $1.1\times10^{-7}$ / $5.5\times10^{-8}$; $n_{\rm rot}$ 6/10/14, $t_{\rm rot}$ 384/640/912; sparse, certified | as stated | PASS |
| `m1_results.py` re-run to scratch vs committed `results/twelve/{UE,UB,step}.json` | same | every key identical except seconds/provenance/file paths (0 diffs); `.qpy` and `.qasm3` byte-identical for all three | exact | PASS |
| Provenance fix: 3 files of `results/twelve` | one identical block, `git_dirty` False, `provenance_captured_at` present | blocks identical (`==` on the dicts); commit `a9702e5`, `git_dirty` False x3; `provenance_captured_at` = `2026-11-05T16:14:13Z` in all, equal to `timestamp_utc` | exact | PASS |
| `python tools/check_lock.py`; `~/.claude/bin/acceptance-check` | LOCK OK; PASS | `LOCK OK`; `PASS: tests/acceptance matches acceptance-v5` | - | PASS |
| `tests/acceptance/m0 + m1` incl. slow, 3 runs | all pass | 56 passed x3 | - | PASS |
| `tests/unit`, 3 runs | all pass | 178 passed x3 | - | PASS |

## 4. Verdict and notes
No physics-output change anywhere. No time regression above 10 % on any call longer than 100 ms. Three flags above the 10 % rule: (a) Paulo-evaluation peak memory +33 %, (b) and (c) warm `logical_metrics` and `t_table(qiskit=False)` +60 % (+6 ms). Neither affects correctness; the coordinator decides whether to log them as known issues for M2 (compression rounds call `logical_metrics` often, so (b)/(c) should be watched; 6 ms per call is negligible next to a 2.3 s evaluate).

Notes: unit-suite wall time is not comparable with 001 (178 vs 140 tests). The `compression round wall time` baseline named in project `CLAUDE.md` is still not measurable (M2 code pending). `m1.json` also contains the M0 re-run raw data (for the next comparison, use the "now" columns above as the M1 baseline: warm evaluate 2.0-2.3 s, cold 6.7-8.2 s, Paulo 83 s / 1.49 GB, m0+m1 acceptance 199.6 s, unit 59.9 s).

VERDICT: PASS (benchmark recorded; no physics change; 3 flags > 10 %: Paulo-evaluation RSS +33 %, warm `logical_metrics` and `t_table(qiskit=False)` +60 % / +6 ms - for the coordinator to log).
