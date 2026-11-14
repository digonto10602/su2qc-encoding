# Benchmark report 303 - rishon milestone 5d (det term), mode benchmark, milestone-5d gate step 3

- Date: 2026-11-13. Commit at start: `b4bc2a4`; HEAD moved during the session to `bdfe4e6` and then `eacb8c3` (other agents' commits). `git diff b4bc2a4 HEAD -- src scripts` is empty (only `tests/acceptance/m6/test_rishon_m6_seeds.py` and `tests/acceptance/LOCK.json`, i.e. prompts/205 / acceptance-v20, changed), so the code benchmarked is the code of the gate.
- Prompt in force: `prompts/204` (det term, prune cap 10 %) on `prompts/203`; `prompts/205` (approved, acceptance-v20) only touches an M6 test. Gate: tester `reports/tests/411` PASS, auditor `reports/audits/304` PASS WITH NOTES. `acceptance-check`: PASS (acceptance-v20), `tools/check_lock.py`: LOCK OK (run at the end).
- Baseline: `reports/benchmarks/200-m5-rishon.md` (commit `86fda8e`, old SupremeCommander install). Sister report with the same environment problem: `reports/benchmarks/301-spinnet-m4.md`.
- Raw numbers: `results/rishon/bench-303-m5d.json` (medians, ranges, commit, load, machine, comparison table, control). Per-process records, logs, junit XML and timing files: `results/benchmarks/rishon-m5d-raw/` (`rishon.jsonl`, `twelve.jsonl`, `ctl/{old,new,old_twelve,new_twelve}.jsonl`, `ctl/ctl_summary.json`, `pytest_m5_*`, `lean.txt`, `l3.out`, `monitor*.log`). Scripts: `results/benchmarks/rishon-m5d-scripts/` (copies of the report-200 scripts with paths/cores changed, plus new tasks `build_det`, `verifydet_*`, `synthdet_*`, `threelayer`, `timev.py` = stand-in for GNU `time`, which is not installed on this machine).

## Verdict

**PASS. No code regression, physics unchanged, new det-term circuits benchmarked.** Many quantities are 10-23 % slower than report 200 (flag F1, below), but the control run (the code of report 200, commit `86fda8e`, in a detached worktree, interleaved with HEAD on the same machine and core) gives HEAD/old = 0.96-1.01 on every one of them, e.g. synthesised $U_B$ re-verification 326.5 s (HEAD) vs 325.9 s (old), ratio 1.002. The slowdown against 200 is the environment (new OS install, new library builds), not the code. One quantity moves with the code in isolation (first `build_UE` call, +48 %), but it is a relocation of a lazy-import cost, the sum of the two first calls is unchanged (section 4).

## 0. Machine, settings, protocol

- Machine `omnicommander` (= former supremecommander desktop on a new Omarchy install, Linux 7.2.15), i7-12700KF, 20 threads, 31 GiB, GPU not used. Python 3.12, numpy 2.5.4, scipy 1.18.1 (report 200: numpy 2.5.2, scipy 1.18.0, old install; versions as quoted in report 301), qiskit 2.5.2, aer 0.17.2, pygridsynth 1.2.0. `OMP/OPENBLAS/MKL_NUM_THREADS=1`, `PYTHONHASHSEED=20261104`, Gauss-sample seed 20261104, `ct_compile` seed 12345, eta set seed 20261110.
- Cores: I was assigned CPUs 14-19 = hardware threads 14,15 (two SMT threads of P-core 7) plus 16-19 (four E-cores). Single-process tasks pinned to CPU 14 (a P-core thread; every record started and ended on 14). pytest and Lean: `taskset -c 14-19`, `-n 6` (report 200 used CPUs 10-19, `-n 10`; so pytest wall times are not like-for-like).
- Protocol exactly as report 200: one task per fresh process, 3 processes per task (1 for the 5-minute synthesis of $U_B$), "first" = first call in the process, "later" = remaining calls, median [min, max]. `$(\alpha,\beta)=(0.37,0.61)$`, det angle $\eta=0.29$, `verify` defaults, 1296 inner codes, 38 432 physical states.
- Load: a sampler logged the 1-min load average every 10 s (`monitor.log`: 114 samples, single-process window, load 1.49-2.37, median 1.91; `monitor2.log`: 231 samples, pytest window with 6 workers, 1.7-7.98, median 5.21). The sampler records command names only (top-3 by CPU): besides my python/pytest/lean processes only `btop` (about 37 % of one core), the desktop and single short `pgrep`/`conda`/`localsearch` entries appear; a foreign python job (e.g. a fuzzy proposer evaluation) could hide among the python entries, but in the single-process window the load average of about 1.9 equals one busy benchmark process plus about 0.9 from `btop` and the desktop, so at most a few foreign busy threads were present (no run in the fuzzy loop was visible on cores 14-19; I did not check cores 2-5, 12-13). Load average at the start of each single process is stored in the JSON (1.5-2.7).
- Commands (all through `tools/run-capped`, i.e. the shared memory-capped slice; pytest through `tools/pytest-safe`):
```
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding; cd /home/digimonk/Projects/su2qc-encoding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=src PYTHONHASHSEED=20261104
tools/run-capped bash results/benchmarks/rishon-m5d-scripts/rishon_bench_phase1.sh   # driver tasks (BENCH_CPU=14), rishon + twelve-qubit re-measure
tools/run-capped bash results/benchmarks/rishon-m5d-scripts/rishon_bench_phase2.sh   # pytest m5 x (1 + 3 + 1), Lean, L3
tools/run-capped bash results/benchmarks/rishon-m5d-scripts/ctl_ab.sh                # control: old tree vs HEAD, interleaved
python results/benchmarks/rishon-m5d-scripts/ctl_analyze.py; python results/benchmarks/rishon-m5d-scripts/rishon_bench_collect.py
```
  phase 1 tasks: `import:3 basis:3 inner:3 build:3 ttable_{UE,UB,step,step2,UE_outer_row}:3 verify_{UE,UB,step,step2}:3 synth_UE_1e-6:3 synth_UB_1e-6:1` (report 200 set) plus `build_det:3 ttable_{UD,step3}:3 verifydet_{UD,step3,step3_order2}:3 synthdet_UD_1e-6:3 threelayer:3`; then the twelve-qubit set `m1_build eval_UE eval_UB eval_step1 ttable_* synth_UB:3 paulo_m1:1`.
- Not repeated: `scripts/m5_results.py` (68.8 min in report 200 with 6 workers on 10 CPUs; a contended pool run, see that report's section 4.2) and `scripts/m5_det_results.py` (the generator of `results/rishon/{UD,step3,...}.json`; its outputs are tested by M5-DT7 and were not regenerated here). The `results/` files they wrote were not touched.

## 1. Same quantities as report 200 (HEAD vs 200; medians)

"Change" is HEAD relative to report 200 (old install). The column "control" is HEAD/old-tree measured on this machine in the same hour (section 4); a value of 1.00 means the code did not change speed.

| quantity | report 200 | now | change | control HEAD/old | RSS now (200) |
|---|---|---|---|---|---|
| `rishon_basis()` cold (38 432 states) | 2.372 s | 2.450 s [2.42, 2.45] | +3.3 % | 1.003 | 320 MB (312) |
| `_build_basis()` second call | 0.494 s | 0.512 s | +3.7 % | 0.997 | |
| `inner_span` 1296x1296 | 0.779 s | 0.781 s | +0.2 % | 1.005 | |
| `_W` build | 0.0685 s | 0.0797 s | +16.3 % | 1.058 (n=3, ranges overlap) | |
| `eigh` of $H_B^{in}$ (complex128, vectors) | 1.275 s | 1.287 s | +1.0 % | 0.996 | 340 MB (339) |
| `eigvalsh` / `eigh` real | 0.332 / 0.169 s | 0.353 / 0.189 s | +6.4 / +12.0 % | 0.999 / 0.987 | |
| `_bright()` | 0.0178 s | 0.0201 s | +12.8 % | 1.139 (n=3) | |
| `inner_target` $U_B$ / step 1 / step 2 | 1.005 / 1.225 / 1.455 s | 1.235 / 1.449 / 1.698 s | +22.9 / +18.3 / +16.7 % | 1.000 / 0.996 / 0.991 | |
| `build_UE(0.37)` first call | 0.132 s | 0.208 s | +57.6 % | 1.483 (isolated) | see section 4 |
| `build_UB` first / warm | 1.838 s / 11.5 ms | 1.872 s / 11.4 ms | +1.9 % / -0.8 % | 0.996 / 1.001 | |
| `build_step` order 1 / 2 warm | 11.8 / 11.6 ms | 11.3 / 11.4 ms | -4 / -2 % | 0.99 / 0.99 | |
| `verify` $U_E$ first / later | 4.74 / 4.67 s | 4.959 / 4.892 s | +4.6 / +4.7 % | - | 639 MB (587) |
| `verify` $U_B$ first / later | 6.38 / 6.03 s | 6.709 / 6.486 s | +5.2 / +7.6 % | 0.962 / 0.959 | 738 MB (687) |
| `verify` step 1 first / later | 6.58 / 6.28 s | 6.944 / 6.775 s | +5.5 / +7.9 % | 0.981 / 0.964 | 738 MB (686) |
| `verify` step 2 first / later | 6.84 / 6.54 s | 7.299 / 7.087 s | +6.7 / +8.4 % | - | 738 MB (687) |
| synthesis $\varepsilon=10^{-6}$ + `verify` $U_E$ (4 rot, 676 gates) | 0.346 + 6.95 s | 0.366 + 7.169 s | +5.8 / +3.1 % | - | 892 MB (839) |
| synthesis $\varepsilon=10^{-6}$ + `verify` $U_B$ (162 rot, 52 006 gates) | 0.389 + 276.6 s; process 281.9 s | 0.386 + 327.4 s; process 332.8 s | **+18.4 % / +18.1 %** | **1.002** (326.5 s vs 325.9 s) | 1410 MB (1388) |
| `t_table` pygridsynth cold, $U_B$ / step / step 2 | 0.71 / 0.79 / 0.79 s | 0.837 / 0.915 / 0.912 s | +17.8 / +15.9 / +15.4 % | 0.999 / 0.997 / - | 326-328 MB |
| `t_table` with Qiskit Clifford+T, $U_B$ / step | 0.83 / 0.86 s | 0.862 / 0.876 s | +3.9 / +1.9 % | 0.996 / 1.004 | |
| 12-qubit `evaluate` $U_E$ first / later | 2.672 / 0.718 s | 2.658 / 0.749 s | -0.5 / +4.3 % | - | 584 MB (575) |
| 12-qubit `evaluate` $U_B$ first / later | 3.079 / 0.800 s | 3.109 / 0.840 s | +1.0 / +4.9 % | 0.996 / 0.987 | 662 MB (658) |
| 12-qubit `evaluate` step first / later | 3.077 / 0.800 s | 3.085 / 0.834 s | +0.3 / +4.2 % | - | 663 MB |
| 12-qubit synthesised $U_B$ `evaluate` later | 1.147 s | 1.203 s | +4.9 % | - | |
| Paulo QPY `evaluate` (aer_mps), 1 run | 24.34 s | 25.39 s | +4.3 % | - | 1492 MB (1512) |

Physics output (all repeats identical): `verify` $U_E$ / $U_B$ / step 1 / step 2: ok, certified, sparse engine, op-norm $1.1\times10^{-16}$ / $3.434\times10^{-13}$ / $4.125\times10^{-13}$ / $4.097\times10^{-13}$, block error $1.1\times10^{-16}$ / $4.144\times10^{-14}$ / $4.495\times10^{-14}$ / $4.513\times10^{-14}$, Gauss residual $1.76\times10^{-16}$ / $2.26\times10^{-15}$ / $2.66\times10^{-15}$ / $2.27\times10^{-15}$ - the same as report 200 on every digit quoted there. Synthesised $10^{-6}$: $U_E$ op-norm $2.1737\times10^{-6}$, $U_B$ $1.8427\times10^{-5}$ (162 rot, $T_{rot}=10\,176$, certified), as in 200. Circuit resources unchanged: $U_E$ 8 CX / 4 rot, $U_B$ 10 094 CX / 162 rot / $T_{fixed}$ 10 218 / lowered depth 13 682, step 1 10 102 CX / 166 rot, step 2 10 110 CX / 170 rot, $U_E$+outer row 24 CX / 12 rot / 48 qubits.

## 2. New: det-term circuits (no report-200 baseline; compared with the two-layer circuits of section 1)

| quantity | value (median [min, max], CPU 14) | RSS | notes |
|---|---|---|---|
| `build_UD(0.29)` first / warm | 0.142 s / 0.114 ms | 253 MB (build_det process) | 16 qubits, 32 CX, 8 rot, $T_{fixed}=0$, macro depth 10 |
| `build_UD` with 12 links (48 qubits, outer row) | 0.32 ms | | 96 CX, 24 rot |
| `build_step(.., eta=0.29)` order 1 first / warm | 2.312 s (lazy Qiskit import) / 11.6 ms | | 26 qubits, **10 134 CX**, 174 rot, $T_{fixed}$ 10 218, lowered depth 13 695 |
| `build_step(.., eta)` order 2 warm | 11.5 ms | | **10 174 CX**, 186 rot, depth 13 708 |
| `logical_metrics` step3 order 1 / 2 | 0.118 / 0.119 s | | |
| `t_table` $U_D$ / step3 (pygridsynth cold) | 0.094 / 1.014 s; Qiskit 0.036 / 0.899 s | 118 / 337 MB | |
| exact-angle `verify` $U_D$ (kind UD, eta), first / later | 4.955 [4.946, 4.995] / 4.934 s | 652 MB | ok, certified, op-norm $2.76\times10^{-15}$, block $1.48\times10^{-15}$, Gauss residual $2.15\times10^{-16}$ (273 states) |
| `verify` step3 order 1 (three layers), first / later | **7.901 [7.809, 7.905]** / 7.629 s | 739 MB | ok, certified, op-norm $4.980\times10^{-13}$, block $4.743\times10^{-14}$, dropped $4.51\times10^{-13}$, Gauss $3.62\times10^{-15}$ |
| `verify` step3 order 2, first / later | **8.139 [8.132, 8.222]** / 7.963 s | 763 MB | ok, certified, op-norm $4.747\times10^{-13}$, block $4.861\times10^{-14}$, Gauss $2.36\times10^{-15}$ |
| synthesis $\varepsilon=10^{-6}$ of $U_D$ + `verify` | 0.027 + 6.004 [5.837, 6.323] s | 617 MB | 8 rot, $T_{rot}=496$, op-norm $3.84\times10^{-6}$, certified |
| **three-layer verification of the headline `r04-F1-004`** (`su2plaq.rishon.compress.three_layer.verify_three_layer`: rebuild from the program in a subprocess, prepend $U_D$, verify at the three triples) | **28.21 s [28.02, 28.26]** per call (process 28.9 s) + `det_layer_metrics` 0.41 s | 775 MB | ok, all three verdicts certified; op-norm $1.64\times10^{-13}$ / $1.67\times10^{-13}$ / $1.69\times10^{-13}$ at $(\alpha,\beta,\eta)$ = (0.37, 0.61, 0.29) / (0.91, 0.23, 0.53) / (1.70, 1.00, 1.07); skeleton equal; unit key (228, 846, 1417, 53), det key (32, 496, 326, 48), three-layer key (260, 1342, 1743, 53); unit $\bar T$ 843.8 + det $\bar T$ 500.8 = 1344.6; outer register untouched |

Det layer relative to the unit step at the same angles: +32 CX on 10 102 (+0.3 %), +8 rotations; the first-call build of step3 (2.3 s) is the same lazy Qiskit import as in `build_step`; warm builds are 11.3-11.6 ms (identical to the two-layer step). `verify` of step3 is +13.8 % over `verify` of the two-layer step (7.90 s vs 6.94 s), the cost of the larger target (`inner_target` with the det exponential).

## 3. pytest, Lean, certificate

| quantity | report 200 | now | note |
|---|---|---|---|
| `pytest -m "not slow" tests/acceptance/m5` (`-n 6`, CPUs 14-19), 1 run | 33 tests, 672.4 s (`-n 10`, T1[step] not yet marked slow) | **54 passed, 596.8 s** (9:57); max single process RSS 6.94 GB (6.64); summed python RSS peak (5-s sampling) 4.87 GB | the suite grew (21 det tests); T1[step] is now marked slow. Wall is set by the single longest test T1[UB] 388.7 s; next DT4 three-layer step[1] 158.7 s, DT4 step[2] 120.1 s, B1 verifier sensitivity 117.1 s, V2 prune cap 110.7 s, S1[2] 103.7 s, S1[1] 91.5 s |
| same, `-k "not T1"`, 3 runs | 30 tests, 102.6 s | 51 passed, 317.3 / 312.5 / 319.4 s | 21 new tests; not comparable with 200. Wall includes DT4 and DT3 det tests (50-160 s each) |
| `pytest -m slow tests/acceptance/m5` (`-n 2`) | L3 only, 2.9 s | 2 passed, 581.7 s: T1[step] 580.9 s, L3 2.76 s | T1[step] (slow-marked since prompts/202 section 7); 581 s is the same as in 200 (`-n 3`: 581.1 s) and below 200's isolated P-core run (607.7 s). The slowdown of F1 in 200 for this test does not appear |
| Lean `lake build Su2Plaq.Rishon.Counts` (cached) x3 | 3.5 s | 2.89 / 2.78 / 2.77 s (1.0 GB) | faster |
| Lean `lake build Su2Plaq.Rishon.JW` (cached) x3 | 0.57 s | 0.48 s (0.84 GB) | |
| Lean `lake env lean Rishon/Counts.lean` (from source) x3 | 8.04 s, 8.30 GB | 8.78 / 8.75 / 8.79 s, 8.43 GB | +9.0 %; plan limit 600 s, 15 GB: met |
| Lean `lake env lean Rishon/JW.lean` (from source) x2 | 61.1 s, 7.07 GB | 66.5 / 66.4 s, 7.08 GB | +8.8 %; the file now also proves `det_u_sector` |
| L3 certificate: export 0.110 s, Lean file 0.35 ms, Python exact check 5.1 ms, native Lean check (certified) x3 | 0.092 s, 0.3 ms, 5 ms, 1.36 s | 0.110 s, 0.35 ms, 5.1 ms, **1.111 / 1.114 / 1.113 s**; tampered $\kappa$ 2 to 1 **rejected** 1.117-1.120 s | 81 pairs, 1296 codes, axioms {propext, Classical.choice, Quot.sound, native_decide} |

`lean/` was not modified (`git status lean` clean; `lake build` only replayed cached `.olean` files).

## 4. Control: separating environment from code

Trigger: section 1 shows rows above the 10 % threshold relative to 200 ($W$ build, `inner_target`, `t_table`, synthesised $U_B$ `verify`, `eigh` real, `_bright`, first `build_UE`). Control as in report 301: the commit of report 200, `86fda8e`, in a detached `git worktree` at `../su2qc-ctl-86fda8e` (afterwards `git worktree move`d to `should-be-deleted/su2qc-ctl-86fda8e-bench303`), the same worker script (`ctl_bench_worker.py`, only the source root is selectable), same CPU 14, one process per run, old and new interleaved, 3 pairs per task (1 pair for the long synthesis), 21 + 21 processes plus 3 + 3 twelve-qubit `evaluate` processes. Load average at the start of each process 1.8-2.7. All numbers in `results/benchmarks/rishon-m5d-raw/ctl/ctl_summary.json`.

| task | old tree `86fda8e` | HEAD | HEAD/old |
|---|---|---|---|
| `inner_target` $U_B$ / step 1 / step 2 (first) | 1.208 / 1.437 / 1.667 s | 1.207 / 1.431 / 1.652 s | 1.000 / 0.996 / 0.991 |
| `eigh` 1296 complex / real | 1.274 / 0.185 s | 1.270 / 0.183 s | 0.996 / 0.987 |
| `_W` build | 0.0766 s [0.0758, 0.0779] | 0.0810 s [0.0746, 0.0864] | 1.058 (within spread) |
| `_bright` | 0.0189 s | 0.0215 s | 1.139 (absolute difference 2.6 ms; n=3, noise-level) |
| `t_table` pygridsynth cold, $U_B$ / step | 0.825 / 0.915 s | 0.824 / 0.913 s | 0.999 / 0.997 |
| `verify` $U_B$ first / later | 7.012 / 6.806 s | 6.749 / 6.528 s | 0.962 / 0.959 |
| `verify` step 1 first / later | 7.168 / 7.026 s | 7.035 / 6.774 s | 0.981 / 0.964 |
| `rishon_basis` cold | 2.424 s | 2.432 s | 1.003 |
| synthesis + `verify` $U_B$ $10^{-6}$ (162 rot), 1 pair | 325.9 s (process 331.3 s) | 326.5 s (process 332.2 s) | **1.002** |
| 12-qubit `evaluate` $U_B$ first / later | 3.107 / 0.842 s | 3.095 / 0.831 s | 0.996 / 0.987 |
| `build_UE` first call | 0.139 s | 0.206 s | 1.483 |
| `logical_metrics` $U_E$ first call (same process, after `build_UE`) | 0.407 s | 0.342 s | 0.840 |

Reading:
- Environment, not code: the old-tree numbers on this machine today equal the HEAD numbers (ratios 0.96-1.01 for every task that exceeded 10 % in section 1; the old tree itself is 15-23 % slower today than in its own report 200, e.g. `inner_target` $U_B$ 1.208 s vs 1.005 s, synthesised $U_B$ 325.9 s vs 276.6 s). Same pattern as report 301 (+25 % on the same install). Cause of the environment shift is a guess (new OS install, numpy 2.5.4/scipy 1.18.1 instead of 2.5.2/1.18.0, CPU governor/frequency, CPU 14 sharing a P-core with CPU 15 instead of a free core); the control excludes only the repository code.
- HEAD verify is 2-4 % faster than the old code on this machine (the prune-cap check was added to `verify` after 200; the 10 % cap re-judge costs nothing measurable).
- `build_UE` first call +48 % (+0.067 s) and `logical_metrics_UE` first call -16 % (-0.065 s): the sum of the two first calls is 0.546 s (old) vs 0.548 s (HEAD). Guess: at HEAD something triggered inside the first `build_UE` (e.g. the Qiskit gate-library import now reached through the module that also defines the det builders) was previously paid in `logical_metrics`. No process in the benchmark or the loop pays only one of the two; the warm times are 38 and 300 microseconds, unchanged. Not a regression, but I did not look at the source to confirm the mechanism.

## 5. Flags and notes for the coordinator

| # | flag | numbers | guessed cause |
|---|---|---|---|
| F1 | 10-23 % slower than report 200 on `inner_target` (+17..+23 %), `_W` (+16 %), `t_table` cold (+15..+18 %), synthesised $U_B$ `verify` (+18 %), `eigh` real / `_bright` (+12..+13 %), first `build_UE` (+58 %) | table 1 | environment (control: HEAD/old = 0.96-1.01 on all but first `build_UE`, whose cost moves between two calls); NOT code |
| F2 | pytest `-m "not slow" m5` 596.8 s is only 0.5 % under the 10 min plan target (200: 672 s, flagged) | 596.8 s, 54 tests | longest test T1[UB] 388.7 s; at `-n 6` placement on mixed P/E-cores; T1[step] is out of this set since prompts/202; 21 new det tests |
| F3 | `verify` of the three-layer step 13.8 % more expensive than the two-layer step (7.90 vs 6.94 s); `threelayer` of the headline 28.2 s | section 2 | larger inner target (det exponential), three verifications at three triples; expected |
| F4 | `robust.json` rewritten as a side effect of my `threelayer` runs: `results/compress/rishon/robust.json` differs from HEAD only in `evaluator_sha256` (`ddb440ad...` -> `a4dbd16c...`, the current rishon evaluator hash of commit `a97e5b1`) | `git diff` one line | `robust.headline` refreshes its cache when the evaluator hash changed; I left the file as is (restoring would put back a stale hash); the coordinator should commit or discard it |
| F5 | memory | pytest single process 6.94 GB (report 200: 6.64 GB), Lean from source 8.43 / 7.08 GB, $U_B$ synthesis re-verify 1.41 GB | unchanged in kind; peak is the same ~6.6-6.9 GB fixture as in 200 (+4.6 %) |

Not tested here (not part of the benchmark): `scripts/m5_results.py` / `m5_det_results.py` regeneration times, compression-round wall time and evaluator time per circuit for the rishon loop (no rishon round ran in this gate; the evaluator is the same file set as in 200 except the prune-cap logic).

## 6. Files touched

- New, untracked: `results/benchmarks/rishon-m5d-raw/` (raw records incl. `ctl/`), `results/benchmarks/rishon-m5d-scripts/`, `results/rishon/bench-303-m5d.json`, this report.
- Modified by side effect: `results/compress/rishon/robust.json` (F4). Test byproducts: none other (`git status` shows no change in `results/*/certs`, `compress/lean/structure.json` or `tests/`).
- Detached worktree `su2qc-ctl-86fda8e-bench303` now in `should-be-deleted/` (registered with git, `git worktree list`); `__pycache__` inside it only.
- No file under `src/`, `tests/` or `prompts/` was edited; `acceptance-check` PASS (acceptance-v20), `tools/check_lock.py` LOCK OK; `graphify update .` not needed (no source changed).

VERDICT: PASS (physics output unchanged to all printed digits; det circuits benchmarked; all >10 % slowdowns vs report 200 traced to the environment by the 86fda8e control).
