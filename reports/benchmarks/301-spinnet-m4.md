# Benchmark report 301 - spinnet M4 (mode benchmark, M4 gate step 3)

- Date: 2026-11-13. Commit at start of the runs: `49e247e` (branch `merge-desktop-tracks`; HEAD moved to `a36d829` during the session, but `git diff 49e247e HEAD -- src scripts/m3_results.py scripts/m4_results.py scripts/m7_results.py` is empty, so no benchmarked file changed; the working tree also held other agents' uncommitted rishon files, none imported by anything timed here).
- Prompt in force for the track: `prompts/104` (§11 E1-E3). Gate: tester `reports/tests/404` (PASS), auditor `reports/audits/302` (PASS WITH NOTES; N1 fixed in `7d06d8e`, results regenerated in `92a4a93`). Previous benchmark (baseline): `reports/benchmarks/100-m3-spinnet.md` (M3, commit `9c0aee6`), raw `results/benchmarks/spinnet-m3.json`. Sister report for LSH: `reports/benchmarks/302-lsh-m7.md`.
- Raw numbers, all repeats, load per run: `results/benchmarks/spinnet-m4.json` (also all control runs). Scripts: `results/benchmarks/spinnet-m4-scripts/` (`bench_worker_m4.py`, `bench_driver_m4.py`, `analyze_m4.py`, `ab*.py`, `physdiff.py`, ...). Scratch outputs: `scratch/bench-m4m7/` (gitignored).
- Machine: `omnicommander` = the former supremecommander desktop (same hardware as report 100: Intel i7-12700KF, 20 logical CPUs, 31 GiB, no GPU) **on a new OS install** (Omarchy, Linux 7.2.15), python 3.12.16, numpy **2.5.4**, scipy **1.18.1** (report 100: 2.5.2 / 1.18.0), qiskit 2.5.2, qiskit-aer 0.17.2, pygridsynth 1.2.0. `OMP/OPENBLAS/MKL_NUM_THREADS=1`, `PYTHONHASHSEED=20261104`. **CPU placement differs from 100**: I was assigned CPUs 14-19. CPU 14-15 are the two SMT threads of P-core 7; CPUs 16-19 are four E-cores (3.8 GHz max, lower IPC). Single-process tasks were pinned to CPU 14 (a P-core thread); suites and loop runs to `taskset -c 14-19` with `-n 6`, i.e. a mix of P- and E-core threads. Report 100 used CPUs 0-9 (P-core threads only) and `-n 10`.
- Machine load: 1-min load average read before every run is stored in the JSON. Single-process tasks 3.1-3.5 (fuzzy round evaluation on CPUs 12-13 plus other agents); scripts 3.5-4.2; suites 3.5-8; unit run 3 started at load 12.6 (other agents' jobs rose to 25-30 during the session). `uptime` at start: `07:23:26 up 2 days, 17:33, load average: 3.12, 1.94, 1.25`.
- Seeds: no stochastic call is timed (`ct_compile` 12345, transpiler 20261104, angle set 20261107 are used by the scripts under test).
- Method: as in 100 (one task per fresh process, "first" = first call of the process, "later" = pooled remaining calls; median [min, max]); 3 processes per task (5 for the encoding build), 3 runs per script / suite / loop command. Parameters: $\alpha=0.37$, $\beta=0.61$, $j_{\max}=1/2$ (433 physical states, 47 inner codes), $\varepsilon=10^{-6}$, engine `sparse`.
- Files touched by my runs: `results/spinnet/certs/*.json` (5) and `results/lsh/certs/*.json` (1) were rewritten by the pytest runs and restored with `git checkout -- results/spinnet/certs results/lsh/certs`; new untracked: `results/benchmarks/{spinnet-m4.json,lsh-m7.json,spinnet-m4-scripts/}`, `scratch/` (ignored). The loop was run only against scratch roots (`--root scratch/bench-m4m7/root_*`), never against `compress/`.

## Verdict

**No code regression; physics unchanged.** Compared directly with report 100, all the exact-angle spin-network `evaluate` rows and the encoding build are 16-31 % slower (flag, section 2). I traced this to the environment, not the code, with a control: the M3 commit `9c0aee6` (extracted with `git archive`, same worker script) run interleaved with HEAD on this machine in the same hour gives HEAD/old = 0.94-1.05 on every per-call quantity and 0.96 on `m3_results.py` (section 5). So the +25 % in the 100-vs-now comparison is the machine state (new OS install, numpy 2.5.4/scipy 1.18.1 instead of 2.5.2/1.18.0, CPU governor and frequency, P-core SMT/E-core placement and load), and the numbers below are a **new baseline for omnicommander**. Cause of the +25 % itself is a guess (environment); the control only excludes the repository code.

## 1. Route A (exact) and encoding build (fresh process, CPU 14)

| quantity | first, s | later, s | peak RSS, MB | note |
|---|---|---|---|---|
| route A `physical_basis()` cold | 0.0778 [0.0735, 0.0799] | - | 156 | report 001: 0.299 s on the laptop; no desktop value |
| route A `h_magnetic_phys(basis)` | 0.108 [0.069, 0.122] | 0.0401 [0.0326, 0.0487] | 156 | laptop 003: 0.195 / 0.0698 |
| route B `h_magnetic_phys_6j` | 0.00509 [0.00506, 0.00513] | 0.00491 [0.00468, 0.00525] | - | laptop 003: 0.0149 / 0.0149 |
| `target(step)` / `target(UB)` (exact `expm`) | 0.120 / 0.116 | 0.114 / 0.110 | - | laptop 003: 0.243 / 0.222 |
| `SpinNet()` build | 0.1867 [0.1782, 0.232] | 0.0646 [0.0523, 0.0800] | 199 | report 100: 0.1615 / 0.0501 (+15.6 % / +29 %) |
| `enc.target("UB", None, beta)` | 0.0191 | 0.0110 | - | 100: 0.0179 / 0.0094 (+6.6 % / +17 %) |
| circuit builders `build_UB` / `build_step` (warm) | 0.064 / 0.069 (cold) | 0.00131 / 0.00142 | - | 100: 0.0012-0.0013 warm |

Route A and the encoding build take under 0.2 s in total; none is a bottleneck. The +15..29 % on `SpinNet()` is of the same size as the `evaluate` shift of section 2 (absolute difference 0.025 s cold, 0.015 s warm); a control for `SpinNet()` alone: HEAD/old = 1.119 cold (noisy, 4 processes) and 1.017 warm (`results/benchmarks/spinnet-m4.json::control_AB`).

## 2. `evaluate` per circuit and synthesised verification, vs report 100

All verdicts: ok, certified, engine `sparse`, 0 outer bits read, leak amplitude 0 (exact-angle circuits). "change" is now versus report 100 (a different OS state, see the Verdict).

| circuit | first, s (now) | first, s (100) | change | later, s (now) | later, s (100) | change | RSS, MB |
|---|---|---|---|---|---|---|---|
| general $U_B$ (`build_UB`, 15 q) | 0.606 [0.601, 0.656] | 0.503 | +20.6 % | 0.2089 [0.1819, 0.2196] | 0.1673 | +24.9 % | 238 |
| $U_E$ | 0.174 | 0.150 | +16.2 % | 0.1702 [0.1607, 0.1828] | 0.1445 | +17.8 % | 193 |
| general step order 1 | 0.638 | 0.501 | +27.3 % | 0.2115 [0.194, 0.2187] | 0.1678 | +26.1 % | 238 |
| general step order 2 | 0.635 | 0.502 | +26.5 % | 0.2120 [0.1834, 0.2275] | 0.1673 | +26.7 % | 238 |
| `pairs9` | 0.659 | 0.502 | +31.1 % | 0.2049 [0.1845, 0.2319] | 0.1656 | +23.7 % | 238 |
| `flags4` | 0.633 | 0.504 | +25.6 % | 0.2057 [0.1958, 0.2186] | 0.1657 | +24.1 % | 238 |
| $U_B$ with outer register (23 q, `physical`) | 0.636 | 0.500 | +27.2 % | 0.2123 | 0.1665 | +27.5 % | 237 |
| Paulo 15-qubit file, gauge-fixed | 0.199 | 0.169 | +18.0 % | 0.223 [0.1975, 0.3016] | 0.1661 | +34.2 % | 193 |
| **M4 headline `r02-F1-002`** (31 CX, 17 q; rebuilt from its program in the sandbox, build 0.63 s) | 0.226 [0.216, 0.246] | new | - | 0.2078 [0.1886, 0.2281] | new | - | 240 |
| 12-qubit $U_B$ (`TwelveQubit`, same call as 100/002) | 3.321 [3.135, 3.443] | 3.072 | +8.1 % | 0.872 [0.835, 0.903] | 0.797 | +9.4 % | 663 |
| synthesised $U_B$ ($\varepsilon=10^{-6}$), `synthesize` | 0.457 | 0.424 | +7.9 % | 0.00285 | 0.00279 | +2.2 % | 239 |
| synthesised $U_B$, `evaluate` (4 rot, 808 gates) | 0.220 | 0.211 | +4.3 % | 0.2083 [0.2080, 0.2128] | 0.2006 | +3.8 % | 239 |
| synthesised step 1, `synthesize` | 0.479 | 0.446 | +7.5 % | 0.00427 | 0.00420 | +1.6 % | 242 |
| synthesised step 1, `evaluate` (8 rot, 1476 gates) | 0.264 | 0.253 | +4.4 % | 0.2464 [0.2444, 0.2833] | 0.2349 | +4.9 % | 242 |
| **synthesised headline** (17 rot, $t_{\rm rot}=1070$, 2808 gates, 17 q), `synthesize` | 0.537 | new | - | 0.00712 | new | - | 245 |
| synthesised headline, `evaluate` | 0.315 | new | - | 0.2975 [0.2935, 0.3011] | new | - | 245 |
| Lean certificate of the headline (export + `su2plaq_cert_spinnet check`, with the 0.5 s program rebuild excluded) | 1.361 [1.312, 1.455] (check 0.705) | new | - | - | - | - | 329 |

Physics in the same runs (op-norm error; all within $10^{-10}$, synthesised within $n_{\rm rot}\varepsilon+10^{-9}$): $U_B$ $1.085\times10^{-14}$, $U_E$ $4.44\times10^{-16}$, step 1/2 $1.146\times10^{-14}$ / $1.133\times10^{-14}$, `flags4` $9.17\times10^{-15}$, `pairs9` $6.46\times10^{-15}$ (100: $7.9\times10^{-15}$; rounding-level change, $\ll$ tolerance), outer-register $U_B$ $1.035\times10^{-14}$, headline $5.13\times10^{-15}$ (Gauss $5.3\times10^{-16}$), synthesised $U_B$ $1.303\times10^{-6}$ (identical to 100), step 1 $2.381\times10^{-6}$ (identical), synthesised headline $4.89\times10^{-6}\le17\times10^{-6}+10^{-9}$.

**Flag (vs report 100):** the exact-angle `evaluate` rows are +16..+31 % and the 12-qubit rows +8..+9 %, above the 10 % threshold for the spin-network rows. The synthesised rows are only +4..+8 %. Cause: environment (section 5 control), not code.

## 3. Compression round and evaluator per circuit (round 5 of spinnet re-evaluated in scratch)

The loop CLI takes `--root`. For each repetition I built a fresh scratch root (`results/benchmarks/spinnet-m4-scripts/make_root.sh`): a copy of `compress/` (programs, archive, attempts, briefs; evaluation cache emptied) with the three round-5 entries and their attempts-log lines removed, then ran `python -m su2plaq.spinnet.loop round --round 5 --evaluate --no-lean --root <scratch>` under `tools/run-capped taskset -c 14-19`. `--no-lean` because round 5 produced no new best (Lean is skipped for non-best entries anyway; its time would be 0 s as in the committed `round-005.json`).

| quantity | median [min, max] | RSS, MB | load before | comparison |
|---|---|---|---|---|
| round 5, 3 programs (F1 `005-nor3-direct-pair`, F2 `005-angle-linear-design-interpreter`, F3 `005-angle-linear-walk`), wall incl. process start, gridsynth disk cache warm | 6.64 [6.38, 6.67] s | 244 | 3.5-3.7 | no baseline round time exists for spinnet; committed per-entry `wall_s` (2026-11-10, same host): 2.21 / 2.62 / 2.15 s, sum 6.98 s |
| same, gridsynth cache empty | 6.62 [6.61, 6.64] s | 245 | 3.7-4.2 | cache has no measurable effect (the cache holds only angles seen in earlier rounds; all three programs reuse the rotation angles) |
| per-entry `wall_s` inside the round (now, warm) | F1 1.776, F2 2.223, F3 1.782 s (sum 5.78 s) | - | - | committed sum 6.98 s: -17 % (faster) |
| `loop candidate <headline program> --full` (one program, nominal + 2 alternate angle pairs, fresh process) | 2.62 [2.57, 2.64] s | 243 | 4.1 | `wall_s` of the headline entry at round 2 on the old OS: 1.368 s in process (the CLI wall of 2.6 s also contains process start, imports and the 3 evaluations of one program) |
| `loop candidate` F1-005 / F2-005 / F3-005 `--full` | 2.62 [2.57, 2.74] / 3.35 [2.98, 3.45] / 2.95 [2.92, 3.03] s | 243 | 4.1 | - |

Physics: the three re-evaluated entries have key $(\mathrm{CX},T,\mathrm{depth}_{CT},q)$ = (32, 834, 1565, 18), (31, 1086, 2262, 17), (32, 832, 1552, 17), identical to the committed `compress/archive/spinnet/entries/r05-*.json`; a field-by-field comparison (excluding timestamps, machine, wall, commit) of all three entries, in both the warm and the cold run, finds 0 differing fields (`results/benchmarks/spinnet-m4.json::physics_diff`). The best key stays (31, 1062, 2173, 17). A round of three programs is about 7 s, i.e. the loop is limited by proposer sessions, not by the evaluator.

## 4. Scripts and suites (CPUs 14-19, `-n 6` for pytest)

| quantity | runs, s | median [min, max], s | peak RSS (largest process), MB | load before | comparison |
|---|---|---|---|---|---|
| `scripts/m3_results.py --out scratch` | 10.97, 10.63, 10.48 | 10.63 [10.48, 10.97] | 293 | 4.0-4.2 | 100: 8.91 s (+19 %); control old-vs-HEAD on this machine: 10.96 s vs 10.47 s (HEAD -4.5 %, 4 interleaved runs each) |
| `scripts/m4_results.py --root <scratch root> --out scratch` (headline rebuild, 4 eps x re-verification, Lean cert reused, theorem file elaboration) | 6.96, 6.86, 6.95 | 6.95 [6.86, 6.96] | 818 | 3.8-4.2 | new; output equal to committed `m4-compressed.json` in every field except provenance (0 diffs) |
| `pytest tests/acceptance/m0 m1` (56 tests incl. slow), `-n 6` | 109.5, 107.5, 107.3 | 107.5 [107.3, 109.5] | 2139 | 3.5-6.3 | 100: 64.8 s at `-n 10` on P-cores; same tests, `-n 6`, HEAD vs `9c0aee6` tree on this machine: 107.5 vs 117.8 s [117.2, 124.4] (loads 3.5-6.3 vs 7.7-8.8): HEAD 8.8 % faster |
| `pytest tests/acceptance/m3 m3x m4` (47 tests, m4 incl. slow L5/R1 and Lean), `-n 6` | 54.0, 56.8, 55.9 | 55.9 [54.0, 56.8] | 6786 (Lean process) | 5.1-7.8 | no baseline (100 timed m0+m1+m3 = 67.9 s at `-n 10`: m3 alone cannot be separated); gate report 404: 43.8 s for m4 alone in the full run |
| `pytest tests/unit` (943 tests), `-n 6` | 484.1, 504.9, 573.9 | 504.9 [484.1, 573.9] | 6780 | 6.2, 6.1, 12.6 | 100: 25.7 s for 295 tests; per test 0.54 s now vs 0.087 s then, because the suite now holds the heavy compress/Lean/rishon/fuzzy/lsh tests; gate reports: 355 s (407, quiet) and 644 s (404, load 19-21): this run is in between and load-dependent (run 3 started at load 12.6) |

The 6.6-6.8 GB suite peak RSS is the Lean (`lake`) process of the Lean-calling tests (as in 100: 6.66 GB), inside the 22 GB per-job cap.

## 5. Control: is the +25 % the code or the machine?

Same worker script and same Python environment, code from `git archive 9c0aee6` (the report-100 commit; scratch tree `scratch/old-9c0aee6`) vs HEAD, tasks alternated old/new in the same hour, CPU 14, loads 7-10. Ratio = HEAD / old (medians); two independent runs (4 and 8 interleaved repetitions of fresh processes):

| quantity | old (9c0aee6), s | HEAD, s | HEAD / old |
|---|---|---|---|
| `evaluate(build_UB)` later, run 1 (4 reps) | 0.2121 | 0.2234 | 1.054 |
| `evaluate(build_UB)` later, run 2 (8 reps) | 0.2153 | 0.2063 | 0.958 |
| `evaluate(build_step 1)` later, run 2 | 0.2207 | 0.2069 | 0.937 |
| `evaluate(build_UE)` later, run 1 / run 2 | 0.1959 / 0.1913 | 0.1905 / 0.1810 | 0.973 / 0.946 |
| `evaluate(build_UB)` first, run 1 / run 2 | 0.6687 / 0.6444 | 0.6166 / 0.6499 | 0.922 / 1.008 |
| 12-qubit `evaluate(build_UB)` first / later (run 1) | 3.792 / 0.951 | 3.703 / 0.959 | 0.977 / 1.008 |
| synthesised $U_B$ `evaluate` later (run 1) | 0.2521 | 0.2541 | 1.008 |
| route A `h_magnetic_phys` first / later | 0.1086 / 0.0401 | 0.1001 / 0.0420 | 0.923 / 1.047 |
| `m3_results.py` wall (4 runs each) | 10.96 | 10.47 | 0.955 |
| m0+m1 acceptance `-n 6` | 117.8 | 107.5 | 0.912 |

Old code on this machine today gives 0.212 s for `evaluate(build_UB)`, i.e. +27 % over the 0.1673 s measured in report 100: the shift is in the environment. The evaluator did change since `9c0aee6` (`git diff` shows the `states=` subset option and `fancy-index` copies in `evaluate`, plus the `word_fn` argument of `synthesize`), and its cost is within the noise (HEAD/old between 0.94 and 1.05). One more observation on the noise: the same task repeated at different times of the session moved by up to about 10 % (HEAD `evaluate(build_UB)` later 0.2089 in the main run, 0.2063 and 0.1925 in two later interleaved runs).

## 6. Physics output unchanged

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| headline `r02-F1-002` counts | 31 CX / 17 rot / $T_{\rm fixed}$ 16 / 17 qubits | 31 / 17 / 16 / 17 (depth 48, 1 ancilla) | exact | PASS |
| headline `m4_results.py` rerun vs committed `results/spinnet/m4-compressed.json` | identical | 0 differing fields (provenance, seconds, files excluded) | exact | PASS |
| round 5 (3 entries, warm and cold cache) vs committed archive entries | identical | 0 differing fields; keys (32,834,1565,18), (31,1086,2262,17), (32,832,1552,17) | exact | PASS |
| `m3_results.py` rerun vs committed `results/spinnet/{UE,UB,step}.json` | same counts and errors | all integer / string fields identical (except the recorded path of the Paulo file: old host path); floats differ by at most $1.4\times10^{-15}$ absolute and $6\times10^{-8}$ relative on quantities of size $10^{-6}$..$10^{-4}$ (i.e. rounding noise at the $10^{-15}$ absolute level in the synthesised-circuit errors; guess: BLAS/numpy version difference, the committed M3 JSON was produced under numpy 2.5.2) | counts exact; errors $\ll10^{-10}$ | PASS |
| op-norm errors of all timed circuits | as in 100 | equal to 3-4 digits (`pairs9` $6.5\times10^{-15}$ vs $7.9\times10^{-15}$) | $10^{-10}$ | PASS |
| Lean certificate of the headline | certified | `certified` (3 of 3 runs, checker sha256 `ec00aa45...`) | - | PASS |
| `pytest m0 m1 m3 m3x m4 unit` | all pass | 56 / 47 / 943 passed, 0 failed (all 3 runs each) | - | PASS |
| `tools/check_lock.py`, `acceptance-check` (end of run) | OK | `LOCK OK`; `PASS: tests/acceptance matches acceptance-v19` | - | PASS |

## Flags and notes

1. vs report 100 the `evaluate` quantities of the spin-network circuits are +16..+31 % slower (12-qubit +8..9 %, synthesised +4..8 %). Guess: new OS install / numpy 2.5.4 / CPU governor and P-core vs E-core placement; **excluded as a code regression** by the old-vs-HEAD control (HEAD/old 0.94-1.05).
2. Report 100 is not a like-for-like baseline for suites (`-n 10` on P-cores vs `-n 6` on a P/E mix); the like-for-like comparison is the old-vs-HEAD pair of section 4/5 (HEAD 9 % faster on m0+m1, 4.5 % faster on `m3_results.py`).
3. Unit-suite wall time varies 484-574 s with the other agents' load (run 3 at load 12.6). Not a regression; the per-test cost has grown with the test mix.
4. No baseline existed for compression-round and headline-evaluation times; sections 1-4 are the new baseline for this machine.
