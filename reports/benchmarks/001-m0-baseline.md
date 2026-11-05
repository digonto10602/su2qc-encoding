# Benchmark report 001 - M0 baseline (mode benchmark)

- Date: 2026-11-04 (run finished 22:36 local). Commit: `30b38a0` (source tree clean; `git status` shows only `notes/STATUS.md` modified and the untracked `reports/audits/002-*.md`, `results/benchmarks/`, so `provenance().git_dirty = true` is due to STATUS.md only).
- Prompt in force: `prompts/004-leak-amplitude-combined-error-bound.md` (on top of 003, 002). Auditor: `reports/audits/001` + `002` (PASS WITH NOTES). Related tests: `reports/tests/012`, `013`, `014`. Previous benchmark: none, this report sets the baseline.
- Machine: Intel Core i7-8750H @ 2.20 GHz (12 logical CPUs), 62 GB RAM, no GPU used, load average 0.46 before start, nothing else running. `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1`, `PYTHONHASHSEED=20261104`; pytest-xdist `-n auto` = 12 workers.
- Versions: python 3.12.14, numpy 2.5.2, scipy 1.18.0, qiskit 2.5.2, qiskit-aer 0.17.2, pygridsynth 1.2.0.
- Seeds: 20261104 (benchmark; no stochastic call is timed), `ct_compile` seed 12345 (its default, as in reports 012/014).
- Parameters: $\alpha=0.37$, $\beta=0.61$, $j_{\max}=1/2$ (dim 433); Paulo QPY vs $U_B(\beta=1)$ with `tol_err = tol_gauss = 2e-5`, `engine="auto"`; $\varepsilon\in\{10^{-4},10^{-6},10^{-8},10^{-10}\}$; `ct_compile` $\varepsilon=10^{-6}$, level 3.
- Raw numbers: `results/benchmarks/m0-baseline.json` (all repeats, provenance). Scripts: `results/benchmarks/scripts/bench_worker.py` (one task per fresh process), `bench_driver.py`.

## Method
Each task runs in a **fresh process** (3 processes per task; the Paulo QPY evaluation 1 process). Inside a process the call is repeated: "first" is the first call of the fresh process (cold: includes lazy caches such as `lru_cache` of Wigner/CG, the pygridsynth word cache, Qiskit's lazy transpiler/pass-manager set-up); "later" is the remaining calls (3 more for evaluate/ops, 2 more for metrics). Setup (building circuits, targets, encoding) is outside the timer. Wall time by `time.perf_counter`, peak RSS from `resource.getrusage(RUSAGE_SELF).ru_maxrss` at process end (whole process, includes imports ~ 55 MB). Statistic: **median [min, max]** over the processes (first) or over all later calls (later). Times in seconds.

```
python results/benchmarks/scripts/bench_driver.py      # tasks: basis ops eval_id_span eval_id_phys eval_ue eval_outer3 metrics metrics_q metrics_c paulo_eval, then
pytest -n auto -q tests/acceptance/m0 (x3) ; pytest -n auto -q tests/unit (x3)
python tools/check_lock.py ; ~/.claude/bin/acceptance-check      # LOCK OK ; PASS: tests/acceptance matches acceptance-v4
```

## 1. Exact (route A / route B) builds - problem size: 433 physical states, 625 inner codes, 3153 outer patterns
| call | first call (cold), s | later calls (warm), s | peak RSS of process, MB |
|---|---|---|---|
| `import su2plaq.exact.physical, geometry` | 0.213 [0.213, 0.219] | - | 59.5 (whole `basis` task) |
| **`physical_basis()` cold** (fresh process, all caches empty) | **0.295** [0.290, 0.302] | - | 59.5 [59.4, 59.6] |
| `physical_basis()` warm, module `_CACHE` hit | 5.4e-6 | 7.9e-7 [5.7e-7, 2.2e-6] | - |
| `physical_basis(diagram=plaquette_diagram())` (bypasses `_CACHE`, `lru_cache`s warm) = warm rebuild | 0.171 [0.166, 0.179] | 0.174 [0.164, 0.179] | - |
| `spinnet.labels(0.5)` | 0.0211 [0.0208, 0.0228] | 0.0207 [0.0205, 0.0210] | - |
| **route B `h_magnetic_phys_6j(labels)`** | **0.0150** [0.0149, 0.0151] | 0.0147 [0.0143, 0.0149] | - |
| `h_magnetic_phys(basis)` (route A, includes `_W_cached` build on first call) | 0.200 [0.198, 0.201] | 0.0694 [0.0687, 0.0794] | - |
| `target(basis,'step',0.37,0.61)` (builds $e^{-i\beta H_B}$, 433$\times$433 `expm`) | 0.243 [0.241, 0.244] | 0.243 [0.242, 0.244] | - |
| `target(basis,'UB',None,0.61)` | 0.221 [0.219, 0.221] | 0.221 [0.221, 0.221] | - |
| `target(basis,'UE',0.37)` | 9.6e-4 | 8.6e-4 | - |
| whole `ops` task (route A + B + targets together) | - | - | 148 [147.8, 148.0] |

Observation: route A is dominated by the one-off basis build (0.30 s cold, 0.17 s with warm CG/6j caches); `expm` costs 0.22-0.24 s per target; route B is 15 ms. Nothing here is a bottleneck; the total exact-side set-up is below 1 s.

## 2. `evaluate` (12-qubit encoding, sparse engine unless stated)
| circuit / target | method (as chosen) | outer bits read | first call (cold), s | later calls, s | peak RSS, MB |
|---|---|---|---|---|---|
| identity, target $\mathbb 1$, `method="inner_span"` | inner_span | 0 | 6.74 [6.69, 6.98] | 2.03 [2.01, 2.08] | 571 [570, 571] |
| identity, target $\mathbb 1$, `method="physical"` | physical | 0 | 1.39 [1.37, 1.42] | 0.932 [0.911, 0.949] | 226 [224, 226] |
| exact $U_E(0.37)$ = `p(-0.75*alpha)` on $q_j$ of the 4 inner links (qubits 2,5,8,11), target `target(basis,'UE',0.37)` | inner_span (auto) | 0 | 6.65 [6.63, 6.81] | 2.02 [2.00, 2.06] | 574 [574, 575] |
| 3 outer bits: `p(-0.75*alpha)` on the $q_j$ of outer links 0,1,2 (qubits 1,3,5 of `o`), target = diag$(e^{-i\alpha\sum_{k<3}j_k(j_k+1)})$ (own construction) | physical (auto), 8 blocks | 3 | 1.43 [1.40, 1.43] | 0.991 [0.976, 1.003] | 229 [229, 231] |
| **Paulo's QPY** (34 qubits, 294 CX, 1162 T) vs $U_B(\beta=1)$, `engine="auto"` | inner_span, **aer_mps** | 0 | **83.1** (1 run only) | - | **1127** |

The cold first call is 3.3x (inner_span) / 1.5x (physical) the warm one: the evaluator's lazy `_phys_data` / span-basis construction is paid on the first call per process (about 4.7 s for inner_span; in a compression loop this is paid once per worker process).

## 3. Metrics (Paulo's uncompiled circuit rebuilt from cells 3-23 of `refs/paulo/optimized_plaquette_dontcare_lowT.ipynb`, as in reports/tests/012: 34 qubits, $n_{\rm rot}=14$, $T_{\rm fixed}=296$)
| call | first call (cold), s | later calls, s |
|---|---|---|
| rebuild the circuit (exec cells + build) | 0.0068 [0.0062, 0.0068] | - |
| `logical_metrics(qc)` | 1.30 [1.29, 1.34] (Qiskit lazy set-up) | 0.0104 [0.0099, 0.0110] |
| `t_table(qc, qiskit=False)` (4 $\varepsilon$ values, pygridsynth on 14 angles each) | 2.01 [1.99, 2.01] (cold pygridsynth word cache) | 0.0107 [0.0103, 0.0109] (word cache hit) |
| `t_table(qc, qiskit=True)` after `t_table(False)` in the same process | 0.282 [0.282, 0.283] | 0.277 [0.276, 0.280] |
| `t_table(qc, qiskit=True)` as the first call of a fresh process (cold everything) | 3.66 [3.63, 3.75] | 0.277 [0.275, 0.285] |
| `ct_compile(qc, 1e-6, level=3, seed=12345)` on Paulo's uncompiled circuit, first call of a fresh process | 0.0767 [0.0765, 0.0767] | 0.0627 [0.0624, 0.0631] |
| peak RSS of the process | 207 [207, 207] (`metrics`), 206 (`metrics_q`), 123 (`metrics_c`) MB | |

## 4. Suites (3 runs each, `-n auto`, 12 workers, `OMP/OPENBLAS/MKL_NUM_THREADS=1`)
| suite | result | wall, s (median [min, max]) | largest single-process RSS, MB |
|---|---|---|---|
| `tests/acceptance/m0` (incl. slow) | 34 passed x3 | **33.4** [33.1, 34.2] | 638 |
| `tests/unit` | 140 passed x3 | **47.7** [47.5, 47.9] | 674 |

## 5. Physics output unchanged vs reports/tests/014 (and 005, 006, 012 for the quantities 014 did not re-run)
Outputs are bit-identical across the 3 repeats in all 10 tasks (checked on the JSON minus timings).

| quantity | expected (report) | got | tolerance | verdict |
|---|---|---|---|---|
| `physical_basis` counts (433 / closed 2 / link strings 256 / ambiguous 95 / far-end weighted 17362) | same (004) | same | exact | PASS |
| spectrum $H_B$ route A: $-2(16),-1(96),-\tfrac12(16),0(177),\tfrac12(16),1(96),2(16)$ | same (005) | same | exact multiplicities | PASS |
| route A vs route B spectrum, $\max|\Delta\lambda|$ | $\le1.1\times10^{-14}$ (006) | $2.66\times10^{-15}$ | $10^{-13}$ | PASS |
| $H_B$ Hermitian error / physical leak / step unitarity $\|U^\dagger U-1\|_\infty$ | 0 / $\sim10^{-15}$ / $\sim10^{-15}$ | $0.0$ / $1.1\times10^{-15}$ / $4.4\times10^{-16}$ | $10^{-12}$ | PASS |
| identity circuit, `inner_span` | block $1.2068\times10^{-13}$ (014 N2) | $1.2068\times10^{-13}$, ok, leak 0, Gauss $5.4\times10^{-16}$ | $10^{-10}$ | PASS |
| identity, `physical` | block $3.4\times10^{-15}$ (014 N2) | $3.4024\times10^{-15}$ | $10^{-10}$ | PASS |
| exact $U_E(0.37)$ as 4 `p` gates | ok, error at the span floor | ok, op-norm $1.2068\times10^{-13}$ (same floor as identity), Gauss $5.3\times10^{-16}$ | $10^{-10}$ | PASS |
| 3 outer bits circuit | (new; no earlier number) ok, 8 blocks | ok, op-norm $4.34\times10^{-15}$, 3 bits read, 8 blocks | $10^{-10}$ | PASS (new baseline) |
| Paulo QPY: ok / reason / engine / certified / engine accuracy | True / ok / aer_mps / True / $2\times10^{-10}$ | identical | exact | PASS |
| Paulo QPY block error | $2.9048\times10^{-6}$ | $2.904794\times10^{-6}$ | $1.6\times10^{-5}$ | PASS |
| Paulo QPY leak amplitude | $7.8511\times10^{-6}$ | $7.851069\times10^{-6}$ | $2\times10^{-5}$ | PASS |
| Paulo QPY combined op-norm | $1.0756\times10^{-5}$ | $1.075586\times10^{-5}$ | $2\times10^{-5}$ | PASS |
| Paulo QPY `max_leak`, `dirty_ancilla`, Gauss | $6.164\times10^{-11}$, $8.77\times10^{-20}$, $1.160\times10^{-10}$ | $6.1639\times10^{-11}$, $8.770\times10^{-20}$, $1.15998\times10^{-10}$ | - | PASS |
| `logical_metrics` | cx 294, depth 391, $n_{\rm rot}$ 14, $T_{\rm fixed}$ 296, 34 qubits, 22 ancilla, same gate dict (012) | identical | exact | PASS |
| `t_table(qiskit=True)` all 4 rows, all 9 columns | `results/tester_012_metrics_step09.json::t4_table` | identical (e.g. $\varepsilon=10^{-6}$: pygridsynth 884, total 1180, $t_{\rm est}$ 1133.13, Qiskit 1096) | $10^{-9}$ | PASS |
| `t_table(qiskit=False)` T columns | same as above | identical | exact | PASS |
| `ct_compile` on the uncompiled circuit | cx 294, T 1162, depth 2549, gates h1155 t1027 s504 cx294 tdg135 sdg92 (012, 014) | identical | exact | PASS |
| `python tools/check_lock.py`; `~/.claude/bin/acceptance-check` | LOCK OK; PASS (v4) | `LOCK OK`; `PASS: tests/acceptance matches acceptance-v4` | - | PASS |

No physics output changed. Paulo QPY wall time: 83.1 s (reports/tests/014: 84.1 s; 013/011 era: 108 s before the audit fixes) - within run-to-run noise.

## 6. Comparison with the previous benchmark
None exists, so there is nothing to compare and no regression flag can be raised. From now on the **baseline numbers to beat** (regression threshold 10 %, project `CLAUDE.md`) are the medians in sections 1-4. Suggested keys for later reports: `physical_basis_cold` 0.295 s, `h_magnetic_phys_6j` 0.0150 s, `evaluate` (warm / cold) = 2.03 / 6.74 s (inner_span identity), 0.932 / 1.39 s (physical identity), Paulo QPY 83.1 s, m0 suite 33.4 s, unit suite 47.7 s.

## 7. Notes (not failures)
1. Timing spread is small: (max - min)/median is $<6\%$ for every call longer than 100 ms with $\ge3$ repeats (checked on the JSON). Calls shorter than 100 ms scatter more: `physical_basis(diagram=...)` 8 %, `labels_6j` 9 %, `h_magnetic_phys` warm 15 % (0.0687-0.0794 s), `logical_metrics` warm 10 %, `target_UE` and `_CACHE` lookups (micro/millisecond) much more; apply the 10 % threshold to medians and treat sub-100 ms calls with care. The Paulo evaluation is a single run, so its spread is unknown (84.1 s earlier vs 83.1 s now suggests $\approx1\%$).
2. Memory: the dominant consumer is the Paulo evaluation (1.13 GB RSS, aer_mps); inner_span evaluations with the sparse engine peak at 0.57 GB; the test workers at 0.64-0.67 GB each.
3. `compression round wall time` (one of the quantities named in project `CLAUDE.md`) cannot be measured yet: M2 compress code (`default_spec`, `Archive.load`, `code_hash`, ...) is still PENDING. It is a baseline to add at the M2 gate.
4. `evaluate` first-call overhead of about 4.7 s (inner_span) and 0.45 s (physical) is lazy initialisation, paid once per process; a persistent worker avoids it.
5. Peak RSS is per process; the pytest figures are the largest single worker, not the sum over 12 workers.

VERDICT: PASS (benchmark baseline recorded; no earlier benchmark, no physics-output change vs reports/tests/014).
